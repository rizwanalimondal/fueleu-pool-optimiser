"""Tests for the FuelEU regulation core.

These validate against values published in primary and class-society sources:
 - 2025 target 89.34 gCO2e/MJ (91.16 * 0.98), per BetterSea/Art. 4(2).
 - ABS cross-check: the GHG-intensity penalty is ~EUR 0.058 per MJ of
   non-compliant energy.
 - Art. 23(2) consecutive-deficit multiplier 1 + (n-1)/10.
"""

import math
import pytest

from fueleu_pool.regulation import (
    REFERENCE_GHG_INTENSITY,
    target_ghg_intensity,
    reduction_for_year,
    compliance_balance,
    penalty_eur,
    consecutive_deficit_multiplier,
)


def test_reference_value():
    assert REFERENCE_GHG_INTENSITY == 91.16


def test_2025_target_matches_published():
    # 91.16 * (1 - 0.02) = 89.3368, published rounded as 89.34
    assert target_ghg_intensity(2025) == pytest.approx(89.34, abs=0.01)


def test_2030_target():
    # 91.16 * (1 - 0.06) = 85.6904
    assert target_ghg_intensity(2030) == pytest.approx(85.69, abs=0.01)


def test_trajectory_breakpoints():
    assert reduction_for_year(2025) == 0.02
    assert reduction_for_year(2029) == 0.02   # still in 2025 band
    assert reduction_for_year(2030) == 0.06
    assert reduction_for_year(2034) == 0.06
    assert reduction_for_year(2035) == 0.145
    assert reduction_for_year(2050) == 0.80


def test_out_of_scope_year_raises():
    with pytest.raises(ValueError):
        reduction_for_year(2024)


def test_compliance_balance_sign():
    # Below target -> surplus (positive). Above target -> deficit (negative).
    target = target_ghg_intensity(2025)
    surplus = compliance_balance(target - 5.0, 1_000_000.0, 2025)
    deficit = compliance_balance(target + 5.0, 1_000_000.0, 2025)
    assert surplus > 0
    assert deficit < 0
    # Symmetric magnitude for symmetric intensity gap and same energy.
    assert surplus == pytest.approx(-deficit)


def test_penalty_zero_on_surplus():
    assert penalty_eur(1_000_000.0, attained_ghg_intensity=85.0) == 0.0
    assert penalty_eur(0.0, attained_ghg_intensity=85.0) == 0.0


def test_penalty_abs_per_mj_crosscheck():
    # ABS: penalty ~ EUR 0.058 per MJ of non-compliant energy.
    # Construct a deficit whose non-compliant energy is exactly 1 MJ:
    # non_compliant_energy = |CB| / GHGIE_actual = 1 MJ  => |CB| = GHGIE_actual.
    ghgie_actual = 95.0
    cb = -ghgie_actual  # gives exactly 1 MJ non-compliant energy
    p = penalty_eur(cb, attained_ghg_intensity=ghgie_actual)
    # 1 MJ / 41000 * 2400 = 0.05854 EUR
    assert p == pytest.approx(0.0585, abs=0.0005)


def test_penalty_known_magnitude():
    # 1000 tonnes VLSFO-equivalent of non-compliant energy:
    # non_compliant_energy = 1000 * 41000 MJ; |CB| = energy * GHGIE_actual.
    ghgie_actual = 91.0
    non_compliant_mj = 1000 * 41000
    cb = -(non_compliant_mj * ghgie_actual)
    p = penalty_eur(cb, attained_ghg_intensity=ghgie_actual)
    assert p == pytest.approx(1000 * 2400, rel=1e-9)  # EUR 2.4M


def test_consecutive_multiplier():
    assert consecutive_deficit_multiplier(1) == 1.0
    assert consecutive_deficit_multiplier(2) == pytest.approx(1.1)
    assert consecutive_deficit_multiplier(3) == pytest.approx(1.2)
    with pytest.raises(ValueError):
        consecutive_deficit_multiplier(0)


def test_penalty_applies_multiplier():
    ghgie_actual = 91.0
    cb = -(1000 * 41000 * ghgie_actual)
    base = penalty_eur(cb, attained_ghg_intensity=ghgie_actual, consecutive_years=1)
    year3 = penalty_eur(cb, attained_ghg_intensity=ghgie_actual, consecutive_years=3)
    assert year3 == pytest.approx(base * 1.2)
