#!/usr/bin/env python3
"""Append claims to the filings ledger. Input: JSON lines on stdin, keys = ledger columns.
Defaults: author=filings, retrieved_date=2026-10-12. Every field is double-quoted."""
import csv, json, sys, os
COLS = ["claim_id","author","claim","tag","metric","value","unit","period","basis","source_title",
        "source_issuer","source_url_or_id","source_date","retrieved_date","locator","source_tier",
        "primary","confidence","corroborated_by","contradicted_by","formula_or_inputs","notes"]
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "specialists", "filings_ledger.csv")
path = os.path.normpath(path)
exists = os.path.exists(path)
existing = set()
if exists:
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            existing.add(r["claim_id"])
rows = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    d.setdefault("author", "filings")
    d.setdefault("retrieved_date", "2026-10-12")
    if d["claim_id"] in existing:
        sys.exit("duplicate claim id " + d["claim_id"])
    existing.add(d["claim_id"])
    tier = str(d.get("source_tier", ""))
    if "primary" not in d and tier:
        d["primary"] = "Y" if tier in "1234" and tier else "N"
    rows.append([str(d.get(c, "")) for c in COLS])
with open(path, "a", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    if not exists:
        w.writerow(COLS)
    w.writerows(rows)
print("appended", len(rows), "->", path, "total", len(existing))
