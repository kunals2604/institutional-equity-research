# Scoring Methodology — Business Quality and Investment Attractiveness

<!-- METHODOLOGY_VERSION: 3.0.0 -->
Methodology version **3.0.0**: the decision is made the way an institutional fund manager makes it (§0): archetype weight profiles fixed in advance, uncertainty never rewarded, non-compensatory must-pass tests, a margin of safety that scales with uncertainty, explicit decision drivers and a conviction measure. 2.4.0 added the scuttlebutt specialist, the independent audit and the document map; 2.3.0 the hurdle-adjusted IA4, the confidence rule and the robustness test; 2.2.0 the quantitative anchor guides. Scorecards without `methodology_version` ≥ 3.0.0 are validated by the 2.x rules (fixed base weights, the 2.x verdict mapping). Bump the version whenever dimensions, weights, anchors, gates or the verdict mapping change.

Owner: CIO. Applies to every company and every run. Machine-checked by `scripts/validate_scorecard.py`, which parses the marked tables in this file.

Two scores, always separate:

| Score | Question it answers | Uses today's price? |
|---|---|---|
| **Business Quality (BQ), 0–100** | How good is the underlying business at creating per-share value over time? | **No** |
| **Investment Attractiveness (IA), 0–100** | At the verified price and research cutoff, how attractive is buying the shares on a risk-adjusted basis? | **Yes** |

IA is **not** derived from BQ. A great business can have a low IA, and an imperfect one can have a high IA. Layer-fit scores (see the constitution) are a third, separate measure and are never averaged into either score.

---

## 0. How the decision is made (not a formula)

A fund manager does not add up analysts' opinions. They ask a sequence of questions, and a "no" to an early one is not rescued by strong answers later. The scorecard follows that sequence; the weighted scores summarize, but **they do not decide alone**.

1. **Is it investable at all?** Gates G1–G6 (§§2–3): unreliable reporting, compromised governance, unpriced distress, no exit, unverifiable valuation inputs. A gate caps the score and, for G1/G3, forces STRONG AVOID.
2. **What kind of opportunity is it?** The primary layer (and any hybrid) is chosen from the four layer assessments *before* scoring. It selects a **weight profile fixed in advance** (§1): the dimensions that decide a compounder are not the ones that decide a cyclical recovery or an option.
3. **How good is the evidence behind each judgment?** Every dimension carries its own confidence. **Uncertainty is never rewarded** (§3b): a high score on weak evidence is shrunk toward neutral; a low score is not raised. A dimension's confidence cannot exceed the evidence quality of the specialists who own it.
4. **Does the thesis pass the archetype's must-pass tests?** (§3c) These are **non-compensatory**: a compounder without returns above its cost of capital, or a cyclical that may not survive the trough, cannot become a buy because other dimensions are strong.
5. **Is the price right for the uncertainty?** A buy requires a **margin of safety that rises as confidence falls** (§5); at Low confidence the answer is to get more evidence or wait, not to buy (Layer 4 aside, which is sized as speculation).
6. **What decides the outcome, and do we see it differently from the market?** The 3–5 **decision drivers** (§6): for each, what the price implies, our evidence-based view, how strongly the evidence supports it, and how much value moves with it. With no difference from the market on a driver that matters, there is no edge from that driver.
7. **How convinced should we be?** **Conviction** (§5) combines the size of the edge (E[IRR] over the hurdle), the payoff asymmetry, the confidence and whether the verdict survives the robustness grid. STRONG BUY needs High conviction.
8. **Judgment, bounded.** The CIO may still move the mapped verdict one notch with a written reason, when a dominant consideration is not captured by the dimensions.

