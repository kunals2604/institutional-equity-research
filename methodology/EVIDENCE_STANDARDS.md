# Evidence Standards — Ledger, Citations and Numerical Controls

Applies to every agent. The tag vocabulary, the claim-ID syntax and the source hierarchy are defined in `.claude/skills/investment-constitution/SKILL.md`. This file defines **how evidence is recorded and checked**. `scripts/validate_ledger.py` parses the marked blocks.

---

## 1. Evidence ledger

Each author writes its own ledger so that parallel agents never write to the same file:

| Author | Ledger path (inside the run directory) |
|---|---|
| Specialist `<name>` | `specialists/<name>_ledger.csv` |
| CIO | `cio/cio_ledger.csv` |

`scripts/merge_ledgers.py` combines them into `evidence_ledger.csv` at the run root. Never edit the merged file by hand.

Record **material** claims: those that a conclusion, score, valuation input or classification depends on. Do not inflate the ledger with trivia. Typical specialist ledgers have 30–150 rows.

### Columns (in this order)
<!-- LEDGER_COLUMNS:BEGIN -->
- claim_id
- author
- claim
- tag
- metric
- value
- unit
- period
- basis
- source_title
- source_issuer
- source_url_or_id
- source_date
- retrieved_date
- locator
- source_tier
- primary
- confidence
- corroborated_by
- contradicted_by
- formula_or_inputs
- notes
<!-- LEDGER_COLUMNS:END -->

| Column | Rule |
|---|---|
| claim_id | `PREFIX-C###`, unique within the run (prefixes are listed in the constitution) |
| author | The agent name, for example `financials`, `bear-case`, `cio` |
| claim | One sentence stating exactly what is claimed |
| tag | One of the six constitution tags, spelled exactly |
| metric | **Required when `value` is filled** for FACT / CALCULATION / ESTIMATE: a key from `methodology/METRIC_DEFINITIONS.md`, a `cagr_<item>_<n>y` key, or `other:<short_name>`. This is what lets `scripts/reconcile_numbers.py` find agents reporting different numbers for the same thing. |
| value / unit / period | For quantitative claims: `48213`, `INR crore`, `FY2025`. Leave blank for qualitative claims. |
| basis | `consolidated`, `standalone`, `segment:<name>`, or `n/a` |
| source_title / source_issuer | For example `Annual Report 2024-25` / `TVS Motor Company Ltd` |
| source_url_or_id | The URL actually retrieved, or a stable identifier (BSE/NSE filing ID, ISIN, CIN, document title + date). **Never invented.** For documents downloaded with `scripts/fetch_source.py`, use the URL. Its SHA-256 fingerprint is then in `source_retrievals.csv`. |
| source_date | Publication or filing date (YYYY-MM-DD where known) |
| retrieved_date | The date you accessed it in this run (YYYY-MM-DD) |
| locator | Page, note, table, schedule, paragraph or transcript timestamp, for example `p.212, Note 28`. Use `NOT_LOCATED` only when genuinely unknown; this lowers confidence. |
| source_tier | 1–7 per the constitution hierarchy |
| primary | `Y` for tiers 1–4 (the issuer's or regulator's own documents), otherwise `N` |
| confidence | `H`, `M` or `L` |
| corroborated_by | Other claim IDs or sources that independently agree |
| contradicted_by | Claim IDs or sources that disagree (required if known) |
| formula_or_inputs | **Required for CALCULATION** (formula plus input claim IDs, for example `FIN-C010 / FIN-C011`). **Required for ESTIMATE** (method and basis). |
| notes | Assumptions, adjustments, reasons for downgrades |

### Validation rules (enforced)
- FACT: `source_url_or_id`, `retrieved_date` and `locator` must be non-empty. `NOT_LOCATED` is allowed with confidence `M` or `L` only. A FACT resting only on tier 6–7 sources produces a warning.
- MANAGEMENT STATEMENT: source and locator (page or timestamp) are required.
- CALCULATION: `formula_or_inputs` is required and should reference input claim IDs.
- ESTIMATE: `formula_or_inputs` or `notes` must state the basis.
- `source_tier` ∈ 1–7, `primary` ∈ {Y, N}, `confidence` ∈ {H, M, L}.
- Quantitative FACT / CALCULATION / ESTIMATE rows carry a valid `metric`.
- Every claim ID cited in a report must exist in a ledger in that run.

### Evidence thresholds (checked by `scripts/evidence_stats.py`; breaches are QC warnings the CIO must address)
<!-- EVIDENCE_THRESHOLDS:BEGIN -->
- min_claims_per_specialist: 25
- min_primary_share_overall: 0.60
- min_primary_share_per_specialist: 0.40
- max_not_located_share: 0.15
- max_low_tier_fact_share: 0.20
<!-- EVIDENCE_THRESHOLDS:END -->
"Low-tier FACT" means a FACT whose only source is tier 6–7.

---

## 2. Citations in reports

- Cite inline with the tag: `Standalone revenue grew to ₹X crore in FY25 [FACT: FIN-C004].`
- In tables, put the claim ID in a column or in the cell (`₹X cr [FACT: FIN-C004]`).
- The report ends with a **Source Register** listing each source once: ID, title, issuer, date, URL or identifier, retrieved date, tier. The register supports the inline citations; it does not replace them.
- Do not paste long extracts. Quote at most the sentence that matters, with its locator.

