# Architecture

## 1. Roles and control flow

```mermaid
flowchart TD
    U["/research-company \"Name\" TICKER EXCHANGE"] --> CIO["CIO = main session<br/>(.claude/agents/cio.md)"]
    CIO --> P["Stage 0 Preflight<br/>identity check (name ↔ ticker ↔ exchange) · price CIO-C001<br/>new_run.py (UTC run id) · manifest.py · brief · source register"]
    P --> F1 & F2 & F3 & F4 & F5 & F6 & F7 & F8 & F9
    subgraph S1["Stage 1 — nine parallel Agent calls in one message, no cross-reading"]
      F1[financials] ; F2[filings] ; F3[management] ; F4[industry] ; F5[moat]
      F6[concalls] ; F7[valuation] ; F8[bear-case] ; F9[special-situations]
    end
    F1 & F2 & F3 & F4 & F5 & F6 & F7 & F8 & F9 --> B["Stage 2 barrier<br/>validate_run.py --stage specialists"]
    B -->|failures| R["targeted re-invocation (≤2)"] --> B
    B --> G1["git batch 1 (specialists) + push"]
    G1 --> A["Stage 3 adjudication<br/>read all · audit ≥12 claims · recompute ≥3 · contradiction log<br/>follow-ups · 4 independent layer assessments · classify<br/>bear-case attack on draft (if buy) · thesis-disproof · insufficient-evidence check · scorecard"]
    A --> Q["Stage 4 QC<br/>merge_ledgers · validate_run --stage final · quality_control.md"]
    Q --> FR["finalize_run.py<br/>complete → locked scoreboard upsert + latest_run.txt<br/>otherwise → manifest only"]
    FR --> G2["git batch 2 (final) + push — never force, never merge"]
```

**Why the CIO is the main session:** in Claude Code, subagents do not launch further subagents. A CIO running as a subagent could not orchestrate, and nesting would only add a layer of summarization. `/research-company` therefore turns the current session into the CIO, which loads `.claude/agents/cio.md` as its protocol. The same file works as a main-thread agent via `claude --agent cio`.

**Why parallel and independent:** the pre-migration system ran specialists in three dependent waves, and each specialist "reconciled" against the earlier reports. Errors spread instead of being caught (audit §4). Now all nine work from primary sources at the same time, and cross-examination is the CIO's job.

## 2. Single sources of truth

| Fact | Lives in | Consumed by |
|---|---|---|
| Layer names and definitions, fit scale, epistemic tags, claim-ID syntax, specialist protocol | `.claude/skills/investment-constitution/SKILL.md` (marked blocks) | Preloaded into every agent via `skills:` frontmatter; parsed by `scripts/research_lib.py` |
| BQ/IA dimensions, weights, gates, verdicts, valuation statuses, methodology version | `methodology/SCORING.md` (marked blocks) | CIO; `validate_scorecard.py` |
| Ledger columns, flagged phrases | `methodology/EVIDENCE_STANDARDS.md` (marked blocks) | All agents; `validate_ledger.py`, `validate_report.py` |
| Common report sections | `methodology/REPORT_CONTRACTS.md` (marked block) | Specialists; `validate_report.py` |
| Domain sections per specialist, final-report sections | `REQUIRED_SECTIONS` block in each `.claude/agents/<name>.md` | That agent; `validate_report.py` |

The code holds **no copies** of these lists. Tests assert the expected canonical values, so an accidental edit to a marked block fails the test suite.

## 3. Claude Code configuration (verified against the installed 2.1.296)

| Item | Setting | Note |
|---|---|---|
| Agent location | `.claude/agents/<name>.md` | Frontmatter: `name`, `description`, `tools`, `model`, `skills` |
| Model | `model: opus` on all ten agents | The alias resolves, in this installation, to the user's Opus model (`claude-opus-5-5` at migration time). No hard-coded version string. |
| Specialist tools | `Read, Write, Edit, Bash, WebSearch, WebFetch` | No `Agent`, so specialists cannot spawn agents |
| CIO tools | Inherited (main session) | Needs `Agent` to launch specialists |
| Shared context | `skills: [investment-constitution]` | Preloads the constitution into every specialist. The constitution also tells agents to read it, as a fallback. |
| Workflow | `.claude/skills/research-company/SKILL.md` with `disable-model-invocation: true` | Runs only when the user types it. Modes: full, `--validate-only [--probe]`, `--dry-run`, `--resume` |
| Permissions | `.claude/settings.json` allows WebSearch, WebFetch, `python3 scripts/*` | Reduces prompts for parallel background agents. Edits still follow the user's permission mode. |

**Effective model reporting:** the CIO records its own model ID only if its system context shows one. Per-subagent model IDs are not exposed to the parent, so the manifest records `opus alias (frontmatter); per-subagent ID not exposed` rather than inventing one.

## 4. Enforcement matrix

| Requirement | Enforced by code | Enforced by instruction and CIO audit |
|---|---|---|
| Canonical layer names; no redefinition | `check_layer_names` (errors on TVS-style redefinition) | Constitution |
| Four-layer crosswalk in every specialist report | `check_crosswalk` | Agent definitions |
| FACT/MS/CALC/ESTIMATE cite existing claim IDs | `check_tags` + ledgers | Constitution §2 |
| Ledger completeness (source, locator, formula) | `validate_ledger` | `EVIDENCE_STANDARDS.md` |
| Scorecard arithmetic, gates, verdict mapping, layer rules | `validate_scorecard` | `SCORING.md` |
| Final report consistent with scorecard | `validate_final_report` | CIO protocol |
| Completion barrier (all 9 exist and validate) | `validate_run --stage specialists` | CIO Stage 2 |
| Scoreboard only for `complete` outcomes; no lost rows | `finalize_run.py` + `scoreboard.py` (lock, re-read, atomic replace, post-write verify, newer-run guard) | CIO Stage 4 |
| Incomplete-run policy (no manufactured scores) | `validate_scorecard` (null scores for insufficient evidence), `finalize_run.py` | `SCORING.md` §8 |
| Previous runs never overwritten; sortable UTC run IDs | `new_run.py` refusal; `validate_system.py` functional check | — |
| Git scoped to run artifacts; truthful messages; no force | `git_publish.py` | `PROJECT_INSTRUCTIONS.md` §6a |
| Agent and skill config, taxonomy, stale references, Antigravity remnants, secrets | `validate_system.py` | — |
| Flagged superlatives | Warnings (specialists), errors (final) | Constitution §4 |
| **Specialist independence (no cross-reading)** | — | Constitution §6, the attestation in each report header, CIO audit |
| **Specialists do not run git or write elsewhere** | — | Constitution §6 |
| Truth of a cited source or figure | — | CIO re-verification of ≥12 claims; ledger confidence |

The code verifies **structure and traceability**. It cannot verify that a cited page says what the report claims. That is why the CIO's independent re-verification and recomputation steps are mandatory, and why every claim records its exact locator.

## 5. Run artifacts

See `methodology/REPORT_CONTRACTS.md` §1. Each run is self-contained and immutable once committed. `run_manifest.json` records identity, cutoff, the hurdle rate, the framework commit, the methodology version, model information and per-specialist invocation status, so a run can be interpreted later even after the methodology changes.

## 5a. Research data layer (v2.2)

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
- Validators check structure, not semantic truth.
- Research quality depends on which primary documents the web tools can retrieve. Paywalled or blocked sources are recorded as missing, not reconstructed.
- Scoring calibration across companies starts empty. Calibration reviews begin once five or more companies are scored (`SCORING.md` §7).
