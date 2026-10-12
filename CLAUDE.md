# CLAUDE.md — Institutional Equity Research System

A Claude Code multi-agent system for buy-side equity research: one CIO (the main session) and nine specialist subagents. The goal is better investment decisions and per-share, risk-adjusted compounding. It is not about producing long reports.

## Run research
- `/research-company <TICKER or name> [exchange] [--cutoff YYYY-MM-DD]`: this session becomes the CIO and follows `.claude/agents/cio.md`.
- Never spawn a `cio` subagent. Specialists are launched by the CIO in parallel via the Agent tool: `financials`, `filings`, `management`, `industry`, `moat`, `concalls`, `valuation`, `bear-case`, `special-situations`.

## Where things live (read the relevant file; do not rely on memory)
- `.claude/skills/investment-constitution/SKILL.md`: **canonical** four layers, fit scale, epistemic tags, citation syntax, specialist protocol
- `methodology/SCORING.md` · `EVIDENCE_STANDARDS.md` · `INVESTOR_LENSES.md` · `REPORT_CONTRACTS.md`
- `MASTER_RESEARCH_FRAMEWORK.md`: what to investigate. `PROJECT_INSTRUCTIONS.md`: global rules
- `research/companies/<TICKER>/runs/<RUN_ID>/`: one directory per run. `COMPANY_SCOREBOARD.csv`: latest QC-passed scores
- `archive/`: old Antigravity definitions, **non-operative**. `docs/`: audit, architecture, operations

## Non-negotiables
1. The four layer names are immutable: Layer 1 — Bedrock Compounder; Layer 2 — High-Growth Business; Layer 3 — Cyclical / Event-Driven Opportunity; Layer 4 — Venture-Style / Optionality Bet. Analyze all four before classifying. SME listing does not set the layer.
2. Business Quality, Investment Attractiveness and layer fit are three separate measures. Score only per `methodology/SCORING.md`.
3. Never invent sources, URLs, pages, figures, quotations, agent outputs or check results. Material claims carry tags and claim IDs from a ledger.
4. Only the CIO updates the scoreboard (via `scripts/update_scoreboard.py`) and runs git. Never push unless asked. Never stage unrelated files (for example the untracked `research/companies/BAJFINANCE/`).
5. Never overwrite a previous run; never edit legacy runs or `archive/`.

## Tooling (Python 3.9, stdlib only)
```
python3 scripts/new_run.py --ticker T --company "Name" --exchange NSE --segment main
python3 scripts/validate_report.py <report> --kind specialist --ledger <ledger>
python3 scripts/validate_run.py <run_dir> --stage specialists|final
python3 scripts/merge_ledgers.py <run_dir>
python3 scripts/validate_scorecard.py <run_dir>/cio/scorecard.json
python3 scripts/update_scoreboard.py <run_dir>
python3 -m unittest discover tests      # run after changing agents, methodology or scripts
```
Canonical vocabularies are parsed from marked blocks (`<!-- NAME:BEGIN -->`) in the markdown. Edit them there, then run the tests.
