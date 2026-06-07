# Primary-source verification

Every hard-coded regulatory number in this tool has been checked against the
official text of Regulation (EU) 2023/1805 and the European Commission's own
guidance and methodology documents. This page records what was checked, the
source, and the result, so the figures are auditable rather than taken on
trust.

Primary sources used:
- Regulation (EU) 2023/1805, Official Journal L 234, 22.9.2023 (EUR-Lex,
  CELEX 32023R1805) — Articles 4 and 23, Annexes I, II and IV.
- European Commission, *FuelEU Maritime guidance document for shipping
  companies* (DG MOVE), reproducing the Annex II default-factor table.
- European Commission Q&A on Regulation (EU) 2023/1805 (DG MOVE).
- European Sustainable Shipping Forum (ESSF) SAPS WS1 calculation
  methodologies working draft.

## Article 4 — reference value and reduction trajectory

| Item | In code | Primary source | Result |
|------|---------|----------------|--------|
| Reference value | 91.16 gCO2e/MJ | Art. 4(2): "reducing the reference value of 91,16 grams of CO2 equivalent per MJ" | Confirmed |
| 2025 reduction | 2% | Art. 4(2) / EC Q&A | Confirmed |
| 2030 reduction | 6% | Art. 4(2) | Confirmed |
| 2035 reduction | 14.5% | Art. 4(2) | Confirmed |
| 2040 reduction | 31% | Art. 4(2) | Confirmed |
| 2045 reduction | 62% | Art. 4(2) | Confirmed |
| 2050 reduction | 80% | Art. 4(2) | Confirmed |
| 2025 target (derived) | 89.34 gCO2e/MJ | EC Q&A states 89.34 | Confirmed |

## Annex IV — penalty

| Item | In code | Primary source | Result |
|------|---------|----------------|--------|
| Penalty rate | EUR 2400 / t VLSFO | Annex IV B: Penalty = CB x 2400 / (GHGIE_actual x 41000) | Confirmed |
| VLSFO energy constant | 41 000 MJ/tonne | Annex IV; "41 000: energy equivalent of 1 t VLSFO" | Confirmed |
| Penalty formula | deficit / (intensity x 41000) x 2400 | Annex IV B (as above) | Confirmed |
| Per-MJ cross-check | ~EUR 0.058 / MJ | ABS published figure | Confirmed |
| Consecutive-deficit multiplier | 1 + (n-1)/10 | Art. 23(2) verbatim | Confirmed |

## Annex II — fuel default factors

All values below are transcribed from the European Commission's guidance
document reproduction of Annex II (LCV in MJ/g; WtT in gCO2e/MJ; Cf in g/g
fuel; Cslip in %). Every value in `fuels.py` matches.

| Fuel | LCV | WtT | Cf_CO2 | Cf_CH4 | Cf_N2O | Cslip | Result |
|------|-----|-----|--------|--------|--------|-------|--------|
| HFO | 0.0405 | 13.5 | 3.114 | 0.00005 | 0.00018 | 0.0% | Confirmed |
| LFO | 0.0410 | 13.2 | 3.151 | 0.00005 | 0.00018 | 0.0% | Confirmed |
| MDO | 0.0427 | 14.4 | 3.206 | 0.00005 | 0.00018 | 0.0% | Confirmed |
| MGO | 0.0427 | 14.4 | 3.206 | 0.00005 | 0.00018 | 0.0% | Confirmed |
| LNG Otto (medium-speed) | 0.0491 | 18.5 | 2.750 | 0.00000 | 0.00011 | 3.1% | Confirmed |

## Global warming potentials (AR4)

| Gas | In code | Source | Result |
|-----|---------|--------|--------|
| CO2 | 1 | RED II / FuelEU current basis (AR4) | Confirmed |
| CH4 | 25 | RED II / FuelEU current basis (AR4) | Confirmed |
| N2O | 298 | RED II / FuelEU current basis (AR4) | Confirmed |

Note: FuelEU currently uses AR4 GWP values. A future revision is expected to
move to AR5 (CH4 = 28, N2O = 265) to align with the revised EU MRV. This tool
uses the current AR4 values and flags this in `fuels.py`.

## End-to-end cross-check

Running the verified Annex II HFO factors through the tool's GHG-intensity
calculation yields a 2025 well-to-wake intensity of 91.74 gCO2e/MJ. An
independent published worked example (BetterSea) computes 91.744 gCO2e/MJ for
the same case. The match confirms not only the input constants but the
tank-to-wake calculation method (combustion factors x GWP, divided by LCV).

The European Commission Q&A separately states that HFO, LFO and MDO/MGO all
exceed the 2025 target of 89.34, while LNG medium-speed is marginally
compliant — the tool reproduces both conclusions.

## Scope note

This verification covers the constants the tool uses. It does not extend the
tool's scope: banking, borrowing, cross-company pooling, OPS penalties, the
RFNBO sub-target, and wind/ice reward factors remain out of scope and are
documented as such in the README. The tool is decision-support, not a
compliance statement of record.
