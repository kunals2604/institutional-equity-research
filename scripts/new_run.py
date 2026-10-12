#!/usr/bin/env python3
"""Create a new research run directory (UTC run ID) with run manifest and templates.

Usage (CIO, Stage 0):
  python3 scripts/new_run.py --ticker TVSMOTOR --company "TVS Motor Company Limited" \
      --exchange NSE --segment main --currency INR --fy-end 03-31 [--isin INE494B01023] \
      [--cutoff 2026-10-12] [--hurdle 0.12] [--reference-position 5000000] [--dry-run]

Prints the run directory path (relative to the repository root). Never
overwrites an existing run. --dry-run prints the paths and plan and writes nothing.
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

EXCHANGES = ("NSE", "BSE", "NSE-SME", "BSE-SME", "NYSE", "NASDAQ", "LSE")


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
    p.add_argument("--exchange", required=True, help="one of %s (others allowed with a warning)" % ", ".join(EXCHANGES))
    p.add_argument("--segment", choices=["main", "sme"], required=True)
    p.add_argument("--currency", default="INR")
    p.add_argument("--fy-end", default="03-31", help="MM-DD fiscal year end")
    p.add_argument("--isin", default="unknown")
    p.add_argument("--cutoff", default=None, help="YYYY-MM-DD (default: today, UTC)")
    p.add_argument("--hurdle", type=float, default=None, help="override the IPS hurdle rate")
    p.add_argument("--reference-position", type=float, default=None, help="override the IPS reference position")
    p.add_argument("--policy", default=str(rl.INVESTMENT_POLICY), help="investment policy JSON (IPS)")
    p.add_argument("--run-id", default=None, help="override (tests only); default UTC YYYYMMDDTHHMMSSZ")
    p.add_argument("--root", default=str(rl.ROOT), help="repository root (tests)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    policy = rl.investment_policy(Path(a.policy))
    hurdle = a.hurdle if a.hurdle is not None else float(policy["hurdle_rate"])
    ref_pos = a.reference_position if a.reference_position is not None else float(policy["reference_position"])
    ticker = a.ticker.strip().upper()
    company = a.company.strip()
    exchange = a.exchange.strip().upper()
    cutoff = a.cutoff or now.date().isoformat()
    if not re.fullmatch(r"[A-Z0-9&._-]{1,30}", ticker):
        p.error("ticker must be 1-30 chars of A-Z 0-9 & . _ -")
    if len(company) < 3:
        p.error("company name is required")
    if exchange not in EXCHANGES:
        print("WARNING: exchange %r not in %s" % (exchange, EXCHANGES), file=sys.stderr)
    if exchange.endswith("-SME") and a.segment != "sme":
        p.error("exchange %s implies --segment sme" % exchange)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cutoff):
        p.error("--cutoff must be YYYY-MM-DD")
    run_id = a.run_id or now.strftime("%Y%m%dT%H%M%SZ")
    if not rl.RUN_ID_RE.fullmatch(run_id):
        p.error("run id must look like 20261012T074500Z")
    root = Path(a.root)
    company_dir = root / "research" / "companies" / ticker
    run_dir = company_dir / "runs" / run_id
    rel = run_dir.relative_to(root)

    if a.dry_run:
        prior = sorted(d.name for d in (company_dir / "runs").glob("*") if d.is_dir()) if (company_dir / "runs").exists() else []
        print("DRY RUN: nothing written. No agents launched.")
        print("  run directory     : %s%s" % (rel, "  (EXISTS — would be refused)" if run_dir.exists() else ""))
        print("  prior runs        : %s" % (", ".join(prior) or "none"))
        latest = company_dir / rl.LATEST_POINTER
        print("  latest_run.txt    : %s" % (latest.read_text().strip() if latest.exists() else "none"))
        print("  manifest          : %s/%s" % (rel, rl.RUN_MANIFEST))
        for name in rl.SPECIALISTS:
            print("  specialist report : %s/specialists/%s.md  (+ %s_ledger.csv)" % (rel, name, name))
        for f in ("cio/final_report.md", "cio/scorecard.json", rl.QC_RECORD, "evidence_ledger.csv"):
            print("  CIO artifact      : %s/%s" % (rel, f))
        print("  stages            : 0 preflight -> 1 nine parallel specialists -> 2 barrier (+git batch 1)"
              " -> 3 CIO adjudication -> 4 QC, finalize, git batch 2 + push")
        return 0

    if run_dir.exists():
        print("ERROR: run directory already exists: %s" % run_dir, file=sys.stderr)
        return 1
    for sub in ("specialists", "cio", "calc", "qc"):
        (run_dir / sub).mkdir(parents=True)

    # Specialists create their own ledgers; the CIO ledger starts with the canonical header.
    with (run_dir / "cio" / "cio_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerow(rl.ledger_columns())

    tpl = rl.ROOT / "templates"
    fields = {
        "company": company, "ticker": ticker, "run_id": run_id, "created_at": now.isoformat(),
        "cutoff": cutoff, "exchange": exchange, "segment": a.segment, "isin": a.isin,
        "currency": a.currency, "fy_end": a.fy_end, "sme_mode": "ON" if a.segment == "sme" else "OFF",
        "hurdle": hurdle, "reference_position": int(ref_pos),
        "benchmark": policy.get("benchmark", ""), "horizon": policy.get("investment_horizon_years", 5),
        "ips_status": "CONFIRMED by user" if policy.get("confirmed_by_user") else "PLACEHOLDER values (not yet confirmed by user)",
    }
    for src, dst in (("research_brief.md", "research_brief.md"),
                     ("contradiction_log.md", "cio/contradiction_log.md"),
                     ("quality_control.md", rl.QC_RECORD)):
        (run_dir / dst).write_text((tpl / src).read_text(encoding="utf-8").format(**fields), encoding="utf-8")
    (run_dir / "source_register.csv").write_text((tpl / "source_register_header.csv").read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "ticker": ticker,
        "company": company,
        "exchange": exchange,
        "listing_segment": a.segment,
        "isin": a.isin,
        "currency": a.currency,
        "fiscal_year_end": a.fy_end,
        "research_cutoff": cutoff,
        "started_at": now.isoformat(),
        "completed_at": None,
        "status": "preflight",
        "assessment_status": None,
        "price": {"value": None, "timestamp": None, "claim_id": "CIO-C001"},
        "hurdle_rate": hurdle,
        "reference_position": ref_pos,
        "investment_policy": policy,
        "ips_confirmed": bool(policy.get("confirmed_by_user")),
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
    rl.write_json(run_dir / rl.RUN_MANIFEST, manifest)
    print(rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
