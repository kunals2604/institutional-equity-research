#!/usr/bin/env python3
"""The synthesis pipeline's scripts (methodology 3.2.0; methodology/SYNTHESIS.md; cio.md Stage 3).

The final report must integrate every piece of evidence the run produced, and no single context can hold it all. These
scripts build the evidence registry (every finding of every specialist, every ledger claim, every conflict, every
reading or digest item, every historian event, each with a stable id, its theme, dimensions and materiality), cut it
into theme slices a session can read, check what the theme analysts, layer analysts and section writers wrote, build
the CIO's packet, assemble the final report and check that the report integrated the evidence.

  python3 scripts/synthesis.py registry  RUN_DIR [--update]      # synthesis/registry.jsonl, REGISTRY.md, slices/
  python3 scripts/synthesis.py status    RUN_DIR                 # what is built, what is stale, what is checked
  python3 scripts/synthesis.py layer-inputs RUN_DIR              # synthesis/layers/<L>_input.md for the layer analysts
  python3 scripts/synthesis.py check-theme   RUN_DIR T1          # the theme analyst's check (brief, dispositions, citations)
  python3 scripts/synthesis.py check-layer   RUN_DIR L1          # the layer analyst's check
  python3 scripts/synthesis.py check-section RUN_DIR W1          # the section writer's check
  python3 scripts/synthesis.py followups RUN_DIR                 # open follow-up requests and contradiction candidates
  python3 scripts/synthesis.py packet    RUN_DIR                 # synthesis/CIO_PACKET.md (the CIO's bounded input)
  python3 scripts/synthesis.py assemble  RUN_DIR                 # cio/final_report.md from the section files
  python3 scripts/synthesis.py integration RUN_DIR [--out F]     # the integration checks (validate_run.py runs them)
  python3 scripts/synthesis.py restatements RUN_DIR [--n 15] [--out F]   # the auditor's restatement sample

Exit: 0 ok, 1 errors, 2 usage.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

SYN = "synthesis"
SYNTHESIS_MD = rl.ROOT / "methodology" / "SYNTHESIS.md"
SLICE_BUDGET = 110000            # tokens of one theme slice part (a session reads it comfortably beside the sources)
PACKET_BUDGET = 150000           # tokens of the CIO's packet
LAYERS = ("L1", "L2", "L3", "L4")
SECTION_KINDS = (                # (kind, report section, how items are cut)
    ("key_finding", "Key Findings", "list"),
    ("conclusion", "Domain Conclusion", "list"),
    ("cio_question", "Questions and Dependencies for the CIO", "list_or_table"),
    ("internal_conflict", "Contradictions and Data Conflicts", "list_or_table"),
)


def themes() -> Dict[str, dict]:
    return rl.read_json_block(SYNTHESIS_MD, "SYNTHESIS_THEMES")


def materiality_rules() -> dict:
    return rl.read_json_block(SYNTHESIS_MD, "SYNTHESIS_MATERIALITY")


def dispositions() -> List[str]:
    return rl.read_block(SYNTHESIS_MD, "SYNTHESIS_DISPOSITIONS")


def consistency_rules() -> List[dict]:
    return rl.read_json_block(SYNTHESIS_MD, "SYNTHESIS_CONSISTENCY_RULES")


def writer_groups() -> Dict[str, dict]:
    return rl.read_json_block(SYNTHESIS_MD, "SECTION_WRITER_GROUPS")


def est_tokens(chars: int) -> int:
    return int(chars / 3.6) + 1


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def syn(run_dir: Path, *parts: str) -> Path:
    return run_dir.joinpath(SYN, *parts)


def active_themes(run_dir: Path) -> Dict[str, dict]:
    """The run's themes: T6 only when its sector modules include a listed-subsidiary or holding-company module."""
    mods = set(rl.run_sector_modules(run_dir) or [])
    return {k: v for k, v in themes().items() if not v.get("when_modules") or mods & set(v["when_modules"])}


def run_version(run_dir: Path) -> tuple:
    return rl.version_tuple(rl.load_json(run_dir / rl.RUN_MANIFEST).get("methodology_version"))


# ------------------------------------------------------------------------------------------------------------------
# parsing the specialist reports
# ------------------------------------------------------------------------------------------------------------------

def section_span(text: str, heading: str) -> Optional[Tuple[str, int]]:
    """(body, line number of the heading) of an H2 section."""
    target = rl.norm_heading(heading)
    for m in re.finditer(r"^##\s+(?!#)(.+)$", text, re.M):
        if rl.norm_heading(m.group(1)) == target:
            body = rl.section(text, heading) or ""
            return body, text[:m.start()].count("\n") + 1
    return None


def list_items(body: str, first_line: int) -> List[Tuple[int, str]]:
    """Top-level list items (`- `, `* `, `1. `) with their continuation lines, as (line number, text)."""
    out, cur, cur_line = [], [], 0
    for i, line in enumerate(body.splitlines()):
        if re.match(r"^(?:[-*]|\d+[.)])\s+\S", line):
            if cur:
                out.append((cur_line, norm(" ".join(cur))))
            cur, cur_line = [re.sub(r"^(?:[-*]|\d+[.)])\s+", "", line)], first_line + i
        elif cur and line.strip() and not line.startswith("#") and not line.strip().startswith("|"):
            cur.append(line.strip())
        elif cur and not line.strip():
            out.append((cur_line, norm(" ".join(cur))))
            cur = []
    if cur:
        out.append((cur_line, norm(" ".join(cur))))
    return out


def table_rows(body: str, first_line: int) -> List[Tuple[int, List[str]]]:
    rows = []
    for i, line in enumerate(body.splitlines()):
        s = line.strip()
        if s.startswith("|") and not re.match(r"^\|\s*:?-{2,}", s):
            rows.append((first_line + i, [c.strip() for c in s.strip("|").split("|")]))
    return rows[1:] if rows else []          # the first row is the header


def report_items(run_dir: Path, path: Path, author: str, followup: bool = False) -> List[dict]:
    """The registry items of one specialist report (or follow-up)."""
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(run_dir))
    out = []
    if followup:
        span = section_span(text, "Key Findings")
        body, line0 = span if span else (text, 1)
        for ln, t in list_items(body, line0) or [(1, norm(text)[:1500])]:
            out.append(item("followup_finding", author, rel, "Key Findings" if span else "(whole report)", ln, t))
        return out
    for kind, heading, how in SECTION_KINDS:
        span = section_span(text, heading)
        if not span:
            continue
        body, line0 = span
        got = list_items(body, line0)
        if how == "list_or_table":
            got += [(ln, norm(" | ".join(c for c in cells if c))) for ln, cells in table_rows(body, line0)]
        if not got and norm(body):
            out.append(item("unparsed", author, rel, heading, line0, norm(body)[:1500]))
        for ln, t in got:
            if t and not re.fullmatch(r"(?i)(none|n/?a|-|—|no (?:questions|conflicts?)[^|]*)\.?", t):
                out.append(item(kind, author, rel, heading, ln, t))
    span = section_span(text, "Four-Layer Evidence Crosswalk")
    if span:
        body, line0 = span
        for head, block in rl.h3_blocks(body):
            layer = layer_of(head)
            if not layer:
                continue
            bl0 = line0 + body[:body.find(block)].count("\n")
            for field in rl.CROSSWALK_FIELDS:
                m = re.search(r"\*\*%s:?\*\*:?\s*(.*?)(?=\n\s*[-*]\s+\*\*|\Z)" % re.escape(field), block, re.S)
                if not m or not norm(m.group(1)):
                    continue
                txt = norm(m.group(1))
                it = item("crosswalk", author, rel, "Four-Layer Evidence Crosswalk / %s / %s" % (layer, field),
                          bl0 + block[:m.start()].count("\n"), txt)
                it["layer"], it["field"] = layer, field
                if field == "Plausibility effect":
                    pl = next((p for p in rl.PLAUSIBILITY_VALUES if txt.lower().startswith(p)), None)
                    it["plausibility"] = pl
                out.append(it)
    span = section_span(text, "Assumptions, Uncertainty and Missing Evidence")
    if span:
        body, line0 = span
        for ln, cells in table_rows(body, line0):
            if len(cells) >= 2 and any(cells):
                out.append(item("assumption", author, rel, "Assumptions", ln, norm(" | ".join(c for c in cells if c))))
        for ln, t in list_items(body, line0):
            out.append(item("missing_evidence", author, rel, "Missing evidence", ln, t))
    span = section_span(text, rl.CHECKLIST_SECTION)
    if span:
        body, line0 = span
        for ln, cells in table_rows(body, line0):
            low = " ".join(cells).lower()
            if re.search(r"\bpartial\b|\bnot available\b", low):
                out.append(item("checklist_gap", author, rel, rl.CHECKLIST_SECTION, ln, norm(" | ".join(c for c in cells if c))))
    return out


def layer_of(head: str) -> Optional[str]:
    m = re.search(r"Layer\s*([1-4])", head)
    return "L%s" % m.group(1) if m else None


def item(kind: str, author: str, file: str, section_: str, line: int, text: str) -> dict:
    return {"kind": kind, "author": author, "file": file, "section": section_, "line": line, "text": text[:1500],
            "claim_ids": sorted(set(rl.CLAIM_ID_RE.findall(text))), "provenance": "specialist"}


# ------------------------------------------------------------------------------------------------------------------
# the other inputs
# ------------------------------------------------------------------------------------------------------------------

def specialist_ledger_paths(run_dir: Path) -> List[Path]:
    return sorted((run_dir / "specialists").glob("*_ledger.csv"))


def author_of_ledger(path: Path) -> str:
    stem = path.name[:-len("_ledger.csv")]
    return re.sub(r"_followup_\d+$", "", stem)


def ledger_items(run_dir: Path) -> List[dict]:
    out = []
    for p in specialist_ledger_paths(run_dir):
        _, rows = rl.read_csv(p)
        for n, r in enumerate(rows, 2):
            txt = "%s [%s%s]" % (norm(r.get("claim")), r.get("tag", ""),
                                 (": %s %s %s %s" % (r.get("metric", ""), r.get("value", ""), r.get("unit", ""), r.get("period", ""))).rstrip()
                                 if r.get("value") else "")
            it = item("ledger_claim", author_of_ledger(p), str(p.relative_to(run_dir)), "ledger", n, txt)
            it["claim_ids"] = [r.get("claim_id", "")]
            it["metrics"] = [r["metric"]] if r.get("metric") else []
            it["periods"] = [r["period"]] if r.get("period") else []
            it["tags"] = [r.get("tag", "")]
            try:
                it["tier"] = int(r.get("source_tier") or 0) or None
            except ValueError:
                it["tier"] = None
            out.append(it)
    return out


