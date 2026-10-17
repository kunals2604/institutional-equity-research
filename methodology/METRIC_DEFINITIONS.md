# Metric Definitions — One Definition per Number

Every agent uses these definitions. A ratio that means different things in different reports is how a research process ends up comparing apples with oranges. (The legacy TVS run used two costs of capital in one report and one "17.2 % ROCE" with two meanings.)

- The **ledger `metric` column** must contain a key from the block below, a `cagr_<item>_<n>y` key (for example `cagr_revenue_10y`), or `other:<short_name>` for anything not listed.
- `scripts/fin_metrics.py` computes the derived metrics from `financial_history.csv` using exactly these formulas.
- `scripts/reconcile_numbers.py` groups ledger claims by `(metric, period, basis, unit)` to find numerical conflicts between agents.

**Conventions**
- **Periods:** `FY2025` = the fiscal year ending in 2025 (for Indian companies, April 2024 – March 2025). Quarters: `Q1FY2026`. TTM: `TTM-Q2FY2026`.
- **Averages:** ratios on balance-sheet denominators use the **average of opening and closing** balances when both exist. If only the closing balance is available, the value is labeled `(closing)`.
- **Basis:** state `consolidated` or `standalone` for every figure. For groups with a captive lender or insurer, compute industrial metrics on an ex-financial-services basis (`segment:<name>`) where disclosures allow.
- **Signs:** cash outflows (capex, dividends, buybacks, acquisitions) are recorded as **positive** numbers in `financial_history.csv`. Exceptional items are positive when they are gains.
- **Leases (Ind AS 116 / IFRS 16):** EBITDA after Ind AS 116 excludes lease rentals. Comparisons across the FY2020 transition must say whether figures are pre- or post-lease. `net_debt` excludes lease liabilities; `net_debt_incl_leases` includes them.

