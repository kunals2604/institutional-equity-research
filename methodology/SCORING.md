# Scoring Methodology — Business Quality and Investment Attractiveness

<!-- METHODOLOGY_VERSION: 2.1.0 -->
Methodology version **2.1.0** (Claude Code version, with the incomplete-run policy in §8; see `docs/FRAMEWORK_CHANGES.md`). Bump the version whenever dimensions, weights, anchors, gates or the verdict mapping change.

Owner: CIO. Applies to every company and every run. Machine-checked by `scripts/validate_scorecard.py`, which parses the marked tables in this file.

Two scores, always separate:

| Score | Question it answers | Uses today's price? |
|---|---|---|
| **Business Quality (BQ), 0–100** | How good is the underlying business at creating per-share value over time? | **No** |
| **Investment Attractiveness (IA), 0–100** | At the verified price and research cutoff, how attractive is buying the shares on a risk-adjusted basis? | **Yes** |

IA is **not** derived from BQ. A great business can have a low IA, and an imperfect one can have a high IA. Layer-fit scores (see the constitution) are a third, separate measure and are never averaged into either score.

---

## 1. Why fixed weights

A score of 82 must mean roughly the same thing for every company. The dimensions and weights are therefore **fixed across companies**. They are not re-weighted per archetype, because per-company weights let any conclusion be reached by choosing weights after the fact. Archetype differences are handled **inside the anchors**: each dimension says how to judge a cyclical, a grower and a financial institution. They are not handled by changing weights.

The CIO must not change weights for a single company. A methodology change is made here, recorded in `docs/FRAMEWORK_CHANGES.md`, and applies to all future runs. Earlier scores are then flagged as produced under the prior version.

---

## 2. Business Quality dimensions

<!-- BQ_DIMENSIONS:BEGIN -->
| ID | Dimension | Weight |
|---|---|---|
| BQ1 | Unit economics and returns on capital (through-cycle and incremental) | 20 |
| BQ2 | Competitive advantage and industry structure | 20 |
| BQ3 | Reinvestment runway and growth durability | 12 |
| BQ4 | Cash generation and earnings quality | 12 |
| BQ5 | Balance-sheet resilience and downside survivability | 10 |
| BQ6 | Management execution and capital allocation | 10 |
| BQ7 | Governance, integrity and reporting reliability | 10 |
| BQ8 | Structural risk exposure (disruption, regulation, concentration, key-person) | 6 |
<!-- BQ_DIMENSIONS:END -->

### Anchors (score each dimension 0–100, then take the weighted average)

**BQ1 Unit economics and returns on capital**
- 90–100: Returns well above the cost of capital through a full cycle (or for financials, ROE well above cost of equity at normal credit costs). Incremental returns are at least as high. Evidenced for 7+ years.
- 70–89: Clearly above the cost of capital through the cycle. Incremental returns are healthy but less proven or slightly declining.
- 50–69: Around the cost of capital through the cycle, or high only at peaks. For growers: unit economics positive and improving, but not yet proven at scale.
- 30–49: Below the cost of capital on average. For growers: unit economics unproven or negative at contribution level.
- 0–29: Persistent value destruction on capital employed.
- *Cyclicals:* use mid-cycle, never peak. *Growers:* score evidenced contribution, cohort or incremental economics, and reduce confidence rather than inflating the score.

**BQ2 Competitive advantage and industry structure** (owner evidence: moat and industry)
- 90–100: An identified mechanism (switching costs, network effects, cost advantage, scale, intangible or regulatory) is evidenced in pricing, retention, share or returns, and survives the competitor-attack test. The industry is rational.
- 70–89: The mechanism is evidenced but narrower, or the industry is competitive yet disciplined.
- 50–69: A modest or emerging advantage, or advantage offset by tough industry structure.
- 30–49: No demonstrated advantage. Returns depend on the cycle or on management alone.
- 0–29: A commoditized or structurally deteriorating position.

**BQ3 Reinvestment runway and growth durability**
- 90–100: A large reachable market relative to current size. The business can redeploy most of its earnings at high returns for 10+ years.
- 70–89: A solid runway for 5–10 years, or a large runway with lower incremental returns.
- 50–69: A moderate runway; the business will become a payout story within ~5 years.
- 30–49: A mature, saturated or shrinking market.
- 0–29: Structural decline.

