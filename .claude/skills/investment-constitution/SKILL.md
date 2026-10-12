---
name: investment-constitution
description: Canonical investment-research constitution for this repository. Defines the four immutable investment layers, the layer-fit scale, the epistemic tag vocabulary, claim-ID citation syntax, the evidence hierarchy, and the Four-Layer Evidence Crosswalk format. Load before any equity research, specialist report, CIO synthesis, or scoring work in this project.
when_to_use: Any task that researches a company, writes or reviews a specialist or CIO report, classifies an investment layer, or assigns scores.
---

# Investment Research Constitution

This document is the **single canonical source** for the definitions below. `MASTER_RESEARCH_FRAMEWORK.md` (what to investigate), `PROJECT_INSTRUCTIONS.md` (global rules) and `methodology/` (scoring, evidence, lenses, report contracts) build on it and must not contradict it. Validation scripts in `scripts/` parse the marked blocks in this file. **Do not edit the text between the `CANONICAL_*` / `EPISTEMIC_TAGS` markers without also running `python3 -m unittest discover tests`.**

The purpose of this research system is to improve the quality of investment decisions and long-term, risk-adjusted, **per-share** compounding while explicitly accounting for permanent capital loss. Impressive-looking research that does not improve a decision is a failure.

---

## 1. The four investment layers (immutable)

<!-- CANONICAL_LAYERS:BEGIN -->
1. Layer 1 — Bedrock Compounder
2. Layer 2 — High-Growth Business
3. Layer 3 — Cyclical / Event-Driven Opportunity
4. Layer 4 — Venture-Style / Optionality Bet
<!-- CANONICAL_LAYERS:END -->

These names and meanings are identical in every agent, report, scorecard, template and synthesis. No agent may rename, redefine, merge, split, re-number or replace them. "Deep value", "special situation", "turnaround", "valuation trap", "commodity", "overvalued growth" and similar terms are **not layers**. Where relevant they are characteristics *within* a layer (deep value and special situations sit inside Layer 3) or price judgments (which never define a layer).

### Layer 1 — Bedrock Compounder
**Core question:** Can the business sustainably grow intrinsic value per share over a long period by reinvesting capital at attractive incremental returns while defending its competitive position?
**What decides it:** returns on capital above the cost of capital measured *through a cycle* (not at a peak); incremental returns on new capital; a reinvestment runway large relative to current capital; an identifiable mechanism that protects those returns; per-share (not aggregate) value creation after dilution and acquisitions; resilience in bad years.
**Not sufficient on its own:** a rising share price, rising EPS, a famous brand, market leadership, or high historical ROCE.

### Layer 2 — High-Growth Business
**Core question:** How large can this business realistically become, how long can it grow, and can that growth eventually translate into attractive per-share economics?
**What decides it:** growth well above nominal GDP that comes from adoption or share gains rather than only market inflation or acquisitions; evidence of customer retention and repeat use; unit and incremental economics that improve with scale; a credible path to sustained free cash flow; the capital and dilution needed to get there; competitive response and saturation.
**Not sufficient on its own:** a TAM slide, revenue growth, or management ambition. **Not disqualifying on its own:** a high trailing multiple or low current profit.

### Layer 3 — Cyclical / Event-Driven Opportunity
**Core question:** Is the market mispricing normalized economics, a cyclical inflection, an identifiable catalyst, a restructuring, or a change in the market's assessment of assets and earnings?
**What decides it:** a measurable gap between current run-rate and normalized (mid-cycle) earnings or asset value; current cycle position; balance-sheet survival at the trough; for events, a specific value-realization mechanism, its timing and probability, and whether it is already priced; the downside if the catalyst fails; temporary mean reversion distinguished from structural decline.
**Includes:** cyclicals, turnarounds, restructurings, demergers and spin-offs, asset monetization, holding-company and SOTP discounts, deep value, and legal or regulatory resolutions.
**Not sufficient on its own:** a low P/E or P/B (possible value trap), or a catalyst without a value-realization mechanism.

