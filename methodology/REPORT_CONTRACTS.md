# Report Contracts

Defines the structure every specialist report shares, the run directory layout, and the completion criteria. Domain-specific sections live in each agent's definition (`.claude/agents/<name>.md`, between `REQUIRED_SECTIONS` markers). The CIO final-report structure lives in `.claude/agents/cio.md`. `scripts/validate_report.py` parses all of these. **Edit sections there, not in the scripts.**

---

## 1. Run directory layout

```text
research/companies/<TICKER>/
├── LATEST_RUN.txt                      # run id of the latest QC-passed run
└── runs/<RUN_ID>/                      # RUN_ID = YYYYMMDD-HHMM (local time at creation)
    ├── manifest.json                   # identity, cutoff, conventions, model, status, specialist invocations
    ├── research_brief.md               # CIO preflight brief given to every specialist
    ├── source_register.csv             # discovery leads (NOT proof, NOT conclusions)
    ├── specialists/
    │   ├── <name>.md                   # 9 initial reports
    │   ├── <name>_ledger.csv           # 9 claim ledgers
    │   └── <name>_followup_<n>.md      # optional targeted follow-ups (+ ledgers)
    ├── cio/
    │   ├── cio_ledger.csv
    │   ├── contradiction_log.md
    │   ├── final_report.md
    │   ├── scorecard.json
    │   └── qc_record.md
    ├── calc/                           # optional reproducible calculation scripts
    ├── evidence_ledger.csv             # merged by scripts/merge_ledgers.py
    └── qc/auto_checks.json             # written by scripts/validate_run.py
```

Create runs only with `python3 scripts/new_run.py`. Never overwrite or delete a previous run. A re-run is a new `RUN_ID`.

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
---
```

`report_status: partial` is allowed only when something specific blocked completion. Name the blocker in Section 1.

---

## 3. Common sections (all nine specialists, in this order)

Domain sections from the agent definition go between *Key Findings* and the *Four-Layer Evidence Crosswalk*. Numbering headings (`## 3. …`) is optional; the heading text must match.

<!-- COMMON_SECTIONS:BEGIN -->
- Mandate, Scope and Independence
- Key Findings
- Four-Layer Evidence Crosswalk
- Contradictions and Data Conflicts
- Assumptions, Uncertainty and Missing Evidence
- Questions and Dependencies for the CIO
- Domain Conclusion
- Source Register
<!-- COMMON_SECTIONS:END -->

What each must contain:
- **Mandate, Scope and Independence:** the decision questions answered; what was in and out of scope; the years and documents covered; blockers.
- **Key Findings:** 5–10 findings, most decision-relevant first, each tagged and cited.
- **Four-Layer Evidence Crosswalk:** exactly as specified in the constitution §5.
- **Contradictions and Data Conflicts:** conflicts *between sources* found in your own research (values, gap, likely cause, resolution, confidence). You have not read other specialists, so do not speculate about them.
- **Assumptions, Uncertainty and Missing Evidence:** the assumptions table and missing-evidence list from `methodology/EVIDENCE_STANDARDS.md` §5.
- **Questions and Dependencies for the CIO:** what another domain should verify, and claims you relied on that belong to another domain. Name the claim and why it matters.
- **Domain Conclusion:** answers to the agent's decision questions plus its formal classifications. **No** BQ or IA score, primary-layer selection, or buy/sell verdict.
- **Source Register:** see `EVIDENCE_STANDARDS.md` §2.

**Length:** depth comes from evidence, not words. Typical length is 3,000–9,000 words. Do not pad, and do not repeat the same finding in several sections; refer back to it instead.

---

## 4. Specialist completion criteria (checked at the Stage-2 barrier)

A specialist deliverable is **complete** only if:
1. `specialists/<name>.md` and `specialists/<name>_ledger.csv` exist.
2. The header matches the run's company, ticker and run id.
3. All common and domain sections are present.
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
