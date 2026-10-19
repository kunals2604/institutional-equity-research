# Architecture

## 1. Roles and control flow

```mermaid
flowchart TD
    U["/research-company \"Name\" TICKER EXCHANGE"] --> CIO["CIO = main session<br/>(.claude/agents/cio.md)"]
    CIO --> P["Stage 0 Preflight<br/>identity check · new_run.py (UTC run id) · price CIO-C001 = exchange close (market_data.py)"]
    P --> ACQ["Stage 0 acquisition<br/>exchange_index.py: NSE + BSE + IR site + Internet Archive<br/>document_map.py: download, validate, cross-check vs. FilingForge corpus → DOCUMENT_MAP.md<br/>librarian (Sonnet): documents the indexes missed<br/>structured_filings.py + xbrl_facts.py: exact exchange filings"]
    ACQ --> RD["Stage 0b reading — one agent at a time<br/>reading.py plan: every page of 5 fiscal years, core sections of the 5 before; passages, sections, critical classes, repeats read once (never labels or values), VIEW REQUIRED pages (no text, images, numbers); documents reused from audited earlier runs<br/>agent_driver.py reading: headless sessions outside the CIO's context · reader (Sonnet) every chunk · critical-reader (Opus) critical chunks again · disagreements resolved on the page<br/>reading.py check · dossiers · status → COVERAGE.md"]
    RD --> S1
    subgraph S1["Stage 1 — ten specialists, one at a time by default (--parallel optional), no cross-reading"]
      F1[financials] --> F2[filings] --> F3[industry] --> F4[scuttlebutt] --> F5[moat]
      F5 --> F6[management] --> F7[concalls] --> F8[valuation] --> F9[special-situations] --> F10[bear-case]
    end
    S1 --> B["Stage 2 barrier + gap-closure loop<br/>validate_run.py --stage specialists · gap_register.md"]
    B -->|failures / closable gaps| R["targeted re-invocation or follow-up"] --> B
    B --> G1["git batch 1 (specialists) + push"]
    G1 --> A["Stage 3 synthesis first, scores last<br/>audit ≥12 claims · recompute ≥3 · contradiction log · follow-ups<br/>CIO independent analysis · synthesis · 4 layer assessments · thesis-disproof<br/>build_scorecard.py · robustness → confidence · symmetric adversarial review"]
    A --> RA["Stage 4 reading audit (reading_audit.py)<br/>from the agents' transcripts: pinned model and effort · every line received · VIEW REQUIRED pages opened · packs read"]
    RA --> AU["Stage 4 independent audit (auditor agent, fresh context)<br/>tie-out · source re-verification sample · recomputation · scoring audit<br/>CIO resolutions · re-audit of Critical findings"]
    AU --> Q["QC<br/>merge_ledgers · validate_run --stage final · quality_control.md"]
    Q --> FR["finalize_run.py<br/>complete → locked scoreboard upsert + latest_run.txt<br/>otherwise → manifest only"]
    FR --> G2["git batch 2 (final) + push — never force, never merge"]
```

**Why the CIO is the main session:** in Claude Code, subagents do not launch further subagents. A CIO running as a subagent could not orchestrate, and nesting would only add a layer of summarization. `/research-company` therefore turns the current session into the CIO, which loads `.claude/agents/cio.md` as its protocol. The same file works as a main-thread agent via `claude --agent cio`.

**Why independent, and why sequential by default:** the pre-migration system ran specialists in dependent waves, and each specialist "reconciled" against the earlier reports, so errors spread instead of being caught (audit §4). Now every specialist works from primary sources without reading the others, and cross-examination is the CIO's job. Running them one at a time (since 2.3.0) changes the order, not the independence: it keeps at most one agent in flight when a usage limit interrupts, and later specialists reuse the documents acquired in Stage 0.

**Why a separate auditor:** the agent that wrote the conclusion should not be the only one certifying it. The auditor (2.4.0) reads the finished draft with fresh context and checks numbers, sources, calculations, scoring and process; the bear-case agent challenges the investment view. Separation of duties is the institutional control the earlier design lacked.