### Layer 4 — Venture-Style / Optionality Bet
**Core question:** Does the business contain credible asymmetric potential that could produce substantial per-share value if a set of uncertain milestones is achieved, and is the entry price appropriate given the possibility of failure?
**What decides it:** evidence of product-market fit and adoption; retention and contribution economics; the reachable (not imaginable) market; the milestones that would prove the option real; cash runway, refinancing needs and dilution; a probability-weighted distribution across success, partial success, stagnation and failure, including near-total loss where appropriate; separating the existing business's value from the option's value.
**Not the same as:** "expensive growth stock" or "small company". Layer 4 describes the *shape of the outcome distribution*, not the price or the size.

### Analyze before classifying
- Every company is examined through all four lenses before any primary layer is chosen. Being profitable, unprofitable, cheap, expensive, cyclical, fast-growing, small or SME-listed **never** determines the layer by itself.
- Permitted outcomes include: a good business that is a poor investment at today's price; a mediocre business that is an attractive Layer 3 opportunity; a maturing grower; a mature business with genuine Layer 4 optionality in one product or subsidiary; a hybrid; and **none of the four is compelling**.
- SME listing triggers **enhanced scrutiny** (governance, accounting, dilution, liquidity and exit, promoter behavior, concentration, permanent-loss risk). It does **not** make Layer 4 the default.

### Layer-fit scale (common to all four layers)
Layer fit measures **how well the opportunity matches the archetype's value-creation mechanism**. It **excludes price**. A layer-fit score must never become a proxy for whether the stock is cheap.

<!-- CANONICAL_FIT_SCALE:BEGIN -->
- 81–100 Archetypal fit: the mechanism is evidenced in primary data over a relevant period, corroborated, durable, with few credible counter-indicators.
- 61–80 Strong fit: the mechanism is evidenced; the main uncertainties are identifiable and bounded.
- 41–60 Plausible fit: the mechanism is present but unproven or materially constrained; a credible case exists.
- 21–40 Weak fit: some features are present but the core question is answered "no" on current evidence.
- 0–20 No fit: the mechanism is absent or contradicted by evidence.
<!-- CANONICAL_FIT_SCALE:END -->

A layer scoring 41 or higher is **materially plausible** and requires its own current-price assessment. Choosing the primary layer is a judgment about **which layer's core question most determines future per-share value and the investment outcome**. The highest fit score does not decide it automatically. If two layers are within 10 points and both 61 or above, the company is a hybrid, and the report explains how the two core questions interact. If every layer is 40 or below, the report says no archetype is compelling.

---

## 2. Epistemic tags and claim-level citation

Every material claim carries exactly one tag.

<!-- EPISTEMIC_TAGS:BEGIN -->
- FACT — directly supported by a retrieved source at a known location.
- MANAGEMENT STATEMENT — what management said or committed to; proof that it was said, not that it is true.
- CALCULATION — reproducible from identified inputs with a stated formula.
- ESTIMATE — a forward-looking or uncertain quantity; its basis must be stated.
- INFERENCE — an interpretation that follows from cited evidence.
- JUDGMENT — an investment conclusion or subjective assessment.
<!-- EPISTEMIC_TAGS:END -->

**Syntax.** Tags carry claim IDs from the author's evidence ledger: `[FACT: FIN-C012]`, `[CALCULATION: FIN-C020; FIN-C003]`, `[MANAGEMENT STATEMENT: CON-C044]`, `[ESTIMATE: VAL-C010]`. `[INFERENCE]` and `[JUDGMENT]` may stand alone, but should cite the claims they rest on when possible (`[INFERENCE: IND-C007; FIN-C031]`).
- FACT, MANAGEMENT STATEMENT, CALCULATION and ESTIMATE **must** carry at least one claim ID that exists in a ledger. The validator rejects reports that break this rule.
- Put the citation **next to the claim**. A list of sources at the end is not a substitute.
- A figure you remember but did not retrieve in this run is **not** a FACT. Retrieve it, or downgrade it to ESTIMATE and say it is unverified.
- Never invent a URL, page, note number, filing date, transcript timestamp, figure or quotation. If the exact location is unknown, record `NOT_LOCATED` in the ledger and lower the confidence.

**Claim-ID prefixes:** FIN (financials), FIL (filings), MGT (management), IND (industry), MOAT (moat), CON (concalls), VAL (valuation), BEAR (bear-case), SPS (special-situations), CIO (CIO). Format: `PREFIX-C###`.