<!-- METRIC_KEYS:BEGIN -->
- revenue — Revenue from operations, net of indirect taxes; excludes other income
- cogs — Cost of materials consumed + purchases of stock-in-trade ± change in inventories
- employee_cost — Employee benefits expense
- other_opex — Other operating expenses (excluding depreciation and finance cost)
- ebitda — revenue − cogs − employee_cost − other_opex (state pre/post Ind AS 116); excludes other income
- depreciation — Depreciation and amortisation expense
- ebit — ebitda − depreciation; operating profit excluding other income
- other_income — Non-operating income (treasury, interest, dividends, gains)
- interest_expense — Finance costs (for lenders: interest expended)
- exceptional_items — Exceptional / extraordinary items (gain positive)
- pbt — Profit before tax
- tax — Total tax expense (current + deferred)
- pat — Profit after tax including non-controlling interests
- pat_attributable — Profit attributable to owners of the parent
- total_assets — Total assets
- current_assets — Total current assets
- current_liabilities — Total current liabilities
- cash_and_equivalents — Cash, bank balances and liquid investments readily available (state what is included)
- current_investments — Current investments
- total_debt — Borrowings, current + non-current, excluding lease liabilities
- lease_liabilities — Lease liabilities (current + non-current)
- total_equity — Equity attributable to owners of the parent
- minority_interest_bs — Non-controlling interests (balance sheet)
- trade_receivables — Trade receivables (net of expected-credit-loss allowance)
- inventories — Inventories
- trade_payables — Trade payables
- net_fixed_assets — Net property, plant and equipment (state whether right-of-use assets are included)
- cwip — Capital work-in-progress
- goodwill_intangibles — Goodwill + other intangible assets (+ intangibles under development)
- cfo — Net cash from operating activities
- capex — Purchase of PP&E and intangibles (positive = cash spent)
- acquisitions — Cash paid for acquisitions / investments in subsidiaries (positive)
- dividends_paid — Dividends paid to owners (positive)
- buybacks — Cash spent on share buybacks (positive)
- equity_issued — Cash raised from equity issuance (positive)
- shares_basic — Weighted-average basic shares
- shares_diluted — Diluted share count (state year-end or weighted)
- dps — Dividend per share declared for the year
- price — Share price at a stated timestamp
- market_cap — price × shares outstanding at the same timestamp
- interest_income — Lenders: interest earned
- nii — Lenders: interest_income − interest_expense
- fee_income — Lenders: fees, commissions and other non-interest operating income
- opex — Lenders: operating expenses (employee + other, excluding provisions)
- ppop — Lenders: nii + fee_income − opex (pre-provision operating profit)
- provisions — Lenders: impairment on financial instruments / loan-loss provisions + write-offs charged to P&L
- advances — Lenders: gross loans on book (or on-book AUM; state which)
- aum — Lenders: assets under management including off-book (securitized, co-lent)
- borrowings — Lenders: borrowings excluding deposits
- deposits — Lenders: customer deposits
- casa_ratio — Banks: CASA deposits ÷ total deposits
- gnpa — Lenders: gross non-performing / Stage-3 assets (amount)
- nnpa — Lenders: net non-performing / Stage-3 assets after provisions (amount)
- crar — Lenders: capital to risk-weighted assets ratio (regulatory)
- tier1_ratio — Lenders: Tier-1 capital ratio (regulatory)
- cost_of_funds — Lenders: interest_expense ÷ average interest-bearing liabilities
- yield_on_advances — Lenders: interest_income on loans ÷ average advances
- revenue_growth — revenue_t ÷ revenue_{t−1} − 1
- ebitda_margin — ebitda ÷ revenue
- ebit_margin — ebit ÷ revenue
- pat_margin — pat ÷ revenue
- effective_tax_rate — tax ÷ pbt
- capital_employed — total_assets − current_liabilities
- roce — ebit ÷ average capital_employed (pre-tax)
- invested_capital — total_equity + minority_interest_bs + total_debt + lease_liabilities − cash_and_equivalents − current_investments
- nopat — ebit × (1 − effective_tax_rate)
- roic — nopat ÷ average invested_capital
- roe — pat_attributable ÷ average total_equity
- roa — pat ÷ average total_assets
- incremental_roic_3y — (nopat_t − nopat_{t−3}) ÷ (invested_capital_{t−1} − invested_capital_{t−4})
- incremental_roic_5y — (nopat_t − nopat_{t−5}) ÷ (invested_capital_{t−1} − invested_capital_{t−6})
- net_debt — total_debt − cash_and_equivalents − current_investments
- net_debt_incl_leases — net_debt + lease_liabilities
- net_debt_to_ebitda — net_debt ÷ ebitda
- interest_coverage — ebit ÷ interest_expense
- cfo_to_pat — cfo ÷ pat
- cfo_to_ebitda — cfo ÷ ebitda
- fcf — cfo − capex (free cash flow to the firm before acquisitions; state treatment of lease payments)
- fcf_to_pat — fcf ÷ pat
- dso — trade_receivables ÷ revenue × 365
- dio — inventories ÷ cogs × 365 (revenue if cogs unavailable; labeled)
- dpo — trade_payables ÷ cogs × 365 (revenue if cogs unavailable; labeled)
- ccc — dso + dio − dpo
- capex_to_revenue — capex ÷ revenue
- capex_to_depreciation — capex ÷ depreciation
- accruals_ratio — (pat − cfo) ÷ average total_assets
- other_income_share_pbt — other_income ÷ pbt
- exceptional_share_pbt — exceptional_items ÷ pbt
- goodwill_to_equity — goodwill_intangibles ÷ total_equity
- payout_ratio — dividends_paid ÷ pat_attributable
- reinvestment_rate — (capex − depreciation + Δ net working capital + acquisitions) ÷ nopat
- maintenance_capex — Estimate of capex required to sustain current capacity and competitive position (ESTIMATE; state the method)
- owner_earnings — pat_attributable + depreciation − maintenance_capex − Δ working capital required (ESTIMATE where maintenance capex is estimated)
- eps — pat_attributable ÷ shares_basic
- bvps — total_equity ÷ shares_diluted
- fcf_per_share — fcf ÷ shares_diluted
- share_count_change — shares_diluted_t ÷ shares_diluted_{t−1} − 1 (dilution if positive)
- beneish_m_score — Beneish (1999) eight-variable M-score; a screen, not a verdict
- piotroski_f_score — Piotroski (2000) nine-signal F-score; a screen, not a verdict
- nim — Lenders: nii ÷ average advances (state if on average total assets instead)
- nii_to_avg_assets — Lenders: nii ÷ average total_assets
- cost_to_income — Lenders: opex ÷ (nii + fee_income)
- credit_cost — Lenders: provisions ÷ average advances
- gnpa_ratio — Lenders: gnpa ÷ advances
- nnpa_ratio — Lenders: nnpa ÷ (advances − (gnpa − nnpa))
- pcr — Lenders: 1 − nnpa ÷ gnpa (provision coverage, excluding technical write-offs)
- leverage_assets_to_equity — average total_assets ÷ average total_equity
- advances_growth — advances_t ÷ advances_{t−1} − 1
- borrowings_growth — borrowings_t ÷ borrowings_{t−1} − 1
- deposits_growth — deposits_t ÷ deposits_{t−1} − 1
- internal_capital_generation — roe × (1 − payout_ratio)
- pe — price ÷ eps (state trailing / forward and the EPS basis)
- pb — price ÷ bvps
- ev — market_cap + total_debt + lease_liabilities (if EBITDA is post-lease) + minority_interest_bs − cash_and_equivalents − current_investments − non-operating assets (state each adjustment)
- ev_ebitda — ev ÷ ebitda (consistent lease treatment)
- ev_ebit — ev ÷ ebit
- ev_sales — ev ÷ revenue
- fcf_yield — fcf ÷ ev (firm) or (fcf − interest after tax) ÷ market_cap (equity); state which
- dividend_yield — dps ÷ price
- risk_free_rate — Yield on the 10-year government bond in the reporting currency, dated
- equity_risk_premium — Equity risk premium used, with its source and date
- beta — Equity beta: method (regression window and index, or bottom-up) stated
- cost_of_equity — risk_free_rate + beta × equity_risk_premium (+ any premium, justified)
- cost_of_debt — Pre-tax marginal borrowing cost
- wacc — Weighted average cost of capital at market-value weights
- terminal_growth — Perpetual growth rate after the explicit forecast period
- value_per_share — Intrinsic value per share from a stated model
- intrinsic_value_low — Low end of the defended intrinsic value range per share
- intrinsic_value_high — High end of the defended intrinsic value range per share
- margin_of_safety — (base value − price) ÷ base value
- expected_irr — Annualized return implied by the probability-weighted horizon value plus dividends versus price (see below)
- asymmetry_ratio — Probability-weighted upside ÷ probability-weighted downside versus the price compounded at the hurdle over the horizon (IA4)
- implied_growth — Revenue/FCF growth that equates a DCF to the price (reverse DCF)
- implied_margin — Steady-state margin that equates a DCF to the price
- adtv — Average daily traded value over a stated window (for example 90 trading days)
- free_float — Shares not held by promoters/promoter group ÷ total shares
- promoter_holding — Promoter and promoter-group shareholding %
- promoter_pledge — Promoter shares pledged/encumbered ÷ promoter shares
- fii_holding — Foreign portfolio investor holding %
- dii_holding — Domestic institutional investor holding %
- max_drawdown — Largest peak-to-trough share-price decline over a stated window
- tsr — Total shareholder return (price change + dividends reinvested) over a stated window, annualized
- market_share — Company share of a defined market (state volume/value, geography, segment, source)
- industry_volume — Industry volume for a defined market and period
- industry_revenue — Industry revenue for a defined market and period
- tam — Total addressable market (state definition and source)
- sam — Serviceable / reachable market (state derivation)
- capacity — Installed capacity (units stated)
- capacity_utilization — Production ÷ capacity
- volume — Company sales volume (units stated)
- asp — Average selling price = revenue (segment) ÷ volume
<!-- METRIC_KEYS:END -->

