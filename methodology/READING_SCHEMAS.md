# Reading Schemas — what the readers extract, and how completeness is proven

The reading stage (Stage 0b, `RESEARCH_PLAYBOOK.md` §1c) reads every page of every in-scope document once, in small
fresh contexts, and turns it into page-cited, quote-verified items. Specialists then start from complete topic
dossiers instead of searching raw files. This file is the contract for that work: the item types, their fields, the
section classes (and which are critical), and the rules a reader follows. `scripts/reading.py` parses the block below;
edit it here, then run the tests.

## Rules for every reader (the reader and critical-reader agents)

1. **Read every line of every chunk file assigned to you, in order.** The file's header explains its format:
   - `[a12] …` starts a passage (cite `a12`); its continuation lines are indented by four spaces;
   - `⟲ …` stands for passages that repeat text read elsewhere: you do not re-read them, and never cite them;
   - `· context …` shows, in full, text read elsewhere that the next passage may depend on: read it for meaning,
     but never cite it or extract items from it;
   - `(running header)`, `(page number)`, `[L half]` and `[R half]` lines are page furniture.

   Never stop early, sample or skim.
2. **Extract every instance of every item type that occurs**, not the ones you judge important. Materiality is
   decided later by the specialists. When a fact (a number, date, party, obligation, commitment, event or
   condition) fits no type, record it as `other_fact`. Anything non-standard, inconsistent or surprising is also
   recorded as `unusual`.
   - **One fact per item.** An item records one fact: one amount per field, one opinion per report, **one CARO
     clause per item** (a table listing several clauses per company is one item per company and clause, the company
     in `report`, the clause's footnote or remark as its `answer`; the check rejects an item naming several
     clauses). Choose the type the fact is (an explanation of a change is `explanation_of_variance`; a statement on
     where capital goes is `capital_allocation_statement`), not the nearest general type.
3. **Tag, do not transcribe.** An item is a tag on the page, not a restatement of it: the dossier prints the
   passage itself, so never paraphrase it.
   - `anchor` is a few consecutive words copied verbatim from the cited passage that state the fact: at least three
     words, or one whole printed line or table cell of it (a statement row: its label; a lone value: the value; a
     heading), or the whole passage when it is shorter; for an item with `to`, anywhere in its span; for a table tag,
     in the table's first five passages (its title, heading rows or first row). Do not copy the passage. The check attaches the printed text as the item's `quote`: the cited passage, run on into the
     passages after it on the same page (eight at most) until it holds the anchor and every number of every field.
   - When a fact runs over several passages (a key audit matter, a CARO remark, a policy, a claim, a litigation
     description, an answer on a call), add `"to": "<last passage id>"` (forty passages at most, across pages of the
     chunk): the quote is then the whole span, and the dossier prints all of it.
   - Write the type's **key fields** (`key` in the schema below: names, amounts, periods, counterparties, the opinion,
     the CARO answer, the rating). Its other fields are optional; when you write one, keep it to a short label (under
     about twelve words), never a summary of the passage.
3a. **Tables: tag the table once; the script writes its rows.** For a table printed one row per passage
   (`| label | … | 1,234 | 1,100 |`), write one `table` item instead of an item per row:
   ```json
   {"type": "table", "unit": "a3", "to": "a131", "page": 216, "period": "as at 31-Mar-2026", "basis": "consolidated",
    "anchor": "Property, plant and equipment", "fields": {"item_type": "statement_line", "label_cell": 1,
    "columns": {"value_current": 3, "value_prior": 4}, "static": {"statement": "Consolidated Balance Sheet",
    "unit_of_amount": "INR million"}, "skip": {"a4": "column headings"}}}
   ```
   - `unit` … `to` is the table's first and last passage; `item_type` is the type each row becomes; `label_cell` is
     the cell holding the row label (1 = the first cell); `columns` maps each amount field of the type to its cell
     (count every cell, empty ones too, as printed between the `|`); `static` gives the fields every row shares
     (statement, unit, segment); `label_field` names the field the label goes to when it is not the type's first.
   - A table with one column per period of a single-value type (a KPI, an ESG metric: `value`) uses
     `"series": {"FY 2024-25": 3, "FY 2023-24": 4}` instead of `columns`: one item per row and period.
   - A table the text layer printed **one cell per line** (`cell_layout`, VIEW REQUIRED: first confirm on the page that
     each label is followed by its own values) uses `"layout": "cells", "values_per_row": 2` and numbers the value cells
     after the label from 1. A row that prints a different number of values is an error until you write its item
     yourself: a missing cell would shift its values into the wrong year.
   - The check expands every row, exactly as printed: a row with values becomes an item (its label, the row's
     headings as `section`, every value copied from its cell); a row whose mapped cells are empty is a heading; a row
     whose mapped cells are not values (merged or text cells) is an error until you write its item yourself or name it
     in `skip` with the reason. Name column-heading rows (the years) in `skip`. Rows of a table whose meaning is not
     one row = one fact (a matrix, footnoted cells, values that need their column heading to make sense) are written
     item by item. Tag every table you read; the script never guesses which tables exist.
