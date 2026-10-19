# Institutional Review of the Research Framework

**Reviewer stance:** buy-side fund owner and CIO, assessing whether this system would meet the standard of an institutional investment process: whether its outputs could be put in front of an investment committee and defended.
**Date:** 2026-10-12 · **Methodology version after review:** 2.2.0 · **Branch:** `claude-code-migration`

---

## 1. Verdict

**Before this review:** the *architecture* was institutional-grade. It had independent specialists, a CIO who adjudicates, separate quality and price scores, a claim-level evidence ledger, QC gates and a run archive. The *research operating layer* was not. Depth was not enforced, agents had no procedure for acquiring and reading documents, every number came from LLM arithmetic, metric definitions were inconsistent, sector depth was thin, and several decision outputs that any investment committee would ask for were missing.

**After this review:** the system has an operating layer that matches the architecture. It enforces a historical depth standard, follows a documented acquisition-and-verification procedure, has deterministic metrics and valuation engines, uses one metric dictionary, gates on cross-agent numeric reconciliation, has 18 sector playbooks, works from an investment policy statement, and produces variant perception, decision triggers, position-risk inputs and falsifiable predictions.

What it still cannot do is listed in §5. The most important limitation: **it has not yet run on a real company.**

---

## 2. What was already at institutional standard (kept as is)

| Area | Why it is sound |
|---|---|
| Independence model | Nine specialists research in parallel without seeing each other's work, which is the right defence against anchoring and groupthink |
| CIO as adjudicator | Re-verification, a contradiction log with independent checks, no averaging and no midpoints |
| Two separate scores + layer fit | Quality, price attractiveness and archetype fit are never conflated |
| Four immutable layers | Canonical, machine-enforced, analyzed before classification; SME status does not set the layer |
| Evidence ledger and epistemic tags | Claim IDs, locators, tiers, confidence; "never invent" rules |
| QC-gated publishing | Scoreboard only for complete, QC-passed runs; truthful git history |
| Calibration intent | Fixed weights, anchors, gates, confidence and an override limited to one notch |

---

## 3. Gaps found (by severity) and how each was closed

