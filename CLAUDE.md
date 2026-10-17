# CLAUDE.md — Institutional Equity Research System

A Claude Code multi-agent system for buy-side equity research: one CIO (the main session) and nine specialist subagents. The goal is better investment decisions and per-share, risk-adjusted compounding. It is not about producing long reports.

## Run research
- `/research-company "<Company name>" <TICKER> <EXCHANGE> [--cutoff YYYY-MM-DD]`: this session becomes the CIO and follows `.claude/agents/cio.md`.
- Modes: `--validate-only [--probe]` (no research), `--dry-run "<Name>" <T> <EX>` (writes nothing), `--resume <T> <RUN_ID>`.
- Never spawn a `cio` subagent. Specialists are launched by the CIO via the Agent tool, **one at a time by default** (`--parallel` optional): `financials`, `filings`, `management`, `industry`, `moat`, `concalls`, `valuation`, `bear-case`, `special-situations`.

## Where things live (read the relevant file; do not rely on memory)
- `.claude/skills/investment-constitution/SKILL.md`: **canonical** four layers, fit scale, epistemic tags, citation syntax, specialist protocol
- `methodology/`: `SCORING.md` · `EVIDENCE_STANDARDS.md` · `REPORT_CONTRACTS.md` · `RESEARCH_PLAYBOOK.md` (how to research; **≥10-year depth standard**) · `METRIC_DEFINITIONS.md` · `SECTOR_PLAYBOOKS.md` · `SOURCE_GUIDE.md` · `INVESTOR_LENSES.md`
- `config/investment_policy.json`: owner policy. **No position or risk limits**; hurdle = the run's cited cost of equity. Nothing in it limits research depth.
- `config/data_sources.json` → FilingForge library (`~/Documents/FilingForgeLibrary`): read the company's filings there via `scripts/corpus.py` (Markdown, token-efficient) **and** run full web research at par. The library may be incomplete or have download glitches, so it never limits research (`methodology/SOURCE_GUIDE.md` §0).
- `MASTER_RESEARCH_FRAMEWORK.md`: what to investigate. `PROJECT_INSTRUCTIONS.md`: global rules
- `research/companies/<TICKER>/runs/<UTC RUN_ID>/`: one directory per run; `latest_run.txt` points to the latest complete run. `COMPANY_SCOREBOARD.csv`: compact two-score index
- `archive/`: old Antigravity definitions, **non-operative**. `docs/`: audit, architecture, operations

## Non-negotiables
1. The four layer names are immutable: Layer 1 — Bedrock Compounder; Layer 2 — High-Growth Business; Layer 3 — Cyclical / Event-Driven Opportunity; Layer 4 — Venture-Style / Optionality Bet. Analyze all four before classifying. SME listing does not set the layer.
2. Business Quality, Investment Attractiveness and layer fit are three separate measures. Score only per `methodology/SCORING.md`.
3. Never invent sources, URLs, pages, figures, quotations, agent outputs or check results. Material claims carry tags and claim IDs from a ledger, and quantitative claims carry a metric key. Material arithmetic comes from the scripts, not mental math.
4. Only the CIO updates the scoreboard (via `scripts/finalize_run.py`) and runs git (via `scripts/git_publish.py`: two serialized batches, push to the current branch, never force, never auto-merge). Never stage unrelated files (for example the untracked `research/companies/BAJFINANCE/`).
5. Never overwrite a previous run; never edit legacy runs or `archive/`.

## Tooling (Python 3.9, stdlib only)
```
python3 scripts/validate_system.py [--live-probe]   # configuration and contracts
python3 -m unittest discover tests                   # run after changing agents, methodology or scripts
python3 scripts/new_run.py ... [--dry-run]   ·   scripts/manifest.py   ·   scripts/validate_run.py RUN --stage specialists|final
scripts/merge_ledgers.py · build_scorecard.py · validate_scorecard.py · finalize_run.py · git_publish.py · compare_runs.py · scoreboard.py validate
scripts/corpus.py · fetch_source.py · html_tables.py · fin_metrics.py · score_guides.py · valuation_tools.py · reconcile_numbers.py · evidence_stats.py   # research tools
```
Canonical vocabularies are parsed from marked blocks (`<!-- NAME:BEGIN -->`) in the markdown. Edit them there, then run the tests.
