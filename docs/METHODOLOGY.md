# Methodology

How the FuelEU Pool Optimiser turns a fleet into a lowest-cost compliance plan,
formula by formula. Every regulatory constant used here is verified against the
primary source in [VERIFICATION.md](VERIFICATION.md). For a gentler,
no-jargon introduction, see [FAQ.md](FAQ.md).

This is decision-support, not a compliance statement of record. Confirm all
figures with your verifier before acting on them.

---

## 1. The GHG intensity limit (Article 4)

FuelEU sets a maximum yearly-average GHG intensity for the energy a ship uses,
measured well-to-wake in grams of CO₂-equivalent per megajoule (gCO₂e/MJ). The
limit is a 2020 reference value reduced by a percentage that tightens over
time.

```
limit(year) = 91.16 × (1 − reduction(year))
```

| Period from | Reduction | Limit (gCO₂e/MJ) |
|-------------|-----------|------------------|
| 2025 | 2%    | 89.34 |
| 2030 | 6%    | 85.69 |
| 2035 | 14.5% | 77.94 |
| 2040 | 31%   | 62.90 |
| 2045 | 62%   | 34.64 |
| 2050 | 80%   | 18.23 |

The reference value 91.16 is the 2020 fleet-average intensity from EU MRV data.
A reduction applies from its start year up to the next breakpoint (so 2025–2029
all use 2%).

In code: `regulation.target_ghg_intensity(year)`.

---

## 2. A ship's GHG intensity (Annexes I & II)

A ship's well-to-wake (WtW) intensity is the sum of two parts:

```
WtW intensity = Well-to-Tank (WtT) + Tank-to-Wake (TtW)
```

- **Well-to-Tank** covers emissions from producing and delivering the fuel
  before it reaches the ship. It's a single default figure per fuel from Annex
  II (e.g. 13.5 gCO₂e/MJ for HFO).

- **Tank-to-Wake** covers emissions from burning the fuel on board. It is *not*
  a single number; it's built from the fuel's carbon factors per gram of fuel
  and the global warming potential (GWP) of each gas:

```
TtW (per g fuel) = Cf_CO2 × GWP_CO2 + Cf_CH4 × GWP_CH4 + Cf_N2O × GWP_N2O
TtW (per MJ)     = TtW (per g fuel) ÷ LCV
```

where `LCV` is the fuel's lower calorific value (MJ per gram) and the GWPs are
the AR4 values currently used by FuelEU: **CO₂ = 1, CH₄ = 25, N₂O = 298**.

