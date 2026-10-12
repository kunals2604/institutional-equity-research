# Framework Change Log

## v2.1.0 — 2026-10-12 — Parts XI–XVI of the implementation brief

| # | Change | Reason |
|---|---|---|
| 1 | Run IDs are UTC and sortable (`YYYYMMDDTHHMMSSZ`); `manifest.json` → `run_manifest.json` with start and completion time, price and timestamp, model, status and status history; `qc_record.md` → `quality_control.md`; `LATEST_RUN.txt` → `latest_run.txt` (points only to the latest **complete** run) | Brief §28 |
| 2 | **Incomplete-run policy** (`SCORING.md` §8): outcomes complete / insufficient_evidence / qc_failed / failed; insufficient evidence issues **no** scores; `finalize_run.py` applies the policy | Brief §§28–29: no manufactured scores, no failed-run placeholders |
| 3 | Scoreboard reduced to 11 columns (identity, run metadata, `business_quality_score`, `investment_attractiveness_score`); locked, atomic, verified writes | Brief §29: a compact index, serialized updates |
| 4 | `/research-company "<Name>" <TICKER> <EXCHANGE>`, all three required and cross-validated; modes `--validate-only [--probe]`, `--dry-run`, `--resume` | Brief §30 |
| 5 | Final report restructured to sections A–L (Decision Dashboard … Final Verdict); each layer block has 12 required items including base rates and layer-fit confidence; the Final Verdict separates quality, fit, valuation, return, downside and confidence | Brief §31 |
| 6 | Git: two serialized, path-scoped batches with push to the current branch; no force or merge; truthful messages (`git_publish.py`) | Brief §32 |
| 7 | `validate_system.py` (static + optional live probe), `manifest.py`, `compare_runs.py`; source documents kept out of git (`_cache/`) | Brief §§28, 33 |
| 8 | Methodology version 2.0.0 → 2.1.0 | The outcome policy is part of scoring |


## v2.0.0 — 2026-10-12 — Claude Code migration

Methodology version `2.0.0` (`methodology/SCORING.md`). Evidence for each change: `docs/CLAUDE_CODE_MIGRATION_AUDIT.md`.

### Methodology
| # | Change | Reason |
|---|---|---|
| 1 | Canonical layer definitions moved to `.claude/skills/investment-constitution/SKILL.md`; exact names enforced by code | Layer 3's label drifted across five files; the TVS run renamed all four layers |
| 2 | Layer scores are now **layer-fit** scores on an anchored scale that **excludes price**; a separate current-price assessment is required for each layer with fit ≥ 41 | Layer scores had no anchors and mixed archetype fit with valuation (TVS "Layer 4 = valuation trap") |
| 3 | Primary-layer rules: fit ≥ 41 required; hybrid when within 10 points and both ≥ 61; "none compelling" is allowed | The framework allowed but never defined hybrid or none |
| 4 | **SME default-to-Layer-4 rule withdrawn**, replaced by SME Enhanced-Scrutiny Mode (all four layers, deeper governance and liquidity work, gate G5) | It contradicted analyze-before-classifying |
| 5 | §5 restructured: the comparative assessment is restored as its own section and SME mode moved to §4A | The comparative table was buried inside the SME block |
| 6 | §50's mixed weighted scorecard replaced by two separate scorecards (BQ1–BQ8, IA1–IA8) with fixed weights, anchors, gates, confidence and judgment bands | The mixed scorecard produced a third, undefined score (Bharti 75.73) |
| 7 | One canonical verdict list with a documented mapping and a one-notch override rule; SPECULATIVE BUY reserved for Layer-4-primary buys | Three different verdict lists existed; TVS used "REDUCE / SELL" |
| 8 | Valuation status vocabulary set to six levels | The framework and valuation agent used different scales |
| 9 | Claim-level evidence ledger, inline claim-ID citations, numerical controls, flagged-phrase list | 0 URLs and almost no locators across 20 legacy reports; inconsistent figures |
| 10 | Investor methods translated into 17 explicit tests mapped to layers and owners (`methodology/INVESTOR_LENSES.md`) | Make the lenses operational and stop name-dropping |
| 11 | Qualitative probability bands mandated when a percentage cannot be defended | Unsupported precise probabilities (for example an "80 %" court outcome) |
| 12 | Position sizing, pair trades and short calls are out of scope unless requested | The TVS report gave untested trading advice |

### System
| # | Change |
|---|---|
| 13 | Ten operative agents in `.claude/agents/`; Antigravity definitions archived as non-operative |
| 14 | Parallel independent Stage 1 replaces the three dependent waves; the CIO adjudicates in Stage 3 with mandatory re-verification and recomputation |
| 15 | Ownership overlaps removed (promise database → concalls; moat verdict → moat; SOTP arithmetic → valuation; value-realization → special-situations) |
| 16 | Per-run archive with manifest; QC-gated scoreboard; deterministic validators and tests |
| 17 | Legacy TVS and Bharti outputs moved to `runs/legacy-antigravity-v1/` with notices; excluded from the scoreboard |

### Preserved from v1
All investigation checklists in `MASTER_RESEARCH_FRAMEWORK.md` §§1–4, 6, 9–49, 51–52, 55–59 (wording updated only where it referenced withdrawn rules); the continuous-execution rule; the two-score principle and its interpretation examples; the six epistemic tags; and the strongest specialist tests (moat look-alikes, catalyst tiers, decoupled management pillars, hidden-assumption audit, reverse DCF expectation classes).
