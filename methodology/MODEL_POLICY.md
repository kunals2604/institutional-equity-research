# Model Policy — which model and effort does which work

The owner's rule: **no loss of research depth.** Judgment stays on Opus at the owner's pinned effort; Sonnet does only
work that it provably does as well, and scripts do everything that needs no model at all. Models and efforts are
pinned in each agent's frontmatter (`validate_system.py` checks them against the block below), so a run's depth no
longer depends on what the model picker was left at. (In run BHARTIARTL 20261012T132311Z every agent, the CIO
included, ran at effort *high* while the owner believed it was *max*; the reading audit now catches that.)

**Effort (owner's decision, 2026-10-19):** every Opus agent is pinned at **xhigh**, not max. A first-time read of
a company costs hours of reading and several usage windows even at xhigh; max remains available per run with
`--effort max`. The readers' work is checked by script and by a second, independent read either way; a read that
ran above its pinned effort is reported, not failed.

## The five tests for giving work to Sonnet

A task goes to Sonnet only when **all five** hold; otherwise it stays on Opus.

1. **Fully specified.** A schema or checklist defines the task completely; nothing open-ended such as "find what is
   interesting".
2. **Checkable.** A script can check every output against the source: the quote is in the cited passage, the
   number is printed there, totals reconcile, the file is the document it claims to be.
3. **Omissions are detectable.** Page receipts, item counts, clause lists and totals that must reconcile, and for
   high-stakes sections an independent Opus read of the same pages.
4. **No judgment** of materiality, credibility or meaning. Sonnet extracts every instance of the listed types and
   flags what is ambiguous; it never decides what matters.
5. **Calibrated.** The work type passed the bake-off below, and it is re-checked every run (the auditor re-reads a
   random sample of Sonnet-read pages with Opus; a material miss moves that class back to a double read).

If a task needs Sonnet at maximum effort to do well, it is a reasoning task and belongs on Opus.

## Assignment

| Work | Who | Model · effort | Why |
|---|---|---|---|
| Downloads, structured filings, de-duplication, tables, tie-outs, page record, coverage tables, reading audit, scoring arithmetic | scripts | none | exact |
| Finding documents the indexes missed | `librarian` | Sonnet · high | search and download; a script validates every file |
| A dated ten-year timeline of the company's major events from news and the web (leads and a completeness check of the reading, never evidence) | `historian` | Sonnet · high | search and list; a script checks every row and that every source was opened |
| Reading non-critical sections, transcripts, presentations, filings | `reader` | Sonnet · high | meets the five tests |
| Reading critical sections (auditor's reports, CARO, IFC, critical notes, Board's report, AOC-1/2, secretarial audit, related-party filings) | `critical-reader` **and** `reader`, independently; a fresh `critical-reader` resolves every disagreement | Opus · xhigh and Sonnet · high | highest stakes; two different models miss different things |
| The ten specialists, the auditor, the CIO | specialists, `auditor`, main session | Opus · xhigh | judgment |
| Re-checking a sample of each specialist's claims at their sources (the verification loop, `scripts/verify.py`) | `verifier` | Opus · xhigh | whether a source says what a claim says needs reading in context; the script checks run first and cost nothing |

**Effort override.** `/research-company ... --effort <low|medium|high|xhigh|max>` sets the effort of every Opus
subagent for that run (the CIO passes it in each Agent call and records it in the manifest). Sonnet workers keep
their pinned effort. The CIO's own effort is the session's: Stage 0 checks it (`reading_audit.py session`) and tells
the owner if it is not Opus at xhigh.

<!-- MODEL_POLICY:BEGIN -->
```json
{
  "policy_version": "1.1",
  "agents": {
    "cio": {"model": "opus", "effort": "xhigh", "kind": "main session"},
    "financials": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "filings": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "management": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "industry": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "moat": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "concalls": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "valuation": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "bear-case": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "special-situations": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "scuttlebutt": {"model": "opus", "effort": "xhigh", "kind": "specialist"},
    "auditor": {"model": "opus", "effort": "xhigh", "kind": "auditor"},
    "critical-reader": {"model": "opus", "effort": "high", "kind": "worker"},
    "reader": {"model": "sonnet", "effort": "high", "kind": "worker"},
    "scanner": {"model": "haiku", "effort": "high", "kind": "worker"},
    "librarian": {"model": "sonnet", "effort": "high", "kind": "worker"},
    "historian": {"model": "sonnet", "effort": "high", "kind": "worker"},
    "verifier": {"model": "opus", "effort": "xhigh", "kind": "worker"}
  },
  "calibration": {
    "status": "pending",
    "record": "docs/MODEL_CALIBRATION.md",
    "single_read_classes": []
  }
}
```
<!-- MODEL_POLICY:END -->

`calibration.single_read_classes` lists the non-critical section classes that a single Sonnet read may cover. It is
filled from the bake-off result (`reading.py bakeoff score`, recorded in `docs/MODEL_CALIBRATION.md`); a class is
added only with **at least 30 adjudicated items**, **zero material misses** and **recall ≥ 0.98** against the adjudicated
items. A class short of 30 items stays double-read until later bake-offs add evidence. While `status` is
`pending`, or for any class not listed, chunks are double-read.

## One-shot reading: Opus primary, cheaper second reads (owner-approved plan, 2026-10-22)

Measured on real chunks against exhaustive agentic Opus reads: a one-shot read (one call, no tools, the chunk and its
page images in the message) with passage and number accounting costs $0.68–0.88 per 12k-token chunk on Opus at high
effort (92 % exact recall on an auditor's report) against $2.3–3.4 for the agentic session; Sonnet ($0.41–0.49) and
Haiku ($0.06) recalled 41–59 % and 46 %. So **Opus (`critical-reader`, high) reads every chunk**; an independent second
read follows: Sonnet (`reader`) on critical sections, Haiku (`scanner`) on the others. Opus adjudicates every conflict,
and on critical sections every item only the second read found; on other sections the second read's checked extra finds
are added and marked. The in-run calibration may still let a cheaper model read a class alone where it passes the rule.
A chunk whose one-shot read cannot pass after two fix turns is read again by the agentic reader.

## In-run calibration (owner's decision, 2026-10-19)

The owner chose to test the system on a full research run of a new company rather than a separate pilot. Calibration
therefore happens **inside every run** and is never carried over from another company: `reading.py plan` marks a
stratified sample of the run's chunks (one per non-critical section class first) and the engine reads that sample with
both models before any other non-critical chunk; once it is reconciled, `reading.py` scores the Sonnet read of each
class against the adjudicated items with the rule above and writes `corpus/reading/calibration.json`
(`BAKEOFF.md`). A class that passes is read by Sonnet alone for the rest of that run; every other class, and every
critical class always, is read by both models. The global `calibration` block above stays `pending` (it applies only
to a plan made with `--no-calibration`, which double-reads everything). The auditor's sample of Sonnet-read pages and
the reading audit keep checking every run. Measured costs per chunk, per specialist and per run are recorded in
`docs/MODEL_CALIBRATION.md` after the first full run.

## The bake-off (calibration)

1. `python3 scripts/reading.py bakeoff plan RUN_DIR --n 12` picks chunks across the section classes (non-critical first)
   and marks them for a double read.
2. The CIO loops `python3 scripts/reading.py next RUN_DIR --bakeoff`, launching the `reader` and the `critical-reader` on
   each chunk, independently, one agent at a time; a fresh `critical-reader` resolves every disagreement against the page
   (A/B labels; it is not told which model wrote which).
3. `python3 scripts/reading.py bakeoff score RUN_DIR` computes, per model and class, recall and precision against the
   adjudicated items and lists every material miss. Record the result in `docs/MODEL_CALIBRATION.md` and set
   `single_read_classes` here; then run the tests.
4. Every run keeps checking: the auditor's sample of Sonnet-read pages (`auditor.md`), and the reading audit
   (`reading_audit.py run`), which also confirms from the transcripts that each agent ran on its pinned model and
   effort.
