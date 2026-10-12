#!/usr/bin/env python3
"""Validate one or more evidence-ledger CSVs against methodology/EVIDENCE_STANDARDS.md.

  python3 scripts/validate_ledger.py RUN_DIR/specialists/financials_ledger.csv [more.csv ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def main(argv=None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    if not paths:
        print(__doc__)
        return 2
    ok = True
    for p in paths:
        path = Path(p)
        res, ids = rl.validate_ledger(path, rl.prefix_for_ledger(path))
        print(res.render() + "\n  claims: %d" % len(ids))
        ok = ok and res.ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