The ledger schema and numerical controls are in `methodology/EVIDENCE_STANDARDS.md`.

---

## 3. Evidence hierarchy

Prefer, adapting to the claim:
1. Audited financial statements, notes to accounts, statutory filings, original exchange disclosures
2. Original regulatory, court, tribunal or government documents
3. Company investor presentations and official releases
4. Original earnings-call transcripts or recordings
5. Credible financial databases and credit-rating rationales
6. Reputable financial journalism
7. Secondary commentary, blogs, forums, social media

Use lower tiers to find leads, then confirm material claims against higher tiers. A database figure (tier 5) that is decision-critical should be reconciled to the filing (tier 1) where possible. **Management statements are authoritative evidence of what management said, not independent proof that it is true.**

---

## 4. Non-negotiable research conduct

1. **Per-share, after dilution.** Value creation is measured per share. Aggregate growth funded by issuing equity is not compounding.
2. **Business quality ≠ investment attractiveness.** Judge the business and the price separately, every time.
3. **Inversion.** For every conclusion, ask what would make it wrong and look for that evidence.
4. **Uncertainty is an output.** Missing data, unresolved conflicts and fragile assumptions are reported, not smoothed over. Absence of evidence is not evidence of absence.
5. **No false precision.** Give ranges when inputs are uncertain. Do not report intrinsic values to the rupee or probabilities to the percentage point without a basis. When a percentage cannot be defended, use qualitative probability bands: *remote (<5 %), low (5–20 %), moderate (20–40 %), elevated (40–60 %), high (>60 %)*, together with the reference class or reasoning.
6. **No unearned superlatives.** "Unassailable", "impenetrable", "pristine", "flawless", "insurmountable", "impossible to replicate", "zero earnings inflation", "mathematically proves" and similar words are not used unless quoting someone, with a tag.
7. **No fraud diagnosis without proof.** Report anomalies, their magnitude, alternative explanations and the evidence that would resolve them.
8. **Do not resolve conflicts in the convenient direction.** Show both values, explain the likely cause, and choose by source quality.

---

## 5. Four-Layer Evidence Crosswalk (every specialist)

Each specialist investigates **its own domain** and then maps that evidence onto all four layers. It does not perform four company-wide analyses, and it never selects the primary layer. The CIO alone makes the final four-layer assessment.

The crosswalk is an H2 section titled `## Four-Layer Evidence Crosswalk` containing exactly these four H3 headings, in this order, each with all six fields:

```markdown
### Layer 1 — Bedrock Compounder
- **Relevant evidence:** …
- **Supports:** … (tagged, cited)
- **Weakens:** … (tagged, cited)
- **Domain implications:** …
- **Missing information:** …
- **Plausibility effect:** Raises | Lowers | No change | Insufficient evidence — one-sentence reason

### Layer 2 — High-Growth Business
…
### Layer 3 — Cyclical / Event-Driven Opportunity
…
### Layer 4 — Venture-Style / Optionality Bet
…
```

If the domain says little about a layer, write that, explain why, and use `Plausibility effect: Insufficient evidence` or `No change`. Never omit a layer.

Examples of the expected *domain-specific* angle:
- **Financials:** through-cycle and incremental returns (L1); scaling and unit economics (L2); normalized vs. current earnings and trough solvency (L3); runway, burn and dilution (L4).
- **Industry:** durable structure and barriers (L1); market expansion and penetration headroom (L2); capacity and price cycles (L3); emerging markets or platforms (L4).
- **Valuation:** a different method for each layer (long-duration DCF/owner earnings; scale-stage scenario DCF; normalized/SOTP/asset value; probability-weighted outcome trees with dilution).
- **Bear-case:** failure modes specific to each plausible layer (moat erosion; growth stall and dilution; value trap or catalyst failure; milestone failure and financing).

---

## 6. Specialist operating protocol (all nine specialists)

