# Framework Change Log

## v3.0.0 — 2026-10-18 — Fund-manager decision engine; acquisition, text and audit layers (includes the 2.4.0 contract)

**Decision engine (3.0.0, `SCORING.md` §§0, 1, 3a–3c, 5, 6).** The verdict is now reached the way an institutional fund manager reaches it, not by one fixed weighted average:

| # | Change |
|---|---|
| 1 | **Decision sequence** (§0): investability gates → classification → evidence quality per dimension → archetype must-pass tests → a margin of safety that scales with uncertainty → decision drivers → conviction → bounded judgment (one-notch override). The weighted scores summarize; they no longer decide alone. |
| 2 | **Weight profiles by primary layer, fixed in advance** (§3a): a compounder is weighted toward returns, moat, runway and the allocator; a grower toward runway, unit economics and the plausibility of implied growth; a cyclical or event toward trough survival, normalized value and the catalyst path; an option toward funding, governance and payoff asymmetry. A hybrid averages two profiles. The Base-profile score is still reported for cross-archetype comparison. |
| 3 | **Uncertainty is never rewarded** (§3b): every dimension carries its own confidence; a score above 50 is shrunk toward neutral by its confidence (High 1.0, Medium 0.85, Low 0.65); a low score is never raised. A dimension cannot be High when an owning specialist's evidence is thin (primary share < 0.50 or NOT_LOCATED > 0.15). |
| 4 | **Must-pass tests, non-compensatory** (§3c): for example, a compounder needs BQ1 ≥ 60 (returns above the cost of capital through the cycle) and an evidenced moat; a cyclical needs trough survival and a probable catalyst; every buy needs E[IRR] at least at the hurdle and acceptable governance. A failure caps the verdict (HOLD for business tests, WATCHLIST for price tests) without touching the scores. |
| 5 | **Required margin of safety by layer and confidence** (§5): from 0 % (a compounder at High confidence) to 50 % (an option at Low); no buy at Low confidence except Layer 4 speculation. |
| 6 | **Decision drivers and conviction**: 3–5 drivers (market-implied vs. our view, evidence, value at stake, signpost) are required; conviction (edge over the hurdle, asymmetry, confidence, robustness) gates STRONG BUY. |
| 7 | `build_scorecard.py` computes the price metrics at the verified price from the scenario inputs, runs the robustness grid, applies the whole sequence and records the **verdict path**; `validate_scorecard.py` recomputes it; `valuation_tools.py price-ladder` applies it at every price, so decision triggers respect every buy condition. Scorecards without `methodology_version` ≥ 3.0.0 keep the 2.x rules (the completed BHARTIARTL run re-validates unchanged). |

**Contract 2.4.0 (applies to every run from this version):**

