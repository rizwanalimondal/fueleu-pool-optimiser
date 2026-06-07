"""Core FuelEU Maritime regulatory calculations.

All constants and formulas trace to Regulation (EU) 2023/1805 ("FuelEU
Maritime"). Article and Annex references are given inline so every number
can be checked against the primary text. Where the regulation is silent or
ambiguous, the assumption is stated explicitly rather than hidden.

This module is decision-support only. It is NOT a compliance guarantee and
does not replace a verifier's assessment.
"""

from __future__ import annotations

# --- Reference value and reduction trajectory -------------------------------
# Article 4(2): the GHG intensity limit is the 2020 reference value reduced by
# a percentage that tightens over time. Reference value is fixed by the
# regulation. Source: Reg (EU) 2023/1805, Art. 4(2) and Annex I.
REFERENCE_GHG_INTENSITY = 91.16  # gCO2e/MJ, well-to-wake (2020 baseline)

# Reduction percentages by period start year (Art. 4(2)). Each value applies
# from its year up to (but not including) the next breakpoint.
REDUCTION_TRAJECTORY = {
    2025: 0.02,   # -2%
    2030: 0.06,   # -6%
    2035: 0.145,  # -14.5%
    2040: 0.31,   # -31%
    2045: 0.62,   # -62%
    2050: 0.80,   # -80%
}

# --- Penalty parameters -----------------------------------------------------
# Annex IV: remedial penalty is EUR 2400 per tonne of VLSFO-equivalent energy
# in deficit. VLSFO lower calorific value is 41 000 MJ/tonne (Annex IV uses
# the conversion factor 41.0 MJ/g i.e. 41 000 MJ per tonne).
PENALTY_PER_TONNE_VLSFO = 2400.0  # EUR
VLSFO_LCV_MJ_PER_TONNE = 41_000.0  # MJ/tonne (Annex IV conversion basis)

# Art. 23(2): for each consecutive reporting period (from the second onward)
# in which the ship is in deficit, the penalty is multiplied by a factor that
# increases. n = number of consecutive deficit periods; multiplier = (n+1)/10
# applied per Annex IV note. v1 models the first-year case (multiplier 1.0)
# and exposes the multiplier as an explicit input for transparency.
def consecutive_deficit_multiplier(consecutive_years: int) -> float:
    """Penalty multiplier for repeated annual deficits (Art. 23(2)).

    Year 1 of deficit: 1.0. The regulation increases the factor for each
    further consecutive deficit year. Exposed explicitly so the user controls
    the assumption rather than the tool silently picking one.
    """
    if consecutive_years < 1:
        raise ValueError("consecutive_years must be >= 1")
    # First deficit year carries no uplift.
    return 1.0 + 0.10 * (consecutive_years - 1)


def reduction_for_year(year: int) -> float:
    """Return the reduction fraction applicable in `year` (Art. 4(2))."""
    applicable = [y for y in REDUCTION_TRAJECTORY if y <= year]
    if not applicable:
        raise ValueError(
            f"FuelEU Maritime applies from 2025; year {year} is out of scope."
        )
    return REDUCTION_TRAJECTORY[max(applicable)]


def target_ghg_intensity(year: int) -> float:
    """GHG intensity limit (gCO2e/MJ) for a given year (Art. 4)."""
    return REFERENCE_GHG_INTENSITY * (1.0 - reduction_for_year(year))


def compliance_balance(
    attained_ghg_intensity: float,
    energy_mj: float,
    year: int,
) -> float:
    """Compliance balance in gCO2e (Annex IV).

    CB = (target - attained) * energy_used_MJ

    Positive => surplus (over-compliant). Negative => deficit.
    `attained_ghg_intensity` is the ship's well-to-wake gCO2e/MJ.
    `energy_mj` is total energy used on board in scope, in MJ.
    """
    if energy_mj < 0:
        raise ValueError("energy_mj must be non-negative")
    return (target_ghg_intensity(year) - attained_ghg_intensity) * energy_mj


def penalty_eur(
    compliance_balance_gco2e: float,
    attained_ghg_intensity: float,
    consecutive_years: int = 1,
) -> float:
    """FuelEU remedial penalty in EUR for a deficit balance (Annex IV).

    Annex IV Part B penalty formula (confirmed verbatim against the regulation
    and the European Commission guidance document):

        penalty = (|CB_deficit| / (GHGIE_actual * 41000)) * 2400

    Reading the conversion chain (confirmed against the Annex IV Part B
    formula in Regulation (EU) 2023/1805 and the EC guidance document):
      1. |CB_deficit| is the deficit in gCO2e.
      2. Divide by GHGIE_actual (gCO2e/MJ) -> non-compliant energy in MJ.
      3. Divide by 41 000 MJ/tonne -> tonnes of VLSFO-equivalent.
      4. Multiply by EUR 2400/tonne -> penalty in EUR.
    This is ~EUR 0.058 per MJ of non-compliant energy, matching ABS's
    published cross-check.

    For repeated consecutive deficit years, Art. 23(2) applies a multiplier of
    1 + (n-1)/10.

    A surplus (>= 0) incurs no penalty.
    """
    if compliance_balance_gco2e >= 0:
        return 0.0
    if attained_ghg_intensity <= 0:
        raise ValueError("attained_ghg_intensity must be positive")
    deficit_gco2e = abs(compliance_balance_gco2e)
    non_compliant_energy_mj = deficit_gco2e / attained_ghg_intensity
    tonnes_vlsfo_equiv = non_compliant_energy_mj / VLSFO_LCV_MJ_PER_TONNE
    base_penalty = tonnes_vlsfo_equiv * PENALTY_PER_TONNE_VLSFO
    return base_penalty * consecutive_deficit_multiplier(consecutive_years)