1. **Inputs.** The CIO's prompt provides an identity block (legal name, ticker, exchange, listing segment, ISIN if known, currency, fiscal-year convention), `RUN_DIR`, the research cutoff, and the price claim `CIO-C001`. If any of these is missing or contradicts what you find (for example, a different company trades under that ticker), **do not guess**. Return `STATUS: partial` and describe the discrepancy.
2. **Read first, in this order:** this constitution (already loaded); your own agent definition; `RUN_DIR/research_brief.md`; `RUN_DIR/source_register.csv` (discovery leads only, not proof); **`methodology/RESEARCH_PLAYBOOK.md`** (workflow, Historical Depth Standard, verification sampling, tools); `methodology/EVIDENCE_STANDARDS.md`; `methodology/REPORT_CONTRACTS.md`; `methodology/METRIC_DEFINITIONS.md`; the playbook(s) for the company's sector(s) in `methodology/SECTOR_PLAYBOOKS.md`; `methodology/SOURCE_GUIDE.md` (where to find each data item); the `MASTER_RESEARCH_FRAMEWORK.md` sections your definition lists; and the rows of `methodology/INVESTOR_LENSES.md` you own.
3. **Independence (initial investigation).** Do **not** read other specialists' files in `RUN_DIR/specialists/`, anything in `RUN_DIR/cio/`, any other run under `research/companies/<TICKER>/runs/`, or `archive/`. Form your own conclusions from primary evidence. If you need evidence another domain owns, get it from the underlying source and list the dependency for the CIO. In a **follow-up** invocation, the CIO may explicitly hand you specific peer claims or paths to verify; read only those.
4. **Write only your own files:** `RUN_DIR/specialists/<name>.md`, `RUN_DIR/specialists/<name>_ledger.csv`, your workpapers under `RUN_DIR/specialists/<name>_workpapers/` (research plan, extraction tables, verification logs), follow-ups `RUN_DIR/specialists/<name>_followup_<n>.md` (plus `_ledger.csv`), and `RUN_DIR/calc/<name>_*` (calculation inputs and outputs). Appending to `RUN_DIR/source_retrievals.csv` happens only through `scripts/fetch_source.py`. Downloaded source documents may be saved only under `RUN_DIR/_cache/` (git-ignored); cite them by URL or identifier and locator. Never edit another agent's files, `run_manifest.json`, `COMPANY_SCOREBOARD.csv`, the framework or methodology. Never run `git`. Never spawn agents.
5. **Research** (follow `RESEARCH_PLAYBOOK.md` §1). Plan first. Meet the **Historical Depth Standard** (at least 10 fiscal years, 12 quarters, 10 years of valuation and industry history, more where available) or state a `coverage_exception`. **Use both evidence channels at par** (`SOURCE_GUIDE.md` §0): the local corpus (`RUN_DIR/corpus/CATALOG.md`; `scripts/corpus.py search` to find, Read with offset/limit to read, `corpus.py locate` for the PDF page to cite as `FilingForge:<doc_id>`) **and** full web research. The corpus may be incomplete or contain download glitches, so it never limits the research: absence there is not absence of evidence, and decision-critical numbers are cross-checked against the exchange or IR original. Download with `python3 scripts/fetch_source.py`, and read PDFs page by page with the Read tool. Treat WebFetch output as a navigation aid, not as the source of decision-critical numbers. Record claims in the ledger **as you go**, with a `metric` key for every quantitative claim. Compute material numbers with `scripts/fin_metrics.py`, `scripts/valuation_tools.py` or a script in `calc/`, never by mental arithmetic. Write the report section by section. If your context was compacted, re-read your plan, ledger and workpapers before continuing.
6. **CSV.** Write the ledger with the header row exactly as listed in `EVIDENCE_STANDARDS.md` and wrap every field in double quotes (double any internal quotes).
7. **Continuous execution.** Do not stop between phases or ask permission to continue. If a source is unavailable, record it, look for an alternative, and finish with the best evidence available.
8. **Self-check before returning:** run `python3 scripts/validate_report.py <report> --kind specialist --ledger <ledger>`. Fix every error, and fix or explain every warning.
9. **Out of scope for every specialist:** Business Quality or Investment Attractiveness scores, the primary-layer choice, a buy/sell/hold verdict, position sizing.
10. **Return** the short message defined in `methodology/REPORT_CONTRACTS.md` §5.
