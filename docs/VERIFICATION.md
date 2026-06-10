# Verification — every constant, audited against its source

This is the audit trail behind `src/fueleu_pool/`. Each hard-coded number is listed with the primary source it was checked against and its status. Status legend: **Verified** = matches the in-force instrument · **Input** = user-supplied by design (the tool optimises against your figures, it doesn't forecast) · **Out of scope** = deliberately not implemented in v1.

This derivation has additionally been **independently re-derived from scratch** during the build of the companion [Maritime GHG Compliance Navigator](https://github.com/rizwanalimondal/ghg-compliance-navigator) — a second pass through Regulation (EU) 2023/1805 a product later, anchored on the Article 4(2) value. Zero drift was found between the two derivations.

## 1. Regulation core (`regulation.py`)

| Constant | Value | Source | Status |
|---|---|---|---|
| Reference intensity (2020 fleet) | 91.16 gCO₂eq/MJ | Regulation (EU) 2023/1805 | Verified |
| Target steps | 2% '25 · 6% '30 · 14.5% '35 · 31% '40 · 62% '45 · 80% '50 | Art. 4 | Verified |
| 2025 target anchor | 89.34 gCO₂eq/MJ = 91.16 × 0.98 | Art. 4(2) — independent confirmation of baseline × first step | Verified |
| Penalty rate | €2,400 per VLSFO-equivalent tonne | Art. 23(2) & Annex IV | Verified |
| VLSFO energy reference | 41,000 MJ/t | Annex IV | Verified |
| Penalty chain | € = \|CB\| / (Attained × 41,000) × 2,400 (≈ €0.0585/MJ cross-check in tests) | Annex IV; cross-checked against published worked guidance | Verified |
| Consecutive-deficit escalation | +10% per additional consecutive year | Annex IV | Verified |
| Pooling validity | single company; pool total ≥ 0 | Art. 21 | Verified |
| Geographic scope | 100% intra-EEA & at-berth; 50% extra-EEA | Art. 2 | Verified |

## 2. Fuel reference table (`fuels.py`)

| Constant | Source | Status |
|---|---|---|
| WtT / TtW emission factors per fuel (e.g. HFO TtW 78.24, WtW 91.74 gCO₂eq/MJ) and LCVs | Annex II of Reg. (EU) 2023/1805, cross-checked against the European Commission's own guidance document | Verified |
| Candidate-fuel intensities for switches | user-supplied (certified PoS values where available) | Input |
| Fuel price spreads | user-supplied — the tool optimises against your quotes | Input |

## 3. Optimiser (`optimiser.py`, `cost_model.py`)

| Element | Status |
|---|---|
| LP formulation in compliance-balance (gCO₂e) space; constraints mapped to Articles 20–23 | Documented in [METHODOLOGY.md](METHODOLOGY.md) §6 |
| Penalty-rate linearisation (rate fixed at starting attained intensity; exact for non-switching ships; ≈ ±5% across 85–95 gCO₂e/MJ for switching ships; exact penalty recomputed for reporting) | Approximation — stated in code, README, and on the tool's own screen |
| Banking / borrowing (multi-year state) | Out of scope (v1) |
| Cross-company pooling | Out of scope (v1) |
| OPS penalties; RFNBO sub-target | Out of scope (v1) — separate penalty regimes |
| Wind-assist / ice-class reward factors | Out of scope — adjust attained intensity upstream and supply the adjusted figure |

## 4. Tests (17)

| Group | What is pinned |
|---|---|
| Regulation | limit trajectory (all six periods), compliance balance, penalty formula, per-MJ cross-check, consecutive-year multiplier — against hand-worked and published values |
| Optimiser | pools when surplus covers deficit; pays when none exists; switches only when cheaper; partial pooling with penalty on the remainder — against hand-verifiable answers |

## 5. How the audit was performed

1. Primary text first: the Official Journal PDF of Regulation (EU) 2023/1805 and the Commission's guidance.
2. Each constant cross-checked against at least one independent authoritative source; the regulation wins any disagreement.
3. Worked examples reproduced inside the automated test suite, so the verification is executable, not just documented.
4. Anything the tool does not model is declared out of scope on its own screen — never silently approximated (the one stated approximation is in §3 above).
5. Independent re-derivation a product later confirmed every constant (see header).

Found a discrepancy against a primary source? Open an issue quoting the instrument and article — that is precisely the kind of contribution this repo wants.

---

*Maintained by [Navallogic Solutions](https://navallogic.com).*
