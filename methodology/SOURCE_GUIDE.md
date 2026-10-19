# Source Guide — Where to Find What, and How to Get It

Discovery and retrieval map for primary evidence, oriented to Indian listed companies, with global equivalents. **Tiers follow the constitution's evidence hierarchy.** Record retrieval failures in the missing-evidence list rather than substituting from memory. The retrieval mechanisms below were verified from this environment on **2026-10-17**; re-verify when a tool reports a new failure pattern.

## 0. Evidence channels at par: the local corpus, the original filings, and the web

Every specialist uses **all three** in full. None is the boundary of the research.

1. **The local corpus** (the owner's FilingForge library): a token-efficient Markdown copy of filings the owner downloaded. It can be incomplete (documents never downloaded, categories skipped, years missing) or faulty (download glitches, truncated or misconverted files, dropped tables, wrong period labels).
2. **The original filings** on NSE, BSE and the company's IR site (and the Internet Archive's copies of the IR site). The CIO indexes them in Stage 0 and downloads the core documents once (`corpus/DOCUMENT_MAP.md`). They are the reference copy when the local corpus disagrees.
3. **The open web**: regulators, courts, rating agencies, industry bodies, peers, news and short-seller reports, which no filing index covers.

Rules:
- **Never limit research to the corpus.** Absence there is not evidence of absence: check the document map, then the exchanges, the IR site and the web, before recording a gap.
- **Use the corpus where it is good**: cross-year search, fast reading, page-cited extraction.
- **Cross-check decision-critical numbers across channels** (corpus vs. exchange original vs. XBRL vs. a second independent source). A disagreement is a contradiction to adjudicate, not a reason to pick the convenient value.
- **Where the document map flags a local defect** (page-count or content mismatch, wrong period label, duplicate label, thin extraction), read and cite the exchange copy, and log the defect so the owner can re-download it.

### 0a. Local corpus: FilingForge library

The owner's FilingForge app downloads exchange filings (annual reports, results, concall transcripts, investor presentations, corporate actions, insider/SAST, AGM documents) into `~/Documents/FilingForgeLibrary/<TICKER>/` (path in `config/data_sources.json`). Each PDF has a Markdown twin, about 25× fewer tokens. `scripts/corpus.py` catalogs it, filters out notices, infers fiscal periods, checks coverage against the depth standard, searches across all years, and maps a passage to its PDF page for citation.

- **Tier:** that of the underlying filing (annual reports and results tier 1; presentations tier 3; transcripts tier 4).
- **Citation:** `source_url_or_id = FilingForge:<doc_id>`; `locator = p.<PDF page>` from `corpus.py locate`, or `MD line <n>` if the page cannot be located (confidence M).
- **Known weaknesses:** downloads are triggered manually, and some may fail or be partial. Markdown has no page markers and can drop table structure, so check decision-critical tables against the PDF page. In the first BHARTIARTL run the library lacked the FY2026 annual report, labelled one FY2024 results file as FY2023, and catalogued a transcript as missing that was present; the document map's cross-check now catches these.

### 0b. Original filings: the Stage-0 index and document map

| Tool | What it does |
|---|---|
| `scripts/exchange_index.py all --run RUN_DIR --symbol <NSE> [--scrip <BSE>] --ir <IR page> --wayback-prefix <IR doc host/path/>` | Indexes NSE, BSE, the IR site and the archive into `_cache/index/exchange_index.csv` (typed: annual_report, transcript, investor_presentation, results / results_xbrl, shareholding, credit_rating, penalty_order, scheme, rpt, kmp_change, auditor, voting_results, insider_trade, sast, corporate_action, …; with fiscal period) |
| `scripts/exchange_index.py show --run RUN_DIR --type <type> [--period FY2025]` | Lists indexed filings of a type, with URLs |
| `scripts/document_map.py build RUN_DIR` | Maps every required document to its local and exchange copies, downloads the exchange copies once, cross-checks the two channels, writes `corpus/DOCUMENT_MAP.md` |
| `scripts/fetch_source.py URL --alt MIRROR` | Downloads anything else, validated, with mirrors and archive fallback |
| `scripts/xbrl_facts.py extract` / `reconcile` | Exchange XBRL results → financial-history rows (tier 1), and the reconciliation with the specialist's dataset |
| `scripts/market_data.py close` / `adtv` / `history` | Exchange bhavcopy price, liquidity and long history (tier 1) |

### 0c. Structured exchange filings: facts filed as data (methodology 3.1.0)

