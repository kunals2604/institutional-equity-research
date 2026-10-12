# Operations Guide

## Running research

```text
/research-company BAJFINANCE NSE
/research-company "TVS Motor Company" NSE --cutoff 2026-10-12
/research-company SOMESME NSE --reference-position 2000000 focus on IPO proceeds use
```

- The session becomes the CIO. Expect a long, multi-stage run: nine Opus subagents doing web research in parallel, then synthesis. It uses substantial compute.
- The CIO pauses for you only if the company's identity is ambiguous.
- Output: `research/companies/<T>/runs/<RUN_ID>/cio/final_report.md`, plus a scoreboard row if QC passes and a local git commit (not pushed).

## Reading results

- `COMPANY_SCOREBOARD.csv` holds one row per company: the latest QC-passed run's layer fits, BQ and IA with confidence, verdict, valuation status, E[IRR] and report path. `methodology_version` tells you which scoring rules produced the row. Compare scores only across rows with the same version.
- Within a report, every number cites a claim ID. Look it up in the run's `evidence_ledger.csv` for the source, page or note, and retrieval date.

## Re-running a company

Run `/research-company <T>` again. A new `RUN_ID` is created and earlier runs are untouched. Specialists do not see the earlier run. The CIO compares the two after Stage 2, in "Change Since Prior Run". `update_scoreboard.py` refuses to replace a newer run with an older one.

## Asking follow-up questions on a finished run

In a session, say for example: "Re-invoke the `moat` specialist on run `research/companies/T/runs/R` to test whether the dealer-network advantage survives the competitor's 2026 expansion." Output goes to `specialists/moat_followup_<n>.md`. Re-run Stage 4 (merge, validate, QC) if the follow-up changes the conclusions. A changed score means writing a new scorecard and going through QC again.

## Manual validation

```bash
python3 scripts/validate_run.py research/companies/T/runs/R --stage specialists
python3 scripts/merge_ledgers.py research/companies/T/runs/R
python3 scripts/validate_run.py research/companies/T/runs/R --stage final
python3 scripts/validate_report.py any_markdown.md --kind any     # layer-name / phrase / tag lint
python3 -m unittest discover tests
```

## Changing the methodology

1. Edit the authoritative file (see the table in `PROJECT_INSTRUCTIONS.md` §1). Canonical lists sit between `<!-- NAME:BEGIN/END -->` markers.
2. If scoring dimensions, weights, anchors, gates or verdict mapping change, bump `METHODOLOGY_VERSION` in `methodology/SCORING.md`.
3. Record the change in `docs/FRAMEWORK_CHANGES.md`.
4. Run `python3 -m unittest discover tests`. Tests pin the canonical layer names and tags deliberately, so a change to those is a conscious, reviewed decision.
5. Commit.

To add a specialist section, edit the agent's `REQUIRED_SECTIONS` block. The validator picks it up automatically.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `Agent type 'financials' not found` | Agent definitions are loaded at session start. Restart Claude Code (or open a new session) in the repository root. |
| `/research-company` not listed | Same as above. The skill lives in `.claude/skills/research-company/`. |
| Specialists stall on permission prompts | Background agents need web and Bash permissions. `.claude/settings.json` allows WebSearch, WebFetch and `python3 scripts/*`; your own permission mode governs file writes. |
| Specialist report fails the barrier | Read the validator output. The CIO re-invokes the specialist with the exact errors (at most 2 retries) and otherwise records the gap. |
| `Merged ledger is stale` | Run `merge_ledgers.py` again after any ledger change. |
| Scoreboard update refused | Check `qc/auto_checks.json` (passed?), `scorecard.json` (`qc_status: PASS`?) and `qc_record.md` (`QC status: PASS` line). |
| Duplicate claim IDs across ledgers | Each author must use only its own prefix. Fix the offending ledger and its report citations. |

## Data hygiene

- Do not place unsourced data files in company folders. If you add raw data (for example an aggregator export), name the source and retrieval date at the top and tag it as tier 5 when cited.
- The untracked `research/companies/BAJFINANCE/raw_financials.md` predates this system. Its title says "audited", but it contains quarterly data in an aggregator layout and has no source line. Treat it as an unverified discovery lead.
