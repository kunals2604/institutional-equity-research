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

## Documents (Stage 0 acquisition: `corpus/DOCUMENT_MAP.md`)
- Sources indexed: NSE _n_, BSE _n_, IR site _n_, Internet Archive _n_ (`corpus/index_summary.json`; failed endpoints: _none / list_)
- Coverage against the depth standard: annual reports _n of 15_ · transcripts _n of 24_ · presentations _n_ · results _n_ · shareholding _n_
- Cross-check flags (local corpus vs. exchange copies) and which copy to read: _none / list_
- Missing core documents and where they were searched: _none / list_
- Text layer: every core document converted (`doc_text.py`); pages to read visually are listed in the map
- Structured data: exchange XBRL facts `calc/xbrl_facts.csv` (_years_); exchange close and liquidity `calc/cio_price.json`; structured exchange filings `corpus/STRUCTURED.md` (BRSR _years_, voting results _meetings_, audit-opinion statements _years_)
- Librarian: documents found and added _n_; still unobtainable _list with the attempt log in `corpus/librarian_log.md`_

## Reading stage (Stage 0b: `corpus/reading/COVERAGE.md`)
- Scope: annual reports _FYxxxx–FYyyyy_ (history scope: _none / years_), transcripts _n quarters_, presentations _n quarters_, exchange filings _n_
- Plan: _n_ pages, _n_ chunks (_n_ critical, read twice), about _n_k tokens; calibration status (`methodology/MODEL_POLICY.md`): _pending (every chunk read by both models) / passed (single-read classes: list)_
- Result: pages read _n_, repeat _n_, structured _n_, out of scope _n_, pending **0**; dossiers in `corpus/dossiers/` and one reading pack per specialist

## User notes
_none_
