#!/usr/bin/env python3
"""Merge every ledger in a run (specialists, follow-ups, CIO) into RUN_DIR/evidence_ledger.csv.

  python3 scripts/merge_ledgers.py RUN_DIR

Deterministic: files in sorted order (CIO last), rows in file order. Adds a
trailing 'ledger_file' column. Fails on duplicate claim IDs across ledgers.
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def merge(run_dir: Path) -> int:
    cols = rl.ledger_columns()
    seen = {}
    rows = []
    for lp in rl.run_ledger_paths(run_dir):
        header, data = rl.read_csv(lp)
        if header != cols:
            print("ERROR: %s has a non-canonical header" % lp, file=sys.stderr)
            return 1
        for r in data:
            cid = r["claim_id"]
            if cid in seen:
                print("ERROR: duplicate claim_id %s in %s and %s" % (cid, seen[cid], lp.name), file=sys.stderr)
                return 1
            seen[cid] = lp.name
            r["ledger_file"] = str(lp.relative_to(run_dir))
            rows.append(r)
    out = run_dir / "evidence_ledger.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols + ["ledger_file"], quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
    print("Merged %d claims from %d ledgers into %s" % (len(rows), len(rl.run_ledger_paths(run_dir)), out))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(merge(Path(sys.argv[1])))
