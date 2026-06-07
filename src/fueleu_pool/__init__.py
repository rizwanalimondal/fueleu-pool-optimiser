"""FuelEU Pool Optimiser.

Lowest-cost FuelEU Maritime fleet compliance: pooling, fuel-switch, and
penalty optimisation. Decision-support only; not a compliance statement of
record.
"""

from .regulation import (
    target_ghg_intensity,
    compliance_balance,
    penalty_eur,
)
from .cost_model import Ship, FuelSwitchOption
from .optimiser import optimise_fleet, FleetResult, ShipPlan
from .io_csv import load_fleet

__version__ = "0.1.0"

__all__ = [
    "target_ghg_intensity",
    "compliance_balance",
    "penalty_eur",
    "Ship",
    "FuelSwitchOption",
    "optimise_fleet",
    "FleetResult",
    "ShipPlan",
    "load_fleet",
]
