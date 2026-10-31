#!/usr/bin/env python3
"""The web digest (methodology 3.2.0, `reading_mode` off; cio.md Stage 0c).

With the reading stage switched off, the `digest` agent collects web summaries of the company's annual reports,
earnings-call transcripts and investor presentations (third-party AR digests, concall summaries, broker and results
notes). Every summary it uses is a snapshot (fetch_source.py --snapshot) opened in its own session, and every item it
records quotes that snapshot. Those items are tier-6 LEADS, never FACT. This script then tries to find each item's
number (or wording) on a page of the filing Stage 0 already downloaded, and marks it page-confirmed (the page a
specialist opens and cites) or a lead. The output has the shape of the reading stage's dossiers and packs, so the
specialists and the synthesis consume one structure in either mode.

  python3 scripts/digest.py plan      RUN_DIR [--years 10] [--quarters 24] [--ppt-quarters 12]
  python3 scripts/digest.py check     RUN_DIR [--doc KEY]          # the agent's check (schema, snapshots, quotes, search log)
  python3 scripts/digest.py confirm   RUN_DIR                      # page-confirm items against the Stage-0 text layers
  python3 scripts/digest.py build     RUN_DIR                      # topic files, packs, entities, events, COVERAGE.md
  python3 scripts/digest.py status    RUN_DIR [--strict]
  python3 scripts/digest.py sample    RUN_DIR [--n 15] [--out audit/digest_sample.csv]
  python3 scripts/digest.py calibrate RUN_DIR --reference OTHER_RUN_DIR   # recall against a run that read the same pages

Files (all under RUN_DIR/corpus/digest/): plan.json and PLAN.md, items/<doc>.jsonl (the agent writes them),
SEARCH_LOG.md (the agent: one row per planned document), confirmations.jsonl, <topic>.md and <topic>.reference.md,
packs/<specialist>.md, entities.md, events.md, events_check.json, INDEX.md, COVERAGE.md, status.json.
Exit: 0 ok, 1 errors (check) or incomplete (status --strict), 2 usage.
"""

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import reading  # noqa: E402

DIGEST = rl.DIGEST_DIR
SOURCE_KINDS = ("ar_digest", "concall_summary", "presentation_summary", "results_summary", "broker_note", "news", "other")
CONFIRM_STATUSES = ("page_confirmed", "value_located", "conflict", "not_found", "no_document")
PROVENANCE = {"page_confirmed": "digest_page_confirmed", "value_located": "digest_value_located",
              "conflict": "digest_conflict"}
ITEM_KEYS = ("type", "fields", "period", "doc_key", "basis", "source_url", "snapshot", "snapshot_page", "quote",
             "publisher", "source_kind", "tier")
EXTRA_FIELDS = {"unit_of_amount", "unit_of_value", "period_label"}
# What to look for in each kind of document (topics of methodology/READING_SCHEMAS.md).
DOC_TOPICS = {
    "annual_report": ("auditor", "accounting", "contingencies", "related_parties", "debt_and_capital",
                      "results_and_segments", "structure_and_transactions", "governance", "strategy_and_outlook", "esg",
                      "other"),
    "transcript": ("transcripts", "strategy_and_outlook", "results_and_segments", "other"),
    "investor_presentation": ("results_and_segments", "strategy_and_outlook", "debt_and_capital", "other"),
}
HEAD = ("Run %s · built by `scripts/digest.py build` from the web digest (reading stage OFF). **Every item is a tier-6 "
        "LEAD taken from a web summary, never a FACT.** ✓ marks an item whose number or wording a script found on a page of "
        "the filing downloaded in Stage 0: open that page (`doc_text.py page`) and cite the document and page. Items "
        "without ✓ are leads to confirm in a primary source before you rely on them. A finding aid, not a source.")


def dpath(run_dir: Path, *parts: str) -> Path:
    return run_dir.joinpath(DIGEST, *parts)


def load_plan(run_dir: Path) -> dict:
    p = dpath(run_dir, "plan.json")
    if not p.exists():
        raise SystemExit("no digest plan: run digest.py plan %s" % run_dir)
    return rl.load_json(p)


def schema() -> dict:
    return reading.schema()


def company(run_dir: Path) -> str:
    return str(rl.load_json(run_dir / rl.RUN_MANIFEST).get("company") or "")


# ------------------------------------------------------------------------------------------------------------------
# plan
# ------------------------------------------------------------------------------------------------------------------