---

## 2a. Document provenance

- Download decision-critical documents (annual reports, results, transcripts, orders, rating rationales) with `scripts/fetch_source.py`. It stores the file under `RUN_DIR/_cache/` (git-ignored, because of licensing and size) and appends a row to `RUN_DIR/source_retrievals.csv` (committed): time, author, URL, final URL, HTTP status, content type, bytes, **SHA-256**, local path. Failed attempts are logged too, which documents missing evidence honestly.
- WebFetch output is a model-processed rendering. It may be cited for **qualitative** facts with the URL. **Decision-critical numbers** must be read from the original document (PDF page via the Read tool, or an HTML table via `scripts/html_tables.py`) and cited at that location.

## 3. Numerical controls (all agents; the CIO audits)

Reconcile and **state explicitly** in every report that uses numbers:

1. **Consolidated vs. standalone:** say which applies to each figure. When they diverge materially (for example, a captive NBFC), explain why and use the economically appropriate basis for each question.
2. **Fiscal vs. calendar periods:** label periods (`FY2025` = year ending March 2025 for Indian companies, unless stated otherwise). Do not mix TTM, fiscal and calendar figures without saying so.
3. **Units and currency:** state units once per table (₹ crore, ₹ lakh, US$ million). Convert explicitly and record the FX rate and date as a claim.
4. **Share count:** basic and diluted. Adjust per-share history for splits and bonuses. Record convertibles, warrants and ESOP overhang.
5. **Price:** price, exchange, timestamp (date and time or "close of DD-MMM-YYYY") and source are recorded once by the CIO in preflight as `CIO-C001`. Specialists cite that ID or record their own with a timestamp. Market cap and EV must reconcile to that price and share count.
6. **Reported vs. adjusted:** keep reported figures and your adjustments in separate rows, and give the adjustment's formula.
7. **Historical vs. forecast:** never place forecasts in a historical table without marking them `E`.
8. **Provider differences:** when a database and a filing disagree, record both, the size of the gap, the likely cause (classification, restatement, consolidation scope) and which figure you use.
9. **Cost of capital:** use **one** cost-of-capital assumption set per run, defined by the valuation specialist and adjudicated by the CIO, with inputs cited. Any sensitivity uses explicitly labeled alternatives.
10. **Valuation inputs → output:** every input in a valuation model traces to a claim ID, and the final value traces to the model.
11. **One definition per metric:** use `methodology/METRIC_DEFINITIONS.md`. If you must deviate (for example ROCE including other income), use a distinct `other:` metric key and say so.
12. **Deterministic arithmetic:** material ratios, CAGRs and valuation math come from `scripts/fin_metrics.py` / `scripts/valuation_tools.py` (or a script in `calc/`), not mental arithmetic.
13. **Cross-ledger reconciliation:** `scripts/reconcile_numbers.py` flags different values for the same `(metric, period, basis, unit)` across agents (tolerance 1 %). The CIO must adjudicate **every** flagged conflict in the contradiction log; `validate_run.py --stage final` fails while any conflict is unaddressed.

**Reproducibility:** for every material calculation, show the formula and enough arithmetic to reproduce it, or put the computation in a small script under the run directory (`calc/*.py`) and cite it.

**Precision:** round to the precision the inputs support. Fair values are reported as ranges (for example ₹2,300–2,800, base ₹2,550), not to the rupee or paisa.

---

## 4. Language controls

These phrases are flagged by the validator. In the final report they are errors unless the line is a tagged MANAGEMENT STATEMENT quotation.

<!-- FLAGGED_PHRASES:BEGIN -->
- unassailable
- impenetrable
- pristine
- flawless
- insurmountable
- impossible to replicate
- zero earnings inflation
- risk-free investment
- cannot lose
- guaranteed return
- mathematically proves
- mathematically disproves
- fortress balance sheet
<!-- FLAGGED_PHRASES:END -->

Say what the evidence shows instead. For example: "net cash of ₹X crore and no debt maturities before FY28 [FACT: FIN-C033]" rather than "fortress balance sheet".

---

## 5. Uncertainty and assumptions register

Every report has an assumptions table:

| # | Assumption | Why necessary | Supporting evidence | Plausible alternative | Effect if wrong | Confidence |
|---|---|---|---|---|---|---|

And a missing-evidence list: what was sought, where, why it was unavailable, and how the gap changes the conclusion.

---

## 6. Source access notes

- Indian listed companies: annual reports, results and transcripts are usually on the company's investor-relations page and on BSE/NSE corporate filings. Shareholding patterns, pledges and insider (SAST/PIT) disclosures are on exchange filings. Credit-rating rationales are on rating-agency sites. Use what you can retrieve and record what you could not.
- If a page will not load or is behind a paywall, say so in the missing-evidence list. Do not reconstruct its contents from memory.
- Aggregators (for example Screener-style datasets, tier 5) are acceptable for discovery and as a cross-check. Reconcile decision-critical numbers to filings.
