---
name: cio-stage-0
description: The CIO's Stage 0: preflight, acquisition, the reading stage or the web digest. Load it when `python3 scripts/orchestrate.py next` names it.
---

## Stage 0 — Preflight (before any specialist starts)

0. **Session check.** `python3 scripts/reading_audit.py session` reports this session's model and effort. The policy
   (`methodology/MODEL_POLICY.md`) is the CIO on Opus at **xhigh**. If it is not, tell the owner once before anything else:
   *"This session runs on <model> at effort <effort>; the framework expects Opus at xhigh for the CIO. Switch in the
   model picker and reply 'go', or reply 'continue' to run as is."* Record the answer as a manifest note after step 4. (Run
   20261012T132311Z ran entirely at *high* while the owner believed *max*.)
1. **Identity validation.** The user supplies a company name, ticker and exchange (see the skill for the argument contract). Using exchange and company sources, confirm that the **ticker on that exchange is the named company's listed equity**. Establish the legal name, listing segment (main board / SME), ISIN, share classes, reporting currency, fiscal-year convention, listing date (it determines how much history can exist), and listed parents or subsidiaries. **If the name, ticker and exchange do not identify the same security, or several securities match, stop and ask. Never research a guess.** Record identity facts as `CIO-C###` FACTs.
2. **Investment policy.** Read `config/investment_policy.json`. None of its values limit research depth. If `hurdle_rate` is null (the owner's setting), the hurdle for this run is the **cost of equity** that valuation computes with `valuation_tools.py wacc` from cited inputs. Adopt it after your audit and record it as `hurdle_rate` in the scenario inputs and the scorecard. The owner set no position or risk limits, so no sizing ceiling is computed.
3. **Cutoff and price.** Research cutoff = today (UTC) unless the user gave one. The price **`CIO-C001`** is the exchange close on the cutoff date (or the last trading day before it) from the NSE bhavcopy, tier 1: `python3 scripts/market_data.py close --run RUN_DIR --symbol <SYM> --date <cutoff> --out RUN_DIR/calc/cio_price.json` (run it right after step 4 creates the run). Cite the bhavcopy URL and its SHA-256. A BSE-only company: the BSE close from the exchange site, recorded the same way. Retrieve shares outstanding (`CIO-C002`, from the latest shareholding pattern or the exchange's company page) and compute market cap (`CIO-C003`, a CALCULATION). If no price can be verified at all, the run can still gather evidence, but it ends as `insufficient_evidence` (`SCORING.md` §8).
4. **Create the run:**
   `python3 scripts/new_run.py --ticker <T> --company "<legal name>" --exchange <EX> --segment <main|sme> --currency <CUR> --fy-end <MM-DD> [--isin <ISIN>] [--cutoff YYYY-MM-DD] [--hurdle <x>] [--reference-position <x>]` (pass the overrides only if the user gave them)
   It prints `RUN_DIR` (`research/companies/<T>/runs/<UTC RUN_ID>`), snapshots the investment policy into `run_manifest.json`, and never overwrites an existing run. Then write the preflight claims into `RUN_DIR/cio/cio_ledger.csv` (with `metric` keys such as `price`, `market_cap`).
5. **Manifest:** `python3 scripts/manifest.py RUN_DIR set price.value=<v> "price.timestamp=<timestamp (source)>" model.effective_cio=<model id from your system context, or unverified>` (add `model.effort_override=<level>` when the user passed `--effort`). Never invent a model ID.
6. **Research brief.** Fill `RUN_DIR/research_brief.md`: identity, listing date, cutoff, price claim, units and currency, fiscal-period labels, known consolidation issues (for example a captive finance arm), known group structure, the sector playbook(s) that apply, SME flag, policy status, the user's notes and, once step 9 is done, the document-map coverage and its cross-check flags. **No investment hypotheses, layer guesses or conclusions.**
7. **Source register** (`RUN_DIR/source_register.csv`, discovery leads only). Minimum categories: the investor-relations page and its document folder; exchange filing pages (results, announcements, shareholding); annual-report links covering **≥ 10 years** (or since listing); transcript and presentation pages covering **≥ 12 quarters**; credit-rating rationale pages; regulator, court or order searches relevant to the company; the industry-data publishers and the **ground-truth sources** from the sector playbook; and all relevant listed peers (at least 3; domestic and global where they inform the economics). The document map (step 9) supplies the exchange documents themselves. You may reuse source URLs from a prior run's ledgers; never include its findings.
8. **Local filing corpus (FilingForge).** Run `python3 scripts/corpus.py status --ticker <T>`.
   - **Company present:** run `python3 scripts/corpus.py catalog --ticker <T> --run RUN_DIR`. This writes `RUN_DIR/corpus/CATALOG.md` (core documents with periods, sizes and quality flags, coverage vs. the depth standard) and `catalog.csv` with SHA-256 fingerprints. Add the catalog to the source register and list its coverage gaps and quality flags in the brief. Tell specialists the corpus is **one of two channels at par**: they must still run full web research (it may be incomplete or contain download glitches) and cross-check decision-critical numbers against the exchange or IR original.
   - **Company absent:** this is the one preflight question to ask the user. *"<T> is not in your FilingForge library. Download it in FilingForge (annual reports, results, concalls, investor presentations), then reply 'go'; or reply 'web' to research from the web only."* Wait for the answer. If the user says 'web', proceed without the corpus.
   - The library is read-only input. Never modify it.
9. **Document acquisition: both channels, cross-checked** (`methodology/RESEARCH_PLAYBOOK.md` §1b). This replaces ten specialists each discovering and downloading the same filings.
   1. **Index the filings:** `python3 scripts/exchange_index.py all --run RUN_DIR --symbol <NSE symbol> [--scrip <BSE code>] --ir <IR documents page> [--ir <results page> ...] --wayback-prefix <IR document host/path/>`. Find the IR pages and the host/path where the IR site keeps its PDFs (open two or three document links) before you run it. This indexes NSE (annual reports, the full announcement history, results with XBRL, integrated filings, shareholding, board meetings, corporate actions, insider and SAST disclosures), BSE (annual reports back to the early 2000s, announcements, the scrip and ISIN lookup), the IR site and every archived copy of its documents. Any endpoint that fails is listed in `corpus/index_summary.json`; re-run that source once before accepting the gap.
   2. **Build the document map and download the core documents:** `python3 scripts/document_map.py build RUN_DIR --years 15 --quarters 24`. It downloads and validates the exchange copy of every annual report, transcript and presentation (mirrors and archive fallback, SHA-256 logged, ZIPs unpacked), cross-checks them against the local corpus (page counts, first-page text, period labels and duplicate labels), and builds the **text layer** of every core PDF (`doc_text.py`: page-anchored text, spreads split, tables rebuilt from coordinates, a section index, and the pages that must be read visually). Read `corpus/DOCUMENT_MAP.md`.
   3. **Structured exchange filings:** `python3 scripts/structured_filings.py fetch RUN_DIR` (BRSR XBRL by year, AGM and
      postal-ballot voting results by shareholder category, the Integrated Filings' audit-opinion statements and board
      composition) and `python3 scripts/xbrl_facts.py extract --run RUN_DIR --basis consolidated --unit "<unit>"` (results
      XBRL for the financials specialist's reconciliation). Read `corpus/STRUCTURED.md`.
   4. **Exchange filings to read:** `python3 scripts/reading.py fetch-filings RUN_DIR` downloads and converts the
      announcements that forensic work needs, over 10 years: related-party disclosures (Reg. 23(9)), auditor changes,
      credit ratings, penalty, litigation and tax-demand disclosures, schemes, and key-personnel changes.
   5. **Close the gaps with the librarian:** for every `missing` or `download_failed` core document in the map, and every
      failed filing download, write the list into a file (identity block, RUN_DIR, the list, and "find and register each
      per your definition") and run `python3 scripts/agent_driver.py librarian RUN_DIR --message-file <file>` (Bash, in
      the background; it runs the `librarian` as its own headless session on its pinned model and effort and logs it as
      stage `0`). Without the CLI, launch the `librarian` agent with the same text (description `librarian <RUN_ID>`). It
      registers what it finds (`document_map.py add`); re-run `reading.py fetch-filings` if it added filings. Put every remaining gap, with
      the librarian's attempt log, into the brief and the gap register; put every cross-check flag into the brief (which
      copy to use) and list suspected local-library defects for the owner.
   **A US run** (`jurisdiction` US in the manifest, from a NYSE or NASDAQ listing; `config/jurisdictions/US.json`):
   set `EQUITY_RESEARCH_USER_AGENT` to the owner's name and contact first (www.sec.gov refuses clients that do not
   say who they are). Steps 1 and 3 become `python3 scripts/edgar.py index --run RUN_DIR --cik <CIK>` (the filings,
   merged into the same exchange index) and `python3 scripts/edgar.py facts --run RUN_DIR --cik <CIK>` (XBRL company
   facts into `calc/xbrl_facts.csv`, USD million); find the CIK with `edgar.py cik TICKER`. Step 2 runs as written: the
   10-Ks are the annual reports. There are no structured exchange filings (voting results come from 8-K Item 5.07),
   and earnings-call transcripts are not filed with the SEC, so the librarian looks for them on the IR site. The
   risk-free rate is `edgar.py treasury --date <cutoff>`; daily prices `edgar.py prices TICKER --run RUN_DIR`.
   Select `us_filings` among the sector modules, and `us_banks` or `us_reits` where they apply.
9b. **The outside view of the company's history:** `python3 scripts/agent_driver.py events RUN_DIR` (Bash, in the
   background). The `historian` (Sonnet) builds a dated timeline of the company's major events over ten years from news,
   the web, the exchanges' indexes, rating agencies and regulators, each with the source it opened
   (`corpus/events.csv`, `corpus/EVENTS.md`; checked by `verify.py events`). Leads, never evidence. At Stage 0b
   `reading.py dossiers` checks every event against what the readers extracted (`corpus/dossiers/events.md`, must-read
   in every pack); an event the reports read do not show is either a reading miss or something the company did not
   disclose.
