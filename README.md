# Institutional Equity Research

A Claude Code–native, multi-agent research system for evaluating listed companies (built with Indian equities in mind, but company-agnostic). A **CIO** acquires and cross-checks the company's filings (NSE, BSE, the IR site, the Internet Archive and the owner's local library), has **every in-scope page read once and recorded** by reader agents (critical sections read twice, by two different models), orchestrates **ten independent specialists** who start from the resulting dossiers, audits and adjudicates their evidence, assesses the company under all four investment layers, and issues two separate, calibrated scores and a verdict. An **independent auditor** then checks the draft before it can pass QC. Every material claim is traceable to a source location.

```text
/research-company "TVS Motor Company Limited" TVSMOTOR NSE
/research-company --validate-only          # cheap configuration check, no research
```

## How it works

| Stage | What happens |
|---|---|
| 0 Preflight and acquisition | The CIO verifies that name, ticker and exchange identify one security, records the exchange close (bhavcopy) as the price, creates `research/companies/<T>/runs/<UTC RUN_ID>/`, then indexes NSE, BSE, the IR site and the Internet Archive, downloads and validates every core document (15 years of annual reports, 24 quarters of transcripts and presentations), and cross-checks them against the local corpus (`corpus/DOCUMENT_MAP.md`) |
| 0b Reading | Every page of the latest 5 fiscal years' annual reports and the core sections (audit, statements and notes, Board's report, MD&A) of the 5 before, 24 quarters of transcripts, 12 of presentations and the forensic exchange filings is read once in small fresh contexts, as headless sessions outside the CIO's context (`agent_driver.py reading`, one at a time by default); a missing in-scope report blocks the plan until found or explained, and a document an earlier run read and audited is reused: `reader` agents (Sonnet) read everything, `critical-reader` agents (Opus) read the auditor's reports, CARO, critical notes, Board's report, AOC-1/2, secretarial audit and related-party filings again, independently, and every disagreement is resolved against the page. Sentences and whole tables that repeat word for word in another year are read once; labels, values and headings are always read, and pages with images, no reliable text or numbers to confirm are viewed on the rendered page. Every quote, and every number an item states, is checked against its passage by script; `corpus/reading/COVERAGE.md` records every page. |
| 1 Independent research | Ten specialists, the separate heads of the fund, run **one at a time by default** (`--parallel` optional) as headless sessions of the engine (`agent_driver.py`), each finished and validated before the next, and **without seeing each other's work** (their sessions cannot read it, and the reading audit checks their transcripts): financials, filings, management, industry, moat, concalls, valuation, bear-case, special-situations and scuttlebutt (ground truth). Each writes a report and a claim ledger. |
| 2 Completion barrier and gap closure | **The verification loop** has already checked each specialist against its own transcripts (every FACT value seen in a source it opened, every cited page opened, its reading pack read) and had an independent `verifier` agent re-open a sample of its claims at the sources, sending every discrepancy back to the specialist; `verify.py run` re-checks the whole research and the barrier fails until it passes. `scripts/validate_run.py --stage specialists` checks every deliverable, including each report's Method Coverage Checklist. Failures are re-invoked, never invented. Every Partial or Not available step goes into `cio/gap_register.md`, and closable gaps go back to the owning specialist. Git batch 1 is committed and pushed. |
| 3 Adjudication | The CIO reads everything, re-verifies at least 12 decision-critical claims, recomputes at least 3 calculations, logs contradictions and runs targeted follow-ups. It then writes its own **independent analysis** (`cio/cio_analysis.md`), the synthesis, the four independent layer assessments and the thesis-disproof exercise, and **only then scores**: `build_scorecard.py` computes the scores from its judgments, and the robustness test sets the confidence |
| 4 Audit, QC and publish | The **reading audit** checks from the agents' own transcripts that every reader received every line and every agent ran on its pinned model and effort; the **auditor** (fresh context) ties out the report's numbers, re-verifies a stratified claim sample at the source, recomputes the calculations and audits the scoring; the CIO resolves every finding, and Critical ones are re-audited → automated and manual QC → `finalize_run.py` (scoreboard and `latest_run.txt` only on a `complete` outcome) → git batch 2, pushed to the current branch (never forced) |

**The four investment layers (immutable):** Layer 1 — Bedrock Compounder · Layer 2 — High-Growth Business · Layer 3 — Cyclical / Event-Driven Opportunity · Layer 4 — Venture-Style / Optionality Bet.

**Two scores, never mixed:** Business Quality (0–100, price-independent) and Investment Attractiveness (0–100, at the verified price), each with fixed dimensions, gates, confidence and a judgment band.

**A fund manager's decision, not a formula** (methodology 3.0.0): weights follow the archetype (fixed in advance per layer), every judgment carries its own confidence and uncertainty is never rewarded, archetype must-pass tests are non-compensatory, the required margin of safety rises as confidence falls, and the verdict states its decision drivers, conviction and the condition that decided it.

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Compact session instructions |
| `.claude/agents/` | The fifteen operative agent definitions (`cio`, ten specialists, `auditor`, and the workers `librarian`, `reader`, `critical-reader`) |
| `.claude/skills/research-company/` | The `/research-company` workflow |
| `.claude/skills/investment-constitution/` | Canonical definitions, preloaded into every specialist |
| `methodology/` | Scoring, evidence standards, report contracts, research playbook (10+ year depth standard, the reading stage), reading schemas, model policy, metric dictionary, 18 sector playbooks, source guide, investor lenses |
| `config/investment_policy.json` | Owner policy: no risk limits; hurdle derived each run from the cost of equity |
| `config/data_sources.json` | Path to the FilingForge library of downloaded filings (read via `scripts/corpus.py`; used at par with full web research, never as a limit) |
| `MASTER_RESEARCH_FRAMEWORK.md` | Comprehensive research specification |
| `PROJECT_INSTRUCTIONS.md` | Global research and execution rules |
| `COMPANY_SCOREBOARD.csv` | Compact index: identity, run metadata and the two scores, one row per company |
| `research/companies/` | Per-company run archive |
| `scripts/`, `tests/` | Deterministic validation and reporting tools, plus their tests |
| `templates/` | Run templates and the scorecard schema example |
| `docs/` | Migration audit, architecture, operations guide, framework change log |
| `archive/` | Pre-migration Antigravity definitions (non-operative) |

## Requirements

- Claude Code (developed against 2.1.296) with access to Opus and Sonnet. Models and efforts are pinned per agent (`methodology/MODEL_POLICY.md`): judgment on Opus at xhigh effort (`--effort max` per run), document reading on Sonnet at high with Opus re-reading the critical sections.
- Web search and fetch tools enabled, because research depends on retrieving primary documents.
- Python 3.9 or newer (standard library only).

See `docs/OPERATIONS.md` for running, re-running, follow-ups, validation and troubleshooting.
