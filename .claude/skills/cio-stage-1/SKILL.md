---
name: cio-stage-1
description: The CIO's Stages 1 and 2: the specialists, the completion barrier and the gap-closure loop. Load it when `python3 scripts/orchestrate.py next` names it.
---

## Stage 1 — Run the specialists (sequential by default)

**Independent heads.** The specialists work like the separate heads of an institutional fund: each researches its
own mandate independently, in its own session, and never sees another's work. The engine (`scripts/agent_driver.py`)
enforces it: a specialist's session cannot read another specialist's files, `cio/`, `audit/`, `qc/`, the engine's
records, other runs, `docs/` or `archive/`, and may write only its own files. The engine fingerprints every other
specialist's files and the shared corpus around each of its segments, and the reading audit checks every specialist
transcript (Stage 4). What they share are facts gathered once, never conclusions: the document map, the structured
filings, the reading dossiers and the downloaded documents (`fetch_source.py` reuses them). Shared inputs remove
duplicated effort, not independent judgment.

**Execution mode.** Default **`sequential`**: one specialist at a time, in the order below. Use `parallel` only when the
user asks for it (`--parallel`).

Why sequential is the default:
- **Same depth.** The research work is identical either way.
- **Fewer, cheaper interruptions.** Ten agents running at once drain the usage window together and all stop half-done
  when it runs out. Run 20261012T132311Z hit six such stops. Run sequentially, at most one agent is in flight, and every
  finished report is safe on disk.
- **Fewer download failures.** Concurrent load caused most of the transient TLS failures in that run.

**Order:**
1. `financials` (numeric base)
2. `filings`
3. `industry`
4. `scuttlebutt` (ground truth: regulators' operating data, customers, pricing, channel, employees, competitors)
5. `moat`
6. `management`
7. `concalls`
8. `forecasting` (methodology 3.2.0: the driver model, consensus, surprise history and peer table)
9. `valuation` (benefits most from the populated source cache; it integrates the forecasting model only in Stage 3)
10. `special-situations`
11. `bear-case` (last, so its attack covers the widest evidence base it can find for itself)

Order does not relax independence: no specialist reads another's report, ledger or workpapers. Reusing a **source
document** that another agent downloaded is allowed and logged.

**Run them with the engine** (models and efforts are pinned in each agent file per `methodology/MODEL_POLICY.md`; a run's
`--effort` override, recorded as `model.effort_override`, applies to every Opus agent):
1. Write the identity block once to `RUN_DIR/engine/identity.md`, in the form `templates/specialist_prompt.md` shows
   (identity, known basis issues, sector playbooks, cutoff, the price claim). Every specialist receives the same brief:
   that template filled with its name, run and identity (`python3 scripts/agent_driver.py prompt RUN_DIR <name>` prints
   it). Never brief one specialist differently from another; what is specific to a domain belongs in its definition.
2. `python3 scripts/manifest.py RUN_DIR set execution_mode=sequential` (or `parallel`).
3. Start `python3 scripts/agent_driver.py specialists RUN_DIR` with Bash in the background (`run_in_background`; add
   `--parallel 2` only in parallel mode) and wait for its completion notification; do not poll. For each specialist in
   order it:
   - logs the invocation in the manifest and runs the agent as its own headless session on its pinned model and effort;
   - validates the report with `validate_report.py --kind specialist` and resumes the same session with the exact errors
     until it passes;
   - waits out a usage limit and resumes the same session; stops at a session boundary when the weekly window passes
     `--weekly-ceiling` (95 %, the owner's reserve) and resumes when run again;
   - when the agent's context passes 250k tokens (every turn re-reads the whole context, so a 500k context costs twice
     as much per turn and helps nothing), asks it to finish its current method step and write everything to disk
     (report sections, ledger, workpapers, `progress.md` with the exact next step), then continues in a fresh session
     that re-reads its own files first (logged as stage `1-continue`). Nothing is shortened;
   - **verifies the work itself, then has it fixed** (`scripts/verify.py`): once the report passes its validator, the
     script checks run against what the specialist's own sessions read and opened (a FACT value that never appeared in
     anything it read, such as a sum presented as a printed figure; a cited source or page it never opened; a must-read
     dossier not read in full; a Done checklist row that points nowhere) and every fixable finding goes back to the same
     session until it passes; then the independent `verifier` agent re-opens a sample of its claims at the sources, and
     every material discrepancy goes back to the specialist and is re-checked (two rounds at most). Findings only you
     can resolve (independence, integrity, a model or effort below its pin) and anything still open after the rounds
     stay in `qc/verification/<name>.json` for Stage 2. The brief each specialist receives carries the process lessons
     from earlier runs' verification (`verify.py lessons`).
   If this session may close before the specialists finish, give the owner the command with `nohup ... &`; the engine is
   safe to stop and restart.
4. **Exit 0:** every report passes its validator. **Exit 1:** read the end of `_cache/engine/engine.log` and
   `engine/ENGINE.md`, fix the cause and run it again: a paused job resumes its session, and a specialist whose job
   failed continues from its own files, never from zero. An `INDEPENDENCE` line in the log means a specialist changed a
   file it does not own: the reading audit will fail until you re-run that specialist or record why.
5. Trust files, not messages: the engine's record of each specialist's return message (`engine/jobs.json`) is for you,
   never for another specialist.

