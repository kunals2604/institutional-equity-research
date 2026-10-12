# Institutional Equity Research

A Claude Code–native, multi-agent research system for evaluating listed companies (built with Indian equities in mind, but company-agnostic). A **CIO** orchestrates **nine independent specialists**, audits and adjudicates their evidence, assesses the company under all four investment layers, and issues two separate, calibrated scores and a verdict, every material claim traceable to a source location.

```text
/research-company TVSMOTOR NSE
```

## How it works

| Stage | What happens |
|---|---|
| 0 Preflight | The CIO verifies identity, listing, price and timestamp, then creates `research/companies/<T>/runs/<RUN_ID>/` with a manifest, research brief and discovery-lead source register |
| 1 Independent research | Nine specialists run **in parallel** and **without seeing each other's work**: financials, filings, management, industry, moat, concalls, valuation, bear-case, special-situations. Each writes a report and a claim ledger. |
| 2 Completion barrier | `scripts/validate_run.py --stage specialists` checks every deliverable. Failures are re-invoked, never invented. |
| 3 Adjudication | The CIO reads everything, re-verifies at least 12 decision-critical claims, recomputes at least 3 calculations, logs contradictions, runs targeted follow-ups, analyzes four layers independently, classifies, runs the thesis-disproof exercise, and scores |
| 4 QC and publish | Automated and manual QC, then a scoreboard update (QC-passed runs only) and a git commit |

**The four investment layers (immutable):** Layer 1 — Bedrock Compounder · Layer 2 — High-Growth Business · Layer 3 — Cyclical / Event-Driven Opportunity · Layer 4 — Venture-Style / Optionality Bet.

**Two scores, never mixed:** Business Quality (0–100, price-independent) and Investment Attractiveness (0–100, at the verified price), each with fixed dimensions and weights, gates, confidence and a judgment band. The verdict follows a documented mapping.

## Repository map

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Compact session instructions |
| `.claude/agents/` | The ten operative agent definitions (`cio` + nine specialists) |
| `.claude/skills/research-company/` | The `/research-company` workflow |
| `.claude/skills/investment-constitution/` | Canonical definitions, preloaded into every specialist |
| `methodology/` | Scoring, evidence standards, investor lenses, report contracts |
| `MASTER_RESEARCH_FRAMEWORK.md` | Comprehensive research specification |
| `PROJECT_INSTRUCTIONS.md` | Global research and execution rules |
| `COMPANY_SCOREBOARD.csv` | Latest QC-passed result per company |
| `research/companies/` | Per-company run archive |
| `scripts/`, `tests/` | Deterministic validation and reporting tools, plus their tests |
| `templates/` | Run templates and the scorecard schema example |
| `docs/` | Migration audit, architecture, operations guide, framework change log |
| `archive/` | Pre-migration Antigravity definitions (non-operative) |

## Requirements

- Claude Code (developed against 2.1.296) with access to an Opus model. All agents use the `opus` alias.
- Web search and fetch tools enabled, because research depends on retrieving primary documents.
- Python 3.9 or newer (standard library only).

See `docs/OPERATIONS.md` for running, re-running, follow-ups, validation and troubleshooting.
