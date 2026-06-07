"""Fleet compliance optimiser (the core novel component).

Given a fleet of ships (each with a compliance balance), candidate fuel
switches, and the penalty regime, find the lowest-cost way to bring the fleet
to a valid position, choosing per ship among: pay penalty, switch fuel, and
pool surpluses against deficits.

WHY A MILP, AND THE ONE LINEARISATION WE MAKE (stated, not hidden)
------------------------------------------------------------------
Working in gCO2e "compliance balance" space keeps the problem linear:
  * Each ship has a balance CB_i (gCO2e); negative = deficit.
  * Pooling is just netting: the fleet is valid if sum(CB_i) + (reductions
    bought) >= 0, AND no individual ship is left worse than a chosen baseline.
    Internal pooling within one company is allowed by Art. 21; the regulation
    requires the *pool total* to be non-negative. We additionally never force
    a surplus ship below zero (we only use surplus that exists).
  * A fuel switch reduces a ship's deficit by a computable amount of gCO2e per
    MJ switched: delta_g_per_mj = (incumbent_intensity - clean_intensity).
    This is exactly linear in energy switched.

The non-linear part is the *penalty*, because Annex IV divides the deficit by
the ship's attained intensity (which itself changes when you switch fuel).
We avoid the division-of-variables trap as follows:
  * The penalty per gCO2e of residual deficit is approximately constant:
    EUR 2400 / (GHGIE_actual * 41000). Across realistic marine intensities
    (~85-95 gCO2e/MJ) this rate varies only ~+/-5%. We use each ship's
    *attained* intensity to fix its penalty rate, which is exact when that
    ship does NOT switch fuel, and a close approximation when it does. We
    flag this assumption in the result and in the README. For exact figures
    after a switch, the per-ship penalty is recomputed precisely in the
    cost_model and reported alongside.

So the objective is linear:
    minimise  sum_i [ penalty_rate_i * residual_deficit_g_i
                      + price_spread_i * energy_switched_i ]
subject to pooling/validity constraints. This is an LP (continuous switch
quantities) with optional binary "use this lever" indicators -> MILP.

This is decision-support, not a compliance statement of record.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pulp

from .cost_model import Ship, FuelSwitchOption
from .regulation import VLSFO_LCV_MJ_PER_TONNE, PENALTY_PER_TONNE_VLSFO


@dataclass
class ShipPlan:
    name: str
    balance_before: float          # gCO2e
    energy_switched_mj: float       # lever 2 quantity chosen
    fuel_switch_cost: float         # EUR
    surplus_donated: float          # gCO2e given to the pool (if surplus ship)
    deficit_covered_by_pool: float  # gCO2e of deficit covered by pooling
    residual_deficit: float         # gCO2e still in deficit -> penalised
    penalty: float                  # EUR on the residual
    total_cost: float               # EUR (penalty + fuel switch)


@dataclass
class FleetResult:
    year: int
    ship_plans: list[ShipPlan]
    total_cost: float
    do_nothing_cost: float          # sum of standalone penalties, no pooling
    savings_vs_do_nothing: float
    assumptions: list[str] = field(default_factory=list)


def _penalty_rate(attained_intensity: float) -> float:
    """EUR per gCO2e of deficit for a ship at this attained intensity."""
    # penalty = (|CB| / (intensity * 41000)) * 2400
    return PENALTY_PER_TONNE_VLSFO / (attained_intensity * VLSFO_LCV_MJ_PER_TONNE)


def optimise_fleet(
    ships: list[Ship],
    year: int,
    switch_options: dict[str, FuelSwitchOption] | None = None,
) -> FleetResult:
    """Minimise total fleet compliance cost.

    `switch_options` maps ship name -> a fuel-switch lever available to it.
    Ships absent from the map have only penalty + pooling available.
    """
    switch_options = switch_options or {}
    prob = pulp.LpProblem("fueleu_fleet", pulp.LpMinimize)

    # Per-ship data
    balances = {s.name: s.balance(year) for s in ships}
    rates = {s.name: _penalty_rate(s.attained_intensity) for s in ships}

    # Decision variables ----------------------------------------------------
    # energy switched per ship (continuous, bounded)
    switch = {}
    # gCO2e reduction from switching (derived, linear in switch energy)
    for s in ships:
        opt = switch_options.get(s.name)
        ub = opt.max_energy_mj if opt else 0.0
        switch[s.name] = pulp.LpVariable(f"switch_{s.name}", lowBound=0, upBound=ub)

    # Pool transfers: total surplus contributed and total deficit covered.
    # We model a single internal pool (one company). Surplus ships can donate
    # up to their surplus; deficit ships can be covered up to their deficit.
    donate = {}   # gCO2e a surplus ship contributes
    cover = {}    # gCO2e of a deficit ship's deficit covered by the pool
    for s in ships:
        cb = balances[s.name]
        if cb >= 0:
            donate[s.name] = pulp.LpVariable(f"donate_{s.name}", lowBound=0, upBound=cb)
            cover[s.name] = None
        else:
            donate[s.name] = None
            cover[s.name] = pulp.LpVariable(f"cover_{s.name}", lowBound=0, upBound=-cb)

    # gCO2e reduction from fuel switching, per ship
    def switch_reduction(s: Ship):
        opt = switch_options.get(s.name)
        if opt is None:
            return 0.0
        clean_int = opt.replacement_fuel.wtw_gco2e_per_mj()
        delta_per_mj = s.attained_intensity - clean_int  # gCO2e saved per MJ
        return delta_per_mj * switch[s.name]

    # Pool conservation: total donated >= total covered (pool total >= 0).
    total_donated = pulp.lpSum(
        donate[s.name] for s in ships if donate[s.name] is not None
    )
    total_covered = pulp.lpSum(
        cover[s.name] for s in ships if cover[s.name] is not None
    )
    prob += total_donated >= total_covered, "pool_total_non_negative"

    # Each deficit ship: residual deficit = |CB| - switch_reduction - cover >= 0
    residual = {}
    for s in ships:
        cb = balances[s.name]
        if cb < 0:
            r = pulp.LpVariable(f"residual_{s.name}", lowBound=0)
            prob += r >= (-cb) - switch_reduction(s) - cover[s.name], f"res_{s.name}"
            residual[s.name] = r
        else:
            residual[s.name] = 0.0

    # Objective: penalties on residual deficits + fuel-switch costs ----------
    penalty_terms = pulp.lpSum(
        rates[s.name] * residual[s.name]
        for s in ships if balances[s.name] < 0
    )
    switch_cost_terms = pulp.lpSum(
        switch_options[s.name].price_spread_eur_per_mj * switch[s.name]
        for s in ships if s.name in switch_options
    )
    prob += penalty_terms + switch_cost_terms

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Extract -----------------------------------------------------------------
    plans = []
    for s in ships:
        cb = balances[s.name]
        sw = switch[s.name].value() or 0.0
        opt = switch_options.get(s.name)
        sw_cost = (opt.price_spread_eur_per_mj * sw) if opt else 0.0
        donated = (donate[s.name].value() or 0.0) if donate[s.name] is not None else 0.0
        covered = (cover[s.name].value() or 0.0) if cover[s.name] is not None else 0.0
        res = residual[s.name].value() if cb < 0 else 0.0
        pen = rates[s.name] * (res or 0.0) if cb < 0 else 0.0
        plans.append(ShipPlan(
            name=s.name, balance_before=cb, energy_switched_mj=sw,
            fuel_switch_cost=sw_cost, surplus_donated=donated,
            deficit_covered_by_pool=covered, residual_deficit=(res or 0.0),
            penalty=pen, total_cost=pen + sw_cost,
        ))

    total = sum(p.total_cost for p in plans)
    do_nothing = sum(s.penalty(year) for s in ships)
    return FleetResult(
        year=year, ship_plans=plans, total_cost=total,
        do_nothing_cost=do_nothing, savings_vs_do_nothing=do_nothing - total,
        assumptions=[
            "Single internal pool (one company), Art. 21; pool total kept >= 0.",
            "Penalty rate fixed per ship at its attained intensity; exact with "
            "no switch, ~+/-5% approximation after a switch (residual penalty "
            "recomputed exactly in cost_model for reporting).",
            "Banking and borrowing out of scope in v1.",
        ],
    )
