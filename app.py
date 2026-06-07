"""FuelEU Pool Optimiser - Streamlit dashboard.

Type your fleet straight into the table (or upload a CSV), pick a reporting
year, and see the lowest-cost compliance plan: how much to pool, how much fuel
to switch, and what penalty remains, compared against doing nothing.

Decision-support only. Not a compliance statement of record. Always confirm
figures with your verifier.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from fueleu_pool.io_csv import load_fleet
from fueleu_pool.optimiser import optimise_fleet
from fueleu_pool.regulation import target_ghg_intensity, REDUCTION_TRAJECTORY

st.set_page_config(page_title="FuelEU Pool Optimiser", layout="wide")

# Column order shared by the editable table and the CSV format.
COLUMNS = [
    "name",
    "attained_intensity",
    "energy_mj",
    "consecutive_deficit_years",
    "switch_intensity",
    "switch_price_spread_eur_mj",
    "switch_max_energy_mj",
]

# A starter fleet so the app shows a working answer the moment it loads.
STARTER = pd.DataFrame(
    [
        ["Aframax_Alpha", 94.5, 2_400_000, 1, None, None, None],
        ["Aframax_Bravo", 93.8, 2_200_000, 2, None, None, None],
        ["Chemtank_Charlie", 82.0, 1_800_000, 1, None, None, None],
        ["Parcel_Delta", 95.2, 2_600_000, 1, 60.0, 0.012, 1_300_000],
        ["Bulker_Echo", 88.5, 2_000_000, 1, None, None, None],
    ],
    columns=COLUMNS,
)


def _money(x: float) -> str:
    return f"\u20ac{x:,.0f}"


def df_to_csv_text(df: pd.DataFrame) -> str:
    """Serialise the editable table to the CSV text the loader expects.

    Routing through the same load_fleet parser means table input and file
    upload share one validated path - there is no second, untested code route.
    """
    return df.to_csv(index=False)


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
    st.metric(
        f"GHG intensity target {year}",
        f"{target_ghg_intensity(year):.2f} gCO\u2082e/MJ",
    )
    st.divider()
    st.caption(
        "The table on the right is pre-filled with an example fleet. Edit it, "
        "add rows, or clear it and enter your own. Prefer a file? Upload a CSV "
        "below \u2014 it uses the same columns."
    )
    uploaded = st.file_uploader("Upload fleet CSV (optional)", type=["csv"])
    st.download_button(
        "Download blank template",
        df_to_csv_text(STARTER),
        "fleet_template.csv",
        "text/csv",
    )

st.subheader("Your fleet")
st.caption(
    "Required: **name**, **attained_intensity** (gCO\u2082e/MJ), **energy_mj**. "
    "Optional: **consecutive_deficit_years** (default 1) and a cleaner-fuel "
    "option \u2014 fill all three switch columns to enable it for a ship."
)

with st.expander("What each column means (tap to open)"):
    st.markdown(
        "**Ship name** \u2014 any label for the vessel. Must be different for each ship.\n\n"
        "**Attained intensity (gCO\u2082e/MJ)** \u2014 how greenhouse-gas-heavy the ship's "
        "energy is, in grams of CO\u2082-equivalent per megajoule. Your verifier provides "
        "this figure. Marine fuels typically sit around 75\u201395; the 2025 limit is "
        "89.34. Below the limit the ship earns a surplus, above it a deficit.\n\n"
        "**Energy (MJ)** \u2014 total energy the ship used on board for in-scope voyages "
        "over the year, in megajoules. As a rough guide, tonnes of VLSFO \u00d7 41,000 "
        "\u2248 MJ. Comes from your fuel-consumption records.\n\n"
        "**Deficit years** \u2014 how many years in a row the ship has been in deficit, "
        "counting this one. Leave at 1 unless it was also in deficit in earlier years; "
        "repeat deficits are penalised more heavily (Article 23(2)).\n\n"
        "**Switch intensity / Switch \u20ac/MJ / Switch max MJ** \u2014 optional, and only "
        "used together. If a ship could move some energy to a cleaner fuel, give that "
        "fuel's intensity (gCO\u2082e/MJ), how much more it costs than the current fuel "
        "(euros per MJ), and the most energy that could be switched (MJ). Leave all "
        "three blank if there's no switch option.\n\n"
        "_All figures are for one reporting year. This is decision-support \u2014 confirm "
        "everything with your verifier._"
    )

# Decide the table's starting content: an uploaded CSV takes precedence,
# otherwise the starter fleet.
if uploaded is not None:
    try:
        upload_df = pd.read_csv(uploaded)
        # Keep only known columns; add any missing optional ones as blank.
        for col in COLUMNS:
            if col not in upload_df.columns:
                upload_df[col] = None
        table_source = upload_df[COLUMNS]
    except Exception as e:
        st.error(f"Could not read that CSV: {e}")
        table_source = STARTER
else:
    table_source = STARTER

edited = st.data_editor(
    table_source,
    num_rows="dynamic",          # users can add and delete rows
    use_container_width=True,
    hide_index=True,
    column_config={
        "name": st.column_config.TextColumn(
            "Ship name", required=True,
            help="Any label for the vessel. Must be different for each ship.",
        ),
        "attained_intensity": st.column_config.NumberColumn(
            "Attained intensity (gCO\u2082e/MJ)", min_value=0.0, format="%.2f",
            help=(
                "How greenhouse-gas-heavy the ship's energy is, in grams of "
                "CO\u2082-equivalent per megajoule. Your verifier provides this "
                "figure. Marine fuels typically fall around 75\u201395; the 2025 "
                "limit is 89.34. Below the limit = surplus, above it = deficit."
            ),
        ),
        "energy_mj": st.column_config.NumberColumn(
            "Energy (MJ)", min_value=0.0, format="%.0f",
            help=(
                "Total energy the ship used on board for in-scope voyages over "
                "the year, in megajoules. Roughly: tonnes of fuel \u00d7 ~41,000 "
                "for VLSFO. From your fuel-consumption records."
            ),
        ),
        "consecutive_deficit_years": st.column_config.NumberColumn(
            "Deficit years", min_value=1, step=1, format="%d",
            help=(
                "How many years in a row this ship has been in deficit, "
                "including this one. Leave at 1 unless it was also in deficit "
                "in previous years \u2014 repeat deficits carry a higher penalty "
                "(Article 23(2))."
            ),
        ),
        "switch_intensity": st.column_config.NumberColumn(
            "Switch intensity", min_value=0.0, format="%.2f",
            help=(
                "Optional. If this ship could switch to a cleaner fuel, its "
                "GHG intensity (gCO\u2082e/MJ). Leave blank if no switch option."
            ),
        ),
        "switch_price_spread_eur_mj": st.column_config.NumberColumn(
            "Switch \u20ac/MJ", min_value=0.0, format="%.4f",
            help=(
                "Optional. Extra cost of the cleaner fuel over the current one, "
                "in euros per megajoule. Leave blank if no switch option."
            ),
        ),
        "switch_max_energy_mj": st.column_config.NumberColumn(
            "Switch max MJ", min_value=0.0, format="%.0f",
            help=(
                "Optional. The most energy (MJ) the ship could realistically "
                "move to the cleaner fuel. Leave blank if no switch option."
            ),
        ),
    },
)

# Drop fully-empty rows (a blank trailing row the editor leaves behind).
clean = edited.dropna(how="all")
clean = clean[clean["name"].notna() & (clean["name"].astype(str).str.strip() != "")]

if clean.empty:
    st.info("Add at least one ship to the table to see a plan.")
    st.stop()

# Plausibility checks: warn (don't block) on values that look like typos.
# A non-expert won't know an intensity of 334 is impossible - the tool does.
# Generous bounds: we flag clear nonsense, not merely unusual-but-valid values.
def _plausibility_warnings(df: pd.DataFrame) -> list[str]:
    # ~1 GJ in MJ for a single very large vessel-year is in the low billions;
    # 100 billion MJ is far beyond any single ship, so it's almost certainly a
    # mistyped figure or wrong unit.
    ENERGY_SANITY_CEILING = 100_000_000_000  # 1e11 MJ
    warns: list[str] = []
    for _, r in df.iterrows():
        nm = str(r.get("name", "")).strip() or "(unnamed)"

        ai = r.get("attained_intensity")
        if pd.notna(ai) and (ai < 50 or ai > 150):
            warns.append(
                f"**{nm}**: attained intensity of {ai:g} gCO\u2082e/MJ is outside "
                "the usual marine range (~75\u201395). Double-check it's not a typo."
            )

        en = r.get("energy_mj")
        if pd.notna(en) and en <= 0:
            warns.append(f"**{nm}**: energy is {en:g} MJ \u2014 should be a positive number.")
        elif pd.notna(en) and en > ENERGY_SANITY_CEILING:
            warns.append(
                f"**{nm}**: energy of {en:,.0f} MJ is implausibly large for one "
                "ship in a year. Check the figure and the unit (the column is MJ)."
            )

        dy = r.get("consecutive_deficit_years")
        if pd.notna(dy) and dy > 10:
            warns.append(
                f"**{nm}**: {int(dy)} consecutive deficit years looks high \u2014 "
                "this is usually 1 unless the ship was in deficit in prior years."
            )

        # Optional switch columns: flag a partial set (only some of the three
        # filled) and out-of-range switch values.
        si = r.get("switch_intensity")
        sp = r.get("switch_price_spread_eur_mj")
        sm = r.get("switch_max_energy_mj")
        filled = [pd.notna(si), pd.notna(sp), pd.notna(sm)]
        if any(filled) and not all(filled):
            warns.append(
                f"**{nm}**: the cleaner-fuel option needs all three switch "
                "columns filled (intensity, \u20ac/MJ, and max MJ). With only some "
                "filled, the switch is ignored for this ship."
            )
        if pd.notna(si) and (si < 0 or si > 150):
            warns.append(
                f"**{nm}**: switch intensity of {si:g} gCO\u2082e/MJ is out of range "
                "(a cleaner fuel should be well below ~90). Double-check it."
            )
        if pd.notna(sm) and pd.notna(en) and sm > en > 0:
            warns.append(
                f"**{nm}**: switch max energy ({sm:,.0f} MJ) exceeds the ship's "
                f"total energy ({en:,.0f} MJ). You can't switch more than the ship uses."
            )
    return warns

issues = _plausibility_warnings(clean)
if issues:
    st.warning(
        "Some values look unusual \u2014 the result below still uses exactly what "
        "you entered, so check these first:\n\n" + "\n\n".join(f"- {w}" for w in issues)
    )

# One validated path: serialise the table and parse it with the same loader
# the CSV upload uses.
try:
    ships, switch_options = load_fleet(df_to_csv_text(clean))
except Exception as e:
    st.error(f"Check the fleet: {e}")
    st.stop()

result = optimise_fleet(ships, year, switch_options)

st.subheader("Result")
c1, c2, c3 = st.columns(3)
c1.metric(
    "If you do nothing",
    _money(result.do_nothing_cost),
    help="Sum of each ship's standalone penalty, no pooling or switching.",
)
c2.metric("Optimised plan", _money(result.total_cost))
c3.metric(
    "Savings",
    _money(result.savings_vs_do_nothing),
    delta=f"{(result.savings_vs_do_nothing / result.do_nothing_cost * 100) if result.do_nothing_cost else 0:.0f}%",
)

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
