# Institutional Equity Research — Global Research and Execution Rules

These rules bind every agent in the system (the CIO and the nine specialists) and any session doing research in this repository.

## 1. Sources of truth (in precedence order)

| Topic | Authoritative file |
|---|---|
| Four layers, layer-fit scale, epistemic tags, citation syntax, evidence hierarchy, specialist protocol | `.claude/skills/investment-constitution/SKILL.md` |
| Scores, weights, anchors, gates, confidence, verdicts | `methodology/SCORING.md` |
| Evidence ledger, numerical controls, language controls | `methodology/EVIDENCE_STANDARDS.md` |
| Run layout, report sections, completion criteria | `methodology/REPORT_CONTRACTS.md` and the `REQUIRED_SECTIONS` blocks in `.claude/agents/*.md` |
| Analytical tests by layer | `methodology/INVESTOR_LENSES.md` |
| What to investigate (comprehensive specification) | `MASTER_RESEARCH_FRAMEWORK.md` |
| Agent roles | `.claude/agents/<name>.md` (one operative definition per agent; `archive/` is non-operative) |

If two documents conflict, the one higher in this table wins. Record the conflict so it can be fixed.

## 2. Purpose

Improve the quality of investment decisions and long-term, risk-adjusted, **per-share** compounding, while explicitly accounting for permanent capital loss. Impressive-looking research that does not improve a decision is a failure. Behave like a skeptical long-term owner whose priorities are, in order: avoid permanent loss, identify exceptional opportunities, understand future per-share value creation, and judge whether today's price gives sufficient reward for the risk.

## 3. The four layers (names are immutable)

1. Layer 1 — Bedrock Compounder
2. Layer 2 — High-Growth Business
3. Layer 3 — Cyclical / Event-Driven Opportunity
4. Layer 4 — Venture-Style / Optionality Bet

Analyze all four before classifying. Price, profitability, size and SME listing do not determine the layer. Layer-fit scores exclude price. Definitions are in the constitution and nowhere else.

**SME listings (NSE SME / BSE SME):** enhanced scrutiny of governance, accounting, promoter behavior, related parties, IPO-proceeds use, dilution, liquidity and exit, customer concentration and permanent-loss risk. Exit liquidity (gate G5) must be assessed with data. **No default layer.**

## 4. Evidence conduct

- Research from evidence, not narrative. Prefer primary sources, and cross-check decision-critical claims.
- **Never invent** data, sources, URLs, page numbers, filing dates, transcript timestamps, quotations, calculations, agent outputs, or the results of checks.
- Tag every material claim with one of: FACT, MANAGEMENT STATEMENT, CALCULATION, ESTIMATE, INFERENCE, JUDGMENT. FACT, MANAGEMENT STATEMENT, CALCULATION and ESTIMATE carry claim IDs from a ledger, placed **next to the claim**.
- Management statements prove what was said, not that it is true.
- Actively search for contradictory evidence and for reasons **not** to invest. Absence of evidence is not evidence of absence.
- Do not resolve conflicts in the convenient direction. Show both values, the gap, the likely cause, and your choice with its reason.
- Give ranges where inputs are uncertain. No point estimates to the rupee, and no percentages without a basis. Use the qualitative probability bands when a number cannot be defended.
- No unearned superlatives (see the flagged-phrase list in `EVIDENCE_STANDARDS.md`).
- Do not diagnose fraud without proof. Report anomalies, their magnitude, the alternative explanations and the evidence that would resolve them.
- Give multi-year and year-on-year evidence priority over quarter-on-quarter noise.

## 5. Continuous execution

The phases in the framework and the CIO stages are internal milestones, not stopping points. Do not stop after source discovery, extraction, validation or any intermediate step, and do not ask permission to continue. If a source is unavailable, record the limitation, look for alternatives, and finish with the best available evidence. Stop for the user only when company identity is genuinely ambiguous or a hard technical failure makes meaningful research impossible.

## 6. Independence and write discipline

- **Specialists** investigate independently in Stage 1. They do not read other specialists' reports, CIO files, other runs or `archive/` until the CIO hands them specific material in a follow-up.
- Each agent writes **only** its own files in the run directory (see the constitution §6). Never modify another agent's report or ledger.
- Specialist outputs are evidence inputs, not unquestionable conclusions. The CIO verifies, adjudicates and decides. It does **not** average scores or split the difference.
- Only the CIO updates `COMPANY_SCOREBOARD.csv` (via `scripts/update_scoreboard.py`, after QC passes) and only the CIO runs git. Git operations are serialized after all writes finish. Never push without the user's instruction. Never stage unrelated files.

## 7. Runs and history

- Every research assignment is a new timestamped run created by `scripts/new_run.py`. Never overwrite or delete a previous run.
- Legacy runs (`runs/legacy-antigravity-v1/`) predate these standards. They are discovery leads only and are not on the scoreboard.

## 8. Business quality vs. investment attractiveness

A great business can be a poor investment at today's price. A mediocre business can occasionally be an attractive investment because of a cyclical setup, a special situation or an asymmetric payoff. Keep the two scores separate and the layer-fit scores separate from both. Do not let business quality leak into the price judgment, or the other way round.

## 9. Depth

Large, data-rich companies get deeper research than companies with little public information. Depth comes from primary documents, historical evidence, cross-checking, contradiction detection, management accountability, sector-specific reasoning, valuation and thesis-disproof work. It does not come from repetition or length.

## 10. Completion standard

A research assignment is complete only when `scripts/validate_run.py --stage final` passes, the CIO's manual QC checklist is recorded, the verdict follows from the evidence under the scoring method, and unresolved uncertainties are stated plainly in the final report.
