#!/usr/bin/env python3
"""Child runs: `new_run.py --deepen RUN_ID` and `new_run.py --refresh RUN_ID`.

A child is a new run with its own run id. It copies what it may reuse from its parent and never refers to the parent's
files, so the parent stays exactly as it was (CLAUDE.md rule 5) and the child's agents read only their own run.

- **deepen**: the same question at the same cutoff, with deeper switches (at least one switch deeper, none lighter). It
  inherits Stage 0 whole (the document map, the downloaded documents and their text, the indexes, structured filings,
  the events timeline, the brief, the identity block, the key questions, the price and the sector modules) and runs
  everything from the specialists on again at the new depth. A document the parent's readers read and audited is reused
  by the reading stage's own reuse, by hash.
- **refresh**: the same company after new results, at a later cutoff, with the parent's switches unless others are given.
  It inherits only the downloaded documents and their text and the record of their download, so the document map
  rebuilt for the new cutoff downloads only what is new (fetch_source.py reuses a URL already downloaded in the run).
  Everything else is done again for the new cutoff; the facts earlier runs verified reach it through the warehouse.

Text files the child inherits name the parent's run (its directory in paths, its id in the brief); each mention is
rewritten to the child's, and the count is recorded. Every inherited file is listed in the child's engine/inherited.csv with its SHA-256 as copied.
"""

import csv
import hashlib
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import switches  # noqa: E402

RELATIONS = ("deepen", "refresh")
STAGE0_CACHE = ("cio", "librarian", "historian", "index", "xbrl", "text", "corpus", "market")
DOWNLOAD_CACHE = ("cio", "librarian", "text")
STAGE0_AUTHORS = ("cio", "librarian")
DEEPEN_FILES = ("research_brief.md", "source_register.csv", "engine/identity.md", "engine/key_questions.md")
CORPUS_SKIP = ("reading", "digest", "facts")          # redone at the child's depth, or rebuilt for it
TEXT_SUFFIXES = (".csv", ".md", ".json", ".jsonl", ".txt")
NOT_DEPTH = ("spend_ceiling", "digest", "early_stop", "reading_transport", "canaries")
INHERITED_FIELDS = ("company", "exchange", "listing_segment", "isin", "currency", "fiscal_year_end", "held", "cost_basis")


def find_run(run_id: str, root: Path = rl.ROOT) -> Path:
    hits = sorted((root / "research" / "companies").glob("*/runs/%s" % run_id))
    if len(hits) != 1:
        raise ValueError("no run %s" % run_id if not hits else "run id %s is not unique: %s" % (run_id, hits))
    return hits[0]


def depth_change(parent: Dict[str, object], child: Dict[str, object]) -> Tuple[List[str], List[str]]:
    """(switches the child sets deeper, switches it sets lighter), among the depth switches."""
    deeper, lighter = [], []
    for name in switches.registry()["switches"]:
        if name in NOT_DEPTH or name not in parent or name not in child:
            continue
        a, b = switches.rank(name, parent[name]), switches.rank(name, child[name])
        if a is None or b is None or a == b:
            continue
        (deeper if b > a else lighter).append("%s %s -> %s" % (name, parent[name], child[name]))
    return deeper, lighter


def check_child(relation: str, parent: dict, child_switches: Dict[str, object], cutoff: str) -> List[str]:
    errs = []
    if parent.get("replay"):
        errs.append("the parent is a replay; a child of a replay would mix a historical question with a live one")
    if relation == "deepen":
        had = switches.of_manifest(parent)
        deeper, lighter = depth_change(had, child_switches)
        if not deeper:
            errs.append("a deepen must set at least one depth switch deeper than the parent's (%s)" % (
                ", ".join("%s=%s" % kv for kv in sorted(had.items()))))
        if lighter:
            errs.append("a deepen may not set a switch lighter: %s" % "; ".join(lighter))
        if cutoff != parent.get("research_cutoff"):
            errs.append("a deepen keeps the parent's cutoff (%s); a later cutoff is a refresh" % parent.get("research_cutoff"))
    elif cutoff <= str(parent.get("research_cutoff")):
        errs.append("a refresh needs a cutoff after the parent's (%s)" % parent.get("research_cutoff"))
    return errs