**Why a reading stage, and why readers are separate from specialists** (3.1.0): ten years of annual reports are 4–5M tokens, several times what one context can hold, and an agent cannot forget what it has read. In run 20261012T132311Z the specialists therefore searched instead of reading: together they saw 11–17 % of each report's text and read transcripts through a keyword filter, while their reports implied more. Reading every page once, in small fresh contexts, is both cheaper per page and more accurate than long contexts, and it separates *reading* (complete, literal, checkable) from *reasoning* (the specialists, who start from complete dossiers and keep their context for analysis). Coverage became a record that scripts generate and the reading audit checks against the transcripts, not a claim.

**Why the models are pinned, and why Sonnet reads** (3.1.0): judgment stays on Opus at the owner's pinned effort (xhigh since 2026-10-19; `--effort max` per run). Sonnet does only work that passes the five tests of `MODEL_POLICY.md` (fully specified, checkable by script, omissions detectable, no judgment, calibrated); the critical sections are read by both models, because two different models miss different things. Pinning removes a silent discrepancy: in run 20261012T132311Z every agent, the CIO included, ran at effort *high* while the owner believed *max*.

**Why acquisition is a stage, not a specialist:** finding and downloading filings is deterministic work. Done once, by scripts, it is faster, cheaper and more reliable than ten agents each searching the same exchange pages, and it produces the two-channel cross-check the owner asked for.

## 2. Single sources of truth

| Fact | Lives in | Consumed by |
|---|---|---|
| Layer names and definitions, fit scale, epistemic tags, claim-ID syntax, specialist protocol | `.claude/skills/investment-constitution/SKILL.md` (marked blocks) | Preloaded into every agent via `skills:` frontmatter; parsed by `scripts/research_lib.py` |
| BQ/IA dimensions, weights, gates, verdicts, valuation statuses, methodology version | `methodology/SCORING.md` (marked blocks) | CIO; `validate_scorecard.py` |
| Ledger columns, flagged phrases | `methodology/EVIDENCE_STANDARDS.md` (marked blocks) | All agents; `validate_ledger.py`, `validate_report.py` |
| Common report sections | `methodology/REPORT_CONTRACTS.md` (marked block) | Specialists; `validate_report.py` |
| Domain sections per specialist, final-report sections | `REQUIRED_SECTIONS` block in each `.claude/agents/<name>.md` | That agent; `validate_report.py` |
| Reading item types, fields, section classes and critical classes | `methodology/READING_SCHEMAS.md` (`READING_SCHEMA` block) | Readers; `reading.py`, `validate_system.py` |
| Model and effort per agent, calibration status | `methodology/MODEL_POLICY.md` (`MODEL_POLICY` block) | Agent frontmatter; `validate_system.py`, `reading.py`, `reading_audit.py` |

The code holds **no copies** of these lists. Tests assert the expected canonical values, so an accidental edit to a marked block fails the test suite.

## 3. Claude Code configuration (verified against the installed 2.1.296)

| Item | Setting | Note |
|---|---|---|
| Agent location | `.claude/agents/<name>.md` | Frontmatter: `name`, `description`, `tools`, `model`, `effort`, `skills` |
| Model and reasoning effort | **Pinned per agent** (3.1.0) from `methodology/MODEL_POLICY.md`: CIO, ten specialists, auditor and critical-reader `opus` · `max`; reader and librarian `sonnet` · `high` | Owner decision after run 20261012T132311Z ran at *high* unnoticed. A frontmatter `effort:` overrides the session level (code.claude.com/docs/en/sub-agents, checked 2026-10-17); `validate_system.py` checks every agent against the policy. A run's `--effort` override is passed per invocation and recorded. Aliases, not version strings. |
| Specialist and auditor tools | `Read, Write, Edit, Bash, WebSearch, WebFetch` | No `Agent`, so they cannot spawn agents |
| Worker tools | reader, critical-reader: `Read, Write, Edit, Bash` (no web); librarian: `Read, Write, Bash, WebSearch, WebFetch` | Workers hold no views, write no claim ledger and cannot spawn agents |
| CIO tools | Inherited (main session) | Needs `Agent` to launch specialists |
| Shared context | `skills: [investment-constitution]` | Preloads the constitution into every specialist. The constitution also tells agents to read it, as a fallback. |
| Workflow | `.claude/skills/research-company/SKILL.md` with `disable-model-invocation: true` | Runs only when the user types it. Modes: full, `--validate-only [--probe]`, `--dry-run`, `--resume` |
| Permissions | `.claude/settings.json` allows WebSearch, WebFetch, `python3 scripts/*` | Reduces prompts for parallel background agents. Edits still follow the user's permission mode. |

