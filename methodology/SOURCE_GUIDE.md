# Source Guide — Where to Find What

Discovery map for primary evidence, oriented to Indian listed companies, with global equivalents. **Tiers follow the constitution's evidence hierarchy.** Site structures and regulation numbers change, so verify the current location when retrieving. Record retrieval failures in the missing-evidence list rather than substituting from memory.

## 0. Local corpus first: FilingForge library

The owner's FilingForge app downloads exchange filings (annual reports, results, concall transcripts, investor presentations, corporate actions, insider/SAST, AGM documents) into `~/Documents/FilingForgeLibrary/<TICKER>/` (path in `config/data_sources.json`). Each PDF has a Markdown twin, about 25× fewer tokens. `scripts/corpus.py` catalogs it, filters out notices (meeting schedules, trading-window closures, newspaper ads), infers fiscal periods, checks coverage against the depth standard, searches across all years, and maps a passage to its PDF page for citation.

- **Tier:** that of the underlying filing (annual reports and results tier 1; presentations tier 3; transcripts tier 4).
- **Citation:** `source_url_or_id = FilingForge:<doc_id>` (the exchange announcement ID in the file's metadata); `locator = p.<PDF page>` from `corpus.py locate`, or `MD line <n>` if the page cannot be located (confidence M).
- **Limits:** downloads are triggered manually in the app, which exposes no API. Markdown has no page markers and can drop table structure, so check decision-critical tables against the PDF page. Documents flagged `thin-extraction` must be read from the PDF.

## 1. Company and exchange disclosures (India)

| Data item | Primary source (tier) | Where | Typical history | Notes |
|---|---|---|---|---|
| Annual reports | Company (1) | Company IR site; BSE and NSE company pages (annual reports sections) | 10–15+ years on many IR sites / exchange archives | Older reports are often scanned PDFs. Read with the Read tool, page by page. |
| Quarterly / annual results | Exchange filings (1) | BSE / NSE corporate filings (financial results, under the SEBI LODR financial-results regulation) | Many years | Check consolidated vs. standalone and audited vs. limited-review |
| Investor presentations, earnings-call transcripts and audio | Company (3/4) | BSE/NSE announcements (LODR disclosure of material information), company IR pages | Transcripts widely available for recent years; older coverage varies | Record when transcripts are unavailable before a certain year |
| Shareholding pattern | Exchange (1) | BSE/NSE shareholding pattern filings (quarterly) | Many years | Promoter, FPI, DII, public, plus pledge columns |
| Pledges / encumbrance, substantial acquisitions | Exchange (1) | SAST disclosures on BSE/NSE | Many years | |
| Insider trading disclosures | Exchange (1) | SEBI PIT disclosures on BSE/NSE | Many years | Context matters: ESOP sales vs. open-market selling |
| Corporate governance reports | Exchange (1) | Quarterly governance compliance filings; annual CG report in the annual report | | |
| Material events (acquisitions, litigation, auditor or KMP changes, credit-rating changes) | Exchange (1) | BSE/NSE announcements | | Auditor resignations must include reasons; read them |
| Schemes of arrangement (mergers, demergers) | Exchange / NCLT (1–2) | Exchange announcements, scheme documents, NCLT orders | | Timeline: board → exchange observation → NCLT → effective date |
| Offer documents (IPO / QIP / rights) | SEBI / exchange (1) | SEBI public-issues filings, exchange offer documents | | Restated pre-listing financials, objects of the issue, risk factors |
| Monitoring-agency reports (use of IPO proceeds) | Exchange (1) | Exchange filings | | Critical for SME and recent IPOs |
| XBRL financial data | Exchange (1) | BSE/NSE XBRL filings | | Machine-readable; verify against the PDF |
| BRSR (sustainability) | Company (1) | Within the annual report for covered companies | Recent years only | Material ESG risks (safety, environment, labour) |

## 2. Regulators, courts and registries (India)

| Item | Source (tier) | Where |
|---|---|---|
| SEBI orders, adjudications, settlements | 2 | sebi.gov.in (enforcement / orders) |
| RBI regulations, penalties, banking statistics | 2 | rbi.org.in; statistics at dbie.rbi.org.in |
| IRDAI (insurance) data and orders | 2 | irdai.gov.in |
| Competition Commission orders | 2 | cci.gov.in |
| Company master data, charges (secured borrowings), directors | 2 | mca.gov.in (MCA21). Some data is free; filings may need paid access. |
| Insolvency / company-law tribunal orders | 2 | NCLT / NCLAT websites; ecourts.gov.in for district and high courts; the Supreme Court site for SC judgments |
| Tax disputes (income tax, indirect tax) | 2 | Tribunal and court records where published; otherwise the company's contingent-liability notes |
| Pharma regulatory actions | 2 | US FDA databases (warning letters, inspection classifications, approvals); CDSCO |
| Real-estate project registrations | 2 | State RERA portals |
| Telecom subscriber and industry data | 2 | trai.gov.in |
| Power-sector statistics | 2 | cea.nic.in |
| Petroleum data | 2 | ppac.gov.in |
| Mutual-fund industry data | 2 / 5 | amfiindia.com |

## 3. Credit ratings (tier 5, but often the best independent view of liquidity and covenants)

CRISIL Ratings (crisilratings.com), ICRA (icra.in), CARE Ratings (careratings.com), India Ratings & Research (indiaratings.co.in), Acuité (acuite.in), Brickwork. Rating **rationale** documents disclose liquidity, debt structure, group support and key sensitivities. Track rating and outlook history over 5–10 years.

## 4. Industry and market data

| Sector | Sources (tier) |
|---|---|
| Automobiles | SIAM (siam.in, 5), FADA retail data (fada.in, 5), VAHAN registrations dashboard (parivahan.gov.in, 2) |
| Telecom | TRAI monthly subscription reports (2) |
| Banking / NBFC | RBI statistical releases, Financial Stability Report (2) |
| Insurance | IRDAI annual reports and monthly data (2) |
| Asset management | AMFI monthly data (5) |
| Power, oil and gas | CEA, PPAC (2) |
| Cement, steel and other commodities | Industry associations and ministry data (2/5); listed-peer filings (1) |
| Indices and valuations | NSE index factsheets and index P/E history (niftyindices.com, 5) |
| Company data aggregators | Screener, Trendlyne, Tijori and similar (5). Good for 10–12-year histories and multiples. **Verify** decision-critical figures against filings (`RESEARCH_PLAYBOOK.md` §3). |
| Peer filings | Competitors' annual reports and results (1). The best source for benchmarking. |

## 5. Global equivalents

| Item | Source |
|---|---|
| US filings (10-K, 10-Q, 8-K, proxy, insider Form 4) | SEC EDGAR (sec.gov) |
| UK company accounts (for example foreign subsidiaries of Indian groups) | Companies House (gov.uk) |
| Other listed companies | National exchange and regulator filing systems; company IR sites |

## 6. Practical access notes

- **Downloading:** use `scripts/fetch_source.py`. It sends a browser-like user agent, caps size, hashes the file and logs failures.
- **Observed access behavior** (tested 2026-10-12 from this environment; re-check over time):
  - **bseindia.com** and company IR sites returned HTTP 200 to `fetch_source.py`.
  - **nseindia.com returned HTTP 403** (it blocks scripted clients). Use the BSE filing or the company-IR copy of the same document, and cite that.
  - **SEC EDGAR returned HTTP 403** to the default agent, because EDGAR's fair-access policy requires a declared user agent with contact details. Pass `--user-agent "<Name> <contact email>"` (or set `EQUITY_RESEARCH_USER_AGENT`). The system never inserts the user's email on its own.
- **Scanned PDFs:** the Read tool renders pages visually, so scanned annual reports remain readable.
- **Paywalls:** do not attempt to bypass them. Record the source as unavailable.
- **Aggregator summaries of calls** (AI-generated) are discovery aids, never quotations.
- **News (tier 6):** use it to find events, then confirm each one in a filing or order.
