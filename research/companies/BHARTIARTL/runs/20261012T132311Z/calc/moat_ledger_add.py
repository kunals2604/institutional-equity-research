"""Append rows to specialists/moat_ledger.csv (fully quoted). Usage: python3 moat_ledger_add.py rows.py
rows.py defines ROWS = [dict(...)] using the ledger columns; missing columns default to ''."""
import csv, os, sys, runpy
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title","source_issuer","source_url_or_id","source_date","retrieved_date","locator","source_tier","primary","confidence","corroborated_by","contradicted_by","formula_or_inputs","notes"]
L = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "specialists", "moat_ledger.csv")
rows = runpy.run_path(sys.argv[1])["ROWS"]
existing = set()
if os.path.exists(L):
    existing = {r["claim_id"] for r in csv.DictReader(open(L))}
new = not os.path.exists(L)
with open(L, "a", newline="") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL)
    if new: w.writerow(COLS)
    n = 0
    for r in rows:
        if r["claim_id"] in existing: continue
        r.setdefault("author", "moat"); r.setdefault("retrieved_date", "2026-10-12")
        w.writerow([r.get(c, "") for c in COLS]); n += 1
print("appended", n)