4. **Numbers exactly as printed, and only printed ones.** Every amount field is copied **exactly as printed** (for
   example `"(1,234.5)"`, `"12.3%"`, `"-"`). Every number you write in **any** field, descriptions included, must be
   printed in the cited passage or the passages after it on its page; a script checks each one. Never compute, convert, round, sum, translate units or infer a
   value. An `unusual` item that compares passages lists them in `"related": ["a40", "a52"]` (passages of the same
   chunk) and may use numbers printed in them; it states what differs ("the listed amounts do not add up to the
   printed total 6,843,594"), never a computed figure. The specialists recompute with scripts.
5. **Cite the passage id and the PDF page** of each item (`unit` = the passage id, for example `"a12"`). A fact
   printed only in a page image cites `unit` = `p<page>` with `"source": "rendered"` (allowed only on pages marked
   `VIEW REQUIRED`); a fact that is in a passage always cites the passage.
6. **Pages marked `VIEW REQUIRED`** must be opened on the rendered PDF page (Read tool, `pages: "<n>"`):
   - *no reliable text* (image-only, sideways or garbled): read everything from the image;
   - *numbers to confirm* (`table_numbers_mismatch`, `table_alignment_uncertain`, and `cell_layout`, a table the
     text layer printed one cell per line): read the passages, and confirm on the image every number you extract
     and which line it belongs to;
   - *images*: read the passages, then extract every fact printed only in an image (a chart, an infographic, a
     scanned table), cited `p<page>` with `"source": "rendered"`.

   When the page is too small or sideways to read, run `python3 scripts/reading.py render RUN_DIR <chunk> <page>
   [--dpi 200] [--rotate 90|270] [--parts 2]` and Read the image files it prints (the only other files you may
   create or open). The page receipt says `"viewed": true`. The reading audit checks from your transcript that you
   opened every such page.
7. **Text order on multi-column pages.** The text layer orders a page's text blocks by position, and on some
   multi-column pages a paragraph appears out of place (a passage starts mid-sentence, a heading follows its own
   text, an award or figure sits under the wrong heading). Attribute every fact to the heading, segment and period it
   sits under **on the page**, not to the passage printed before it. Whenever the order or a number looks wrong, open
   that page of your chunk on the rendered PDF (allowed for any page of your chunk; list it in `pages_viewed`, and its
   receipt says `"viewed": true`) and say what you found in the chunk receipt's `notes`.
7a. **Account for every passage and every number** (checked by script). Every passage of the chunk is cited by an item
    (its `unit`, inside a `to` span or a table span) or listed in the chunk receipt's `"no_fact"` (ids or ranges such as
    `"a10-a14"`) because it states no fact of any type. Every significant number a cited passage prints (amounts,
    percentages, counts; not years, the day of a date, or note, section, rule or page references) is recorded in a field
    of an item citing that passage, or set aside in the receipt's `"numbers_not_facts"` (`{"a12": ["135"]}`) because it
    is a reference, not a fact (a short span item of up to eight passages, such as a key audit matter, carries its
    numbers in its quote). The check names every passage and number left over.
8. **One page receipt per page** of the chunk: `items` when at least one item cites the page, otherwise `no_items`
   with the reason (for example `"photograph and caption only"`).
9. **No outside knowledge, no web, no other files**: only the chunk files, this schema and the document PDFs (and
   the page images `render` writes). Do not judge credibility, quality or meaning; that is the specialists' work.
