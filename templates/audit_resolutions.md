# Audit Resolutions — {company} ({ticker}) · run {run_id}

The CIO's response to every finding in `audit/audit_report.md` (`.claude/agents/auditor.md`). One row per finding, in the auditor's order.

- **Resolution** is exactly one of **Fixed** (the report, scorecard, ledger or calculation was corrected; say what changed and where), **Rebutted** (the finding is wrong; cite the evidence, with claim IDs, that shows it) or **Accepted limitation** (Major or Minor only; the residual is disclosed in the final report's limitations).
- A **Critical** finding can never be an accepted limitation. After fixing or rebutting it, re-invoke the auditor; the re-audit (`audit/audit_followup_<n>.md`) must mark it **Closed**.
- If a fix changes any score input, rebuild the scorecard (`build_scorecard.py`), re-run the robustness test and the price ladder, and say so here.

| Finding | Severity | Resolution | What changed, or the evidence for a rebuttal | Re-audit |
|---|---|---|---|---|