def conflict_items(run_dir: Path) -> List[dict]:
    import reconcile_numbers
    out = []
    for n, c in enumerate(reconcile_numbers.conflicts(run_dir), 1):
        ids = [x for x in re.split(r"[;,\s]+", str(c.get("claim_ids") or "")) if x]
        txt = "Numeric conflict on %s %s %s %s: %s to %s (gap %s) between %s" % (
            c.get("metric"), c.get("period"), c.get("basis"), c.get("unit"), c.get("min"), c.get("max"), c.get("gap"),
            ", ".join(ids))
        it = item("numeric_conflict", "scripts", "qc/numeric_conflicts.csv", "conflict", n, txt)
        it["claim_ids"], it["metrics"], it["provenance"] = ids, [c.get("metric")], "script"
        out.append(it)
    return out


def open_verification(v: dict) -> List[dict]:
    """Every finding of qc/verification.json still open, the run's own and each specialist's. Information-only lines
    (a value read off a page image, say) and waived findings are not open."""
    found = list(v.get("run_findings") or [])
    for name, rec in sorted((v.get("specialists") or {}).items()):
        found += [dict(f, agent=f.get("agent") or name) for f in rec.get("findings") or []]
    return [{k: f.get(k) for k in ("check", "agent", "detail", "claims")} for f in found
            if not f.get("waived") and f.get("severity") != "info"]


def verification_items(run_dir: Path) -> List[dict]:
    p = run_dir / "qc" / "verification.json"
    if not p.exists():
        return []
    out = []
    for f in open_verification(rl.load_json(p)):
        txt = "%s %s: %s %s" % (f.get("check"), f.get("agent"), f.get("detail"), "; ".join((f.get("claims") or [])[:8]))
        it = item("verification", f.get("agent") or "scripts", "qc/verification.json", f.get("check", ""), 0, txt)
        it["provenance"] = "script"
        out.append(it)
    return out


def forecast_items(run_dir: Path) -> List[dict]:
    p = run_dir / "calc" / "forecasting_reconcile.json"
    if not p.exists():
        return []
    out = []
    for n, flag in enumerate(rl.load_json(p).get("flags", []), 1):
        it = item("forecast_reconciliation", "scripts", "calc/forecasting_reconcile.json", "forecast vs valuation", n,
                  "Forecasting model vs valuation inputs: %s" % flag)
        it["provenance"] = "script"
        out.append(it)
    return out


def corpus_items(run_dir: Path) -> List[dict]:
    """Reading on: every reconciled reader item (provenance read_page_verified, the document's tier). Reading off: every
    web-digest item, with its page confirmation (digest_page_confirmed ... digest_unconfirmed_lead, tier 6)."""
    sch = rl.reading_schema()
    out = []
    if rl.reading_on(run_dir):
        import reading
        p = reading.load_json(run_dir / reading.READING / "plan.json")
        if not p:
            return out
        pol = reading.run_policy(run_dir)
        docs = {d["key"]: d for d in p["documents"]}
        for c in p["chunks"]:
            for it in reading.final_items(run_dir, c, pol):
                spec = sch["types"].get(it.get("type"))
                if not spec or it.get("type") == "table":
                    continue
                d = docs.get(c["doc"], {})
                txt = "%s · %s · %s — \"%s\"" % (it.get("type"), it.get("period") or "-", "; ".join(
                    "%s: %s" % (k, v) for k, v in (it.get("fields") or {}).items() if str(v).strip()), norm(it.get("quote"))[:500])
                ri = item("corpus_item", "reading", d.get("text") or d.get("pdf") or c["doc"], "%s p.%s" % (c["doc"], it.get("page")),
                          0, txt)
                ri.update(doc=c["doc"], page=it.get("page"), type=it.get("type"), topic=spec["topic"],
                          material_type=bool(spec.get("material")), provenance="read_page_verified",
                          tier=1 if d.get("doc_type") == "annual_report" else (4 if d.get("doc_type") == "transcript" else 3),
                          anchor="%s|%s|%s" % (c["id"], it.get("unit"), it.get("type")))
                out.append(ri)
    else:
        import digest
        if not (run_dir / rl.DIGEST_DIR / "plan.json").exists():
            return out
        for it in digest.digest_items(run_dir):
            spec = sch["types"][it["type"]]
            c = it.get("confirm") or {}
            txt = "%s · %s · %s — \"%s\" [%s, %s]%s" % (
                it["type"], it.get("period") or "-", "; ".join("%s: %s" % (k, v) for k, v in (it.get("fields") or {}).items()
                                                           if str(v).strip()), norm(it.get("quote"))[:500],
                it.get("publisher"), it.get("source_url"),
                " — page-confirmed %s p.%s" % (it.get("doc_key"), c.get("page")) if c.get("status") == "page_confirmed" else "")
            ri = item("corpus_item", "digest", "%s/items/%s.jsonl" % (rl.DIGEST_DIR, it.get("file")), "digest", it.get("line", 0), txt)
            ri.update(doc=it.get("doc_key"), page=c.get("page"), type=it["type"], topic=spec["topic"],
                      material_type=bool(spec.get("material")), provenance=it["provenance"], tier=6, anchor=it["id"])
            out.append(ri)
    return out


def event_items(run_dir: Path) -> List[dict]:
    p = run_dir / rl.events_check_rel(run_dir)
    if not p.exists():
        return []
    out = []
    for r in rl.load_json(p).get("rows", []):
        txt = "Historian event %s (%s, %s): %s — %s; source %s" % (
            r.get("event_id"), r.get("date"), r.get("category"), norm(r.get("event")), r.get("status"), r.get("source_url"))
        it = item("event", "historian", "corpus/events.csv", r.get("status", ""), 0, txt)
        it.update(provenance="web_event_lead", tier=6, status=r.get("status"), anchor=r.get("event_id"))
        out.append(it)
    return out


# ------------------------------------------------------------------------------------------------------------------
# classification
# ------------------------------------------------------------------------------------------------------------------

def dimension_index() -> Dict[str, List[str]]:
    inv = defaultdict(list)
    for dim, owners in rl.dimension_owners().items():
        for o in owners:
            inv[o].append(dim)
    return inv


def classify(items: List[dict], run_dir: Path) -> None:
    th = active_themes(run_dir)
    rules = materiality_rules()
    dims_of = dimension_index()
    by_author = {}
    for tid, t in th.items():
        for a in t.get("authors", []):
            by_author.setdefault(a, tid)
    by_topic = {}
    for tid, t in th.items():
        for tp in t.get("topics", []):
            by_topic[tp] = tid                        # a later theme (T6) takes a shared topic over
    cited_by_findings: Set[str] = set()
    for it in items:
        if it["kind"] in ("key_finding", "conclusion", "followup_finding"):
            cited_by_findings |= set(it["claim_ids"])
    for it in items:
        k = it["kind"]
        low = it["text"].lower()
        dims = sorted(set(dims_of.get(it["author"], [])))
        if k == "corpus_item":
            owner = by_topic.get(it.get("topic"), "T1")
            dims = sorted({d for tid, t in th.items() if tid == owner for d in t.get("dimensions", [])})
        elif k == "event":
            owner = "T5"
        elif k in ("numeric_conflict", "forecast_reconciliation"):
            owner = "T4" if k == "forecast_reconciliation" else by_author.get(
                next((rl.agent_of_prefix(c) for c in it["claim_ids"] if rl.agent_of_prefix(c)), ""), "T1")
        elif k == "verification":
            owner = by_author.get(it["author"], "T1")
        else:
            owner = by_author.get(it["author"], "T1")
        if "T6" in th and it["author"] == "special-situations" and re.search(r"subsidiar|associate|holding|stake", low):
            owner = "T6"
        it["owner_theme"] = owner
        it["themes"] = sorted({owner} | {tid for tid, t in th.items() if set(t.get("dimensions", [])) & set(dims)})
        it["dimensions"] = dims
        if k == "crosswalk":
            it["owner_theme"] = "layer"           # layer analysts disposition crosswalk rows
            mat = "material" if it.get("plausibility") in ("raises", "lowers") else "standard"
        elif k == "corpus_item":
            if it.get("type") in rules["gating_corpus_types"]:
                mat = "gating"
            elif it.get("material_type"):
                mat = "material"
            else:
                mat = "reference"
        elif k == "event":
            mat = "material" if it.get("status") == "unmatched" else "reference"
        elif k == "ledger_claim":
            mat = "standard" if set(it["claim_ids"]) & cited_by_findings else "reference"
        elif k in rules["material_kinds"]:
            mat = "gating" if k in rules["gating_kinds"] and red_flag(it["text"], rules) else "material"
        else:
            mat = "standard"
        it["materiality"] = mat
        if mat == "reference":
            if k == "ledger_claim":
                it["cluster"] = "C-%s-%s" % (it["author"], cluster_slug((it.get("metrics") or ["qualitative"])[0]))
            elif k == "corpus_item":
                it["cluster"] = "C-%s-%s" % (it.get("topic"), it.get("type"))
            else:
                it["cluster"] = "C-%s-%s" % (k, it.get("status") or "other")


def red_flag(text: str, rules: dict) -> bool:
    """Does the text state a red flag? Read sentence by sentence, so a negated sentence ("searches found nothing on fraud")
    is not one and a clear sentence after it still counts."""
    for sentence in re.split(r"(?<=[.;:])\s+|\n+", text):
        low = sentence.lower().replace("with or without", " ")
        if any(re.search(p, low) for p in rules["gating_patterns"]) and not re.search(rules["gating_negation"], low):
            return True
    return False


def cluster_slug(key: str) -> str:
    """A metric key as part of a cluster id: only characters a register row can carry."""
    return re.sub(r"[^\w-]+", "_", key).strip("_")


