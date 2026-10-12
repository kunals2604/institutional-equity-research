#!/usr/bin/env python3
"""Deterministic updates to RUN_DIR/run_manifest.json (CIO only).

  python3 scripts/manifest.py RUN_DIR show
  python3 scripts/manifest.py RUN_DIR set price.value=1234.5 "price.timestamp=2026-10-12 10:00 UTC (NSE quote)" model.effective_cio=claude-opus-5-5
  python3 scripts/manifest.py RUN_DIR status specialists_running
  python3 scripts/manifest.py RUN_DIR invocation financials --stage 1 --purpose "initial investigation"
  python3 scripts/manifest.py RUN_DIR note "Transcript archive for FY2019-20 unavailable"

Values are parsed as JSON when possible (numbers, null, true), otherwise kept as strings.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

STATUSES = ("preflight", "specialists_running", "specialists_complete", "specialists_incomplete",
            "synthesis", "qc_auto_passed", "qc_auto_failed", "complete", "insufficient_evidence",
            "qc_failed", "failed", "interrupted")
PROTECTED = {"run_id", "ticker", "started_at", "framework_commit", "methodology_version"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_value(v: str):
    try:
        return json.loads(v)
    except ValueError:
        return v


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    s = sub.add_parser("set")
    s.add_argument("pairs", nargs="+", help="dotted.key=value")
    st = sub.add_parser("status")
    st.add_argument("value", choices=STATUSES)
    inv = sub.add_parser("invocation")
    inv.add_argument("specialist", choices=list(rl.SPECIALISTS))
    inv.add_argument("--stage", required=True)
    inv.add_argument("--purpose", required=True)
    n = sub.add_parser("note")
    n.add_argument("text")
    a = p.parse_args(argv)

    path = Path(a.run_dir) / rl.RUN_MANIFEST
    m = rl.load_json(path)
    if a.cmd == "show":
        print(json.dumps(m, indent=2, ensure_ascii=False))
        return 0
    if a.cmd == "set":
        for pair in a.pairs:
            if "=" not in pair:
                p.error("expected key=value, got %r" % pair)
            key, val = pair.split("=", 1)
            parts = key.split(".")
            if parts[0] in PROTECTED:
                p.error("%s is set at run creation and cannot be changed" % parts[0])
            if parts[0] == "status":
                p.error("use the 'status' subcommand")
            node = m
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = parse_value(val)
    elif a.cmd == "status":
        m["status"] = a.value
        m.setdefault("status_history", []).append({"status": a.value, "at": now()})
    elif a.cmd == "invocation":
        m["specialists"][a.specialist]["invocations"].append({"stage": a.stage, "purpose": a.purpose, "at": now()})
    elif a.cmd == "note":
        m.setdefault("notes", []).append({"at": now(), "text": a.text})
    rl.write_json(path, m)
    print("updated %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