def plan(run_dir: Path, years: int = 10, quarters: int = 24, ppt_quarters: int = 12, log=print) -> dict:
    """One row per in-scope document of the Stage-0 document map: the latest `years` annual reports, `quarters`
    transcript quarters and `ppt_quarters` presentation quarters (also those whose exchange filing is only a cover
    letter: the web is where their content is found), with the item types to look for and suggested searches."""
    path = run_dir / "corpus" / "document_map.csv"
    if not path.exists():
        raise SystemExit("no document map: run document_map.py build first (cio.md Stage 0)")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    sch = schema()
    want = {"annual_report": years, "transcript": quarters, "investor_presentation": ppt_quarters}
    name = company(run_dir)
    docs = []
    for dtype, n in want.items():
        sub = sorted((r for r in rows if r["doc_type"] == dtype), key=lambda r: reading.period_order(r["period"]),
                     reverse=True)[:n]
        for r in sorted(sub, key=lambda r: reading.period_order(r["period"])):
            key = "%s-%s" % (reading.PREFIX[dtype], r["period"])
            types = sorted(t for t, spec in sch["types"].items() if spec["topic"] in DOC_TOPICS[dtype] and t != "table")
            label = "%s %s" % (reading.LABEL[dtype], r["period"])
            flags = r.get("flags") or ""
            queries = {"annual_report": ['"%s" annual report %s highlights' % (name, r["period"]),
                                         '"%s" %s auditor key audit matters contingent liabilities' % (name, r["period"])],
                       "transcript": ['"%s" %s earnings call summary' % (name, r["period"]),
                                      '"%s" %s concall key takeaways guidance' % (name, r["period"])],
                       "investor_presentation": ['"%s" %s investor presentation highlights' % (name, r["period"]),
                                                 '"%s" %s results AUM NIM credit cost' % (name, r["period"])]}[dtype]
            docs.append({"key": key, "doc_type": dtype, "period": r["period"], "label": label,
                         "filed": r.get("filed", ""), "url": r.get("primary_url", ""),
                         "text": r.get("text_path", ""), "pages": r.get("cached_pages") or r.get("local_pages") or "",
                         "status": r.get("status", ""), "cover_letter_only": "short_document" in flags,
                         "types": types, "queries": queries})
    out = {"created_at": reading.now_iso(), "run_id": rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id"),
           "scope": {"years": years, "quarters": quarters, "ppt_quarters": ppt_quarters}, "documents": docs}
    dpath(run_dir).mkdir(parents=True, exist_ok=True)
    (dpath(run_dir, "items")).mkdir(exist_ok=True)
    rl.write_json(dpath(run_dir, "plan.json"), out)
    lines = ["# Digest plan — run %s" % out["run_id"], "",
             "Reading stage OFF. For each document below, find web summaries of it (search the web; open each page you use "
             "and snapshot it with `fetch_source.py URL --snapshot`), and record every instance of the listed item types "
             "they state, one JSON line each in `corpus/digest/items/<key>.jsonl` (schema: `.claude/agents/digest.md`). "
             "Record every document in `corpus/digest/SEARCH_LOG.md`, also when nothing was found.", "",
             "| Key | Document | Filed | Text layer | Note | Suggested searches |", "|---|---|---|---|---|---|"]
    for d in docs:
        lines.append("| %s | %s | %s | %s | %s | %s |" % (d["key"], d["label"], d["filed"] or "-", "yes" if d["text"] else "no",
                                                         "exchange filing is a cover letter only" if d["cover_letter_only"] else "",
                                                         " · ".join(d["queries"])))
    dpath(run_dir, "PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("digest plan: %d documents (%d annual reports, %d transcripts, %d presentations) -> %s" % (
        len(docs), sum(d["doc_type"] == "annual_report" for d in docs), sum(d["doc_type"] == "transcript" for d in docs),
        sum(d["doc_type"] == "investor_presentation" for d in docs), reading.rel(run_dir, dpath(run_dir, "PLAN.md"))))
    return out


# ------------------------------------------------------------------------------------------------------------------
# items and the agent's check
# ------------------------------------------------------------------------------------------------------------------

def item_id(doc_key: str, it: dict) -> str:
    raw = "|".join([doc_key, str(it.get("type")), str(it.get("source_url")), str(it.get("snapshot_page")),
                    reading.norm_space(str(it.get("quote") or ""))[:400],
                    json.dumps(it.get("fields") or {}, sort_keys=True, ensure_ascii=False)])
    return "D-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def load_items(run_dir: Path) -> List[Tuple[str, int, dict]]:
    """(file key, line number, item) for every line of corpus/digest/items/*.jsonl (bad JSON yields {"_bad": text})."""
    out = []
    for f in sorted(dpath(run_dir, "items").glob("*.jsonl")) if dpath(run_dir, "items").exists() else []:
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                it = json.loads(line)
            except ValueError:
                it = {"_bad": line[:120]}
            out.append((f.stem, n, it if isinstance(it, dict) else {"_bad": line[:120]}))
    return out


def snapshot_rows(run_dir: Path) -> Dict[str, dict]:
    """local_path -> retrieval row, for every successful page snapshot of the run."""
    p = run_dir / "source_retrievals.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8", newline="") as f:
        return {r["local_path"]: r for r in csv.DictReader(f)
                if r.get("method") == "chrome-snapshot" and r.get("local_path") and not r.get("error")}


def pdf_pages_text(run_dir: Path, pdf: Path) -> Dict[int, str]:
    """Page -> text of a PDF, through the run's text layer (doc_text.py), converted once and cached."""
    import doc_text
    try:
        meta = doc_text.meta_for(run_dir, pdf)
    except Exception:                       # noqa: BLE001 (a broken snapshot is reported by the caller)
        return {}
    return {p["page"]: doc_text.page_text(meta, p["page"], p["page"]) for p in meta.get("page_index", [])}


def search_log_keys(run_dir: Path) -> Dict[str, str]:
    """Document key -> the result cell of its row in SEARCH_LOG.md (a markdown table: | doc | queries | sources | items | result |)."""
    p = dpath(run_dir, "SEARCH_LOG.md")
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|") or re.match(r"^\|\s*:?-{2,}", line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] and cells[0].lower() not in ("doc", "document", "key"):
            out[cells[0].strip("`*")] = cells[-1] if len(cells) > 1 else ""
    return out


def _digits(s: str) -> str:
    return re.sub(r"[^\d.]", "", str(s).replace(",", ""))


def _value(s: str) -> Optional[Decimal]:
    """A printed number's value (commas ignored), or None when the string is not one number."""
    try:
        return Decimal(_digits(s).strip("."))
    except InvalidOperation:
        return None