def assign_ids(items: List[dict]) -> None:
    seen = Counter()
    for it in items:
        anchor = it.get("anchor") or "%s|%s|%s" % (it["section"], it["text"][:200], ",".join(it["claim_ids"]))
        base = "%s|%s|%s" % (it["kind"], it["file"], anchor)
        seen[base] += 1
        if seen[base] > 1:
            base += "|%d" % seen[base]
        it["id"] = "R-" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:8]


# ------------------------------------------------------------------------------------------------------------------
# registry and slices
# ------------------------------------------------------------------------------------------------------------------

def inputs_of(run_dir: Path) -> List[Path]:
    v = run_version(run_dir)
    out = []
    for name in rl.specialists_for(v):
        out.append(run_dir / "specialists" / ("%s.md" % name))
    out += sorted((run_dir / "specialists").glob("*_followup_*.md"))
    out += specialist_ledger_paths(run_dir)
    out += [run_dir / "qc" / "verification.json", run_dir / "calc" / "forecasting_reconcile.json",
            run_dir / rl.events_check_rel(run_dir)]
    out += [run_dir / rl.coverage_rel(run_dir)]
    return [p for p in out if p.exists()]


def build_registry(run_dir: Path, log=print) -> dict:
    v = run_version(run_dir)
    items: List[dict] = []
    for name in rl.specialists_for(v):
        p = run_dir / "specialists" / ("%s.md" % name)
        if p.exists():
            items += report_items(run_dir, p, name)
    for p in sorted((run_dir / "specialists").glob("*_followup_*.md")):
        items += report_items(run_dir, p, re.sub(r"_followup_\d+$", "", p.stem), followup=True)
    items += ledger_items(run_dir)
    items += conflict_items(run_dir) + verification_items(run_dir) + forecast_items(run_dir)
    items += corpus_items(run_dir) + event_items(run_dir)
    classify(items, run_dir)
    assign_ids(items)
    out_dir = syn(run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "registry.jsonl").open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    slices = write_slices(run_dir, items)
    counts = Counter((it["kind"], it["materiality"]) for it in items)
    by_theme = Counter(it["owner_theme"] for it in items if it["materiality"] != "reference")
    lines = ["# Evidence registry — run %s" % rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id"), "",
             "Built by `scripts/synthesis.py registry` (methodology/SYNTHESIS.md). Reading mode: **%s**. %d items; %d "
             "reference items in %d clusters." % (rl.reading_mode(run_dir), len(items),
                                                  sum(1 for i in items if i["materiality"] == "reference"),
                                                  len({i["cluster"] for i in items if i.get("cluster")})), "",
             "| Kind | Gating | Material | Standard | Reference |", "|---|---|---|---|---|"]
    for k in sorted({i["kind"] for i in items}):
        lines.append("| %s | %d | %d | %d | %d |" % (k, counts[(k, "gating")], counts[(k, "material")],
                                                   counts[(k, "standard")], counts[(k, "reference")]))
    lines += ["", "| Owner | Items to disposition (non-reference) | Clusters | Slice parts | ≈ tokens |", "|---|---|---|---|---|"]
    for tid, s in slices.items():
        lines.append("| %s | %d | %d | %d | %s |" % (tid, by_theme.get(tid, 0), len(s["clusters"]), len(s["parts"]),
                                                   format(s["tokens"], ",")))
    lines.append("| layer (crosswalk rows) | %d | - | - | - |" % by_theme.get("layer", 0))
    (out_dir / "REGISTRY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    status = {"built_at": now(), "reading_mode": rl.reading_mode(run_dir), "items": len(items),
              "inputs": {str(p.relative_to(run_dir)): input_hash(p) for p in inputs_of(run_dir)},
              "themes": {tid: {"parts": [p["file"] for p in s["parts"]], "items": s["n_items"], "clusters": len(s["clusters"])}
                         for tid, s in slices.items()}}
    rl.write_json(out_dir / "status.json", status)
    log("registry: %d items (%s) -> %s" % (len(items), ", ".join("%s %d" % (m, sum(1 for i in items if i["materiality"] == m))
                                                                for m in ("gating", "material", "standard", "reference")),
                                         out_dir / "REGISTRY.md"))
    return status


def now() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_registry(run_dir: Path) -> List[dict]:
    p = syn(run_dir, "registry.jsonl")
    if not p.exists():
        raise SystemExit("no registry: run synthesis.py registry %s" % run_dir)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def input_hash(p: Path) -> str:
    """What the registry depends on in an input file. verify.py stamps qc/verification.json on every run: only its open
    findings matter, so re-running verification with nothing new does not make the registry stale."""
    if p.name == "verification.json" and p.exists():
        return hashlib.sha256(json.dumps(open_verification(rl.load_json(p)), sort_keys=True).encode()).hexdigest()
    return sha_file(p)


def stale(run_dir: Path) -> List[str]:
    """Inputs changed (or added) since the registry was built."""
    st_p = syn(run_dir, "status.json")
    if not st_p.exists():
        return ["the registry has not been built"]
    old = rl.load_json(st_p).get("inputs", {})
    cur = {str(p.relative_to(run_dir)): input_hash(p) for p in inputs_of(run_dir)}
    return sorted([k for k in cur if old.get(k) != cur[k]] + [k for k in old if k not in cur])


def item_line(it: dict) -> str:
    head = "### %s · %s · %s · %s%s" % (it["id"], it["kind"], it["author"], it["materiality"],
                                        " · " + ",".join(it["dimensions"]) if it.get("dimensions") else "")
    where = "%s:%s" % (it["file"], it["line"]) if it.get("line") else it["file"]
    meta = "%s · %s · claims: %s%s" % (where, it["section"], ", ".join(it["claim_ids"]) or "-",
                                       " · provenance: %s" % it["provenance"] if it["provenance"] != "specialist" else "")
    return "%s\n%s\n> %s\n" % (head, meta, it["text"])


def write_slices(run_dir: Path, items: List[dict]) -> Dict[str, dict]:
    """One slice per theme: its items individually, its reference items as clusters; split into parts within the
    budget (by author or topic) when larger."""
    out_dir = syn(run_dir, "slices")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.md"):
        old.unlink()
    th = active_themes(run_dir)
    result = {}
    for tid, t in th.items():
        mine = [i for i in items if i["owner_theme"] == tid and i["materiality"] != "reference"]
        refs = [i for i in items if i["owner_theme"] == tid and i["materiality"] == "reference"]
        clusters = defaultdict(list)
        for i in refs:
            clusters[i["cluster"]].append(i)
        order = {"gating": 0, "material": 1, "standard": 2}
        mine.sort(key=lambda i: (order.get(i["materiality"], 3), i["author"], i["kind"], i["file"], i.get("line", 0)))
        blocks = [(i.get("author") if i["kind"] != "corpus_item" else i.get("topic"), item_line(i)) for i in mine]
        cblocks = []
        for cid, cl in sorted(clusters.items()):
            ex = cl[0]["text"][:220]
            cblocks.append((cl[0].get("author"), "### %s · cluster · %d reference items · e.g. %s\n> %s\n" % (
                cid, len(cl), ", ".join(sorted({c for i in cl for c in i["claim_ids"]})[:6]) or cl[0]["id"], ex)))
        head = ["# Slice %s — %s" % (tid, t["title"]), "",
                "Theme analyst's input (methodology/SYNTHESIS.md). Disposition **every** item (`R-…`) and **every** cluster "
                "(`C-…`) below in your Disposition Register, exactly once. Items are ordered gating, material, standard; "
                "open the cited report line or source wherever the text here is not enough.", ""]
        parts, cur, cur_tok, part_key = [], [], 0, None
        for key, b in blocks + cblocks:
            tok = est_tokens(len(b))
            if cur and cur_tok + tok > SLICE_BUDGET:
                parts.append(cur)
                cur, cur_tok = [], 0
            cur.append(b)
            cur_tok += tok
        if cur or not parts:
            parts.append(cur)
        files = []
        for n, part in enumerate(parts, 1):
            name = "%s.md" % tid if len(parts) == 1 else "%s.p%d.md" % (tid, n)
            text = "\n".join(head + (["Part %d of %d." % (n, len(parts)), ""] if len(parts) > 1 else []) + part) + "\n"
            (out_dir / name).write_text(text, encoding="utf-8")
            files.append({"file": "%s/slices/%s" % (SYN, name), "tokens": est_tokens(len(text)),
                          "ids": re.findall(r"^### ((?:R|C)-[\w-]+)", text, re.M)})
        result[tid] = {"parts": files, "clusters": sorted(clusters), "n_items": len(mine),
                       "tokens": sum(f["tokens"] for f in files)}
    rl.write_json(syn(run_dir, "slices.json"), result)
    return result


def theme_scope(run_dir: Path, tid: str) -> Set[str]:
    """Every id (item or cluster) the theme must disposition."""
    sl = rl.load_json(syn(run_dir, "slices.json"))
    return {i for p in sl.get(tid, {}).get("parts", []) for i in p["ids"]}


# ------------------------------------------------------------------------------------------------------------------
# what the synthesis agents write, and its checks
# ------------------------------------------------------------------------------------------------------------------

DISP_ROW_RE = re.compile(r"^\|\s*`?((?:R|C)-[\w-]+)`?\s*\|\s*`?([a-z_]+)`?\s*\|([^|]*)\|(.*)\|\s*$")
F_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:#{3,4}\s*)?\**\s*(F\d+)\b")


def pointer_errors(rid: str, disp: str, ptr: str, reason: str, reg: Dict[str, dict], known: Set[str],
                   clusters: Set[str]) -> List[str]:
    """The two dispositions that take an item out of the report. superseded must name what replaced it, and that must
    exist; unverified_lead is for leads, never for a specialist's finding."""
    it = reg.get(rid, {})
    words = len(re.findall(r"\w+", reason))
    if disp == "superseded":
        if not (ptr in reg or ptr in known or ptr in clusters):
            return ["superseded must point to the R-id, cluster or claim ID that replaces it, and %r does not exist" % ptr]
        if it.get("materiality") == "gating" and words < 10:
            return ["a gating item superseded needs a reason of at least ten words saying what replaced it and why"]
    elif disp == "unverified_lead":
        if not (it.get("kind") == "event" or str(it.get("provenance", "")).startswith("digest")):
            return ["only a digest or historian lead can be an unverified lead; integrate, contest or follow up this item"]
        if words < 5:
            return ["unverified_lead must say what was checked"]
    return []


