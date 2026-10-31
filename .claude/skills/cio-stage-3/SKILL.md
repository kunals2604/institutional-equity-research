---
name: cio-stage-3
description: The CIO's Stage 3: the synthesis pipeline, contradictions, the decision and the sections. Load it when `python3 scripts/orchestrate.py next` names it.
---

## Stage 3 — Synthesis first, then scores (methodology 3.2.0: the synthesis pipeline)

`python3 scripts/manifest.py RUN_DIR status synthesis`

The CIO is the final analyst, not a summariser, and the final report must rest on **all** the evidence the run produced
(`methodology/SYNTHESIS.md`). No single context can hold ten or eleven reports, their ledgers and the reading or digest
items, so the evidence goes through a pipeline in which every item has a recorded fate, and the CIO decides from what
the pipeline returns. Runs of methodology 3.1.0 or earlier keep the single-context Stage 3 of their version.

The order is fixed: **evidence** (registry, themes) → **contradictions and follow-ups** → **CIO independent work** →
**layers and written synthesis** → **scores** → **confidence test** → **adversarial challenge** → **decision outputs** →
**sections and assembly**. No score is drafted before step 10.

1. **Registry and numeric base.**
   - `python3 scripts/merge_ledgers.py RUN_DIR`, `python3 scripts/reconcile_numbers.py RUN_DIR`,
     `python3 scripts/evidence_stats.py RUN_DIR`, `python3 scripts/claim_graph.py build RUN_DIR`.
   - `python3 scripts/agent_driver.py synthesis RUN_DIR --step registry` (`synthesis/REGISTRY.md`: every finding,
     claim, conflict, reading or digest item and event, its theme and materiality; the theme slices).
   - After auditing the financials dataset (step 3), adopt it as the run's **canonical numeric base**.
2. **Theme analysts.** `python3 scripts/agent_driver.py synthesis RUN_DIR --step themes` in the background (one Opus
   session per theme, or per part of a large theme then a reduce session; each writes `synthesis/themes/<T>.md`: integrated
   findings, correlated sources, contradiction candidates, numbers of record, dimension evidence, layer implications,
   follow-up requests, and a disposition for **every** item of its slice, checked by `synthesis.py check-theme`).
   Then `python3 scripts/synthesis.py followups RUN_DIR` and `python3 scripts/synthesis.py packet RUN_DIR`. Read
   `synthesis/CIO_PACKET.md` in full (it is bounded); open the briefs and reports wherever it is not enough. Read every
   `immaterial` disposition it lists: none may hide a finding.
3. **Independent audit.**
   - **Re-verify at least 12** decision-critical claims from primary sources. Always include: price; share count; the key return metric; the largest growth figure; net debt; the largest contingency; key valuation inputs (risk-free rate, ERP, beta, base revenue, net debt, minorities); anything that drives a layer-fit score.
   - Record them in `cio_ledger.csv` with `corroborated_by` / `contradicted_by`.
   - **Recompute at least 3** important calculations by re-running the scripts on the cited inputs, and confirm the outputs match. Examples: `fin_metrics.py` on the history; `valuation_tools.py wacc`, `dcf`, `residual-income` and `scenario-irr` on the valuation inputs; `forecast_tools.py model` on the forecasting drivers.
   - **Check that the base case is complete.** Does it carry the evidenced recurring events (price rounds, capacity additions, regulatory schedules)? Is its capital intensity consistent with history?
4. **Correlated-evidence check.** The theme briefs list where specialists agree because they share a source; confirm the decision-relevant ones. Shared-source agreement counts as one piece of evidence.
5. **Contradiction log** (`cio/contradiction_log.md`). Every contradiction candidate of the theme briefs (`CC-…`, by its id), every numeric conflict, and every disagreement between a specialist and your audit, each with:
   - issue ID (and the `CC-…` id) and the question;
   - each position, with its report and claim IDs;
   - evidence for each, and contrary evidence;
   - assumptions;
   - **your independent check** (CIO claim IDs);
   - the resolution and its method, or **Unresolved**;
   - confidence and investment impact.

   No midpoints without a stated method. Use the template's labelled fields: `synthesis.py followups` counts a candidate as adjudicated only when its entry has them filled, with a CIO claim in the independent check. **Unresolved** is a valid resolution; a mention is not.