def amount_in(text: str, value: str) -> bool:
    """A recorded amount appears in a text, compared by value: 25,000 matches 25000.00 and never 2,500."""
    v = _digits(value).strip(".")
    if not v or not re.search(r"\d", v):
        return True
    nums = {_digits(n).strip(".") for n in reading.NUMBER_RE.findall(text)}
    target = _value(value)
    return v in nums or (target is not None and target in {x for x in map(_value, nums) if x is not None})


def scaled_amount_in(text: str, value: str) -> bool:
    """The same significant digits at another scale: a unit conversion or a ten-times error, which a script cannot tell
    apart, so it is reported and never confirmed."""
    sig = lambda s: re.sub(r"\D", "", _digits(s)).strip("0")  # noqa: E731
    v = sig(value)
    return bool(v) and v in {sig(n) for n in reading.NUMBER_RE.findall(text)}


def check_errors(run_dir: Path, doc: Optional[str] = None, tdir: Optional[Path] = None,
                 doc_type: Optional[str] = None) -> List[str]:
    """The digest agent's check: every planned document has a search-log row; every item follows the schema, quotes a
    snapshot of a web page that the run logged and the agent opened in its own session, its quote is printed on the
    snapshot page it names, and every amount it records is in its quote."""
    pl = load_plan(run_dir)
    keys = {d["key"] for d in pl["documents"]}
    scope = {d["key"] for d in pl["documents"] if doc_type is None or d["doc_type"] == doc_type}
    if doc is not None:
        scope = {doc}
    sch = schema()
    errs = []
    if doc is None and scope and not any(fkey in scope for fkey, _, _ in load_items(run_dir)):
        errs.append("no item recorded for any of the %d documents of this job: the search-log rows alone do not make a "
                    "digest" % len(scope))
    log_rows = search_log_keys(run_dir)
    if not dpath(run_dir, "SEARCH_LOG.md").exists():
        errs.append("corpus/digest/SEARCH_LOG.md does not exist yet: one row per planned document "
                    "(| doc | queries run | sources opened | items | result |)")
    for k in sorted(scope):
        if k not in log_rows:
            errs.append("%s: no row in SEARCH_LOG.md (record the searches you ran, also when nothing was found)" % k)
        elif not log_rows[k].strip():
            errs.append("%s: its SEARCH_LOG.md row has an empty result cell" % k)
    snaps = snapshot_rows(run_dir)
    import verify
    sessions = verify.agent_sessions(run_dir, "digest", tdir)
    seen = verify.Seen(sessions) if sessions else None
    page_cache: Dict[str, Dict[int, str]] = {}
    for fkey, n, it in load_items(run_dir):
        if fkey != "web" and fkey not in scope and fkey in keys:
            continue
        where = "items/%s.jsonl line %d" % (fkey, n)
        if "_bad" in it:
            errs.append("%s: not a JSON object: %s" % (where, it["_bad"]))
            continue
        if fkey not in keys and fkey != "web":
            errs.append("%s: the file must be named after a planned document key (or web.jsonl)" % where)
        missing = [k for k in ITEM_KEYS if k not in it or it[k] in (None, "")]
        if missing:
            errs.append("%s: missing %s" % (where, ", ".join(missing)))
            continue
        spec = sch["types"].get(it["type"])
        if not spec or it["type"] == "table":
            errs.append("%s: type %r is not an item type of methodology/READING_SCHEMAS.md" % (where, it["type"]))
            continue
        if not isinstance(it["fields"], dict):
            errs.append("%s: fields must be an object" % where)
            continue
        unknown = set(it["fields"]) - set(spec["fields"]) - EXTRA_FIELDS
        if unknown:
            errs.append("%s: fields %s are not fields of %s (%s)" % (where, sorted(unknown), it["type"], ", ".join(spec["fields"])))
        if it["doc_key"] != fkey:
            errs.append("%s: doc_key %r differs from its file %s" % (where, it["doc_key"], fkey))
        if it["source_kind"] not in SOURCE_KINDS:
            errs.append("%s: source_kind %r is not one of %s" % (where, it["source_kind"], ", ".join(SOURCE_KINDS)))
        if str(it["tier"]) != "6":
            errs.append("%s: tier must be 6 (a web summary is a lead, whatever its publisher)" % where)
        url = str(it["source_url"])
        if not re.match(r"^https?://", url):
            errs.append("%s: source_url must be the http(s) address of the page summarised" % where)
        elif seen is not None and not seen.opened({url, re.sub(r"^https?://", "", url).rstrip("/")}):
            errs.append("%s: its source page was never opened in your session (%s)" % (where, url[:90]))
        snap = str(it["snapshot"])
        snap_rel = snap if not snap.startswith(str(run_dir)) else reading.rel(run_dir, snap)
        if snap_rel not in snaps:
            errs.append("%s: snapshot %s is not a logged page snapshot of this run (fetch_source.py URL --snapshot)" % (where, snap[:90]))
            continue
        if snaps[snap_rel].get("url") != url and snaps[snap_rel].get("final_url") != url:
            errs.append("%s: the snapshot was taken of %s, not of source_url" % (where, snaps[snap_rel].get("url", "?")[:90]))
        if snap_rel not in page_cache:
            page_cache[snap_rel] = pdf_pages_text(run_dir, run_dir / snap_rel)
        pages = page_cache[snap_rel]
        try:
            pg = int(it["snapshot_page"])
        except (TypeError, ValueError):
            errs.append("%s: snapshot_page must be a page number" % where)
            continue
        if pg not in pages:
            errs.append("%s: snapshot_page %s is not a page of the snapshot (%d pages)" % (where, pg, len(pages)))
            continue
        import doc_text
        quote = str(it["quote"])
        if len(quote) < 12:
            errs.append("%s: quote too short: copy the sentence(s) of the summary that state the item" % where)
        elif doc_text.squash(quote) not in doc_text.squash(pages[pg]):
            errs.append("%s: the quote is not printed on snapshot page %d: copy it word for word" % (where, pg))
        for a in spec["amounts"]:
            v = str((it["fields"] or {}).get(a, "")).strip()
            if v and not amount_in(quote, v):
                errs.append("%s: %s %r is not in the quote (record numbers exactly as the summary prints them)" % (where, a, v))
    return errs[:80]


