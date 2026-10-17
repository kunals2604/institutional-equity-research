"""Append claims to the bear-case ledger (QUOTE_ALL CSV). Usage: python3 ledger_add.py rows.json
rows.json: list of dicts keyed by ledger columns (missing keys -> empty)."""
import csv, json, sys, os
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title","source_issuer",
        "source_url_or_id","source_date","retrieved_date","locator","source_tier","primary","confidence",
        "corroborated_by","contradicted_by","formula_or_inputs","notes"]
LEDGER = os.environ.get("BEAR_LEDGER") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bear-case_ledger.csv")
rows = json.load(open(sys.argv[1]))
existing = set()
new = not os.path.exists(LEDGER)
if not new:
    with open(LEDGER, newline="") as f:
        existing = {r["claim_id"] for r in csv.DictReader(f)}
with open(LEDGER, "a", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    if new:
        w.writerow(COLS)
    for r in rows:
        if r["claim_id"] in existing:
            print("SKIP duplicate", r["claim_id"]); continue
        r.setdefault("author", "bear-case"); r.setdefault("retrieved_date", "2026-10-12")
        w.writerow([str(r.get(c, "")) for c in COLS])
        print("added", r["claim_id"])