6. **Targeted follow-ups.** For each follow-up request of the briefs (`FU-…`) and each material unresolved question that domain research could settle, re-invoke the relevant specialist with a narrow question and the specific peer claims or paths to examine: `python3 scripts/agent_driver.py followup RUN_DIR <name> --stage 3 --purpose "<issue id>" --message-file <file> --output specialists/<name>_followup_<n>.md`. A Stage-3 follow-up is cross-examination after the independent work is filed: it runs in a fresh session that may read the other specialists' files and the synthesis briefs (never `cio/` or `audit/`), and it never resumes the specialist's independent session.
   - **Valuation on the forecast (methodology 3.2.0):** run `python3 scripts/forecast_tools.py reconcile --forecast RUN_DIR/calc/forecasting_model.json --valuation <valuation's dcf or residual-income inputs> --out RUN_DIR/calc/forecasting_reconcile.json`, then a valuation follow-up that values the company on the forecasting specialist's base path (`calc/forecasting_to_valuation.json`) beside its own, and explains every gap above the thresholds.
   - Then `python3 scripts/agent_driver.py synthesis RUN_DIR --step registry` and `--step themes` again: only the themes whose items changed run (the check names the new ids), and every `needs_follow_up` disposition is closed.
7. **CIO independent analysis** (`cio/cio_analysis.md`; summarised in the report section of the same name). This is the CIO's own work beyond the specialists. All of it is required, and every number comes from code in `calc/cio_*`.
   1. **Primary reading.** Read the latest annual report's chairman's/MD letter and MD&A, and the Q&A of the latest two earnings calls, yourself. Record what changes your view.
   2. **Independent valuation cross-check** by a method different from valuation's primary one. Examples: owner-earnings or FCF yield against the hurdle; EV/(EBITDA − capex) against its own history; a reverse DCF on a different driver; a justified P/B for a lender; a peer-relative value. State whether it confirms or contradicts valuation's range, and why.
   3. **Peer and consensus cross-check.** Place the company against its closest peers on growth, returns, leverage and multiples (the forecasting specialist's peer table), and against consensus (tagged ESTIMATE).
   4. **Quantitative score guides.** Run `python3 scripts/score_guides.py`, which gives the BQ1, BQ4 and BQ5 guide inputs from `financials_metrics.csv` and the run's WACC.
   5. **What the specialists missed or under-weighted.** At least three items, each with evidence. Examples: a base case without a recurring event; a capital-intensity assumption out of line with history; a risk no domain owned.
8. **Layers, then the written synthesis, before any score.**
   - **Layer analysts:** `python3 scripts/agent_driver.py synthesis RUN_DIR --step layers` (one Opus session per layer, independent of each other, from every crosswalk row for that layer and every brief's layer implications; each writes `synthesis/layers/<L>_draft.md` with the layer block and a proposed fit, checked by `synthesis.py check-layer`). It refuses to start while the registry is stale, a theme fails its check, a contradiction candidate is not adjudicated or a follow-up is open. Run `python3 scripts/synthesis.py packet RUN_DIR` again afterwards, so the packet carries the layer proposals. Read all four drafts. The final layer fits and the classification are yours; a final fit more than 10 points from the proposal states the deviation and its reason in the layer's block.
   - **Your sections** (`cio/sections/*.md`, one H2 per report section, citing claim IDs): **Key Debates and Variant Perception**, the **Layer Classification**, the **Thesis-Disproof Exercise** and **CIO Independent Analysis**, from steps 1–7 and the layer drafts.

   **Variant perception** must cover:
   - (a) the **consensus view** and where it comes from: sell-side estimates (ESTIMATE), market-implied expectations from the reverse DCF, recurring analyst concerns from concalls; and the ground truth (scuttlebutt) that confirms or contradicts it, with the leading indicators that run ahead of the reported numbers;
   - (b) **our view**;
   - (c) **why we differ**, with evidence;
   - (d) **when and how the difference resolves**, with the signpost and its date.

   If there is no variant perception, say so; any edge must then come from price alone. Then list the **3–5 key debates**.

   **Layer classification.** Classify only after reading the four independent layer drafts; say why each other layer is less applicable.

   **Thesis-disproof exercise.** Answer each question explicitly:
    1. What is the strongest argument against the investment?
    2. Which assumptions does the market price appear to require?
    3. What would permanently damage intrinsic value per share?
    4. What evidence would disprove the primary layer classification?
    5. What evidence would invalidate the bull case?
    6. What could cause several risks to materialize at once?
    7. What has this research failed to establish?
    8. Which conclusion would change first if the next two reporting periods disappoint?
    9. What would an exceptionally skeptical investor demand before committing capital?
9. **Insufficient-evidence check** (`SCORING.md` §8). If any trigger holds, set `assessment_status: insufficient_evidence` with the reason, leave the BQ/IA finals and the verdict `null`, and say so plainly. Do not manufacture scores.
10. **Decide the way a fund manager does, then score** (`methodology/SCORING.md` §0: the scores summarize; the decision sequence decides):
    - **Classification first.** The primary layer (and any hybrid) comes from the layer assessments in step 8, never from the scores. It selects the weight profile and the must-pass tests, so defend it there.
    - **Score each dimension from its evidence**, starting from its **quantitative guide** (BQ guides from `score_guides.py`; IA1, IA2 and IA4 from `valuation_tools.py price-ladder` on scenario inputs built with `valuation_tools.py scenario-build`). Each rationale cites the synthesis evidence and states any deviation from the guide with its reason.
    - **Give every dimension its own confidence** (High / Medium / Low, by the §4 criteria applied to that dimension's evidence). Weak evidence shrinks a high score toward neutral and never raises a low one; the builder caps a dimension at Medium when an owning specialist's evidence is thin.
    - **Write the 3–5 decision drivers** (`decision_drivers`): driver · what the price implies (reverse DCF) · our view · the evidence (claim IDs) and its confidence · the value at stake per share across the plausible range (from the valuation sensitivity) · the signpost and its date. If no driver differs from the market, say so: the edge then comes from price alone.
    - Put the judgments in `cio/scorecard_inputs.json`, with `"scenario_inputs": "calc/<scenario-build inputs>.json"`, then run `python3 scripts/build_scorecard.py RUN_DIR`. It computes the price metrics at the verified price, the robustness flag, the weight profile, the effective scores, the gates, the must-pass tests, the required margin of safety, conviction and the mapped verdict, then validates. Read its verdict path: a failed must-pass test or a margin of safety below the table's figure is a finding to weigh and explain in the report, not a number to adjust.
    - Never reverse-engineer dimension scores, confidences or the classification to reach a desired verdict.
    - **Then write the verdict: it is your judgment across all the research (`SCORING.md` §0, from 4.0.0).** In `cio/scorecard_inputs.json` set `verdict`, and `verdict_reasoning` with `for`, `against` and `judgment`, each citing claims: weigh the whole picture, not the tables. No gate, must-pass test or margin-of-safety figure sets or caps it: each one is a flag to weigh and explain. If your verdict leaves the computed guide, say why in `guide_departure`. Set the price levels at which your view would change yourself; the ladder is an input to them. `build_scorecard.py` computes the guide and never touches your verdict.
11. **Confidence assessment** (`SCORING.md` §4).
    - Run `python3 scripts/valuation_tools.py robustness --inputs <scenario-build inputs> --scorecard RUN_DIR/cio/scorecard.json`.
    - Check each High criterion for BQ and for IA.
    - **If either is below High**, return to step 6 or Stage 2 step 4 for every closable gap behind it, then re-score.
    - Report the residual as **closable but unobtainable** (with the attempt log) vs. **irreducible** (forecast, competitor conduct, rate regime).
    - **Never raise confidence by assertion.**
12. **Adversarial review (symmetric).**
    - **When:** whenever the draft mapped verdict is **BUY, STRONG BUY, SPECULATIVE BUY, AVOID or STRONG AVOID**, or whenever the verdict changes from a prior complete run.
    - **How:** re-invoke `bear-case` with your **draft conclusion** (not the specialist reports) for a targeted attack: put the draft conclusion in a file and run `agent_driver.py followup RUN_DIR bear-case --stage 3 --purpose "adversarial review of the draft" --message-file <file> --output specialists/bear-case_followup_<n>.md`. It attacks in whichever direction the draft points; errors of omission (wrongly avoiding a great opportunity) cost money as errors of commission do.
    - **After:** adjudicate every challenge in the contradiction log, re-score if any input changes (rebuild the scorecard), and re-run the confidence test.
13. **Decision outputs** (`SCORING.md` §§9–10).
    - **Decision triggers:** `python3 scripts/valuation_tools.py price-ladder --inputs <scenario inputs> --scorecard RUN_DIR/cio/scorecard.json --range <lo:hi:step> --out RUN_DIR/calc/cio_price_ladder.json`. Record `buy_below`, `strong_buy_below` and `avoid_above`, and note IA5's price sensitivity.
    - **Position-risk profile:** `valuation_tools.py sizing-ceiling` (bear value including dividends, ADTV, speculative flag), plus 2–4 factor exposures from industry's macro sensitivities.
    - **Falsifiable predictions:** 3–7 dated, measurable predictions with probabilities between 0.05 and 0.95, tied to the key debates, each in its **resolvable form** (`SCORING.md` §10): `metric`, `comparator` (`>=`, `<=`, `>`, `<`, `between`, or `event` with its `resolution_rule`), `threshold`, `unit`, `period` and `resolution_source` (`price` predictions are resolved by script from exchange closes; the others by you at the next run, with evidence).
    - **Next review date:** within 12 months; earlier if a calendar event (special-situations' event calendar) could change the verdict; on or after the due date of at least one prediction, so the review resolves something.
    - **Calibration record:** read the generated section of `docs/CALIBRATION_LOG.md` (`outcomes.py score`) before setting probabilities and confidence: if your stated probabilities have come true less often than stated, state lower ones (`SCORING.md` §10).
14. **Change analysis** (if a prior complete run exists).
    - Run `python3 scripts/compare_runs.py <prior RUN_DIR> RUN_DIR`.
    - Explain each material change with the evidence that caused it.
    - **Resolve every prior prediction that has fallen due** (`python3 scripts/outcomes.py due --ticker <T> --cutoff <cutoff>`): record each as hit, miss or void with its evidence, a claim ID of this run or the source (`outcomes.py record <RUN_ID> <PID> hit|miss|void --actual <value> --evidence <...>`); `validate_run.py --stage final` fails while one is unresolved. In **Change Since Prior Run**, name the prior run and say how its decision turned out (its verdict and price against the price now, and its triggers).
15. **Sections and assembly.**
    - `scorecard_inputs.json` carries **`key_quantities`**: every number the decision rests on (price, value range, E[IRR], the permanent-loss band, the decisive operating metrics), each with `label`, `aliases`, `value` and `claim_ids`; every line of the report that names one must state it alike (`synthesis.py integration` checks it).
    - **Section writers:** `python3 scripts/agent_driver.py synthesis RUN_DIR --step writers` (Opus, one per section group: the evidence sections from the briefs, the layer drafts and your adjudications, each with a Not Carried table; checked by `synthesis.py check-section`).
    - **Your remaining sections** in `cio/sections/`: Decision Dashboard, Executive Investment Thesis, the two scorecards, Confidence Assessment, Position-Risk Profile and Decision Triggers, Independent Audit and Resolutions (Stage 4), Falsifiable Predictions and Review Schedule, Final Verdict, Change Since Prior Run and Sources.
    - `python3 scripts/synthesis.py assemble RUN_DIR` builds `cio/final_report.md`: the front matter from the scorecard, every section in the contract's order, the coverage record, and the generated **Evidence Integration Register**. The report is a build artifact: edit the section files and assemble again. Then `python3 scripts/synthesis.py integration RUN_DIR` and fix every error (a gating finding that never reaches the body, a contradiction candidate not adjudicated, a dimension not resting on its owners' evidence, a key quantity stated two ways, a tie-out mismatch).