10. **Write in parts, with the Write tool**, into the chunk's parts directory named in the launch file: `01.jsonl`
    (about 40 items), then `02.jsonl`, and so on; the page receipts and the chunk receipt go in the last part. Never
    write the extraction file itself and never use the shell to write: `python3 scripts/reading.py check RUN_DIR
    <chunk> --role <role>` assembles the parts, in order, and checks them. Short parts keep every turn short and keep
    what you wrote if the launch is interrupted. Fix every error the check names in the part file it names (Edit
    tool) and re-run it until it prints PASS. Do not delete items to pass a check; fix the anchor or the field. Your
    final message is exactly one line (the launch file gives it); process notes go in the chunk receipt's `notes`.

## Output format (one JSON object per line, `RUN_DIR/corpus/reading/extractions/<chunk>.<role>.jsonl`)

```json
{"type": "contingent_liability", "unit": "a12", "page": 214, "period": "as at 31-Mar-2025", "basis": "consolidated",
 "anchor": "Claims against the Group not acknowledged as debts", "fields": {"category": "Claims not acknowledged as debts",
 "amount_current": "1,23,456", "amount_prior": "1,10,234", "unit_of_amount": "INR million", "description": ""}}
{"type": "unusual", "unit": "a40", "page": 121, "period": "FY 2025-26", "basis": "na", "anchor": "Total 6,843,594",
 "related": ["a31", "a32"], "fields": {"description": "The district amounts listed above it do not add up to the printed total 6,843,594; Fatehpur is listed twice", "why_unusual": "a table total that does not foot"}}
{"type": "kpi", "unit": "p57", "page": 57, "period": "FY2025", "basis": "na", "source": "rendered",
 "fields": {"name": "Homes passed", "value": "2.5 Mn", "unit_of_value": "", "period_label": "FY25"}}
{"type": "key_audit_matter", "unit": "a61", "to": "a74", "page": 302, "period": "FY2025", "basis": "standalone",
 "anchor": "Revenue recognition and IT systems", "fields": {"report": "standalone", "title": "Revenue recognition and IT systems"}}
{"type": "table", "unit": "a80", "to": "a96", "page": 214, "period": "as at 31-Mar-2025", "basis": "consolidated",
 "anchor": "Claims against the Group", "fields": {"item_type": "contingent_liability", "label_cell": 1,
 "columns": {"amount_current": 2, "amount_prior": 3}, "static": {"unit_of_amount": "INR million"}}}
{"type": "page_receipt", "page": 214, "status": "items", "viewed": false, "reason": ""}
{"type": "chunk_receipt", "chunk": "AR-FY2025-c18", "role": "reader", "model": "<model id from your system context>", "units_read": 41, "pages_viewed": [57], "notes": ""}
```

Unknown or not-stated key fields are `""`; key fields are never omitted; other fields are optional (`related`, `to`,
`source` and `notes` too; an item cited to a rendered page `p<n>` has no anchor). The assembled extraction holds each
table tag followed by the rows the check expanded from it (`from_table`).
`period` and `basis` (`standalone`, `consolidated` or `na`) are as stated in the document.

## Critical classes, core classes and the double read

Classes marked `core` are the sections read in the core years (the five fiscal years before the latest five, whose
reports are otherwise not read page by page): the auditor's reports, CARO and IFC, the statements and every note,
the Board's report and its statutory annexures (AOC-1, AOC-2, secretarial audit, remuneration disclosures) and MD&A.

A chunk whose section class is **critical** is read twice, independently: by the `critical-reader` (Opus) and by the
`reader` (Sonnet). `reading.py compare` lists every disagreement (an item one read has and the other lacks, or a
different amount, opinion or answer for the same passage), and a fresh `critical-reader` resolves each one against
the page (labels A and B, models not disclosed). Which classes a single Sonnet read may cover is set by
`MODEL_POLICY.md` from the calibration bake-off; until the bake-off has passed, every class is double-read.

## Canonical schema