# ------------------------------------------------------------------------------------------------------------------
# confirm: look for each item on a page of the downloaded filing
# ------------------------------------------------------------------------------------------------------------------

LABEL_STOP = set(reading.EVENT_STOP) | set("total other others net gross current prior previous during period quarter "
                                           "ended march june september december annual report standalone consolidated "
                                           "amount amounts value values".split())


def label_tokens(it: dict, spec: dict) -> List[str]:
    toks = []
    for k, v in (it.get("fields") or {}).items():
        if k in spec["amounts"] or k in EXTRA_FIELDS:
            continue
        toks += [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z&-]{3,}", str(v))]
    return [t for t in dict.fromkeys(toks) if t not in LABEL_STOP][:8]


def doc_pages(run_dir: Path, doc: dict) -> Dict[int, List[str]]:
    """Page -> lines of a planned document's Stage-0 text layer (empty if it has none)."""
    if not doc.get("text"):
        return {}
    tp = Path(doc["text"]) if Path(doc["text"]).is_absolute() else run_dir / doc["text"]
    meta_p = tp.parent / "meta.json"
    if not meta_p.exists():
        return {}
    import doc_text
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    return {p["page"]: doc_text.page_text(meta, p["page"], p["page"]).splitlines() for p in meta.get("page_index", [])}


def confirm_item(it: dict, spec: dict, pages: Dict[int, List[str]]) -> dict:
    """page_confirmed: the amount (or, for an item without amounts, its wording) on a page next to its label (±3 lines);
    value_located: the amount on a page but not next to its label; conflict: its label on a line printing other numbers
    and not the amount; not_found; no_document (no text layer)."""
    if not pages:
        return {"status": "no_document"}
    toks = label_tokens(it, spec)
    amounts = [str(it["fields"].get(a, "")).strip() for a in spec["amounts"] if str(it["fields"].get(a, "")).strip()]
    amounts = [a for a in amounts if re.search(r"\d", a)]
    located = None
    conflict = None
    for pg, lines in sorted(pages.items()):
        low = [l.lower() for l in lines]
        for i, line in enumerate(lines):
            if amounts:
                if not any(amount_in(line, a) for a in amounts):
                    if conflict is None and len(toks) >= 2 and sum(t in low[i] for t in toks) >= 2 and reading.NUMBER_RE.search(line):
                        conflict = {"page": pg, "line": i + 1, "matched": line.strip()[:160]}
                        if any(scaled_amount_in(line, a) for a in amounts):
                            conflict["scale_differs"] = True
                    continue
                window = " ".join(low[max(0, i - 3): i + 4])
                hits = sum(t in window for t in toks)
                if hits >= min(2, len(toks)) and toks:
                    return {"status": "page_confirmed", "page": pg, "line": i + 1, "matched": line.strip()[:160]}
                if located is None:
                    located = {"status": "value_located", "page": pg, "line": i + 1, "matched": line.strip()[:160]}
            else:
                if len(toks) >= 2:
                    window = " ".join(low[max(0, i - 2): i + 3])
                    if sum(t in window for t in toks) >= min(3, len(toks)):
                        return {"status": "page_confirmed", "page": pg, "line": i + 1, "matched": line.strip()[:160]}
    if located:
        return located
    if conflict:
        return dict(conflict, status="conflict")
    return {"status": "not_found"}


def confirm(run_dir: Path, log=print) -> dict:
    pl = load_plan(run_dir)
    docs = {d["key"]: d for d in pl["documents"]}
    sch = schema()
    page_cache: Dict[str, Dict[int, List[str]]] = {}
    out_rows, counts = [], Counter()
    for fkey, n, it in load_items(run_dir):
        if "_bad" in it or it.get("type") not in sch["types"]:
            continue
        spec = sch["types"][it["type"]]
        d = docs.get(it.get("doc_key"))
        if d is None:
            res = {"status": "no_document"}
        else:
            if d["key"] not in page_cache:
                page_cache[d["key"]] = doc_pages(run_dir, d)
            res = confirm_item(it, spec, page_cache[d["key"]])
            if d.get("text") and res.get("page"):
                res["text"] = d["text"]
        counts[res["status"]] += 1
        out_rows.append(dict(res, id=item_id(fkey, it), doc_key=it.get("doc_key"), file=fkey, line=n))
    p = dpath(run_dir, "confirmations.jsonl")
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows), encoding="utf-8")
    log("digest confirm: %d items: %s -> %s" % (len(out_rows), ", ".join("%s %d" % (s, counts[s]) for s in CONFIRM_STATUSES
                                                                       if counts[s]), reading.rel(run_dir, p)))
    return dict(counts)