**Without the CLI** (`agent_driver.py cli` finds no `claude` binary): launch each specialist through the Agent tool, one
at a time, with exactly the prompt `agent_driver.py prompt` prints and the description `<name> <RUN_ID>` (the reading
audit finds the run's agents by it); never pass `model`, and pass `effort` only for a run override. Log each call with
`manifest.py invocation <name> --stage 1 --purpose "initial investigation"`, wait for the notification, run
`validate_report.py` yourself, and re-invoke the same agent (SendMessage) with the exact errors until it passes. After a
usage limit, resume the same agent with SendMessage; if it cannot be resumed, start a fresh one with the same prompt plus
`RESUME: read <name>_workpapers/progress.md and continue; do not redo completed steps`, logged as stage `1-resume`.

**Never ask a specialist to shorten, prioritise or "write early" to beat a limit.** Depth is not traded for speed. In
run 20261012T132311Z that instruction cost depth.

**While the specialists run**, do independent baseline verification to prepare for the audit, recorded in `cio_ledger.csv` (from filings, never from a specialist's files):
- price, share count and the share bridge to the latest balance sheet;
- headline revenue, PAT, net worth, debt and CFO for the latest 3 years and one older year, from filings.

Do **not** draft layer assessments or scores yet.

If the run's segment is `sme`, the template adds to every specialist's prompt: "SME ENHANCED SCRUTINY is ON: add the section `SME Enhanced Scrutiny` defined in your agent definition."

If neither the engine nor the Agent tool can run a specialist, stop and tell the user. **Never write a specialist's report yourself.**

## Stage 2 — Completion barrier, gap-closure loop and first git batch

0. **Verify the research.** `python3 scripts/verify.py run RUN_DIR --stage specialists` re-checks every specialist
   from its transcripts and files and writes `qc/VERIFICATION.md`. For each open finding: a fixable one goes back to
   its specialist (`agent_driver.py followup ... --stage 2` with the finding, or `agent_driver.py verify RUN_DIR --only
   <name>` for the verifier's re-check); an independence or integrity breach means re-running that specialist from a
   clean start; anything you accept is waived with its reason (`verify.py waive RUN_DIR <finding id> --reason "..."`)
   and goes into the gap register. Never waive a value that was never seen in a source because it is convenient: fix
   it or remove the claim.
1. **Run the barrier.** `python3 scripts/validate_run.py RUN_DIR --stage specialists` checks:
   - the reading stage (methodology 3.1.0; reading on): the reading status complete, `COVERAGE.md` matching it, the dossiers built; or the digest (reading off): its status complete, `corpus/digest/COVERAGE.md` matching it, one pack per specialist;
   - the sector modules (methodology 3.2.0): selected in the manifest, every module step in its owner's checklist;
   - the verification (`qc/verification.json` PASS);
   - existence, headers and sections;
   - **historical depth** and the **Method Coverage Checklists**;
   - crosswalks, claim traceability, metric keys and ledgers.

   It records per-specialist status in `run_manifest.json`.
2. **Trust files, not messages.** A returned message does not prove a deliverable exists; the validator and the files do.
3. **Fix failing reports.** For each missing or failing report, re-invoke **that** specialist with the exact validator errors: write them to a file and run `python3 scripts/agent_driver.py followup RUN_DIR <name> --stage 2 --purpose "validator errors" --message-file <file>` (it continues the specialist's own session when its context is still small, otherwise a fresh session that reads its files first; it logs the invocation and re-runs the validator). Keep re-invoking while the failures are fixable.
4. **Gap-closure loop** (`cio/gap_register.md`).
   - **Collect** every gap:
     - each **Partial** or **Not available** row in the specialists' checklists (sector-module steps included);
     - every `missing` or flagged row of `corpus/DOCUMENT_MAP.md` that a specialist did not resolve;
     - every event of the events file (`corpus/dossiers/events.md` with reading on, `corpus/digest/events.md` with reading off) **not found in the documents** that no specialist confirmed or
       explained in a primary source (owner: the specialist whose domain it is; say whether the reading missed it or the
       company did not disclose it);
     - every *Missing evidence* item;
     - every tier-6-only FACT warning on a decision-relevant claim;
     - every unresolved data conflict.
   - **Record** each in a table: gap · owner · decision relevance (High/Medium/Low) · closable? · attempt log · status.
   - **Close** each closable gap with a decision relevance of High or Medium. Re-invoke the owner with a narrow follow-up: `python3 scripts/agent_driver.py followup RUN_DIR <name> --stage 2 --purpose "<gap id>" --message-file <file> --output specialists/<name>_followup_<n>.md` (it validates the follow-up and its ledger). A Stage-2 follow-up is still independent work: name sources to try, never another specialist's findings. Name the alternative sources to try:
     - exchange archive vs. IR site vs. regulator vs. rating agency;
     - BSE vs. NSE;
     - the company's own older reports;
     - a different URL pattern.
   - **Repeat** until every such gap is **closed** or proven **unobtainable** (each alternative tried and logged in `source_retrievals.csv`).
   - **Carry the residue.** Unobtainable gaps go into the report's Confidence Assessment and the accepted limitations.
   - Apply the insufficient-evidence triggers in `SCORING.md` §8 honestly.
5. **Git batch 1:** `python3 scripts/git_publish.py RUN_DIR --batch specialists --push`. If the push fails, keep going and report it at the end.