Regulators make listed companies file many key facts in machine-readable form. They are primary (tier 1) and exact, so
they come **before** reading for the facts they carry, and they cross-check the reports for everything else.
`scripts/structured_filings.py fetch` collects them into `corpus/structured/` and `corpus/STRUCTURED.md`:

| Filing | Content | From | Notes |
|---|---|---|---|
| Results XBRL and the Integrated Filing (Financial) | Statements, segments; at the year end, the declaration of an unmodified opinion or the statement on the impact of audit qualifications, and the audit firms | XBRL from about FY2012; Integrated Filing from Q3 FY2025 | `xbrl_facts.py` (statements), `structured_filings.py` (audit opinion) |
| BRSR XBRL | Every BRSR answer: workforce, safety, complaints, penalties, energy, emissions, value-chain data | FY2022 | Covers the annual report's BRSR pages only when its numbers and text match them (`reading.py plan` tests it) |
| Voting results XBRL (AGMs, postal ballots) | Votes polled, for and against, by shareholder category, for every resolution | about FY2021 on NSE | Institutional dissent on related-party, remuneration and auditor resolutions |
| Integrated Filing (Governance) | Board composition: category, appointment, re-appointment, cessation, tenure | Q3 FY2025 | Earlier quarterly governance reports are listed but not machine-readable |
| Related-party disclosures, Reg. 23(9) | Half-yearly statement of every related-party transaction and balance | about FY2020, as PDF announcements | Not structured on NSE: `reading.py fetch-filings` downloads them and the readers read them (a critical class) |
| Shareholding, insider (PIT) and SAST disclosures | Holdings by category, pledges, insider trades, acquisitions | NSE feeds | `exchange_index.py nse` |

Out of reach: the ministry's XBRL of the accounts (Form AOC-4, which carries CARO and secretarial-audit fields) sits
behind the MCA portal's login and paid document view. Third-party "annual report summaries" (AI or broker) are
discovery leads (tier 6), never evidence and never a substitute for reading: they cannot be checked against a page,
their coverage is unknown, and they omit the forensic details this framework looks for.

## 1. Company and exchange disclosures (India)

| Data item | Primary source (tier) | How to get it | Typical history | Notes |
|---|---|---|---|---|
| Annual reports | Company (1) | Document map (NSE `annual-reports` API, BSE `AnnualReport_New` API, IR site, archive) | NSE ~FY2010+, BSE ~FY2002+ (older ones often ZIP or scanned) | Read with the Read tool, page by page |
| Quarterly / annual results | Exchange filings (1) | Document map; NSE `corporates-financial-results` (XBRL to FY2024) and `integrated-filing-results` (2025+) | XBRL from about FY2019 | Check consolidated vs. standalone and audited vs. limited-review |
| Results data, machine-readable | Exchange XBRL (1) | `xbrl_facts.py extract` | About FY2019+ | Cross-check for the financial history; NSE's year-to-date XBRL context mislabels its dates, which the tool corrects from the filing's own reporting-period facts |
| Investor presentations, transcripts, audio | Company (3/4) | Document map (exchange announcements, IR site, archive) | Exchange transcripts mostly 2021+; older ones on the IR site and the archive | Some exchange "transcript" filings are cover letters with a link: the map flags documents under 4 pages |
| Shareholding pattern | Exchange (1) | `exchange_index.py` (NSE shareholding feed) | ~6 years on NSE; older on BSE | Promoter, public, employee trusts |
| Pledges / encumbrance, substantial acquisitions | Exchange (1) | NSE SAST feed; BSE announcements | Many years | |
| Insider trading | Exchange (1) | NSE PIT feed by year | Many years | ESOP-trust and market purchases are listed separately |
| Every Regulation 30 announcement | Exchange (1) | NSE announcement history (full, since about 2004); BSE by year | Since listing | Penalties, orders, KMP and auditor changes, schemes, ratings, voting results |
| Corporate actions | Exchange (1) | NSE corporate-action feed | Many years | Dividends, splits, bonuses, record dates |
| Corporate governance reports | Exchange (1) | Exchange filings; annual report | | |
| Schemes of arrangement | Exchange / NCLT (1–2) | Announcements (type `scheme`), scheme documents, NCLT orders | | Board → exchange observation → NCLT → effective date |
| Offer documents (IPO / QIP / rights) | SEBI / exchange (1) | SEBI public-issues filings, exchange offer documents | | Restated pre-listing financials, objects, risk factors |
| Monitoring-agency reports | Exchange (1) | Exchange filings | | Critical for SME and recent IPOs |
| BRSR (sustainability) | Company (1) | Within the annual report | Recent years | Attrition, safety, environment: also ground-truth data |

## 2. Regulators, courts and registries (India)