def confirmations(run_dir: Path) -> Dict[str, dict]:
    p = dpath(run_dir, "confirmations.jsonl")
    if not p.exists():
        return {}
    return {r["id"]: r for r in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())}


def digest_items(run_dir: Path) -> List[dict]:
    """Every valid item with its id, confirmation and provenance flag (the synthesis registry's OFF-mode adapter)."""
    sch = schema()
    conf = confirmations(run_dir)
    out = []
    for fkey, n, it in load_items(run_dir):
        if "_bad" in it or it.get("type") not in sch["types"] or it.get("type") == "table":
            continue
        iid = item_id(fkey, it)
        c = conf.get(iid, {"status": "not_found"})
        out.append(dict(it, id=iid, file=fkey, line=n, confirm=c,
                        provenance=PROVENANCE.get(c.get("status"), "digest_unconfirmed_lead")))
    return out


# ------------------------------------------------------------------------------------------------------------------
# build: topic files, packs, entities, events, index, coverage
# ------------------------------------------------------------------------------------------------------------------

def digest_line(it: dict) -> str:
    fields = "; ".join("%s: %s" % (k, v) for k, v in (it.get("fields") or {}).items() if str(v).strip())
    c = it.get("confirm") or {}
    mark = {"page_confirmed": " ✓ **%s p.%s** (page-confirmed)", "value_located": " value found on %s p.%s, label not "
            "next to it (lead)", "conflict": " ⚠ conflict: %s p.%s prints other numbers for this label (lead)"}.get(c.get("status"))
    where = (mark % (it.get("doc_key"), c.get("page"))) if mark else " (lead: not found in the filing)" \
        if c.get("status") == "not_found" else " (lead: no text layer)"
    return "- **%s** · %s · %s — \"%s\" `[%s, %s · snapshot p.%s]`%s" % (
        it["type"], it.get("period") or "-", fields or "-", reading.norm_space(str(it.get("quote") or ""))[:400],
        it.get("publisher"), it.get("source_kind"), it.get("snapshot_page"), where)


def events_check_off(run_dir: Path, pl: dict, items: List[dict], log=print) -> dict:
    """The historian's events against what the run holds with reading off: the digest items and the Stage-0 text layers
    of that fiscal year's documents (and the next year's annual report). Same scoring as reading.events_check."""
    path = run_dir / "corpus" / "events.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        events = list(csv.DictReader(f))
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    fy_end = int(str(m.get("fy_end") or "03-31")[:2]) if re.match(r"\d{2}-\d{2}", str(m.get("fy_end") or "")) else 3
    by_fy = defaultdict(list)
    for d in pl["documents"]:
        by_fy[reading.doc_fiscal_year(d, fy_end)].append(d)
    blobs: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for it in items:
        blobs[it.get("doc_key")].append(((str(it.get("quote") or "") + " " + " ".join(str(v) for v in (it.get("fields") or {}).values())).lower(),
                                         "digest item %s" % it["id"]))
    for d in pl["documents"]:
        for pg, lines in doc_pages(run_dir, d).items():
            blobs[d["key"]].append((" ".join(lines).lower(), "%s p.%s" % (d["key"], pg)))
    results = []
    for e in events:
        fy = int(re.sub(r"\D", "", e.get("fiscal_year") or "0") or 0)
        docs = by_fy.get(fy, []) + [d for d in by_fy.get(fy + 1, []) if d["doc_type"] == "annual_report"]
        names = [x.strip().lower() for x in (e.get("entities") or "").split(";") if len(x.strip()) >= 4]
        words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z&-]{4,}", e.get("event") or "")} - reading.EVENT_STOP
        nums = {re.sub(r"\D", "", n).strip("0") for n in reading.NUMBER_RE.findall((e.get("amount") or "") + " " + (e.get("event") or ""))}
        nums = {n for n in nums if len(n) >= 3 and not re.fullmatch(r"(19|20)\d\d", n)}
        best = []
        for d in docs:
            for blob, where in blobs.get(d["key"], []):
                digits = {re.sub(r"\D", "", n).strip("0") for n in reading.NUMBER_RE.findall(blob)}
                score = 2 * sum(1 for n in names if n in blob) + sum(1 for w in words if w in blob) + 3 * len(nums & digits)
                if score >= 3:
                    best.append((score, where))
        best.sort(reverse=True)
        status = "outside_reading" if not docs else ("matched" if best else "unmatched")
        results.append(dict(e, status=status, matches=[w for _, w in best[:3]]))
    out = {"events": len(results), "matched": sum(r["status"] == "matched" for r in results),
           "unmatched": sum(r["status"] == "unmatched" for r in results),
           "outside_reading": sum(r["status"] == "outside_reading" for r in results), "rows": results}
    rl.write_json(run_dir / rl.events_check_rel(run_dir), out)
    order = {"unmatched": 0, "outside_reading": 1, "matched": 2}
    lines = ["# Events: the outside view against the documents — run %s" % pl["run_id"], "",
             "The historian's timeline (`corpus/EVENTS.md`) checked against the web digest and the text of that year's "
             "filings (reading stage OFF: the filings were searched by script, not read). **Leads, not evidence.** An event "
             "**not found** is a lead for its owning specialist: confirm it in a primary source, or record that the company "
             "did not disclose it.", "",
             "%d events: %d found, **%d not found**, %d before the documents' window." % (
                 out["events"], out["matched"], out["unmatched"], out["outside_reading"]), "",
             "| Event | Date | Category | What happened | Source | Found in |", "|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (order[r["status"]], r.get("date", ""))):
        found = {"unmatched": "**not found**", "outside_reading": "before the window"}.get(r["status"]) or "; ".join(r["matches"])
        lines.append("| %s | %s | %s | %s | [%s](%s) | %s |" % (r.get("event_id"), r.get("date"), r.get("category"),
                                                            (r.get("event") or "").replace("|", "/"),
                                                            (r.get("source_title") or "source").replace("|", "/")[:60],
                                                            r.get("source_url"), found))
    dpath(run_dir, "events.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("events check (reading off): %d events, %d found, %d not found, %d before the window" % (
        out["events"], out["matched"], out["unmatched"], out["outside_reading"]))
    return out


