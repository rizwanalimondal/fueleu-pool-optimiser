# FAQ — plain-language guide

This page assumes no shipping background *and* no software background. Pick the section that matches you.

---

## The problem, in one paragraph

Since 1 January 2025, every large ship touching European ports lives under FuelEU Maritime: an annual cap on how "dirty" its energy is, per unit, well-to-wake. A ship below the cap earns a surplus; a ship above it runs a deficit and faces a penalty of €2,400 per tonne of VLSFO-equivalent energy in deficit. An operator with a deficit has exactly three moves — pay the penalty, switch some fuel to something cleaner, or *pool* the deficit against a surplus elsewhere in the fleet (the regulation explicitly allows netting across ships). Which combination is cheapest is not obvious by inspection: it depends on every ship's balance, the price spread of cleaner fuel, and how surpluses are allocated. That's a constrained optimisation problem, and every existing tool that solves it is closed, paid SaaS. This tool open-sources the optimiser: feed it your fleet, get the lowest-cost compliance plan, and read exactly how it decided.

---

## I'm a software person with no shipping background

Five concepts and you understand the whole tool:

1. **The regulated quantity is intensity, not volume.** FuelEU caps well-to-wake GHG per megajoule of energy used (gCO₂eq/MJ) against a declining target (91.16 × (1−r), with r stepping 2% in 2025 to 80% in 2050). Burn a lot of clean energy: fine. Burn a little dirty energy: deficit.
2. **The compliance balance turns intensity into a tradeable quantity.** CB = (target − attained) × energy. It's denominated in grams of CO₂eq, it's signed (surplus/deficit), and — crucially — it's *additive across ships*. That additivity is what makes pooling a netting problem.
3. **Pooling is regulated netting.** Under Article 21 a company may pool its ships; the pool is valid if its total balance is non-negative. So one very clean ship can carry several slightly-dirty ones. The optimiser's job is allocating surplus to deficits, alongside the other two levers.
4. **The optimisation is a linear program, on purpose.** Working in compliance-balance (gCO₂e) space keeps everything linear: pooling is summation, fuel-switching reduces a deficit linearly in the energy switched, and the objective minimises penalty-on-residual-deficit plus fuel-switch cost. Built with the open `pulp` library; the constraints map almost one-to-one onto the regulation's articles, which is what keeps it auditable. For a single company's fleet it solves instantly.
5. **There is exactly one approximation, and it's stated, not hidden.** The penalty formula divides the deficit by the ship's *attained intensity* — which changes if the ship switches fuel, making the objective non-linear. The optimiser fixes each ship's penalty *rate* at its starting intensity: exact for any ship that doesn't switch, within about ±5% for one that does (across the realistic 85–95 gCO₂e/MJ range), and the exact penalty is recomputed for reporting. See [METHODOLOGY.md](METHODOLOGY.md) §6.

Start reading at `src/fueleu_pool/regulation.py` (the verified constants), then `optimiser.py` (the novel core).

## I'm a mariner with no software background

You don't need to touch any code. The tool runs in your web browser:

1. Open the live app (fueleu-pool-optimiser.streamlit.app).
2. Enter your fleet directly in the editable table — one row per ship, with each ship's energy used and attained GHG intensity (your DOC holder or MRV verifier can supply both). A CSV upload is available as an alternative; the table is the primary input and your edits persist.
3. If a fuel switch is on the table for any ship, enter the candidate fuel's intensity and the price spread you're actually being quoted — the tool optimises against *your* prices; it does not forecast fuel markets.
4. Press optimise. You get: the cheapest combined plan, the do-nothing penalty cost beside it (the saving is the headline), and a per-ship breakdown — which ships donate surplus, which receive it, which switch fuel, which simply pay.
5. The glossary expander on the page defines every column, and the validation layer warns about implausible entries (intensities outside the realistic range, energy figures that look like unit slips) before they corrupt a result.