**BQ4 Cash generation and earnings quality** (owner evidence: financials and filings)
- 90–100: Cumulative CFO ≈ or > PAT over 5+ years, FCF consistent with owner earnings, no material accrual or capitalization concerns.
- 70–89: Good conversion with explainable gaps (for example, growth working capital).
- 50–69: Uneven conversion; some reliance on other income or one-offs.
- 30–49: Persistent CFO < PAT, rising receivables or inventory, or aggressive capitalization.
- 0–29: Earnings not backed by cash.
- *Financials:* use internal capital generation, credit-cost normalization and provisioning adequacy instead of FCF.

**BQ5 Balance-sheet resilience and downside survivability**
- 90–100: Net cash or very low leverage. Survives a severe downturn without external capital.
- 70–89: Comfortable leverage and maturity profile. Survives a normal downturn.
- 50–69: Leverage acceptable at mid-cycle but uncomfortable at a trough.
- 30–49: Refinancing or covenant risk in a downturn.
- 0–29: Solvency depends on favorable conditions or new capital.
- *Financials:* capital adequacy versus requirements, ALM, liquidity buffers, funding stability.

**BQ6 Management execution and capital allocation** (owner evidence: management and concalls)
- 90–100: Long record of delivering against stated goals. Capital allocation has created per-share value, including M&A, buybacks and dividends at sensible prices.
- 70–89: Reliable delivery with isolated misses. Allocation mostly value-creating.
- 50–69: Mixed delivery, or at least one value-destroying allocation decision.
- 30–49: Repeated misses, goalpost moving, or empire building.
- 0–29: Systematic value destruction.

**BQ7 Governance, integrity and reporting reliability** (owner evidence: filings and management)
- 90–100: No material related-party leakage. Independent board. Fair treatment of minority shareholders. Reliable reporting.
- 70–89: Standard governance with minor, disclosed issues.
- 50–69: Some concerns (elevated related-party flows, weak board independence, unusual remuneration) without evidence of extraction.
- 30–49: Material concerns (evidence of value transfer to insiders, unexplained auditor or CFO changes).
- 0–29: Compromised.

**BQ8 Structural risk exposure** (higher score = lower exposure)
- 90–100: Low exposure to disruption, regulatory discretion, customer or supplier concentration, and key-person risk.
- 50–69: One material exposure.
- 0–29: Several severe exposures, or one existential exposure.

### BQ gates (applied after the weighted average; record every gate considered)
<!-- BQ_GATES:BEGIN -->
| Gate | Trigger | Effect |
|---|---|---|
| G1 | Filings reporting-reliability classification = Highly concerning | BQ ≤ 35 |
| G2 | Filings reporting-reliability classification = Material concerns | BQ ≤ 55 |
| G3 | Management governance classification = Compromised | BQ ≤ 40 |
<!-- BQ_GATES:END -->

---

## 3. Investment Attractiveness dimensions

<!-- IA_DIMENSIONS:BEGIN -->
| ID | Dimension | Weight |
|---|---|---|
| IA1 | Price versus intrinsic-value range (base-case margin of safety) | 25 |
| IA2 | Probability-weighted expected return versus hurdle rate | 20 |
| IA3 | Permanent-loss risk (probability and magnitude) | 20 |
| IA4 | Payoff asymmetry (upside versus downside) | 10 |
| IA5 | Expectations gap (plausibility of what the price implies) | 10 |
| IA6 | Value-realization path (compounding or catalyst clarity and timing) | 5 |
| IA7 | Liquidity, dilution and exit | 5 |
| IA8 | Valuation evidence quality | 5 |
<!-- IA_DIMENSIONS:END -->

Definitions used below:
- **Base value** = the midpoint of the CIO's base-case intrinsic-value range per share.
- **MoS** = (base value − price) / base value.
- **H** = hurdle rate recorded in `run_manifest.json`. The default `0.12` (nominal, INR) is a placeholder. The CIO must state the risk-free rate and equity risk premium used, with sources, or confirm the default with the user.
- **E[IRR]** = the probability-weighted 5-year annualized total return (including dividends and dilution) across bear, base and bull.
- **P(loss)** = the probability of a **permanent** loss of 30 % or more of capital over the holding horizon. Volatility does not count.