def cluster_ids(run_dir: Path) -> Set[str]:
    sl = rl.load_json(syn(run_dir, "slices.json")) if syn(run_dir, "slices.json").exists() else {}
    return {i for t in sl.values() for p in t.get("parts", []) for i in p["ids"] if i.startswith("C-")}


def theme_briefs(run_dir: Path) -> List[Path]:
    """Every theme brief, parts of a split theme included."""
    d = syn(run_dir, "themes")
    return sorted(d.glob("T[0-9].md")) + sorted(d.glob("T[0-9].p*.md"))


def known_claim_ids(run_dir: Path) -> Set[str]:
    ids = set()
    for p in rl.run_ledger_paths(run_dir):
        ids |= {r.get("claim_id", "") for r in rl.read_csv(p)[1]}
    return ids


def ledger_rows_by_id(run_dir: Path) -> Dict[str, dict]:
    out = {}
    for p in rl.run_ledger_paths(run_dir):
        for r in rl.read_csv(p)[1]:
            out[r.get("claim_id", "")] = r
    return out


def register_rows(text: str, heading: str) -> List[Tuple[str, str, str, str]]:
    body = rl.section(text, heading) or ""
    out = []
    for line in body.splitlines():
        m = DISP_ROW_RE.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()))
    return out


def findings_of(text: str) -> Dict[str, str]:
    """F# -> its text, from the Integrated Findings section."""
    body = rl.section(text, "Integrated Findings") or ""
    out, cur = {}, None
    for line in body.splitlines():
        m = F_RE.match(line)
        if m:
            cur = m.group(1)
            out[cur] = line
        elif cur and line.strip():
            out[cur] += "\n" + line
    return out


def common_checks(run_dir: Path, path: Path, errs: List[str], known: Optional[Set[str]] = None) -> None:
    """Claim IDs exist, tags carry them, cited numbers tie to their claims, no flagged phrases, canonical layer names."""
    import audit_tools
    text = path.read_text(encoding="utf-8")
    known = known if known is not None else known_claim_ids(run_dir)
    res = rl.Result(str(path))
    rl.check_tags(text, res, known)
    rl.check_flagged_phrases(text, res, strict=True)
    rl.check_layer_names(text, res)
    # a brief or draft with no tagged claim at all (an empty theme, a monitoring table) is not an error here: the final
    # report's own validator checks its tags
    errs += ["%s: %s" % (path.name, e) for e in res.errors if not e.startswith("No epistemic tags")]
    bad = sorted(set(rl.CLAIM_ID_RE.findall(text)) - known)
    if bad:
        errs.append("%s: claim IDs no ledger holds: %s" % (path.name, ", ".join(bad[:15])))
    for r in audit_tools.tieout_rows(run_dir, path):
        if r["status"] in ("mismatch", "other_claim"):
            errs.append("%s line %s: the number does not tie to the cited claim (%s; cited %s; numbers %s)%s" % (
                path.name, r["line"], r["status"], r["cited"][:80], r["numbers"][:50],
                " — it equals %s" % r["uncited_matches"] if r["uncited_matches"] else ""))


def numbers_of_record(text: str) -> List[List[str]]:
    rows = []
    for _, cells in table_rows(rl.section(text, "Numbers of Record") or "", 0):
        if len(cells) >= 5:
            rows.append(cells)
    return rows


def check_theme(run_dir: Path, tid: str, part: Optional[int] = None) -> List[str]:
    """The theme analyst's check. `part` k (a theme split into parts): only part brief k and the ids of slice part k."""
    errs: List[str] = []
    st = stale(run_dir)
    if st:
        return ["the registry is stale (changed: %s): re-run synthesis.py registry" % ", ".join(st[:6])]
    sl = rl.load_json(syn(run_dir, "slices.json")).get(tid)
    if sl is None:
        return ["%s is not a theme of this run (%s)" % (tid, ", ".join(sorted(rl.load_json(syn(run_dir, "slices.json")))))]
    reg = {i["id"]: i for i in load_registry(run_dir)}
    scope = theme_scope(run_dir, tid)
    tdir = syn(run_dir, "themes")
    main_ = tdir / ("%s.md" % tid)
    parts = [tdir / ("%s.p%d.md" % (tid, n)) for n in range(1, len(sl["parts"]) + 1)] if len(sl["parts"]) > 1 else []
    if part is not None:
        if not 1 <= part <= len(parts):
            return ["%s has %d slice part(s)" % (tid, len(sl["parts"]))]
        scope = set(sl["parts"][part - 1]["ids"])
        parts = [parts[part - 1]]
        main_ = None
    files = [f for f in ([main_] if main_ else []) + parts if f.exists()]
    if main_ is not None and not main_.exists():
        errs.append("synthesis/themes/%s.md does not exist yet" % tid)
    for f in parts:
        if not f.exists():
            errs.append("synthesis/themes/%s does not exist yet (part brief)" % f.name)
    for f in parts:
        if f.exists():
            res = rl.Result(str(f))
            rl.check_sections(f.read_text(encoding="utf-8"), ["Integrated Findings", "Contradiction Candidates",
                                                             "Numbers of Record", "Gaps and Follow-up Requests",
                                                             "Disposition Register"], res)
            errs += ["%s: %s" % (f.name, e) for e in res.errors]
    if main_ is not None and main_.exists():
        res = rl.Result(str(main_))
        rl.check_sections(main_.read_text(encoding="utf-8"), rl.read_block(SYNTHESIS_MD, "THEME_BRIEF_SECTIONS"), res)
        errs += ["%s.md: %s" % (tid, e) for e in res.errors]
    vocab = set(dispositions())
    seen: Dict[str, str] = {}
    known = known_claim_ids(run_dir)
    ledger = ledger_rows_by_id(run_dir)
    for f in files:
        text = f.read_text(encoding="utf-8")
        fs = findings_of(text)
        for fid, ftxt in fs.items():
            if not re.search(r"\b(?:R|C)-[\w-]{4,}", ftxt):
                errs.append("%s %s: name the registry items (R-ids) it integrates" % (f.name, fid))
        ccs = set(re.findall(r"\bCC-%s-\d+\b" % tid, rl.section(text, "Contradiction Candidates") or ""))
        fus = set(re.findall(r"\bFU-%s-\d+\b" % tid, rl.section(text, "Gaps and Follow-up Requests") or ""))
        for rid, disp, ptr, reason in register_rows(text, "Disposition Register"):
            where = "%s %s" % (f.name, rid)
            if rid in seen:
                errs.append("%s: dispositioned twice (also in %s)" % (where, seen[rid]))
            seen[rid] = f.name
            if rid not in scope:
                errs.append("%s: not an id of this %s" % (where, "slice part" if part else "theme's slice"))
                continue
            if disp not in vocab:
                errs.append("%s: disposition %r is not one of %s" % (where, disp, ", ".join(sorted(vocab))))
                continue
            gating = reg.get(rid, {}).get("materiality") == "gating"
            if disp == "integrated" and not (re.fullmatch(r"F\d+", ptr) and ptr in fs):
                errs.append("%s: integrated must point to an Integrated Finding of this brief (got %r)" % (where, ptr))
            elif disp == "contested" and ptr not in ccs:
                errs.append("%s: contested must point to a Contradiction Candidate of this brief (got %r)" % (where, ptr))
            elif disp == "needs_follow_up" and ptr not in fus:
                errs.append("%s: needs_follow_up must point to a Follow-up Request of this brief (got %r)" % (where, ptr))
            elif disp in ("superseded", "unverified_lead"):
                errs += ["%s: %s" % (where, e) for e in pointer_errors(rid, disp, ptr, reason, reg, known, cluster_ids(run_dir))]
            elif disp == "immaterial":
                if gating:
                    errs.append("%s: a gating item cannot be immaterial (integrate it, contest it or ask for a follow-up)" % where)
                elif len(re.findall(r"\w+", reason)) < 10:
                    errs.append("%s: immaterial needs a reason of at least ten words" % where)
        common_checks(run_dir, f, errs, known)
        for cells in numbers_of_record(text):
            cid = next(iter(rl.CLAIM_ID_RE.findall(" ".join(cells))), None)
            if not cid:
                errs.append("%s Numbers of Record: a row without its claim ID: %s" % (f.name, " | ".join(cells)[:80]))
                continue
            row = ledger.get(cid)
            if row is None:
                continue                      # reported above as an unknown claim ID
            lv = (row.get("value") or "").strip()
            stated = cells[3] if len(cells) > 3 else ""
            if lv and stated and _num(stated) is not None and _num(lv) is not None and abs(_num(stated) - _num(lv)) > 0.005 * max(1.0, abs(_num(lv))):
                errs.append("%s Numbers of Record: %s states %s but its ledger value is %s" % (f.name, cid, stated, lv))
    missing = sorted(scope - set(seen))
    if missing:
        errs.append("%d slice id(s) without a disposition: %s%s" % (len(missing), ", ".join(missing[:20]),
                                                                    " …" if len(missing) > 20 else ""))
    return errs[:120]


def _num(s: str) -> Optional[float]:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(s).replace("−", "-"))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def layer_scope(run_dir: Path, layer: str) -> Set[str]:
    return {i["id"] for i in load_registry(run_dir) if i["kind"] == "crosswalk" and i.get("layer") == layer}