What it is and isn't: decision support for planning your compliance strategy — not a substitute for your verifier, and not a compliance guarantee. The plan it proposes is only as good as the balances and prices you feed it.

---

## Common questions

**Why is pooling such a big deal? Isn't it just bookkeeping?**
Because the penalty is steeply asymmetric: a deficit costs €2,400/t VLSFO-equivalent, while a surplus left unused earns nothing. Netting a surplus you already own against a deficit you'd otherwise pay for is often the cheapest compliance there is — but only if allocated correctly across the fleet, which is exactly the part done here by optimisation rather than eyeballing.

**Why only single-company (internal) pooling?**
A deliberate scope decision, not a gap. Cross-company pooling drags in Document-of-Compliance liability and counterparty contractual risk — a legal layer, not a mathematical one. Companies pool internally first in practice; v1 solves that clean core exactly.

**Where do the numbers in the penalty chain come from?**
Regulation (EU) 2023/1805 directly: the 91.16 gCO₂eq/MJ reference, the 2%→80% target steps, the Annex IV penalty (€2,400 per tonne VLSFO-equivalent via the 41,000 MJ/t divisor, ≈ €0.0585 per MJ of non-compliant energy), the +10% consecutive-year multiplier, and the Annex II fuel emission factors cross-checked against the European Commission's own guidance. Every constant's source is tabulated in [VERIFICATION.md](VERIFICATION.md), and the test suite pins the maths to hand-worked and published values.

**What does the tool deliberately NOT do?**
Banking and borrowing across years (multi-year state — a clean v2), cross-company pools, OPS shore-power penalties, the RFNBO sub-target, and wind-assist/ice-class reward factors (those adjust attained intensity upstream — supply an already-adjusted figure if they apply). Where something is out of scope, the tool says so rather than pretending.

**How does this relate to the IMO's new global rules?**
FuelEU is the EU intensity regime; the IMO's draft Net-Zero Framework is the coming global one, with a different baseline and penalty structure — and no pooling. The companion [Maritime GHG Compliance Navigator](https://github.com/rizwanalimondal/ghg-compliance-navigator) scores one fuel picture against both (plus EU ETS and CII) side by side.

**A figure looks wrong / the regulation changed. What do I do?**
Open an issue on the GitHub repository quoting the primary source. Corrections against primary sources are the point of publishing this openly.

**Can I get help applying this to my fleet?**
This tool is maintained by [Navallogic Solutions](https://navallogic.com), an independent maritime advisory focused on vessel-performance analytics and decarbonisation compliance. For fleet pooling strategy, fuel-procurement trade-off studies, or multi-regime exposure modelling beyond what a public tool can responsibly do, reach out via the website.

---

## Command glossary (for non-developers running it locally)

| You type | What it actually does |
|---|---|
| `git clone <url>` | Downloads a complete copy of the project from GitHub to your computer. |
| `python -m venv .venv` | Creates a private sandbox of Python packages just for this project. |
| `source .venv/Scripts/activate` | Steps your terminal into that sandbox (Windows Git Bash). The prompt shows `(.venv)` when you're in. |
| `pip install -e .` | Installs the package itself into the sandbox, in "editable" mode so the code you see is the code that runs. |
| `python -m pytest -v` | Runs the 17 automated checks pinning the maths and the optimiser's decisions to hand-worked values. |
| `streamlit run app.py` | Starts the dashboard in your browser at `localhost:8501`. `Ctrl+C` stops it. |

---

*Maintained by [Navallogic Solutions](https://navallogic.com) · See also: [METHODOLOGY.md](METHODOLOGY.md) for the formulas, [VERIFICATION.md](VERIFICATION.md) for the audit of every constant against its source. Companion tools: [noonkit](https://github.com/rizwanalimondal/noonkit) · [Maritime GHG Compliance Navigator](https://github.com/rizwanalimondal/ghg-compliance-navigator).*
