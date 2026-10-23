#!/usr/bin/env python3
"""Apply the incomplete-run policy (methodology/SCORING.md §8) and finalize a run (CIO only).

  python3 scripts/finalize_run.py RUN_DIR [--scoreboard PATH]

Outcome:
  complete               automated QC passed, scorecard qc_status PASS, quality_control.md
                         records 'QC status: PASS', assessment_status complete
                         -> upsert scoreboard (locked), update latest_run.txt, manifest status complete
  insufficient_evidence  scorecard assessment_status insufficient_evidence
                         -> manifest only; scoreboard and pointer untouched
  qc_failed              final report exists but QC did not pass
                         -> manifest only; scoreboard and pointer untouched
  failed                 no final report
                         -> manifest only

Exit: 0 complete, 3 non-complete outcome recorded, 1 error.
"""

import argparse
import datetime as dt
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import scoreboard as sb  # noqa: E402


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def decide(run_dir: Path):
    auto = run_dir / "qc" / "auto_checks.json"
    auto_ok = auto.exists() and rl.load_json(auto).get("passed") is True
    sc_path = run_dir / "cio" / "scorecard.json"
    sc = rl.load_json(sc_path) if sc_path.exists() else None
    qc_path = run_dir / rl.QC_RECORD
    qc_ok = qc_path.exists() and re.search(r"^#*\s*QC status:\s*PASS\b", qc_path.read_text(encoding="utf-8"), re.M)
    if not (run_dir / "cio" / "final_report.md").exists() or sc is None:
        return "failed", sc, "no final report / scorecard"
    if sc.get("assessment_status") == "insufficient_evidence":
        return "insufficient_evidence", sc, sc.get("insufficient_evidence_reason") or "insufficient evidence"
    reasons = []
    if not auto_ok:
        reasons.append("automated QC not passed (run validate_run.py --stage final)")
    if sc.get("qc_status") != "PASS":
        reasons.append("scorecard qc_status=%r" % sc.get("qc_status"))
    if not qc_ok:
        reasons.append("quality_control.md lacks 'QC status: PASS'")
    if reasons:
        return "qc_failed", sc, "; ".join(reasons)
    return "complete", sc, "all QC gates passed"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir")
    p.add_argument("--scoreboard", default=str(rl.SCOREBOARD))
    a = p.parse_args(argv)
    run_dir = Path(a.run_dir).resolve()
    mpath = run_dir / rl.RUN_MANIFEST
    manifest = rl.load_json(mpath)
    outcome, sc, reason = decide(run_dir)

    if outcome == "complete":
        if sc["run_id"] != manifest["run_id"] or sc["ticker"] != manifest["ticker"]:
            print("ERROR: scorecard identity does not match manifest", file=sys.stderr)
            return 1
        row = {
            "company": manifest["company"], "ticker": manifest["ticker"], "exchange": manifest["exchange"],
            "assessment_date": sc.get("as_of_date") or manifest["research_cutoff"],
            "latest_run_id": manifest["run_id"],
            "price": sc["price"]["value"], "currency": sc.get("currency") or manifest["currency"],
            "price_timestamp": sc["price"]["timestamp"],
            "methodology_version": manifest.get("methodology_version", rl.methodology_version()),
            "business_quality_score": sc["business_quality"]["final"],
            "investment_attractiveness_score": sc["investment_attractiveness"]["final"],
        }
        board = Path(a.scoreboard)
        sb.write_header_if_missing(board)
        try:
            sb.upsert(board, row)
        except sb.ScoreboardError as exc:
            print("ERROR: scoreboard not updated: %s" % exc, file=sys.stderr)
            return 1
        pointer = run_dir.parent.parent / rl.LATEST_POINTER
        current = pointer.read_text().strip() if pointer.exists() else ""
        if manifest["run_id"] >= current:
            atomic_write(pointer, manifest["run_id"] + "\n")
        import outcomes                       # the decision and its predictions, for the outcome loop
        dec, preds = outcomes.record_decision(run_dir)
        print("outcomes: decision %s recorded with %d prediction(s) (research/outcomes/)" % (dec.get("verdict"), len(preds)))

    manifest["status"] = outcome
    manifest["assessment_status"] = (sc or {}).get("assessment_status")
    manifest["completed_at"] = utcnow()
    manifest.setdefault("status_history", []).append({"status": outcome, "at": manifest["completed_at"], "reason": reason})
    rl.write_json(mpath, manifest)
    print("OUTCOME: %s (%s)" % (outcome, reason))
    if outcome != "complete":
        print("Scoreboard and latest_run.txt were NOT changed.")
    return 0 if outcome == "complete" else 3


if __name__ == "__main__":
    sys.exit(main())
