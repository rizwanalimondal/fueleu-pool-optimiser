"""Compliance cost model: the three levers an operator can pull.

For a single ship in deficit, FuelEU offers three responses (banking and
borrowing are out of scope for v1 and flagged in the README):

  1. PAY THE PENALTY   - do nothing, pay the Annex IV remedial penalty.
  2. BUY COMPLIANT FUEL - swap some non-compliant energy for a cleaner fuel,
                          changing the attained intensity and thus the balance.
  3. POOL INTERNALLY    - net this ship's deficit against fleet surpluses.

This module computes the cost of levers (1) and (2) per ship and exposes the
per-ship compliance balance. Pooling (3) is a fleet-level allocation handled
by the optimiser, because whether a deficit can be covered depends on the
whole fleet, not one ship.

All money is EUR. All energy is MJ. Intensities are gCO2e/MJ.
Decision-support only; not a compliance statement of record.
"""

from __future__ import annotations

from dataclasses import dataclass

from .regulation import compliance_balance, penalty_eur
from .fuels import Fuel


@dataclass
class Ship:
    """A vessel's in-scope position for one reporting period.

    `attained_intensity` is the ship's actual WtW GHG intensity (gCO2e/MJ),
    either computed from its fuel mix via fuels.py or supplied directly.
    `energy_mj` is total in-scope energy used on board.
    `consecutive_deficit_years` drives the Art. 23(2) penalty multiplier.
    """

    name: str
    attained_intensity: float
    energy_mj: float
    consecutive_deficit_years: int = 1

    def balance(self, year: int) -> float:
        """Compliance balance in gCO2e (positive surplus / negative deficit)."""
        return compliance_balance(self.attained_intensity, self.energy_mj, year)

    def penalty(self, year: int) -> float:
        """Cost of lever 1: pay the Annex IV penalty for any deficit."""
        return penalty_eur(
            self.balance(year),
            attained_ghg_intensity=self.attained_intensity,
            consecutive_years=self.consecutive_deficit_years,
        )


@dataclass
class FuelSwitchOption:
    """Lever 2: replace a quantity of energy with a cleaner fuel.

    Models swapping `energy_mj_switched` of the ship's energy from its current
    blend to `replacement_fuel`. Cost is the price spread (EUR per MJ) times
    energy switched — the extra cost of the cleaner fuel over the incumbent.

    The intensity effect is computed by the optimiser/model using the energy-
    weighted average of switched vs unswitched energy, so it stays exact.
    """

    replacement_fuel: Fuel
    price_spread_eur_per_mj: float  # (clean price - incumbent price), per MJ
    max_energy_mj: float            # upper bound on how much can be switched


def blended_intensity(
    base_intensity: float,
    base_energy_mj: float,
    switch_intensity: float,
    switch_energy_mj: float,
) -> float:
    """Energy-weighted WtW intensity after switching part of the energy.

    Switching `switch_energy_mj` of the total to a fuel of `switch_intensity`,
    leaving (base_energy - switch_energy) at `base_intensity`.
    """
    if switch_energy_mj < 0 or switch_energy_mj > base_energy_mj:
        raise ValueError("switched energy must be within [0, total energy]")
    remaining = base_energy_mj - switch_energy_mj
    total = base_energy_mj
    if total <= 0:
        raise ValueError("total energy must be positive")
    return (remaining * base_intensity + switch_energy_mj * switch_intensity) / total


def fuel_switch_cost(option: FuelSwitchOption, energy_mj_switched: float) -> float:
    """Cost of lever 2 for a given quantity switched (EUR)."""
    if energy_mj_switched < 0:
        raise ValueError("energy switched must be non-negative")
    return option.price_spread_eur_per_mj * energy_mj_switched
