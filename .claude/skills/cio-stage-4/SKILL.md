---
name: cio-stage-4
description: The CIO's Stage 4: reading audit, independent audit, QC, finalization, git, and the final report contract. Load it when `python3 scripts/orchestrate.py next` names it.
---

## Stage 4 — Independent audit, QC, finalization, git batch 2

0. **Reading audit.** `python3 scripts/reading_audit.py run RUN_DIR` checks, from the agents' own transcripts, that every
   agent ran on its pinned model and effort (the CIO session included), that every specialist read its pack (over all
   of its sessions: `corpus/dossiers/packs/` with reading on, `corpus/digest/packs/` with reading off), and that every
   specialist's independent work (Stages 1 and 2) touched no other specialist's work, nor `synthesis/`, `cio/`,
   `audit/`, another run or the archive (`INDEPENDENCE` errors, from the transcripts and the engine's fingerprints).
   With reading on it also checks that every reader received every line of its chunks and opened every VIEW REQUIRED
   page. Fix every failure before the audit: re-run the engine for a reader's chunks, re-invoke a specialist to read the
   pack it skipped (and revise its report if it changes anything), re-run a specialist whose independence was
   breached from a clean start (or record exactly what it saw and why its conclusions stand), or record a model or
   effort deviation as an accepted limitation. If no transcript can be found, run it with `--waive "<reason>"` and
   disclose the waiver in the report.
1. **Independent audit** (`.claude/agents/auditor.md`). The draft final report and the scorecard must be complete
   (methodology 3.2.0: assembled by `synthesis.py assemble`, with `synthesis.py integration` free of errors). The
   auditor's Evidence Integration Audit reviews every uncited Key Finding and material item, samples the report's
   restatements against the specialists' own sentences, and reviews the tie-out exceptions.
   1. `python3 scripts/merge_ledgers.py RUN_DIR`, then `python3 scripts/manifest.py RUN_DIR invocation auditor --stage 4 --purpose "independent audit of the draft"`.
   2. Write the auditor's prompt to a file: the identity block, `RUN_DIR`, the cutoff, the price claim, and "Audit cio/final_report.md and cio/scorecard.json per your definition. Write only under RUN_DIR/audit/." Do not tell it your concerns or the conclusion you want; it reads the files itself. Run `python3 scripts/agent_driver.py audit RUN_DIR --message-file <file>` in the background (a fresh headless session on its pinned model and effort, writes confined to `audit/`). Without the CLI, invoke the `auditor` agent (description `auditor <RUN_ID>`) with the same text.
   3. The engine validates its report (`validate_report.py RUN_DIR/audit/audit_report.md --kind audit --run RUN_DIR`) and resumes it with the errors until it passes; run the validator yourself to confirm.
   4. **Resolve every finding** in `cio/audit_resolutions.md`: **Fixed** (say what changed: a section file and the re-assembled report, scorecard inputs, ledger or calculation) or **Rebutted** (with the evidence and claim IDs); **Accepted limitation** only for Major or Minor findings, disclosed in the report's limitations. If a fix changes any score input, rebuild the scorecard (`build_scorecard.py`), re-run `robustness` and the price ladder, and update the report. When a claim is corrected, `python3 scripts/claim_graph.py down RUN_DIR <ID>` lists everything built on it: review each of your own claims and scorecard inputs among them and record it in `cio/propagation.csv` (`claim,dependent,action,reason`; `verify.py run` fails on any not recorded).
   5. **Re-audit** whenever a Critical finding existed: `python3 scripts/agent_driver.py followup RUN_DIR auditor --stage 4 --purpose "re-audit" --message-file <file> --output audit/audit_followup_<n>.md` (or SendMessage without the CLI) to verify the resolutions. It writes `audit/audit_followup_<n>.md` and must mark every Critical finding **Closed**. Repeat until it does.
   6. Add the report section **Independent Audit and Resolutions** (`cio/sections/`, then `synthesis.py assemble`): the opinion, the findings by severity, how each Critical and Major finding was resolved, and the re-audit result.
2. `python3 scripts/merge_ledgers.py RUN_DIR`, then `python3 scripts/verify.py run RUN_DIR --stage final` (a finding it leaves open that was not open before makes the registry stale: run `synthesis.py registry` and the themes step on it): every
   specialist again (after the follow-ups), the reading audit, the audit's resolutions, and **your own ledger**
   against what your session read (a CIO FACT value never seen in a source, a cited source never opened). Fix every
   blocking finding in your outputs; waive only with a reason that does not touch a decision-critical claim.
3. `python3 scripts/validate_run.py RUN_DIR --stage final` writes `qc/auto_checks.json` and `qc/evidence_stats.json`, and **fails on any unadjudicated numeric conflict**, on any unresolved Critical or Major audit finding, on a verification that did not pass, on a reading audit that did not pass (or was not waived with a reason), on a final report whose coverage block differs from the run's coverage record (`corpus/reading/COVERAGE.md` with reading on, `corpus/digest/COVERAGE.md` with reading off), and, from methodology 3.2.0, on every `synthesis.py integration` error (stale registry, an item without a disposition, a gating finding that never reaches the report's body, a material finding in neither the body nor the Evidence Integration Register, a contradiction candidate missing from the log, a dimension not resting on its owners' evidence, a key quantity stated two ways, an unexplained tie-out mismatch, a consistency rule broken). Fix errors in your outputs. Errors in a specialist report mean a re-invocation, or an accepted limitation recorded with its reason.
4. Complete `cio/quality_control.md`: the automated results, the evidence statistics, the manual checklist below, the cross-company calibration comparison (`SCORING.md` §7), accepted limitations, and the line **`QC status: PASS`** or **`QC status: FAIL`**. PASS requires zero automated errors and every manual check satisfied or waived with a reason that does not touch a decision-critical claim.
5. Set `qc_status` in `scorecard.json` and in the final-report front matter to match. Re-run step 3 if anything changed.
6. `python3 scripts/finalize_run.py RUN_DIR` applies the outcome policy. Only a `complete` outcome upserts the scoreboard (locked, atomic, verified), moves `latest_run.txt` and records the decision and its predictions for the outcome loop (`research/outcomes/`; `outcomes.py watch` then tells the owner when a price trigger, the review date or a due prediction calls for a re-run). Stage the `research/outcomes/` files in the final git batch.
7. **Git batch 2:** `python3 scripts/git_publish.py RUN_DIR --batch final --push`. If the push fails, report it; the artifacts stay committed locally.
8. **Completion summary** for the user (concise): outcome; verdict; BQ and IA with confidence; primary and secondary layers; price and as-of date; variant perception in one sentence; decision triggers; the three most decision-relevant findings; the largest unresolved uncertainty; data coverage achieved (document map); the audit opinion and how its findings were resolved; the reading mode and its coverage (reading on: pages read, repeat, structured, out of scope; reading off: documents digested, items page-confirmed and leads) and the reading-audit result; evidence integration (per-specialist uptake, items not carried and why), including the models and efforts the agents actually ran on; QC status; commit SHAs and push status; paths to `final_report.md` and `scorecard.json`.

### Manual QC checklist (record each item in quality_control.md)
- Layer names are canonical everywhere; each layer was assessed separately with a fit score that excludes price.
- The Historical Depth Standard was met by every specialist, or each exception is justified.
- At least 12 decision-critical claims were re-verified and at least 3 calculations were recomputed by re-running the scripts.
- Every `reconcile_numbers.py` conflict is adjudicated; one cost-of-capital set is used throughout; price and share count reconcile with market cap and EV.
- Standalone and consolidated bases, and FY and TTM figures, are labeled consistently.
- The contradiction log is complete; every resolution has an independent check.
- The evidence-statistics thresholds are met, or each breach is explained; confidence levels are consistent with them.
- No FACT rests only on tier 6–7 sources; no probability lacks a basis or band.
- BQ was judged without price; IA was not derived from BQ; IA1, IA2 and IA4 match the price ladder (or the deviation is explained).
- The variant perception, key debates, thesis-disproof questions, decision triggers, position risk, predictions and review date are all present.
- The symmetric adversarial review ran when required.
- Specialists ran in the recorded execution mode; every interruption and resume is logged; no specialist was asked to cut depth.
- Every Method Coverage Checklist gap is in `cio/gap_register.md` with its closure attempt or unobtainability evidence.
- `cio/cio_analysis.md` contains the CIO's own reading, an independent valuation cross-check, a peer/consensus cross-check and at least three items the specialists missed.
- The synthesis sections were written before the scorecard; every dimension rationale cites the synthesis; the scorecard was built with `build_scorecard.py` (methodology 3.2.0: with `key_quantities`, stated alike everywhere in the report).
- The Confidence Assessment applies `SCORING.md` §4 criterion by criterion, with the `robustness` output; confidence was not raised by assertion.
- The document map was built from both channels; every `missing` core document was searched for; every cross-check flag was handled (which copy was used, and the local defect reported).
- The price is the exchange close (bhavcopy) with its URL and SHA-256; ADTV and the price history come from exchange data or are verified against it.
- The independent audit ran; every Critical and Major finding is resolved in `cio/audit_resolutions.md`; every Critical finding is Closed by a re-audit; the report's Independent Audit section matches.
- The ground-truth (scuttlebutt) evidence is reflected in the synthesis and the variant perception, not only summarized.
- Reading on: the reading stage is complete (`reading.py status --strict` passes, every critical chunk was read twice and every disagreement resolved). Reading off (methodology 3.2.0): the digest is complete (`digest.py status --strict` passes), every number was run through `digest.py confirm`, and no digest lead is cited as FACT (`DIGEST_AS_FACT`). Either way the final report carries the generated coverage block unchanged.
- The reading audit passed: every agent on its pinned model and effort (or the deviation disclosed), every specialist read its pack, and with reading on every reader received every line of its chunks and opened its VIEW REQUIRED pages; the auditor's reading or digest sample found no material omission (or the affected chunks were re-read, or the leads re-checked).
- Methodology 3.2.0: the sector modules were selected in Stage 0 and every module step was done with its metric evidence, or is in the gap register; the forecasting specialist's base path was valued in a Stage-3 valuation follow-up and `calc/forecasting_reconcile.json` explains the gaps.
- Methodology 3.2.0: every registry item has a disposition (theme briefs and layer drafts pass their checks); every `immaterial` call in the CIO packet was read and none hides a finding; every contradiction candidate is in the contradiction log; every layer fit more than 10 points from the analyst's proposal states the deviation; `synthesis.py integration` reports no error and its warnings are explained; the auditor's Evidence Integration Audit is resolved.
- The verification passed (`qc/VERIFICATION.md`): every specialist's FACT values were seen in sources it opened, its
  claim sample was re-checked by the verifier, and every waiver has a reason in the gap register.
- No specialist report states its own reading coverage of documents; structured exchange filings (`corpus/STRUCTURED.md`) were used before reading for the facts they cover.
- SME runs: every specialist report and the final report carry the SME Enhanced Scrutiny section.
- No out-of-scope advice (sizing beyond the IPS ceiling, pairs, shorts) unless requested.
- The cross-company calibration check is done, and prior predictions are resolved where due.

---
