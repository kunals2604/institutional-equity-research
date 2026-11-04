#!/usr/bin/env python3
"""The release gate for methodology 4.0.0: what must hold before the version is tagged and the first live run starts.

  python3 scripts/release_gate.py check [--skip-tests]
  python3 scripts/release_gate.py confirm-labels --by "<owner's name>"     # the owner, after reviewing the labels

Scripts only, as the owner decided: no agent runs here. It never tags and never pushes: tagging `v4.0.0` is the owner's
step once every line passes. What it checks:
- the methodology marker reads 4.0.0, and no switch is listed as not yet wired;
- `validate_system.py` passes, and so does the whole test suite (the golden replay of the Bharti run, the mutation
  suite, fault injection and every contract test among it); the mutation suite catches at least 95 % of planted errors;
- the gating labels (`tests/golden/gating_labels.csv`) are confirmed by the owner, on the file as it stands now;
- no item in `docs/V4_DEFECT_REGISTER.md` is marked "Open, release item";
- the framework's files are committed (a release is a commit, not a working tree).
Items the register marks open for a reason other than the release (the US path, unproven until a US run) are listed,
not counted against it.
"""

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

ROOT = rl.ROOT
LABELS = ROOT / "tests" / "golden" / "gating_labels.csv"
CONFIRMATION = ROOT / "tests" / "golden" / "gating_labels.confirmed.json"
REGISTER = ROOT / "docs" / "V4_DEFECT_REGISTER.md"
FRAMEWORK_PATHS = (".claude", "methodology", "scripts", "config", "templates", "tests", "docs", "CLAUDE.md", "README.md",
                   "MASTER_RESEARCH_FRAMEWORK.md", "PROJECT_INSTRUCTIONS.md")
MUTATION_FLOOR = 0.95


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def labels_confirmed() -> Tuple[bool, str]:
    if not CONFIRMATION.exists():
        return False, "not confirmed: the owner reviews tests/golden/gating_labels.csv, then runs release_gate.py confirm-labels"
    rec = json.loads(CONFIRMATION.read_text(encoding="utf-8"))
    if rec.get("sha256") != sha(LABELS):
        return False, "confirmed on %s by %s, but the labels have changed since: confirm them again" % (rec.get("at"), rec.get("by"))
    return True, "confirmed on %s by %s" % (rec.get("at"), rec.get("by"))


def open_items() -> Tuple[List[str], List[str]]:
    """(items blocking the release, items open for another reason)."""
    blocking, other = [], []
    for line in REGISTER.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(O\d+|[A-Z]\d+)\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        status = cells[-1]
        if "Open, release item" in status:
            blocking.append("%s: %s" % (m.group(1), cells[2]))
        elif status.startswith("Open"):
            other.append("%s: %s (%s)" % (m.group(1), cells[2], status))
    return blocking, other


def mutation_rate(test_output: str) -> Tuple[int, int]:
    m = re.search(r"mutation suite: (\d+) of (\d+) planted errors caught", test_output)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def uncommitted() -> List[str]:
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--"] + list(FRAMEWORK_PATHS),
                       capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l.strip()]


def check(skip_tests: bool = False, run=subprocess.run) -> List[Tuple[str, bool, str]]:
    import switches
    out = []
    version = rl.methodology_version()
    out.append(("methodology marker is 4.0.0", version == "4.0.0", version))
    nyw = switches.registry().get("not_yet_wired") or {}
    out.append(("no switch is listed as not yet wired", not nyw, ", ".join(nyw) or "none"))
    r = run([sys.executable, str(ROOT / "scripts" / "validate_system.py")], capture_output=True, text=True, cwd=str(ROOT))
    tail = (r.stdout.strip().splitlines() or [""])[-2:]
    out.append(("validate_system.py passes", r.returncode == 0, " ".join(tail)[:200]))
    if skip_tests:
        out.append(("the test suite passes", False, "skipped (--skip-tests): the gate cannot pass without it"))
    else:
        r = run([sys.executable, "-m", "unittest", "discover", "tests"], capture_output=True, text=True, cwd=str(ROOT))
        text = r.stdout + r.stderr
        ran = re.search(r"Ran (\d+) tests", text)
        out.append(("the test suite passes (golden replay, mutation, fault injection, contracts)", r.returncode == 0,
                    "%s tests%s" % (ran.group(1) if ran else "?", "" if r.returncode == 0 else ": " + "; ".join(
                        l for l in text.splitlines() if l.startswith(("FAIL:", "ERROR:")))[:300])))
        caught, planted = mutation_rate(text)
        out.append(("the mutation suite catches at least %d %% of planted errors" % (MUTATION_FLOOR * 100),
                    planted > 0 and caught / planted >= MUTATION_FLOOR, "%d of %d" % (caught, planted)))
    ok, why = labels_confirmed()
    out.append(("the owner has confirmed the gating labels", ok, why))
    blocking, other = open_items()
    out.append(("no item of the defect register is open for the release", not blocking, "; ".join(blocking) or "none"))
    dirty = uncommitted()
    out.append(("the framework's files are committed", not dirty, "; ".join(dirty[:5]) or "clean"))
    out.append(("(listed, not counted) open for another reason", True, "; ".join(other) or "none"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--skip-tests", action="store_true")
    k = sub.add_parser("confirm-labels")
    k.add_argument("--by", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "confirm-labels":
        rl.write_json(CONFIRMATION, {"by": a.by, "at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                                     "file": str(LABELS.relative_to(ROOT)) if str(LABELS).startswith(str(ROOT)) else str(LABELS),
                                     "sha256": sha(LABELS)})
        print("gating labels confirmed by %s (%s)" % (a.by, sha(LABELS)[:12]))
        return 0
    rows = check(a.skip_tests)
    for name, ok, detail in rows:
        print("%-4s %s — %s" % ("PASS" if ok else "FAIL", name, detail))
    failed = [r for r in rows if not r[1]]
    print("\n%s" % ("RELEASE GATE PASSES: the owner may tag v4.0.0 and start the first live run (BHARTIARTL, standard)."
                    if not failed else "RELEASE GATE FAILS: %d item(s) above." % len(failed)))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
