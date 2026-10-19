#!/usr/bin/env python3
"""Validate a specialist, CIO final or audit report against the report contracts.

  python3 scripts/validate_report.py RUN_DIR/specialists/moat.md --kind specialist --ledger RUN_DIR/specialists/moat_ledger.csv
  python3 scripts/validate_report.py RUN_DIR/cio/final_report.md --kind final --scorecard RUN_DIR/cio/scorecard.json --run RUN_DIR
  python3 scripts/validate_report.py RUN_DIR/audit/audit_report.md --kind audit --run RUN_DIR
  python3 scripts/validate_report.py some_report.md --kind any      # layer-name / phrase / tag checks only

The run's contract (methodology version and listing segment) is read from run_manifest.json: from --run, or from
the report's location inside a run directory. A report outside a run is checked against the current contract.

Exit code 0 = no errors (warnings allowed), 1 = errors.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def run_context(report: Path, run: str):
    """(run_dir or None, version tuple, segment) for the report."""
    candidates = [Path(run)] if run else [report.resolve().parent.parent, report.resolve().parent]
    for d in candidates:
        mpath = d / rl.RUN_MANIFEST
        if mpath.exists():
            m = rl.load_json(mpath)
            return d, rl.version_tuple(m.get("methodology_version")), str(m.get("listing_segment") or "")
    return None, rl.current_version(), ""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("report")
    p.add_argument("--kind", choices=["specialist", "followup", "final", "audit", "any"], required=True)
    p.add_argument("--ledger", help="ledger CSV whose claim IDs the report may cite")
    p.add_argument("--run", help="run directory (final / audit: all run ledgers are loaded)")
    p.add_argument("--scorecard")
    a = p.parse_args(argv)
    path = Path(a.report)
    run_dir, version, segment = run_context(path, a.run)

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
        res = rl.validate_specialist_report(path, ids, followup=(a.kind == "followup"), version=version, segment=segment)
    elif a.kind == "final":
        sc = rl.load_json(Path(a.scorecard)) if a.scorecard else None
        res = rl.validate_final_report(path, sc, ids, version=version, segment=segment)
    elif a.kind == "audit":
        res, findings = rl.validate_audit_report(path, ids, version=version)
        n = {s: sum(1 for _, x in findings if x == s) for s in rl.AUDIT_SEVERITIES}
        print("findings: %s" % ", ".join("%s %d" % kv for kv in n.items()))
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
