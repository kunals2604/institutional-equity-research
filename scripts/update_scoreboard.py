#!/usr/bin/env python3
"""Upsert a company's row in COMPANY_SCOREBOARD.csv from a QC-passed run (CIO only).

  python3 scripts/update_scoreboard.py RUN_DIR [--scoreboard PATH]

Refuses unless ALL hold:
  * RUN_DIR/qc/auto_checks.json exists with passed = true
  * cio/scorecard.json has qc_status = PASS
  * cio/qc_record.md contains the line 'QC status: PASS'
  * the run is not older than the run already on the scoreboard for that ticker

Also writes research/companies/<TICKER>/LATEST_RUN.txt.
"""

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

COLUMNS = [
    "ticker", "exchange", "company", "run_id", "research_cutoff", "price", "currency", "price_timestamp",
    "primary_layer", "secondary_layers", "l1_fit", "l2_fit", "l3_fit", "l4_fit",
    "business_quality", "bq_confidence", "investment_attractiveness", "ia_confidence",
    "verdict", "valuation_status", "expected_irr_5y", "methodology_version", "qc_status",
    "model_effective", "report_path", "updated_at",
]


def refuse(msg: str) -> int:
    print("REFUSED: " + msg, file=sys.stderr)
    return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir")
    p.add_argument("--scoreboard", default=str(rl.SCOREBOARD))
    a = p.parse_args(argv)
    run_dir = Path(a.run_dir).resolve()
    board = Path(a.scoreboard)

    auto = run_dir / "qc" / "auto_checks.json"
    if not auto.exists() or not rl.load_json(auto).get("passed"):
        return refuse("automated QC has not passed (run validate_run.py --stage final)")
    sc = rl.load_json(run_dir / "cio" / "scorecard.json")
    if sc.get("qc_status") != "PASS":
        return refuse("scorecard qc_status is %r" % sc.get("qc_status"))
    qc_text = (run_dir / "cio" / "qc_record.md").read_text(encoding="utf-8")
    if not re.search(r"^#*\s*QC status:\s*PASS\b", qc_text, re.M):
        return refuse("qc_record.md does not record 'QC status: PASS'")
    manifest = rl.load_json(run_dir / "manifest.json")

    rows = []
    if board.exists():
        header, rows = rl.read_csv(board)
        if header and header != COLUMNS:
            return refuse("scoreboard header differs from expected columns")
    existing = [r for r in rows if r["ticker"] == sc["ticker"] and r["exchange"] == sc.get("exchange", manifest["exchange"])]
    if existing and existing[0]["run_id"] > sc["run_id"]:
        return refuse("scoreboard already holds a newer run (%s)" % existing[0]["run_id"])

    try:
        report_path = str((run_dir / "cio" / "final_report.md").relative_to(rl.ROOT))
    except ValueError:
        report_path = str(run_dir / "cio" / "final_report.md")
    new = {
        "ticker": sc["ticker"],
        "exchange": sc.get("exchange", manifest["exchange"]),
        "company": sc.get("company", manifest["company"]),
        "run_id": sc["run_id"],
        "research_cutoff": sc.get("research_cutoff", manifest["research_cutoff"]),
        "price": sc["price"]["value"],
        "currency": sc.get("currency", manifest["currency"]),
        "price_timestamp": sc["price"]["timestamp"],
        "primary_layer": sc["primary_layer"],
        "secondary_layers": "; ".join(sc.get("secondary_layers") or []),
        "l1_fit": sc["layer_fit"]["L1"]["score"],
        "l2_fit": sc["layer_fit"]["L2"]["score"],
        "l3_fit": sc["layer_fit"]["L3"]["score"],
        "l4_fit": sc["layer_fit"]["L4"]["score"],
        "business_quality": sc["business_quality"]["final"],
        "bq_confidence": sc["business_quality"]["confidence"],
        "investment_attractiveness": sc["investment_attractiveness"]["final"],
        "ia_confidence": sc["investment_attractiveness"]["confidence"],
        "verdict": sc["verdict"],
        "valuation_status": sc["valuation_status"],
        "expected_irr_5y": sc.get("expected_irr_5y", ""),
        "methodology_version": manifest.get("methodology_version", rl.methodology_version()),
        "qc_status": sc["qc_status"],
        "model_effective": (sc.get("model") or {}).get("effective_cio", "unverified"),
        "report_path": report_path,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    rows = [r for r in rows if r not in existing] + [new]
    rows.sort(key=lambda r: (r["ticker"], r["exchange"]))
    with board.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    (run_dir.parent.parent / "LATEST_RUN.txt").write_text(sc["run_id"] + "\n", encoding="utf-8")
    print("Scoreboard updated: %s %s -> %s (BQ %s, IA %s)" % (new["ticker"], new["run_id"], new["verdict"],
                                                             new["business_quality"], new["investment_attractiveness"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