def layer_inputs(run_dir: Path, log=print) -> List[Path]:
    """synthesis/layers/<L>_input.md: every crosswalk row for the layer, every theme brief's Layer Implications and
    Numbers of Record, the layer's definition and lenses."""
    reg = load_registry(run_dir)
    out_dir = syn(run_dir, "layers")
    out_dir.mkdir(parents=True, exist_ok=True)
    names = dict(zip(LAYERS, rl.canonical_layers()))
    const = rl.CONSTITUTION.read_text(encoding="utf-8")
    lenses = (rl.ROOT / "methodology" / "INVESTOR_LENSES.md").read_text(encoding="utf-8")
    briefs = sorted(syn(run_dir, "themes").glob("T[0-9].md"))
    paths = []
    for L in LAYERS:
        n = L[1]
        rows = sorted((i for i in reg if i["kind"] == "crosswalk" and i.get("layer") == L),
                      key=lambda i: (i["author"], rl.CROSSWALK_FIELDS.index(i["field"]) if i.get("field") in rl.CROSSWALK_FIELDS else 9))
        m = re.search(r"^### Layer %s .*?(?=^### |\Z)" % n, const, re.M | re.S)
        lens = [l for l in lenses.splitlines() if l.startswith("| L%s " % n)]
        lines = ["# Layer input — %s (run %s)" % (names[L], rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id")), "",
                 "The layer analyst's input (methodology/SYNTHESIS.md). Disposition every crosswalk row (`R-…`) below in "
                 "your Crosswalk Disposition Register.", "", "## The layer", "", (m.group(0).strip() if m else names[L]), ""]
        lines += ["Lenses: %s" % l for l in lens] + [""]
        lines += ["## Crosswalk rows (%d)" % len(rows), ""]
        for i in rows:
            lines.append("### %s · %s · %s\n%s:%s\n> %s\n" % (i["id"], i["author"], i.get("field"), i["file"], i["line"], i["text"]))
        for b in briefs:
            text = b.read_text(encoding="utf-8")
            li = rl.section(text, "Layer Implications") or ""
            nor = rl.section(text, "Numbers of Record") or ""
            lines += ["## Theme %s — layer implications" % b.stem, "", li.strip() or "(none)", "",
                      "### Theme %s — numbers of record" % b.stem, "", nor.strip() or "(none)", ""]
        path = out_dir / ("%s_input.md" % L)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(path)
    log("layer inputs: %s" % ", ".join(str(p.relative_to(run_dir)) for p in paths))
    return paths


def check_layer(run_dir: Path, layer: str) -> List[str]:
    errs: List[str] = []
    draft = syn(run_dir, "layers", "%s_draft.md" % layer)
    if not draft.exists():
        return ["synthesis/layers/%s_draft.md does not exist yet" % layer]
    text = draft.read_text(encoding="utf-8")
    res = rl.Result(str(draft))
    rl.check_sections(text, rl.read_block(SYNTHESIS_MD, "LAYER_DRAFT_SECTIONS"), res)
    errs += res.errors
    body = rl.section(text, "Layer Assessment") or ""
    for f in rl.LAYER_BLOCK_FIELDS:
        if not re.search(r"\*\*%s:?\*\*" % re.escape(f), body):
            errs.append("Layer Assessment: the labelled item **%s:** is missing" % f)
    fit = re.search(r"Proposed layer-fit score:\**\s*\**\s*(\d{1,3})\s*/\s*100", text)
    if not fit:
        errs.append("Proposed Layer Fit: write 'Proposed layer-fit score: NN/100'")
    if not re.search(r"Proposed confidence:\**\s*\**\s*(High|Medium|Low)", text):
        errs.append("Proposed Layer Fit: write 'Proposed confidence: High|Medium|Low'")
    if fit and int(fit.group(1)) >= 41:
        m = re.search(r"\*\*Current-price assessment:?\*\*:?\s*(.*?)(?=\n\s*[-*]?\s*\*\*|\Z)", body, re.S)
        if not m or len(re.findall(r"\w+", m.group(1))) < 15:
            errs.append("a proposed fit of 41 or more needs a current-price assessment")
    scope = layer_scope(run_dir, layer)
    rows = register_rows(text, "Crosswalk Disposition Register")
    got = {r[0] for r in rows}
    vocab = set(dispositions())
    reg_by_id = {i["id"]: i for i in load_registry(run_dir)}
    known, clusters = known_claim_ids(run_dir), cluster_ids(run_dir)
    for rid, disp, ptr, reason in rows:
        if rid not in scope:
            errs.append("%s: not a crosswalk row of %s" % (rid, layer))
        if disp not in vocab:
            errs.append("%s: disposition %r is not one of %s" % (rid, disp, ", ".join(sorted(vocab))))
        if disp == "immaterial" and len(re.findall(r"\w+", reason)) < 10:
            errs.append("%s: immaterial needs a reason of at least ten words" % rid)
        if disp in ("superseded", "unverified_lead"):
            errs += ["%s: %s" % (rid, e) for e in pointer_errors(rid, disp, ptr, reason, reg_by_id, known, clusters)]
    newest = max((b.stat().st_mtime for b in theme_briefs(run_dir)), default=0)
    if draft.stat().st_mtime < newest:
        errs.append("a theme brief changed after this draft was written: re-run the layers step")
    missing = sorted(scope - got)
    if missing:
        errs.append("%d crosswalk row(s) without a disposition: %s" % (len(missing), ", ".join(missing[:20])))
    common_checks(run_dir, draft, errs)
    return errs[:120]


def layers_blocked(run_dir: Path) -> List[str]:
    """What must be true before the layer analysts start (cio.md Stage 3: evidence, contradictions and follow-ups first)."""
    if stale(run_dir):
        return ["the registry is stale: run the themes step"]
    out = ["theme %s: %s" % (t, e) for t in active_themes(run_dir) for e in check_theme(run_dir, t)[:2]]
    out += ["contradiction candidate %s is not adjudicated" % c
            for c in followups(run_dir, log=lambda m: None, write=False)["open_candidates"]]
    out += ["%s still needs a follow-up" % rid for rid, d in all_dispositions(run_dir).items()
            if d["disposition"] == "needs_follow_up"]
    return out


def writers_blocked(run_dir: Path) -> List[str]:
    """What must be true before the section writers start: every layer draft current, and the CIO's scorecard."""
    out = ["layer %s: %s" % (L, e) for L in LAYERS for e in check_layer(run_dir, L)[:2]]
    if not (run_dir / "cio" / "scorecard.json").exists():
        out.append("the CIO's scorecard does not exist yet")
    return out


def answer_waiting(run_dir: Path, subject: str) -> bool:
    """A theme whose brief passes its own check must still run again when one of its follow-ups has been answered, or a
    needs_follow_up disposition can never close (the answer may be routed to another theme by its author)."""
    b = syn(run_dir, "themes", "%s.md" % subject)
    if not b.exists() or "needs_follow_up" not in b.read_text(encoding="utf-8"):
        return False
    return any(p.stat().st_mtime > b.stat().st_mtime for p in (run_dir / "specialists").glob("*_followup_*.md"))


def group_findings(run_dir: Path, group: dict) -> Dict[str, Set[str]]:
    """'T1-F3' -> the claim IDs of that Integrated Finding, for the themes feeding a section group."""
    out = {}
    for tid in group.get("themes", []):
        b = syn(run_dir, "themes", "%s.md" % tid)
        if not b.exists():
            continue
        for fid, ftxt in findings_of(b.read_text(encoding="utf-8")).items():
            out["%s-%s" % (tid, fid)] = set(rl.CLAIM_ID_RE.findall(ftxt))
    return out


def check_section(run_dir: Path, wid: str) -> List[str]:
    groups = writer_groups()
    if wid not in groups:
        return ["%s is not a section group (%s)" % (wid, ", ".join(groups))]
    g = groups[wid]
    draft = syn(run_dir, "sections", "%s.md" % wid)
    if not draft.exists():
        return ["synthesis/sections/%s.md does not exist yet" % wid]
    text = draft.read_text(encoding="utf-8")
    errs: List[str] = []
    res = rl.Result(str(draft))
    rl.check_sections(text, list(g["sections"]) + ["Not Carried"], res)
    errs += res.errors
    cited = set(rl.CLAIM_ID_RE.findall(text))
    nc = rl.section(text, "Not Carried") or ""
    for key, ids in group_findings(run_dir, g).items():
        tid, fid = key.split("-", 1)
        listed = re.search(r"\b%s\b.*\b%s\b|\b%s\b" % (tid, fid, re.escape(key)), nc)
        if not (ids & cited) and not listed:
            errs.append("%s (%s) is neither cited (its claims: %s) nor listed under Not Carried with a reason" % (
                key, tid, ", ".join(sorted(ids)[:5]) or "none"))
    common_checks(run_dir, draft, errs)
    return errs[:120]


LOG_FIELDS = ("Specialist positions", "Independent check", "Resolution", "Confidence", "Investment impact")


def log_block(log_text: str, needle: str) -> str:
    """The contradiction-log entry holding this id: from the heading above it to the next heading."""
    lines = log_text.splitlines()
    at = next((n for n, l in enumerate(lines) if needle in l), None)
    if at is None:
        return ""
    head = next((n for n in range(at, -1, -1) if re.match(r"#{2,4}\s", lines[n])), None)
    if head is None:
        return lines[at]
    end = next((n for n in range(head + 1, len(lines)) if re.match(r"#{2,4}\s", lines[n])), len(lines))
    return "\n".join(lines[head:end])


def filled(block: str, field: str) -> str:
    """A labelled field's text, or "" when it is absent or still the template's placeholder."""
    m = re.search(r"\*\*%s[^*]*:?\*\*:?\s*(.*)" % re.escape(field), block)
    value = (m.group(1) if m else "").strip()
    return "" if not value or set(value) <= set("…. ") else value


def adjudication_gaps(log_text: str, cid: str) -> List[str]:
    """What the log's entry for a contradiction candidate still lacks (cio.md Stage 3): empty means adjudicated."""
    block = log_block(log_text, cid)
    if not block:
        return ["no entry"]
    gaps = [f for f in LOG_FIELDS if not filled(block, f)]
    check = filled(block, "Independent check")
    if check and not re.search(r"\bCIO-C\d+", check):
        gaps.append("the independent check cites no CIO claim")
    return gaps


def conflict_adjudicated(log_text: str, claim_ids: List[str]) -> bool:
    """A numeric conflict is adjudicated by a log entry holding one of its claims and stating a resolution."""
    return any(filled(log_block(log_text, c), "Resolution") for c in claim_ids)


def followups(run_dir: Path, log=print, write: bool = True) -> dict:
    """Open follow-up requests and the contradiction candidates the CIO's log does not yet address."""
    log_text = (run_dir / "cio" / "contradiction_log.md").read_text(encoding="utf-8") if (run_dir / "cio" / "contradiction_log.md").exists() else ""
    fus, ccs = [], []
    for b in theme_briefs(run_dir):
        text = b.read_text(encoding="utf-8")
        for line in (rl.section(text, "Gaps and Follow-up Requests") or "").splitlines():
            m = re.search(r"\b(FU-T\d-\d+)\b", line)
            if m and m.group(1) not in {f["id"] for f in fus}:
                fus.append({"id": m.group(1), "theme": b.stem, "text": norm(line)[:400]})
        for line in (rl.section(text, "Contradiction Candidates") or "").splitlines():
            m = re.search(r"\b(CC-T\d-\d+)\b", line)
            if m and m.group(1) not in {c["id"] for c in ccs}:
                ccs.append({"id": m.group(1), "theme": b.stem, "text": norm(line)[:400],
                            "in_log": not adjudication_gaps(log_text, m.group(1))})
    out = {"followups": fus, "contradiction_candidates": ccs,
           "open_candidates": [c["id"] for c in ccs if not c["in_log"]]}
    lines = ["# Follow-ups and contradiction candidates", "",
             "## Contradiction candidates (%d; %d not yet in cio/contradiction_log.md)" % (len(ccs), len(out["open_candidates"])), ""]
    lines += ["- %s%s — %s" % (c["id"], "" if c["in_log"] else " **(not in the log)**", c["text"]) for c in ccs]
    lines += ["", "## Follow-up requests (%d)" % len(fus), ""] + ["- %s — %s" % (f["id"], f["text"]) for f in fus]
    if write:
        syn(run_dir, "FOLLOWUPS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("follow-ups: %d requests; contradiction candidates %d (%d not in the log) -> synthesis/FOLLOWUPS.md" % (
        len(fus), len(ccs), len(out["open_candidates"])))
    return out


