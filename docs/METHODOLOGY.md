# Methodology — every formula, worked through

This document walks through exactly what the tool computes — the regulation chain first, then the optimisation that sits on top of it. Nothing here is claimed that the code does not produce; the 17-test suite pins the regulation maths to hand-worked and published values and the optimiser's decisions to hand-verifiable cases.

Notation: energy in MJ; intensities in gCO₂eq/MJ; 1 tonne = 10⁶ g.

---

## 1. The target trajectory

FuelEU caps the well-to-wake GHG intensity of the energy a ship uses, against the 2020 fleet-average reference of **91.16 gCO₂eq/MJ**:

```
Target(year) = 91.16 × (1 − r)
```

with *r* stepping at five-year boundaries — 2% (2025–29), 6% (2030–34), 14.5% (2035–39), 31% (2040–44), 62% (2045–49), 80% (2050). The 2025 target, 89.3368 ≈ 89.34, is the Article 4(2) figure — a useful independent anchor, since 91.16 × 0.98 reproducing the published value confirms the baseline and the first step simultaneously. The full six-period table is hard-coded in `regulation.py` with sources, and the trajectory test checks every period.

## 2. A ship's attained intensity

Attained intensity is the energy-weighted well-to-wake intensity of everything the ship used in scope. Per fuel, the well-to-wake figure is Well-to-Tank (upstream) plus Tank-to-Wake (combustion, with CH₄ and N₂O folded in at their global-warming potentials). The Annex II defaults in `fuels.py` were cross-checked against the European Commission's own guidance, using the AR4 global-warming potentials FuelEU currently applies (**CO₂ = 1, CH₄ = 25, N₂O = 298**); for gaseous fuels, unburned methane slip is counted at GWP_CH₄ and added in.

**Worked check.** HFO has LCV 0.0405 MJ/g, WtT 13.5, Cf_CO₂ 3.114, Cf_CH₄ 0.00005, Cf_N₂O 0.00018. The Tank-to-Wake side works out to about **78.24 gCO₂e/MJ**, so Well-to-Wake ≈ 13.5 + 78.24 = **91.74** — matching an independent published worked example to three decimals, and sitting correctly *above* the 2025 limit of 89.34. A ship on pure HFO is in deficit from day one; the regulation is *designed* to bite immediately and tighten. In code: `fuels.Fuel.wtw_gco2e_per_mj()`. For biofuels and RFNBOs — whose intensity comes from a Proof of Sustainability rather than a fixed table — you supply the attained intensity directly.

The dashboard accepts attained intensity directly (from your verifier) or computes it from a fuel breakdown; reward factors such as wind-assist adjust intensity upstream of this tool — supply an adjusted figure if they apply.

## 3. The compliance balance — intensity made additive

```
CB [gCO₂eq] = (Target − Attained) × Energy_in_scope
```

Positive = surplus, negative = deficit. Two properties make everything downstream work. It scales with energy, so a big ship slightly over the line can out-deficit a small ship far over it. And it is *additive across ships* — the property the regulation's own pooling article relies on, and the reason pooling reduces to netting.

## 4. The penalty chain

The penalty is expressed per tonne of VLSFO-equivalent energy. Annex IV's chain, for a deficit:

```
deficit [gCO₂eq] → non-compliant energy = |CB| / Attained [MJ]
                → VLSFO-equivalent tonnes = energy / 41,000
                → Penalty [€] = tonnes × 2,400
```

i.e. `Penalty = |CB| / (Attained × 41,000) × 2,400`, which works out near **€0.0585 per MJ** of non-compliant energy — the per-MJ cross-check in the test suite. Consecutive deficit years escalate the penalty by +10% per additional year. Both the chain and the multiplier are tested against published worked guidance.

## 5. The three levers

For any ship in deficit an operator has exactly three responses; the tool weighs them *together* rather than in isolation:

1. **Pay the penalty** — the do-nothing baseline, via section 4.
2. **Switch fuel** — replace some energy with a cleaner candidate. Each MJ switched reduces the deficit by (incumbent intensity − candidate intensity) gCO₂e, linearly; the cost is the user-supplied price spread per unit. The tool optimises against your quoted prices — it does not forecast fuel markets.
3. **Pool internally** — net surpluses against deficits across the company's own fleet. Under Article 21 a pool must belong to one company and its total compliance balance must stay non-negative; the tool additionally never pushes a surplus ship below zero (it only allocates surplus that exists).

In code: `cost_model.py` defines the levers; `optimiser.py` chooses among them.

## 6. The optimisation (the novel core)

The tool finds the lowest-cost combination of those three levers across the whole fleet, set up as a linear program (solved with the open `pulp` library) **in compliance-balance (gCO₂e) space** — the choice that keeps the whole problem linear:

- **Pooling** is netting: the fleet is valid if total donated surplus ≥ total covered deficit, with no surplus ship pushed below zero.
- **Fuel switching** reduces a ship's deficit linearly in the energy switched.
- **The objective** minimises: Σ (penalty on each ship's residual deficit) + Σ (cost of fuel switched).

Why an LP and not a heuristic: the constraints map almost one-to-one onto the regulation's articles, so the model itself is auditable — anyone can read a constraint and check it against the text — and for a single company's fleet it solves instantly.

### The one approximation, stated plainly

The penalty (section 4) divides the deficit by the ship's *attained* intensity — and that intensity changes if the ship switches fuel, which would make the objective non-linear (one decision variable divided by another). To keep the problem a clean, auditable linear program, the optimiser fixes each ship's penalty *rate* at its starting attained intensity. That rate is **exact** for any ship that doesn't switch fuel, and a close approximation — within roughly ±5% across the realistic marine intensity range of 85–95 gCO₂e/MJ — for one that does. The per-ship penalty is then recomputed **exactly** for reporting, so the displayed costs are true even where the optimiser's internal rate was approximate. This trade-off is deliberate and is surfaced in the tool's own "Methodology and assumptions" panel, not hidden.

In code: `optimiser.optimise_fleet(...)`.

## 7. What's out of scope (v1)

Kept out deliberately so the first version is correct rather than broad:

- **Banking and borrowing** — carrying surplus across years needs multi-year state; a clean v2, not a half-built v1 feature.
- **Cross-company pooling** — only single-company internal pools, avoiding the Document-of-Compliance liability and counterparty layer.
- **OPS (shore-power) penalties** and the **RFNBO sub-target** — separate penalty regimes.
- **Wind-assist and ice-class reward factors** — these adjust attained intensity upstream; supply an already-adjusted figure if they apply.

## 8. Testing

Run `python -m pytest -v`:

- **Regulation tests** check the limit trajectory (all six periods), the compliance balance, the penalty formula, the per-MJ cross-check, and the consecutive-year multiplier against hand-worked and published values.
- **Optimiser tests** check the *decisions*: that the tool pools when a surplus can cover a deficit, falls back to paying when no surplus exists, switches fuel only when it's cheaper than the alternatives, and handles partial pooling with a penalty on the remainder — each against a hand-verifiable answer.

---

For every regulatory constant and its primary source, see [VERIFICATION.md](VERIFICATION.md). For the plain-language overview, see [FAQ.md](FAQ.md).

*Maintained by [Navallogic Solutions](https://navallogic.com) — independent maritime advisory for vessel-performance analytics and decarbonisation compliance. Companion tools: [noonkit](https://github.com/rizwanalimondal/noonkit) · [Maritime GHG Compliance Navigator](https://github.com/rizwanalimondal/ghg-compliance-navigator).*