**Effective model reporting:** the CIO records its own model ID only if its system context shows one. Per-subagent model IDs are not exposed to the parent at launch; `reading_audit.py run` reads them, with each agent's effort, from the agents' transcripts (`~/.claude/projects/<project>/<session>/subagents/`) and records them in `qc/READING_AUDIT.md`.

## 4. Enforcement matrix

| Requirement | Enforced by code | Enforced by instruction and CIO audit |
|---|---|---|
| Canonical layer names; no redefinition | `check_layer_names` (errors on TVS-style redefinition) | Constitution |
| Four-layer crosswalk in every specialist report | `check_crosswalk` | Agent definitions |
| FACT/MS/CALC/ESTIMATE cite existing claim IDs | `check_tags` + ledgers | Constitution §2 |
| Ledger completeness (source, locator, formula) | `validate_ledger` | `EVIDENCE_STANDARDS.md` |
| Scorecard arithmetic, gates, verdict mapping, layer rules | `validate_scorecard` | `SCORING.md` |
| Final report consistent with scorecard | `validate_final_report` | CIO protocol |
| Completion barrier (every specialist the run's version requires exists and validates) | `validate_run --stage specialists` | CIO Stage 2 |
| Method Coverage Checklist, depth standard, SME section (version-aware) | `validate_report.py` | Agent definitions |
| Independent audit run; every Critical/Major finding resolved; Critical findings Closed by a re-audit | `validate_run --stage final` (`validate_audit_report`, `check_audit_resolutions`) | CIO Stage 4 |
| Document map present (both channels cross-checked) | `validate_run --stage final` (2.4.0 runs) | CIO Stage 0 |
| Every in-scope page read once and recorded; critical chunks read twice and reconciled; no in-scope report silently missing | `reading.py plan` (fiscal-year window; refuses while an in-scope report is missing and unexplained), `reading.py check` (anchors in their passages, every number in every field printed there, receipts, VIEW REQUIRED pages viewed), `validate_run` (3.1.0: status complete, `COVERAGE.md` untouched, dossiers and packs built) | CIO Stage 0b |
| Readers really read every line; agents ran on their pinned model and effort; specialists read their packs | `reading_audit.py run` (from transcripts), `validate_run --stage final` | CIO Stage 4; auditor step 8 |
| No self-claimed reading coverage; the final report carries the generated coverage block | `check_no_coverage_claims`, `check_reading_coverage_block` | `EVIDENCE_STANDARDS.md` §2 |
| Pinned models and efforts; worker tool limits | `validate_system.py` against `MODEL_POLICY.md` | — |
| Scoreboard only for `complete` outcomes; no lost rows | `finalize_run.py` + `scoreboard.py` (lock, re-read, atomic replace, post-write verify, newer-run guard) | CIO Stage 4 |
| Incomplete-run policy (no manufactured scores) | `validate_scorecard` (null scores for insufficient evidence), `finalize_run.py` | `SCORING.md` §8 |
| Previous runs never overwritten; sortable UTC run IDs | `new_run.py` refusal; `validate_system.py` functional check | — |
| Git scoped to run artifacts; truthful messages; no force | `git_publish.py` | `PROJECT_INSTRUCTIONS.md` §6a |
| Agent and skill config, taxonomy, stale references, Antigravity remnants, secrets | `validate_system.py` | — |
| Flagged superlatives | Warnings (specialists), errors (final) | Constitution §4 |
| **Specialist independence (no cross-reading)** | — | Constitution §6, the attestation in each report header, CIO audit |
| **Specialists do not run git or write elsewhere** | — | Constitution §6 |
| Numbers in the report tie to their cited claims | `audit_tools.py tieout` (screen) | Auditor (every flagged row by hand) |
| Truth of a cited source or figure | — | CIO re-verification of ≥12 claims; the auditor's stratified re-verification sample (≥25 claims) |

The code verifies **structure and traceability**, and screens numbers against the ledgers. It cannot verify that a cited page says what the report claims. That is why the CIO's and the auditor's re-verification and recomputation steps are mandatory, and why every claim records its exact locator.

## 5. Run artifacts

See `methodology/REPORT_CONTRACTS.md` §1. Each run is self-contained and immutable once committed. `run_manifest.json` records identity, cutoff, the hurdle rate, the framework commit, the methodology version, model information and per-specialist invocation status, so a run can be interpreted later even after the methodology changes.

## 5a. Research data layer (v2.2; acquisition layer v2.4)

```text
NSE API + archives ─┐                       ┌─▶ _cache/index/exchange_index.csv (typed, period-labelled)
BSE API (HTTP/2) ───┼─ exchange_index.py ───┤
IR site (crawl) ────┤                       └─▶ corpus/index_summary.json
Internet Archive ───┘
                         document_map.py ──▶ downloads via fetch_source.py (netfetch: curl-first, validated,
FilingForge corpus ─────▶ (cross-check) ──▶   mirrors, archive fallback) ──▶ corpus/DOCUMENT_MAP.md
NSE XBRL / Integrated Filing ── xbrl_facts.py ──▶ calc/xbrl_facts.csv ──▶ reconcile vs. financial_history.csv
NSE bhavcopy ── market_data.py ──▶ price claim, ADTV and delivery, split-adjusted price history
core PDFs ── doc_text.py ──▶ _cache/text/<sha>/pages.md (page anchors, spreads split, tables from coordinates) + meta.json
NSE BRSR / voting / Integrated Filing ── structured_filings.py ──▶ corpus/structured/*.csv + corpus/STRUCTURED.md
text layers + filings ── reading.py plan ──▶ _cache/reading/ (passages, chunk files) ──▶ agent_driver.py reading (headless
   readers, one at a time by default: Sonnet; Opus for critical) ──▶ _cache/reading/parts/ ──▶ reading.py check
   ──▶ corpus/reading/extractions/*.jsonl ──▶ corpus/dossiers/ (topics, packs) + corpus/reading/COVERAGE.md
earlier runs' audited reading (same SHA-256) ── reading.py plan ──▶ copied extractions (recorded, re-verified)
agent and session transcripts ── reading_audit.py ──▶ qc/READING_AUDIT.md (models, efforts, lines received, pages viewed, packs read)
```


```text
sources ──fetch_source.py──▶ _cache/ (git-ignored) + source_retrievals.csv (SHA-256, status)
   │                                   │
   └──Read tool (PDF pages) / html_tables.py ──▶ workpapers (financial_history.csv, tables, logs)
                                                   │
                       fin_metrics.py ◀────────────┘           valuation_tools.py ◀── calc/*.json inputs
                             │                                        │
                             ▼                                        ▼
                ledgers (claim + metric key + locator)   ──▶  reconcile_numbers.py · evidence_stats.py
                                                                       │
                                                         CIO adjudication ─▶ scorecard (IA1/2/4 via price ladder)
```

- **Depth:** the Historical Depth Standard (`RESEARCH_PLAYBOOK.md` §2) is counted by `validate_report.py` in the relevant sections.
- **One number per fact:** the metric dictionary, cross-ledger reconciliation, and the audited financials dataset as the canonical numeric base.
- **Arithmetic by code:** formulas live in the scripts and the dictionary; tests check them against closed-form identities.

## 6. Verification performed at migration (2026-10-12)

| Check | Method | Result |
|---|---|---|
| Static system validation | `python3 scripts/validate_system.py` | 207 checks, 0 failed (v2.2). Covers agents, frontmatter keys, models, tools, skills, taxonomy, output paths, scorecard schema, scoreboard schema, run preservation, stale references, Antigravity remnants and credentials. |
| Unit and integration tests | `python3 -m unittest discover tests` | 62 tests pass (v2.2), including the metrics engine, the valuation identities, provenance tools, the numeric-conflict gate, depth enforcement and decision outputs. Earlier coverage: full synthetic runs (complete, qc_failed, insufficient_evidence), ledger, scorecard and report failure cases, 12 concurrent scoreboard writers losing no rows, scoped git batches in a throwaway repo (unrelated staged file untouched; push failure keeps the local commit), dry-run writing nothing, the legacy TVS regression |
| Live delegation probe | `validate_system.py --live-probe` (fresh headless Claude Code 2.1.296 session) | `bear-case` invoked via the native Agent tool and replied `PRELOADED=Y; PREFIX=BEAR; MODEL=claude-opus-5-5; AGENT_TOOL=N` |
| Parallel launch of all nine | Fresh headless session, nine Agent calls in one message | All nine returned their correct prefixes (FIN, FIL, MGT, IND, MOAT, CON, VAL, BEAR, SPS) with zero tool calls; all `claude-opus-5-5`; none has the Agent tool |
| `/research-company --validate-only --probe` | Fresh headless session through the skill | Ran the validator and tests, probed one specialist, wrote nothing |
| `/research-company --dry-run "TVS Motor Company Limited" TVSMOTOR NSE` | Fresh headless session | Printed the identity, the planned UTC run directory, the existing legacy run and the stages; `research/` unchanged |
| `/research-company TVSMOTOR` (missing identifiers) | Fresh headless session | Rejected with the required syntax; no run created |
| Legacy TVS layer redefinition | `check_layer_names` | 6 errors detected |

**Not verified:** a full production research run (deliberately not launched; the user chooses the first company). The quality of specialist research, CIO adjudication, and the Stage 2 and 4 git pushes in a real run will first be exercised then.

Headless sessions ignore `.claude/settings.json` permission rules until the workspace is trusted. Open Claude Code interactively in the repository once and accept the trust dialog.

## 7. Known limitations

- Independence is instruction-enforced. A hook-based read guard could enforce it technically; it was not added because a wrong hook would block legitimate CIO reads.
- Validators check structure and traceability; the auditor and the CIO's re-verification check semantic truth on samples, not on every claim.
- Exchange endpoints are unofficial and change without notice. `exchange_index.py` records every failing endpoint in `corpus/index_summary.json`, and the retrieval mechanics are documented with their verification date (`SOURCE_GUIDE.md` §6).
- The reading audit depends on Claude Code's local transcript files; if they are absent or their format changes, the audit reports *not measurable* and the run needs a recorded waiver, never a silent pass.
- Sonnet's parity with Opus on reading is established per section class by the bake-off (`docs/MODEL_CALIBRATION.md`); recall is measured against the adjudicated union of both reads, so an item both models miss is invisible to it. The auditor's per-run re-read of Sonnet pages is the backstop.
- Reading every page costs about 0.45–0.6M tokens per annual report (measured on BHARTIARTL FY2024–FY2026), roughly 4–6M per company over 10 years with transcripts and filings, most of it on Sonnet; while calibration is pending every chunk is also read by Opus.
- Exchange XBRL covers about FY2019 onward; earlier years rest on the annual-report PDFs (now retrievable from the exchanges back to the 2000s).
- Paywalled sources are recorded as missing, not reconstructed.
- Scoring calibration across companies starts empty. Calibration reviews begin once five or more companies are scored (`SCORING.md` §7).
