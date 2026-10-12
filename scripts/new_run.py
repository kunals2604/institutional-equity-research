#!/usr/bin/env python3
"""Create a new timestamped research run directory with manifest and templates.

Usage (CIO, Stage 0):
  python3 scripts/new_run.py --ticker TVSMOTOR --company "TVS Motor Company Ltd" \
      --exchange NSE --segment main --currency INR --fy-end 03-31 [--isin INE494B01023] \
      [--cutoff 2026-10-12] [--hurdle 0.12] [--reference-position 5000000]

Prints the run directory path. Never overwrites an existing run.
"""

import argparse
import csv
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def git_head(root: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--",
                                ".claude", "methodology", "scripts", "MASTER_RESEARCH_FRAMEWORK.md",
                                "PROJECT_INSTRUCTIONS.md"],
                               capture_output=True, text=True, check=True).stdout.strip()
        return out.stdout.strip() + ("+uncommitted-method-changes" if dirty else "")
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ticker", required=True)
    p.add_argument("--company", required=True)
    p.add_argument("--exchange", required=True)
    p.add_argument("--segment", choices=["main", "sme"], required=True)
    p.add_argument("--currency", default="INR")
    p.add_argument("--fy-end", default="03-31", help="MM-DD fiscal year end")
    p.add_argument("--isin", default="unknown")
    p.add_argument("--cutoff", default=dt.date.today().isoformat())
    p.add_argument("--hurdle", type=float, default=0.12)
    p.add_argument("--reference-position", type=float, default=5_000_000)
    p.add_argument("--run-id", default=None, help="override (tests); default YYYYMMDD-HHMM")
    p.add_argument("--root", default=str(rl.ROOT), help="repository root (tests)")
    a = p.parse_args(argv)

    ticker = a.ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9&._-]{1,30}", ticker):
        p.error("ticker must be 1-30 chars of A-Z 0-9 & . _ -")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.cutoff):
        p.error("--cutoff must be YYYY-MM-DD")
    now = dt.datetime.now()
    run_id = a.run_id or now.strftime("%Y%m%d-%H%M")
    root = Path(a.root)
    run_dir = root / "research" / "companies" / ticker / "runs" / run_id
    if run_dir.exists():
        print("ERROR: run directory already exists: %s" % run_dir, file=sys.stderr)
        return 1

    for sub in ("specialists", "cio", "calc", "qc"):
        (run_dir / sub).mkdir(parents=True, exist_ok=False if sub == "specialists" else True)

    # Specialists create their own ledgers; the CIO ledger starts with the canonical header.
    cols = rl.ledger_columns()
    with (run_dir / "cio" / "cio_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerow(cols)

    tpl = rl.ROOT / "templates"
    fields = {
        "company": a.company, "ticker": ticker, "run_id": run_id, "created_at": now.isoformat(timespec="minutes"),
        "cutoff": a.cutoff, "exchange": a.exchange, "segment": a.segment, "isin": a.isin,
        "currency": a.currency, "fy_end": a.fy_end, "sme_mode": "ON" if a.segment == "sme" else "OFF",
        "hurdle": a.hurdle, "reference_position": int(a.reference_position),
    }
    (run_dir / "research_brief.md").write_text((tpl / "research_brief.md").read_text(encoding="utf-8").format(**fields), encoding="utf-8")
    (run_dir / "cio" / "contradiction_log.md").write_text((tpl / "contradiction_log.md").read_text(encoding="utf-8").format(**fields), encoding="utf-8")
    (run_dir / "cio" / "qc_record.md").write_text((tpl / "qc_record.md").read_text(encoding="utf-8").format(**fields), encoding="utf-8")
    (run_dir / "source_register.csv").write_text((tpl / "source_register_header.csv").read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "ticker": ticker,
        "company": a.company,
        "exchange": a.exchange,
        "listing_segment": a.segment,
        "isin": a.isin,
        "currency": a.currency,
        "fiscal_year_end": a.fy_end,
        "research_cutoff": a.cutoff,
        "created_at": now.isoformat(timespec="seconds"),
        "status": "preflight",
        "hurdle_rate": a.hurdle,
        "reference_position": a.reference_position,
        "framework_commit": git_head(root),
        "methodology_version": rl.methodology_version(),
        "model": {"requested": "opus", "effective_cio": "unverified",
                  "subagents": "opus alias (frontmatter); per-subagent ID not exposed"},
        "specialists": {
            name: {"status": "pending",
                   "report": "specialists/%s.md" % name,
                   "ledger": "specialists/%s_ledger.csv" % name,
                   "invocations": []}
            for name in rl.SPECIALISTS
        },
        "notes": [],
    }
    rl.write_json(run_dir / "manifest.json", manifest)
    print(run_dir.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