**IA1 Margin of safety:** ≥40 % → 90–100; 25–40 % → 75–89; 10–25 % → 60–74; −10 to 10 % → 40–59; −30 to −10 % → 20–39; < −30 % → 0–19.
**IA2 Expected return:** E[IRR] ≥ H+8 pp → 90–100; H+4 to H+8 → 75–89; H to H+4 → 60–74; H−4 to H → 40–59; 0 to H−4 → 20–39; < 0 → 0–19.
**IA3 Permanent-loss risk:** P(loss) remote (<5 %) → 90–100; low (5–10 %) → 75–89; 10–20 % → 55–74; moderate (20–35 %) → 35–54; elevated/high (>35 %) → 0–34. Within a band, a larger loss in the failure case means a lower score.
**IA4 Asymmetry** (probability-weighted upside ÷ probability-weighted downside): ≥3.0 → 90–100; 2.0–3.0 → 70–89; 1.2–2.0 → 50–69; 0.8–1.2 → 30–49; <0.8 → 0–29.
**IA5 Expectations gap** (from reverse valuation): price implies worse than the bear case → 90–100; between bear and base → 70–89; ≈ base → 50–69; between base and bull → 30–49; beyond the bull case → 0–29.
**IA6 Value-realization path:** a compounding engine or hard catalyst visible within 3 years → 80–100; a probable catalyst or slower compounding → 55–79; soft or speculative → 30–54; none → 0–29.
**IA7 Liquidity, dilution and exit:** liquid with no expected dilution → 90–100; minor dilution or liquidity friction → 60–89; material dilution expected or thin liquidity → 30–59; exit impractical or heavy dilution likely → 0–29.
**IA8 Valuation evidence quality:** ≥80 % of material valuation inputs primary-sourced and reconciled → 90–100; 60–80 % → 70–89; 40–60 % → 50–69; <40 % → 0–49.

### IA gates
<!-- IA_GATES:BEGIN -->
| Gate | Trigger | Effect |
|---|---|---|
| G1 | Filings reporting-reliability classification = Highly concerning | IA ≤ 20 |
| G2 | Filings reporting-reliability classification = Material concerns | IA ≤ 45 |
| G3 | Management governance classification = Compromised | IA ≤ 30 |
| G4 | Credible distress risk within 24 months without new capital, and the thesis does not explicitly price distress | IA ≤ 40 |
| G5 | Exiting the reference position would take more than 20 trading days at 20 % of average daily traded value | IA ≤ 70 |
| G6 | Less than 50 % of material valuation inputs primary-sourced | IA ≤ 60 and confidence = Low |
<!-- IA_GATES:END -->

The reference position defaults to `reference_position_inr` in the manifest (₹50 lakh unless the user sets otherwise).

---

## 4. Confidence (reported separately from each score)

| Level | Criteria |
|---|---|
| High | ≥75 % of the material claims behind the score are tier 1–3 and reconciled; no unresolved material contradiction; key assumptions bounded by evidence |
| Medium | 50–75 % primary support, or one unresolved material contradiction, or one key assumption with wide plausible range |
| Low | <50 % primary support, several unresolved contradictions, or the score hinges on an assumption with weak evidence |

Report a **judgment band** with each score (typically ±5 for High, ±8 for Medium, ±12 for Low confidence). This is the uncertainty of the judgment, not measurement precision. Report scores as integers.

---

## 5. Verdict mapping

<!-- VERDICTS:BEGIN -->
- STRONG BUY
- BUY
- SPECULATIVE BUY
- WATCHLIST — WAIT FOR BETTER PRICE
- HOLD / NEUTRAL
- AVOID
- STRONG AVOID
<!-- VERDICTS:END -->

Mapped verdict, applied in order:
1. Any of gates G1 or G3 triggered, or IA < 25 → **STRONG AVOID**
2. IA 25–44 → **AVOID**
3. IA 45–64 → **WATCHLIST — WAIT FOR BETTER PRICE** if BQ ≥ 70, otherwise **HOLD / NEUTRAL**
4. IA 65–79, or IA ≥ 80 with IA confidence = Low → **BUY**
5. IA ≥ 80 with IA confidence High or Medium → **STRONG BUY**
6. If the primary layer is Layer 4 and step 4 or 5 applies → **SPECULATIVE BUY** (the outcome distribution includes near-total loss; size accordingly).

