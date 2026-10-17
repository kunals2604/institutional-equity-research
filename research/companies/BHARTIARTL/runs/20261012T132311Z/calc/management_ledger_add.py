"""Append rows to the management ledger with exact header and full quoting.
Usage: python3 calc/management_ledger_add.py rows.json   (list of dicts keyed by column name)"""
import csv, json, os, sys
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title","source_issuer",
        "source_url_or_id","source_date","retrieved_date","locator","source_tier","primary","confidence",
        "corroborated_by","contradicted_by","formula_or_inputs","notes"]
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "specialists", "management_ledger.csv")
existing = set()
if os.path.exists(path):
    with open(path, newline="", encoding="utf-8") as f:
        existing = {r["claim_id"] for r in csv.DictReader(f)}
new = not os.path.exists(path)
rows = json.load(open(sys.argv[1], encoding="utf-8"))
with open(path, "a", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS, quoting=csv.QUOTE_ALL)
    if new: w.writeheader()
    n = 0
    for r in rows:
        if r["claim_id"] in existing:
            print("skip duplicate", r["claim_id"]); continue
        r.setdefault("author", "management"); r.setdefault("retrieved_date", "2026-10-12")
        w.writerow({c: r.get(c, "") for c in COLS}); n += 1
print("appended", n)
