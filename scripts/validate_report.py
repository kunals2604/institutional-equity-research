#!/usr/bin/env python3
"""Validate a specialist or CIO final report against the report contracts.

  python3 scripts/validate_report.py RUN_DIR/specialists/moat.md --kind specialist --ledger RUN_DIR/specialists/moat_ledger.csv
  python3 scripts/validate_report.py RUN_DIR/cio/final_report.md --kind final --scorecard RUN_DIR/cio/scorecard.json --run RUN_DIR
  python3 scripts/validate_report.py some_report.md --kind any      # layer-name / phrase / tag checks only

Exit code 0 = no errors (warnings allowed), 1 = errors.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("report")
    p.add_argument("--kind", choices=["specialist", "followup", "final", "any"], required=True)
    p.add_argument("--ledger", help="ledger CSV whose claim IDs the report may cite")
    p.add_argument("--run", help="run directory (final: all run ledgers are loaded)")
    p.add_argument("--scorecard")
    a = p.parse_args(argv)
    path = Path(a.report)

    ids = None
    if a.run:
        ids = set()
        for lp in rl.run_ledger_paths(Path(a.run)):
            ids |= rl.validate_ledger(lp)[1]
    if a.ledger:
        lres, lids = rl.validate_ledger(Path(a.ledger))
        ids = (ids or set()) | lids
        print(lres.render())

    if a.kind in ("specialist", "followup"):
        res = rl.validate_specialist_report(path, ids, followup=(a.kind == "followup"))
    elif a.kind == "final":
        sc = rl.load_json(Path(a.scorecard)) if a.scorecard else None
        res = rl.validate_final_report(path, sc, ids)
    else:
        res = rl.Result(str(path))
        text = path.read_text(encoding="utf-8")
        rl.check_layer_names(text, res)
        rl.check_flagged_phrases(text, res, strict=False)
        rl.check_tags(text, res, None)
    print(res.render())
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