For gaseous fuels like LNG, a fraction of fuel escapes unburned ("methane
slip"); that slipped mass is counted as methane (× GWP_CH4) and added in.

The built-in fuel table (HFO, LFO, MDO, MGO, LNG) uses the Annex II default
values, every one verified against the EU Commission's guidance reproduction of
Annex II. Each value is editable, and for biofuels or RFNBOs — whose intensity
comes from a Proof of Sustainability rather than a fixed table — you supply the
attained intensity directly.

In code: `fuels.Fuel.wtw_gco2e_per_mj()`.

**Worked check.** HFO has LCV 0.0405, WtT 13.5, Cf_CO2 3.114, Cf_CH4 0.00005,
Cf_N2O 0.00018. The TtW works out to about 78.24 gCO₂e/MJ, so WtW ≈ 13.5 +
78.24 = 91.74. That matches an independent published worked example to three
decimals, and correctly sits *above* the 2025 limit of 89.34 — i.e. a ship on
pure HFO is in deficit, exactly as the Commission's own examples state.

---

## 3. Compliance balance (Annex IV Part A)

For each ship over the reporting year:

```
compliance balance = (limit − attained intensity) × energy_used_MJ
```

measured in grams of CO₂e.

- Cleaner than the limit → positive → **surplus**.
- Dirtier than the limit → negative → **deficit**.

In code: `regulation.compliance_balance(...)`.

---

## 4. The penalty (Annex IV Part B, Article 23)

A ship left in deficit pays a remedial penalty. The regulation's formula:

```
penalty (EUR) = |deficit in gCO₂e| ÷ (attained intensity × 41 000) × 2 400
```

Reading the chain:

1. Take the deficit in gCO₂e.
2. Divide by the ship's attained intensity → the "non-compliant energy" in MJ.
3. Divide by 41 000 (the energy in MJ of one tonne of VLSFO) → tonnes of
   VLSFO-equivalent.
4. Multiply by €2 400 per tonne.

This works out to about €0.058 per MJ of non-compliant energy — a cross-check
published by ABS, which the tool reproduces.

**Repeat deficits.** If a ship is in deficit for consecutive years, Article
23(2) raises the penalty by a multiplier:

```
multiplier = 1 + (n − 1) / 10
```

where `n` is the number of consecutive deficit years (year 1 → ×1.0, year 2 →
×1.1, and so on). The "Deficit years" column drives this.

In code: `regulation.penalty_eur(...)` and
`regulation.consecutive_deficit_multiplier(...)`.

---

## 5. The three compliance levers

For a deficit, an operator has three responses, and the tool weighs all three:

1. **Pay the penalty** — the do-nothing cost from section 4.

2. **Switch fuel** — move some energy to a cleaner fuel. This reduces the
   deficit by a computable amount per MJ switched
   (`incumbent intensity − cleaner intensity`), at a cost you supply (the price
   spread in €/MJ), up to a maximum you set.

3. **Pool internally** — net surpluses against deficits across the company's
   own fleet. Under Article 21 a pool must belong to one company and its total
   compliance balance must stay non-negative.

In code: `cost_model.py` defines the levers; `optimiser.py` chooses among them.

---

## 6. The optimisation (the novel core)

The tool finds the lowest-cost combination of those three levers across the
whole fleet. It is set up as a linear program, solved with the open `pulp`
library, working in compliance-balance (gCO₂e) space — which keeps pooling and
fuel-switching exactly linear:

- **Pooling** is netting: the fleet is valid if total donated surplus ≥ total
  covered deficit, with no surplus ship pushed below zero.
- **Fuel switching** reduces a ship's deficit linearly in the energy switched.
- **The objective** minimises: sum of (penalty on each ship's residual deficit)
  + (cost of any fuel switched).

### The one approximation, stated plainly

The penalty (section 4) divides the deficit by the ship's *attained* intensity,
and that intensity changes if the ship switches fuel — which would make the
objective non-linear. To keep the problem a clean, auditable linear program,
the optimiser fixes each ship's penalty *rate* at its starting attained
intensity. That rate is exact for any ship that doesn't switch fuel, and a
close approximation (within roughly ±5% across the realistic marine intensity
range of 85–95 gCO₂e/MJ) for one that does. The per-ship penalty is recomputed
exactly for reporting. This trade-off is deliberate and is surfaced in the
tool's own "Methodology and assumptions" panel, not hidden.

In code: `optimiser.optimise_fleet(...)`.

---

## 7. What's out of scope (v1)

Kept out deliberately so the first version is correct rather than broad:

- **Banking and borrowing** — carrying surplus across years; needs multi-year
  state.
- **Cross-company pooling** — only single-company internal pools, to avoid the
  contractual/liability layer.
- **OPS (shore-power) penalties** and the **RFNBO sub-target** — separate
  penalty regimes.
- **Wind-assist and ice-class reward factors** — these adjust attained
  intensity upstream; supply an already-adjusted figure if they apply.

---

## 8. Testing

The repository ships with an automated test suite (run `python -m pytest -v`):

- **Regulation tests** check the limit trajectory, compliance balance, penalty
  formula, the per-MJ cross-check, and the consecutive-year multiplier against
  hand-worked and published values.
- **Optimiser tests** check that the tool pools when a surplus can cover a
  deficit, falls back to paying when no surplus exists, switches fuel only when
  it's cheaper than the alternatives, and handles partial pooling with a
  penalty on the remainder — each against a hand-verifiable answer.

---

For every regulatory constant and its primary source, see
[VERIFICATION.md](VERIFICATION.md). For the plain-language overview, see
[FAQ.md](FAQ.md).
