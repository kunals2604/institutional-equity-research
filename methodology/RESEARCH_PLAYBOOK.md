# Research Playbook — How Agents Acquire, Read, Verify, Compute and Write

This is the operating procedure every specialist (and the CIO, for its own audit work) follows. The constitution says *what* standards apply. This file says *how* to meet them within real constraints: 300-page PDFs, blocked websites, finite context windows, and data that must be traceable to a page.

---

## 1. The workflow, step by step

| Step | What you do | Output |
|---|---|---|
| **1. Plan** (before any search) | Write your decision questions, the data series you need, the years required by the depth standard (§2), and the likely sources (`methodology/SOURCE_GUIDE.md`) | `specialists/<name>_workpapers/research_plan.md` |
| **2. Acquire** | **Both channels, at par** (`SOURCE_GUIDE.md` §0): the local corpus is one input, never the boundary of the research, and may be incomplete or contain download glitches. **Local corpus:** read `RUN_DIR/corpus/CATALOG.md` (built from the owner's FilingForge library: annual reports, results, transcripts and presentations already converted to Markdown, about 25× fewer tokens than the PDFs). Use `python3 scripts/corpus.py search --ticker <T> "<regex>" --types annual_report` to jump to the exact line across all years, then read only that region with the Read tool (`offset`/`limit`). Get the citation page with `corpus.py locate --run RUN_DIR <md> "<phrase>"`. Where the catalog flags `thin-extraction`, read the PDF instead. **Web research, in full:** run the complete web search your agent definition requires (exchange filings, IR, regulators, rating agencies, courts, industry bodies, peers, news, short-seller reports) whatever the corpus covers, cross-check decision-critical corpus numbers against the exchange or IR original, and retrieve documents. For PDFs and decision-critical pages, **download** with `python3 scripts/fetch_source.py URL --run RUN_DIR --author <name> --name "<label>"`, which records the SHA-256, size and retrieval time in `source_retrievals.csv`. For quick HTML lookups, use WebFetch. | Cached files plus the retrieval log (failures are logged too) |
| **3. Read efficiently** | PDFs: open the first pages (table of contents) with the **Read tool** (`pages: "1-6"`), locate the sections you need, and then read only those page ranges (at most 20 pages per call). HTML tables: `python3 scripts/html_tables.py <cached.html> --match "<text>"` extracts tables deterministically. | Page-level locators |
| **4. Extract** | Record the numbers as you read, with page or note locators, into workpaper CSVs. Financial statements go into `financial_history.csv` (long format, one row per item and period; `templates/financial_history_template.csv`). Record material claims in your ledger **immediately**. | Workpapers + ledger |
| **5. Verify** | Apply the verification sampling plan (§3). Reconcile aggregator figures with filings and log every discrepancy. | Verification log in workpapers |
| **6. Compute** | **Never do material arithmetic in your head.** Use `python3 scripts/fin_metrics.py` (ratios, CAGRs, forensic screens) and `python3 scripts/valuation_tools.py` (WACC, DCF, reverse DCF, scenario IRR, price ladder, return decomposition). Save input files under `RUN_DIR/calc/`. Cite outputs as CALCULATION with the formula. | `calc/` inputs and outputs |
| **7. Analyze** | Apply your domain method, the relevant sector playbook (`methodology/SECTOR_PLAYBOOKS.md`), your owned lenses (`methodology/INVESTOR_LENSES.md`), and the four-layer crosswalk | — |
| **8. Write incrementally** | Write the report to disk **section by section** as each analysis completes; don't hold the whole report in memory until the end. Tag and cite as you write. | Report file |
| **9. Self-QC** | Run `validate_report.py`. Check your Data Coverage table against §2. Re-read your Key Findings against the ledger: does every number match? | Clean validator output |
| **10. Return** | The short return message (`REPORT_CONTRACTS.md` §5) | — |

**Context discipline.** Your files are your memory. Long documents do not belong in your context. Extract what matters, with locators, into workpapers. If you notice that earlier context was summarized (auto-compaction), **re-read your research plan, ledger and workpapers before continuing**, and never reconstruct a figure from memory.

**WebFetch caution.** WebFetch returns a model-processed rendering of a page, not the raw document. It can paraphrase or mis-transcribe numbers. Use it to discover and navigate. For any **decision-critical number**, read it from the original document (a PDF page via Read, or an HTML table via `html_tables.py`) and cite that location.

---

## 2. Historical Depth Standard

Institutional conclusions about durability, cycles and management credibility need long histories. The minimums below are enforced by `scripts/validate_report.py`. A shorter history is acceptable **only** with a written `coverage_exception:` in the report's front matter, for example "listed in 2019; pre-IPO FY2015–FY2018 taken from the RHP restated financials".

<!-- DEPTH_MINIMUMS:BEGIN -->
- financials.fiscal_years: 10
- concalls.quarters: 12
- valuation.history_years: 10
- management.shareholding_quarters: 12
- industry.history_years: 10
<!-- DEPTH_MINIMUMS:END -->

| Data series | Minimum | Target | Owner | Notes |
|---|---|---|---|---|
| Annual P&L, balance sheet, cash flow | **10 fiscal years** | 15–20 years; **≥2 full cycles** for any Layer-3-plausible company | financials | Tier-5 aggregators usually give 10–12 years. Older annual reports (company IR site, exchange archives) extend the history. For recent IPOs, the offer document's restated financials add pre-listing years. |
| Annual reports read in substance (MD&A, notes, auditor report, CARO, related parties, contingencies) | Latest **5** in full (targeted sections) + key notes for years 6–10 | 10+ | filings (financials for notes) | Policy changes, auditor history and related-party trends need the longer window |
| Quarterly results | 12 quarters | 20+ | financials, concalls | For inflections and seasonality; never a substitute for annual history |
| Earnings-call transcripts and presentations | **12 quarters** (or all that exist, if fewer) | 20–40 quarters | concalls | Promise tracking needs commitments old enough to have resolved |
| Promise-to-delivery database | All resolved commitments in the transcript window | 10 years including annual-report targets | concalls | Older annual-report MD&A fills gaps before transcripts were published |
| Shareholding, pledges, insider transactions | 12 quarters | 40 quarters | management | Pledge and insider history over at least one market downturn |
| Leadership, board, auditor history | 10 years | Since listing | management, filings | |
| Credit ratings | 5 years | 10 years | filings | Outlook changes are early-warning signals |
| Industry volumes, market shares | **10 years** | 15+ years / 2 cycles | industry | |
| Share price, valuation multiples, drawdowns | **10 years** including at least one market drawdown | 15–20 years | valuation | Percentile of current multiples within own history |
| Corporate actions | 10 years | Since listing | special-situations | |

Every report's **Data Coverage** section is a table: data series | periods covered | count | sources and tier | verification (full / sampled / aggregator-only) | gaps and exceptions.

---

## 3. Verification sampling plan (aggregator data → filings)

Reading 15 annual reports end to end is not feasible in one run, and it isn't necessary. Institutional practice is to **verify a sample and widen the verification when errors appear**:

1. Build the full history from the best available source. A tier-5 aggregator is acceptable for the long tail, and every row records its source and tier.
2. **Verify against tier-1 filings** (annual-report statements, exchange results) at least:
   - the latest **3** fiscal years, in full;
   - **every anomaly year** (inflection, loss, restatement, acquisition, policy change);
   - at least **3 further years** spread across the history (for example years 5, 8 and 12).
3. Verification items: revenue, EBITDA (or PPOP for lenders), PAT, total equity, total debt, CFO, capex and shares, in the stated basis.
4. **Tolerance:** a difference above 1 % (or any classification difference that changes a ratio by more than 1 pp) is a discrepancy. Log it with the cause (restatement, reclassification, consolidation scope, aggregator error).
5. **Escalation:** if two or more sampled years show material discrepancies, verify **all** years for the affected items, or mark the series aggregator-only with lower confidence.
6. In `financial_history.csv`, set `verified=Y` only for figures read from a tier-1 document. The Data Coverage table states what was verified.

---

## 4. Reading annual reports efficiently (Indian filings; adapt elsewhere)

| You need | Usually found in | Tip |
|---|---|---|
| Consolidated and standalone statements | "Financial Statements" sections (consolidated usually second) | Locate the page numbers in the TOC, then read only the 3–5 statement pages |
| Segment data | The "Segment information" note | Note-numbering is not stable across years. Search the TOC or notes index. |
| Related parties | The related-party note; Form AOC-2 in the Board's report | Compare the counterparty list year to year |
| Contingent liabilities, commitments | Their own note | Track by category across 5–10 years |
| Auditor opinion, KAMs | "Independent Auditor's Report"; CARO annexure (standalone) | CARO covers loans to related parties, defaults and fraud reporting |
| Subsidiary financials | Form AOC-1 | The fastest way to see loss-making subsidiaries |
| Strategy, targets | Chairman/MD letter, MD&A | Feeds the promise database |
| Governance | Corporate Governance Report, Board's report | Attendance, committee composition, remuneration, auditor fees |
| ESG and material sustainability risks | BRSR (where published) | Safety incidents, environmental liabilities, labour |

Transcripts: read the **Q&A first**. Analysts' recurring questions reveal what the market doubts. Record guidance verbatim with the page.

---

## 5. Tools reference

| Tool | Purpose |
|---|---|
| WebSearch | Discovery of documents and news; never a citation by itself |
| WebFetch | Quick reading or navigation of HTML pages; not for decision-critical numbers (§1) |
| `scripts/corpus.py` | Local FilingForge library: `status`, `catalog`, `search` (regex across all years, with line numbers), `locate` (PDF page for a passage, via poppler), `pages` (page-marked text) |
| `scripts/fetch_source.py` | Download with provenance (SHA-256, timestamp, status) into `RUN_DIR/_cache/` (git-ignored); logs failures too |
| Read tool (with `pages`) | Read PDFs page by page; this is where page locators come from |
| `scripts/html_tables.py` | Deterministic HTML table → CSV extraction |
| `scripts/fin_metrics.py` | Ratios, CAGRs, per-share compounding, forensic screens from `financial_history.csv` (general and lender profiles) |
| `scripts/valuation_tools.py` | `wacc`, `dcf`, `reverse-dcf`, `scenario-irr`, `price-ladder`, `decompose` |
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