def _copy(src: Path, dst: Path, old: str, new: str) -> Tuple[str, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in TEXT_SUFFIXES:
        text = src.read_text(encoding="utf-8", errors="surrogateescape")
        n = text.count(old)
        if n:
            dst.write_text(text.replace(old, new), encoding="utf-8", errors="surrogateescape")
            shutil.copystat(str(src), str(dst))
            return hashlib.sha256(dst.read_bytes()).hexdigest(), n
    shutil.copy2(str(src), str(dst))
    return hashlib.sha256(dst.read_bytes()).hexdigest(), 0


def plan(parent_dir: Path, relation: str, child_switches: Dict[str, object]) -> List[Path]:
    """Every parent file the child inherits, relative to the parent's directory."""
    out: List[Path] = []

    def tree(rel: str, skip=()):
        base = parent_dir / rel
        if base.is_dir():
            for p in sorted(base.rglob("*")):
                r = p.relative_to(parent_dir)
                if p.is_file() and not (len(r.parts) > 1 and r.parts[1] in skip) and not p.name.startswith(".part-"):
                    out.append(r)

    if relation == "deepen":
        for f in DEEPEN_FILES:
            if (parent_dir / f).is_file():
                out.append(Path(f))
        tree("corpus", skip=CORPUS_SKIP)
        for c in STAGE0_CACHE:
            tree("_cache/%s" % c)
        same_digest = (parent_dir / "corpus" / "digest").is_dir() and child_switches.get("digest") == "on" and \
            (rl.load_json(parent_dir / rl.RUN_MANIFEST).get("switches") or {}).get("digest") == "on"
        if same_digest:
            tree("corpus/digest")
            tree("_cache/digest")
    else:
        for c in DOWNLOAD_CACHE:
            tree("_cache/%s" % c)
    return out


def inherit(parent_dir: Path, child_dir: Path, relation: str, child_switches: Dict[str, object]) -> dict:
    """Copy what the child inherits and record it. Returns the manifest's `parent_run` entry."""
    pm = rl.load_json(parent_dir / rl.RUN_MANIFEST)
    cm = rl.load_json(child_dir / rl.RUN_MANIFEST)
    old, new = pm["run_id"], cm["run_id"]                # run ids are unique timestamps: every mention is the parent
    rows, rewritten, size = [], 0, 0
    for rel in plan(parent_dir, relation, child_switches):
        if (child_dir / rel).exists() and rel.as_posix() in DEEPEN_FILES:
            (child_dir / rel).unlink()                     # the child's blank template gives way to the parent's work
        sha, n = _copy(parent_dir / rel, child_dir / rel, old, new)
        rewritten += n
        size += (child_dir / rel).stat().st_size
        rows.append({"path": rel.as_posix(), "sha256": sha, "paths_rewritten": n})
    if relation == "deepen":
        rows += inherit_cio_claims(parent_dir, child_dir, pm)
    log = parent_dir / "source_retrievals.csv"
    if log.exists():                                       # the downloads, so fetch_source.py reuses them by URL
        with log.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            keep = [dict(r, name=(r.get("name", "") + " [inherited from run %s]" % pm["run_id"]).strip())
                    for r in reader if r.get("author") in STAGE0_AUTHORS and r.get("local_path")
                    and (child_dir / r["local_path"]).exists()]
        with (child_dir / "source_retrievals.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(keep)
        rows.append({"path": "source_retrievals.csv", "sha256": hashlib.sha256((child_dir / "source_retrievals.csv").read_bytes()).hexdigest(),
                     "paths_rewritten": 0})
    (child_dir / "engine").mkdir(exist_ok=True)
    with (child_dir / "engine" / "inherited.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "sha256", "paths_rewritten"])
        w.writeheader()
        w.writerows(rows)
    return {"run_id": pm["run_id"], "relation": relation, "files": len(rows), "bytes": size, "paths_rewritten": rewritten,
            "list": "engine/inherited.csv"}


def inherit_cio_claims(parent_dir: Path, child_dir: Path, pm: dict) -> List[dict]:
    """The CIO's Stage 0 claims the inherited files rest on: the price claim and every claim the brief or the identity
    block cites. Never the parent's later claims, which carry its conclusions."""
    cited = {(pm.get("price") or {}).get("claim_id")}
    for f in ("research_brief.md", "engine/identity.md"):
        if (child_dir / f).exists():
            cited.update(rl.CLAIM_ID_RE.findall((child_dir / f).read_text(encoding="utf-8")))
    src = parent_dir / "cio" / "cio_ledger.csv"
    if not src.exists():
        return []
    with src.open(encoding="utf-8", newline="") as f:
        keep = [r for r in csv.DictReader(f) if r.get("claim_id") in cited]
    dst = child_dir / "cio" / "cio_ledger.csv"
    with dst.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=rl.ledger_columns(), quoting=csv.QUOTE_ALL, extrasaction="ignore").writerows(keep)
    return [{"path": "cio/cio_ledger.csv#%s" % r["claim_id"], "sha256": "", "paths_rewritten": 0} for r in keep]


def inherited_manifest(parent: dict, relation: str) -> dict:
    """Manifest fields the child takes from its parent: its identity always, and for a deepen the Stage 0 decisions
    made at the same cutoff (the price and the sector modules)."""
    out = {k: parent.get(k) for k in INHERITED_FIELDS if k in parent}
    if relation == "deepen":
        out["price"] = parent.get("price")
        out["sector_modules"] = parent.get("sector_modules")
    return out
