# FAQ — FuelEU Pool Optimiser in plain language

A plain-English companion to the code. If you're new to this — whether you
know shipping but not software, or software but not shipping — start here. For
the formula-by-formula detail, see [METHODOLOGY.md](METHODOLOGY.md). For the
audit of every regulatory number against the law, see
[VERIFICATION.md](VERIFICATION.md).

---

## What problem does this solve, in one paragraph?

The EU charges ships a penalty if the fuel they burn is too carbon-heavy. A
company that runs several ships can avoid a lot of that penalty by being smart
about it: some ships do better than the limit (a "surplus"), some do worse (a
"deficit"), and the rules let a company cancel one against the other across its
own fleet. There are also other moves — switch a ship to cleaner fuel, or just
pay the fine. Working out the cheapest *combination* of those moves across a
whole fleet is a genuine optimisation problem, and that's what this tool does.

---

## I'm a software person with no shipping background. What's the absolute minimum I need to know?

Five ideas, and you'll understand the whole tool:

1. **GHG intensity.** A number describing how carbon-heavy a ship's energy is —
   grams of CO₂-equivalent per megajoule of energy (gCO₂e/MJ). Lower is
   cleaner. Think of it like a car's emissions-per-km rating, but per unit of
   energy instead of per distance.

2. **The limit.** The EU sets a maximum GHG intensity for each year. For 2025
   it's 89.34 gCO₂e/MJ. It gets stricter over time (down to an 80% cut by
   2050).

3. **Compliance balance.** For each ship: `(limit − actual) × energy used`. If
   a ship is cleaner than the limit, this is positive — a **surplus**. Dirtier
   than the limit — negative, a **deficit**. It's measured in grams of CO₂e.

4. **The penalty.** A ship left in deficit pays a fine, roughly €0.058 for
   every megajoule of "non-compliant" energy. For a big ship over a year that's
   easily six or seven figures of euros.

5. **The three escape routes for a deficit.** Pay the fine; switch some fuel to
   a cleaner one (if you have that option); or **pool** — use another ship's
   surplus to cancel your deficit, as long as both ships belong to the same
   company and the pool's total stays positive.

The tool takes a fleet, works out each ship's balance, then finds the
lowest-cost mix of those three routes. That's it.

---

## I'm a mariner with no software background. How do I just use it?

You don't need to touch any code. Go to the live app, and you'll see a table
already filled with an example fleet. Either edit that table directly — click a
cell, type your number — or upload a CSV with your own ships. The tool shows
you the cheapest plan straight away and updates as you change numbers.

Each column has a little "?" you can hover for an explanation, and there's a
"What each column means" panel above the table that opens with one tap. If you
type something that looks wrong (an impossible emissions figure, a ship that
somehow used almost no fuel), the tool shows an amber warning so you can catch
the typo.

---

## What do I actually type in for each ship?

Three things are required:

- **Ship name** — any label, just make each one different.
- **Attained intensity** — the ship's GHG intensity in gCO₂e/MJ. Your verifier
  gives you this figure, or you compute it from your fuel mix. Marine fuels sit
  around 75–95.
- **Energy (MJ)** — total in-scope energy the ship used over the year. Rough
  rule of thumb: tonnes of VLSFO × 41,000 ≈ MJ.

Three things are optional:

- **Deficit years** — leave at 1 unless the ship was also in deficit in
  earlier years (repeat deficits cost more).
- **Switch intensity / Switch €/MJ / Switch max MJ** — only if a ship could
  move to a cleaner fuel. Fill in all three together (the cleaner fuel's
  intensity, how much more it costs per MJ, and how much energy could switch).
  Leave all three blank if there's no switch option.

---

## What do the results mean?

Three headline numbers:

- **If you do nothing** — what the fleet pays in penalties if every ship just
  pays its own fine, no pooling or switching.
- **Optimised plan** — the lowest total cost the tool could find.
- **Savings** — the difference between the two.

