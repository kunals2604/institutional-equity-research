#!/usr/bin/env python3
"""The claim graph (methodology 3.1.0): what each conclusion rests on, and what a wrong claim reaches.

  python3 scripts/claim_graph.py build RUN_DIR [--json]   # qc/claim_graph.json and a summary; exit 1 on errors
  python3 scripts/claim_graph.py down  RUN_DIR ID [ID ...] # everything built on these claims
  python3 scripts/claim_graph.py up    RUN_DIR ID [ID ...] # everything these rest on, down to the facts

The links already exist in the run's records: a CALCULATION or ESTIMATE names its input claim IDs in
`formula_or_inputs` (methodology/EVIDENCE_STANDARDS.md), the scorecard's dimensions, drivers and predictions carry
`claim_ids`, and every report line cites the claim IDs it rests on. Read together they are a graph:

  * down: when the verifier, a script check or the auditor finds a claim wrong, every claim, scorecard input and
    report line built on it (`verify.py` asks the owner of each to review it and record what it did);
  * up: the facts a conclusion actually rests on, through the calculations it cites (`verify.py sample` and the
    auditor's sample check those first).

Errors (`build` exits 1): a claim ID cited anywhere that no ledger holds (the scorecard included); a CALCULATION that
names no input claim; a cycle among claims. Measured on run BHARTIARTL 20261012T132311Z: 180 CALCULATION rows, every
one naming its input claim IDs; nothing read those links until now (correcting what was built on a wrong claim was
only an instruction to the agents).
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

GRAPH = "qc/claim_graph.json"
FACT_TAGS = ("FACT", "MANAGEMENT STATEMENT")
DEPENDENT_TAGS = ("CALCULATION", "ESTIMATE")      # claims whose inputs are named claims


def ledger_files(run_dir: Path) -> List[Path]:
    out = sorted((run_dir / "specialists").glob("*_ledger.csv")) + sorted((run_dir / "cio").glob("*_ledger.csv"))
    return [p for p in out if p.is_file()]


def report_files(run_dir: Path) -> List[Path]:
    """The specialists' reports and follow-ups and the CIO's documents (the audit's own files are not conclusions)."""
    return sorted(p for p in list((run_dir / "specialists").glob("*.md")) + list((run_dir / "cio").glob("*.md"))
                  if p.is_file())


def owner_of_file(path: Path) -> str:
    if path.parent.name == "cio":
        return "cio"
    return re.sub(r"(_followup_\d+)?(_ledger)?$", "", path.stem)


def scorecard_nodes(sc: dict) -> Dict[str, List[str]]:
    """{node: claim IDs} for every object of the scorecard that carries claim_ids (dimension, driver, prediction)."""
    out = {}

    def walk(o, path):
        if isinstance(o, dict):
            if "claim_ids" in o:
                ids = o["claim_ids"] if isinstance(o["claim_ids"], list) else [o["claim_ids"]]
                name = o.get("name") or o.get("dimension") or o.get("driver") or o.get("id") or ""
                out["scorecard:%s%s" % (path.lstrip("."), " (%s)" % name if name else "")] = [str(x) for x in ids if x]
            for k, v in o.items():
                if k != "claim_ids":
                    walk(v, "%s.%s" % (path, k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, "%s[%d]" % (path, i))
    walk(sc, "")
    return out


def build(run_dir: Path, write: bool = True) -> dict:
    claims, inputs, links, owners = {}, {}, defaultdict(list), {}
    for p in ledger_files(run_dir):
        with p.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                cid = (r.get("claim_id") or "").strip()
                if not cid:
                    continue
                claims[cid] = {"tag": (r.get("tag") or "").strip().upper(), "owner": owner_of_file(p), "file": p.name,
                               "metric": r.get("metric", ""), "value": r.get("value", ""), "claim": (r.get("claim") or "")[:160]}
                owners[cid] = owner_of_file(p)
                got = [x for x in dict.fromkeys(rl.CLAIM_ID_RE.findall(r.get("formula_or_inputs") or "")) if x != cid]
                if got:
                    inputs[cid] = got
                for col in ("corroborated_by", "contradicted_by"):
                    for x in rl.CLAIM_ID_RE.findall(r.get(col) or ""):
                        if x != cid:
                            links[cid].append({"to": x, "kind": col})
    sc_path = run_dir / "cio" / "scorecard.json"
    if sc_path.exists():
        for node, ids in scorecard_nodes(json.loads(sc_path.read_text(encoding="utf-8"))).items():
            inputs[node] = ids
            owners[node] = "cio"
    lines = {}
    for p in report_files(run_dir):
        rel = "%s/%s" % (p.parent.name, p.name)
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            ids = list(dict.fromkeys(rl.CLAIM_ID_RE.findall(line)))
            if ids:
                node = "%s:%d" % (rel, n)
                inputs[node] = ids
                owners[node] = owner_of_file(p)
                lines[node] = line.strip()[:200]
    missing = sorted({(node, x) for node, ids in inputs.items() for x in ids if x not in claims})
    no_inputs = sorted(c for c, v in claims.items() if v["tag"] == "CALCULATION" and not inputs.get(c))
    g = {"claims": claims, "inputs": inputs, "links": dict(links), "owners": owners, "lines": lines,
         "errors": {"missing": [{"node": n, "id": x} for n, x in missing], "calculation_without_inputs": no_inputs,
                    "cycles": cycles(claims, inputs)}}
    if write:
        out = run_dir / GRAPH
        out.parent.mkdir(parents=True, exist_ok=True)
        rl.write_json(out, g)
    return g


def cycles(claims: dict, inputs: dict) -> List[List[str]]:
    found, state = [], {}

    def visit(c, stack):
        state[c] = 1
        for x in inputs.get(c, []):
            if x not in claims:
                continue
            if state.get(x) == 1:
                found.append(stack[stack.index(x):] + [x] if x in stack else [c, x])
            elif not state.get(x):
                visit(x, stack + [x])
        state[c] = 2
    for c in sorted(claims):
        if not state.get(c):
            visit(c, [c])
    return found[:20]


def errors(g: dict) -> List[str]:
    e = g["errors"]
    out = ["%s cites %s, which no ledger holds" % (m["node"], m["id"]) for m in e["missing"]]
    out += ["%s is a CALCULATION that names no input claim ID in formula_or_inputs" % c for c in e["calculation_without_inputs"]]
    out += ["cycle among claims: %s" % " -> ".join(c) for c in e["cycles"]]
    return out


def dependents_map(g: dict) -> Dict[str, Set[str]]:
    rev = defaultdict(set)
    for node, ids in g["inputs"].items():
        for x in ids:
            rev[x].add(node)
    return rev


def down(g: dict, ids: Iterable[str]) -> List[str]:
    """Every node built on these claims, transitively (claims, scorecard inputs, report lines), excluding the claims."""
    rev, seen, todo = dependents_map(g), set(), list(ids)
    start = set(ids)
    while todo:
        x = todo.pop()
        for d in rev.get(x, ()):
            if d not in seen:
                seen.add(d)
                if d in g["claims"]:
                    todo.append(d)
    return sorted(seen - start)


def up(g: dict, ids: Iterable[str]) -> List[str]:
    """Every claim these nodes rest on, transitively."""
    seen, todo = set(), list(ids)
    while todo:
        x = todo.pop()
        for i in g["inputs"].get(x, []):
            if i not in seen:
                seen.add(i)
                todo.append(i)
    return sorted(seen)


def fact_inputs(g: dict, ids: Iterable[str]) -> List[str]:
    """The FACT and MANAGEMENT STATEMENT claims these nodes rest on, through every calculation they cite."""
    ids = list(ids)
    every = set(up(g, ids)) | {i for i in ids if i in g["claims"]}
    return sorted(c for c in every if g["claims"].get(c, {}).get("tag") in FACT_TAGS)


def load(run_dir: Path, rebuild: bool = True) -> dict:
    return build(run_dir) if rebuild or not (run_dir / GRAPH).exists() else rl.load_json(run_dir / GRAPH)


def summary(g: dict) -> List[str]:
    rev = dependents_map(g)
    reach = sorted(((len(down(g, [c])), c) for c in g["claims"] if rev.get(c)), reverse=True)[:10]
    sc = [n for n in g["inputs"] if n.startswith("scorecard:")]
    lines = ["claims: %d; calculations and estimates with named inputs: %d; scorecard inputs: %d; report lines citing "
             "claims: %d" % (len(g["claims"]), sum(1 for c in g["claims"] if g["inputs"].get(c)), len(sc), len(g["lines"])),
             "facts the scorecard rests on (through every calculation): %d" % len(fact_inputs(g, sc)),
             "claims with the widest reach (nodes built on them): %s" % (", ".join("%s (%d)" % (c, n) for n, c in reach) or "-")]
    errs = errors(g)
    lines.append("errors: %d" % len(errs))
    lines += ["  - %s" % e for e in errs[:40]]
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("run_dir")
    b.add_argument("--json", action="store_true")
    b.add_argument("--no-write", action="store_true", help="do not write qc/claim_graph.json (a finished run)")
    for name in ("down", "up"):
        s = sub.add_parser(name)
        s.add_argument("run_dir")
        s.add_argument("ids", nargs="+")
        s.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not run_dir.is_dir():
        print("no such run directory: %s" % run_dir, file=sys.stderr)
        return 2
    g = build(run_dir, write=not a.no_write)
    if a.cmd == "build":
        if a.json:
            print(json.dumps(g["errors"], indent=1))
        else:
            print("\n".join(summary(g)))
        return 1 if errors(g) else 0
    got = down(g, a.ids) if a.cmd == "down" else up(g, a.ids)
    for n in got:
        info = g["claims"].get(n)
        print("%s  %s" % (n, ("[%s] %s" % (info["tag"], info["claim"])) if info else g["lines"].get(n, "")))
    print("%d node(s)" % len(got))
    return 0


if __name__ == "__main__":
    sys.exit(main())