| Item | Source (tier) | Where |
|---|---|---|
| SEBI orders, adjudications, settlements | 2 | sebi.gov.in (enforcement / orders) |
| RBI regulations, penalties, banking statistics | 2 | rbi.org.in; statistics at dbie.rbi.org.in |
| IRDAI (insurance) data and orders | 2 | irdai.gov.in |
| Competition Commission orders | 2 | cci.gov.in |
| Company master data, charges (secured borrowings), directors | 2 | mca.gov.in (MCA21). Some data is free; filings may need paid access. |
| Insolvency / company-law tribunal orders | 2 | NCLT / NCLAT websites; ecourts.gov.in; the Supreme Court site |
| Tax disputes | 2 | Tribunal and court records where published; otherwise the contingent-liability notes |
| Auditor regulation | 2 | NFRA orders (nfra.gov.in); ICAI disciplinary records |
| Pharma regulatory actions | 2 | US FDA databases (warning letters, 483s, inspection classifications, approvals); CDSCO |
| Real-estate project registrations | 2 | State RERA portals |
| Telecom subscriber, porting, quality-of-service and complaint data | 2 | trai.gov.in |
| Power-sector statistics | 2 | cea.nic.in |
| Petroleum data | 2 | ppac.gov.in |
| Mutual-fund industry data | 2 / 5 | amfiindia.com |

## 3. Credit ratings (tier 5, but often the best independent view of liquidity and covenants)

CRISIL Ratings (crisilratings.com), ICRA (icra.in), CARE Ratings (careratings.com), India Ratings & Research (indiaratings.co.in), Acuité (acuite.in), Brickwork. Rating **rationale** documents disclose liquidity, debt structure, group support and key sensitivities. Track rating and outlook history over 5–10 years. The exchange index also lists the company's credit-rating announcements (type `credit_rating`), which give the dates.

## 4. Industry and market data

| Sector | Sources (tier) |
|---|---|
| Automobiles | SIAM (siam.in, 5), FADA retail data (fada.in, 5), VAHAN registrations dashboard (parivahan.gov.in, 2) |
| Telecom | TRAI monthly subscription, porting and quality-of-service reports (2) |
| Banking / NBFC | RBI statistical releases, Financial Stability Report (2) |
| Insurance | IRDAI annual reports and monthly data (2) |
| Asset management | AMFI monthly data (5) |
| Power, oil and gas | CEA, PPAC (2) |
| Cement, steel and other commodities | Industry associations and ministry data (2/5); listed-peer filings (1) |
| Indices and valuations | NSE index factsheets and index P/E history (niftyindices.com, 5) |
| Company data aggregators | Screener, Trendlyne, Tijori and similar (5). Good for 10–12-year histories and multiples. **Verify** decision-critical figures against filings and XBRL (`RESEARCH_PLAYBOOK.md` §3). |
| Peer filings | Competitors' annual reports and results (1), indexed the same way (`exchange_index.py` with the peer's symbol in a scratch run, or the exchange pages). The best source for benchmarking. |

### 4a. Ground-truth (scuttlebutt) sources

Evidence that comes from neither management nor the financial statements (owner: the scuttlebutt specialist; the sector playbooks list sector-specific series).

| Channel | Sources (tier) | Cautions |
|---|---|---|
| Regulator / registry operating data | TRAI, VAHAN, RBI, IRDAI, AMFI, CEA, PPAC, DGCA, port and rail freight statistics, RERA, CDSCO and US FDA databases, GST and e-way bill aggregates (2) | Compulsory and comparable across competitors: the strongest ground truth |
| Customer evidence | Regulator complaint statistics; National Consumer Helpline and consumer-commission data; recalls and safety notices; independent quality tests (crash ratings, network-experience and speed-test reports, lab tests); app-store ratings and review counts (5–7) | Normalize per customer or unit; record sample sizes and dates; ratings are sentiment |
| Pricing | Published price lists, tariff cards and plan pages of the company and competitors; regulator tariff filings; dated e-commerce listings (1–6) | Save each page with `fetch_source.py`: the retrieval time is evidence |
| Channel, supplier, partner | Dealer and distributor associations; FADA-type inventory data; customers' and suppliers' own filings naming the company; GeM and other procurement portals; trade press (2–6) | A customer's filing that names the company is tier 1 evidence about the relationship |
| Employees | BRSR attrition and headcount (1); labour orders (2); job-posting trends and employee-review ratings (7, sentiment only) | Never quote an individual reviewer as a fact |
| Digital demand | Search-interest trends, app rankings and downloads, web-traffic estimates (6–7) | Leading indicators only, never decision-critical alone |

