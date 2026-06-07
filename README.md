# FuelEU Pool Optimiser

Find the lowest-cost way to bring a fleet into FuelEU Maritime compliance.

**[▶ Try it live](https://fueleu-pool-optimiser.streamlit.app)** — edit the fleet table and see the lowest-cost compliance plan.

New here? Start with the plain-language [FAQ](docs/FAQ.md) — it assumes no shipping *or* software background. For the formula-by-formula detail see the [methodology](docs/METHODOLOGY.md), and for the audit of every regulatory number against the law see the [verification](docs/VERIFICATION.md).

FuelEU Maritime (Regulation (EU) 2023/1805, in force since 1 January 2025) puts an annual GHG-intensity limit on the energy ships use on EU-linked voyages. Ships below the limit earn a surplus; ships above it run a deficit and face a penalty of €2,400 per tonne of VLSFO-equivalent energy in deficit. Operators have three ways to deal with a deficit: pay the penalty, switch to cleaner fuel, or pool the deficit against surpluses elsewhere in the fleet.

Plenty of tools calculate a single ship's penalty. This one does something they don't: given a whole fleet, it works out the cheapest *combination* of those three levers across all ships at once — which surpluses should cover which deficits, where a fuel switch is worth its cost, and what penalty (if any) is left to pay. That allocation is a constrained optimisation problem, not a calculation, and the answer is usually not obvious by eye.

## What it does

You give it a fleet: each ship's attained GHG intensity, its in-scope energy, and optionally a cleaner-fuel option it could take. It returns a per-ship plan and the total cost, compared against the do-nothing baseline of everyone paying their own penalty.

The optimiser chooses, for each ship:

- **Pay the penalty** — the Annex IV remedial penalty on any residual deficit.
- **Switch fuel** — replace some energy with a cleaner fuel, at a price spread you supply, when that costs less per gram abated than the alternatives.
- **Pool internally** — net surpluses against deficits within the fleet, which under Article 21 must be a single company's pool with a non-negative total.

## Why pooling, and why single-company

The regulation allows pooling across companies, but the practical guidance from compliance specialists is to start with fleet-internal pooling, because cross-company pools drag in Document-of-Compliance liability and counterparty risk that have to be settled by contract. v1 scopes to the single-company internal pool deliberately: it's the clean mathematical core, and it's the case most operators will actually run first. Cross-company pooling is a natural extension once the contractual layer is modelled.

## Methodology

Everything that affects a number is traceable to the regulation. The constants and formulas live in `regulation.py` with article and annex references inline. Every hard-coded figure has been checked against the official Regulation (EU) 2023/1805 text and the European Commission's own guidance documents; the full audit trail is in [docs/VERIFICATION.md](docs/VERIFICATION.md).

- **GHG-intensity target** (Article 4): the 2020 reference value of 91.16 gCO₂e/MJ reduced by 2% (2025), 6% (2030), 14.5% (2035), 31% (2040), 62% (2045), 80% (2050). The 2025 target works out to 89.34 gCO₂e/MJ, matching published guidance.
- **Compliance balance** (Annex IV): `(target − attained) × energy_MJ`, in gCO₂e. Positive is surplus, negative is deficit.
- **Penalty** (Annex IV, Article 23): the deficit in gCO₂e is converted to non-compliant energy by dividing by the ship's attained intensity, then to tonnes of VLSFO-equivalent by dividing by 41,000 MJ/tonne, then multiplied by €2,400. Repeated consecutive-year deficits carry the Article 23(2) multiplier of `1 + (n−1)/10`. This works out to about €0.058 per MJ of non-compliant energy, which matches the cross-check published by ABS.
- **Fuel GHG intensity** (Annex I and II): well-to-wake intensity is well-to-tank plus tank-to-wake. Tank-to-wake is built from per-gram carbon factors and global warming potentials, not a single flat number. The default fuel table in `fuels.py` transcribes Annex II values (HFO, LFO, MDO, MGO, LNG), cross-checked against several published sources; running them through the model reproduces the regulation's own worked conclusions (HFO, LFO and MGO all sit above the 2025 target; LNG medium-speed comes out marginally compliant).

### Global warming potentials

FuelEU currently uses AR4 values (CO₂ = 1, CH₄ = 25, N₂O = 298) via RED II. A future revision is expected to move to AR5 (CH₄ = 28, N₂O = 265) to align with the revised EU MRV. This tool uses the **current** AR4 values and says so, rather than quietly picking the newer ones.

### The one approximation, stated plainly

The optimiser works in compliance-balance (gCO₂e) space, which keeps pooling and fuel-switching exactly linear. The penalty is the one piece that isn't perfectly linear, because Annex IV divides the deficit by the ship's *attained* intensity — and that intensity changes if the ship switches fuel. The optimiser fixes each ship's penalty rate at its starting attained intensity. That rate is exact for any ship that doesn't switch fuel, and a close approximation (within roughly ±5% across realistic marine intensities of 85–95 gCO₂e/MJ) for one that does. The model recomputes the exact penalty on the chosen plan for reporting. This is a deliberate, documented trade-off to keep the problem solvable as a linear program; it's flagged in the output, not hidden.

## What's out of scope in v1

- **Banking and borrowing.** FuelEU lets you bank a surplus forward and borrow against next year's allowance. Both span multiple reporting periods and need multi-year state to model honestly. v1 is single-period; multi-year is a clean v2.
- **Cross-company pooling**, for the contractual-risk reasons above.
- **OPS (shore-power) penalties** and the RFNBO sub-target, which are separate penalty regimes.
- **Wind-assist and ice-class reward factors**, which adjust attained intensity upstream of this tool — supply an already-adjusted attained intensity if they apply to you.

## This is decision-support, not compliance

It will not make you compliant and it is not a statement of record. The regulation has genuine ambiguities, verifier practice is still settling, and your inputs (fuel prices, intensities) are yours to get right. Use it to compare options and understand the shape of the decision; confirm every figure with your verifier before you act on it.

## Install and run

```bash
git clone https://github.com/rizwanalimondal/fueleu-pool-optimiser.git
cd fueleu-pool-optimiser
pip install -r requirements.txt

# run the tests
PYTHONPATH=src python -m pytest -v

# launch the dashboard
PYTHONPATH=src streamlit run app.py
```

## Entering a fleet

The dashboard opens with an editable table pre-filled with an example fleet, so you see a working result immediately. Edit the cells, add or delete rows, or clear it and type your own. No file needed.

If you'd rather work from a file, the sidebar takes a CSV upload using the same columns, and a template is downloadable from there. The columns are: `name`, `attained_intensity` (gCO₂e/MJ) and `energy_mj` (required); `consecutive_deficit_years` (optional, default 1); and `switch_intensity`, `switch_price_spread_eur_mj`, `switch_max_energy_mj` (optional — fill all three to give a ship a cleaner-fuel option). A sample fleet is in `examples/sample_fleet.csv`. Table input and file upload are parsed by the same loader, so both follow identical rules.

## Using your own fuel data

The Annex II table is there for convenience and every value is editable. For biofuels and RFNBOs, the regulation derives intensity from the fuel's Proof of Sustainability rather than a fixed table, so supply the attained intensity directly. Fossil-fuel tank-to-wake CO₂ factors are not user-overridable under Article 10; the README notes this even though the code will let you change them.

## Project layout

```
src/fueleu_pool/
  regulation.py   targets, compliance balance, penalty (Art. 4, 23, Annex IV)
  fuels.py        Annex I/II fuel intensities with provenance
  cost_model.py   the three levers as a per-ship cost model
  optimiser.py    the MILP fleet optimiser (the novel core)
  io_csv.py       fleet CSV loader
app.py            Streamlit dashboard
tests/            regulation and optimiser test suites
examples/         sample fleet CSV
```

## Licence

MIT.