# ------------------------------------------------------------------------------------------------------------------
# the final stage: the CIO's packet, assembly, the integration checks and the register
# ------------------------------------------------------------------------------------------------------------------

REGISTER_BLOCK = "INTEGRATION_REGISTER"
REGISTER_SECTION = "Evidence Integration Register"


def all_dispositions(run_dir: Path) -> Dict[str, dict]:
    """id -> {disposition, pointer, reason, file, f_claims (claim IDs of the finding it was integrated into)}."""
    out = {}
    files = sorted(syn(run_dir, "themes").glob("T*.md")) + sorted(syn(run_dir, "layers").glob("L*_draft.md"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        fs = findings_of(text)
        heading = "Crosswalk Disposition Register" if f.name.endswith("_draft.md") else "Disposition Register"
        for rid, disp, ptr, reason in register_rows(text, heading):
            out[rid] = {"disposition": disp, "pointer": ptr, "reason": reason, "file": f.name,
                        "f_claims": sorted(set(rl.CLAIM_ID_RE.findall(fs.get(ptr, "")))) if disp == "integrated" else []}
    return out


def body_without_register(text: str) -> str:
    return re.sub(r"<!--\s*%s:BEGIN\s*-->.*?<!--\s*%s:END\s*-->" % (REGISTER_BLOCK, REGISTER_BLOCK), " ", text, flags=re.S)


def register_block_of(text: str) -> Optional[str]:
    m = re.search(r"<!--\s*%s:BEGIN\s*-->(.*?)<!--\s*%s:END\s*-->" % (REGISTER_BLOCK, REGISTER_BLOCK), text, re.S)
    return m.group(1).strip() if m else None


COMMON_CLAIM_ITEMS = 3     # a claim cited by this many report items or more is context (price, revenue), not a finding's own


def common_claims(reg: List[dict]) -> Set[str]:
    """Claims too widely cited to show that one particular finding reached the report: the CIO's (price, shares) and any
    claim that this many report items or more cite."""
    from collections import Counter
    n = Counter(c for i in reg if i.get("kind") != "ledger_claim" for c in set(i.get("claim_ids") or []))
    return {c for c, k in n.items() if k >= COMMON_CLAIM_ITEMS} | {
        c for i in reg for c in i.get("claim_ids") or [] if rl.agent_of_prefix(c) == "cio"}


def gating_missing(it: dict, cited: Set[str], common: Set[str] = frozenset()) -> Set[str]:
    """The claims of a gating item the body does not cite: every distinctive claim must be cited (a finding that folds
    several facts together, or cites the price or the revenue line in passing, must not let its own evidence vanish
    while a shared claim is cited); with no distinctive claim, any one of its claims will do."""
    own = set(it.get("claim_ids") or [])
    dist = own - set(common)
    if dist:
        return dist - cited
    return set() if own & cited else own


def reached(it: dict, disp: dict, cited: Set[str], common: Set[str] = frozenset(), body: str = "") -> bool:
    """Did the item reach the report's body? A gating item with claims of its own reaches it only through them, all of
    its distinctive ones (gating_missing); any other item through one of its claims or the claims of the finding it was
    integrated into. An item with no claims contested in a candidate reaches it through that candidate."""
    own = set(it.get("claim_ids") or [])
    if not own and disp.get("disposition") == "contested" and disp.get("pointer") and disp["pointer"] in body:
        return True
    if it.get("materiality") == "gating" and own:
        return not gating_missing(it, cited, common)
    if own & cited:
        return True
    return bool(set(disp.get("f_claims") or []) & cited)


def quantity(token: str) -> str:
    """A printed number as its value: 1,000.00 and 1000 are the same quantity."""
    v = token.replace(",", "")
    return v.rstrip("0").rstrip(".") if "." in v else v


def key_quantity_errors(text: str, kq: List[dict]) -> List[str]:
    """Every line that names a key quantity (label or alias) and prints numbers must print its recorded value."""
    errs = []
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":        # the front matter is built from the scorecard, not written
        start = next((n + 1 for n, l in enumerate(lines[1:], 1) if l.strip() == "---"), 0)
    for q in kq or []:
        names = [q.get("label", "")] + list(q.get("aliases") or [])
        names = [n.lower() for n in names if n and len(n) >= 4]
        want = set(map(quantity, re.findall(r"\d[\d,]*(?:\.\d+)?", str(q.get("value", "")))))
        if not names or not want:
            continue
        pats = [re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(nm)) for nm in names]
        for n, line in enumerate(lines[start:], start + 1):
            low = line.lower()
            if not any(p.search(low) for p in pats):
                continue
            found = re.findall(r"\d[\d,]*(?:\.\d+)?", rl.CLAIM_ID_RE.sub(" ", line))
            nums = {quantity(x) for x in found if not re.fullmatch(r"(19|20)\d\d", x)}
            if nums and not want <= nums:
                errs.append("line %d states %r with %s, not its recorded value %r (key_quantities)" % (
                    n, q.get("label"), ", ".join(sorted(nums)[:6]), q.get("value")))
    return errs


def dimension_owner_errors(run_dir: Path, sc: dict) -> List[str]:
    """Each scored dimension's cited claims reach (directly or through the claim graph) a claim of an owning specialist."""
    import claim_graph
    owners = rl.dimension_owners()
    g = claim_graph.build(run_dir, write=False)
    errs = []
    for block in ("business_quality", "investment_attractiveness"):
        for d in (sc.get(block) or {}).get("dimensions", []) or []:
            did = d.get("id")
            if not did or did not in owners or d.get("score") is None:
                continue
            ids = set(d.get("claim_ids") or [])
            reach = set(ids)
            frontier = list(ids)
            while frontier:
                c = frontier.pop()
                for up in (g.get("inputs") or {}).get(c, []) if isinstance(g.get("inputs"), dict) else []:
                    if up not in reach:
                        reach.add(up)
                        frontier.append(up)
            agents = {rl.agent_of_prefix(c) for c in reach}
            if not agents & set(owners[did]):
                errs.append("%s rationale cites no claim of its evidence owners (%s), directly or through the claims it "
                            "cites" % (did, ", ".join(owners[did])))
    return errs


def consistency_errors(run_dir: Path, text: str, reg: List[dict]) -> List[str]:
    errs = []
    low_lines = [(n, l.lower()) for n, l in enumerate(text.splitlines(), 1)]
    for rule in consistency_rules():
        have = [i for i in reg if i.get("type") in rule.get("when_types", [])
                or (i["kind"] != "corpus_item" and any(tp.replace("_", " ") in i["text"].lower() for tp in rule.get("when_types", [])))]
        if not have:
            continue
        if rule.get("forbid"):
            for n, l in low_lines:
                if re.search(rule["forbid"], l) and not (rule.get("unless") and rule["unless"] in l):
                    errs.append("line %d: %s (%s)" % (n, rule["message"], rule["id"]))
        if rule.get("require_any") and not any(any(r in l for r in rule["require_any"]) for _, l in low_lines):
            errs.append("%s (%s)" % (rule["message"], rule["id"]))
    return errs


def tieout_exceptions(run_dir: Path) -> Set[str]:
    p = run_dir / "qc" / "tieout_exceptions.csv"
    if not p.exists():
        return set()
    with p.open(encoding="utf-8", newline="") as f:
        return {str(r.get("line", "")).strip() for r in csv.DictReader(f) if (r.get("classification") or "").strip()}


def uptake(run_dir: Path, reg: List[dict], disp: Dict[str, dict], cited: Set[str]) -> List[dict]:
    rows = []
    common = common_claims(reg)
    for name in rl.specialists_for(run_version(run_dir)):
        kf = [i for i in reg if i["author"] == name and i["kind"] == "key_finding"]
        claims = [i for i in reg if i["author"] == name and i["kind"] == "ledger_claim"]
        cw = [i for i in reg if i["author"] == name and i["kind"] == "crosswalk"]
        rows.append({"specialist": name, "key_findings": len(kf),
                     "key_findings_reached": sum(1 for i in kf if reached(i, disp.get(i["id"], {}), cited, common)),
                     "claims": len(claims), "claims_cited": sum(1 for i in claims if set(i["claim_ids"]) & cited),
                     "crosswalk_rows": len(cw),
                     "crosswalk_integrated": sum(1 for i in cw if disp.get(i["id"], {}).get("disposition") == "integrated")})
    return rows


def integration(run_dir: Path, write: bool = True) -> dict:
    """The final-stage integration checks (validate_run.py --stage final, methodology 3.2.0) and the Evidence Integration
    Register (synthesis/INTEGRATION.md, carried unchanged into the final report)."""
    errs, warns = [], []
    st = stale(run_dir)
    if st:
        errs.append("the registry is stale (changed: %s): re-run synthesis.py registry and the theme step" % ", ".join(st[:6]))
    if not syn(run_dir, "registry.jsonl").exists():
        return {"errors": ["no registry (synthesis.py registry)"], "warnings": [], "register": ""}
    reg = load_registry(run_dir)
    for tid in active_themes(run_dir):
        errs += ["theme %s: %s" % (tid, e) for e in check_theme(run_dir, tid)]
    for L in LAYERS:
        errs += ["layer %s: %s" % (L, e) for e in check_layer(run_dir, L)]
    for w in writer_groups():
        errs += ["section %s: %s" % (w, e) for e in check_section(run_dir, w)]
    disp = all_dispositions(run_dir)
    for rid, d in disp.items():
        if d["disposition"] == "needs_follow_up":
            errs.append("%s still needs a follow-up (%s): close it (the follow-up's answer, then a new disposition)" % (rid, d["pointer"]))
    report = run_dir / "cio" / "final_report.md"
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    body = body_without_register(text)
    cited = set(rl.CLAIM_ID_RE.findall(body))
    log_text = (run_dir / "cio" / "contradiction_log.md").read_text(encoding="utf-8") if (run_dir / "cio" / "contradiction_log.md").exists() else ""
    for c in followups(run_dir, log=lambda m: None, write=write)["open_candidates"]:
        errs.append("contradiction candidate %s is not adjudicated in cio/contradiction_log.md" % c)
    by_id = {i["id"]: i for i in reg}
    unreached = []
    common = common_claims(reg)
    for i in reg:
        if i["materiality"] not in ("gating", "material") and i["kind"] != "key_finding":
            continue
        d = disp.get(i["id"], {})
        if reached(i, d, cited, common, body):
            continue
        unreached.append(i)
        if i["materiality"] == "gating" and d.get("disposition") not in ("superseded", "unverified_lead"):
            miss = sorted(gating_missing(i, cited, common)) if i.get("claim_ids") else []
            errs.append("gating %s %s (%s) never reaches the report's body: cite it (%s) in the section it belongs to" % (
                i["kind"], i["id"], i["author"], "its claims %s" % ", ".join(miss) if miss else
                "its claims or the finding it was integrated into"))
    sc_p = run_dir / "cio" / "scorecard.json"
    sc = rl.load_json(sc_p) if sc_p.exists() else {}
    inputs_p = run_dir / "cio" / "scorecard_inputs.json"
    kq = (rl.load_json(inputs_p).get("key_quantities") if inputs_p.exists() else None) or sc.get("key_quantities") or []
    if sc and not kq:
        errs.append("scorecard_inputs.json has no key_quantities (the decision's numbers, each with label, aliases, "
                    "value and claim IDs, so that every section states them alike)")
    if text:
        errs += key_quantity_errors(body, kq)
        errs += consistency_errors(run_dir, body, reg)
        import audit_tools
        exc = tieout_exceptions(run_dir)
        for r in audit_tools.tieout_rows(run_dir, report):
            if r["status"] in ("mismatch", "other_claim") and str(r["line"]) not in exc:
                errs.append("final report line %s: the number does not tie to the cited claim (%s; %s) — fix it, or classify "
                            "it in qc/tieout_exceptions.csv (line,classification,reason)" % (r["line"], r["status"], r["cited"][:70]))
    if sc:
        errs += dimension_owner_errors(run_dir, sc)
        for L in LAYERS:
            dp = syn(run_dir, "layers", "%s_draft.md" % L)
            m = re.search(r"Proposed layer-fit score:\**\s*\**\s*(\d{1,3})", dp.read_text(encoding="utf-8")) if dp.exists() else None
            final = (sc.get("layer_fit") or {}).get(L, {}).get("score")
            if m and final is not None and abs(int(m.group(1)) - int(final)) > 10:
                block = ""
                for head, b in rl.h3_blocks(text):
                    if layer_of(head) == L:
                        block = b
                if "deviation" not in block.lower():
                    warns.append("%s: final fit %s differs from the layer analyst's proposal %s by more than 10 points; "
                                 "state the deviation and its reason in the layer's block" % (L, final, m.group(1)))
    ups = uptake(run_dir, reg, disp, cited)
    for u in ups:
        if u["key_findings"] and u["key_findings_reached"] / u["key_findings"] < 0.5:
            warns.append("%s: only %d of %d Key Findings reach the report's body" % (u["specialist"], u["key_findings_reached"],
                                                                                   u["key_findings"]))
    lines = ["Generated by `scripts/synthesis.py integration` from the evidence registry (%d items) and the dispositions "
             "of the theme and layer analysts. Reading mode: %s." % (len(reg), rl.reading_mode(run_dir)), "",
             "| Specialist | Key findings reaching the report | Claims cited | Crosswalk rows integrated |", "|---|---|---|---|"]
    for u in ups:
        lines.append("| %s | %d of %d | %d of %d | %d of %d |" % (u["specialist"], u["key_findings_reached"], u["key_findings"],
                                                              u["claims_cited"], u["claims"], u["crosswalk_integrated"],
                                                              u["crosswalk_rows"]))
    lines += ["", "Material evidence not cited in the report's body, with its fate (%d):" % len(unreached), "",
              "| Item | Kind | Source | What it says | Disposition | Reason or pointer |", "|---|---|---|---|---|---|"]
    for i in sorted(unreached, key=lambda i: ({"gating": 0, "material": 1}.get(i["materiality"], 2), i["author"])):
        d = disp.get(i["id"], {})
        lines.append("| %s | %s%s | %s | %s | %s | %s |" % (
            i["id"], i["kind"], " (gating)" if i["materiality"] == "gating" else "", i["author"],
            rl.CLAIM_ID_RE.sub("", i["text"]).replace("|", "/")[:160], d.get("disposition", "**none**"),
            (d.get("reason") or d.get("pointer") or "").replace("|", "/")[:160]))
    register = "\n".join(lines)
    if write:
        syn(run_dir).mkdir(parents=True, exist_ok=True)
        syn(run_dir, "INTEGRATION.md").write_text(register + "\n", encoding="utf-8")
        (run_dir / "qc").mkdir(exist_ok=True)
        rl.write_json(run_dir / "qc" / "integration.json", {"errors": errs, "warnings": warns, "uptake": ups,
                                                             "unreached": [i["id"] for i in unreached]})
    if text:
        blk = register_block_of(text)
        if blk is None:
            errs.append("the final report has no Evidence Integration Register block (<!-- %s:BEGIN --> ... END): re-run "
                        "synthesis.py assemble" % REGISTER_BLOCK)
        elif re.sub(r"\s+", " ", blk) != re.sub(r"\s+", " ", register.strip()):
            errs.append("the Evidence Integration Register in the report differs from synthesis/INTEGRATION.md: re-run "
                        "synthesis.py assemble")
    else:
        errs.append("cio/final_report.md does not exist yet (synthesis.py assemble)")
    return {"errors": errs, "warnings": warns, "register": register, "uptake": ups}


def packet(run_dir: Path, log=print) -> Path:
    """synthesis/CIO_PACKET.md: what the CIO decides from — every theme's summary, contradiction candidates, dimension
    evidence and numbers of record; every immaterial disposition (so none hides a finding); the layer analysts'
    proposals; numeric conflicts; open follow-ups; the gap register. Bounded by PACKET_BUDGET."""
    reg = load_registry(run_dir)
    disp = all_dispositions(run_dir)
    by_id = {i["id"]: i for i in reg}
    out = ["# CIO packet — run %s" % rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id"), "",
           "Built by `scripts/synthesis.py packet`. Decide from this, open the briefs and reports for detail. %d of %d "
           "registry items have a disposition; the immaterial ones are listed below so that none hides a finding." % (
               sum(i["id"] in disp or i.get("cluster") in disp for i in reg), len(reg)), ""]
    for b in sorted(syn(run_dir, "themes").glob("T[0-9].md")):
        text = b.read_text(encoding="utf-8")
        out += ["## Theme %s" % b.stem, ""]
        for sec in ("Theme Summary for the CIO", "Contradiction Candidates", "Dimension Evidence", "Numbers of Record",
                    "Gaps and Follow-up Requests"):
            s = (rl.section(text, sec) or "").strip()
            out += ["### %s" % sec, "", s or "(none)", ""]
    main_text = "\n".join(b.read_text(encoding="utf-8") for b in sorted(syn(run_dir, "themes").glob("T[0-9].md")))
    only_parts = [c for c in followups(run_dir, log=lambda m: None, write=False)["contradiction_candidates"]
                  if c["id"] not in main_text]
    if only_parts:
        out += ["## Contradiction candidates raised only in part briefs (%d)" % len(only_parts), ""]
        out += ["- %s (%s) %s" % (c["id"], c["theme"], c["text"]) for c in only_parts] + [""]
    layers_done = [L for L in LAYERS if syn(run_dir, "layers", "%s_draft.md" % L).exists()]
    out += ["## Layer analysts' proposals", ""]
    if len(layers_done) < len(LAYERS):
        out += ["Not all four drafts exist yet: run `synthesis.py packet` again after the layers step.", ""]
    for L in LAYERS:
        dp = syn(run_dir, "layers", "%s_draft.md" % L)
        if dp.exists():
            text = dp.read_text(encoding="utf-8")
            out += ["### %s" % L, "", (rl.section(text, "Proposed Layer Fit") or "").strip(), ""]
    imm = [(rid, d) for rid, d in disp.items() if d["disposition"] == "immaterial"]
    out += ["## Immaterial dispositions (%d)" % len(imm), "", "| Item | Author | What it says | Reason |", "|---|---|---|---|"]
    for rid, d in imm:
        i = by_id.get(rid, {})
        out.append("| %s | %s | %s | %s |" % (rid, i.get("author", "cluster"), (i.get("text") or rid).replace("|", "/")[:140],
                                            d["reason"].replace("|", "/")[:160]))
    fu = followups(run_dir, log=lambda m: None)
    out += ["", "## Open contradiction candidates (%d) and follow-up requests (%d)" % (len(fu["open_candidates"]), len(fu["followups"])),
            "", "See synthesis/FOLLOWUPS.md.", ""]
    nc = [i for i in reg if i["kind"] == "numeric_conflict"]
    out += ["## Numeric conflicts (%d)" % len(nc), ""] + ["- %s %s" % (i["id"], i["text"][:220]) for i in nc] + [""]
    gr = run_dir / "cio" / "gap_register.md"
    if gr.exists():
        out += ["## Gap register", "", gr.read_text(encoding="utf-8").strip(), ""]
    text = "\n".join(out) + "\n"
    path = syn(run_dir, "CIO_PACKET.md")
    path.write_text(text, encoding="utf-8")
    tok = est_tokens(len(text))
    log("CIO packet: ≈%s tokens%s -> %s" % (format(tok, ","), " (ABOVE the %s budget: read it in parts)" % format(PACKET_BUDGET, ",")
                                            if tok > PACKET_BUDGET else "", path))
    return path


def h2_blocks(text: str) -> List[Tuple[str, str]]:
    ms = list(re.finditer(r"^##\s+(?!#)(.+)$", text, re.M))
    return [(m.group(1).strip(), text[m.start(): ms[k + 1].start() if k + 1 < len(ms) else len(text)].rstrip() + "\n")
            for k, m in enumerate(ms)]


def front_matter(run_dir: Path, sc: dict) -> str:
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)

    def show(v):
        return "not issued" if v is None else v
    bq, ia = sc.get("business_quality") or {}, sc.get("investment_attractiveness") or {}
    price = sc.get("price") or {}
    sec = sc.get("secondary_layers") or []
    fm = [("company", m.get("company")), ("ticker", m.get("ticker")), ("exchange", m.get("exchange")),
          ("run_id", m.get("run_id")), ("as_of_date", m.get("research_cutoff")), ("research_cutoff", m.get("research_cutoff")),
          ("price", price.get("value")), ("price_timestamp", "%s (%s)" % (price.get("timestamp"), price.get("claim_id", "CIO-C001"))),
          ("currency", m.get("currency")), ("primary_layer", sc.get("primary_layer") or "None"),
          ("secondary_layers", ", ".join(sec) if isinstance(sec, list) and sec else (sec or "None")),
          ("business_quality", show(bq.get("final"))), ("business_quality_confidence", bq.get("confidence")),
          ("investment_attractiveness", show(ia.get("final"))), ("investment_attractiveness_confidence", ia.get("confidence")),
          ("verdict", show(sc.get("verdict"))), ("valuation_status", sc.get("valuation_status")),
          ("assessment_status", sc.get("assessment_status")), ("qc_status", sc.get("qc_status")),
          ("model_effective", (m.get("model") or {}).get("effective_cio") or "unverified")]
    return "---\n" + "".join("%s: %s\n" % (k, v) for k, v in fm) + "---\n"