<!-- READING_SCHEMA:BEGIN -->
```json
{
  "schema_version": "1.2",
  "topics": {
    "auditor": {"title": "Auditor's reports, KAMs, CARO, IFC, auditor changes and fees", "owners": ["filings", "financials", "management"]},
    "accounting": {"title": "Accounting policies, estimates, changes and restatements", "owners": ["filings", "financials"]},
    "contingencies": {"title": "Contingent liabilities, commitments, guarantees, litigation, tax disputes, provisions", "owners": ["filings", "bear-case", "valuation"]},
    "related_parties": {"title": "Related parties, transactions, balances, approvals, s.186 loans and guarantees", "owners": ["filings", "management", "bear-case"]},
    "debt_and_capital": {"title": "Borrowings, maturities, covenants, defaults, ratings, charges, capital actions, dividends", "owners": ["financials", "filings", "valuation", "special-situations"]},
    "results_and_segments": {"title": "Statement lines, segments, exceptional items, KPIs, revenue mix", "owners": ["financials", "moat", "industry", "valuation"]},
    "structure_and_transactions": {"title": "Subsidiaries and associates, acquisitions, disposals, schemes, AOC-1", "owners": ["special-situations", "management", "filings", "financials"]},
    "governance": {"title": "Board, committees, remuneration, incentives, resolutions, penalties, secretarial audit, CSR", "owners": ["management", "filings", "bear-case"]},
    "strategy_and_outlook": {"title": "Management claims, targets and guidance, capital allocation, capex plans, risks, industry data", "owners": ["concalls", "management", "industry", "moat", "scuttlebutt", "special-situations"]},
    "transcripts": {"title": "Earnings-call statements, questions, answers, explanations and numbers", "owners": ["concalls", "management", "bear-case", "industry", "moat"]},
    "esg": {"title": "BRSR and sustainability metrics and incidents", "owners": ["filings", "management", "scuttlebutt"]},
    "other": {"title": "Unusual items and facts that fit no other type", "owners": ["financials", "filings", "management", "industry", "moat", "concalls", "valuation", "bear-case", "special-situations", "scuttlebutt"]}
  },
  "types": {
    "audit_opinion": {"topic": "auditor", "material": true, "fields": ["report", "opinion", "auditor_firm", "basis_summary"], "key": ["report", "opinion", "auditor_firm"], "amounts": []},
    "emphasis_of_matter": {"topic": "auditor", "material": true, "fields": ["report", "matter"], "key": ["report"], "amounts": []},
    "other_matter": {"topic": "auditor", "material": false, "fields": ["report", "matter"], "key": ["report"], "amounts": []},
    "material_uncertainty_going_concern": {"topic": "auditor", "material": true, "fields": ["report", "matter"], "key": ["report"], "amounts": []},
    "key_audit_matter": {"topic": "auditor", "material": true, "fields": ["report", "title", "why_kam", "response_summary"], "key": ["report", "title"], "amounts": []},
    "caro_clause": {"topic": "auditor", "material": true, "fields": ["report", "clause", "answer", "adverse"], "key": ["report", "clause", "answer", "adverse"], "amounts": []},
    "ifc_opinion": {"topic": "auditor", "material": true, "fields": ["report", "opinion", "exceptions"], "key": ["report", "opinion"], "amounts": []},
    "auditor_signoff": {"topic": "auditor", "material": false, "fields": ["report", "firm", "frn", "partner", "membership_no", "udin", "date", "place"], "key": ["report", "firm", "frn", "partner", "membership_no", "udin", "date", "place"], "amounts": []},
    "fraud_reported": {"topic": "auditor", "material": true, "fields": ["reporter", "description", "amount", "unit_of_amount"], "key": ["reporter", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "auditor_change": {"topic": "auditor", "material": true, "fields": ["from_firm", "to_firm", "reason", "date"], "key": ["from_firm", "to_firm", "date"], "amounts": []},
    "auditor_fee": {"topic": "auditor", "material": false, "fields": ["service", "amount", "unit_of_amount"], "key": ["service", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "accounting_policy": {"topic": "accounting", "material": false, "fields": ["area", "summary"], "key": ["area"], "amounts": []},
    "critical_estimate": {"topic": "accounting", "material": true, "fields": ["area", "summary"], "key": ["area"], "amounts": []},
    "policy_change": {"topic": "accounting", "material": true, "fields": ["area", "change_summary", "effect"], "key": ["area"], "amounts": []},
    "restatement": {"topic": "accounting", "material": true, "fields": ["item", "description", "amount", "unit_of_amount"], "key": ["item", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "new_standard": {"topic": "accounting", "material": false, "fields": ["standard", "effect_summary"], "key": ["standard"], "amounts": []},
    "contingent_liability": {"topic": "contingencies", "material": true, "fields": ["category", "amount_current", "amount_prior", "unit_of_amount", "description"], "key": ["category", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "commitment": {"topic": "contingencies", "material": true, "fields": ["category", "amount_current", "amount_prior", "unit_of_amount"], "key": ["category", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "guarantee": {"topic": "contingencies", "material": true, "fields": ["beneficiary", "purpose", "amount", "unit_of_amount"], "key": ["beneficiary", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "legal_or_regulatory_matter": {"topic": "contingencies", "material": true, "fields": ["forum", "counterparty", "subject", "amount", "unit_of_amount", "status"], "key": ["forum", "counterparty", "amount", "unit_of_amount", "status"], "amounts": ["amount"]},
    "tax_dispute": {"topic": "contingencies", "material": true, "fields": ["tax_type", "forum", "period_in_dispute", "amount", "unit_of_amount", "status"], "key": ["tax_type", "forum", "period_in_dispute", "amount", "unit_of_amount", "status"], "amounts": ["amount"]},
    "provision_movement": {"topic": "contingencies", "material": false, "fields": ["provision", "opening", "additions", "utilised", "reversed", "closing", "unit_of_amount"], "key": ["provision", "opening", "additions", "utilised", "reversed", "closing", "unit_of_amount"], "amounts": ["opening", "additions", "utilised", "reversed", "closing"]},
    "related_party": {"topic": "related_parties", "material": false, "fields": ["name", "relationship"], "key": ["name", "relationship"], "amounts": []},
    "rpt_transaction": {"topic": "related_parties", "material": true, "fields": ["party", "nature", "amount_current", "amount_prior", "unit_of_amount"], "key": ["party", "nature", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "rpt_balance": {"topic": "related_parties", "material": true, "fields": ["party", "nature", "amount_current", "amount_prior", "unit_of_amount"], "key": ["party", "nature", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "rpt_approval": {"topic": "related_parties", "material": true, "fields": ["party", "nature", "approval_type", "limit_amount", "unit_of_amount"], "key": ["party", "nature", "approval_type", "limit_amount", "unit_of_amount"], "amounts": ["limit_amount"]},
    "loan_guarantee_investment_186": {"topic": "related_parties", "material": true, "fields": ["counterparty", "nature", "amount", "unit_of_amount", "purpose"], "key": ["counterparty", "nature", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "borrowing": {"topic": "debt_and_capital", "material": true, "fields": ["instrument", "lender_or_holder", "amount_current", "amount_prior", "unit_of_amount", "rate", "maturity", "security"], "key": ["instrument", "lender_or_holder", "amount_current", "amount_prior", "unit_of_amount", "rate", "maturity"], "amounts": ["amount_current", "amount_prior"]},
    "debt_maturity": {"topic": "debt_and_capital", "material": true, "fields": ["bucket", "amount", "unit_of_amount"], "key": ["bucket", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "covenant": {"topic": "debt_and_capital", "material": true, "fields": ["description", "status"], "key": ["status"], "amounts": []},
    "default_or_breach": {"topic": "debt_and_capital", "material": true, "fields": ["description", "amount", "unit_of_amount", "date"], "key": ["amount", "unit_of_amount", "date"], "amounts": ["amount"]},
    "credit_rating": {"topic": "debt_and_capital", "material": true, "fields": ["agency", "instrument", "rating", "outlook", "action", "date"], "key": ["agency", "instrument", "rating", "outlook", "action", "date"], "amounts": []},
    "charge_or_pledge": {"topic": "debt_and_capital", "material": true, "fields": ["holder", "asset", "amount", "unit_of_amount"], "key": ["holder", "asset", "amount", "unit_of_amount"], "amounts": ["amount"]},
    "capital_action": {"topic": "debt_and_capital", "material": true, "fields": ["action", "details", "amount", "unit_of_amount", "date"], "key": ["action", "amount", "unit_of_amount", "date"], "amounts": ["amount"]},
    "dividend": {"topic": "debt_and_capital", "material": false, "fields": ["dividend_type", "per_share", "total", "unit_of_amount", "record_date"], "key": ["dividend_type", "per_share", "total", "unit_of_amount", "record_date"], "amounts": ["per_share", "total"]},
    "statement_line": {"topic": "results_and_segments", "material": false, "fields": ["statement", "line_item", "value_current", "value_prior", "unit_of_amount"], "key": ["statement", "line_item", "value_current", "value_prior", "unit_of_amount"], "amounts": ["value_current", "value_prior"]},
    "segment_data": {"topic": "results_and_segments", "material": true, "fields": ["segment", "metric", "value_current", "value_prior", "unit_of_amount"], "key": ["segment", "metric", "value_current", "value_prior", "unit_of_amount"], "amounts": ["value_current", "value_prior"]},
    "exceptional_item": {"topic": "results_and_segments", "material": true, "fields": ["description", "amount_current", "amount_prior", "unit_of_amount"], "key": ["description", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "kpi": {"topic": "results_and_segments", "material": false, "fields": ["name", "value", "unit_of_value", "period_label"], "key": ["name", "value", "unit_of_value", "period_label"], "amounts": ["value"]},
    "revenue_disaggregation": {"topic": "results_and_segments", "material": false, "fields": ["category", "amount_current", "amount_prior", "unit_of_amount"], "key": ["category", "amount_current", "amount_prior", "unit_of_amount"], "amounts": ["amount_current", "amount_prior"]},
    "subsidiary_or_associate": {"topic": "structure_and_transactions", "material": false, "fields": ["name", "relationship", "holding_pct", "country", "change"], "key": ["name", "relationship", "holding_pct", "country", "change"], "amounts": ["holding_pct"]},
    "subsidiary_financials": {"topic": "structure_and_transactions", "material": false, "fields": ["name", "revenue", "profit", "net_worth", "unit_of_amount"], "key": ["name", "revenue", "profit", "net_worth", "unit_of_amount"], "amounts": ["revenue", "profit", "net_worth"]},
    "business_combination": {"topic": "structure_and_transactions", "material": true, "fields": ["target", "consideration", "goodwill", "unit_of_amount", "date"], "key": ["target", "consideration", "goodwill", "unit_of_amount", "date"], "amounts": ["consideration", "goodwill"]},
    "disposal_or_deconsolidation": {"topic": "structure_and_transactions", "material": true, "fields": ["asset_or_entity", "consideration", "gain_loss", "unit_of_amount", "date"], "key": ["asset_or_entity", "consideration", "gain_loss", "unit_of_amount", "date"], "amounts": ["consideration", "gain_loss"]},
    "scheme_or_restructuring": {"topic": "structure_and_transactions", "material": true, "fields": ["description", "status", "date"], "key": ["status", "date"], "amounts": []},
    "board_member": {"topic": "governance", "material": false, "fields": ["name", "category", "role", "tenure_or_appointment"], "key": ["name", "category", "role", "tenure_or_appointment"], "amounts": []},
    "board_change": {"topic": "governance", "material": true, "fields": ["name", "change", "date", "reason"], "key": ["name", "change", "date"], "amounts": []},
    "committee": {"topic": "governance", "material": false, "fields": ["name", "members", "meetings"], "key": ["name", "members", "meetings"], "amounts": []},
    "remuneration": {"topic": "governance", "material": true, "fields": ["name", "role", "amount", "unit_of_amount", "ratio_to_median"], "key": ["name", "role", "amount", "unit_of_amount", "ratio_to_median"], "amounts": ["amount"]},
    "esop_or_incentive": {"topic": "governance", "material": false, "fields": ["scheme", "details", "grants", "exercise_price"], "key": ["scheme", "grants", "exercise_price"], "amounts": []},
    "shareholder_resolution": {"topic": "governance", "material": true, "fields": ["meeting", "resolution", "resolution_type", "subject", "outcome"], "key": ["meeting", "resolution", "resolution_type", "subject", "outcome"], "amounts": []},
    "penalty_or_noncompliance": {"topic": "governance", "material": true, "fields": ["authority", "description", "amount", "unit_of_amount", "date"], "key": ["authority", "amount", "unit_of_amount", "date"], "amounts": ["amount"]},
    "secretarial_observation": {"topic": "governance", "material": true, "fields": ["observation", "management_response"], "key": [], "amounts": []},
    "whistleblower_or_complaints": {"topic": "governance", "material": false, "fields": ["category", "count", "summary"], "key": ["category", "count"], "amounts": []},
    "csr": {"topic": "governance", "material": false, "fields": ["obligation", "spent", "unspent", "unit_of_amount"], "key": ["obligation", "spent", "unspent", "unit_of_amount"], "amounts": ["obligation", "spent", "unspent"]},
    "management_claim": {"topic": "strategy_and_outlook", "material": false, "fields": ["topic", "claim", "speaker"], "key": ["topic", "speaker"], "amounts": []},
    "target_or_guidance": {"topic": "strategy_and_outlook", "material": true, "fields": ["metric", "target", "deadline", "speaker", "conditions"], "key": ["metric", "target", "deadline", "speaker"], "amounts": []},
    "capital_allocation_statement": {"topic": "strategy_and_outlook", "material": true, "fields": ["topic", "statement", "speaker"], "key": ["topic", "speaker"], "amounts": []},
    "capex_plan": {"topic": "strategy_and_outlook", "material": true, "fields": ["amount", "unit_of_amount", "period_label", "purpose"], "key": ["amount", "unit_of_amount", "period_label"], "amounts": ["amount"]},
    "risk_disclosure": {"topic": "strategy_and_outlook", "material": false, "fields": ["risk", "description", "mitigation"], "key": ["risk"], "amounts": []},
    "strategy_initiative": {"topic": "strategy_and_outlook", "material": false, "fields": ["initiative", "description", "timeline"], "key": ["initiative", "timeline"], "amounts": []},
    "market_or_industry_data": {"topic": "strategy_and_outlook", "material": false, "fields": ["metric", "value", "unit_of_value", "source_cited", "period_label"], "key": ["metric", "value", "unit_of_value", "source_cited", "period_label"], "amounts": ["value"]},
    "competitor_mention": {"topic": "strategy_and_outlook", "material": false, "fields": ["competitor", "statement"], "key": ["competitor"], "amounts": []},
    "forward_statement": {"topic": "transcripts", "material": true, "fields": ["speaker", "topic", "metric", "target", "deadline", "hedging_words"], "key": ["speaker", "topic", "metric", "target", "deadline", "hedging_words"], "amounts": []},
    "analyst_question": {"topic": "transcripts", "material": false, "fields": ["analyst", "firm", "topic", "question_summary"], "key": ["analyst", "firm", "topic"], "amounts": []},
    "management_answer": {"topic": "transcripts", "material": false, "fields": ["speaker", "to_question_unit", "topic", "answer_summary", "answer_units"], "key": ["speaker", "to_question_unit", "topic", "answer_units"], "amounts": []},
    "explanation_of_variance": {"topic": "transcripts", "material": true, "fields": ["metric", "explanation", "speaker"], "key": ["metric", "speaker"], "amounts": []},
    "disclosed_number": {"topic": "transcripts", "material": false, "fields": ["metric", "value", "unit_of_value", "period_label", "speaker"], "key": ["metric", "value", "unit_of_value", "period_label", "speaker"], "amounts": ["value"]},
    "esg_metric": {"topic": "esg", "material": false, "fields": ["metric", "value", "unit_of_value", "period_label"], "key": ["metric", "value", "unit_of_value", "period_label"], "amounts": ["value"]},
    "esg_incident": {"topic": "esg", "material": true, "fields": ["description", "amount", "unit_of_amount"], "key": ["amount", "unit_of_amount"], "amounts": ["amount"]},
    "unusual": {"topic": "other", "material": true, "fields": ["description", "why_unusual"], "key": ["description", "why_unusual"], "amounts": []},
    "other_fact": {"topic": "other", "material": false, "fields": ["description"], "key": [], "amounts": []},
    "table": {"topic": "other", "material": false, "fields": ["item_type", "label_cell", "label_field", "columns", "series", "series_field", "static", "skip"], "key": ["item_type", "label_cell"], "amounts": []}
  },
  "classes": {
    "auditor_report": {"critical": true, "core": true, "hint": ["audit_opinion", "emphasis_of_matter", "other_matter", "material_uncertainty_going_concern", "key_audit_matter", "auditor_signoff", "fraud_reported"]},
    "caro": {"critical": true, "core": true, "hint": ["caro_clause", "default_or_breach", "fraud_reported", "tax_dispute", "auditor_signoff"]},
    "ifc": {"critical": true, "core": true, "hint": ["ifc_opinion", "auditor_signoff"]},
    "notes_critical": {"critical": true, "core": true, "hint": ["accounting_policy", "critical_estimate", "policy_change", "restatement", "contingent_liability", "commitment", "guarantee", "legal_or_regulatory_matter", "tax_dispute", "related_party", "rpt_transaction", "rpt_balance", "borrowing", "debt_maturity", "covenant", "default_or_breach", "exceptional_item", "segment_data", "business_combination", "disposal_or_deconsolidation", "subsidiary_or_associate"]},
    "board": {"critical": true, "core": true, "hint": ["loan_guarantee_investment_186", "rpt_approval", "fraud_reported", "credit_rating", "auditor_change", "board_change", "capital_action", "dividend", "management_claim", "unusual"]},
    "board_annex": {"critical": false, "hint": ["csr", "other_fact", "kpi", "esg_metric"]},
    "aoc1": {"critical": true, "core": true, "hint": ["subsidiary_financials", "subsidiary_or_associate"]},
    "aoc2": {"critical": true, "core": true, "hint": ["rpt_transaction", "rpt_approval"]},
    "secretarial": {"critical": true, "core": true, "hint": ["secretarial_observation", "penalty_or_noncompliance"]},
    "filing_critical": {"critical": true, "hint": ["rpt_transaction", "rpt_balance", "auditor_change", "audit_opinion"]},
    "statements": {"critical": false, "core": true, "hint": ["statement_line"]},
    "notes": {"critical": false, "core": true, "hint": ["statement_line", "provision_movement", "revenue_disaggregation", "kpi", "other_fact"]},
    "mdna": {"critical": false, "core": true, "hint": ["management_claim", "target_or_guidance", "capex_plan", "risk_disclosure", "kpi", "market_or_industry_data", "segment_data"]},
    "cg": {"critical": false, "hint": ["board_member", "board_change", "committee", "remuneration", "auditor_fee", "penalty_or_noncompliance", "whistleblower_or_complaints", "related_party"]},
    "remuneration": {"critical": false, "core": true, "hint": ["remuneration", "esop_or_incentive"]},
    "notice": {"critical": false, "hint": ["shareholder_resolution", "remuneration", "rpt_approval", "capital_action", "board_change"]},
    "brsr": {"critical": false, "hint": ["esg_metric", "esg_incident", "penalty_or_noncompliance", "whistleblower_or_complaints"]},
    "narrative": {"critical": false, "hint": ["management_claim", "target_or_guidance", "strategy_initiative", "kpi", "capital_allocation_statement", "risk_disclosure", "market_or_industry_data"]},
    "transcript": {"critical": false, "hint": ["forward_statement", "analyst_question", "management_answer", "explanation_of_variance", "disclosed_number", "target_or_guidance", "capital_allocation_statement", "competitor_mention"]},
    "presentation": {"critical": false, "hint": ["kpi", "segment_data", "target_or_guidance", "management_claim", "market_or_industry_data", "capex_plan"]},
    "filing": {"critical": false, "hint": ["penalty_or_noncompliance", "legal_or_regulatory_matter", "tax_dispute", "credit_rating", "board_change", "scheme_or_restructuring", "capital_action", "other_fact"]}
  },
  "critical_note_title": "accounting polic|material accounting|critical (accounting )?(estimates|judg)|significant (accounting )?(estimates|judg)|contingent|commitment|related part|borrowing|debt|loans?\\b|lease liabilit|exceptional|segment|subsequent event|business combination|acquisition|disposal|discontinued|impairment|provisions?\\b|income tax|deferred tax|tax (expense|matter)|financial risk|capital management|going concern|restate|prior period|investment in subsidiar|interest in other entit|share.based|employee stock|guarantee|regulatory|licen[cs]e fee|spectrum|agr\\b|financial instrument|fair value"
}
```
<!-- READING_SCHEMA:END -->
