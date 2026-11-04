---
name: scan
description: Every company in the warehouse on one table as known on a date — value, quality, growth, price record, forensic flags and an ordering rank — as a lead list for triage. Scripts only, no agent. Use when the owner asks what to look at next.
argument-hint: "[YYYY-MM-DD] [NSE|BSE|US] [--top N] [--min-traded-inr X]"
---

# /scan

**Arguments:** `$ARGUMENTS`

1. `python3 scripts/warehouse.py status`. If the warehouse has no prices for the date or no results facts, say what to
   load and stop: `warehouse.py ingest-prices --exchange NSE --from ... --to ...` (about 250 requests a year) and
   `warehouse.py crawl-xbrl --symbols universe:<date>` (resumable; days for the whole universe). For US names,
   `warehouse.py crawl-edgar` and `ingest-us-prices`.
2. `python3 scripts/scan.py run --date <date, default the last day with prices> --exchange <NSE> [--top N]`.
3. Show the top of `SCAN_<date>_<exchange>.md` and the flag counts, and say plainly what the scan is: a survivor-biased
   lead list from facts as filed, ordered by a rank that does not say what to buy. Suggest `/triage SYMBOL` for the names
   the owner picks; never pick for them.
