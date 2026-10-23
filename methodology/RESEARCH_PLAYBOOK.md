# Research Playbook — How Agents Acquire, Read, Verify, Compute and Write

This is the operating procedure every specialist (and the CIO, for its own audit work) follows. The constitution says *what* standards apply. This file says *how* to meet them within real constraints: 300-page PDFs, blocked websites, finite context windows, and data that must be traceable to a page.

---

## 1. The workflow, step by step

| Step | What you do | Output |
|---|---|---|
| **1. Plan** (before any search) | Write your decision questions, the data series you need, the years required by the depth standard (§2), and the likely sources (`methodology/SOURCE_GUIDE.md`) | `specialists/<name>_workpapers/research_plan.md` |
| **2. Acquire** | **Start from `RUN_DIR/corpus/DOCUMENT_MAP.md`**: the CIO has already indexed the exchanges, the IR site and the Internet Archive, downloaded the exchange copy of every annual report, transcript and presentation (cached under `_cache/cio/`), and cross-checked them against the local corpus. **All channels at par** (`SOURCE_GUIDE.md` §0). **Local corpus:** `RUN_DIR/corpus/CATALOG.md`; `python3 scripts/corpus.py search --ticker <T> "<regex>" --types annual_report` jumps to the exact line across all years; read only that region with the Read tool (`offset`/`limit`); get the citation page with `corpus.py locate --run RUN_DIR <md> "<phrase>"`. Where the map or the catalog flags a defect, read the exchange copy instead. **Other filings:** `python3 scripts/exchange_index.py show --run RUN_DIR --type <type> [--period FY2025]` lists every indexed announcement (penalties, schemes, KMP and auditor changes, ratings, voting results, insider trades …) with its URL. **Web research, in full:** run the complete web search your agent definition requires (regulators, rating agencies, courts, industry bodies, peers, news, short-seller reports) whatever the filings cover. Download with `python3 scripts/fetch_source.py URL --run RUN_DIR --author <name> --name "<label>" [--alt MIRROR]`, which validates the file, tries mirrors and the archive, reuses copies already in the run, and records SHA-256, size and time in `source_retrievals.csv`. For quick HTML lookups, use WebFetch. | Cached files plus the retrieval log (failures are logged too) |
| **3. Read efficiently** | **From your reading pack first** (§1c): every in-scope page of every document in the map has been read and its items, quote-verified and page-cited, are in the topic dossiers; read the must-read part of your pack in full (each topic's series and material items) and search its reference part for what your method needs. Then, **through the text layer** (§4) for verification and depth: `python3 scripts/doc_text.py toc RUN_DIR <pdf>` gives the section's PDF pages and the line where each starts in `pages.md`; Read those lines (`offset`/`limit`) or run `doc_text.py page RUN_DIR <pdf> <n>`; `doc_text.py search RUN_DIR "<regex>" [--type annual_report]` finds a term across every document. Read the rendered PDF page (Read tool, `pages: "n"`) for every flagged page and to confirm every decision-critical number (§4). HTML tables: `python3 scripts/html_tables.py <cached.html> --match "<text>"`. | Page-level locators |
| **4. Extract** | Record the numbers as you read, with page or note locators, into workpaper CSVs. Financial statements go into `financial_history.csv` (long format, one row per item and period; `templates/financial_history_template.csv`). Record material claims in your ledger **immediately**. | Workpapers + ledger |
| **5. Verify** | Apply the verification sampling plan (§3). Reconcile aggregator figures with filings and log every discrepancy. | Verification log in workpapers |
| **6. Compute** | **Never do material arithmetic in your head.** Use `python3 scripts/fin_metrics.py` (ratios, CAGRs, forensic screens) and `python3 scripts/valuation_tools.py` (WACC, DCF, reverse DCF, scenario IRR, price ladder, return decomposition). Save input files under `RUN_DIR/calc/`. Cite outputs as CALCULATION with the formula. | `calc/` inputs and outputs |
| **7. Analyze** | Apply your domain method, the relevant sector playbook (`methodology/SECTOR_PLAYBOOKS.md`), your owned lenses (`methodology/INVESTOR_LENSES.md`), and the four-layer crosswalk | — |
| **8. Write incrementally** | Write the report to disk **section by section** as each analysis completes; don't hold the whole report in memory until the end. Tag and cite as you write. After each method step, update `specialists/<name>_workpapers/progress.md` (steps done, files written, next step) so that an interruption costs nothing. Writing early is about **safety, never about brevity**: an interruption or a resume never justifies shortening any section. | Report file + `progress.md` |
| **9. Self-QC** | Fill the **Method Coverage Checklist** (`REPORT_CONTRACTS.md`): one row per numbered step of your `## Method`. Every Partial or Not available row needs what you tried and what would close it; go back and close any you can before returning. Run `validate_report.py`. Check your Data Coverage table against §2. Re-read your Key Findings against the ledger: does every number match? | Clean validator output |
| **10. Return** | The short return message (`REPORT_CONTRACTS.md` §5) | — |

**Context discipline.** Your files are your memory. Long documents do not belong in your context. Extract what matters, with locators, into workpapers. If you notice that earlier context was summarized (auto-compaction), **re-read your research plan, ledger and workpapers before continuing**, and never reconstruct a figure from memory.

**Interrupted runs.** If you are resumed after an interruption, read `progress.md`, your plan, ledger and report first, then continue from the next step at full depth. Never redo finished work, and never reconstruct figures from memory.

### 1a. Retrieval protocol (when a download fails)

1. `fetch_source.py` already uses the system curl with the right request profile for the host (NSE, BSE, SEC, default), retries transient failures with backoff, falls back to urllib, then to the **Internet Archive's raw copy** of the URL, and rejects error pages, truncated PDFs and corrupt ZIPs. It reuses a document any agent (or the CIO's Stage-0 acquisition) already downloaded. Pass every known copy of the document with `--alt` (for example the BSE `AttachHis` copy of an NSE filing).
2. If it still fails, find the same document elsewhere, in this order: the document map and `exchange_index.py show` (the other exchange's copy, the IR copy, archived captures); the company IR site; the regulator (SEBI, MCA, RBI, TRAI and so on); the rating agency's own site; `exchange_index.py wayback --prefix <the IR document folder>` for files the IR site has moved or removed; a search for the exact title or file name.
3. Only then record it as Not available: name the document, every URL tried with its error (they are in `source_retrievals.csv`), and the evidence you used instead. That goes in the missing-evidence list and the Method Coverage Checklist, so the CIO's gap-closure loop can pick it up.

### 1b. Stage-0 document acquisition (CIO)

Before any specialist starts, the CIO acquires the company's documents once, for the whole run (`cio.md` Stage 0 step 9):

1. `exchange_index.py all` indexes NSE (annual reports, the full announcement history, results XBRL and integrated filings, shareholding, board meetings, corporate actions, PIT and SAST), BSE (annual reports, announcements, scrip and ISIN), the IR site (bounded crawl) and the Internet Archive's copies of the IR document folder.
2. `document_map.py build` maps every document the depth standard requires (15 fiscal years of annual reports; 24 quarters of transcripts, presentations, results and shareholding) to its local and exchange copies, downloads the exchange copies of the core documents (validated, ZIPs unpacked), and cross-checks the two channels: page counts, first-page text, period labels, duplicate labels, local extraction quality, short "cover-letter" documents.
3. `xbrl_facts.py extract` turns the exchange XBRL results into tier-1 financial-history rows for the financials specialist's reconciliation; `market_data.py` gives the exchange close for the price claim.

4. `structured_filings.py fetch` collects the exact structured filings (BRSR XBRL, voting results by shareholder category, the Integrated Filings' audit-opinion statements and board composition; `SOURCE_GUIDE.md` §0c); `reading.py fetch-filings` downloads the announcements that forensic work reads (related-party disclosures, auditor changes, ratings, penalty and litigation disclosures, schemes, key-personnel changes).
5. The `librarian` agent searches for every document the map still lacks (other exchange, IR archives, the Internet Archive, the web), confirms each from its first page and registers it (`document_map.py add`), or logs why it is unobtainable.

Specialists therefore start from documents that exist, are validated and are cross-checked, and they spend their effort reading rather than searching.

### 1c. Stage-0b reading stage (CIO and the readers)

No agent can hold ten years of annual reports (4–5M tokens) in one context, and searching only finds what you already suspect: in run 20261012T132311Z the ten specialists together saw 11–17 % of each annual report's text and read transcripts through a keyword filter. So every in-scope page is read once, in small fresh contexts, and the reading is recorded page by page (`cio.md` Stage 0b; `READING_SCHEMAS.md`; `MODEL_POLICY.md`):

1. **Plan** (`reading.py plan`). Scope (owner's decision, 2026-10-19): **every page** of the annual reports of the latest five fiscal years and the **core sections** of the five before them (auditor's reports, CARO, IFC, the statements and every note, the Board's report and its statutory annexures, MD&A: the schema's `core` classes), 24 quarters of transcripts, 12 of presentations, and the fetched exchange filings. The window is fixed by fiscal year (the latest is the newest report in the map or, if later, the newest one due by the cutoff), so a missing report is a gap that blocks the plan until the librarian finds it or the CIO records why it cannot be had (`reading.py accept-gap`); it never slides the window back. A document an earlier run of the company read completely (the same file by SHA-256, the same reading format and schema, every read passed by that run's reading audit) is reused rather than read again, and COVERAGE.md says in which run it was read. Each page becomes passages (paragraphs split into sentences; one table row each; every other line of text, however short, is its own passage: a lone `420` or `-` in a statement is a value, and only running headers and the printed page number are page furniture). Sections are classified from their titles (running navigation bars are ignored; a title is a short block of its own), and **critical** classes — auditor's reports, CARO, IFC, critical notes (policies and estimates, contingent liabilities and commitments, related parties, borrowings, exceptional items, segments, tax, subsequent events, business combinations ...), the Board's report, AOC-1/AOC-2, the secretarial audit, related-party and auditor filings — are read twice. A sentence of 60 characters or more, or a whole table, that repeats word for word text already scheduled for reading (another year, or the standalone and consolidated notes) is read once; its items are carried to every place it repeats (`also in`). Read-once never removes meaning: labels, values, headings and column headers are always read, a label followed by its values is always read, a row of a changed table is read with its table, and the repeated sentence just before new text is shown as context. **VIEW REQUIRED** pages are read on the rendered image: no reliable text layer (read from the image), raster images covering 10 % of the page or more (read for what only the images print), and numbers to confirm (including tables the text layer printed one cell per line). BRSR pages that the BRSR XBRL filing covers in full (numbers and text) are `structured`.
2. **Read** (`agent_driver.py reading`: one launch at a time by default, about one chunk per launch, each launch its own headless session with a one-hour prompt cache, outside the CIO's context, continuing unattended through usage limits; without the CLI, the CIO runs `reading.py next` through the Agent tool). The `reader` (Sonnet) reads every chunk; the `critical-reader` (Opus) reads the critical chunks again, independently. Readers extract **every instance** of every item type as **tags, not transcriptions** (schema 1.2): each item cites its passage (or its span of passages, `to`) and a few of its words (`anchor`) with the key fields and amounts exactly as printed, never a paraphrase, because the dossier prints the passage itself; each table is tagged once (its span, the item type of its rows, which cell holds which amount or period) and the script writes every row exactly as printed, refusing any row it cannot expand until the reader writes it; a receipt for every page and every VIEW REQUIRED page opened; written in parts with the Write tool; they never judge materiality and never compute. `reading.py check` assembles the parts, attaches the printed text of the cited passages as each item's quote, and verifies every anchor against its passage and every number in every field against that text. For a chunk read twice, `compare` lists every disagreement (an item one read lacks, or an amount in a different field) and a fresh critical-reader resolves each against the page.
3. **Deliver** (`reading.py dossiers`, `reading.py status --strict`). Topic dossiers across all years (auditor, accounting, contingencies, related parties, debt and capital, results and segments, structure and transactions, governance, strategy and outlook, transcripts, ESG, unusual items), each in three parts: **series** (every value of every recurring line item on one line across all years, each with its page; a year whose value differs between two reports is flagged as a changed comparative: restated or reclassified?), **material items** with their full printed text (the auditor's wording, the litigation description, the policy change), and a **reference** file of every other item with its text; one reading pack per specialist, listing the must-read parts (series and material items of the topics it owns, with their token size) and the reference parts; the page ledger and `corpus/reading/COVERAGE.md`, the only statement of what was read.
4. **Prove** (`reading_audit.py run`, Stage 4): from the agents' own transcripts (subagents and the driver's headless sessions alike), every extraction in the record came from an agent that received every line of its chunk and opened its VIEW REQUIRED pages, every agent ran on its pinned model and effort, every reused document's copies match what its earlier run's passed audit covered, and every specialist read its pack.

Rules for specialists: read the must-read part of your pack in full (across sessions when it is large, noting in your workpapers what each dossier established); verify every decision-critical item on its page and cite the **document and page**, never the dossier; go beyond the dossiers wherever your method needs it; never state your own reading coverage ("read in full", "read in substance"), which the validator rejects.

**WebFetch caution.** WebFetch returns a model-processed rendering of a page, not the raw document. It can paraphrase or mis-transcribe numbers. Use it to discover and navigate. For any **decision-critical number**, read it from the original document (a PDF page via Read, or an HTML table via `html_tables.py`) and cite that location. A web page you cite is kept as a snapshot (`fetch_source.py URL --snapshot`; `--dom` for a page whose table JavaScript builds, then `html_tables.py`).

---

## 2. Historical Depth Standard

Institutional conclusions about durability, cycles and management credibility need long histories. The minimums below are enforced by `scripts/validate_report.py`. A shorter history is acceptable **only** with a written `coverage_exception:` in the report's front matter, for example "listed in 2019; pre-IPO FY2015–FY2018 taken from the RHP restated financials".

<!-- DEPTH_MINIMUMS:BEGIN -->
- financials.fiscal_years: 10
- concalls.quarters: 12
- valuation.history_years: 10
- management.shareholding_quarters: 12
- industry.history_years: 10
- filings.annual_report_years: 10
- moat.history_years: 10
- special-situations.history_years: 10
- scuttlebutt.history_years: 5
<!-- DEPTH_MINIMUMS:END -->

| Data series | Minimum | Target | Owner | Notes |
|---|---|---|---|---|
| Annual P&L, balance sheet, cash flow | **10 fiscal years** | 15–20 years; **≥2 full cycles** for any Layer-3-plausible company | financials | Tier-5 aggregators usually give 10–12 years. Older annual reports (company IR site, exchange archives) extend the history. For recent IPOs, the offer document's restated financials add pre-listing years. |
| Annual reports read by the reading stage (§1c) | **every page of the latest 5 fiscal years; the core sections of the 5 before them** (10 years of audit, statements, notes, Board's report and MD&A) | more core years with `--core-years` | the CIO's reading stage; filings and financials use the dossiers | Policy changes, auditor history and related-party trends need the 10-year window; a missing in-scope report blocks the plan until found or its absence is explained; coverage is recorded in `corpus/reading/COVERAGE.md`, not claimed |
| Quarterly results | 12 quarters | 20+ | financials, concalls | For inflections and seasonality; never a substitute for annual history |
| Earnings-call transcripts and presentations | **12 quarters** (or all that exist, if fewer) | 20–40 quarters | concalls | Promise tracking needs commitments old enough to have resolved |
| Promise-to-delivery database | All resolved commitments in the transcript window | 10 years including annual-report targets | concalls | Older annual-report MD&A fills gaps before transcripts were published |
| Shareholding, pledges, insider transactions | 12 quarters | 40 quarters | management | Pledge and insider history over at least one market downturn |
| Leadership, board, auditor history | 10 years | Since listing | management, filings | |
| Credit ratings | 5 years | 10 years | filings | Outlook changes are early-warning signals |
| Industry volumes, market shares | **10 years** | 15+ years / 2 cycles | industry | |
| Moat metrics (returns, share, margins, unit economics) for the company and its strongest competitors | **10 years** | 15+ years | moat | Counted in *Quantified Advantage Metrics* |
| Annual reports used by filings (from its dossiers and the pages behind them) | **10 fiscal years** | 15+ | filings | Counted in *Filings Reviewed*; the exchanges carry most companies' reports back to the 2000s |
| Independent operating (ground-truth) series | **5 years** | 10 years | scuttlebutt | Regulator / registry data reconciled to company KPIs; counted in *Independent Operating Data* |
| Share price, valuation multiples, drawdowns | **10 years** including at least one market drawdown | 15–20 years | valuation | Percentile of current multiples within own history |
| Corporate actions | 10 years | Since listing | special-situations | |

Every report's **Data Coverage** section is a table: data series | periods covered | count | sources and tier | verification (full / sampled / aggregator-only) | gaps and exceptions.

---

## 3. Verification sampling plan (aggregator data → filings)

The reading stage reads every page of the annual reports, but a long history assembled from an aggregator (or from older reports outside the reading scope) still needs verification against the filings. Institutional practice is to **verify a sample and widen the verification when errors appear**:

1. Build the full history from the best available source. A tier-5 aggregator is acceptable for the long tail, and every row records its source and tier.
2. **Verify against tier-1 filings** (annual-report statements, exchange results) at least:
   - the latest **3** fiscal years, in full;
   - **every anomaly year** (inflection, loss, restatement, acquisition, policy change);
   - at least **3 further years** spread across the history (for example years 5, 8 and 12).
3. Verification items: revenue, EBITDA (or PPOP for lenders), PAT, total equity, total debt, CFO, capex and shares, in the stated basis.
4. **Exchange XBRL reconciliation** (in addition to the sample): for every year with exchange XBRL (about FY2019 onward), run `xbrl_facts.py reconcile` against the history and explain every gap above 1 %. Many gaps are definitional (for example PBT including the share of associates, capex excluding intangibles, dividends including those paid to minorities): state the definition you use, consistently with `METRIC_DEFINITIONS.md`.
4. **Tolerance:** a difference above 1 % (or any classification difference that changes a ratio by more than 1 pp) is a discrepancy. Log it with the cause (restatement, reclassification, consolidation scope, aggregator error).
5. **Escalation:** if two or more sampled years show material discrepancies, verify **all** years for the affected items, or mark the series aggregator-only with lower confidence.
6. In `financial_history.csv`, set `verified=Y` only for figures read from a tier-1 document. The Data Coverage table states what was verified.

---

## 4. Reading large documents: the text layer and the zero-loss rule

**Why a text layer.** A 300-page annual report is about 400k tokens as text and several times that as rendered pages: far more than one agent should hold. The reading stage reads it in small chunks (§1c); specialists use the text layer to verify and to go deeper. In Stage 0, `document_map.py` converts every core PDF (exchange and local copies) with `scripts/doc_text.py`. The text is built so that what you read is what the page says:

- **Spreads split.** Many reports print two A4 pages on one landscape PDF page. Each half is converted separately, so a Balance Sheet row and a P&L row never share a line.
- **Prose in reading order.** Words come from poppler's word boxes, ordered by an XY-cut (bands top to bottom, columns left to right), with correct word spacing.
- **Tables rebuilt from coordinates.** Rows come from vertical position. Columns come from the right edges of the numbers (financial tables right-align them), so an empty cell stays empty and a value never slides into the notes column.
- **Anchors and index.** Every page starts with `<<<PAGE n/N | printed p | view | flags>>>`; `meta.json` holds its line range, so you can Read exactly page *n*. `toc` lists the statement and section ranges (standalone vs. consolidated statements and notes, auditor's report, CARO, related parties, contingent liabilities, segments, MD&A, board's report, governance, BRSR, AOC-1/2, secretarial audit; for transcripts, the Q&A).
- **Flags that send you to the rendered page:** `image_only` (no text layer), `rotated_text` (sideways tables: the layer prints a notice, never fake rows), `table_numbers_mismatch` (the rebuilt table lost or added a number against poppler's word list), `table_alignment_uncertain` (numbers outside every column), `encoding_suspect`. A header note tells you when a font extracts the rupee sign as `C`.

**The zero-loss rule** (accuracy is procedural, not assumed):
1. Navigate and read in the text layer: `toc` → the section's pages → Read those lines.
2. **Every decision-critical number** (anything in Key Findings, a ledger row with a value that feeds a conclusion, a score or a valuation input) is confirmed twice before it is cited as a FACT: `python3 scripts/doc_text.py verify RUN_DIR <pdf> <page> "<value>"` (present in both the text layer and an independent raw extraction), **and** visually on the rendered page with the Read tool (`pages: "n"`).
3. **Every flagged page** is read on the rendered page, never from the text layer.
4. Financial statements are also reconciled to exchange XBRL (`xbrl_facts.py`), a third, machine-readable channel.
5. Cite the **PDF page** from the anchor (`p.201`); add the printed page in the note when it helps a reader (`printed p.394`).

| You need | Usually found in | `toc` key |
|---|---|---|
| Consolidated and standalone statements | "Financial Statements" sections (consolidated usually second) | `standalone_balance_sheet`, `consolidated_pnl`, `consolidated_cash_flow` … |
| Segment data | The "Segment information" note (numbering is not stable across years) | `segment_information` |
| Related parties | The related-party note; Form AOC-2 in the Board's report | `related_parties`, `aoc_2` |
| Contingent liabilities, commitments | Their own note | `contingent_liabilities` |
| Auditor opinion, KAMs, CARO, IFC | "Independent Auditor's Report" and its annexures | `independent_auditors_report`, `caro_annexure`, `ifc_report` |
| Subsidiary financials | Form AOC-1 | `aoc_1` |
| Strategy, targets | Chairman/MD letter, MD&A | `mdna` |
| Governance, remuneration | Corporate Governance Report, Board's report, particulars of employees | `corporate_governance`, `boards_report`, `remuneration` |
| Secretarial compliance | Secretarial Audit Report (MR-3) | `secretarial_audit` |
| ESG and material sustainability risks | BRSR | `brsr` |

Transcripts are read in full by the readers; the `transcripts` dossier holds every question, answer, forward statement, explanation and number. Analysts' recurring questions reveal what the market doubts; open the transcript page (`toc` key `qa_session`) of every exchange you rely on, and record guidance verbatim with the page. Never substitute a keyword filter for reading.

---

## 5. Tools reference

| Tool | Purpose |
|---|---|
| WebSearch | Discovery of documents and news; never a citation by itself |
| WebFetch | Quick reading or navigation of HTML pages; not for decision-critical numbers (§1) |
| `scripts/corpus.py` | Local FilingForge library: `status`, `catalog`, `search` (regex across all years, with line numbers), `locate` (PDF page for a passage, via poppler), `pages` (page-marked text) |
| `scripts/fetch_source.py` | Download with provenance (SHA-256, timestamp, status) into `RUN_DIR/_cache/` (git-ignored); validated payloads; mirrors (`--alt`), archive fallback and in-run reuse (§1a); logs failures too |
| `scripts/exchange_index.py` | NSE / BSE / IR / archive filing index; `show` to list filings of a type or period |
| `scripts/fetch_source.py --snapshot` / `--dom` | A web page as headless Chrome renders it (citable PDF with URL and date; or the DOM after JavaScript), cached and logged |
| `scripts/connectors.py` | Free external sources, cached and logged: `list`, `open <source>` (landing-page snapshot), `tri` (index total returns), `mospi` (official statistics), `gdelt` (news leads), `openfda`, `kanoon` (courts and tribunals, with a key), `transcribe` (audio-only calls); registry `config/data_sources.json` |
| `scripts/doc_text.py` | The text layer (§4): `toc`, `page`, `search`, `verify` on every core document |
| `scripts/reading.py` | The reading stage (§1c): `plan`, `next`, `check`, `compare`, `dossiers`, `status`, `sample`, `bakeoff`, `reference`; your reading pack is `corpus/dossiers/packs/<name>.md` |
| `scripts/structured_filings.py` | Exact structured exchange filings: BRSR XBRL, voting results, audit-opinion statements, board composition (`corpus/STRUCTURED.md`) |
| `scripts/reading_audit.py` | What each agent actually read, on which model and effort, from its transcript (Stage 4) |
| `scripts/document_map.py` | Stage-0 document map and the two-channel cross-check (`corpus/DOCUMENT_MAP.md`) |
| `scripts/xbrl_facts.py` | Exchange XBRL results → financial-history rows; `reconcile` against your history |
| `scripts/market_data.py` | Exchange close, ADTV and delivery, long split-adjusted price history (NSE bhavcopy, tier 1) |
| `scripts/audit_tools.py` | The auditor's numeric tie-out and claim sample (also useful for your own self-QC) |
| Read tool (with `pages`) | Read PDFs page by page; this is where page locators come from |
| `scripts/html_tables.py` | Deterministic HTML table → CSV extraction |
| `scripts/fin_metrics.py` | Ratios, CAGRs, per-share compounding, forensic screens from `financial_history.csv` (general and lender profiles) |
| `scripts/valuation_tools.py` | `wacc`, `dcf` (with `event_uplifts`), `reverse-dcf`, `scenario-build` (horizon values from DCF inputs), `scenario-irr` (hurdle-adjusted asymmetry), `price-ladder`, `decompose`, `robustness` |
| `scripts/validate_report.py` | Self-check before returning |

If a site blocks automated access (exchange sites sometimes do), try the company's own IR page, or another official mirror of the same document. If nothing works, record the gap in the missing-evidence list. **Never reconstruct a document's contents from memory.**

---

## 6. Writing standard

- **Lead with the answer.** Each section opens with its conclusion (tagged), then the evidence.
- **Tables for numbers, prose for reasoning.** Each table states units, basis and periods.
- **Quantify.** Prefer "receivable days rose from 41 to 68 between FY2021 and FY2024 [CALCULATION: FIN-C031]" to "receivables rose sharply".
- **One finding, one place.** Refer back instead of repeating.
- **Uncertainty is part of the answer.** Say what you could not establish and how much it matters.
- **No length limit.** Be as detailed and thorough as the evidence supports. Depth comes from evidence and analysis, not repetition.
