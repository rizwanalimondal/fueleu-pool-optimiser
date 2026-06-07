"""Optimiser tests with hand-verifiable scenarios.

Each scenario is small enough to reason about by hand so the optimiser's
choice can be checked against the obviously-correct answer.
"""

import pulp
import pytest

from fueleu_pool.cost_model import Ship, FuelSwitchOption
from fueleu_pool.fuels import Fuel
from fueleu_pool.optimiser import optimise_fleet
from fueleu_pool.regulation import target_ghg_intensity


YEAR = 2025
TARGET = target_ghg_intensity(YEAR)  # 89.34


def _clean_fuel(intensity: float) -> Fuel:
    """A synthetic fuel whose WtW intensity is exactly `intensity`."""
    return Fuel(
        name=f"clean_{intensity}", fuel_class="Biofuel",
        lcv_mj_per_g=0.04, wtt_gco2e_per_mj=0.0,
        cf_co2=0.0, cf_ch4=0.0, cf_n2o=0.0,
        attained_intensity_override=intensity, source="synthetic test fuel",
    )


def test_solver_available():
    assert pulp.PULP_CBC_CMD(msg=0).available()


def test_pooling_beats_paying_when_surplus_covers_deficit():
    # One deficit ship and one surplus ship in the same fleet. The surplus
    # fully covers the deficit, so internal pooling should drive cost to ~0,
    # far below the standalone penalty.
    deficit_ship = Ship("deficit", attained_intensity=95.0, energy_mj=2_000_000)
    surplus_ship = Ship("surplus", attained_intensity=80.0, energy_mj=2_000_000)
    res = optimise_fleet([deficit_ship, surplus_ship], YEAR)

    assert res.do_nothing_cost > 0          # standalone, the deficit ship pays
    assert res.total_cost == pytest.approx(0.0, abs=1.0)  # pooling covers it
    assert res.savings_vs_do_nothing == pytest.approx(res.do_nothing_cost, abs=1.0)


def test_no_pooling_possible_falls_back_to_penalty():
    # Two deficit ships, no surplus anywhere -> pooling can't help, so the
    # fleet cost must equal the sum of standalone penalties.
    a = Ship("a", attained_intensity=95.0, energy_mj=1_000_000)
    b = Ship("b", attained_intensity=92.0, energy_mj=1_500_000)
    res = optimise_fleet([a, b], YEAR)
    assert res.total_cost == pytest.approx(res.do_nothing_cost, rel=1e-6)
    assert res.savings_vs_do_nothing == pytest.approx(0.0, abs=1.0)


def test_cheap_fuel_switch_chosen_over_penalty():
    # A single deficit ship with a very cheap clean-fuel option should switch
    # rather than pay. Make the spread trivially small so switching dominates.
    ship = Ship("solo", attained_intensity=95.0, energy_mj=1_000_000)
    clean = _clean_fuel(50.0)  # well below target
    opt = FuelSwitchOption(
        replacement_fuel=clean,
        price_spread_eur_per_mj=1e-6,   # almost free
        max_energy_mj=1_000_000,
    )
    res = optimise_fleet([ship], YEAR, switch_options={"solo": opt})
    # Switching is nearly free and removes the deficit, so cost << penalty.
    assert res.total_cost < res.do_nothing_cost * 0.05
    plan = res.ship_plans[0]
    assert plan.energy_switched_mj > 0


def test_expensive_fuel_switch_rejected_in_favour_of_penalty():
    # If the clean fuel spread is more expensive per gCO2e abated than the
    # penalty rate, the optimiser should prefer paying the penalty.
    ship = Ship("solo", attained_intensity=95.0, energy_mj=1_000_000)
    clean = _clean_fuel(50.0)
    opt = FuelSwitchOption(
        replacement_fuel=clean,
        price_spread_eur_per_mj=1.0,    # absurdly expensive
        max_energy_mj=1_000_000,
    )
    res = optimise_fleet([ship], YEAR, switch_options={"solo": opt})
    plan = res.ship_plans[0]
    assert plan.energy_switched_mj == pytest.approx(0.0, abs=1.0)
    assert res.total_cost == pytest.approx(res.do_nothing_cost, rel=1e-6)


def test_partial_pooling_then_penalty_on_remainder():
    # Surplus partially covers a larger deficit; remainder is penalised.
    # deficit ship: (89.34-95)*3e6 = -16.98e6 gCO2e deficit
    # surplus ship: (89.34-85)*1e6 = +4.34e6 gCO2e surplus
    # ~4.34e6 covered, residual ~12.64e6 penalised.
    deficit_ship = Ship("deficit", attained_intensity=95.0, energy_mj=3_000_000)
    surplus_ship = Ship("surplus", attained_intensity=85.0, energy_mj=1_000_000)
    res = optimise_fleet([deficit_ship, surplus_ship], YEAR)

    assert 0 < res.total_cost < res.do_nothing_cost
    deficit_plan = next(p for p in res.ship_plans if p.name == "deficit")
    assert deficit_plan.deficit_covered_by_pool == pytest.approx(4.34e6, rel=0.05)
    assert deficit_plan.residual_deficit > 0
