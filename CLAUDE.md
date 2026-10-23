# CLAUDE.md — Institutional Equity Research System

A Claude Code multi-agent system for buy-side equity research: one CIO (the main session), ten specialist subagents, an independent auditor, and three workers that acquire and read the documents (`librarian`, `reader`, `critical-reader`). The goal is better investment decisions and per-share, risk-adjusted compounding. It is not about producing long reports.

## Run research
- `/research-company "<Company name>" <TICKER> <EXCHANGE> [--cutoff YYYY-MM-DD] [--effort <level>]`: this session becomes the CIO and follows `.claude/agents/cio.md`. Start the session on **Opus at xhigh**: models and efforts are pinned per agent in `methodology/MODEL_POLICY.md` (the CIO, specialists, auditor and critical reader on Opus at xhigh; reader and librarian on Sonnet at high; `--effort max` for a run).
- Modes: `--validate-only [--probe]` (no research), `--dry-run "<Name>" <T> <EX>` (writes nothing), `--resume <T> <RUN_ID>`.
- Never spawn a `cio` subagent. Every other agent runs as its own headless session through the engine `scripts/agent_driver.py` (isolated from user-level hooks, plugins and memory, checked by the reading audit; pinned model and effort, one-hour cache, usage limits waited out, long agents handed to a fresh session at 250k context after a checkpoint; the Agent tool only when no `claude` binary is found). The ten specialists are **independent heads**: none can read another's work, `cio/`, `audit/` or other runs, and the reading audit checks it. They run **one at a time by default** (`--parallel` optional): `financials`, `filings`, `industry`, `scuttlebutt`, `moat`, `management`, `concalls`, `valuation`, `special-situations`, `bear-case`, all from one brief (`templates/specialist_prompt.md`). Each specialist's work is **verified** the moment it passes its validator (`scripts/verify.py`: values never seen in a source, sources and pages never opened, pack not read; then the `verifier` agent re-opens a sample of its claims at the sources) and every finding goes back to it; `verify.py run` gates Stages 2 and 4, and lessons from earlier runs' verification go into the next briefs. The `auditor` runs once the draft is complete (Stage 4) and writes only under `RUN_DIR/audit/`.
- Stage 0 acquires the filings once for the whole run: `scripts/exchange_index.py` (NSE, BSE, IR site, Internet Archive) → `scripts/document_map.py` (download, validate, cross-check against the FilingForge corpus) → `corpus/DOCUMENT_MAP.md`; the `librarian` finds what the indexes missed; the `historian` (`agent_driver.py events`) builds a sourced ten-year timeline of major events from news and the web, which the reading is checked against; `scripts/structured_filings.py` fetches the exact exchange filings (BRSR XBRL, voting results, audit-opinion statements).
- Stage 0b reads every in-scope page once and records it (every page of the latest 5 fiscal years' annual reports, the core sections of the 5 before; a missing in-scope report blocks the plan until found or explained): `scripts/reading.py plan` → `scripts/agent_driver.py reading` runs the `reader` / `critical-reader` launches as headless sessions outside the CIO's context, one at a time by default (critical sections read by both, independently; disagreements resolved against the page) → `reading.py dossiers` (topic dossiers and one reading pack per specialist) → `reading.py status --strict` (`corpus/reading/COVERAGE.md`, the only statement of what was read). A document an earlier run read and audited is reused. `scripts/reading_audit.py` checks it from the agents' transcripts at Stage 4.

## Where things live (read the relevant file; do not rely on memory)
- `.claude/skills/investment-constitution/SKILL.md`: **canonical** four layers, fit scale, epistemic tags, citation syntax, specialist protocol
- `methodology/`: `SCORING.md` · `EVIDENCE_STANDARDS.md` · `REPORT_CONTRACTS.md` · `RESEARCH_PLAYBOOK.md` (how to research; **≥10-year depth standard**; §1c the reading stage) · `READING_SCHEMAS.md` (what readers extract) · `MODEL_POLICY.md` (which model and effort does which work) · `METRIC_DEFINITIONS.md` · `SECTOR_PLAYBOOKS.md` · `SOURCE_GUIDE.md` · `INVESTOR_LENSES.md`
- `config/investment_policy.json`: owner policy. **No position or risk limits**; hurdle = the run's cited cost of equity. Nothing in it limits research depth.
- `config/data_sources.json` → FilingForge library (`~/Documents/FilingForgeLibrary`): read the company's filings there via `scripts/corpus.py` (Markdown, token-efficient) **and** the exchange / IR originals (document map) **and** full web research, at par. The library may be incomplete or have download glitches, so it never limits research (`methodology/SOURCE_GUIDE.md` §0).
- `MASTER_RESEARCH_FRAMEWORK.md`: what to investigate. `PROJECT_INSTRUCTIONS.md`: global rules
- `research/companies/<TICKER>/runs/<UTC RUN_ID>/`: one directory per run; `latest_run.txt` points to the latest complete run. `COMPANY_SCOREBOARD.csv`: compact two-score index
- `archive/`: old Antigravity definitions, **non-operative**. `docs/`: audit, architecture, operations

## Non-negotiables
1. The four layer names are immutable: Layer 1 — Bedrock Compounder; Layer 2 — High-Growth Business; Layer 3 — Cyclical / Event-Driven Opportunity; Layer 4 — Venture-Style / Optionality Bet. Analyze all four before classifying. SME listing does not set the layer.
2. Business Quality, Investment Attractiveness and layer fit are three separate measures. Score only per `methodology/SCORING.md`.
3. Never invent sources, URLs, pages, figures, quotations, agent outputs or check results. Never state reading coverage that the reading ledger does not record. Material claims carry tags and claim IDs from a ledger, and quantitative claims carry a metric key. Material arithmetic comes from the scripts, not mental math.
4. Only the CIO updates the scoreboard (via `scripts/finalize_run.py`) and runs git (via `scripts/git_publish.py`: two serialized batches, push to the current branch, never force, never auto-merge). Never stage unrelated files (for example the untracked `research/companies/BAJFINANCE/`).
5. Never overwrite a previous run; never edit legacy runs or `archive/`.

## Tooling (Python 3.9, stdlib only)
```
python3 scripts/validate_system.py [--live-probe]   # configuration and contracts
python3 -m unittest discover tests                   # run after changing agents, methodology or scripts
python3 scripts/new_run.py ... [--dry-run]   ·   scripts/manifest.py   ·   scripts/validate_run.py RUN --stage specialists|final
scripts/merge_ledgers.py · build_scorecard.py · validate_scorecard.py · finalize_run.py · git_publish.py · compare_runs.py · scoreboard.py validate
scripts/agent_driver.py   # the engine: runs readers, librarian, specialists, follow-ups and the auditor as headless sessions
scripts/reading.py · reading_audit.py · verify.py · structured_filings.py   # reading stage, reading and independence audit, verification loop, structured exchange filings
scripts/claim_graph.py · entities.py · outcomes.py   # what each conclusion rests on and what a wrong claim reaches; every entity across years; decisions, predictions and their outcomes (research/outcomes/)
scripts/connectors.py · browser.py   # free external sources (index TRI, MoSPI, GDELT, openFDA, Indian Kanoon, local transcription; registry in config/data_sources.json) and headless-Chrome page snapshots (fetch_source.py --snapshot)
scripts/corpus.py · exchange_index.py · document_map.py · doc_text.py · fetch_source.py (netfetch.py) · market_data.py · xbrl_facts.py · html_tables.py · fin_metrics.py · score_guides.py · valuation_tools.py · reconcile_numbers.py · evidence_stats.py · audit_tools.py   # research tools
```
Canonical vocabularies are parsed from marked blocks (`<!-- NAME:BEGIN -->`) in the markdown. Edit them there, then run the tests.