9c. **What the framework already knows (v4.0).** The orchestrator runs `python3 scripts/warehouse.py facts RUN_DIR`: the
   company's facts from the warehouse, as known at the cutoff (exchange results as filed, and earlier finished runs'
   verified tier 1–3 facts, never their conclusions), into `corpus/facts/`. For a key question that turns on how often
   something happens (sustained growth, margins, returns), compute the reference class by script and give it to the run:
   `python3 scripts/base_rates.py cagr --metric revenue --years 5 --threshold 0.20 --run RUN_DIR` or `dist --metric roe
   --period FY2025 --run RUN_DIR` (`metrics` lists what it derives). It is survivor-biased and says so; the CIO and the
   specialists weigh it as an outside view, never as a fact about the company. Agents never read the warehouse itself.
10. **Prior runs.** Do not show prior conclusions to specialists. Read a prior run's final report yourself only **after** Stage 2.
11. **Sector modules and the reading mode (methodology 3.2.0).** Select the sector modules that apply
    (`methodology/SECTOR_PLAYBOOKS.md`, the SECTOR_MODULES block: one per material sector of the company, plus
    `listed_subsidiaries`, `holding_companies`, `capital_allocation_roi` or `unlisted_segment_value` where they apply)
    and record them: `python3 scripts/manifest.py RUN_DIR set 'sector_modules=["nbfc","listed_subsidiaries"]'` (or `[]`
    with a note when none applies). Every module step goes into its owner's brief, needs its own checklist row and,
    where it names metrics, the ledger series to back a Done row. The run's reading mode is in the manifest
    (`reading_mode`, set by `new_run.py --reading on|off`; default off): **on** → Stage 0b; **off** → Stage 0c. It can
    change only before any specialist runs (`manifest.py RUN_DIR mode reading on|off --reason "..."`).

