# Report Contracts

Defines the structure every specialist report shares, the run directory layout, and the completion criteria. Domain-specific sections live in each agent's definition (`.claude/agents/<name>.md`, between `REQUIRED_SECTIONS` markers). The CIO final-report structure lives in `.claude/agents/cio.md`. `scripts/validate_report.py` parses all of these. **Edit sections there, not in the scripts.**

---

## 1. Run directory layout

```text
COMPANY_SCOREBOARD.csv                      # compact index: one row per company (scripts/scoreboard.py)
research/companies/<TICKER>/
├── latest_run.txt                          # RUN_ID of the most recent run with outcome "complete" (never a failed/partial run)
└── runs/<RUN_ID>/                          # RUN_ID = UTC, sortable: YYYYMMDDTHHMMSSZ (e.g. 20261012T074500Z)
    ├── run_manifest.json                   # identity, cutoff, start/completion time, price + timestamp, model, status, specialist invocations
    ├── research_brief.md                   # CIO preflight brief given to every specialist (facts only)
    ├── source_register.csv                 # discovery leads (NOT proof, NOT conclusions)
    ├── source_retrievals.csv               # every download: time, author, URL, HTTP status, bytes, SHA-256 (scripts/fetch_source.py)
    ├── corpus/                             # CATALOG.md, catalog.csv (+ SHA-256 of each local document), coverage.json (scripts/corpus.py)
    ├── specialists/
    │   ├── <name>.md                       # 9 initial reports: financials, filings, management, industry, moat,
    │   ├── <name>_ledger.csv               #   concalls, valuation, bear-case, special-situations (+ 9 claim ledgers)
    │   ├── <name>_workpapers/              # research plan, extraction tables (e.g. financial_history.csv), verification logs
    │   └── <name>_followup_<n>.md          # optional targeted follow-ups (+ ledgers)
    ├── cio/
    │   ├── cio_ledger.csv
    │   ├── contradiction_log.md
    │   ├── final_report.md                 # states its as-of date in front matter and the Decision Dashboard
    │   ├── scorecard.json
    │   └── quality_control.md
    ├── calc/                               # inputs/outputs of fin_metrics.py, valuation_tools.py and other reproducible calculations
    ├── evidence_ledger.csv                 # merged by scripts/merge_ledgers.py
    ├── qc/                                 # auto_checks.json, evidence_stats.json, numeric_conflicts.csv (validate_run.py --stage final)
    └── _cache/                             # local downloads only; git-ignored, never committed
```

Rules:
- Create runs only with `python3 scripts/new_run.py`. It refuses to overwrite an existing run. A re-run is a new `RUN_ID`, independently identifiable and comparable via `scripts/compare_runs.py`.
- `run_manifest.json` `status` moves through `preflight → specialists_running → specialists_complete|specialists_incomplete → synthesis → qc_auto_passed|qc_auto_failed → complete | insufficient_evidence | qc_failed | failed`. `interrupted` runs are continued with `/research-company --resume`.
- `scripts/finalize_run.py` alone decides the outcome (`methodology/SCORING.md` §8). Only `complete` updates the scoreboard and `latest_run.txt`.
- **Source documents are not committed** (licensing, size, access). The repository stores traceable references (URL or identifier, locator, retrieval date) and short permitted extracts in ledgers and reports. Local downloads go to `_cache/`.

---

## 2. Specialist report header (YAML front matter, required)

```yaml
---
specialist: financials
company: <legal name>
ticker: <TICKER>
exchange: <NSE|BSE|NSE-SME|BSE-SME|...>
run_id: <RUN_ID>
research_cutoff: <YYYY-MM-DD>
report_status: complete        # complete | partial
model_requested: opus
independence_attestation: "Initial investigation completed without reading other specialists' reports or prior-run conclusions for this company."
coverage_exception: ""         # optional: why the Historical Depth Standard could not be met
---
```

`report_status: partial` is allowed only when something specific blocked completion. Name the blocker in Section 1.

---

## 3. Common sections (all nine specialists, in this order)

Order: the **head** sections, then the domain sections from the agent definition, then the **tail** sections. Numbering headings (`## 3. …`) is optional; the heading text must match.

<!-- COMMON_SECTIONS_HEAD:BEGIN -->
- Mandate, Scope and Independence
- Key Findings
- Data Coverage
<!-- COMMON_SECTIONS_HEAD:END -->

<!-- COMMON_SECTIONS_TAIL:BEGIN -->
- Four-Layer Evidence Crosswalk
- Contradictions and Data Conflicts
- Assumptions, Uncertainty and Missing Evidence
- Questions and Dependencies for the CIO
- Domain Conclusion
- Source Register
<!-- COMMON_SECTIONS_TAIL:END -->

What each must contain:
- **Mandate, Scope and Independence:** the decision questions answered; what was in and out of scope; blockers; the sector playbook(s) applied.
- **Key Findings:** 5–10 findings, most decision-relevant first, each tagged and cited.
- **Data Coverage:** a table with columns data series | periods covered | count | sources and tier | verification (full / sampled / aggregator-only) | gaps and exceptions. It must meet the Historical Depth Standard (`methodology/RESEARCH_PLAYBOOK.md` §2), or the front matter must carry a `coverage_exception:` explaining why not. `validate_report.py` counts the periods.
- **Four-Layer Evidence Crosswalk:** exactly as specified in the constitution §5.
- **Contradictions and Data Conflicts:** conflicts *between sources* found in your own research (values, gap, likely cause, resolution, confidence). You have not read other specialists, so do not speculate about them.
- **Assumptions, Uncertainty and Missing Evidence:** the assumptions table and missing-evidence list from `methodology/EVIDENCE_STANDARDS.md` §5.
- **Questions and Dependencies for the CIO:** what another domain should verify, and claims you relied on that belong to another domain. Name the claim and why it matters.
- **Domain Conclusion:** answers to the agent's decision questions plus its formal classifications. **No** BQ or IA score, primary-layer selection, or buy/sell verdict.
- **Source Register:** see `EVIDENCE_STANDARDS.md` §2.

**Length:** there is **no upper limit**. Research is as deep and thorough as the evidence allows, and the depth standards are floors, not ceilings. Depth comes from evidence, not padding: do not repeat the same finding in several sections; refer back to it instead.

---

## 4. Specialist completion criteria (checked at the Stage-2 barrier)

A specialist deliverable is **complete** only if:
1. `specialists/<name>.md` and `specialists/<name>_ledger.csv` exist.
2. The header matches the run's company, ticker and run id.
3. All common and domain sections are present, and the Data Coverage meets the depth standard (or there is a stated exception).
4. The crosswalk has all four canonical layer headings, each with a plausibility effect.
5. Every FACT, MANAGEMENT STATEMENT, CALCULATION and ESTIMATE tag cites a claim ID that exists in the ledger.
6. The ledger passes `scripts/validate_ledger.py` with no errors.
7. No layer name is altered (`validate_report.py` checks this).

Run: `python3 scripts/validate_run.py <run_dir> --stage specialists`.

---

## 5. Return message (specialist → CIO)

Keep the final message short; the report file carries the substance:

```
STATUS: complete | partial (reason)
REPORT: <path>
LEDGER: <path> (<n> claims)
TOP FINDINGS: 3–5 one-line findings with claim IDs
OPEN ISSUES: up to 5 unresolved questions
SELF-CHECK: output of `python3 scripts/validate_report.py <report> --kind specialist` (pass/fail + counts)
```