| # | Severity | Gap | Fix | Where |
|---|---|---|---|---|
| 1 | **Critical** | **Historical depth was not enforced.** Agents were told "5 years, 10 where meaningful", and nothing checked. Durability, cycle and credibility conclusions need 10+ years. | A **Historical Depth Standard**: at least 10 fiscal years of financials (15–20 and two cycles targeted), at least 12 quarters of calls, at least 10 years of valuation, share-price and industry history, at least 12 quarters of shareholding. **Enforced by the validator**, which counts FY and quarter labels; shorter coverage needs a written `coverage_exception`. Every report now has a Data Coverage table, and the scorecard records coverage. | `methodology/RESEARCH_PLAYBOOK.md` §2; `scripts/research_lib.py` `check_coverage`; all agent definitions |
| 2 | **Critical** | **No research operating procedure.** Nothing said how to acquire 300-page annual reports, read them within context limits, verify aggregator data, or survive compaction. | A 10-step **research playbook**: plan → acquire → read (PDF pages via the Read tool) → extract to workpapers → **verification sampling plan** (latest 3 years + anomaly years + 3 spread years; escalate on discrepancies) → compute with scripts → analyze → write incrementally → self-QC. Includes context discipline and an annual-report reading map. | `RESEARCH_PLAYBOOK.md` |
| 3 | **Critical** | **Numbers came from LLM arithmetic** (the cause of the legacy run's two WACCs and inconsistent ratios). | **Deterministic engines:** `fin_metrics.py` (ratios, 3/5/10/15-year CAGRs, per-share compounding, incremental ROIC, accruals, Beneish, Piotroski; general and lender profiles) and `valuation_tools.py` (WACC, DCF with sanity checks and sensitivity, reverse DCF, scenario IRR, price ladder, decomposition, sizing ceiling). Covered by tests that check the formulas against closed-form identities. | `scripts/` |
| 4 | **High** | **No single definition per metric.** "ROCE" could mean three things. | A **metric dictionary** of 151 keys with formulas and conventions (averages, leases, bases, E[IRR], normalized earnings, maintenance capex). Every quantitative ledger claim must carry a valid `metric` key. | `methodology/METRIC_DEFINITIONS.md` |
| 5 | **High** | **No cross-agent numeric reconciliation.** Different agents could report different values for the same metric without anyone noticing. | `reconcile_numbers.py` groups claims by metric, period, basis and unit. **Final QC fails** until every conflict is adjudicated in the contradiction log, citing the claim IDs. | `scripts/reconcile_numbers.py`, `validate_run.py` |
| 6 | **High** | **Thin sector coverage** (4 sectors). | **18 sector playbooks**: economics, KPIs, accounting traps, cycle drivers, valuation use/avoid, layer questions to test, sources. | `methodology/SECTOR_PLAYBOOKS.md` |
| 7 | **High** | **No source map or provenance for documents.** | **Source guide** (India and global: where each data item lives, tier, typical history, access notes, verified access behavior). **`fetch_source.py`** records a SHA-256 fingerprint, timestamp and HTTP status for every download, logs failed attempts, and keeps documents out of git. | `methodology/SOURCE_GUIDE.md`, `scripts/fetch_source.py`, `html_tables.py` |
| 8 | **High** | **Missing decision outputs.** No variant perception, no key debates, no price at which the decision changes, no position-risk inputs, no learning loop. | The CIO now must produce: **variant perception** (consensus → our view → why → signpost); **3–5 key debates**; **decision triggers** from a deterministic price ladder (buy below / strong buy below / avoid above); a **position-risk profile** (bear-case loss, permanent-loss band, days to exit, factor exposures, sizing ceiling from the policy); **3–7 falsifiable, dated predictions with probabilities**, resolved by the next run and tracked for calibration; a **next review date**. All are validated in `scorecard.json`. | `.claude/agents/cio.md`, `SCORING.md` §§9–10, `research_lib.py` |
| 9 | **High** | **No investment policy statement.** The hurdle and limits were ad-hoc run flags. | `config/investment_policy.json` (hurdle, horizon, benchmark, reference position, liquidity rule, risk limits) is snapshotted into every run. Reports flag unconfirmed placeholders. | `config/`, `new_run.py` |
| 10 | **Medium** | **Score anchors were mostly verbal**, so calibration across companies was weak. | **Quantitative guides** for BQ1 (ROIC − WACC spread; ROE − CoE for lenders), BQ3 (runway × reinvestment), BQ4 (10-year CFO/PAT, forensic adjustments), BQ5 (net debt/EBITDA, coverage, maturities; capital headroom for lenders). IA1, IA2 and IA4 are now scored deterministically by the price ladder. A layer-specific IA interpretation table was added. | `SCORING.md` §§2–3 |
| 11 | **Medium** | **Adversarial review was one-sided** (only buys were attacked). An avoid verdict that wrongly skips a great company was never challenged. | **Symmetric adversarial review:** the bear-case agent attacks the CIO's draft whichever direction it points, for any buy or avoid verdict, or any verdict change. | `cio.md` Stage 3.11, `bear-case.md` |
| 12 | **Medium** | **Ownership gaps.** No agent owned liquidity/ADTV (needed by gate G5), price drawdown and TSR history, credit-rating history, ESG/BRSR risks, promoter-group structure, macro sensitivities, the event calendar, the short-seller search or quantified moat metrics. | Assigned: valuation (liquidity, ownership flows, drawdowns, TSR, price ladder); filings (rating history, ESG/BRSR); management (promoter group and holding structure, value per rupee retained); industry (macro and factor sensitivities); special-situations (event calendar); bear-case (pre-mortem, short-seller, litigation and regulatory search); moat (quantified metrics, competitive-advantage period); concalls (analyst concern tracker); financials (segments, forensic screens, per-share compounding). | `.claude/agents/*.md` |
| 13 | **Medium** | **No evidence-quality measurement** behind the confidence levels. | `evidence_stats.py` reports claims, primary share, tier mix, NOT_LOCATED and low-tier FACT shares per agent against thresholds. Confidence must be consistent with them. | `scripts/evidence_stats.py`, `EVIDENCE_STANDARDS.md` |
| 14 | **Low** | WebFetch returns model-processed page renderings, which can mis-transcribe numbers. | Rule: decision-critical numbers must be read from the original document (PDF page or deterministic HTML table extraction). | `EVIDENCE_STANDARDS.md` §2a |

---

## 4. How agents now research and write (end to end)

1. **The CIO's preflight** produces a factual brief and a source register with minimum categories (≥ 10 years of annual reports, ≥ 12 quarters of transcripts, ratings, regulators, industry publishers, peers).
2. **Each specialist** writes a research plan, downloads documents with provenance, reads PDFs page by page (table of contents first), and extracts figures **with page locators** into workpapers and its ledger as it goes.
3. **Financials** builds the 10–20-year `financial_history.csv`. It uses an aggregator for the long tail, verifies a defined sample against filings, escalates on discrepancies, then runs `fin_metrics.py`. **Valuation** builds JSON inputs and runs `valuation_tools.py`. Material arithmetic is done by code.
4. Each specialist writes its report **section by section** and self-validates (structure, depth counts, citations, metric keys) before returning.
5. **The CIO** reconciles numbers across agents, measures evidence quality, re-verifies at least 12 claims and re-runs at least 3 calculations, adjudicates every conflict, forms its variant perception, assesses the four layers, scores with the quantitative guides and the price ladder, runs the symmetric adversarial review, and writes the decision outputs.
6. **QC** gates on structure, depth, traceability, scorecard arithmetic, report–scorecard consistency and numeric reconciliation. Only a complete, QC-passed run reaches the scoreboard.

---

## 5. Remaining limitations (honest)

| Limitation | Effect | Mitigation |
|---|---|---|
| **No production run yet** | Research quality, agent behavior under long tasks, and the run-time git pushes are untested on a real company | Run the first company and review it closely. Then tune the depth minimums and evidence thresholds. |
| **NSE blocks scripted access (403)** | Agents must rely on BSE and company-IR copies of the same filings | Documented in `SOURCE_GUIDE.md` §6 |
| **No PDF text tooling installed** (`pdftotext`, `pypdf` absent) | Agents cannot grep a 300-page PDF; they navigate by table of contents and read pages with the Read tool | Adequate for targeted reading. Installing `poppler` would enable full-text search later (optional). |
| **Paywalled data** (Bloomberg, CMIE, proprietary industry reports) | Some industry series and consensus estimates are unavailable | Recorded as missing evidence; confidence is reduced, never filled in from memory |
| **Validators check structure, not semantic truth** | A wrong page citation can pass the automated checks | The CIO's mandatory re-verification of 12+ claims; locators make spot audits cheap |
| **Independence is instruction-enforced** | A specialist could, in principle, read a peer's file | Attestations, the CIO audit, and the cross-citation warning in the validator |
| **Calibration starts empty** | Cross-company comparability builds up over time | `SCORING.md` §7 drift review after 5 companies; prediction hit rates in `docs/CALIBRATION_LOG.md` |
| **The investment policy is unconfirmed** | The hurdle (12 %) and the absent risk limits are placeholders | **You should review `config/investment_policy.json` and set `confirmed_by_user: true`** |

---

## 6. Recommended next steps for the owner

1. Review and confirm `config/investment_policy.json` (hurdle, benchmark, horizon, reference position, risk limits).
2. Run one company you know well, so you can judge the output against your own knowledge. Then review the depth coverage, evidence statistics and contradiction log before trusting the scores.
3. After 5 companies, run the calibration review (`SCORING.md` §7) and adjust anchors **only** through a methodology version change.

---

## 7. Second review (2026-10-18): after the first live run (BHARTIARTL)

**Question from the owner: are ten agents (the CIO and nine specialists) enough?** Not quite. Two functions had no owner, and adding more agents beyond them would cost depth rather than add it.

| Function | Was it covered? | Evidence from the first run | Decision |
|---|---|---|---|
| Ground truth (scuttlebutt: customers, channel, competitors, employees, regulators' operating data) | Declared as lens T1 for industry, moat and management, each of which had a different primary job | Zero network-quality, complaint, app-rating, channel, employee or search-trend evidence in 808 claims; only porting data | **New specialist `scuttlebutt`** (it owns T1) |
| Independent verification of the CIO's own work | The CIO marked its own QC checklist | The CIO ledger carried reversed claim IDs and unsupported numbers that only came to light on review; run on that report, the new tie-out finds 71 sentences whose number matches a different claim from the one cited (an incomplete citation) and 4 numbers it cannot tie to any claim | **New `auditor`** (Stage 4, fresh context, separation of duties) |
| Document acquisition | Every specialist searched and downloaded on its own | 52 failed downloads (41 transient TLS errors); "pre-FY2017 annual reports unavailable", although NSE and BSE list them back to FY2010 and FY2002 | **A deterministic Stage-0 stage, not an agent** (`exchange_index.py`, `document_map.py`) |
| Credit, ESG, macro, forensic, quant | Within financials, filings, industry, valuation and bear-case | Covered; deepened inside those agents (debt maturity ladder, secretarial audit, registered charges, market-positioning signals) | No new agent: splitting them would thin each report |

**Retrieval.** Both exchanges are reliably scriptable when requests are made correctly: the NSE API needs only JSON accept headers and a referer (no cookie handshake), and the BSE API needs HTTP/2 with a browser header set. The system Python's TLS library, not the websites, caused most failures; curl is now the primary transport, every payload is validated, and the Internet Archive is the fallback for moved or removed IR files.

**Reading.** Annual reports are converted once into a page-anchored text layer that splits two-page spreads, keeps prose in reading order and rebuilds tables from word coordinates. Pages the text cannot be trusted for (scanned, rotated tables, mismatched numbers) are flagged, and the zero-loss rule requires every decision-critical number to be confirmed on the rendered page.

**Scoring.** The verdict follows a fund manager's sequence (methodology 3.0.0): archetype weight profiles fixed in advance, uncertainty never rewarded, non-compensatory must-pass tests, a margin of safety that scales with uncertainty, decision drivers and conviction. On the first run's own judgments the engine still concludes AVOID, but now also states why the company would not qualify as a compounder at any price on its evidence (through-cycle returns below the cost of capital).

**Remaining limitations.** Exchange endpoints are unofficial and can change without notice (failures are recorded and the mechanics documented with their verification date); scanned pages without a text layer must be read visually (no OCR is installed); XBRL covers only about FY2019 onward; the auditor and the CIO verify samples, not every claim.

## 8. Third review (2026-10-18): what the agents actually read

**Question from the owner: a 300-page annual report is about 450k tokens and the run covered ten years, so how could
specialists that ended at about 500k tokens each have read them?** They could not, and they did not. Measured from the
nine specialists' own transcripts (every tool result matched against the full text of each report):

| Measure | Result |
|---|---|
| Final context per specialist (no compaction) | 355k–506k tokens: everything each agent ever read or wrote |
| Share of each annual report's text that reached any one agent | filings 4–10 %, financials 4–6 %, others below 6 %; industry, concalls and valuation below 1 % |
| All ten agents and the CIO combined, overlap removed | 11–17 % of each year's text; 233 of 3,310 pages had half their text seen by anyone, about 2,400 pages less than a tenth |
| Transcripts | the concalls specialist read its own keyword-filtered extracts: 13–21 % of each transcript |
| Effort | every agent, the CIO included, ran at *high*; the session moved to *max* only after the run |
| Usage | each specialist re-processed its context 100–150 times (22–37M tokens); re-caching after usage-limit pauses in the parallel run was about 40 % of their input-side usage |

The reports said "annual reports read" (filings: "Full for FY2025–FY2026"; that full read was about 10 % of the FY2025
report: the auditor's reports, CARO and a few notes). Nothing in the framework measured or recorded what was read; the
depth standard counted years, which one search hit per year satisfies.

**Third-party summaries were considered and rejected as a basis**: no page citations (checking one means reading the
report anyway), unknown coverage, generic selection that drops exactly the forensic details, patchy availability. The
structured filings regulators require (BRSR XBRL, voting results, audit-opinion statements, board composition) are
primary and exact and are now used first (`SOURCE_GUIDE.md` §0c).

**Design response (methodology 3.1.0):** a reading stage that reads every in-scope page once, in small fresh contexts
(Sonnet readers; Opus reads the critical sections again, independently; disagreements resolved against the page),
quote- and amount-checked by script, delivered as topic dossiers and reading packs, recorded page by page in
`corpus/reading/COVERAGE.md` (the only statement of coverage), and checked against the transcripts by the reading audit;
models and efforts pinned per agent (`MODEL_POLICY.md`); work goes to Sonnet only when it passes five tests and a
calibration bake-off (`docs/MODEL_CALIBRATION.md`). Specialists stay whole and on Opus: splitting each into a "deep" and a
"cheap" half was rejected, because questions arise while gathering evidence; the split is by function (reading versus
reasoning), not by specialist.

**The first live read found what the checks did not (2026-10-18/19).** The first calibration launch (Opus at max, six
chunks of the Airtel FY2025–FY2026 reports) passed every check, but its output and transcript showed the chunk format
losing meaning: values of three digits or fewer and nil dashes were hidden as "trivial" (the reader put `420` and
`(771)` into free-text descriptions, where nothing checked them); row labels and column headers that recur every year
were hidden as "already read", leaving the reader values without their line or period; continuation lines of a
passage looked like page furniture; pages carrying raster images (60–80 per report) were never viewed; and two reads
that swapped the current and prior year's amounts would have agreed. All were fixed before the calibration continued
(`FRAMEWORK_CHANGES.md` 3.1.0 item 13). The second launch (Opus, the FY2026 MD&A and Board's report) then showed that the
text layer can print a multi-column page's paragraphs out of order, so that an award or figure appears under the
wrong heading. Three alternative orderings were measured on 852 report pages and none was reliably better (each fails
on a different layout), so the remedy is in the reading rules: attribute every fact to the heading it sits under on
the page and open the page whenever the order looks wrong. This is a residual risk for single-read chunks, and the
calibration measures it. The lesson for the framework: a passing check proves only what it checks, so
each new reading stage is calibrated on real documents and its outputs are read, not just validated.

**Cost, honestly:** after those fixes, about 0.64–0.70M tokens of text and page images per annual report (measured on
BHARTIARTL FY2024–FY2026; 120–150 pages per report viewed on the image), roughly 6–8M tokens of reading content per
company over ten years with transcripts and filings. Read-once now saves about 10 % of an older report (another 10 %
repeats but is shown as context so nothing loses its meaning). What the agents process is several times that, because
every turn re-reads the agent's context; launches of about one chunk keep the multiple low.

**Feasibility, measured (2026-10-19).** The bake-off then measured what a read really costs: an Opus critical read at
max effort, run as a subagent, took 20–33 minutes and 1.7–2.8M processed tokens for one chunk of 10–15k tokens; two
thinking turns over five minutes let the subagent's five-minute prompt cache expire, so its context was processed
again; and the CIO's own turns around four launches processed three times what the readers did. One five-hour usage
window held about four launches. At that rate a first ten-year read of a large company (about 230 critical chunks
for Opus alone) would have taken weeks of usage windows: not feasible. The owner chose a narrower full read (every
page of five years, the core sections of the five before, fixed by fiscal year so a missing report is never silently
skipped) and Opus at xhigh; the framework moved the reading loop out of the CIO's context into headless sessions with
a one-hour cache (`reading_driver.py`, now `agent_driver.py`), replaced retyped quotes with anchors, and reuses audited reading across runs
(`FRAMEWORK_CHANGES.md` 3.1.0 item 14). The effect of these changes is measured on the next launches, not assumed;
even with them, a first read is a multi-day job, and a later run reads only what is new.
