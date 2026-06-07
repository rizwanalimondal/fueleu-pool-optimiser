"""Fuel reference data and GHG-intensity calculation (Annex I & II).

Every default value here is transcribed from Annex II of Regulation (EU)
2023/1805 and cross-checked against published guidance (ABS FAQ, BetterSea
GHG-intensity guide, Sustainable Ships' Annex II transcription, and the
European Commission ESSF SAPS WS1 methodology working draft).

IMPORTANT modelling notes (stated, not hidden):
  * GWP values use AR4 (CO2=1, CH4=25, N2O=298), which is what FuelEU
    currently references via RED II. A future revision is expected to move to
    AR5 (CO2=1, CH4=28, N2O=265) to align with the revised EU MRV; this tool
    uses the CURRENT (AR4) values and flags this so the user is not surprised.
  * Fossil-fuel TtW CO2 factors are NOT user-overridable under the regulation
    (Art. 10). The tool lets you edit, but the README states this clearly.
  * Biofuels/RFNBOs: GHG intensity comes from the fuel's Proof of
    Sustainability (an "E value", a WtW figure). For those, supply the
    attained intensity directly (BYO) rather than relying on a default; the
    blended examples below (B30) are illustrative only and labelled as such.

This module is decision-support, not a compliance calculation of record.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Global warming potentials (AR4, current FuelEU/RED II basis) -----------
GWP_CO2 = 1.0
GWP_CH4 = 25.0
GWP_N2O = 298.0


@dataclass
class Fuel:
    """A fuel pathway with Annex II default parameters.

    Fields mirror Annex II columns. TtW carbon factors are per gram of fuel.
    `source` records provenance; `user_supplied` marks any value the user has
    overridden so the tool never presents an edited number as the regulation's
    own default.
    """

    name: str
    fuel_class: str            # "Fossil", "Biofuel", "RFNBO"
    lcv_mj_per_g: float        # Lower calorific value, MJ/g fuel
    wtt_gco2e_per_mj: float    # Well-to-Tank emission factor, gCO2e/MJ
    cf_co2: float              # TtW CO2, g/g fuel
    cf_ch4: float              # TtW CH4, g/g fuel
    cf_n2o: float              # TtW N2O, g/g fuel
    c_slip: float = 0.0        # Fraction of fuel slipped unburned (e.g. LNG)
    source: str = ""
    user_supplied: bool = False
    # For non-fossil fuels, an attained WtW intensity may be given directly
    # (from the Proof of Sustainability). If set, it overrides the computed
    # value entirely.
    attained_intensity_override: float | None = None

    def ttw_gco2e_per_mj(self) -> float:
        """Tank-to-Wake intensity in gCO2e/MJ (Annex I).

        Combustion term: (Cf_CO2*GWP_CO2 + Cf_CH4*GWP_CH4 + Cf_N2O*GWP_N2O)
        per gram of fuel, divided by LCV (MJ/g) to get gCO2e/MJ. Slipped fuel
        (unburned) is treated as CH4 escaping to atmosphere for gaseous fuels.
        """
        burned_fraction = 1.0 - self.c_slip
        combustion = (
            self.cf_co2 * GWP_CO2
            + self.cf_ch4 * GWP_CH4
            + self.cf_n2o * GWP_N2O
        ) * burned_fraction
        # Methane slip: slipped mass treated as CH4 (g/g fuel) * GWP_CH4.
        slip = self.c_slip * GWP_CH4
        return (combustion + slip) / self.lcv_mj_per_g

    def wtw_gco2e_per_mj(self) -> float:
        """Well-to-Wake GHG intensity in gCO2e/MJ (Annex I).

        If an attained-intensity override is set (non-fossil, from PoS), use
        it. Otherwise WtW = WtT + TtW.
        """
        if self.attained_intensity_override is not None:
            return self.attained_intensity_override
        return self.wtt_gco2e_per_mj + self.ttw_gco2e_per_mj()


# --- Annex II default pathways ----------------------------------------------
# Carbon factors (Cf) and LCVs transcribed from Annex II; cross-checked across
# ABS, BetterSea and Sustainable Ships' Annex II transcription.
def _default_fuels() -> dict[str, Fuel]:
    ann2 = "Reg (EU) 2023/1805 Annex II"
    return {
        "HFO": Fuel(
            name="HFO", fuel_class="Fossil",
            lcv_mj_per_g=0.0405, wtt_gco2e_per_mj=13.5,
            cf_co2=3.114, cf_ch4=0.00005, cf_n2o=0.00018,
            source=ann2,
        ),
        "LFO": Fuel(
            name="LFO", fuel_class="Fossil",
            lcv_mj_per_g=0.0410, wtt_gco2e_per_mj=13.2,
            cf_co2=3.151, cf_ch4=0.00005, cf_n2o=0.00018,
            source=ann2,
        ),
        "MDO": Fuel(
            name="MDO", fuel_class="Fossil",
            lcv_mj_per_g=0.0427, wtt_gco2e_per_mj=14.4,
            cf_co2=3.206, cf_ch4=0.00005, cf_n2o=0.00018,
            source=ann2,
        ),
        "MGO": Fuel(
            name="MGO", fuel_class="Fossil",
            lcv_mj_per_g=0.0427, wtt_gco2e_per_mj=14.4,
            cf_co2=3.206, cf_ch4=0.00005, cf_n2o=0.00018,
            source=ann2,
        ),
        "LNG_Otto_MS": Fuel(
            name="LNG (Otto, medium-speed dual fuel)", fuel_class="Fossil",
            lcv_mj_per_g=0.0491, wtt_gco2e_per_mj=18.5,
            cf_co2=2.750, cf_ch4=0.0, cf_n2o=0.00011, c_slip=0.031,
            source=ann2 + " (LNG Otto medium-speed; methane slip 3.1%)",
        ),
        # B30: 30% bio / 70% fossil blend. ILLUSTRATIVE ONLY — real biofuel
        # intensity comes from the Proof of Sustainability. Modelled here as a
        # VLSFO-equivalent fossil base with a typical certified bio E-value.
        "B30_illustrative": Fuel(
            name="B30 (illustrative blend)", fuel_class="Biofuel",
            lcv_mj_per_g=0.0405, wtt_gco2e_per_mj=0.0,
            cf_co2=0.0, cf_ch4=0.0, cf_n2o=0.0,
            attained_intensity_override=65.0,  # illustrative WtW gCO2e/MJ
            source="ILLUSTRATIVE — supply your own PoS E-value for real use",
        ),
    }


DEFAULT_FUELS = _default_fuels()


def get_fuel(name: str) -> Fuel:
    """Return a copy of a default fuel so edits don't mutate the table."""
    import copy
    if name not in DEFAULT_FUELS:
        raise KeyError(
            f"Unknown fuel '{name}'. Known: {sorted(DEFAULT_FUELS)}. "
            "For biofuels/RFNBOs, supply attained intensity from your PoS."
        )
    return copy.deepcopy(DEFAULT_FUELS[name])