## 5. Global equivalents

| Item | Source |
|---|---|
| US filings (10-K, 10-Q, 8-K, proxy, insider Form 4) | SEC EDGAR (sec.gov); requires a declared user agent (`EQUITY_RESEARCH_USER_AGENT`) |
| UK company accounts (for example foreign subsidiaries of Indian groups) | Companies House (gov.uk) |
| Other listed companies | National exchange and regulator filing systems; company IR sites |

## 6. Access behaviour and retrieval mechanics (verified 2026-10-17; structured feeds 2026-10-18)

| Host | What works | What fails | Handled by |
|---|---|---|---|
| **NSE API** (`www.nseindia.com/api/...`) | JSON with an `Accept: application/json` header and an nseindia.com referer, **no cookie handshake needed**: `annual-reports`, `corporate-announcements` (full history in one call), `corporates-financial-results`, `integrated-filing-results` (financial and governance views), `corporate-share-holdings-master`, `corporate-board-meetings`, `corporates-corporateActions`, `corporates-pit` (by year), `corporate-sast-reg29`; verified 2026-10-18: `corporate-bussiness-sustainabilitiy` (sic; BRSR XBRL per year, with `from_date`/`to_date`), `corporate-voting-results` (with `from_date`/`to_date`; without them only the latest meetings), `corporate-governance-master` (quarter list only) | The homepage, `quote-equity` and `historical/cm/equity` return 403/503 to scripts; the `corporate-credit-rating` feed ignores the symbol | `netfetch.py` profile `nse-api`; prices come from bhavcopy instead |
| **NSE archives** (`nsearchives.nseindia.com`) | Every filing attachment, annual-report PDFs and ZIPs, XBRL, bhavcopy files (`sec_bhavdata_full_DDMMYYYY.csv` 2020+, `content/historical/EQUITIES/...bhav.csv.zip` 2012–2024, UDiFF 2024+) | `sec_bhavdata_full` before 2020 (404) | profile `nse-archive`; `market_data.py` picks the format by date |
| **BSE API** (`api.bseindia.com`) | JSON **only over HTTP/2 with a browser's full header set** (`sec-ch-ua`, `sec-fetch-*`, origin, referer): `AnnualReport_New`, `AnnSubCategoryGetData` (paged, by year), `PeerSmartSearch` (scrip and ISIN lookup) | HTTP/1.1 or partial headers: Akamai 403; Python's urllib cannot do HTTP/2. An end date in the future returns no rows | profile `bse-api` (curl `--http2`); the indexer caps end dates at today |
| **BSE files** (`www.bseindia.com/xml-data/corpfiling/AttachHis|AttachLive/...`) | Announcement attachments and annual reports | `AttachLive` holds only recent files (`AttachHis` the rest) | profile `bse-file`; both paths tried |
| **Internet Archive** | `archive.org/wayback/available`, the CDX index (`web.archive.org/cdx/search/cdx?url=<prefix>*`) and raw captures (`web.archive.org/web/<ts>id_/<url>`) | Rate limits under heavy use | automatic fallback in `fetch_source.py`; `exchange_index.py wayback` for discovery |
| **Company IR sites** | Usually fine with a browser-like request | JavaScript-only sites expose no links to a crawl; restructured sites return 404 for old links | `exchange_index.py ir` crawl; the archive for JavaScript sites and moved files |
| **SEC EDGAR** | Works with a declared user agent | 403 to a default agent | profile `sec`; set `EQUITY_RESEARCH_USER_AGENT` |
| **Yahoo Finance chart API** | Long daily histories (tier 5) | Rate-limited (HTTP 429) under repeated use | prefer `market_data.py history` (exchange bhavcopy, tier 1) |

**The TLS problem behind the first run's download failures.** The macOS system Python (3.9.6) links LibreSSL 2.8.3, which fails intermittently with `DECRYPTION_FAILED_OR_BAD_RECORD_MAC` and connection resets under parallel load. In a 12-download test, urllib failed 3 of 12 while the system curl (SecureTransport, HTTP/2) succeeded 12 of 12. `scripts/netfetch.py` therefore uses **curl first**, retries transient failures with backoff, and **validates every payload** (an HTML "Access Denied" page saved as a PDF, a truncated PDF, or a corrupt ZIP is a failure, not a document).

- **Scanned PDFs:** the Read tool renders pages visually, so scanned annual reports remain readable.
- **Paywalls:** do not attempt to bypass them. Record the source as unavailable.
- **Aggregator summaries of calls** (AI-generated) are discovery aids, never quotations.
- **News (tier 6):** use it to find events, then confirm each one in a filing or order.
