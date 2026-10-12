# Research Brief — {company} ({ticker})

Run: `{run_id}` · Created: {created_at} · Research cutoff: **{cutoff}**

> Factual starting point for every specialist. **No investment hypotheses, layer guesses or conclusions belong here.**

## Identity
| Field | Value | Claim |
|---|---|---|
| Legal name | {company} | CIO-C… |
| Ticker / exchange | {ticker} / {exchange} | CIO-C… |
| Listing segment | {segment} | CIO-C… |
| ISIN | {isin} | CIO-C… |
| Reporting currency | {currency} | |
| Fiscal year end | {fy_end} (label FYyyyy = year ending in yyyy) | |

## Price snapshot
- `CIO-C001`: price = _fill_ {currency} at _timestamp_ (_source_)
- `CIO-C002`: shares outstanding = _fill_ (_source, date_)
- `CIO-C003`: market cap = CIO-C001 × CIO-C002 = _fill_

## Conventions for this run
- Units: _e.g. ₹ crore unless stated_
- Consolidated vs. standalone: _known issues, e.g. captive finance subsidiary, listed subsidiaries_
- Group structure leads: _listed parent/subsidiaries, holding companies_
- SME enhanced-scrutiny mode: **{sme_mode}**
- Investment policy (config/investment_policy.json): **{ips_status}**. Hurdle {hurdle}; horizon {horizon} years; benchmark {benchmark}; reference position for the exit-liquidity test {reference_position} {currency}
- Historical depth required (methodology/RESEARCH_PLAYBOOK.md §2): at least 10 fiscal years of financials, 12 quarters of calls and results, 10 years of valuation and industry history. Use more where available; cyclicals need two full cycles.

## User notes
_none_
