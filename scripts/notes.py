#!/usr/bin/env python3
"""The owner's primary research: expert calls, plant visits, channel checks, the owner's own diligence.

  python3 scripts/notes.py add RUN_DIR --what "Dealer call, Pune" --date 2026-10-30 --file note.md --attest "public or my own observation; no insider information"
  python3 scripts/notes.py list RUN_DIR

A note goes to corpus/owner_notes/<n>.md, where every specialist can read it and cite it as `owner-note:<n>`. It is the owner's
account: tier 7, to be corroborated, never a FACT by itself. Nothing enters without the attestation, because material
non-public information must not reach the research at all. The run records who attested what and when.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def notes_dir(run: Path) -> Path:
    return run / "corpus" / "owner_notes"


def add(run: Path, what: str, date: str, text: str, attest: str) -> Path:
    if len(attest.split()) < 4:
        raise SystemExit("say in words that this holds no material non-public information: nothing enters without it")
    dt.date.fromisoformat(date)
    d = notes_dir(run)
    d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob("*.md"))) + 1
    path = d / ("%03d.md" % n)
    path.write_text("# Owner note %03d: %s\n\nDate: %s\nCite as: owner-note:%03d (tier 7, the owner's account: corroborate it)\n"
                    "MNPI attestation: %s\nRecorded: %s\n\n%s\n" % (
                        n, what, date, n, attest, dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(), text), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("add")
    a_.add_argument("run_dir")
    a_.add_argument("--what", required=True)
    a_.add_argument("--date", required=True)
    a_.add_argument("--file", required=True)
    a_.add_argument("--attest", required=True)
    sub.add_parser("list").add_argument("run_dir")
    a = ap.parse_args(argv)
    run = Path(a.run_dir)
    if a.cmd == "add":
        print(add(run, a.what, a.date, Path(a.file).read_text(encoding="utf-8"), a.attest))
    else:
        for p in sorted(notes_dir(run).glob("*.md")) if notes_dir(run).exists() else []:
            print(p.read_text(encoding="utf-8").splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