| # | Change |
|---|---|
| 8 | **Stage-0 acquisition** (`exchange_index.py`, `document_map.py`): NSE (annual reports since ~FY2010, the full announcement history, results XBRL and integrated filings, shareholding, board meetings, corporate actions, PIT, SAST), BSE (annual reports since ~FY2002 over HTTP/2, announcements, scrip/ISIN lookup), the IR site and the Internet Archive are indexed; the core documents are downloaded once, validated and **cross-checked against the local FilingForge corpus** (page counts, content, period labels, duplicates). The first run's "pre-FY2017 annual reports unavailable" was a missing mechanism, not missing documents. |
| 9 | **Reliable transport** (`netfetch.py`): curl first (Python's LibreSSL 2.8.3 failed 3 of 12 parallel downloads in a test; curl 12 of 12), host request profiles, retries, payload validation (an "Access Denied" page saved as a PDF is now a failure), mirrors and archive fallback, safe ZIP unpacking. |
| 10 | **Exchange-grade data**: `xbrl_facts.py` (results XBRL to FY2024 and Integrated Filing tables from 2025, correcting NSE's mislabelled year-to-date contexts) with a reconciliation against the specialist's history; `market_data.py` (bhavcopy close, ADTV and delivery, split-adjusted long history). |
| 11 | **Text layer and the zero-loss rule** (`doc_text.py`, `RESEARCH_PLAYBOOK.md` §4): spreads split, prose in reading order, tables rebuilt from word coordinates (empty cells kept), page anchors, a section index, flags for pages that must be read visually (image-only, rotated, table mismatch, alignment, encoding); every decision-critical number confirmed with `verify` and on the rendered page. |
| 12 | **Scuttlebutt specialist** (ground truth: regulators' operating data, customers, pricing, channel, employees, competitors, digital signals; owner of lens T1, which the first run declared but never executed) and **independent auditor** (Stage 4: numeric tie-out, source re-verification sample, recomputation, scoring and process audit; every Critical/Major finding resolved, Critical ones Closed by a re-audit). `audit_tools.py` supports both the auditor and the CIO. |
| 13 | **Specialists upgraded**: every method extended (financials 22 steps: XBRL reconciliation, debt maturity ladder, tax, capex split, cost structure, minority leakage, quarterly inflections; filings 15: 10 annual reports in substance, secretarial audit, registered charges, restatements, disclosure quality; and so on), with new sections marked `(since 2.4.0)` so older runs keep their contract. |
| 14 | **SME enhanced scrutiny wired in**: every specialist definition has an SME section; the validator requires `SME Enhanced Scrutiny` in every report of an SME run. |
| 15 | **Effort follows the model picker**: no agent hard-codes `effort`; the validator rejects one. |
| 16 | New depth minimums (2.4.0): filings 10 annual-report years, moat 10 years, special situations 10 years, scuttlebutt 5 years of independent operating data. Ground-truth sources added to all 18 sector playbooks. |

## v2.3.0 — 2026-10-17 — Lessons from the first full run (BHARTIARTL)

| # | Change |
|---|---|
| 1 | **Method Coverage Checklist** in every specialist report: one row per numbered step of the agent's `## Method`, each Done / Partial / Not available / Not applicable with where it is covered and, if not done, what was tried. Validator-enforced (missing rows or statuses are errors). It makes coverage gaps visible, so they can be closed rather than discovered by the reader. |
| 2 | **Gap-closure loop** (CIO Stage 2): every Partial / Not available step and every material missing-evidence item goes into `cio/gap_register.md`, is classified closable or irreducible, and closable gaps are sent back to the owning specialist before synthesis. |
| 3 | **CIO compiles first, scores last:** Stage 3 is a fixed order: audit, contradiction log, follow-ups, **CIO independent analysis** (`cio/cio_analysis.md`: own reconstruction of the key numbers, base-rate check, cross-specialist tensions, what the specialists missed, the CIO's own view), then synthesis, layers and thesis disproof, and only then scoring. New report sections: CIO Independent Analysis and Confidence Assessment. |
| 4 | **Deterministic scoring:** `build_scorecard.py` computes the scorecard from the CIO's judgments; `score_guides.py` computes the BQ1/BQ4/BQ5 guide bands. Single rounding rule: round half up (`research_lib.round_half_up`), in the builder, the validator and the price ladder. |
| 5 | **Confidence criteria (SCORING.md §4):** High is the target and is earned by (a) ≥ 75 % tier 1–3 evidence, reconciled; (b) no unresolved material contradiction; (c) the gap-closure loop done; (d) robustness: the IA verdict is stable on the `valuation_tools.py robustness` grid (value ±15 %, probabilities ±10 pp, hurdle ±1 pp) and each BQ dimension stays in its anchor band under the plausible alternative. The report separates closable from irreducible uncertainty. |
| 6 | **IA4 hurdle-adjusted:** asymmetry is measured against the price compounded at the hurdle over the horizon, not today's price (it was a documented CIO deviation in the BHARTIARTL run; now native). `scenario-build` and `event_uplifts` replace the run-specific scripts. |
| 7 | **Sequential specialists by default** (`--parallel` optional): each specialist finishes and is validated before the next starts, with a `progress.md` checkpoint. Interruptions never justify reduced depth. |
| 8 | **Robust retrieval:** `fetch_source.py` retries transient failures, falls back to curl (41 of 52 failed downloads in the first run were transient TLS errors under parallel load) and reuses documents already downloaded in the run. `corpus.py` recognises call transcripts whose headline lacks the word "transcript". |
| 9 | **Version-aware, read-only re-validation:** `validate_run.py` judges a run by the contract of the methodology version in its manifest (the 2.3.0 checklist, sections and CIO files are not required of older runs), and never writes into a finalized run (`complete` or `insufficient_evidence`). The BHARTIARTL 2.2.0 run still passes, unchanged. |

## v2.2.2 — 2026-10-12 — Local corpus and web research at par; breadth floors

| # | Change |
|---|---|
| 1 | **Two channels at par:** the FilingForge corpus is no longer "read first, then fill gaps from the web". Specialists use it **and** run full web research regardless of corpus coverage, because a library can be incomplete or contain download glitches. Absence in the corpus is not absence of evidence; decision-critical corpus numbers are cross-checked against the exchange or IR original; suspected corpus defects are logged. (`SOURCE_GUIDE.md` §0, `RESEARCH_PLAYBOOK.md`, constitution §6, `cio.md`, `CATALOG.md` header.) |
| 2 | **Breadth counts are floors, not ceilings:** peers "3–6" became "all relevant (at least 3)"; macro drivers "3–6" became "every driver that matters"; moat competitors "2–3" became "at least 2, more where relevant"; competitor benchmarking runs over 10 years. |
| 3 | **No retry cap:** the CIO re-invokes a failing specialist while the failures are fixable, instead of stopping at 2 retries. |

## v2.2.1 — 2026-10-12 — Local filing corpus, owner policy

| # | Change |
|---|---|
| 1 | **FilingForge integration:** `scripts/corpus.py` (status, catalog with SHA-256 and coverage, cross-year search, PDF page `locate` via poppler, page-marked text). The CIO catalogs the local library in Stage 0 (and asks once if the company is missing). Specialists read the Markdown first (about 25× fewer tokens), cite `FilingForge:<doc_id>` with PDF pages, and fill gaps from the web. Config: `config/data_sources.json`; the library is granted as an additional readable directory in `.claude/settings.json`. |
| 2 | **Owner policy:** no position or risk limits; the hurdle is no longer a fixed 12 % but **derived each run** from the cited cost of equity (`valuation_tools.py wacc`). It is only the yardstick for IA2, never a research limit. The policy is marked confirmed. |
| 3 | **No length limits:** removed "typical 3,000–9,000 words"; depth standards are floors, not ceilings. |
| 4 | poppler installed (`pdftotext`, `pdfinfo`) for page-accurate citations from PDFs. |


## v2.2.0 — 2026-10-12 — Institutional review (`docs/INSTITUTIONAL_REVIEW.md`)

| # | Change |
|---|---|
| 1 | **Historical Depth Standard** (at least 10 FY financials, 12 quarters of calls, 10 years of valuation and industry history, 12 quarters of shareholding), validator-enforced, with `coverage_exception`; a Data Coverage section is required in every specialist report; `coverage` recorded in the scorecard |
| 2 | `methodology/RESEARCH_PLAYBOOK.md` (operating procedure, verification sampling plan, context discipline), `SOURCE_GUIDE.md`, `SECTOR_PLAYBOOKS.md` (18 sectors), `METRIC_DEFINITIONS.md` (151 metric keys) |
| 3 | Ledger gains a `metric` column (required for quantitative claims); evidence thresholds; the WebFetch rule; document provenance via SHA-256 |
| 4 | Scripts: `fetch_source.py`, `html_tables.py`, `fin_metrics.py`, `valuation_tools.py`, `evidence_stats.py`, `reconcile_numbers.py`; the final QC fails on unadjudicated numeric conflicts |
| 5 | Scoring 2.2.0: quantitative guides for BQ1/BQ3/BQ4/BQ5; deterministic IA1/IA2/IA4 via the price ladder; a layer-specific IA interpretation table; investment policy inputs and the position-risk profile (§9); decision outputs: triggers, predictions, review date (§10); forecast calibration |
| 6 | `config/investment_policy.json` (IPS) snapshotted into every run |
| 7 | CIO: variant perception and key debates, a canonical numeric base, symmetric adversarial review, decision triggers, the position-risk profile, falsifiable predictions, prior-prediction resolution; the final report gains three sections |
| 8 | Specialists: minimum evidence sets; new sections (segment economics, forensic screens, rating history, ESG risks, promoter structure, macro sensitivities, quantified moat metrics, analyst concerns, liquidity, drawdowns and TSR, return decomposition, price ladder, pre-mortem, short-seller search, event calendar); ownership gaps closed |


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