---

## Valuation and return definitions (used by `scripts/valuation_tools.py`)

| Term | Definition |
|---|---|
| **Base value** | Midpoint of the CIO's base-case intrinsic value range per share. Layer-specific: L1 owner-earnings/DCF; L2 scenario DCF; L3 normalized or catalyst-adjusted value, discounted for time to realization; L4 probability-weighted, dilution-adjusted value |
| **Expected IRR (E[IRR])** | The annualized return that equates today's price with the **probability-weighted** horizon value plus probability-weighted dividends (IRR of expected cash flows). The probability-weighted mean of the scenario IRRs is reported alongside for reference, but E[IRR] is the decision metric. |
| **Asymmetry ratio** | Σ pᵢ·max(Vᵢ − B, 0) ÷ Σ pᵢ·max(B − Vᵢ, 0), where Vᵢ is scenario horizon value per share plus dividends and **B = P·(1+H)^T**, the price compounded at the hurdle H over the horizon T. Comparing horizon values with today's price P instead (the pre-2.3.0 definition, still reported as `asymmetry_ratio_undiscounted`) counts a return below the hurdle as upside. |
| **Horizon value convention** | Scenario horizon value = scenario value today × (1+H)^T − future value of interim dividends (the price converges to scenario value by the horizon). Built by `valuation_tools.py scenario-build`. |
| **Margin of safety** | (base value − price) ÷ base value |
| **Normalized earnings (cyclicals)** | Mid-cycle margin (average over at least one full cycle, excluding the single best and worst years, or stated otherwise) × current or normalized revenue capacity. Never peak-year earnings. |
| **Maintenance capex** | Choose and state one method: (a) depreciation adjusted for inflation of replacement cost; (b) management disclosure (a MANAGEMENT STATEMENT, to be tested); (c) capex in no-growth years; (d) capacity-based (cost to maintain units × capacity). Report as an ESTIMATE with a range. |
| **Reverse DCF** | Hold the cost of capital, terminal assumptions and reinvestment efficiency fixed and solve for the growth (or margin) that makes value per share equal to the price. Always report the assumption chain. |
| **Expected-return decomposition** | Annual return ≈ (1 + EPS growth)·(1 + annualized multiple change)·(1 − annual dilution) − 1 + dividend yield. Used as a sanity check on the DCF. |

## Forensic screens (computed when inputs exist; never a verdict on their own)

| Screen | Use |
|---|---|
| `accruals_ratio` | Persistently positive and rising values (profit outrunning cash) warrant explanation |
| `cfo_to_pat` (3/5/10-year cumulative) | Below about 0.8 over 5+ years needs a specific explanation (growth working capital, an acquisition) |
| `dso` / `dio` trend vs. revenue growth | Receivables or inventory growing faster than revenue for 2+ years is a classic early-warning sign |
| `other_income_share_pbt`, `exceptional_share_pbt` | A high or rising dependence on non-operating profit |
| `capex_to_depreciation` with CWIP ageing | Persistent CWIP that is not capitalized can point to stranded or impaired projects |
| `beneish_m_score` | Above about −1.78 (eight-variable model) is the original "likely manipulator" zone; many practitioners use −2.22. Indian-context false positives are common for high-growth firms. |
| `piotroski_f_score` | 0–3 weak, 7–9 strong financial momentum; most useful for Layer 3 and value candidates |