## Stage 0b — Reading stage (reading_mode on: every in-scope page read once, and recorded)

Only when the run's `reading_mode` is **on**; with reading off, go to Stage 0c.

A specialist cannot read four or five million tokens of reports in one context, so in run 20261012T132311Z the ten
agents together saw 11–17 % of each annual report while their reports implied more. The reading stage reads every
in-scope page once, in small fresh contexts, and records it page by page (`methodology/RESEARCH_PLAYBOOK.md` §1c,
`methodology/READING_SCHEMAS.md`, `methodology/MODEL_POLICY.md`).

1. **Plan:** `python3 scripts/reading.py plan RUN_DIR --years 5 --core-years 5 --quarters 24 --ppt-quarters 12` (the
   owner's scope: **every page** of the annual reports of the latest five fiscal years, and the **core sections** of
   the five before them: auditor's reports, CARO, IFC, the statements and every note, the Board's report and its
   statutory annexures, MD&A). The window is set by fiscal year (the latest is the newest report in the map or, if
   later, the newest one due by the cutoff), so a missing report never shifts it. If an in-scope report is missing,
   `plan` refuses and names it: run the librarian for it; only when it truly cannot be had (not yet listed, never
   published) record why with `python3 scripts/reading.py accept-gap RUN_DIR AR-FY<year> --reason "<why>"`, put it in
   the gap register, and plan again. A document an earlier run of the company read completely (same file, same
   reading format, every read audited) is reused, not read again (`--no-reuse` reads everything afresh). The plan
   splits every page into passages, classifies sections (critical ones are read twice), marks text of 60 characters
   or more (or a whole table) that repeats word for word elsewhere so it is read once (labels, values and shorter text
   are always read), marks the pages that must be viewed on the rendered image (no reliable text, raster images,
   numbers to confirm), and prints the volume. It also starts the **in-run calibration**: a stratified sample of
   chunks (one per non-critical section class first) is read by both models before any other non-critical chunk; when
   it is reconciled, a class whose Sonnet read matched the adjudicated result (at least 30 items, recall ≥ 0.98, zero
   material misses) is read by the second model alone for the rest of the run, and every other class stays double-read
   (`corpus/reading/calibration.json`, `BAKEOFF.md`; `--no-calibration` double-reads everything). Put the reading plan (scope, documents, reused documents, accepted gaps,
   pages, pages to view, chunks, estimated tokens, calibration status) into the brief. If readers already worked on an
   earlier plan of this run, `plan` refuses; re-plan only for a stated reason with `--replan "<reason>"`, which moves
   their work to `corpus/reading/superseded/` (nothing is deleted).
   Then run `python3 scripts/agent_driver.py estimate RUN_DIR` and put its cost, five-hour windows and weeks into the
   brief; tell the owner before reading starts (`engine/ESTIMATE.md`).
