#!/usr/bin/env python3
"""Deterministic updates to RUN_DIR/run_manifest.json (CIO only).

  python3 scripts/manifest.py RUN_DIR show
  python3 scripts/manifest.py RUN_DIR set price.value=1234.5 "price.timestamp=2026-10-12 10:00 UTC (NSE quote)" model.effective_cio=claude-opus-5-5
  python3 scripts/manifest.py RUN_DIR status specialists_running
  python3 scripts/manifest.py RUN_DIR invocation financials --stage 1 --purpose "initial investigation"
  python3 scripts/manifest.py RUN_DIR invocation auditor --stage 4 --purpose "independent audit of the draft"
  python3 scripts/manifest.py RUN_DIR invocation reader --stage 0b --purpose "L007"
  python3 scripts/manifest.py RUN_DIR note "Transcript archive for FY2019-20 unavailable"
  python3 scripts/manifest.py RUN_DIR mode reading off --reason "reading 800+ chunks unaffordable on the current plan"

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
PROTECTED = {"run_id", "ticker", "started_at", "framework_commit", "methodology_version", "reading_mode"}


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
    inv.add_argument("specialist", choices=sorted(rl.AGENT_NAMES - {"cio"}))
    inv.add_argument("--stage", required=True)
    inv.add_argument("--purpose", required=True)
    n = sub.add_parser("note")
    n.add_argument("text")
    md = sub.add_parser("mode", help="switch the run's reading mode (refused once any specialist has been invoked)")
    md.add_argument("what", choices=["reading"])
    md.add_argument("value", choices=rl.READING_MODES)
    md.add_argument("--reason", required=True)
    a = p.parse_args(argv)

    path = Path(a.run_dir) / rl.RUN_MANIFEST
    if a.cmd == "show":
        print(json.dumps(rl.load_json(path), indent=2, ensure_ascii=False))
        return 0
    with rl.locked(path):
        return apply(a, p, path)


def apply(a, p, path: Path) -> int:
    m = rl.load_json(path)
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
        if a.specialist == rl.AUDITOR:
            node = m.setdefault("auditor", {"status": "pending", "report": rl.AUDIT_REPORT, "invocations": []})
        elif a.specialist in rl.WORKERS:
            node = m.setdefault("workers", {}).setdefault(a.specialist, {"invocations": []})
        elif a.specialist in rl.SYNTHESIS_ROLES:
            node = m.setdefault("synthesis", {}).setdefault(a.specialist, {"invocations": []})
        else:
            node = m["specialists"].setdefault(a.specialist, {"status": "pending", "invocations": []})
        node.setdefault("invocations", []).append({"stage": a.stage, "purpose": a.purpose, "at": now()})
    elif a.cmd == "note":
        m.setdefault("notes", []).append({"at": now(), "text": a.text})
    elif a.cmd == "mode":
        started = [n for n, s in (m.get("specialists") or {}).items() if (s or {}).get("invocations")]
        if started:
            p.error("specialists already ran (%s): their briefs named the %s-mode pack, so the reading mode can no longer "
                    "change; start a new run" % (", ".join(sorted(started)), m.get("reading_mode", "on")))
        old_mode = m.get("reading_mode", "on")
        m["reading_mode"] = a.value
        m.setdefault("notes", []).append({"at": now(), "text": "reading mode %s -> %s: %s" % (old_mode, a.value, a.reason)})
    rl.write_json(path, m)
    print("updated %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
