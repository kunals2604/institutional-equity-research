#!/usr/bin/env python3
"""Append ledger rows (JSON list on stdin) to specialists/valuation_ledger.csv, all fields quoted.
Usage: python3 -I calc/valuation_ledger_add.py RUN_DIR < rows.json   (rows: list of dicts; missing keys blank)"""
import csv, json, sys
from pathlib import Path
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title","source_issuer",
        "source_url_or_id","source_date","retrieved_date","locator","source_tier","primary","confidence",
        "corroborated_by","contradicted_by","formula_or_inputs","notes"]
run = Path(sys.argv[1]); p = run / "specialists/valuation_ledger.csv"
rows = json.load(sys.stdin)
existing = {}
if p.exists():
    with open(p, newline="") as fh:
        for r in csv.DictReader(fh):
            existing[r["claim_id"]] = r
for r in rows:
    r.setdefault("author", "valuation"); r.setdefault("retrieved_date", "2026-10-12")
    existing[r["claim_id"]] = {c: str(r.get(c, "")) for c in COLS}   # replace on same id
with open(p, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, quoting=csv.QUOTE_ALL)
    w.writeheader()
    for k in sorted(existing, key=lambda x: int(x.split("-C")[1])):
        w.writerow(existing[k])
print("ledger rows:", len(existing))