**The CIO weighs evidence, not agents.** No specialist's view counts by default. Each dimension is scored from the evidence its owners produced (§3b lists the owners), weighted by that evidence's quality (tier, corroboration, reconciliation, the auditor's sample), and the weight profile reflects what matters for this archetype, not how many specialists contributed.

## 1. Weight profiles: by archetype, fixed in advance

A score of 82 must mean the same thing for every company **of the same archetype**. Weights are therefore fixed by the methodology for each primary layer (§3a) and never chosen per company: the CIO cannot change a weight, only the evidence-based classification, which is made in the four layer assessments before any score and must be defended there. A hybrid uses the average of its two layers' profiles. The scorecard also reports the score under the **Base** profile, so companies of different archetypes can still be compared.

A methodology change is made here, recorded in `docs/FRAMEWORK_CHANGES.md`, and applies to all future runs. Earlier scores are flagged as produced under the prior version.

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
- **Quantitative guide** (start here; deviate only with a written reason). Non-financials: the spread of 10-year (or through-cycle) median `roic` over the run's WACC: ≥ 15 pp → 90–100; 8–15 pp → 75–89; 3–8 pp → 60–74; 0–3 pp → 45–59; −5–0 pp → 30–44; < −5 pp → 0–29. Lenders: the spread of through-cycle `roe` (at normalized credit cost) over cost of equity: ≥ 8 pp → 90–100; 4–8 → 75–89; 1–4 → 60–74; −1–1 → 45–59; < −1 → 0–44. **Adjust within or one band down** if `incremental_roic_5y` is below half the historical median, or if returns depend on a single peak period.

**BQ2 Competitive advantage and industry structure** (owner evidence: moat and industry; ground truth: scuttlebutt)
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
- **Quantitative guide:** the reachable market (from industry) relative to current revenue, together with the reinvestment rate × incremental return. Reachable market ≥ 5× revenue with reinvestment ≥ 50 % of NOPAT at incremental returns ≥ WACC + 5 pp → 85–100. Reachable market 2–5× with a moderate reinvestment rate → 65–84. Reachable market < 2×, or reinvestment returns ≈ WACC → 45–64. Shrinking reachable market → < 45.

**BQ4 Cash generation and earnings quality** (owner evidence: financials and filings)
- 90–100: Cumulative CFO ≈ or > PAT over 5+ years, FCF consistent with owner earnings, no material accrual or capitalization concerns.
- 70–89: Good conversion with explainable gaps (for example, growth working capital).
- 50–69: Uneven conversion; some reliance on other income or one-offs.
- 30–49: Persistent CFO < PAT, rising receivables or inventory, or aggressive capitalization.
- 0–29: Earnings not backed by cash.
- *Financials:* use internal capital generation, credit-cost normalization and provisioning adequacy instead of FCF.
- **Quantitative guide** (non-financials): 10-year cumulative `cfo_to_pat` ≥ 1.0 and FCF positive in ≥ 8 of 10 years → 85–100; `cfo_to_pat` 0.85–1.0 → 70–84; 0.7–0.85 → 50–69; 0.5–0.7 → 30–49; < 0.5 → 0–29. Subtract up to one band for an adverse forensic screen (rising `accruals_ratio`, `dso` growing faster than revenue for 2+ years, `other_income_share_pbt` > 25 %) that the evidence does not explain. For heavy-growth-capex businesses, judge CFO/EBITDA after tax rather than FCF, and say so. Lenders: `internal_capital_generation` vs. advances growth (self-funding ≥ 1 → upper bands), plus provisioning adequacy (PCR, ECL coverage).

**BQ5 Balance-sheet resilience and downside survivability**
- **Quantitative guide** (non-financials, mid-cycle EBITDA): net cash → 90–100; `net_debt_to_ebitda` ≤ 1× → 75–89; 1–2.5× → 55–74; 2.5–4× → 35–54; > 4× → 0–34. Subtract one band if `interest_coverage` < 3× at trough, or if > 40 % of debt matures within 24 months without committed refinancing. Lenders: capital headroom over the regulatory minimum (Tier-1) ≥ 5 pp with positive ALM gaps in the ≤ 1-year buckets → 85–100; 3–5 pp → 70–84; 1–3 pp → 50–69; < 1 pp or negative short-term ALM gaps → < 50.
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
- **H** = the hurdle: the minimum annual return that compensates for equity risk, used **only** to judge whether an expected return is attractive. It is **not** a research limit. By owner direction, H is derived each run as the **cost of equity** (dated 10-year government bond yield + beta × equity risk premium, inputs cited) from `valuation_tools.py wacc`, unless the IPS sets a fixed value.
- **E[IRR]** = the probability-weighted 5-year annualized total return (including dividends and dilution) across bear, base and bull.
- **P(loss)** = the probability of a **permanent** loss of 30 % or more of capital over the holding horizon. Volatility does not count.

**IA1 Margin of safety:** ≥40 % → 90–100; 25–40 % → 75–89; 10–25 % → 60–74; −10 to 10 % → 40–59; −30 to −10 % → 20–39; < −30 % → 0–19.
**IA2 Expected return:** E[IRR] ≥ H+8 pp → 90–100; H+4 to H+8 → 75–89; H to H+4 → 60–74; H−4 to H → 40–59; 0 to H−4 → 20–39; < 0 → 0–19.
**IA3 Permanent-loss risk:** P(loss) remote (<5 %) → 90–100; low (5–10 %) → 75–89; 10–20 % → 55–74; moderate (20–35 %) → 35–54; elevated/high (>35 %) → 0–34. Within a band, a larger loss in the failure case means a lower score.
**IA4 Asymmetry** (probability-weighted upside ÷ probability-weighted downside, **measured against the price compounded at the hurdle over the horizon**, so that an outcome which merely earns the passage of time is not counted as upside): ≥3.0 → 90–100; 2.0–3.0 → 70–89; 1.2–2.0 → 50–69; 0.8–1.2 → 30–49; <0.8 → 0–29. `valuation_tools.py` reports this ratio as `asymmetry_ratio` whenever the inputs carry `hurdle_rate`, and the undiscounted ratio separately for reference only.
**IA5 Expectations gap** (from reverse valuation): price implies worse than the bear case → 90–100; between bear and base → 70–89; ≈ base → 50–69; between base and bull → 30–49; beyond the bull case → 0–29.
**IA6 Value-realization path:** a compounding engine or hard catalyst visible within 3 years → 80–100; a probable catalyst or slower compounding → 55–79; soft or speculative → 30–54; none → 0–29.
**IA7 Liquidity, dilution and exit:** liquid with no expected dilution → 90–100; minor dilution or liquidity friction → 60–89; material dilution expected or thin liquidity → 30–59; exit impractical or heavy dilution likely → 0–29.
**IA8 Valuation evidence quality:** ≥80 % of material valuation inputs primary-sourced and reconciled → 90–100; 60–80 % → 70–89; 40–60 % → 50–69; <40 % → 0–49.

**Deterministic scoring of IA1, IA2 and IA4.** `scripts/valuation_tools.py price-ladder` maps MoS, E[IRR] and asymmetry to these anchors by linear interpolation within each band. Use its output; deviate only with a written reason. E[IRR] and asymmetry are defined in `methodology/METRIC_DEFINITIONS.md`: E[IRR] is the IRR of the probability-weighted horizon value plus dividends.

### Layer-specific interpretation of IA inputs

| Input | L1 Bedrock Compounder | L2 High-Growth Business | L3 Cyclical / Event-Driven | L4 Venture-Style / Optionality |
|---|---|---|---|---|
| Base value (IA1) | Owner-earnings / long-duration DCF | Scenario DCF to steady-state economics | Normalized or catalyst-adjusted value, discounted for expected time to realization | Probability-weighted, dilution-adjusted outcome value |
| Horizon for E[IRR] (IA2) | Policy horizon (default 5 years) | Policy horizon | Expected time to realization + 1 year (capped at the policy horizon) | Policy horizon. Include financing dilution. |
| Permanent-loss focus (IA3) | Moat erosion, de-rating of a long-duration multiple | Growth stall + de-rating + dilution | Value trap, structural decline, trough solvency | Milestone failure; near-total loss is inherent |
| Realization path (IA6) | Compounding engine visibility | Scaling milestones | Hard or probable catalyst with mechanism | Milestone calendar |

Layer-4 opportunities score lower on IA3 by construction. They can still reach a buy-level IA through asymmetry (IA4) and margin of safety on a probability-weighted value. The resulting verdict is SPECULATIVE BUY with a sizing ceiling (§9). This conservatism is intentional.

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

### 3a. Weight profiles by primary layer (3.0.0)

The **Base** column repeats the dimension tables above and is used when no layer is compelling (primary layer `None`) and for cross-archetype comparison. A hybrid (two layers within 10 points, both ≥ 61) uses the mean of its two profiles.

<!-- WEIGHT_PROFILES:BEGIN -->
| Dimension | Base | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|
| BQ1 | 20 | 22 | 18 | 16 | 14 |
| BQ2 | 20 | 22 | 16 | 12 | 12 |
| BQ3 | 12 | 14 | 22 | 6 | 18 |
| BQ4 | 12 | 10 | 8 | 14 | 6 |
| BQ5 | 10 | 6 | 8 | 22 | 18 |
| BQ6 | 10 | 12 | 12 | 12 | 12 |
| BQ7 | 10 | 10 | 10 | 10 | 14 |
| BQ8 | 6 | 4 | 6 | 8 | 6 |
| IA1 | 25 | 20 | 15 | 25 | 10 |
| IA2 | 20 | 25 | 22 | 18 | 15 |
| IA3 | 20 | 20 | 18 | 20 | 15 |
| IA4 | 10 | 8 | 12 | 12 | 30 |
| IA5 | 10 | 12 | 18 | 5 | 10 |
| IA6 | 5 | 5 | 5 | 12 | 8 |
| IA7 | 5 | 5 | 5 | 4 | 7 |
| IA8 | 5 | 5 | 5 | 4 | 5 |
<!-- WEIGHT_PROFILES:END -->

Why these shifts: a **compounder** (L1) is decided by returns, moat, runway and the allocator, and by the long-run return over the hurdle more than by today's discount. A **grower** (L2) is decided by runway and unit economics, and by whether the growth the price implies is plausible (IA5). A **cyclical or event** (L3) is decided by trough survival (BQ5), earnings quality, the discount to normalized value (IA1) and the realization path (IA6). An **option** (L4) is decided by funding (BQ5), governance (BQ7), the runway, and above all by the payoff asymmetry (IA4).

### 3b. Uncertainty is never rewarded (3.0.0)

Every BQ and IA dimension carries its own `confidence` (High / Medium / Low, by the §4 criteria applied to that dimension's evidence). The **effective score** used in the weighted average and in the must-pass tests is:

- the score itself if it is 50 or below (weak evidence never raises a low score);
- otherwise `50 + (score − 50) × k`, with k by confidence:

<!-- CONFIDENCE_SHRINK:BEGIN -->
- High: 1.0
- Medium: 0.85
- Low: 0.65
<!-- CONFIDENCE_SHRINK:END -->

**Evidence ceiling.** A dimension's confidence cannot be High when a specialist that owns its evidence has a primary-source share below 0.50 or a NOT_LOCATED share above 0.15 (`qc/evidence_stats.json`), or when the auditor's re-verification found a material discrepancy in that specialist's claims (the CIO re-scores after the audit). `build_scorecard.py` applies the first rule.

<!-- DIMENSION_OWNERS:BEGIN -->
| Dimension | Evidence owners |
|---|---|
| BQ1 | financials, moat |
| BQ2 | moat, industry, scuttlebutt |
| BQ3 | industry, financials, scuttlebutt |
| BQ4 | financials, filings |
| BQ5 | financials, filings |
| BQ6 | management, concalls |
| BQ7 | filings, management |
| BQ8 | industry, bear-case, management |
| IA1 | valuation |
| IA2 | valuation |
| IA3 | bear-case, valuation |
| IA4 | valuation |
| IA5 | valuation, concalls |
| IA6 | special-situations, valuation |
| IA7 | valuation |
| IA8 | valuation |
<!-- DIMENSION_OWNERS:END -->

### 3c. Must-pass tests (non-compensatory, 3.0.0)

Evaluated on effective scores. `ALL` applies to every primary layer; a layer code applies when that layer is primary (or part of a hybrid). A failed **business** test caps the verdict at HOLD / NEUTRAL; a failed **price** test caps it at WATCHLIST — WAIT FOR BETTER PRICE. Neither changes the scores: they decide whether a buy is allowed.

<!-- MUST_PASS:BEGIN -->
| Applies to | Test | Kind | Why |
|---|---|---|---|
| ALL | BQ7 >= 50 | business | No buy where governance or reporting raises material concerns |
| ALL | IA2 >= 60 | price | The expected return must at least reach the hurdle |
| None,L1,L2,L3 | IA3 >= 45 | price | Permanent-loss risk must not be elevated (Layer 4 carries it by construction) |
| L1 | BQ1 >= 60 | business | A compounder must earn above its cost of capital through the cycle |
| L1 | BQ2 >= 60 | business | A compounder needs an evidenced advantage |
| L1 | BQ6 >= 55 | business | A compounder needs a capable allocator |
| L2 | BQ3 >= 65 | business | A grower needs a real runway |
| L2 | BQ1 >= 50 | business | A grower's unit economics must be at least positive |
| L2 | BQ5 >= 45 | business | Growth must be fundable |
| L3 | BQ5 >= 55 | business | A cyclical must survive the trough |
| L3 | IA6 >= 55 | price | An event needs at least a probable catalyst with a mechanism |
| L3 | IA1 >= 60 | price | A cyclical buy needs a discount to normalized value |
| L4 | BQ7 >= 60 | business | Binary outcomes need clean governance |
| L4 | BQ5 >= 45 | business | The option must be funded through its milestones |
| L4 | IA4 >= 60 | price | An option must pay asymmetrically against the hurdle |
<!-- MUST_PASS:END -->

---

## 4. Confidence (reported separately from each score)

Confidence measures **how far the evidence supports the score**. It is a property of the research, so it is earned by research and never raised by assertion. **The target for every complete run is High.** A score below High obliges the CIO to run the gap-closure loop (`cio.md` Stage 3) before scoring, and to say in the report which remaining uncertainty is **closable** (evidence that exists but was not obtained) and which is **irreducible** (forecasts, competitor conduct, the rate regime).

| Level | Criteria (all of them for High) |
|---|---|
| High | (a) ≥75 % of the material claims behind the score are tier 1–3 and reconciled; (b) no unresolved material contradiction bearing on the score; (c) every closable gap in the specialists' Method Coverage Checklists that bears on the score has been re-attempted in a CIO follow-up (gap-closure loop) and is now closed or documented as unobtainable; (d) **IA:** `valuation_tools.py robustness` maps the same verdict across the default grid (base value ±15 %, 10 pp of probability moved to bear or bull, hurdle ±1 pp); **BQ:** every dimension stays inside its anchor band under the plausible alternative for its key assumption (the CIO states the alternative and the result) |
| Medium | (a) is 50–75 %; or exactly one of (b)–(d) fails |
| Low | <50 % primary support; or two or more of (b)–(d) fail; or the score hinges on an assumption with weak evidence |

The report's *Confidence Assessment* section shows each criterion as met or not met, with its evidence.

**Per-dimension confidence (3.0.0).** The same criteria are applied to each dimension's own evidence, and each dimension records its confidence. It drives the effective score (§3b) and is capped by the evidence ceiling. The block-level confidence of BQ and of IA (above) summarizes them and cannot be higher than the confidence of the dimensions carrying most of the profile's weight.

Report a **judgment band** with each score (typically ±5 for High, ±8 for Medium, ±12 for Low confidence). This is the uncertainty of the judgment, not measurement precision. Report scores as integers, rounded **half up** (`research_lib.round_half_up`, used by every tool and validator).

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

Mapped verdict (3.0.0), applied in order:
1. Gate G1 or G3 triggered, or IA < 25 → **STRONG AVOID**
2. IA 25–44 → **AVOID**
3. IA 45–64 → **WATCHLIST — WAIT FOR BETTER PRICE** if BQ ≥ 70, otherwise **HOLD / NEUTRAL**
4. IA ≥ 65 (a buy candidate), then:
   1. a failed **business** must-pass test → **HOLD / NEUTRAL**;
   2. a failed **price** must-pass test, or the margin of safety below the **required margin of safety** for the layer and IA confidence (table below; "none" means no buy at that confidence) → **WATCHLIST — WAIT FOR BETTER PRICE**;
   3. primary layer Layer 4 → **SPECULATIVE BUY** (the outcome distribution includes near-total loss; size accordingly);
   4. IA ≥ 80 with IA confidence High or Medium **and conviction High** → **STRONG BUY**;
   5. otherwise → **BUY**.

**Required margin of safety** (MoS against the base value; a hybrid takes the stricter of its two layers):

<!-- REQUIRED_MOS:BEGIN -->
| Layer | High | Medium | Low |
|---|---|---|---|
| None | 0.15 | 0.25 | none |
| L1 | 0.00 | 0.10 | none |
| L2 | 0.10 | 0.20 | none |
| L3 | 0.20 | 0.30 | none |
| L4 | 0.30 | 0.40 | 0.50 |
<!-- REQUIRED_MOS:END -->

A compounder bought near fair value can still compound above the hurdle (the IA2 must-pass checks that), so its requirement is lowest; a cyclical or event case must pay for being wrong about timing; an option is valued on a probability-weighted outcome tree and needs the widest cushion.

**Conviction** (reported with the verdict; STRONG BUY requires High). Points:

<!-- CONVICTION:BEGIN -->
- edge_pp: 8=3, 4=2, 0=1
- asymmetry: 3.0=2, 1.5=1
- confidence: High=2, Medium=1, Low=0
- robust: 1
- high_at: 6
- medium_at: 3
<!-- CONVICTION:END -->

*edge_pp* is E[IRR] minus the hurdle in percentage points (≥ 8 pp scores 3, ≥ 4 pp 2, ≥ 0 pp 1, below 0 nothing); *asymmetry* is the hurdle-adjusted ratio; *confidence* is the IA confidence; *robust* scores 1 when the `robustness` grid maps one verdict. Conviction is High at 6 points or more, Medium at 3–5, Low below 3. Conviction is not confidence: confidence says how well the evidence supports the scores; conviction says how large and reliable the edge is.

**2.x mapping (runs before 3.0.0, kept for re-validation):** G1/G3 or IA < 25 → STRONG AVOID; IA 25–44 → AVOID; IA 45–64 → WATCHLIST if BQ ≥ 70, else HOLD / NEUTRAL; IA 65–79, or IA ≥ 80 with Low IA confidence → BUY; IA ≥ 80 with High or Medium IA confidence → STRONG BUY; Layer 4 primary with a buy → SPECULATIVE BUY. Fixed Base weights, no shrinkage, no must-pass tests.

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
1. Each dimension score, its confidence and its effective score, with a 1–3 sentence rationale citing claim IDs.
2. The weight profile used (and the Base-profile score for comparison), the weighted raw score, gates considered and applied, and the final score.
2a. **The must-pass table** (each applicable test, its effective score and pass / fail), the **required margin of safety** against the actual one, and **conviction** with its points.
2b. **The decision drivers** (3–5): driver · what the price implies · our view · the evidence (claim IDs) and its confidence · the value at stake per share across the plausible range (from the valuation sensitivity) · the signpost that will resolve it.
3. **What prevents a higher score** (the specific evidence or uncertainty).
4. **What would cause a lower score** (observable developments).
5. Confidence and judgment band.
6. **The evidence most likely to change the score** in the next 12 months.

`scripts/build_scorecard.py` computes all of this from the CIO's judgments; `scripts/validate_scorecard.py` recomputes it (weight profile, effective scores, gates, must-pass tests, required margin of safety, conviction, verdict mapping) and rejects inconsistencies.

---

## 7. Calibration

- **Meaning of BQ levels:** 90+ rare, world-class economics with long proven durability; 75–89 high-quality; 60–74 good but with an identifiable structural weakness; 45–59 average; 30–44 weak; <30 impaired.
- **Meaning of IA levels:** 80+ exceptional price-to-value with limited permanent-loss risk (rare); 65–79 attractive; 45–64 fair, with no edge from price; 25–44 unattractive; <25 a high probability of poor or negative real returns, or a disqualifying gate.
- **Cross-company check:** after every new company is scored, the CIO compares it with the two closest companies on `COMPANY_SCOREBOARD.csv` and states in the QC record whether the relative ordering is defensible. If it is not, the CIO revisits the dimension scores. It does not adjust the weights.
- **Drift review:** once 5 or more companies have scores under the same methodology version, review the distribution in `docs/CALIBRATION_LOG.md`. Clustering of all BQ scores in 75–90 indicates anchor inflation.
- **Re-scoring:** a new run of the same company uses the same method. Report changes in each dimension with the evidence that caused them.
- **Forecast calibration:** falsifiable predictions (§10) are scored when they fall due (`scripts/compare_runs.py` lists them). Track the hit rate by probability bucket in `docs/CALIBRATION_LOG.md`. A process whose "70 %" predictions come true 40 % of the time is overconfident, and its confidence levels must be lowered.

---

## 8. Incomplete-run and insufficient-evidence policy (predefined)

Scores are issued only when the evidence can support them. Precise scores are never manufactured to fill a gap.

| Outcome | Trigger | What is produced | Scoreboard / `latest_run.txt` |
|---|---|---|---|
| **complete** | All ten specialists complete (nine for runs before 2.4.0), or a gap is accepted under QC; the independent audit has run and every Critical and Major finding is resolved (Critical ones confirmed Closed by a re-audit); automated and manual QC PASS; and no insufficient-evidence trigger | Full final report, `scorecard.json` with `assessment_status: complete` | Row upserted; pointer updated |
| **insufficient_evidence** | Any of: (a) the price or share count cannot be verified; (b) after retries, two or more of `financials`, `filings` and `valuation` are missing or failed; (c) fewer than 8 of the ≥12 decision-critical claims selected for re-verification could be confirmed from tier 1–4 sources; (d) consolidated financials for the latest completed fiscal year are unavailable | Final report with **no BQ/IA scores or verdict** (`assessment_status: insufficient_evidence`, scores `null`, `insufficient_evidence_reason` stated); the evidence gathered is preserved | **Unchanged.** Any prior valid row and pointer stay. |
| **qc_failed** | Automated or manual QC fails and cannot be fixed in the run | Artifacts preserved; report and scorecard carry `qc_status: FAIL` | **Unchanged** |
| **failed / interrupted** | The run stopped before synthesis (interruption, tool failure) | Whatever artifacts exist, plus a manifest status. Resume with `/research-company --resume <RUN_ID>`. | **Unchanged** |

A failed or insufficient-evidence run never overwrites, blanks or placeholders a previously valid scoreboard row. `scripts/finalize_run.py` applies this table deterministically.

---

## 9. Investment policy inputs and position-risk profile

The **Investment Policy Statement** in `config/investment_policy.json` holds the hurdle rate, horizon, benchmark, reference position, liquidity rule and risk limits. `scripts/new_run.py` snapshots it into `run_manifest.json`. The owner has confirmed the policy: **no position or risk limits**, and the hurdle derived per run. With no risk limits, no sizing ceiling is computed. The position-risk profile still reports the facts an investor needs (bear-case loss, permanent-loss band, liquidity, factor exposures).

Every complete run includes a **position-risk profile** (in the report and in `scorecard.json`). It is *inputs for sizing*, not a trade instruction:

| Item | Definition |
|---|---|
| Bear-case loss | (price − bear-case horizon value incl. dividends) ÷ price, if positive |
| Permanent-loss band | Qualitative band for P(loss ≥ 30 %) (constitution §4) |
| Days to exit the reference position | reference position ÷ (ADTV × max participation), from the IPS liquidity rule |
| Key factor exposures | The 2–4 macro or factor drivers that would correlate this holding with others (rates, crude, rural demand, INR, credit cycle…) |
| **Sizing ceiling** (only if the IPS sets risk limits) | min(IPS max position %, IPS max loss per position % ÷ bear-case loss, liquidity cap). Computed by `scripts/valuation_tools.py sizing-ceiling`. SPECULATIVE BUY positions are additionally capped at the IPS `speculative_max_position_pct`. |

Position sizing beyond this ceiling, trading instructions, pair trades and short recommendations remain outside the system's scope unless the user asks for them.

## 10. Decision outputs (complete runs)

1. **Decision triggers (price ladder).** Using `valuation_tools.py price-ladder` with the run's scenario values and the non-price IA dimensions held constant, state the price at or below which the mapped verdict would become BUY, and STRONG BUY (if reachable), and above which it would become AVOID. From 3.0.0 the ladder applies the whole decision sequence at each price (weight profile, effective scores, must-pass tests, required margin of safety, conviction), so `buy_below` is the highest price at which every condition for a buy holds. These are hypothetical triggers, not limit orders. They go stale when the evidence changes.
2. **Falsifiable predictions (decision journal).** Write 3–7 specific, measurable, dated predictions that the thesis implies, each with a probability between 0.05 and 0.95. For example: "FY2027 consolidated EBITDA margin ≥ 18 % (p = 0.65)". They are recorded in `scorecard.json` and resolved by the next run of the company.
3. **Next review date.** Within 12 months, and earlier if a monitored trigger or a scheduled event (results, regulatory decision, record date) could change the verdict.