Then a per-ship table shows what the optimiser decided for each vessel: how
much deficit was covered by pooling, how much surplus a ship donated, whether
it switched fuel, and any penalty still left to pay.

---

## How do I know the numbers are right?

Every regulatory figure the tool uses — the limit, the reduction percentages,
the penalty rate, the fuel emission factors — has been checked line-by-line
against the official Regulation (EU) 2023/1805 and the European Commission's
own guidance documents. That audit is written up in
[VERIFICATION.md](VERIFICATION.md), with a table of every number, its source,
and the result.

As a cross-check: feed the tool the standard HFO fuel figures and it computes a
2025 GHG intensity of 91.74 gCO₂e/MJ. An independent published worked example
gets 91.744 for the same case. The match confirms the calculation method, not
just the input numbers.

The tool also has an automated test suite (17 tests) that checks the
regulation maths and the optimiser's decisions against hand-worked answers.
They run with one command (see the glossary below).

---

## Is this an official compliance tool? Can I file its output with a regulator?

No. It's **decision-support** — built to help you compare options and
understand the shape of the decision. It is not a Statement of Compliance and
doesn't replace your verifier. The regulation has genuine grey areas, verifier
practice is still settling, and the fuel prices and intensities you feed in are
your own assumptions. Always confirm figures with your verifier before acting
on them. The app says this on its face, deliberately.

---

## What does it deliberately NOT do (yet)?

To keep the first version correct rather than broad, these are out of scope and
flagged as such:

- **Banking and borrowing** (carrying surplus across years) — needs multi-year
  modelling; a clean future addition.
- **Cross-company pooling** — only single-company internal pools for now,
  because cross-company pools drag in contractual and liability questions.
- **Shore-power (OPS) penalties** and the **RFNBO sub-target** — separate
  penalty regimes.
- **Wind-assist and ice-class reward factors** — these adjust a ship's
  intensity before it reaches this tool; feed in an already-adjusted figure if
  they apply.

---

## Why "pooling optimiser" and not just a "calculator"?

Lots of free tools calculate one ship's penalty. The hard part isn't the
arithmetic for one ship — it's deciding, across a whole fleet, which surpluses
should cover which deficits, where a fuel switch is worth its cost, and what to
leave as a fine. With more than a couple of ships the best answer isn't
obvious by eye. That allocation is a constrained optimisation problem, and
solving it is what makes this different from a calculator.

---

## Command glossary (for non-developers)

If you want to run the project on your own machine, here are the few commands
involved and what each piece means.

- **`cd foldername`** — "change directory," i.e. step into a folder. `cd
  fueleu-pool-optimiser` moves you inside the project.
- **`pip install -r requirements.txt`** — installs the supporting libraries the
  project needs. `pip` is Python's installer; `-r requirements.txt` means
  "install everything listed in this file."
- **`pip install -e .`** — installs *this* project's own code so the app can
  find it. The `.` (a dot) means "the project in this folder"; `-e` means
  "editable," so changes you make take effect without reinstalling.
- **`python -m pytest`** — runs the test suite (the self-checks). `python -m`
  means "run this tool through Python," which is the reliable way to launch it.
  Add **`-v`** ("verbose") to see each test by name.
- **`streamlit run app.py`** — starts the dashboard locally and opens it in your
  browser. Press `Ctrl+C` in the terminal to stop it.
- **`git add .` / `git commit -m "..."` / `git push`** — the three commands that
  save your changes and send them to GitHub. `git` is for saving and sharing
  work; the `-m "..."` is just a short note describing what changed.

A simple way to hold it together: `git` saves and shares your work;
`python` / `pip` / `streamlit` run and test the code; the little flags (`-r`,
`-e`, `-v`, `.`) are tiny instructions that tweak how a command behaves.

---

For the regulation, the formulas, and how each calculation is built up, see
[METHODOLOGY.md](METHODOLOGY.md).
