"""Load a fleet from CSV into Ship objects and optional fuel-switch options.

Expected columns (header row required):
  name                       - vessel name (string, unique)
  attained_intensity         - WtW GHG intensity, gCO2e/MJ (float)
  energy_mj                  - in-scope energy used on board, MJ (float)
  consecutive_deficit_years  - optional, default 1 (int)
  switch_intensity           - optional, WtW intensity of the clean fuel option
  switch_price_spread_eur_mj - optional, clean-minus-incumbent EUR per MJ
  switch_max_energy_mj       - optional, upper bound on energy that can switch

A ship gets a fuel-switch lever only if all three switch_* columns are present
and non-empty for that row. Otherwise it has penalty + pooling only.

Two ways to populate `attained_intensity`:
  1. Directly (BYO), e.g. from your verifier's figure or Proof of Sustainability.
  2. Compute it from a fuel mix using fuels.py before building the CSV.
"""

from __future__ import annotations

import csv
from io import StringIO

from .cost_model import Ship, FuelSwitchOption
from .fuels import Fuel


REQUIRED_COLUMNS = {"name", "attained_intensity", "energy_mj"}
SWITCH_COLUMNS = {
    "switch_intensity",
    "switch_price_spread_eur_mj",
    "switch_max_energy_mj",
}


def _nonempty(row: dict, key: str) -> bool:
    return key in row and row[key] is not None and str(row[key]).strip() != ""


def load_fleet(csv_text: str) -> tuple[list[Ship], dict[str, FuelSwitchOption]]:
    """Parse CSV text into (ships, switch_options)."""
    reader = csv.DictReader(StringIO(csv_text))
    if reader.fieldnames is None:
        raise ValueError("CSV has no header row.")
    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise ValueError(f"CSV missing required columns: {sorted(missing)}")

    ships: list[Ship] = []
    switch_options: dict[str, FuelSwitchOption] = {}
    seen = set()

    for i, row in enumerate(reader, start=2):  # row 2 = first data row
        name = (row.get("name") or "").strip()
        if not name:
            raise ValueError(f"Row {i}: empty 'name'.")
        if name in seen:
            raise ValueError(f"Row {i}: duplicate ship name '{name}'.")
        seen.add(name)

        try:
            intensity = float(row["attained_intensity"])
            energy = float(row["energy_mj"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Row {i} ('{name}'): attained_intensity and energy_mj must be numeric."
            )
        if energy < 0:
            raise ValueError(f"Row {i} ('{name}'): energy_mj must be non-negative.")

        years = 1
        if _nonempty(row, "consecutive_deficit_years"):
            years = int(float(row["consecutive_deficit_years"]))
            if years < 1:
                raise ValueError(
                    f"Row {i} ('{name}'): consecutive_deficit_years must be >= 1."
                )

        ships.append(Ship(
            name=name, attained_intensity=intensity,
            energy_mj=energy, consecutive_deficit_years=years,
        ))

        # Fuel-switch lever: only if all three switch columns are populated.
        if all(_nonempty(row, c) for c in SWITCH_COLUMNS):
            sw_int = float(row["switch_intensity"])
            sw_spread = float(row["switch_price_spread_eur_mj"])
            sw_max = float(row["switch_max_energy_mj"])
            if sw_max < 0:
                raise ValueError(
                    f"Row {i} ('{name}'): switch_max_energy_mj must be non-negative."
                )
            clean = Fuel(
                name=f"{name}_clean_option", fuel_class="Biofuel",
                lcv_mj_per_g=0.04, wtt_gco2e_per_mj=0.0,
                cf_co2=0.0, cf_ch4=0.0, cf_n2o=0.0,
                attained_intensity_override=sw_int,
                source="user-supplied switch option",
            )
            switch_options[name] = FuelSwitchOption(
                replacement_fuel=clean,
                price_spread_eur_per_mj=sw_spread,
                max_energy_mj=sw_max,
            )

    if not ships:
        raise ValueError("CSV contained a header but no ship rows.")
    return ships, switch_options