def build(run_dir: Path, tdir: Optional[Path] = None, log=print) -> dict:
    pl = load_plan(run_dir)
    sch = schema()
    items = digest_items(run_dir)
    docs = {d["key"]: d for d in pl["documents"]}
    order = {d["key"]: i for i, d in enumerate(pl["documents"])}
    out_dir = dpath(run_dir)
    head = HEAD % pl["run_id"]
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    fy_end = int(str(m.get("fy_end") or "03-31")[:2]) if re.match(r"\d{2}-\d{2}", str(m.get("fy_end") or "")) else 3
    import entities as ent
    graph = ent.EntityGraph()
    series = defaultdict(dict)
    material, reference = defaultdict(list), defaultdict(list)
    for it in items:
        spec = sch["types"][it["type"]]
        d = docs.get(it.get("doc_key"), {"key": it.get("doc_key"), "label": "web", "period": it.get("period") or "",
                                         "doc_type": ""})
        graph.add(dict(it, page=(it.get("confirm") or {}).get("page")), d["key"], d["label"],
                  reading.doc_fiscal_year(dict(d, period=it.get("period") or d.get("period")), fy_end))
        topic = spec["topic"]
        vals = "; ".join(("%s %s" % (a, it["fields"][a]) if len(spec["amounts"]) > 1 else str(it["fields"][a]))
                         for a in spec["amounts"] if str(it["fields"].get(a, "")).strip())
        if it["type"] in reading.SERIES_TYPES and vals:
            key, label = reading.series_key(it, spec, it.get("doc_key", ""))
            s = series[topic].setdefault(key, {"label": label, "type": it["type"], "basis": it.get("basis", ""),
                                               "unit": key[2], "cells": defaultdict(list)})
            c = it.get("confirm") or {}
            mark = ("✓ %s p.%s" % (it["doc_key"], c.get("page"))) if c.get("status") == "page_confirmed" else "lead"
            s["cells"][str((it.get("fields") or {}).get("period_label") or it.get("period") or "-")].append(
                "%s (%s; %s)" % (vals, it.get("publisher"), mark))
        elif spec.get("material"):
            material[topic].append(it)
        else:
            reference[topic].append(it)
    index_rows = []
    for topic, meta in sch["topics"].items():
        ss = sorted(series.get(topic, {}).values(), key=lambda s: (s["type"], s["label"].lower()))
        lines = ["# Digest: %s" % meta["title"], "", head, ""]
        if ss:
            lines += ["## Series — values across periods as the web summaries state them (%d series)" % len(ss), ""]
            for s in ss:
                parts = ["%s %s" % (per, " | ".join(dict.fromkeys(v))) for per, v in
                         sorted(s["cells"].items(), key=lambda kv: reading.period_order(kv[0]), reverse=True)]
                lines.append("- **%s** · %s · %s%s: %s" % (s["label"], s["type"], s["basis"] or "-",
                                                         " · " + s["unit"] if s["unit"] else "", " · ".join(parts)))
            lines.append("")
        mat = sorted(material.get(topic, []), key=lambda r: (order.get(r.get("doc_key"), 999), str(r.get("period"))))
        lines += ["## Material items (%d)" % len(mat), ""]
        cur = None
        for r in mat:
            if r.get("doc_key") != cur:
                cur = r.get("doc_key")
                lines += ["", "### %s" % (docs[cur]["label"] if cur in docs else "Not tied to one document (web)"), ""]
            lines.append(digest_line(r))
        text = "\n".join(lines) + "\n"
        (out_dir / ("%s.md" % topic)).write_text(text, encoding="utf-8")
        ref = sorted(reference.get(topic, []), key=lambda r: (order.get(r.get("doc_key"), 999), str(r.get("period"))))
        rlines = ["# Digest reference: %s" % meta["title"], "", head, ""] + [digest_line(r) for r in ref]
        rtext = "\n".join(rlines) + "\n"
        (out_dir / ("%s.reference.md" % topic)).write_text(rtext, encoding="utf-8")
        index_rows.append((topic, meta["title"], len(ss), len(mat), len(ref), reading.est_tokens(len(text)),
                           reading.est_tokens(len(rtext)), meta["owners"]))
    ev = events_check_off(run_dir, pl, items, log=log)
    ev_tok = reading.est_tokens(len(dpath(run_dir, "events.md").read_text(encoding="utf-8"))) if ev else 0
    graph.finish()
    ev_rows = []
    if (run_dir / "corpus" / "events.csv").exists():
        with (run_dir / "corpus" / "events.csv").open(encoding="utf-8", newline="") as f:
            ev_rows = list(csv.DictReader(f))
    etext = graph.markdown(pl["run_id"], head, ev_rows)
    (out_dir / "entities.md").write_text(etext, encoding="utf-8")
    ent_tok, ent_n = reading.est_tokens(len(etext)), len(graph.entities)
    packs = out_dir / "packs"
    packs.mkdir(exist_ok=True)
    version = rl.version_tuple(m.get("methodology_version"))
    for name in rl.specialists_for(version):
        mine = [r for r in index_rows if name in r[7]]
        lines = ["# Digest pack — %s (run %s)" % (name, pl["run_id"]), "",
                 "**Reading stage OFF.** Read in full (the reading audit checks it): the digest topic files you own. They "
                 "are web summaries of the company's reports, transcripts and presentations: tier-6 leads. Open the page "
                 "of every ✓ item you use and cite the document and page; confirm every other item in a primary source "
                 "before relying on it; and research the filings and the web as your definition requires.", "",
                 "| Topic file (read in full) | Contents | Series | Material items | ≈ tokens |", "|---|---|---|---|---|"]
        lines += ["| `%s/%s.md` | %s | %d | %d | %d |" % (DIGEST, r[0], r[1], r[2], r[3], r[5]) for r in mine]
        if name in reading.ENTITY_OWNERS:
            lines.append("| `%s/entities.md` | Companies and people named in the digest items | - | %d | %d |" % (DIGEST, ent_n, ent_tok))
        if ev:
            lines.append("| `%s/events.md` | The company's major events from news and the web, checked against the digest "
                         "and the filings' text (%d not found) | - | %d | %d |" % (DIGEST, ev["unmatched"], ev["events"], ev_tok))
        lines += ["", "Reference (search it; not required in full):", ""]
        lines += ["- %s/%s.reference.md — %d items, ≈ %s tokens" % (DIGEST, r[0], r[4], format(r[6], ",")) for r in mine]
        lines += ["", "What the digest covered: `%s`." % rl.DIGEST_COVERAGE]
        (packs / ("%s.md" % name)).write_text("\n".join(lines) + "\n", encoding="utf-8")
    counts = Counter((it.get("confirm") or {}).get("status", "not_found") for it in items)
    idx = ["# Digest index — run %s" % pl["run_id"], "", head, "",
           "%d items from web summaries; %d page-confirmed. What was covered: `%s`." % (
               len(items), counts["page_confirmed"], rl.DIGEST_COVERAGE), "",
           "| Topic | Contents | Series | Material items | ≈ tokens | Reference items | ≈ tokens | Owners |",
           "|---|---|---|---|---|---|---|---|"]
    idx += ["| [%s](%s.md) | %s | %d | %d | %d | %d | %d | %s |" % (t_, t_, title, ns, nm, tok, nr, rtok, ", ".join(own))
            for t_, title, ns, nm, nr, tok, rtok, own in index_rows]
    (out_dir / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    return write_status(run_dir, pl, items, tdir=tdir, log=log)


def write_status(run_dir: Path, pl: dict, items: List[dict], tdir: Optional[Path] = None, log=print) -> dict:
    """COVERAGE.md (what the digest covered, per document) and status.json (complete when every planned document has a
    search-log row and the check passes)."""
    log_rows = search_log_keys(run_dir)
    per = defaultdict(Counter)
    for it in items:
        per[it.get("doc_key")][(it.get("confirm") or {}).get("status", "not_found")] += 1
        per[it.get("doc_key")]["items"] += 1
    errs = check_errors(run_dir, tdir=tdir)
    pending = [d["key"] for d in pl["documents"] if d["key"] not in log_rows]
    lines = ["Reading stage OFF: no page was read by readers. The documents below were covered by web summaries "
             "(tier-6 leads), and each summary's numbers and wording were searched for by script in the filing's text "
             "(page-confirmed: found on the page next to its label).", "",
             "| Document | Text layer | Search log | Items | Page-confirmed | Value located | Conflict | Not found |",
             "|---|---|---|---|---|---|---|---|"]
    for d in pl["documents"]:
        c = per.get(d["key"], Counter())
        lines.append("| %s | %s | %s | %d | %d | %d | %d | %d |" % (
            d["key"], "yes" if d.get("text") else "no", (log_rows.get(d["key"]) or "**missing**")[:60].replace("|", "/"),
            c["items"], c["page_confirmed"], c["value_located"], c["conflict"], c["not_found"] + c["no_document"]))
    web = per.get("web", Counter())
    tot = Counter()
    for c in per.values():
        tot.update(c)
    lines += ["", "Totals: %d documents, %d items (%d not tied to one document), %d page-confirmed, %d value located, "
              "%d conflicts, %d not found." % (len(pl["documents"]), tot["items"], web["items"], tot["page_confirmed"],
                                               tot["value_located"], tot["conflict"], tot["not_found"] + tot["no_document"])]
    text = "\n".join(lines) + "\n"
    dpath(run_dir, "COVERAGE.md").write_text(text, encoding="utf-8")
    conf = confirmations(run_dir)
    unconfirmed = sum(1 for it in items if it["id"] not in conf)
    st = {"complete": not pending and not errs and not unconfirmed, "pending": len(pending), "pending_documents": pending,
          "check_errors": len(errs), "documents": len(pl["documents"]), "items": tot["items"], "unconfirmed": unconfirmed,
          "page_confirmed": tot["page_confirmed"], "coverage_sha256": hashlib.sha256(text.encode()).hexdigest(),
          "built_at": reading.now_iso()}
    rl.write_json(run_dir / rl.DIGEST_STATUS, st)
    log("digest build: %d documents, %d items, %d page-confirmed; %s" % (
        st["documents"], st["items"], st["page_confirmed"],
        "complete" if st["complete"] else "INCOMPLETE (%d documents without a search-log row, %d check errors)" % (
            len(pending), len(errs))))
    return st


# ------------------------------------------------------------------------------------------------------------------
# sample (auditor) and calibrate (recall against a run that read the same pages)
# ------------------------------------------------------------------------------------------------------------------

def sample(run_dir: Path, n: int, out: Path, seed: str = "auditor") -> List[dict]:
    """Page-confirmed items first (open the page: is the number there, with that label?), then leads: a reproducible
    sample for the auditor's check that no digest lead reached the report as FACT and that confirmations hold."""
    items = digest_items(run_dir)
    rng = random.Random(seed)
    conf = [i for i in items if i["confirm"].get("status") == "page_confirmed"]
    other = [i for i in items if i["confirm"].get("status") != "page_confirmed"]
    rng.shuffle(conf)
    rng.shuffle(other)
    chosen = conf[: max(1, (2 * n) // 3)] + other[: n - min(len(conf), max(1, (2 * n) // 3))]
    rows = [{"id": i["id"], "doc_key": i.get("doc_key"), "type": i["type"], "period": i.get("period"),
             "fields": json.dumps(i.get("fields"), ensure_ascii=False), "confirm": i["confirm"].get("status"),
             "page": i["confirm"].get("page", ""), "source_url": i.get("source_url"), "result": "", "notes": ""}
            for i in chosen[:n]]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    print("digest sample: %d items -> %s (fill `result`: Confirmed | Wrong page | Not on page | Lead cited as FACT)" % (
        len(rows), out))
    return rows


def calibrate(run_dir: Path, reference: Path, log=print) -> dict:
    """Recall of the digest against a run whose readers read the same documents: of the reference's material items (on
    the pages it read), the share for which the digest holds an item of the same type and period (and, where the type
    has amounts, the same number). Measures what reading off loses; never a reason to cite a digest item."""
    items = digest_items(run_dir)
    rp = reading.load_json(reference / reading.READING / "plan.json")
    if not rp:
        raise SystemExit("the reference run has no reading plan")
    pol = reading.run_policy(reference)
    sch = schema()
    docs = {d["key"]: d for d in rp["documents"]}
    have = defaultdict(list)
    for it in items:
        have[(it.get("doc_key"), it["type"])].append(it)
    tot, hit, by_type = 0, 0, defaultdict(lambda: [0, 0])
    for c in rp["chunks"]:
        for it in reading.final_items(reference, c, pol):
            spec = sch["types"].get(it.get("type"))
            if not spec or not spec.get("material") or it.get("type") == "table":
                continue
            tot += 1
            by_type[it["type"]][0] += 1
            cands = have.get((c["doc"], it["type"]), [])
            amounts = [str((it.get("fields") or {}).get(a, "")) for a in spec["amounts"] if str((it.get("fields") or {}).get(a, "")).strip()]
            ok = bool(cands) if not amounts else any(any(amount_in(json.dumps(x.get("fields")), a) for a in amounts) for x in cands)
            if ok:
                hit += 1
                by_type[it["type"]][1] += 1
    res = {"reference": str(reference), "material_items": tot, "found": hit, "recall": round(hit / tot, 3) if tot else None,
           "by_type": {k: {"items": v[0], "found": v[1]} for k, v in sorted(by_type.items())},
           "documents_compared": sorted({c["doc"] for c in rp["chunks"]} & {d for d, _ in have})}
    rl.write_json(dpath(run_dir, "calibration.json"), res)
    log("digest calibration against %s: %s of %s material items found (recall %s)" % (
        reference, hit, tot, res["recall"]))
    return res


# ------------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("run_dir")
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--quarters", type=int, default=24)
    p.add_argument("--ppt-quarters", type=int, default=12)
    c = sub.add_parser("check")
    c.add_argument("run_dir")
    c.add_argument("--doc")
    c.add_argument("--type", choices=list(DOC_TOPICS), help="only the documents of this type")
    for name in ("confirm", "build"):
        sub.add_parser(name).add_argument("run_dir")
    s = sub.add_parser("status")
    s.add_argument("run_dir")
    s.add_argument("--strict", action="store_true")
    sm = sub.add_parser("sample")
    sm.add_argument("run_dir")
    sm.add_argument("--n", type=int, default=15)
    sm.add_argument("--out")
    cb = sub.add_parser("calibrate")
    cb.add_argument("run_dir")
    cb.add_argument("--reference", required=True)
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "plan":
        plan(run_dir, a.years, a.quarters, a.ppt_quarters)
        return 0
    if a.cmd == "check":
        errs = check_errors(run_dir, a.doc, doc_type=a.type)
        print("\n".join(errs) if errs else "digest check: PASS")
        return 1 if errs else 0
    if a.cmd == "confirm":
        confirm(run_dir)
        return 0
    if a.cmd == "build":
        st = build(run_dir)
        return 0 if st.get("complete") else 1
    if a.cmd == "status":
        p_ = run_dir / rl.DIGEST_STATUS
        st = rl.load_json(p_) if p_.exists() else {"complete": False, "pending": "?"}
        print(json.dumps(st, indent=1))
        return 1 if a.strict and not st.get("complete") else 0
    if a.cmd == "sample":
        seed = rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", "auditor")
        sample(run_dir, a.n, Path(a.out) if a.out else run_dir / "audit" / "digest_sample.csv", seed)
        return 0
    calibrate(run_dir, Path(a.reference))
    return 0


if __name__ == "__main__":
    sys.exit(main())