**Override:** the CIO may move the verdict **one notch** from the mapped verdict with a written `override_reason` in `scorecard.json`, for example when a single dominant risk is not well captured by the weighted dimensions. Moving more than one notch is not allowed; change the dimension scores and justify them instead. Notch order: STRONG AVOID < AVOID < HOLD / NEUTRAL = WATCHLIST — WAIT FOR BETTER PRICE < BUY = SPECULATIVE BUY < STRONG BUY.

The verdict is about **fresh capital at today's price**. Position sizing, trading instructions, pair trades and short recommendations are outside this system's scope unless the user asks.

### Valuation status vocabulary
<!-- VALUATION_STATUS:BEGIN -->
- Extremely Cheap
- Cheap
- Reasonably Valued
- Fair-to-Full
- Expensive
- Extremely Expensive
<!-- VALUATION_STATUS:END -->
Guide (price versus base value): ≥40 % below → Extremely Cheap; 20–40 % below → Cheap; within ±15 % → Reasonably Valued; 0–15 % above with little margin of safety → Fair-to-Full; 15–35 % above → Expensive; >35 % above → Extremely Expensive. Where the bands overlap, the CIO states which applies and why.

---

## 6. Mandatory scoring discipline (both scores)

For BQ and IA the final report must state:
1. Each dimension score with a 1–3 sentence rationale citing claim IDs.
2. The weighted raw score, gates considered and applied, and the final score.
3. **What prevents a higher score** (the specific evidence or uncertainty).
4. **What would cause a lower score** (observable developments).
5. Confidence and judgment band.
6. **The evidence most likely to change the score** in the next 12 months.

`scripts/validate_scorecard.py` recomputes the weighted sums, checks gates and the verdict mapping, and rejects inconsistencies.

---

## 7. Calibration

- **Meaning of BQ levels:** 90+ rare, world-class economics with long proven durability; 75–89 high-quality; 60–74 good but with an identifiable structural weakness; 45–59 average; 30–44 weak; <30 impaired.
- **Meaning of IA levels:** 80+ exceptional price-to-value with limited permanent-loss risk (rare); 65–79 attractive; 45–64 fair, with no edge from price; 25–44 unattractive; <25 a high probability of poor or negative real returns, or a disqualifying gate.
- **Cross-company check:** after every new company is scored, the CIO compares it with the two closest companies on `COMPANY_SCOREBOARD.csv` and states in the QC record whether the relative ordering is defensible. If it is not, the CIO revisits the dimension scores. It does not adjust the weights.
- **Drift review:** once 5 or more companies have scores under the same methodology version, review the distribution in `docs/CALIBRATION_LOG.md`. Clustering of all BQ scores in 75–90 indicates anchor inflation.
- **Re-scoring:** a new run of the same company uses the same method. Report changes in each dimension with the evidence that caused them.

---

## 8. Incomplete-run and insufficient-evidence policy (predefined)

Scores are issued only when the evidence can support them. Precise scores are never manufactured to fill a gap.

| Outcome | Trigger | What is produced | Scoreboard / `latest_run.txt` |
|---|---|---|---|
| **complete** | All nine specialists complete (or a gap is accepted under QC), automated and manual QC PASS, and no insufficient-evidence trigger | Full final report, `scorecard.json` with `assessment_status: complete` | Row upserted; pointer updated |
| **insufficient_evidence** | Any of: (a) the price or share count cannot be verified; (b) after retries, two or more of `financials`, `filings` and `valuation` are missing or failed; (c) fewer than 8 of the ≥12 decision-critical claims selected for re-verification could be confirmed from tier 1–4 sources; (d) consolidated financials for the latest completed fiscal year are unavailable | Final report with **no BQ/IA scores or verdict** (`assessment_status: insufficient_evidence`, scores `null`, `insufficient_evidence_reason` stated); the evidence gathered is preserved | **Unchanged.** Any prior valid row and pointer stay. |
| **qc_failed** | Automated or manual QC fails and cannot be fixed in the run | Artifacts preserved; report and scorecard carry `qc_status: FAIL` | **Unchanged** |
| **failed / interrupted** | The run stopped before synthesis (interruption, tool failure) | Whatever artifacts exist, plus a manifest status. Resume with `/research-company --resume <RUN_ID>`. | **Unchanged** |

A failed or insufficient-evidence run never overwrites, blanks or placeholders a previously valid scoreboard row. `scripts/finalize_run.py` applies this table deterministically.
