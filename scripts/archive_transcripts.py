#!/usr/bin/env python3
"""Keep a run's agent transcripts beyond Claude Code's retention period.

  python3 scripts/archive_transcripts.py archive RUN_DIR [RUN_DIR ...]
  python3 scripts/archive_transcripts.py verify

Verification and the reading audit read the agents' transcripts. Claude Code deletes those silently after its
`cleanupPeriodDays` (30 by default), which would leave a finished run impossible to audit. This copies every session of
a run (main sessions, subagents with their metadata, the engine's headless sessions) to
research/_archive/transcripts/, keeping each file's path relative to the transcripts folder, and records a SHA-256 for
each in MANIFEST.csv. `reading_audit` looks there whenever a live file is gone; a live file is always preferred.

Transcripts are local records: the archive is gitignored, and agents may not read it (agent_driver.DENY_TRANSCRIPTS).
Archiving is safe to repeat: a session that grew is copied again, and nothing is ever deleted.
"""

import argparse
import csv
import datetime as dt
import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402

MANIFEST = "MANIFEST.csv"
FIELDS = ["path", "sha256", "bytes", "run_id", "archived_at"]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest(archive: Path) -> Dict[str, dict]:
    path = archive / MANIFEST
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["path"]: r for r in csv.DictReader(f)}


def write_manifest(archive: Path, rows: Dict[str, dict]) -> None:
    tmp = archive / (MANIFEST + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for key in sorted(rows):
            w.writerow(rows[key])
    os.replace(str(tmp), str(archive / MANIFEST))


def session_files(run_dir: Path, tdir: Path, run_id: str) -> Iterable[Path]:
    """Every transcript of the run, and the metadata file beside each subagent's."""
    for a in ra.find_agents(tdir, run_id):
        yield a["path"]
        meta = a["path"].with_name(a["path"].name.replace(".jsonl", ".meta.json"))
        if meta.exists():
            yield meta
    for path in ra.find_main_sessions(tdir, run_id):
        yield path
    for h in ra.headless_sessions(run_dir, tdir):
        yield h["path"]


def copy_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copy2(str(src), str(tmp))
    os.replace(str(tmp), str(dst))


def archive_run(run_dir: Path, tdir: Path = None) -> Tuple[int, int, int]:
    """(files in the run, files copied, bytes copied). A session several runs share keeps every run id on its row."""
    tdir = tdir or ra.transcripts_dir()
    run_id = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name)
    archive = ra.archive_dir()
    archive.mkdir(parents=True, exist_ok=True)
    rows = load_manifest(archive)
    total = copied = size = 0
    for src in sorted(set(session_files(run_dir, tdir, run_id))):
        if archive in src.parents:      # the live file is gone: the archived copy is already the record
            rel = str(src.relative_to(archive))
            digest, length = rows[rel]["sha256"], int(rows[rel]["bytes"])
        else:
            rel = str(src.relative_to(tdir))
            digest, length = sha256(src), src.stat().st_size
            if rel not in rows or rows[rel]["sha256"] != digest or not (archive / rel).exists():
                copy_atomic(src, archive / rel)
                copied += 1
                size += length
        total += 1
        runs = set((rows.get(rel, {}).get("run_id") or "").split(";")) - {""}
        rows[rel] = {"path": rel, "sha256": digest, "bytes": length, "run_id": ";".join(sorted(runs | {run_id})),
                     "archived_at": now()}
    write_manifest(archive, rows)
    return total, copied, size


def verify_archive() -> List[str]:
    """Each archived file that is missing or no longer matches its recorded checksum."""
    archive = ra.archive_dir()
    problems = []
    for rel, row in load_manifest(archive).items():
        path = archive / rel
        if not path.exists():
            problems.append("%s: missing from the archive" % rel)
        elif sha256(path) != row["sha256"]:
            problems.append("%s: does not match its recorded checksum" % rel)
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("archive")
    a.add_argument("run_dir", nargs="+")
    sub.add_parser("verify")
    args = ap.parse_args(argv)
    if args.cmd == "verify":
        problems = verify_archive()
        print("\n".join(problems) if problems else "archive verified: %d files" % len(load_manifest(ra.archive_dir())))
        return 1 if problems else 0
    for d in args.run_dir:
        run_dir = Path(d)
        total, copied, size = archive_run(run_dir)
        print("%s: %d transcript files, %d copied (%.1f MB) -> %s" % (run_dir.name, total, copied, size / 1e6, ra.archive_dir()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