2. **Read with the engine:** `python3 scripts/agent_driver.py reading RUN_DIR`, started with Bash in the background
   (`run_in_background`); wait for its completion notification, do not poll. It reads each chunk in one call with no
   tools (the chunk and its rendered VIEW REQUIRED pages in the message): Opus (`critical-reader`) on every chunk, then
   an independent second read, Sonnet (`reader`) on critical sections and Haiku (`scanner`) on the others, the two
   never seeing each other's work; it checks every extraction (each anchor in its passage, every number of every field
   printed there, every passage and every significant number accounted for, a receipt for every page, every VIEW
   REQUIRED page shown), sends fix turns that name exactly what is missing, reads a chunk that still fails again with
   the agentic reader, resumes a session whose check fails, waits out usage limits and resumes the
   same session, issues a `resolved` launch whenever the two reads of a double-read chunk disagree, and records every
   session on its launch. None of this passes through this session's context. One launch at a time by default;
   `--parallel N` runs up to N, another starting only while the five-hour usage window is below 60 %, so parallel
   sessions do not all stop at the same limit (the tokens per launch are the same either way). Exit 0: every chunk is
   read, checked and reconciled. Exit 1: read the last lines of `_cache/engine/engine.log` and the failed launch's
   record in `corpus/reading/launches.json`, fix the cause, and run it again (it resumes where it stopped). A usage
   window that resets later than `--max-wait-hours` (default 12), or a weekly window above `--weekly-ceiling` (95 %, the
   owner's reserve), also stops it at a session boundary; run it again after the reset. If this session may close
   before the reading ends, give the owner the same command to run in a terminal
   (`nohup python3 scripts/agent_driver.py reading RUN_DIR &`); it is safe to stop and restart.
   - **Without the CLI** (`agent_driver.py cli` finds no `claude` binary): loop through the Agent tool instead. Run
     `python3 scripts/reading.py next RUN_DIR`; launch the agent it names with exactly its description and prompt (do
     not pass `model` or `effort`); wait for the completion notification; run `next` again until it prints that every
     chunk is read, checked and reconciled. After a usage limit, resume the same agent with SendMessage; if it cannot
     be resumed, run `next --restart "<why>"`, which closes that launch and issues its chunks afresh. The loop is
     driven by files, so it survives a compaction of this session: after one, re-read this section and run `next`.
   - Never ask a reader to shorten, sample or hurry.
3. **Dossiers and the record:** `python3 scripts/reading.py dossiers RUN_DIR`, then `python3 scripts/reading.py status RUN_DIR --strict`,
   which must exit 0: every in-scope page is read, repeat, structured or out of scope. `corpus/reading/COVERAGE.md` is the
   run's statement of what was read; nobody writes their own.
4. While `MODEL_POLICY.md` calibration is `pending`, every chunk is read by both models: say so in the brief, with the
   engine's measured time, tokens and cost so far (`python3 scripts/agent_driver.py show RUN_DIR`).
5. `python3 scripts/manifest.py RUN_DIR status specialists_running`

## Stage 0c — Web digest (reading_mode off, methodology 3.2.0)

With the reading stage off, nobody reads the filings page by page before the specialists start; the web digest gives
them a structured start instead, in the dossiers' shape, and every specialist reads its own domain's documents through
the text layer. Every digest item is a **tier-6 lead**, never evidence (`verify.py` blocks a FACT that cites one).

1. `python3 scripts/digest.py plan RUN_DIR` (the latest 10 annual reports, 24 transcript quarters and 12 presentation
   quarters of the document map, with the item types to look for; quarters whose exchange filing is only a cover letter
   are included, since the web is where their content is).
2. `python3 scripts/agent_driver.py digest RUN_DIR` in the background (three `digest` jobs, one per document type; Sonnet;
   each searches the web for summaries of each planned document, snapshots every page it uses, records every instance of
   the listed item types quoting its snapshot, logs every document in `SEARCH_LOG.md`, and runs `digest.py check` until it
   passes). Without the CLI, launch the `digest` agent once per type with the prompt `agent_driver.py` prints.
3. `python3 scripts/digest.py confirm RUN_DIR` (each item's number or wording searched for, by script, in the filing's
   Stage-0 text layer: page-confirmed, value located, conflict, not found).
4. `python3 scripts/digest.py build RUN_DIR` (topic files and one pack per specialist under `corpus/digest/`, the entity
   graph, the historian's events checked against the digest and the filings' text, `COVERAGE.md`) and
   `python3 scripts/digest.py status RUN_DIR --strict` (must exit 0).
5. When an earlier run of the company read some of the same documents, measure what the digest misses:
   `python3 scripts/digest.py calibrate RUN_DIR --reference <that RUN_DIR>`, and put the recall in the brief.
6. Put the digest's coverage (documents, items, page-confirmed share, documents with nothing found) in the brief, then
   `python3 scripts/manifest.py RUN_DIR status specialists_running`.