def assemble(run_dir: Path, log=print) -> List[str]:
    """cio/final_report.md from the section files: the CIO's (cio/sections/*.md) and the writers'
    (synthesis/sections/W*.md, without their Not Carried tables), in the contract's order, with the front matter from the
    scorecard, the coverage record in the Contradiction and Evidence Audit section and the generated Evidence Integration
    Register. The report is a build artifact: edit the section files and assemble again."""
    sc_p = run_dir / "cio" / "scorecard.json"
    if not sc_p.exists():
        return ["cio/scorecard.json does not exist yet"]
    sc = rl.load_json(sc_p)
    blocks: Dict[str, Tuple[str, str]] = {}
    errs = []
    sources = sorted((run_dir / "cio" / "sections").glob("*.md")) + sorted(syn(run_dir, "sections").glob("W*.md"))
    for f in sources:
        for head, body in h2_blocks(f.read_text(encoding="utf-8")):
            key = rl.norm_heading(head)
            if key == "not carried":
                continue
            if key in blocks:
                errs.append("section %r is written twice (%s and %s)" % (head, blocks[key][0], f.name))
            blocks[key] = (f.name, body)
    required = rl.final_sections_for(run_version(run_dir))
    if str(rl.load_json(run_dir / rl.RUN_MANIFEST).get("segment", "")).lower() == "sme":
        required = required + [rl.SME_SECTION]
    out = [front_matter(run_dir, sc)]
    for s in required:
        key = rl.norm_heading(s)
        if key == rl.norm_heading(REGISTER_SECTION):
            reg = integration(run_dir, write=True)["register"]
            out.append("## %s\n\n<!-- %s:BEGIN -->\n%s\n<!-- %s:END -->\n" % (REGISTER_SECTION, REGISTER_BLOCK, reg, REGISTER_BLOCK))
            continue
        if key not in blocks:
            errs.append("no section file writes %r (cio/sections/ for the CIO's sections, synthesis/sections/ for the writers')" % s)
            continue
        body = blocks.pop(key)[1]
        if key == rl.norm_heading("Contradiction and Evidence Audit") and rl.coverage_block_of(body) is None:
            cov = run_dir / rl.coverage_rel(run_dir)
            if cov.exists():
                body += "\n<!-- %s:BEGIN -->\n%s\n<!-- %s:END -->\n" % (rl.COVERAGE_BLOCK, cov.read_text(encoding="utf-8").strip(),
                                                                         rl.COVERAGE_BLOCK)
        out.append(body)
    for key, (f, _) in blocks.items():
        errs.append("section %r (in %s) is not a section of the final report" % (key, f))
    report = run_dir / "cio" / "final_report.md"
    report.write_text("\n".join(out), encoding="utf-8")
    # the register in the report must equal INTEGRATION.md: regenerate now that the body exists
    reg = integration(run_dir, write=True)["register"]
    text = report.read_text(encoding="utf-8")
    text = re.sub(r"(<!--\s*%s:BEGIN\s*-->).*?(<!--\s*%s:END\s*-->)" % (REGISTER_BLOCK, REGISTER_BLOCK),
                  lambda m_: "%s\n%s\n%s" % (m_.group(1), reg, m_.group(2)), text, flags=re.S)
    report.write_text(text, encoding="utf-8")
    log("assembled cio/final_report.md from %d section file(s)%s" % (len(sources), "; %d problem(s)" % len(errs) if errs else ""))
    return errs


