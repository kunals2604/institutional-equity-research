#!/usr/bin/env python3
"""COMPANY_SCOREBOARD.csv: compact screening index, one row per company.

Schema is deliberately minimal: identification + the run metadata needed to
interpret the two scores + the two scores. No commentary, layers or verdicts
(those live in the run directory referenced by latest_run_id).

Writes are serialized with an exclusive file lock, re-read inside the lock,
written to a temp file, fsynced, atomically replaced, then re-verified.

  python3 scripts/scoreboard.py validate [--scoreboard PATH] [--check-runs]

Rows are written only by scripts/finalize_run.py (CIO).
"""

import argparse
import csv
import fcntl
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

COLUMNS = [
    "company", "ticker", "exchange", "assessment_date", "latest_run_id",
    "price", "currency", "price_timestamp", "methodology_version",
    "business_quality_score", "investment_attractiveness_score",
]


class ScoreboardError(Exception):
    pass


@contextmanager
def locked(board: Path):
    lock_path = board.with_name(board.name + ".lock")
    with open(lock_path, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def read_rows(board: Path) -> List[Dict[str, str]]:
    if not board.exists() or board.stat().st_size == 0:
        return []
    header, rows = rl.read_csv(board)
    if header != COLUMNS:
        raise ScoreboardError("scoreboard header %s != expected %s" % (header, COLUMNS))
    return rows


def validate_rows(rows: List[Dict[str, str]]) -> List[str]:
    errors, seen = [], set()
    for i, r in enumerate(rows, 2):
        key = (r.get("ticker"), r.get("exchange"))
        if key in seen:
            errors.append("row %d: duplicate company %s/%s" % (i, key[0], key[1]))
        seen.add(key)
        for col in COLUMNS:
            if not (r.get(col) or "").strip():
                errors.append("row %d: empty %s" % (i, col))
        for col in ("business_quality_score", "investment_attractiveness_score"):
            v = (r.get(col) or "").strip()
            if not re.fullmatch(r"\d{1,3}", v) or not 0 <= int(v) <= 100:
                errors.append("row %d: %s must be an integer 0-100 (got %r)" % (i, col, v))
        if not rl.RUN_ID_RE.fullmatch((r.get("latest_run_id") or "").strip()):
            errors.append("row %d: latest_run_id %r is not a UTC run id" % (i, r.get("latest_run_id")))
        for col in ("company", "price_timestamp"):
            if len(r.get(col) or "") > 120:
                errors.append("row %d: %s too long; the scoreboard is not for commentary" % (i, col))
    return errors


def write_header_if_missing(board: Path) -> None:
    if not board.exists():
        with board.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUMNS)


def upsert(board: Path, row: Dict[str, str]) -> None:
    """Insert or replace the row for (ticker, exchange). Refuses to replace a newer run."""
    missing = [c for c in COLUMNS if str(row.get(c, "")).strip() == ""]
    if missing:
        raise ScoreboardError("new row missing %s" % missing)
    with locked(board):
        rows = read_rows(board)
        errs = validate_rows(rows)
        if errs:
            raise ScoreboardError("existing scoreboard invalid; fix before writing: %s" % errs)
        key = (row["ticker"], row["exchange"])
        for r in rows:
            if (r["ticker"], r["exchange"]) == key and r["latest_run_id"] > row["latest_run_id"]:
                raise ScoreboardError("scoreboard already holds newer run %s for %s" % (r["latest_run_id"], key[0]))
        rows = [r for r in rows if (r["ticker"], r["exchange"]) != key] + [{c: str(row[c]) for c in COLUMNS}]
        rows.sort(key=lambda r: (r["ticker"], r["exchange"]))
        errs = validate_rows(rows)
        if errs:
            raise ScoreboardError("refusing to write invalid scoreboard: %s" % errs)
        fd, tmp = tempfile.mkstemp(dir=str(board.parent), prefix=".scoreboard-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=COLUMNS)
                w.writeheader()
                w.writerows(rows)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, board)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        after = read_rows(board)
        if len(after) != len(rows) or not any((r["ticker"], r["exchange"], r["latest_run_id"]) ==
                                              (row["ticker"], row["exchange"], row["latest_run_id"]) for r in after):
            raise ScoreboardError("post-write verification failed")


def validate_file(board: Path, check_runs: bool = False) -> List[str]:
    try:
        rows = read_rows(board)
    except ScoreboardError as exc:
        return [str(exc)]
    errors = validate_rows(rows)
    if check_runs:
        for r in rows:
            run_dir = rl.ROOT / "research" / "companies" / r["ticker"] / "runs" / r["latest_run_id"]
            sc = run_dir / "cio" / "scorecard.json"
            if not sc.exists():
                errors.append("%s: run %s has no scorecard" % (r["ticker"], r["latest_run_id"]))
                continue
            d = rl.load_json(sc)
            if d.get("qc_status") != "PASS" or d.get("assessment_status") != "complete":
                errors.append("%s: run %s is not a complete QC-passed run" % (r["ticker"], r["latest_run_id"]))
            if str(d["business_quality"]["final"]) != r["business_quality_score"] or \
                    str(d["investment_attractiveness"]["final"]) != r["investment_attractiveness_score"]:
                errors.append("%s: scores differ from run scorecard" % r["ticker"])
    return errors


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["validate"])
    p.add_argument("--scoreboard", default=str(rl.SCOREBOARD))
    p.add_argument("--check-runs", action="store_true")
    a = p.parse_args(argv)
    errs = validate_file(Path(a.scoreboard), a.check_runs)
    for e in errs:
        print("ERROR: " + e)
    print("scoreboard %s" % ("PASS" if not errs else "FAIL"))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
