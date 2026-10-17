"""Append ledger rows (JSON lines on stdin) to specialists/special-situations_ledger.csv, all fields quoted.
Each JSON object uses ledger column names; author/retrieved_date/primary defaulted."""
import csv, json, sys, os
R = "research/companies/BHARTIARTL/runs/20261012T132311Z"
P = os.path.join(R, "specialists", "special-situations_ledger.csv")
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title","source_issuer",
        "source_url_or_id","source_date","retrieved_date","locator","source_tier","primary","confidence",
        "corroborated_by","contradicted_by","formula_or_inputs","notes"]
exists = os.path.exists(P)
existing = set()
if exists:
    with open(P, newline="", encoding="utf-8") as f:
        existing = {r["claim_id"] for r in csv.DictReader(f)}
n = 0
with open(P, "a", newline="", encoding="utf-8") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    if not exists:
        w.writerow(COLS)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        d.setdefault("author", "special-situations")
        d.setdefault("retrieved_date", "2026-10-12")
        t = str(d.get("source_tier", ""))
        d.setdefault("primary", "Y" if t in ("1","2","3","4") else "N")
        if d["claim_id"] in existing:
            print("SKIP duplicate", d["claim_id"]); continue
        w.writerow([str(d.get(c, "")) for c in COLS]); existing.add(d["claim_id"]); n += 1
print("appended", n, "total", len(existing))