def restatements(run_dir: Path, n: int, out: Path, seed: str = "auditor") -> List[dict]:
    """A reproducible sample of report lines that cite specialist claims, each beside the ledger row and the specialist's
    own sentence: for the auditor to judge whether the report restates the evidence faithfully."""
    import random
    report = run_dir / "cio" / "final_report.md"
    text = body_without_register(report.read_text(encoding="utf-8")) if report.exists() else ""
    ledger = ledger_rows_by_id(run_dir)
    cand = []
    for k, line in enumerate(text.splitlines(), 1):
        ids = [c for c in rl.CLAIM_ID_RE.findall(line) if rl.agent_of_prefix(c) in rl.SPECIALISTS]
        if ids:
            cand.append((k, line.strip(), ids))
    rng = random.Random(seed)
    rng.shuffle(cand)
    rows = []
    for k, line, ids in cand[:n]:
        c = ids[0]
        r = ledger.get(c, {})
        spec_line = ""
        rep = run_dir / "specialists" / ("%s.md" % rl.agent_of_prefix(c))
        if rep.exists():
            spec_line = next((l.strip() for l in rep.read_text(encoding="utf-8").splitlines() if c in l), "")
        rows.append({"report_line": k, "report_text": line[:400], "claim_id": c, "ledger_claim": r.get("claim", "")[:300],
                     "ledger_value": "%s %s %s" % (r.get("value", ""), r.get("unit", ""), r.get("period", "")),
                     "specialist_text": spec_line[:400], "result": "", "notes": ""})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["report_line"])
        w.writeheader()
        w.writerows(rows)
    print("restatement sample: %d report lines -> %s (fill `result`: Faithful | Overstated | Understated | Wrong)" % (len(rows), out))
    return rows


# ------------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("registry")
    r.add_argument("run_dir")
    r.add_argument("--update", action="store_true", help="rebuild after follow-ups (ids of unchanged items are kept)")
    sub.add_parser("status").add_argument("run_dir")
    sub.add_parser("layer-inputs").add_argument("run_dir")
    sub.add_parser("followups").add_argument("run_dir")
    sub.add_parser("packet").add_argument("run_dir")
    sub.add_parser("assemble").add_argument("run_dir")
    ig = sub.add_parser("integration")
    ig.add_argument("run_dir")
    ig.add_argument("--out", help="also write the result here (the auditor: audit/integration.json)")
    rs = sub.add_parser("restatements")
    rs.add_argument("run_dir")
    rs.add_argument("--n", type=int, default=15)
    rs.add_argument("--out")
    for name, what in (("check-theme", "theme"), ("check-layer", "layer"), ("check-section", "group")):
        c = sub.add_parser(name)
        c.add_argument("run_dir")
        c.add_argument(what)
        if name == "check-theme":
            c.add_argument("--part", type=int, help="only part k of a theme split into parts")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "registry":
        build_registry(run_dir)
        return 0
    if a.cmd == "status":
        st = stale(run_dir)
        print("registry: %s" % ("current" if not st else "STALE: %s" % ", ".join(st[:10])))
        return 1 if st else 0
    if a.cmd == "layer-inputs":
        layer_inputs(run_dir)
        return 0
    if a.cmd == "followups":
        out = followups(run_dir)
        return 1 if out["open_candidates"] else 0
    if a.cmd == "packet":
        packet(run_dir)
        return 0
    if a.cmd == "assemble":
        errs = assemble(run_dir)
        print("\n".join(errs) if errs else "assemble: PASS")
        return 1 if errs else 0
    if a.cmd == "integration":
        res = integration(run_dir, write=not a.out)
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            rl.write_json(Path(a.out), {k: v for k, v in res.items() if k != "register"})
        for w_ in res["warnings"]:
            print("warn: %s" % w_)
        print("\n".join(res["errors"]) if res["errors"] else "integration: PASS")
        return 1 if res["errors"] else 0
    if a.cmd == "restatements":
        seed = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", "auditor")
        restatements(run_dir, a.n, Path(a.out) if a.out else run_dir / "audit" / "restatements.csv", seed)
        return 0
    errs = {"check-theme": lambda: check_theme(run_dir, a.theme, a.part), "check-layer": lambda: check_layer(run_dir, a.layer),
            "check-section": lambda: check_section(run_dir, a.group)}[a.cmd]()
    print("\n".join(errs) if errs else "%s: PASS" % a.cmd)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
