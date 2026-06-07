"""FuelEU Pool Optimiser - Streamlit dashboard.

Upload a fleet CSV, pick a reporting year, and see the lowest-cost compliance
plan: how much to pool, how much fuel to switch, and what penalty remains,
compared against doing nothing.

Decision-support only. Not a compliance statement of record. Always confirm
figures with your verifier.
"""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from fueleu_pool.io_csv import load_fleet
from fueleu_pool.optimiser import optimise_fleet
from fueleu_pool.regulation import target_ghg_intensity, REDUCTION_TRAJECTORY

st.set_page_config(page_title="FuelEU Pool Optimiser", layout="wide")

st.title("FuelEU Maritime Pool Optimiser")
st.caption(
    "Find the lowest-cost path to fleet compliance: pool surpluses against "
    "deficits, switch fuel where it pays, and pay the penalty only on what's "
    "left. Decision-support only \u2014 not a compliance statement of record."
)

with st.sidebar:
    st.header("Inputs")
    years = sorted(REDUCTION_TRAJECTORY)
    year = st.selectbox("Reporting year", years, index=0)
    st.metric(f"GHG intensity target {year}", f"{target_ghg_intensity(year):.2f} gCO\u2082e/MJ")
    st.divider()
    uploaded = st.file_uploader("Fleet CSV", type=["csv"])
    st.caption(
        "Need the format? Download the sample below, edit it, and re-upload."
    )
    sample = (
        "name,attained_intensity,energy_mj,consecutive_deficit_years,"
        "switch_intensity,switch_price_spread_eur_mj,switch_max_energy_mj\n"
        "Aframax_Alpha,94.5,2400000,1,,,\n"
        "Chemtank_Charlie,82.0,1800000,1,,,\n"
        "Parcel_Delta,95.2,2600000,1,60.0,0.012,1300000\n"
    )
    st.download_button("Download sample CSV", sample, "sample_fleet.csv", "text/csv")


def _money(x: float) -> str:
    return f"\u20ac{x:,.0f}"


if uploaded is None:
    st.info("Upload a fleet CSV to begin, or grab the sample from the sidebar.")
    with st.expander("What the columns mean"):
        st.markdown(
            "- **name** \u2014 unique vessel name\n"
            "- **attained_intensity** \u2014 well-to-wake GHG intensity in gCO\u2082e/MJ "
            "(from your verifier, or computed from your fuel mix)\n"
            "- **energy_mj** \u2014 in-scope energy used on board, in MJ\n"
            "- **consecutive_deficit_years** \u2014 optional; drives the Article 23(2) "
            "repeat-deficit multiplier (default 1)\n"
            "- **switch_intensity / switch_price_spread_eur_mj / switch_max_energy_mj** "
            "\u2014 optional; a cleaner-fuel option for that ship. Provide all three to "
            "enable it."
        )
    st.stop()

try:
    text = uploaded.getvalue().decode("utf-8")
    ships, switch_options = load_fleet(text)
except Exception as e:  # surface parse errors plainly
    st.error(f"Could not read that CSV: {e}")
    st.stop()

result = optimise_fleet(ships, year, switch_options)

c1, c2, c3 = st.columns(3)
c1.metric("If you do nothing", _money(result.do_nothing_cost),
          help="Sum of each ship's standalone penalty, no pooling or switching.")
c2.metric("Optimised plan", _money(result.total_cost))
c3.metric("Savings", _money(result.savings_vs_do_nothing),
          delta=f"{(result.savings_vs_do_nothing / result.do_nothing_cost * 100) if result.do_nothing_cost else 0:.0f}%")

st.subheader("Per-ship plan")
rows = []
for p in result.ship_plans:
    rows.append({
        "Ship": p.name,
        "Balance (gCO\u2082e)": f"{p.balance_before/1e6:+.2f}M",
        "Status": "surplus" if p.balance_before >= 0 else "deficit",
        "Fuel switched (MJ)": f"{p.energy_switched_mj/1e6:.2f}M" if p.energy_switched_mj else "\u2014",
        "Deficit pooled (gCO\u2082e)": f"{p.deficit_covered_by_pool/1e6:.2f}M" if p.deficit_covered_by_pool else "\u2014",
        "Surplus donated (gCO\u2082e)": f"{p.surplus_donated/1e6:.2f}M" if p.surplus_donated else "\u2014",
        "Residual penalty": _money(p.penalty),
        "Ship cost": _money(p.total_cost),
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("Methodology and assumptions"):
    for a in result.assumptions:
        st.markdown(f"- {a}")
    st.markdown(
        "- GHG-intensity targets, compliance balance and the penalty follow "
        "Regulation (EU) 2023/1805 (Articles 4, 21, 23 and Annexes I, II, IV).\n"
        "- This tool is decision-support, not a compliance statement of record. "
        "Confirm all figures with your verifier before acting."
    )
