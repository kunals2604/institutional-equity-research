#!/usr/bin/env python3
"""Stage 0b reading: every in-scope page read once, quote-verified, with a record that proves it.

  python3 scripts/reading.py fetch-filings RUN_DIR [--types rpt,auditor,credit_rating,penalty_order,scheme,kmp_change] [--years 10]
  python3 scripts/reading.py plan     RUN_DIR [--years 5] [--core-years 5] [--quarters 24] [--ppt-quarters 12] [--no-reuse]
  python3 scripts/reading.py accept-gap RUN_DIR AR-FY2019 --reason "<why this in-scope report cannot be had>"
  python3 scripts/reading.py next     RUN_DIR [--json] [--bakeoff]   # the next launch and its exact Agent prompt (logged)
  python3 scripts/reading.py check    RUN_DIR CHUNK --role reader|critical|resolved   # assembles the reader's parts first
  python3 scripts/reading.py render   RUN_DIR CHUNK PAGE [--dpi 150] [--rotate 0|90|180|270] [--parts 1]   # a page image
  python3 scripts/reading.py compare  RUN_DIR [CHUNK ...]        # double-read chunks: disagreements between the reads
  python3 scripts/reading.py dossiers RUN_DIR                    # topic dossiers + one reading pack per specialist
  python3 scripts/reading.py status   RUN_DIR [--strict]         # page ledger, COVERAGE.md, status.json
  python3 scripts/reading.py bakeoff  plan|score RUN_DIR [--n 12]
  python3 scripts/reading.py sample   RUN_DIR [--n 15] [--out RUN_DIR/audit/reading_sample.csv]   # the auditor's check

Why. In run BHARTIARTL 20261012T132311Z the ten agents together saw at most 11–17 % of each annual report's text
(233 of 3,310 pages had half their text reach any agent), and transcripts were read through a keyword filter, while
the reports said "annual reports read". A specialist cannot read 4–5M tokens in one context, so reading is done
here, once, in small fresh contexts (`methodology/READING_SCHEMAS.md`), and coverage is a record, not a claim.

Scope (fiscal years, not documents): every page of the annual reports of the latest `--years` fiscal years (default 5)
and the core sections (auditor's reports, CARO, IFC, statements, all notes, Board's report and its statutory annexures,
MD&A; the schema's `core` classes) of the `--core-years` before them (default 5). The latest fiscal year is the newest
report in the map or, if later, the newest one due by the cutoff (six months after the year end), so a missing recent
report is a gap, never a silently shifted window. `plan` refuses while an in-scope report is missing, until the
librarian finds it or `accept-gap` records why it cannot be had. A document read in an earlier run of the company
(same SHA-256, same reading format and schema, every read audited) is reused, not read again (`--no-reuse` to read
everything afresh).

How. Input: the text layer of every document in the document map (`doc_text.py`, page-anchored) and, with
`fetch-filings`, the exchange announcements that matter for forensic work. `plan` splits each page into passages
(prose sentences or paragraphs, table rows, and every other line of text, however short: a lone "420" or "-" in a
statement is a value), classifies them by section (auditor's report, CARO, notes, Board's report, ...; critical
classes are read twice), and marks a passage of 60 characters or more that repeats text already scheduled for
reading, in any year or section, so it is read once (its items are carried to every place it repeats). Read-once
never removes meaning: shorter text (labels, headings, column headers, names) is always read, a label followed by
its values is always read, a table row is read once only when its whole table repeats, and the repeated passage just
before new text is shown as context. Pages without a reliable text layer, pages whose raster images cover 10 % of the
page or more, and pages whose table the text layer printed one cell per line are VIEW REQUIRED: read (or confirmed)
on the rendered PDF page (`render` makes a larger or upright image). Pages are grouped into chunk files of about 16k
tokens and launches of about one chunk (small fresh contexts: a six-chunk launch peaked at 424k tokens of context);
`next` prints and logs the next launch and role (`agent_driver.py reading` runs them as headless sessions; or the
CIO through the Agent tool); each reader writes its JSONL items in parts (RUN_DIR/_cache/reading/parts/<chunk>.<role>/
01.jsonl, 02.jsonl, ...) citing a passage and a few verbatim words of it (`anchor`), and `check` assembles the parts,
attaches the printed text of the cited passages as each item's quote and verifies (the anchor is in the passage, every
number in every field is printed there, every page has a receipt). For a double-read chunk `compare` lists the
disagreements and a fresh critical-reader resolves them. `dossiers` merges the verified items into topic files across
all years, and `status` writes the page ledger: every in-scope page is read (here or, reused, in an earlier run),
repeat, structured (covered by an exchange filing), out-of-scope (core scope) or pending.

Files: RUN_DIR/corpus/reading/{plan.json, launches.json, gaps.json, ledger.csv, COVERAGE.md, status.json,
extractions/, disagreements/}, RUN_DIR/corpus/dossiers/ (committed); passages, chunk files, launch instructions,
reader parts, image shares and page renders in RUN_DIR/_cache/reading/.
Exit: 0 ok, 1 errors (check/status --strict) or nothing to do, 2 usage.
"""

import argparse
import calendar
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

READING = "corpus/reading"
DOSSIERS = "corpus/dossiers"
CACHE = "_cache/reading"
ROLES = ("critical", "reader", "resolved")
ROLE_AGENT = {"critical": "critical-reader", "reader": "reader", "resolved": "critical-reader"}
CORE_TYPES = ("annual_report", "transcript", "investor_presentation")
VISUAL_FLAGS = {"image_only", "blank_or_graphic", "rotated_text", "encoding_suspect"}   # no reliable text: read the image
VERIFY_FLAGS = {"table_numbers_mismatch", "table_alignment_uncertain", "cell_layout"}  # confirm the numbers on the image
IMAGE_FLAG = "image_content"              # text plus raster images: view the page for what only the images print
CHUNK_TOKENS = 16000
CHUNK_MAX_PAGES = 40
LAUNCH_TOKENS = 16000                     # about one chunk per launch: context grows with every chunk a launch reads
LAUNCH_MAX_CHUNKS = 4                     # (small chunks are packed together up to LAUNCH_TOKENS)
PROSE_CHARS_PER_TOKEN = 3.8
TABLE_CHARS_PER_TOKEN = 2.8
VISUAL_TOKENS = 1600
LONG_UNIT = 60                            # the shortest passage that may be read once; shorter text is always read
SPLIT_UNIT = 200
GROUP_CHARS = 700
MIN_SENTENCE = 60
IMAGE_MIN_SHARE = 0.10                    # raster images (not shared page furniture) covering this share of the page
SHARED_IMAGE_PAGES = 5                    # an image object drawn on this many pages is furniture (logo, background)
CELL_LAYOUT_MIN = 10                      # numeric-only passages on a page (and >= 25 % of them): one cell per line
CONTEXT_MAX_CHARS = 600
QUOTE_SPAN = 8                            # a quote may run on into this many following passages of the same page
ANCHOR_MAX = 300                          # an anchor is a few words of the passage, not the passage
ANCHOR_MIN_WORDS = 3                      # (or the whole passage, when it is shorter)
DEFAULT_YEARS = 5                         # every page of the latest five fiscal years' annual reports ...
DEFAULT_CORE_YEARS = 5                    # ... and the core sections of the five before them
AR_DUE_DAYS = 183                         # an annual report is due within six months of the year end (the AGM deadline)
SCHEMA_COMPATIBLE = {"1.2": ("1.1", "1.2")}   # a read under an earlier schema version that still satisfies this one
TABLE_SPAN_MAX = 600                      # passages one table tag may cover
PROSE_SPAN_MAX = 40                       # passages one item's `to` may cover
NON_KEY_WORDS = 30                        # a non-key field is a short label; longer is reported (the passage is shown)
READING_FORMAT = 2                        # bump when passages, classes, read-once or chunk files change: a document's
                                          # reading is reused across runs only within one format (and one schema)
RENDER_DPI = 150
BAKEOFF_MIN_ITEMS = 30
DEFAULT_FILING_TYPES = ("rpt", "auditor", "credit_rating", "penalty_order", "scheme", "kmp_change")
CRITICAL_FILING_TYPES = ("rpt", "auditor")
PREFIX = {"annual_report": "AR", "transcript": "TR", "investor_presentation": "PPT"}
LABEL = {"annual_report": "Annual report", "transcript": "Earnings-call transcript",
         "investor_presentation": "Investor presentation"}

# doc_text section anchors -> reading classes, and the precedence when a page carries several.
SECTION_TO_CLASS = {
    "independent_auditors_report": "auditor_report", "caro_annexure": "caro", "ifc_report": "ifc",
    "standalone_balance_sheet": "statements", "consolidated_balance_sheet": "statements",
    "standalone_pnl": "statements", "consolidated_pnl": "statements",
    "standalone_cash_flow": "statements", "consolidated_cash_flow": "statements",
    "standalone_notes": "notes", "consolidated_notes": "notes",
    "related_parties": "notes_critical", "contingent_liabilities": "notes_critical",
    "segment_information": "notes_critical",
    "mdna": "mdna", "boards_report": "board", "corporate_governance": "cg", "brsr": "brsr",
    "aoc_1": "aoc1", "aoc_2": "aoc2", "secretarial_audit": "secretarial", "remuneration": "remuneration",
    "agm_notice": "notice",
}
EXTRA_SECTIONS = [
    ("board_annex", re.compile(r"annual report on (the )?csr|csr (activities|projects)|corporate social responsibility "
                               r"(policy|activities|projects)|conservation of energy|technology absorption|"
                               r"dividend distribution policy", re.I)),
    ("remuneration", re.compile(r"particulars of employees|ratio of the remuneration of each director|median remuneration", re.I)),
    ("notice", re.compile(r"notice is hereby given|remote e-voting|instructions for (members|shareholders)", re.I)),
]
STATUTORY_STATES = ("board", "board_annex", "aoc1", "aoc2", "secretarial", "remuneration", "cg", "brsr")
PRECEDENCE = ["caro", "ifc", "auditor_report", "aoc2", "aoc1", "secretarial", "statements", "notes_critical", "notes",
              "board", "board_annex", "cg", "brsr", "remuneration", "mdna", "notice"]
FS_STATES = ("statements", "notes", "notes_critical")
NOTE_TITLE_RE = re.compile(r"^\s*(?:note\s*)?(\d{1,3}(?:\.\d{1,2})?)\s*[\.\):\-]?\s+([A-Za-z][^│]{2,100})$", re.I)


# --------------------------------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------------------------------

QUOTE_MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-", " ": " "})


TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
ABBR_END_RE = re.compile(r"(?:\b(?:p\.m|a\.m|nos?|rs|ltd|pvt|co|inc|sr|jr|mr|mrs|ms|dr|vs|viz|e\.g|i\.e|etc|approx|u\.s|govt|dept|"
                         r"cl|sec|reg|art|para|ch|vol|fig|ref|st|nd|rd|th)|\b[A-Z])\.$", re.I)


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("│", " ").replace("|", " ")).strip()


def norm_quote(s: str) -> str:
    return norm_space((s or "").translate(QUOTE_MAP))


def norm_amount(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "").translate(QUOTE_MAP).replace("│", "").replace("|", ""))


def alnum(s: str) -> int:
    return sum(1 for ch in s if ch.isalnum())


NUM_TOKEN = r"(?:\(?[-–—−]?[₹$€£]?\d[\d,]*(?:\.\d+)?%?\)?\*{0,3}|[-–—−]{1,3}|nil|n\.?a\.?)"
NUMERIC_ONLY_RE = re.compile(r"^\s*%s(?:\s+%s)*\s*$" % (NUM_TOKEN, NUM_TOKEN), re.I)
NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numeric_only(text: str) -> bool:
    """A line of values only ("420", "(1,416) (771)", "-", "Nil"): a statement cell the text layer printed apart."""
    return bool(NUMERIC_ONLY_RE.match(norm_space(text)))


def number_tokens(s) -> List[str]:
    """The numbers written in a value, commas removed ("1,23,456" -> "123456"); single digits are ignored."""
    out = []
    for m in NUMBER_RE.finditer(str(s if s is not None else "")):
        t = m.group(0).rstrip(",").replace(",", "")
        if "." in t or len(t) >= 2:
            out.append(t)
    return out


def view_pages(c: dict) -> List[int]:
    """The VIEW REQUIRED pages of a chunk (or its store): no text, numbers to confirm, or images to read."""
    return sorted(set(c.get("visual_pages", [])) | set(c.get("verify_pages", [])) | set(c.get("image_pages", [])))


def unit_id(sha12: str, page: int, k: int) -> str:
    return "u" + hashlib.sha1(("%s|%d|%d" % (sha12, page, k)).encode()).hexdigest()[:10]


def est_tokens(chars: int, table: bool = False) -> int:
    return int(chars / (TABLE_CHARS_PER_TOKEN if table else PROSE_CHARS_PER_TOKEN)) + 1


def rel(run_dir: Path, p) -> str:
    p = Path(p)
    try:
        return str(p.resolve().relative_to(run_dir.resolve()))
    except ValueError:
        return str(p)


def repo_path(run_dir: Path, p) -> str:
    """A path as the agents use it: relative to the repository root when inside it, else absolute."""
    p = Path(p)
    full = p if p.is_absolute() else run_dir / p
    try:
        return str(full.resolve().relative_to(rl.ROOT.resolve()))
    except ValueError:
        return str(full.resolve())


def run_id_of(run_dir: Path) -> str:
    return rl.load_json(run_dir / rl.RUN_MANIFEST).get("run_id", run_dir.name)


def schema() -> dict:
    return rl.reading_schema()


def compatible_schemas(sch: dict) -> tuple:
    """Schema versions whose reads this schema accepts unchanged (1.2 only made fields optional and added tables)."""
    return SCHEMA_COMPATIBLE.get(sch["schema_version"], (sch["schema_version"],))


def critical_classes(sch: dict) -> set:
    return {c for c, v in sch["classes"].items() if v.get("critical")}


def core_classes(sch: dict) -> set:
    """The sections read in the core years (the schema's `core` classes): the audit, the statements and every note,
    the Board's report and its statutory annexures, MD&A."""
    return {c for c, v in sch["classes"].items() if v.get("core")}


def fiscal_year(period: str) -> int:
    m = re.fullmatch(r"FY(\d{4})", period or "")
    return int(m.group(1)) if m else 0


def due_fiscal_year(run_dir: Path) -> int:
    """The latest fiscal year whose annual report is due by the run's cutoff (AR_DUE_DAYS after the year end; the
    fiscal year is named for the calendar year in which it ends, so FY2026 ends in March 2026 for a March year end)."""
    _, month, cutoff = _manifest_context(run_dir)
    month = month if 1 <= month <= 12 else 3
    y = cutoff.year
    while y > 1900:
        end = dt.date(y, month, calendar.monthrange(y, month)[1])
        if end + dt.timedelta(days=AR_DUE_DAYS) <= cutoff:
            return y
        y -= 1
    return 0


def period_key(doc_type: str, period: str) -> tuple:
    m = re.match(r"Q([1-4])FY(\d{4})", period or "")
    if m:
        return (int(m.group(2)), int(m.group(1)))
    m = re.match(r"FY(\d{4})", period or "")
    if m:
        return (int(m.group(1)), 9)
    return (0, 0)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------------------------
# Documents in scope
# --------------------------------------------------------------------------------------------------------------

def map_documents(run_dir: Path) -> List[dict]:
    path = run_dir / "corpus" / "document_map.csv"
    out = []
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("doc_type") not in CORE_TYPES or not r.get("text_path"):
                continue
            text = Path(r["text_path"]) if Path(r["text_path"]).is_absolute() else run_dir / r["text_path"]
            meta = text.parent / "meta.json"
            if not meta.exists():
                continue
            m = load_json(meta, {})
            out.append({"key": "%s-%s" % (PREFIX[r["doc_type"]], r["period"]), "doc_type": r["doc_type"],
                        "period": r["period"], "label": "%s %s" % (LABEL[r["doc_type"]], r["period"]),
                        "text": rel(run_dir, text), "meta": rel(run_dir, meta), "pdf": repo_path(run_dir, m.get("source", "")),
                        "sha12": (m.get("sha256") or "")[:12], "sha256": m.get("sha256") or "", "pages": m.get("pages", 0),
                        "filed": r.get("filed", "")})
    return out


def filing_documents(run_dir: Path) -> List[dict]:
    path = run_dir / READING / "filings.csv"
    out = []
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("text_path"):
                continue
            text = run_dir / r["text_path"]
            meta = text.parent / "meta.json"
            if not meta.exists():
                continue
            m = load_json(meta, {})
            out.append({"key": r["key"], "doc_type": "filing:%s" % r["doc_type"], "period": r.get("date", ""),
                        "label": "Exchange filing (%s) %s: %s" % (r["doc_type"], r.get("date", ""), r.get("title", "")[:80]),
                        "text": r["text_path"], "meta": rel(run_dir, meta), "pdf": repo_path(run_dir, m.get("source", "")),
                        "sha12": (m.get("sha256") or "")[:12], "sha256": m.get("sha256") or "", "pages": m.get("pages", 0),
                        "filed": r.get("date", "")})
    return out


def ar_windows(run_dir: Path, docs: List[dict], years: int, core_years: int) -> Tuple[int, set, set]:
    """(latest fiscal year, full-read years, core years). The window is anchored on fiscal years, not on the reports
    that happen to be in the map: the latest year is the newest report in the map or, if later, the newest one due by
    the cutoff, so a missing recent report shows as a gap instead of pulling an older year into the full read."""
    fys = [fiscal_year(d["period"]) for d in docs if d["doc_type"] == "annual_report"]
    latest = max([f for f in fys if f] + [due_fiscal_year(run_dir)])
    full = set(range(latest - years + 1, latest + 1)) if latest and years > 0 else set()
    core = set(range(latest - years - core_years + 1, latest - years + 1)) if latest and core_years > 0 else set()
    return latest, full, core


def select(run_dir: Path, years: int, quarters: int, ppt_quarters: int,
           core_years: int = 0) -> Tuple[List[dict], List[dict], List[dict]]:
    """(documents to read, documents out of scope, gaps: in-scope annual reports missing from the map)."""
    docs = map_documents(run_dir)
    chosen, excluded, gaps = [], [], []
    by_type = defaultdict(list)
    for d in docs:
        by_type[d["doc_type"]].append(d)
    for t in by_type:
        by_type[t].sort(key=lambda d: period_key(t, d["period"]), reverse=True)
    latest, full, core = ar_windows(run_dir, docs, years, core_years)
    for d in by_type.get("annual_report", []):
        fy = fiscal_year(d["period"])
        if not fy or fy in full:                   # a report whose year cannot be told is read in full
            chosen.append(dict(d, scope="full"))
        elif fy in core:
            chosen.append(dict(d, scope="core"))
        else:
            excluded.append(dict(d, reason="outside the reading window (every page of FY%d-FY%d, core sections of the "
                                            "%d years before)" % (latest - years + 1, latest, core_years)))
    have = {fiscal_year(d["period"]) for d in by_type.get("annual_report", [])}
    for y in sorted(full | core, reverse=True):
        if y not in have:
            gaps.append({"key": "AR-FY%d" % y, "doc_type": "annual_report", "period": "FY%d" % y,
                         "label": "Annual report FY%d" % y, "scope": "full" if y in full else "core",
                         "reason": "not in the document map"})
    for t, n in (("transcript", quarters), ("investor_presentation", ppt_quarters)):
        for i, d in enumerate(by_type.get(t, [])):
            (chosen.append(dict(d, scope="full")) if i < n else
             excluded.append(dict(d, reason="older than the %d-quarter window" % n)))
    for d in filing_documents(run_dir):
        chosen.append(dict(d, scope="full"))
    order = {"annual_report": 0, "transcript": 2, "investor_presentation": 3}

    def sort_key(d):
        yr, q = period_key(d["doc_type"], d["period"])
        try:
            ordinal = dt.date.fromisoformat(d["period"]).toordinal()
        except ValueError:
            ordinal = 0
        return (order.get(d["doc_type"], 4) + (0.5 if d["scope"] == "core" else 0), -yr, -q, -ordinal, d["key"])
    chosen.sort(key=sort_key)
    return chosen, excluded, gaps


def _manifest_context(run_dir: Path):
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    fy_end = str(m.get("fiscal_year_end") or "03-31")
    try:
        month = int(fy_end.split("-")[0])
    except ValueError:
        month = 3
    try:
        cutoff = dt.date.fromisoformat(str(m.get("research_cutoff")))
    except ValueError:
        cutoff = dt.date.today()
    return m, month, cutoff


# --------------------------------------------------------------------------------------------------------------
# Passages and classes
# --------------------------------------------------------------------------------------------------------------

def split_long(text: str) -> List[str]:
    """A paragraph longer than SPLIT_UNIT characters -> its sentences, so text that repeats word for word in another
    year or section is read once while every changed sentence is read. Line breaks are kept as printed."""
    if len(text) <= SPLIT_UNIT:
        return [text]
    flat = text.replace("\n", " \n")
    raw = re.split(r"(?<=[.;:?!])\s+(?=[A-Z(\"'\d•])", flat)
    sents = []
    for part in raw:                      # "P.M." / "Rs." / "No." / "Ltd." do not end a sentence
        if sents and ABBR_END_RE.search(sents[-1]):
            sents[-1] = sents[-1] + " " + part
        else:
            sents.append(part)
    # One sentence per passage (very short sentences join the next): boundaries depend only on the sentence itself,
    # so an edit early in a paragraph does not shift the passages after it, and every unchanged sentence matches the
    # other year's text word for word. Measured on BHARTIARTL FY2024-26 this read-once share was 17-27 % of older
    # reports, against 10-20 % for whole paragraphs.
    parts, cur = [], ""
    for sent in sents:
        cur = (cur + " " + sent) if cur else sent
        if len(cur) >= MIN_SENTENCE or len(cur) >= GROUP_CHARS:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    return [re.sub(r" \n", "\n", x).strip() for x in parts if x.strip()]


def segment(body: List[str]) -> List[Tuple[str, str, int]]:
    """Page text -> [(kind, text, block)]: 'table' rows (one line each; a run of rows is one block), 'prose' passages
    (a paragraph, or one sentence of a long paragraph; the paragraph is one block), 'marker' lines (half-page)."""
    out, buf = [], []
    state = {"block": 0, "last": None}

    def flush():
        if buf:
            text = "\n".join(buf).strip("\n")
            if text.strip():
                state["block"] += 1
                out.extend(("prose", t, state["block"]) for t in split_long(text))
                state["last"] = "prose"
            buf.clear()

    for ln in body:
        s = ln.rstrip()
        if re.match(r"^\[(L|R) half", s.strip()):
            flush()
            state["block"] += 1
            out.append(("marker", s.strip(), state["block"]))
            state["last"] = "marker"
        elif TABLE_ROW_RE.match(s) or "│" in s:
            flush()
            if state["last"] != "table":
                state["block"] += 1
            out.append(("table", s, state["block"]))
            state["last"] = "table"
        elif not s.strip():
            flush()
        else:
            buf.append(s)
    flush()
    return out


def page_number_positions(segs: List[Tuple[str, str, int]], printed: str) -> set:
    """Indexes of the printed page number lines: a passage that is exactly the printed number of its half (or page)
    and is the first or last passage of that half. Anything else that looks like a number is a value."""
    halves, cur, num = [], [], set(x for x in (printed or "").split("/") if x)
    for i, (kind, text, _) in enumerate(segs):
        if kind == "marker":
            if cur:
                halves.append((cur, num))
            m = re.search(r"printed p\.(\S+?)\]", text)
            cur, num = [], ({m.group(1)} if m else set())
            continue
        cur.append(i)
    if cur:
        halves.append((cur, num))
    out = set()
    for idx, nums in halves:
        for i in (idx[:1] + idx[-1:]):
            kind, text, _ = segs[i]
            if kind == "prose" and norm_space(text) in nums:
                out.add(i)
    return out


def navigation_lines(bodies: List[List[str]]) -> set:
    """Lines repeated across most of a document (a section tab bar, the company name, a footer): they name sections
    without starting them, so section detection ignores them. A running header that belongs to one section (for
    example 'Notes to the consolidated financial statements') is kept: it recurs only within that section's range."""
    occ = defaultdict(set)
    n = len(bodies)
    for i, body in enumerate(bodies):
        k = 0
        for ln in body:                      # the first 60 lines of each half of a spread
            t = norm_space(ln).lower()
            if re.match(r"^\[(l|r) half", t):
                k = 0
                continue
            k += 1
            if k <= 60 and 3 <= len(t) <= 160:
                occ[t].add(i)
    nav = set()
    for t, idx in occ.items():
        if len(idx) >= max(6, 0.2 * n) and (max(idx) - min(idx) + 1) >= 0.6 * n:
            nav.add(t)
    return nav


TITLE_LINES = 8
TITLE_BLOCKS = 6
TITLE_PREFIX_RE = re.compile(r"^(?:(?:\(?[A-Za-z0-9]{1,3}[\.\)]|[•\-–])\s+|annexure\s*['‘\"]?[a-z0-9]{1,3}['’\"]?\s*[-–:,]?\s*(?:to\s+the\s+)?)", re.I)


def page_sections(p: dict, body: List[str], nav: Optional[set] = None) -> set:
    """Section keys whose title appears in the page's title area or in a large-font heading.

    The title area of each half of a spread is its first few text blocks (blank-line separated), navigation removed;
    a title is a short block of its own (at most two lines, ~120 characters) that starts with the section name
    (after an enumeration or an "Annexure X –" prefix). A section named inside a paragraph ("... the Board's Report
    including Annexures ...", "which comprise the Consolidated Balance Sheet ...") does not count."""
    import doc_text  # noqa: E402
    nav = nav or set()
    blocks, cur, half_blocks = [], [], 0

    def close():
        nonlocal cur, half_blocks
        if cur:
            if half_blocks < TITLE_BLOCKS:
                blocks.append(cur)
            half_blocks += 1
            cur = []

    for ln in body:
        t = norm_space(ln)
        if re.match(r"^\[(L|R) half", t):
            close()
            half_blocks = 0
            continue
        if not t:
            close()
            continue
        if t.lower() in nav or "│" in ln or TABLE_ROW_RE.match(ln):
            continue
        cur.append(t)
    close()
    titles = [" ".join(b) for b in blocks if len(b) <= 2 and len(" ".join(b)) <= 120]
    heads = [s[len("heading: "):] for r in p.get("regions", []) for s in r.get("sections", []) if s.startswith("heading: ")]
    heads = [h for h in heads if norm_space(h).lower() not in nav]
    starts = [TITLE_PREFIX_RE.sub("", t) for t in titles]
    secs = {"annexure"} if any(re.match(r"^annexure\s*[-–]?\s*['‘\"]?[a-z0-9]{1,3}\b", t, re.I) for t in titles) else set()
    for key, rx in list(doc_text.SECTION_RES) + EXTRA_SECTIONS:
        if any(rx.match(t) for t in starts) or any(rx.match(TITLE_PREFIX_RE.sub("", norm_space(h))) for h in heads):
            secs.add(key)
    return secs


def classify_page(doc_type: str, p: dict, body: List[str], state: str, nav: Optional[set] = None) -> Tuple[str, str]:
    """(class of this page, new sticky state)."""
    if doc_type == "transcript":
        return "transcript", "transcript"
    if doc_type == "investor_presentation":
        return "presentation", "presentation"
    if doc_type.startswith("filing:"):
        cls = "filing_critical" if doc_type.split(":", 1)[1] in CRITICAL_FILING_TYPES else "filing"
        return cls, cls
    if set(p.get("flags", [])) & {"rotated_text", "image_only", "blank_or_graphic"}:
        return (state or "narrative"), (state or "narrative")      # no reliable title text: the section continues
    secs = page_sections(p, body, nav)
    if "annexure" in secs:                   # a new annexure inside the statutory reports (not in the financial statements)
        secs.discard("annexure")
        if state in STATUTORY_STATES:
            secs.add("board_annex")
    doc_secs = {s for s in secs if s in SECTION_TO_CLASS}
    if len(doc_secs) >= 4:                       # a contents page lists every section: it moves nothing
        return "narrative", state
    classes = {SECTION_TO_CLASS.get(s, s) for s in secs if s in SECTION_TO_CLASS or s in ("board_annex", "remuneration", "notice")}
    in_fs = state in FS_STATES
    if not in_fs:
        classes.discard("notes_critical")       # 'contingent liabilities' mentioned outside the financial statements
    if "remuneration" in classes and state not in ("board", "board_annex", "remuneration", "cg"):
        classes.discard("remuneration")
    for c in PRECEDENCE:
        if c in classes:
            if c == "notes_critical":            # inside the notes: the page is critical, the state stays 'notes'
                return "notes_critical", "notes"
            return c, c
    return (state or "narrative"), (state or "narrative")


def build_units(doc: dict, run_dir: Path, sch: dict, crit_note: re.Pattern,
                image_share: Optional[Dict[int, float]] = None) -> List[dict]:
    """Every page of a document -> page records with their passages (text, class, critical flag, block)."""
    meta = load_json(run_dir / doc["meta"], {})
    lines = (run_dir / doc["text"]).read_text(encoding="utf-8").splitlines()
    crit = critical_classes(sch)
    pages, state, note_cls = [], "narrative", "notes"
    index = meta.get("page_index", [])
    bodies = [lines[p["start_line"]:p["end_line"]] for p in index]
    nav = navigation_lines(bodies)
    image_share = image_share or {}
    for p, body in zip(index, bodies):
        n = p["page"]
        flags = set(p.get("flags", []))
        cls, new_state = classify_page(doc["doc_type"], p, body, state, nav)
        if new_state != state and (new_state == "statements" or (new_state == "notes" and state not in FS_STATES)):
            note_cls = "notes"
        state = new_state
        visual = bool(flags & VISUAL_FLAGS)
        units = []
        if not visual:
            k = 0
            segs = segment(body)
            page_nums = page_number_positions(segs, p.get("printed", ""))
            for i, (kind, text, block) in enumerate(segs):
                if kind == "marker" or norm_space(text).lower() in nav or i in page_nums:
                    # half-page markers, running headers/footers (the same line across the document) and the printed
                    # page number are shown for orientation but are not passages: they carry no information of their own
                    units.append({"id": "", "kind": "marker", "text": text,
                                  "marker": "half" if kind == "marker" else ("page_number" if i in page_nums else "header")})
                    continue
                u_cls = cls
                if cls in ("notes", "notes_critical") and state in FS_STATES:
                    first = text.strip().splitlines()[0] if text.strip() else ""
                    m = NOTE_TITLE_RE.match(first) if kind == "prose" and "\n" not in text.strip() else None
                    if m and len(m.group(2).split()) <= 14 and not m.group(2).rstrip().endswith("."):
                        note_cls = "notes_critical" if crit_note.search(m.group(2)) else "notes"
                    elif kind == "prose" and len(first) < 100 and crit_note.match(first.strip()) and not first.rstrip().endswith("."):
                        note_cls = "notes_critical"
                    u_cls = "notes_critical" if (cls == "notes_critical" or note_cls == "notes_critical") else "notes"
                k += 1
                units.append({"id": unit_id(doc["sha12"], n, k), "kind": kind, "text": text, "class": u_cls,
                              "critical": u_cls in crit, "block": block,
                              "numeric": kind == "prose" and numeric_only(text)})
            passages = [u for u in units if u["id"]]
            cells = sum(1 for u in passages if u["numeric"])
            if cells >= CELL_LAYOUT_MIN and cells >= 0.25 * len(passages):
                flags.add("cell_layout")            # a table printed one cell per line: which value is on which line?
            if image_share.get(n, 0.0) >= IMAGE_MIN_SHARE:
                flags.add(IMAGE_FLAG)
        verify = bool(flags & VERIFY_FLAGS)
        pages.append({"page": n, "printed": p.get("printed", ""), "class": cls, "flags": sorted(flags),
                      "visual": visual, "verify": verify, "images": (IMAGE_FLAG in flags) and not visual, "units": units})
    return pages


def poppler(name: str) -> Optional[str]:
    p = shutil.which(name) or "/opt/homebrew/bin/%s" % name
    return p if Path(p).exists() else None


def pdf_path(doc_pdf: str) -> Path:
    return Path(doc_pdf) if Path(doc_pdf).is_absolute() else rl.ROOT / doc_pdf


def image_shares(run_dir: Path, doc: dict) -> Optional[Dict[int, float]]:
    """Page -> share of the page covered by raster images that are not page furniture (an image object drawn on
    SHARED_IMAGE_PAGES pages or more: logo, background, ornament). From `pdfinfo` and `pdfimages -list` (poppler);
    cached per document. None when poppler or the PDF is missing: the plan and COVERAGE.md then say images were not
    checked."""
    cache = run_dir / CACHE / "images" / ("%s.json" % (doc.get("sha12") or doc["key"]))
    got = load_json(cache)
    if got is not None:
        return {int(k): v for k, v in got.items()}
    pdf = pdf_path(doc["pdf"])
    pdfinfo, pdfimages = poppler("pdfinfo"), poppler("pdfimages")
    if not (pdf.exists() and pdfinfo and pdfimages):
        return None
    try:
        info = subprocess.run([pdfinfo, "-f", "1", "-l", str(max(1, int(doc.get("pages") or 0) or 9999)), str(pdf)],
                              capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
        listing = subprocess.run([pdfimages, "-list", str(pdf)], capture_output=True, timeout=300).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return None
    out = shares_from_listing(info, listing)
    write_json(cache, {str(k): v for k, v in sorted(out.items())})
    return out


def shares_from_listing(info: str, listing: str) -> Dict[int, float]:
    """Image shares from `pdfinfo -f 1 -l N` and `pdfimages -list` output (see image_shares)."""
    size = {}
    for m in re.finditer(r"^Page\s+(\d+)\s+size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", info, re.M):
        size[int(m.group(1))] = (float(m.group(2)) / 72.0) * (float(m.group(3)) / 72.0)
    default = next(iter(size.values()), 0.0)
    if not default:
        m = re.search(r"^Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", info, re.M)
        default = (float(m.group(1)) / 72.0) * (float(m.group(2)) / 72.0) if m else 0.0
    rows, pages_of = [], defaultdict(set)
    for ln in listing.splitlines()[2:]:
        f = ln.split()
        if len(f) < 14 or not f[0].isdigit() or f[2] in ("smask", "stencil"):
            continue
        try:
            pg, w, h, xp, yp = int(f[0]), int(f[3]), int(f[4]), float(f[12]), float(f[13])
        except ValueError:
            continue
        if xp <= 0 or yp <= 0:
            continue
        obj = f[10] + ":" + f[11]
        rows.append((pg, obj, (w / xp) * (h / yp)))
        pages_of[obj].add(pg)
    share = defaultdict(float)
    for pg, obj, area in rows:
        if len(pages_of[obj]) >= SHARED_IMAGE_PAGES:
            continue
        a = size.get(pg, default)
        if a:
            share[pg] = min(1.0, share[pg] + area / a)
    return {pg: round(v, 3) for pg, v in share.items()}


def mark_repeats(pg: dict, doc_key: str, seen: dict, seen_tables: dict) -> None:
    """Set each passage's status on a page: `new` (read here), `repeat` (read elsewhere; shown by reference) or
    `context` (read elsewhere; shown in full just before new text, for meaning; not cited).

    Read-once never removes meaning:
    - a passage shorter than LONG_UNIT characters (a label, heading, column header, name or value) is always read;
    - a label followed by its values (a numeric-only passage next on the page) is always read;
    - a table is read once only when the whole table, every row in order, repeats a table read elsewhere: a row of a
      changed table can carry another period under new column headers;
    - the repeated sentence or paragraph just before a new passage is shown in full as context."""
    units = [u for u in pg["units"] if u["id"]]
    tables = defaultdict(list)
    for u in units:
        if u["kind"] == "table":
            tables[u["block"]].append(u)
    for rows in tables.values():
        key = hashlib.sha1("\n".join(norm_quote(r["text"]) for r in rows).encode()).hexdigest()
        hit = seen_tables.get(key)
        crit = any(r["critical"] for r in rows)
        if hit and (hit[1] or not crit):
            for r, orig in zip(rows, hit[0]):
                r.update(status="repeat", repeat_of=orig, repeat_where="%s p.%d" % (hit[2], hit[3]))
        else:
            for r in rows:
                r["status"] = "new"
            seen_tables[key] = ([r["id"] for r in rows], crit, doc_key, pg["page"])
    for i, u in enumerate(units):
        if u["kind"] == "table":
            continue
        n = norm_quote(u["text"])
        nxt = units[i + 1] if i + 1 < len(units) else None
        label = bool(nxt and nxt.get("numeric") and not u.get("numeric"))
        key = hashlib.sha1(n.encode()).hexdigest() if (len(n) >= LONG_UNIT and not label and not u.get("numeric")) else None
        hit = seen.get(key) if key else None
        if hit and (hit[1] or not u["critical"]):        # a critical passage is read even if it repeats non-critical text
            u.update(status="repeat", repeat_of=hit[0], repeat_where="%s p.%d" % (hit[2], hit[3]))
        else:
            u["status"] = "new"
            if key:
                seen[key] = (u["id"], u["critical"], doc_key, pg["page"])
    for a, b in zip(units, units[1:]):
        if a["kind"] == "prose" and a["status"] == "repeat" and b["status"] == "new":
            a["status"] = "context"


# --------------------------------------------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------------------------------------------

def structured_cover(run_dir: Path):
    """BRSR pages covered by the company's BRSR XBRL filing (structured_filings.py), as a callable."""
    try:
        import structured_filings as sf  # noqa: E402
    except ImportError:
        return None
    try:
        return sf.brsr_coverage_tester(run_dir)
    except (OSError, ValueError):
        return None


def supersede(run_dir: Path, reason: str, log=print) -> Optional[Path]:
    """Before a new plan replaces one that readers already worked on: move its extractions, disagreements and
    bake-off record to corpus/reading/superseded/<UTC time>/, and mark every recorded launch superseded (kept in
    launches.json, so the reading audit can still account for those agents). Nothing is deleted."""
    reading = run_dir / READING
    movable = [reading / x for x in ("extractions", "disagreements", "bakeoff.json", "bakeoff_score.json", "BAKEOFF.md",
                                     "plan.json") if (reading / x).exists()]
    if not movable:
        return None
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = reading / "superseded" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for src in movable:
        src.rename(dest / src.name)
    log_ = load_json(launches_path(run_dir), {"launches": []})
    for l in log_["launches"]:
        if not l.get("superseded_at"):
            l.update(superseded_at=stamp, superseded_reason=reason, superseded_to=rel(run_dir, dest))
    if log_["launches"]:
        write_json(launches_path(run_dir), log_)
    (dest / "REASON.md").write_text("# Superseded reading plan (%s)\n\n%s\n" % (stamp, reason), encoding="utf-8")
    log("superseded the previous plan and %d launch(es): moved to %s" % (len(log_["launches"]), rel(run_dir, dest)))
    return dest


def gaps_path(run_dir: Path) -> Path:
    return run_dir / READING / "gaps.json"


def accepted_gaps(run_dir: Path) -> Dict[str, dict]:
    return load_json(gaps_path(run_dir), {"accepted": {}}).get("accepted", {})


def accept_gap(run_dir: Path, key: str, reason: str) -> dict:
    """Record why an in-scope annual report cannot be read (for example "listed in 2021: no earlier annual report").
    COVERAGE.md lists every accepted gap with its reason."""
    if not reason.strip():
        raise SystemExit("a reason is required")
    data = load_json(gaps_path(run_dir), {"accepted": {}})
    data.setdefault("accepted", {})[key] = {"reason": reason.strip(),
                                            "at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}
    write_json(gaps_path(run_dir), data)
    return data


# --------------------------------------------------------------------------------------------------------------
# Reuse: a document read in an earlier run of the company is not read again
# --------------------------------------------------------------------------------------------------------------

def prior_runs(run_dir: Path) -> List[Path]:
    """The company's other runs that made a reading plan, newest first (run ids are UTC timestamps)."""
    me = run_dir.resolve()
    parent = me.parent
    out = [d for d in parent.iterdir() if d.is_dir() and d.resolve() != me and (d / READING / "plan.json").exists()]
    return sorted(out, key=lambda d: d.name, reverse=True)


def audited_reads(prior: Path) -> set:
    """(chunk, role) pairs that an earlier run's reading audit passed: an agent received every line and opened every
    VIEW REQUIRED page, or the read was itself reused there and its copy verified. Nothing without a passed audit."""
    a = load_json(prior / rl.READING_AUDIT, {})
    if a.get("status") != "PASS":
        return set()
    ok = set()
    for r in a.get("readers", []):
        if not r.get("superseded") and r.get("lines_total") and r.get("lines_seen", 0) >= r["lines_total"] \
                and not r.get("view_pages_missing"):
            ok.add((r["chunk"], r["role"]))
    for r in a.get("reused", []):
        if r.get("verified"):
            ok.update((r["chunk"], role) for role in r.get("roles", []))
    return ok


def reusable_documents(run_dir: Path, docs: List[dict], sch: dict, log=print) -> Dict[str, dict]:
    """Documents of this plan that an earlier run read completely: the same file (SHA-256), the same reading format
    and schema, every chunk read, checked and reconciled under today's model policy, every read passed by that run's
    reading audit, at least the pages this run's scope needs, and its passage files still on this machine. A document
    whose repeats point to a document that is not reused is read again (its passages were read once against text this
    run does not carry)."""
    pol = rl.model_policy()
    core_cls = core_classes(sch)
    want = {d["key"]: d for d in docs if d.get("sha256")}
    found: Dict[str, dict] = {}
    for prior in prior_runs(run_dir):
        pplan = load_json(prior / READING / "plan.json", {})
        pol = run_policy(prior)
        if pplan.get("reading_format") != READING_FORMAT or pplan.get("schema_version") not in compatible_schemas(sch):
            continue
        audited = audited_reads(prior)
        if not audited:
            continue
        for pd in pplan.get("documents", []):
            d = want.get(pd["key"])
            if not d or pd["key"] in found or pd.get("sha256") != d["sha256"] or pd.get("refers_to") is None:
                continue
            if any(r.get("status") == "out_of_scope" and (d["scope"] == "full" or r.get("class") in core_cls)
                   for r in pd.get("page_records", [])):
                continue                            # the earlier run read less of it than this run must
            chunks = [c for c in pplan.get("chunks", []) if c["doc"] == pd["key"]]
            caches = [prior / CACHE / "units" / ("%s.json" % pd["key"])] + \
                [prior / CACHE / "chunks" / ("%s.%s" % (c["id"], x)) for c in chunks for x in ("json", "md")]
            if not all(p.exists() for p in caches):
                continue
            ok = True
            for c in chunks:
                state, _ = chunk_state(prior, c, pol, write=False)
                need = set(required_roles(c, pol))
                if need == {"critical", "reader"} and compare_chunk(prior, c["id"], write=False):
                    need.add("resolved")
                if state != "read" or not all((c["id"], r) in audited for r in need):
                    ok = False
                    break
            if ok:
                found[pd["key"]] = {"run_dir": prior, "run_id": pplan.get("run_id", prior.name), "doc": pd, "chunks": chunks}
    changed = True
    while changed:                                  # closure: every document a reused one repeats must be reused too
        changed = False
        for k in list(found):
            if not set(found[k]["doc"].get("refers_to", [])) <= set(found):
                del found[k]
                changed = True
    return found


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_document(run_dir: Path, doc: dict, cand: dict) -> Tuple[dict, List[dict]]:
    """Copy a document's reading from an earlier run into this one: its passages and chunk files (cache) and every
    extraction, resolution and disagreement file, unchanged, recording each file's SHA-256 so that the reading audit
    can confirm the copy. Page records keep their status and name the run that read them."""
    prior, pd = cand["run_dir"], cand["doc"]
    cache, pcache = run_dir / CACHE, prior / CACHE
    for sub in ("units", "chunks", "images"):
        (cache / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(pcache / "units" / ("%s.json" % pd["key"])), str(cache / "units" / ("%s.json" % pd["key"])))
    img = pcache / "images" / ("%s.json" % (pd.get("sha12") or pd["key"]))
    if img.exists():
        shutil.copy2(str(img), str(cache / "images" / img.name))
    chunks = []
    for c in cand["chunks"]:
        files = {}
        for x in ("json", "md"):
            shutil.copy2(str(pcache / "chunks" / ("%s.%s" % (c["id"], x))), str(cache / "chunks" / ("%s.%s" % (c["id"], x))))
        srcs = [extraction_path(prior, c["id"], role) for role in ROLES] + \
            [prior / READING / "disagreements" / ("%s.json" % c["id"])]
        for src in srcs:
            if src.exists():
                dst = run_dir / src.relative_to(prior)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
                files[str(src.relative_to(prior))] = file_sha256(dst)
        store_path = cache / "chunks" / ("%s.json" % c["id"])
        store = load_json(store_path)
        store.update(pdf=doc["pdf"], file=repo_path(run_dir, cache / "chunks" / ("%s.md" % c["id"])))
        write_json(store_path, store)
        chunks.append(dict(c, pdf=doc["pdf"], doc_label=doc["label"], bakeoff=False,
                           reused={"run": cand["run_id"], "files": files}))
    recs = [dict(r, reused_from=cand["run_id"]) for r in pd["page_records"]]
    rec = dict(doc, page_records=recs, images_checked=pd.get("images_checked", True), refers_to=pd.get("refers_to", []),
               reused_from=cand["run_id"])
    return rec, chunks


def calibration_path(run_dir: Path) -> Path:
    return run_dir / READING / "calibration.json"


def run_policy(run_dir: Path) -> dict:
    """The model policy for this run: MODEL_POLICY.md, with this run's own calibration (the in-run bake-off) in place
    of the global one once the plan has started it."""
    pol = rl.model_policy()
    cal = load_json(calibration_path(run_dir))
    return dict(pol, calibration=cal) if cal else pol


def start_calibration(run_dir: Path, n: int = 12, log=print) -> List[str]:
    """In-run calibration: a stratified sample of this run's chunks (one per non-critical section class first) is read
    by both models before any other non-critical chunk; when it is reconciled, `finish_calibration` scores the Sonnet
    read of each class against the adjudicated result. Only a class that passes (at least BAKEOFF_MIN_ITEMS items,
    recall >= 0.98, zero material misses) is read by Sonnet alone for the rest of the run; every other class stays
    double-read. Nothing is assumed from another run: each run proves it on its own pages."""
    picked = bakeoff_plan(run_dir, n, log=log)
    write_json(calibration_path(run_dir), {"status": "in_progress", "chunks": picked, "started_at": now_iso(),
                                           "single_read_classes": [], "rule": "at least %d adjudicated items, recall >= "
                                           "0.98 and zero material misses for the Sonnet read of the class" % BAKEOFF_MIN_ITEMS})
    return picked


def finish_calibration(run_dir: Path, log=print) -> dict:
    out = bakeoff_score(run_dir, log=lambda m: None)
    cal = load_json(calibration_path(run_dir), {})
    eligible = out["eligible_single_read_classes"]
    cal.update(status="passed" if eligible else "failed", single_read_classes=eligible, computed_at=now_iso(),
               rows=out["rows"], material_misses=len(out["material_misses"]))
    write_json(calibration_path(run_dir), cal)
    log("calibration: %s; single Sonnet read for %s; every other class stays double-read (corpus/reading/BAKEOFF.md)" % (
        cal["status"], ", ".join(eligible) or "no class"))
    return cal


def plan(run_dir: Path, years: int = DEFAULT_YEARS, quarters: int = 24, ppt_quarters: int = 12,
         core_years: int = DEFAULT_CORE_YEARS, log=print, replan: str = "", reuse: bool = True,
         calibrate: bool = True) -> dict:
    reading = run_dir / READING
    worked = (reading / "extractions").exists() and any((reading / "extractions").glob("*.jsonl"))
    if worked and not replan:
        raise SystemExit("this run already has reader extractions for the current plan: a new plan would change passage ids "
                         "under them. Re-run with --replan \"<reason>\" to move them to corpus/reading/superseded/ first.")
    sch = schema()
    crit_note = re.compile(sch["critical_note_title"], re.I)
    crit = critical_classes(sch)
    core_cls = core_classes(sch)
    docs, excluded, gaps = select(run_dir, years, quarters, ppt_quarters, core_years)
    acc = accepted_gaps(run_dir)
    open_gaps = [g for g in gaps if g["key"] not in acc]
    if open_gaps:
        raise SystemExit("in-scope annual reports are missing from the document map: %s. Find them (the librarian, then "
                         "document_map.py add) or record why one cannot be had: reading.py accept-gap RUN_DIR <key> "
                         "--reason \"...\"" % ", ".join("%s (%s)" % (g["key"], g["scope"]) for g in open_gaps))
    if not docs:
        raise SystemExit("no documents with a text layer: run document_map.py build (and reading.py fetch-filings) first")
    if replan and (reading / "plan.json").exists():
        supersede(run_dir, replan, log)
    latest, full_years, core_window = ar_windows(run_dir, docs, years, core_years)
    reused = reusable_documents(run_dir, docs, sch, log) if reuse else {}
    cache = run_dir / CACHE
    (cache / "chunks").mkdir(parents=True, exist_ok=True)
    cover = structured_cover(run_dir)
    seen: Dict[str, Tuple[str, bool, str, int]] = {}      # normalized text key -> (unit id, critical, doc key, page)
    seen_tables: Dict[str, Tuple[List[str], bool, str, int]] = {}   # whole-table key -> (row ids, critical, doc, page)
    doc_records, chunks = [], []
    for doc in docs:
        if doc["key"] in reused:
            rec, doc_chunks = import_document(run_dir, doc, reused[doc["key"]])
            doc_records.append(rec)
            chunks.extend(doc_chunks)
            log("%-14s %4d pages: reused from run %s (same file, read and audited there): %d chunks" % (
                doc["key"], len(rec["page_records"]), reused[doc["key"]]["run_id"], len(doc_chunks)))
            continue
        shares = image_shares(run_dir, doc)
        if shares is None:
            log("%-14s WARNING: images not checked (poppler pdfimages/pdfinfo or the PDF is missing); COVERAGE.md says so"
                % doc["key"])
        pages = build_units(doc, run_dir, sch, crit_note, shares or {})
        fy = int(doc["period"][2:]) if doc["doc_type"] == "annual_report" and re.fullmatch(r"FY\d{4}", doc["period"]) else 0
        page_recs = []
        refers = set()
        for pg in pages:
            rec = {"page": pg["page"], "printed": pg["printed"], "class": pg["class"], "flags": pg["flags"],
                   "visual": pg["visual"], "verify": pg["verify"], "images": pg["images"], "new": 0, "repeat": 0,
                   "context": 0, "status": "", "chunk": "", "reason": ""}
            if doc["scope"] == "core" and pg["class"] not in core_cls:
                rec.update(status="out_of_scope", reason="core-year report (FY%d-FY%d): only the core sections are read"
                           % (latest - years - core_years + 1, latest - years))
                page_recs.append(rec)
                continue
            if pg["class"] == "brsr" and cover and fy and not pg["visual"]:
                ok, why = cover(fy, [u["text"] for u in pg["units"] if u["id"]])
                if ok:
                    rec.update(status="structured", reason=why)
                    page_recs.append(rec)
                    continue
            mark_repeats(pg, doc["key"], seen, seen_tables)
            for u in pg["units"]:
                if u["id"]:
                    rec[u["status"]] += 1
                    if u.get("repeat_where"):
                        refers.add(u["repeat_where"].rsplit(" p.", 1)[0])
            rec["critical"] = any(u.get("status") == "new" and u["critical"] for u in pg["units"]) or \
                ((pg["visual"] or pg["images"]) and pg["class"] in crit)
            # images are never read once: a page whose text repeats is still viewed for what its images print
            rec["needs_read"] = bool(rec["new"] or pg["visual"] or pg["images"])
            if not rec["needs_read"]:
                rec["status"] = "repeat"
                rec["reason"] = "every passage repeats text read elsewhere" if rec["repeat"] else "no readable passages"
            page_recs.append(rec)
        units_out = {pg["page"]: pg["units"] for pg in pages}
        write_json(cache / "units" / ("%s.json" % doc["key"]), {"doc": doc, "pages": {str(k): v for k, v in units_out.items()}})
        doc_chunks = make_chunks(doc, page_recs, units_out, sch)
        for c in doc_chunks:
            for pn in c["pages"]:
                for r in page_recs:
                    if r["page"] == pn:
                        r["chunk"] = c["id"]
        chunks.extend(doc_chunks)
        doc_records.append(dict(doc, page_records=page_recs, images_checked=shares is not None,
                                refers_to=sorted(refers - {doc["key"]})))
        log("%-14s %4d pages: %4d to read (%d viewed: %d no text, %d images, %d numbers), %4d repeat, %3d structured, "
            "%3d out of scope, %d chunks" % (
                doc["key"], len(page_recs), sum(1 for r in page_recs if r.get("needs_read")),
                sum(1 for c in doc_chunks for _ in view_pages(c)), sum(len(c["visual_pages"]) for c in doc_chunks),
                sum(len(c["image_pages"]) for c in doc_chunks), sum(len(c["verify_pages"]) for c in doc_chunks),
                sum(1 for r in page_recs if r["status"] == "repeat"), sum(1 for r in page_recs if r["status"] == "structured"),
                sum(1 for r in page_recs if r["status"] == "out_of_scope"), len(doc_chunks)))
    for c in chunks:
        if not c.get("reused"):
            write_chunk_files(run_dir, c, doc_records, sch)
    p = {"created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
         "run_id": run_id_of(run_dir), "schema_version": sch["schema_version"], "reading_format": READING_FORMAT,
         "scope": {"years": years, "core_years": core_years, "latest_fy": latest,
                   "full_fys": sorted(full_years, reverse=True), "core_fys": sorted(core_window, reverse=True),
                   "quarters": quarters, "ppt_quarters": ppt_quarters},
         "documents": doc_records, "excluded": [{k: d[k] for k in ("key", "doc_type", "period", "label", "reason")} for d in excluded],
         "gaps": [dict(g, accepted=acc[g["key"]]) for g in gaps],
         "chunks": [{k: v for k, v in c.items() if k != "page_units"} for c in chunks]}
    write_json(run_dir / READING / "plan.json", p)
    fresh = [c for c in chunks if not c.get("reused")]
    if calibration_path(run_dir).exists():
        calibration_path(run_dir).unlink()
    if calibrate and any(not c["critical"] for c in fresh):
        start_calibration(run_dir, log=log)
        p = load_json(run_dir / READING / "plan.json")
        fresh = [c for c in p["chunks"] if not c.get("reused")]
    all_tok = sum(c["est_tokens"] for c in fresh)
    pol = run_policy(run_dir)
    double = sum(c["est_tokens"] for c in fresh if required_roles(c, pol) == ["critical", "reader"])
    if gaps:
        log("accepted gaps: %s" % "; ".join("%s (%s)" % (g["key"], acc[g["key"]]["reason"]) for g in gaps))
    log("plan: %d documents (%d reused from earlier runs), %d chunks to read; about %dk tokens of text and page images: "
        "every chunk by the reader, and %dk (critical chunks, the calibration sample, and every chunk whose class is not "
        "calibrated for a single read) also by the critical-reader; launches of about %dk tokens%s"
        % (len(doc_records), len(reused), len(fresh), all_tok // 1000, double // 1000, LAUNCH_TOKENS // 1000,
           "; in-run calibration first: the sample is read by both models before the other non-critical chunks"
           if calibration_path(run_dir).exists() else ""))
    return p


def make_chunks(doc: dict, recs: List[dict], units: Dict[int, List[dict]], sch: dict) -> List[dict]:
    chunks, cur = [], None

    def close():
        if cur and cur["pages"]:
            chunks.append(cur)

    n = 0
    for r in recs:
        if not r.get("needs_read"):
            continue
        page_units = units[r["page"]]
        tok = 0
        for u in page_units:
            st = u.get("status")
            if st == "new":
                tok += est_tokens(len(norm_space(u["text"])), u["kind"] == "table") + 3
            elif st == "context":
                tok += est_tokens(min(len(norm_space(u["text"])), CONTEXT_MAX_CHARS)) + 8
            elif not u["id"]:
                tok += 4
        runs = sum(1 for a, b in zip([None] + page_units, page_units) if b.get("status") == "repeat"
                   and (a is None or a.get("status") != "repeat"))
        tok += 30 * runs
        tok += VISUAL_TOKENS if (r["visual"] or r.get("images") or (r["verify"] and r["new"])) else 0
        if cur is None or cur["critical"] != r["critical"] or cur["est_tokens"] + tok > CHUNK_TOKENS \
                or len(cur["pages"]) >= CHUNK_MAX_PAGES:
            close()
            n += 1
            cur = {"id": "%s-c%02d" % (doc["key"], n), "doc": doc["key"], "doc_label": doc["label"], "pdf": doc["pdf"],
                   "critical": r["critical"], "pages": [], "classes": [], "visual_pages": [], "verify_pages": [],
                   "image_pages": [], "new_units": 0, "est_tokens": 0, "bakeoff": False}
        cur["pages"].append(r["page"])
        cur["est_tokens"] += tok
        cur["new_units"] += r["new"]
        for c in {u["class"] for u in page_units if u.get("status") == "new"} | \
                ({r["class"]} if (r["visual"] or r.get("images")) else set()):
            if c not in cur["classes"]:
                cur["classes"].append(c)
        if r["visual"]:
            cur["visual_pages"].append(r["page"])
        else:
            if r["verify"] and r["new"]:
                cur["verify_pages"].append(r["page"])
            if r.get("images"):
                cur["image_pages"].append(r["page"])
    close()
    return chunks


def chunk_cache(run_dir: Path, chunk_id: str) -> dict:
    data = load_json(run_dir / CACHE / "chunks" / ("%s.json" % chunk_id))
    if data is None:
        raise FileNotFoundError("chunk %s has no cached passages (run reading.py plan on this machine)" % chunk_id)
    return data


CHUNK_LEGEND = [
    "How to read this file:",
    "- A passage starts with its id in brackets, for example `[a12]`; its continuation lines are indented by four spaces. "
    "Cite the id as the item's `unit` and copy a few of its words as the item's `anchor`. The check attaches the printed "
    "text as the quote: the cited passage, run on into the passages after it on the same page where the fact continues "
    "there (for example a statement row whose label and values the text layer printed on separate lines).",
    "- `⟲` lines stand for passages that repeat text read elsewhere: they are not read or cited.",
    "- `· context` lines show, in full, text read elsewhere that the next passage may depend on: read them for meaning; "
    "never cite them or extract items from them.",
    "- `(running header)`, `(page number)` and `[L half]` / `[R half]` lines are page furniture, not passages.",
    "- A page marked `VIEW REQUIRED` is opened on the rendered PDF page as its marker says. A fact printed only in the "
    "image cites unit `p<page>` with `\"source\": \"rendered\"`; a fact in a passage cites the passage.",
    "- Tag, do not transcribe: a fact over several passages carries `to` (its last passage); a table printed row by row "
    "(`| … |`) or cell by cell is tagged once with a `table` item and the check writes its rows "
    "(methodology/READING_SCHEMAS.md rules 3 and 3a).",
]


def write_chunk_files(run_dir: Path, c: dict, doc_records: List[dict], sch: dict) -> None:
    """The chunk file a reader reads (short local passage ids a1, a2 ...; continuation lines indented; runs of
    repeated passages collapsed into one reference line; context shown in full) and its JSON store (local id ->
    global id, page, text) that `check` verifies against."""
    units_file = load_json(run_dir / CACHE / "units" / ("%s.json" % c["doc"]))
    pages = units_file["pages"]
    rec_by_page = {r["page"]: r for d in doc_records if d["key"] == c["doc"] for r in d["page_records"]}
    hint = []
    for cl in c["classes"]:
        for t in sch["classes"].get(cl, {}).get("hint", []):
            if t not in hint:
                hint.append(t)
    view = view_pages(c)
    body = []
    store = {"chunk": c["id"], "doc": c["doc"], "doc_label": c["doc_label"], "pdf": c["pdf"], "pages": c["pages"],
             "classes": c["classes"], "critical": c["critical"], "visual_pages": c["visual_pages"],
             "verify_pages": c["verify_pages"], "image_pages": c.get("image_pages", []), "units": {}, "order": []}
    k = 0
    for pn in c["pages"]:
        r = rec_by_page[pn]
        tags = []
        if r["visual"]:
            tags.append("VIEW REQUIRED (%s): no reliable text; read everything on the rendered page; cite unit p%d with "
                        "source rendered" % (", ".join(sorted(set(r["flags"]) & VISUAL_FLAGS)), pn))
        else:
            if pn in c["verify_pages"]:
                fl = sorted(set(r["flags"]) & VERIFY_FLAGS)
                if fl == ["cell_layout"]:
                    tags.append("VIEW REQUIRED (cell_layout): the text layer printed this table one cell per line; confirm "
                                "on the rendered page which values belong to which line, and every number you extract")
                else:
                    tags.append("VIEW REQUIRED (%s): read the passages and confirm every number on the rendered page"
                                % ", ".join(fl))
            if pn in store["image_pages"]:
                tags.append("VIEW REQUIRED (images): read the passages, then view the rendered page and extract every "
                            "fact printed only in an image (unit p%d, source rendered)" % pn)
        body.append("<<<PAGE %d%s | class %s%s>>>" % (pn, " | printed %s" % r["printed"] if r["printed"] else "", r["class"],
                                                      "".join(" | " + t for t in tags)))
        if pn in view:
            store["units"]["p%d" % pn] = {"page": pn, "text": "", "class": r["class"], "visual": True,
                                          "critical": bool(r.get("critical")), "gid": "p%d@%s" % (pn, c["doc"])}
        run = []

        def flush_run():
            if run:
                where = sorted({u["repeat_where"] for u in run})
                words = norm_space(run[0]["text"]).split()
                body.append("⟲ %d passage%s (%d chars) as read in %s: \"%s…\"" % (
                    len(run), "" if len(run) == 1 else "s", sum(len(u["text"]) for u in run),
                    "; ".join(where[:3]) + (" …" if len(where) > 3 else ""), " ".join(words[:8])))
                run.clear()

        for u in pages.get(str(pn), []):
            st = u.get("status") or ("new" if u["id"] else "")
            if st == "repeat":
                run.append(u)
                continue
            flush_run()
            if not u["id"]:
                mk = u.get("marker", "half")
                body.append(u["text"] if mk == "half" else
                            "(%s) %s" % ("page number" if mk == "page_number" else "running header", norm_space(u["text"])))
            elif st == "context":
                t = u["text"] if len(u["text"]) <= CONTEXT_MAX_CHARS else "…" + u["text"][-CONTEXT_MAX_CHARS:]
                tl = t.splitlines() or [""]
                body.append("· context (read in %s): %s" % (u.get("repeat_where", "another section"), tl[0]))
                body.extend("    " + x for x in tl[1:])
            else:
                k += 1
                lid = "a%d" % k
                tl = u["text"].splitlines() or [""]
                body.append("[%s] %s" % (lid, tl[0]))
                body.extend("    " + x for x in tl[1:])
                store["units"][lid] = {"page": pn, "text": u["text"], "class": u["class"], "critical": u["critical"], "gid": u["id"]}
                store["order"].append(lid)
        flush_run()
        body.append("")
    c["new_units"] = k
    store["new_units"] = k
    head = ["# Reading chunk %s — %s" % (c["id"], c["doc_label"]),
            "PDF: `%s` · pages %s · classes: %s · %s" % (c["pdf"], page_ranges(c["pages"]), ", ".join(c["classes"]),
                                                        "CRITICAL (read twice, independently)" if c["critical"] else "standard"),
            "Passages to read: %d%s." % (k, " (a1 to a%d)" % k if k else ""),
            "Pages to view on the rendered PDF page (Read tool on the PDF, pages: \"n\"): %s. If a page is too small or "
            "sideways to read, run `python3 scripts/reading.py render %s %s <page> [--dpi 200] [--rotate 90|270] "
            "[--parts 2]` and Read the image files it prints." % (", ".join(map(str, view)) or "none", rel_run(run_dir), c["id"]),
            "Item types most likely here: %s (any type in methodology/READING_SCHEMAS.md may be used)." % ", ".join(hint[:24])] \
        + CHUNK_LEGEND
    rest = "\n".join([""] + body)
    total = len(head) + 1 + rest.count("\n") + 1
    content = "\n".join(head + ["This file has %d lines: read all of them (use offset/limit when one Read does not "
                                "return them all)." % total]) + "\n" + rest + "\n"
    out = run_dir / CACHE / "chunks" / ("%s.md" % c["id"])
    out.write_text(content, encoding="utf-8")
    store["file"] = repo_path(run_dir, out)
    store["lines"] = content.count("\n")
    write_json(run_dir / CACHE / "chunks" / ("%s.json" % c["id"]), store)


def page_ranges(pages: List[int]) -> str:
    out, start, prev = [], None, None
    for p in sorted(pages):
        if start is None:
            start = prev = p
        elif p == prev + 1:
            prev = p
        else:
            out.append("%d" % start if start == prev else "%d-%d" % (start, prev))
            start = prev = p
    if start is not None:
        out.append("%d" % start if start == prev else "%d-%d" % (start, prev))
    return ", ".join(out)


# --------------------------------------------------------------------------------------------------------------
# Roles, batches, prompts
# --------------------------------------------------------------------------------------------------------------

def required_roles(chunk: dict, policy: Optional[dict] = None) -> List[str]:
    """critical + reader for a critical chunk, a bake-off chunk, or any class not yet calibrated for a single read."""
    if chunk.get("critical") or chunk.get("bakeoff"):
        return ["critical", "reader"]
    cal = (policy or rl.model_policy()).get("calibration", {})
    if cal.get("status") == "passed" and set(chunk.get("classes", [])) <= set(cal.get("single_read_classes", [])):
        return ["reader"]
    return ["critical", "reader"]


def extraction_path(run_dir: Path, chunk_id: str, role: str) -> Path:
    return run_dir / READING / "extractions" / ("%s.%s.jsonl" % (chunk_id, role))


def rel_run(run_dir: Path) -> str:
    try:
        return str(run_dir.resolve().relative_to(rl.ROOT.resolve()))
    except ValueError:
        return str(run_dir)


def agent_prompt(run_dir: Path, rid: str, agent: str, role: str, batch_file: str) -> str:
    return ("You are the %s for run %s (role: %s).\nRUN_DIR: %s\nRead and follow %s exactly: it lists your chunk files, "
            "the PDF pages to view, your output files and the check command. Do not read any other file except "
            "methodology/READING_SCHEMAS.md, the PDFs it names and the page images `reading.py render` prints for them. "
            "Your final message is one line." % (agent.upper(), rid, role, rel_run(run_dir), batch_file))


def launches_path(run_dir: Path) -> Path:
    return run_dir / READING / "launches.json"


def pending_for(run_dir: Path, p: dict, role: str, pol: dict, only_bakeoff: bool = False, exclude=()) -> List[dict]:
    out = []
    for c in p["chunks"]:
        if (only_bakeoff and not c.get("bakeoff")) or c["id"] in exclude or "%s:%s" % (c["id"], role) in exclude:
            continue
        if role in required_roles(c, pol) and not check(run_dir, c["id"], role).ok:
            out.append(c)
    return out


def take_launch(chunks: List[dict]) -> List[dict]:
    """Chunks in plan order, up to LAUNCH_TOKENS and LAUNCH_MAX_CHUNKS (at least one): about one full chunk per
    launch, small chunks packed together. A reader's context holds everything it has read and written, and every turn
    re-reads it: a launch of six chunks (44k tokens of text) peaked at 424k tokens of context and 8.7M tokens processed,
    about four times what the same chunks cost one launch each, and its long turns let the prompt cache expire."""
    batch, tok = [], 0
    for c in chunks:
        if batch and (tok + c["est_tokens"] > LAUNCH_TOKENS or len(batch) >= LAUNCH_MAX_CHUNKS):
            break
        batch.append(c)
        tok += c["est_tokens"]
    return batch


def parts_dir(run_dir: Path, chunk_id: str, role: str) -> Path:
    """Where a reader writes its items, in parts (01.jsonl, 02.jsonl, ...); `check` assembles them, in order, into the
    extraction file. Writing in parts keeps every turn short and keeps what is written when a launch is interrupted."""
    return run_dir / CACHE / "parts" / ("%s.%s" % (chunk_id, role))


def part_files(run_dir: Path, chunk_id: str, role: str) -> List[Path]:
    d = parts_dir(run_dir, chunk_id, role)
    if not d.is_dir():
        return []

    def key(p: Path):
        m = re.match(r"(\d+)", p.stem)
        return (int(m.group(1)) if m else 10 ** 6, p.name)
    return sorted(d.glob("*.jsonl"), key=key)


def write_launch_file(run_dir: Path, launch: dict, chunks: List[dict]) -> Path:
    role = launch["role"]
    rid = run_id_of(run_dir)
    lines = ["# Launch %s — role `%s` (agent `%s`), run %s" % (launch["id"], role, ROLE_AGENT[role], rid), "",
             "Follow your agent definition and `methodology/READING_SCHEMAS.md`. For each chunk below, in order:", "",
             "1. Read **every line** of the chunk file (it states its line count; continue with offset/limit until you "
             "have read the last line).",
             "2. Open every page listed under *View pages* on the rendered PDF (Read tool on the PDF with `pages`; open "
             "them together, in one turn). When a page is too small or sideways to read: `python3 scripts/reading.py "
             "render %s <chunk> <page> [--dpi 200] [--rotate 90|270] [--parts 2]`, then Read the image files it prints."
             % rel_run(run_dir),
             "3. Write the items with the Write tool, in parts of about 40 items, into the chunk's parts directory: "
             "`01.jsonl`, then `02.jsonl`, and so on (the page receipts and the chunk receipt go in the last part). Each "
             "item cites its passage (`unit`, and `to` when the fact runs on) and copies a few of its words (`anchor`): "
             "never copy or paraphrase the passage. Tag each table once (`\"type\": \"table\"`): the check writes its "
             "rows. Do not write the extraction file: the check assembles it from the parts.",
             "4. Run the check command. Fix every error it names in the part file it names (Edit tool) and re-run it "
             "until it prints PASS.", "",
             "| Chunk | File | Lines | PDF | View pages | Parts directory | Check |", "|---|---|---|---|---|---|---|"]
    for c in chunks:
        store = load_json(run_dir / CACHE / "chunks" / ("%s.json" % c["id"]), {})
        lines.append("| %s | `%s` | %s | `%s` | %s | `%s/` | `python3 scripts/reading.py check %s %s --role %s` |" % (
            c["id"], store.get("file", ""), store.get("lines", ""), c["pdf"],
            ", ".join(str(x) for x in view_pages(c)) or "-",
            repo_path(run_dir, parts_dir(run_dir, c["id"], role)), rel_run(run_dir), c["id"], role))
    lines += ["", "Your final message is exactly one line: `%s: <n> items, <m> pages, check PASS` (or the chunk and the "
                  "error you could not fix). Nothing else: observations belong in the items (`unusual`, `other_fact`) "
                  "or in the chunk receipt's `notes`." % launch["id"]]
    out = run_dir / CACHE / "launches" / ("%s.md" % launch["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def log_invocation(run_dir: Path, agent: str, purpose: str) -> None:
    """The manifest's record of a worker launch (what `manifest.py invocation` writes), so the CIO's loop is one
    `next` call and one Agent call per launch."""
    path = run_dir / rl.RUN_MANIFEST
    if not path.exists():
        return
    m = json.loads(path.read_text(encoding="utf-8"))
    node = m.setdefault("workers", {}).setdefault(agent, {"invocations": []})
    node.setdefault("invocations", []).append({"stage": "0b", "purpose": purpose,
                                               "at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()})
    rl.write_json(path, m)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def update_launch(run_dir: Path, launch_id: str, **fields) -> dict:
    """Set fields on a recorded launch (the engine records its sessions, usage and outcome here)."""
    log_ = load_json(launches_path(run_dir), {"launches": []})
    for l in log_["launches"]:
        if l["id"] == launch_id:
            l.update(fields)
            write_json(launches_path(run_dir), log_)
            return l
    raise KeyError(launch_id)


def set_aside(run_dir: Path, launch_id: str, chunk_ids: List[str], role: str) -> List[str]:
    """Before a new launch reads a chunk afresh: move the unfinished work of an earlier launch on it (parts and an
    extraction that does not pass) to _cache/reading/abandoned/<launch>/, so the new reader starts from nothing and
    writes every item itself. Nothing is deleted."""
    moved = []
    for cid in chunk_ids:
        srcs = [parts_dir(run_dir, cid, role)] + ([extraction_path(run_dir, cid, role)] if
                                                 extraction_path(run_dir, cid, role).exists() else [])
        srcs = [s for s in srcs if s.exists()]
        if not srcs or check(run_dir, cid, role, write=False).ok:
            continue
        dest = run_dir / CACHE / "abandoned" / launch_id
        dest.mkdir(parents=True, exist_ok=True)
        for s in srcs:
            target = dest / s.name
            if target.exists():
                target = dest / ("%s.%s" % (s.name, dt.datetime.now().strftime("%H%M%S%f")))
            s.rename(target)
            moved.append(rel(run_dir, target))
    return moved


def issue(run_dir: Path, role: str, chunk_ids: List[str], writer, bakeoff: bool = False, restart: str = "") -> dict:
    """Record a launch and log it in the manifest when it is new. The last launch, when it is still open (not closed
    by the driver, not superseded) and has the same role and chunks, is returned again: its agent is resumed or
    re-launched on the same parts. `restart` closes that launch as abandoned (its agent cannot be resumed) and issues
    a new one; a new launch sets aside any unfinished work on its chunks."""
    log_ = load_json(launches_path(run_dir), {"launches": []})
    last = log_["launches"][-1] if log_["launches"] else None
    same = bool(last and not last.get("superseded_at") and not last.get("closed_at") and last["role"] == role
                and last["chunks"] == chunk_ids)
    if same and restart:
        last.update(closed_at=now_iso(), outcome="abandoned", note=restart)
        same = False
    if same:
        launch = last
    else:
        launch = {"id": "L%03d" % (len(log_["launches"]) + 1), "role": role, "agent": ROLE_AGENT[role], "chunks": chunk_ids,
                  "issued_at": now_iso()}
        moved = set_aside(run_dir, launch["id"], chunk_ids, role)
        if moved:
            launch["set_aside"] = moved
        log_["launches"].append(launch)
        write_json(launches_path(run_dir), log_)
        log_invocation(run_dir, launch["agent"], "%s %s: %s%s" % (launch["id"], role, ", ".join(chunk_ids),
                                                                  " (bake-off)" if bakeoff else ""))
    path = writer(launch)
    launch = dict(launch, file=repo_path(run_dir, path))
    return launch


def pinned(run_dir: Path, agent: str) -> Tuple[str, str]:
    """(model, effort) for a worker: methodology/MODEL_POLICY.md, with the run's recorded --effort override for Opus."""
    spec = rl.model_policy()["agents"].get(agent, {})
    model, effort = spec.get("model", ""), spec.get("effort", "")
    override = (rl.load_json(run_dir / rl.RUN_MANIFEST).get("model") or {}).get("effort_override") \
        if (run_dir / rl.RUN_MANIFEST).exists() else None
    if override and model == "opus":
        effort = override
    return model, effort


def plan_next(run_dir: Path, p: dict, pol: dict, only_bakeoff: bool = False,
              exclude=()) -> Optional[Tuple[str, List[dict]]]:
    """(role, chunks) of the next launch, without recording it: resolutions first (both reads done), then critical
    reads, then reader batches. `exclude` holds chunk ids (skipped: the engine's chunks that failed twice) and
    "<chunk>:<role>" keys (that role of the chunk is being read in another session now); neither is checked here."""
    hold = pol.get("calibration", {}).get("status") == "in_progress"

    def skip(c):                      # while the in-run calibration runs, other non-critical chunks wait for its result
        return ((only_bakeoff and not c.get("bakeoff")) or c["id"] in exclude
                or any("%s:%s" % (c["id"], r) in exclude for r in ROLES)
                or (hold and not c.get("critical") and not c.get("bakeoff")))
    need_resolve = []
    for c in p["chunks"]:
        if skip(c):
            continue
        if required_roles(c, pol) == ["critical", "reader"] and check(run_dir, c["id"], "critical").ok \
                and check(run_dir, c["id"], "reader").ok:
            if compare_chunk(run_dir, c["id"]) and not check(run_dir, c["id"], "resolved").ok:
                need_resolve.append(c)
    if need_resolve:
        batch, n_dis = [], 0                  # resolutions are small: pack chunks up to about 60 disagreements
        for c in need_resolve:
            k = len(compare_chunk(run_dir, c["id"], write=False))
            if batch and (n_dis + k > 60 or len(batch) >= 6):
                break
            batch.append(c)
            n_dis += k
        return "resolved", batch
    for role in ("critical", "reader"):
        pend = [c for c in pending_for(run_dir, p, role, pol, only_bakeoff, exclude) if not skip(c)]
        if pend:
            return role, take_launch(pend)
    return None


def driver_owner(run_dir: Path) -> Optional[dict]:
    """The live engine of this run (scripts/agent_driver.py, its lock), or None."""
    lock = load_json(run_dir / "_cache" / "engine" / "engine.lock")
    if not lock:
        return None
    try:
        import os
        import socket
        if lock.get("host") != socket.gethostname():
            return lock                         # another machine: assume it is live
        os.kill(int(lock["pid"]), 0)
        return lock
    except (OSError, ValueError, KeyError):
        return None


def next_action(run_dir: Path, only_bakeoff: bool = False, exclude=(), restart: str = "") -> dict:
    """The next agent to launch, recorded in launches.json and the manifest. `only_bakeoff` restricts the loop to the
    calibration chunks (`bakeoff plan`)."""
    p = load_json(run_dir / READING / "plan.json")
    if not p:
        return {"action": "plan", "message": "run reading.py plan first"}
    rid = p["run_id"]
    pol = run_policy(run_dir)
    cal = pol.get("calibration", {})
    if cal.get("status") == "in_progress":
        sample = [c for c in p["chunks"] if c["id"] in cal.get("chunks", [])]
        if all(chunk_state(run_dir, c, pol)[0] == "read" for c in sample):
            finish_calibration(run_dir)
            pol = run_policy(run_dir)
    got = plan_next(run_dir, p, pol, only_bakeoff, exclude)
    if not got and pol.get("calibration", {}).get("status") == "in_progress" and not only_bakeoff:
        finish_calibration(run_dir)            # the sample cannot all be read (a chunk failed twice): decide on the rest
        pol = run_policy(run_dir)
        got = plan_next(run_dir, p, pol, only_bakeoff, exclude)
    if not got:
        return {"action": "done", "message": "every chunk is read, checked and reconciled; run reading.py dossiers and "
                                             "reading.py status --strict"}
    role, batch = got
    ids = [c["id"] for c in batch]
    if role == "resolved":
        launch = issue(run_dir, role, ids, lambda l: write_resolve_file(run_dir, l["id"], ids), only_bakeoff, restart)
        role_text = "resolved (adjudicate disagreements A vs B)"
    else:
        launch = issue(run_dir, role, ids, lambda l: write_launch_file(run_dir, l, batch), only_bakeoff, restart)
        role_text = role
    agent = ROLE_AGENT[role]
    model, effort = pinned(run_dir, agent)
    return {"action": "launch", "agent": agent, "role": role, "launch": launch["id"], "chunks": ids,
            "model": model, "effort": effort, "file": launch["file"],
            "description": "%s %s %s" % (agent, rid, launch["id"]),
            "prompt": agent_prompt(run_dir, rid, agent, role_text, launch["file"])}


def clear_stale_resolution(run_dir: Path, chunk_id: str) -> None:
    """Nothing to resolve: a disagreement file with no rows is kept as the record; no resolution is required."""
    return None


def write_resolve_file(run_dir: Path, launch_id: str, chunk_ids: List[str]) -> Path:
    for cid in chunk_ids:                    # the passages each disagreement refers to, for the resolver
        compare_chunk(run_dir, cid)
    lines = ["# Launch %s — resolve disagreements (agent `critical-reader`, role `resolved`)" % launch_id, "",
             "Two independent readers, **A** and **B**, read the chunks below. For each disagreement, open the passage (and "
             "the rendered PDF page when the passage is a table or the page is marked VIEW REQUIRED), decide what the "
             "document says, and write one `resolution` line per disagreement:", "",
             "```json",
             "{\"type\": \"resolution\", \"id\": \"<disagreement id>\", \"decision\": \"A|B|both|neither|corrected\", "
             "\"reason\": \"<one sentence>\", \"items\": [<the correct items, in the schema format (unit and anchor); [] "
             "when neither>]}",
             "```", "",
             "Write the lines with the Write tool into the chunk's parts directory (`01.jsonl`, then `02.jsonl`, ... for "
             "long lists) and end with a chunk receipt (`\"role\": \"resolved\"`); the check assembles the parts. The "
             "models behind A and B are not disclosed: judge only against the page. When a page is too small or sideways "
             "to read: `python3 scripts/reading.py render %s <chunk> <page> [--dpi 200] [--rotate 90|270] [--parts 2]`, "
             "then Read the image files it prints." % rel_run(run_dir),
             "", "| Chunk | Disagreements file | Passages | Parts directory | Check |", "|---|---|---|---|---|"]
    for cid in chunk_ids:
        store = load_json(run_dir / CACHE / "chunks" / ("%s.json" % cid), {})
        lines.append("| %s | `%s` | `%s` | `%s/` | `python3 scripts/reading.py check %s %s --role resolved` |" % (
            cid, repo_path(run_dir, run_dir / READING / "disagreements" / ("%s.json" % cid)), store.get("file", ""),
            repo_path(run_dir, parts_dir(run_dir, cid, "resolved")), rel_run(run_dir), cid))
    lines += ["", "Your final message is exactly one line: `%s: <n> disagreements resolved, check PASS` (or the chunk and "
                  "the error you could not fix)." % launch_id]
    out = run_dir / CACHE / "launches" / ("%s.md" % launch_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------------------------------------------
# Check (the readers run it; next, compare and status rely on it)
# --------------------------------------------------------------------------------------------------------------

def read_jsonl(path: Path, res: rl.Result, label: str = "") -> List[dict]:
    """JSON objects of a JSONL file; each carries `_line` and `_where` ("line 7", or "02.jsonl line 7" for a part)."""
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        where = "%s line %d" % (label, n) if label else "line %d" % n
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError as exc:
            res.error("%s: not valid JSON (%s)" % (where, exc))
            continue
        if not isinstance(obj, dict):
            res.error("%s: not a JSON object" % where)
            continue
        obj["_line"] = n
        obj["_where"] = where
        out.append(obj)
    return out


def span_ids(it: dict, store: dict) -> Tuple[List[str], str]:
    """(passage ids, error) an item's quote may draw on: with `to`, every passage from `unit` to `to` in reading order
    (the whole fact, across pages: a key audit matter, a claim, a note); otherwise the cited passage and the passages
    after it on its page (QUOTE_SPAN at most)."""
    uid = str(it.get("unit"))
    if not it.get("to"):
        return [uid] + store.get("_after", {}).get(uid, []), ""
    order = store.get("order", [])
    pos = {u: i for i, u in enumerate(order)}
    to = str(it["to"])
    if uid not in pos or to not in pos:
        return [], "to %r is not a passage of this chunk" % to
    if pos[to] < pos[uid]:
        return [], "to %s comes before unit %s" % (to, uid)
    if pos[to] - pos[uid] + 1 > PROSE_SPAN_MAX:
        return [], "to %s: a span of %d passages (at most %d; tag a long table with a table item)" % (
            to, pos[to] - pos[uid] + 1, PROSE_SPAN_MAX)
    return order[pos[uid]:pos[to] + 1], ""


def derive_quote(it: dict, store: dict, spec: dict, rel_text: List[str]) -> Tuple[str, str]:
    """(quote, error) for an item that cites a passage and an anchor: the printed text of the cited passage, run on
    into the passages after it on the same page (QUOTE_SPAN at most) until it holds the anchor, every amount field and
    every number written in any other field; with `to`, the whole span. The reader copies a few words; the script
    copies the text."""
    uid = str(it.get("unit"))
    ids, err = span_ids(it, store)
    if err:
        return "", err
    norms = [norm_quote(store["units"][x]["text"]) for x in ids]
    a = norm_quote(str(it.get("anchor") or ""))
    if len(a) > ANCHOR_MAX:
        return "", "anchor longer than %d characters: copy a few words of the passage, not the passage" % ANCHOR_MAX
    if len(a.split()) < ANCHOR_MIN_WORDS and a != norms[0]:
        return "", ("anchor %r: copy at least %d consecutive words of the passage (or the whole passage when it is "
                    "shorter)" % (a, ANCHOR_MIN_WORDS))
    at = " ".join(norms).find(a)
    if at < 0 or at >= len(norms[0]):
        return "", "anchor %r is not printed verbatim in passage %s (it must start there)" % (a[:80], uid)
    fields = it.get("fields") if isinstance(it.get("fields"), dict) else {}
    amount_fields = spec.get("amounts", [])
    amounts = [str(fields.get(f) or "").strip() for f in amount_fields if str(fields.get(f) or "").strip()]
    nums = set()
    for f, v in fields.items():
        if f not in amount_fields:
            nums.update(number_tokens(v))
    if it.get("type") == "unusual":
        for x in rel_text:
            nums -= set(number_tokens(x))
    end, raw = at + len(a), ""
    if it.get("to"):                                   # the whole span is the quote
        raw = " ".join(norm_space(store["units"][x]["text"]) for x in ids)
        qa, toks = norm_amount(raw), set(number_tokens(raw))
        missing = [v for v in amounts if norm_amount(v) not in qa] + sorted(n for n in nums if n not in toks)
        if missing:
            return "", "%s not printed in passages %s to %s (copy numbers exactly as printed; never compute)" % (
                ", ".join(missing[:4]), uid, it["to"])
        return raw, ""
    for k in range(len(ids)):
        raw = " ".join(norm_space(store["units"][x]["text"]) for x in ids[:k + 1])
        if len(" ".join(norms[:k + 1])) < end:
            continue
        qa, toks = norm_amount(raw), set(number_tokens(raw))
        if all(norm_amount(v) in qa for v in amounts) and nums <= toks:
            return raw, ""
    qa, toks = norm_amount(raw), set(number_tokens(raw))
    missing = [v for v in amounts if norm_amount(v) not in qa] + sorted(n for n in nums if n not in toks)
    return "", ("%s not printed in passage %s or the %d passage(s) after it on its page (copy numbers exactly as printed; "
                "never compute)" % (", ".join(missing[:4]) or "a value", uid, len(ids) - 1))


def check_item(it: dict, store: dict, sch: dict, res: rl.Result, where: str) -> None:
    t = it.get("type")
    spec = sch["types"].get(t)
    if spec is None:
        res.error("%s: unknown item type %r (see methodology/READING_SCHEMAS.md)" % (where, t))
        return
    for k in ("unit", "page", "period", "basis", "fields"):
        if k not in it:
            res.error("%s (%s): missing key %r" % (where, t, k))
    unit = store["units"].get(str(it.get("unit", "")))
    if unit is None:
        res.error("%s (%s): unit %r is not a passage of this chunk (repeats ⟲ are not cited)" % (where, t, it.get("unit")))
        return
    if it.get("page") != unit["page"]:
        res.error("%s (%s): page %r but passage %s is on page %d" % (where, t, it.get("page"), it.get("unit"), unit["page"]))
    if it.get("basis", "na") not in ("standalone", "consolidated", "na", ""):
        res.error("%s (%s): basis must be standalone, consolidated or na" % (where, t))
    fields = it.get("fields") if isinstance(it.get("fields"), dict) else None
    if fields is None:
        res.error("%s (%s): fields must be an object" % (where, t))
        fields = {}
    missing = [f for f in spec.get("key", spec["fields"]) if f not in fields]
    if missing:
        res.error("%s (%s): key fields missing %s (use \"\" when not stated)" % (where, t, missing))
    for f, v in fields.items():
        if f not in spec.get("key", spec["fields"]) and len(str(v).split()) > NON_KEY_WORDS:
            res.warn("%s (%s): %s has %d words: a non-key field is a short label; the dossier prints the passage itself"
                     % (where, t, f, len(str(v).split())))
    related = it.get("related", [])
    if not isinstance(related, list):
        res.error("%s (%s): related must be a list of passage ids of this chunk" % (where, t))
        related = []
    rel_text = []
    for r_id in related:
        ru = store["units"].get(str(r_id))
        if ru is None:
            res.error("%s (%s): related %r is not a passage of this chunk" % (where, t, r_id))
        else:
            rel_text.append(ru.get("text", ""))
    if unit.get("visual"):
        if it.get("source") != "rendered":
            res.error("%s (%s): an item cited to the rendered page p%s must have \"source\": \"rendered\"" % (where, t, unit["page"]))
        return
    quote = str(it.get("quote") or "")
    if not quote.strip():
        if not str(it.get("anchor") or "").strip():
            res.error("%s (%s): give an anchor: a few words copied verbatim from passage %s" % (where, t, it.get("unit")))
            return
        quote, err = derive_quote(it, store, spec, rel_text)
        if err:
            res.error("%s (%s): %s" % (where, t, err))
            return
        it["quote"], it["quote_by"] = quote, "script"
    elif len(quote) > 600 and it.get("quote_by") != "script":
        res.error("%s (%s): quote longer than 600 characters (keep quotes to 500)" % (where, t))
    base = norm_quote(unit["text"])
    ids, err = span_ids(it, store)
    if err:
        res.error("%s (%s): %s" % (where, t, err))
        return
    hay = base + "".join(" " + norm_quote(store["units"][x]["text"]) for x in ids[1:])
    at = hay.find(norm_quote(quote))
    if at < 0 or at >= len(base):
        res.error("%s (%s): quote not found verbatim starting in passage %s on page %s: %r" % (
            where, t, it.get("unit"), unit["page"], quote[:80]))
        return
    qa = norm_amount(quote)
    for f in spec.get("amounts", []):
        v = str(fields.get(f) or "").strip()
        if v and norm_amount(v) not in qa:
            res.error("%s (%s): %s %r is not printed in the quote (copy amounts exactly as printed)" % (where, t, f, v))
    # Every number written anywhere in the fields is printed in the quote (an `unusual` item may also take numbers from
    # its related passages): a value outside the quote is unverified, and a computed one is not the document's.
    allowed = set(number_tokens(quote)) | set(it.get("_allowed") or [])
    if t == "unusual":
        for x in rel_text:
            allowed |= set(number_tokens(x))
    for f, v in fields.items():
        if f in spec.get("amounts", []):
            continue
        bad = [x for x in number_tokens(v) if x not in allowed]
        if bad:
            res.error("%s (%s): field %s has %s, not printed in the quote%s (copy numbers as printed; never compute)" % (
                where, t, f, ", ".join(bad[:4]), " or its related passages" if t == "unusual" else ""))


VALUE_RE = re.compile(r"^(?:%s)$" % NUM_TOKEN, re.I)


def is_table_row(text: str) -> bool:
    return bool(TABLE_ROW_RE.match(text.strip())) or "│" in text


def table_cells(text: str) -> List[str]:
    """The cells of a table row as the text layer printed it (`| a | b |`, or cells separated by `│`), stripped."""
    s = text.strip()
    if TABLE_ROW_RE.match(s):
        s = s[1:-1]
    return [c.strip() for c in re.split(r"[|│]", s)]


def label_field_of(spec: dict, static: dict) -> str:
    for f in spec["fields"]:
        if f not in spec["amounts"] and f not in static and not f.startswith("unit_of_"):
            return f
    return ""


def table_rows(store: dict, ids: List[str], layout: str, label_cell: int, errs: List[str], skip: dict, covered: set):
    """(first passage, label, value cells, last passage) of each row of a table span. `rows`: every table-row passage
    is a row (its cells as printed, empty ones kept). `cells`: a label passage and the value passages after it; a value
    passage with no label before it is an error unless covered by the reader's own item or named in skip."""
    if layout == "rows":
        for u in ids:
            text = store["units"][u]["text"]
            if is_table_row(text):
                cells = table_cells(text)
                yield u, (cells[label_cell - 1] if 0 < label_cell <= len(cells) else ""), cells, u
        return
    i = 0
    while i < len(ids):
        u = ids[i]
        if VALUE_RE.match(norm_space(store["units"][u]["text"])):
            if u not in skip and u not in covered:
                errs.append("value passage %s %r has no label before it: write its item yourself or name it in skip" % (
                    u, norm_space(store["units"][u]["text"])[:30]))
            i += 1
            continue
        j = i + 1
        while j < len(ids) and VALUE_RE.match(norm_space(store["units"][ids[j]]["text"])):
            j += 1
        vals = [norm_space(store["units"][x]["text"]) for x in ids[i + 1:j]]
        yield u, norm_space(store["units"][u]["text"]), (vals if vals else []), ids[j - 1]
        i = j


def expand_table(tag: dict, store: dict, sch: dict, covered: set) -> Tuple[List[dict], List[str]]:
    """The items of a table tag: one per row passage from `unit` to `to` (one per period with `series`), each field
    copied from its cell exactly as printed, the row's printed text as the quote. A row whose mapped cells are all
    empty is a heading (it becomes the `section` of the rows below it). A row the reader already wrote an item for is
    left to that item. A row whose mapped cells are not values (merged cells, a text cell, a different layout) is an
    error unless the tag's `skip` names it with the reason: such a row needs its own item, so nothing is lost."""
    f = tag.get("fields") if isinstance(tag.get("fields"), dict) else {}
    errs, items = [], []
    t = f.get("item_type")
    spec = sch["types"].get(t)
    if not spec or not spec.get("amounts") or t == "table":
        return [], ["item_type %r must be a schema type with amount fields" % t]
    order = store.get("order", [])
    pos = {u: i for i, u in enumerate(order)}
    a, b = str(tag.get("unit")), str(tag.get("to") or tag.get("unit"))
    if a not in pos or b not in pos:
        return [], ["unit %s and to %s must be passages of this chunk" % (a, b)]
    if pos[b] < pos[a] or pos[b] - pos[a] + 1 > TABLE_SPAN_MAX:
        return [], ["to %s must come after unit %s, within %d passages" % (b, a, TABLE_SPAN_MAX)]
    try:
        label_cell = int(f.get("label_cell", 1))
    except (TypeError, ValueError):
        return [], ["label_cell must be the 1-based cell number of the row label"]
    static = f.get("static") or {}
    columns, series = f.get("columns") or {}, f.get("series") or {}
    skip = f.get("skip") or {}
    if not isinstance(static, dict) or not isinstance(columns, dict) or not isinstance(series, dict) or not isinstance(skip, dict):
        return [], ["static, columns, series and skip must be objects"]
    if bool(columns) == bool(series):
        return [], ["give exactly one of columns ({\"<amount field>\": <cell>}) or series ({\"<period>\": <cell>})"]
    bad_static = [k for k in static if k not in spec["fields"] or k in spec["amounts"]]
    if bad_static:
        errs.append("static %s: not non-amount fields of %s" % (bad_static, t))
    if columns and not set(columns) <= set(spec["amounts"]):
        return [], ["columns %s: the keys must be amount fields of %s (%s)" % (sorted(columns), t, ", ".join(spec["amounts"]))]
    series_field = f.get("series_field") or spec["amounts"][0]
    if series and series_field not in spec["amounts"]:
        return [], ["series_field %r is not an amount field of %s" % (series_field, t)]
    mapping = columns or series
    try:
        mapping = {k: int(v) for k, v in mapping.items()}
    except (TypeError, ValueError):
        return [], ["the cell numbers in columns / series must be integers (1 = the first cell)"]
    label_field = f.get("label_field") or label_field_of(spec, static)
    if label_field not in spec["fields"] or label_field in spec["amounts"]:
        return [], ["label_field %r is not a non-amount field of %s" % (label_field, t)]
    nums_static = set(number_tokens(" ".join(str(v) for v in static.values())))
    span_text = " ".join(store["units"][u]["text"] for u in order[pos[a]:pos[b] + 1])
    if nums_static - set(number_tokens(span_text)):
        errs.append("static values carry numbers not printed in the table: %s" % sorted(nums_static - set(number_tokens(span_text))))
    layout = f.get("layout", "rows")
    if layout not in ("rows", "cells"):
        return [], ["layout must be rows (a table row per passage) or cells (the label, then its values, a passage each)"]
    try:
        per_row = int(f.get("values_per_row", 0))
    except (TypeError, ValueError):
        per_row = 0
    if layout == "cells" and (per_row < 1 or any(not 0 < i <= per_row for i in mapping.values())):
        return [], ["layout cells needs values_per_row (the number of value cells every row prints) and columns / series "
                    "numbered 1..values_per_row (1 = the first value after the label)"]
    headers: List[str] = []
    prev_head = None                               # (passage, label) of a label-only row just before this one
    for u, label, cells, last in table_rows(store, order[pos[a]:pos[b] + 1], layout, label_cell, errs, skip, covered):
        if layout == "rows" and not label and prev_head and order.index(u) == order.index(prev_head[0]) + 1 \
                and any(c for c in cells):
            u, label = prev_head                   # a wrapped label: its values print on the row after it
            headers = headers[:-1] if headers and headers[-1] == label else headers
        prev_head = None
        if u in skip:                              # column headings, or rows the reader wrote itself
            continue
        unit = store["units"][u]
        text = " ".join(norm_space(store["units"][x]["text"]) for x in order[pos[u]:pos[last] + 1])
        if layout == "cells" and not cells:            # a label with no values under it: a heading
            if label:
                headers = (headers + [label])[-2:]
            continue
        if layout == "cells" and len(cells) != per_row:
            errs.append("row %s %r has %d value cells, not %d: write this row's item yourself (a missing cell would "
                        "shift its values into the wrong column), or name it in skip with the reason" % (
                            u, label[:50], len(cells), per_row))
            continue
        vals = {k: (cells[i - 1] if 0 < i <= len(cells) else None) for k, i in mapping.items()}
        if u in covered:
            continue
        if all(v == "" for v in vals.values()):
            if label:
                headers = (headers + [label])[-2:]
                prev_head = (u, label)
            continue
        bad = sorted(k for k, v in vals.items() if v is None or (v and not VALUE_RE.match(norm_space(v))))
        if bad:
            if u not in skip:
                errs.append("row %s %r: the cell(s) mapped to %s are not values (cells: %s); write this row's item "
                            "yourself, or name it in skip with the reason" % (u, norm_space(text)[:60], ", ".join(bad), cells))
            continue
        base = {fld: "" for fld in spec["key"]}
        base.update({k: str(v) for k, v in static.items()})
        base[label_field] = label
        periods = [(None, vals)] if columns else [(per, {series_field: v}) for per, v in vals.items() if v != ""]
        for per, vv in periods:
            fields = dict(base)
            fields.update(vv)
            if per and "period_label" in spec["fields"] and "period_label" not in static:
                fields["period_label"] = per
            items.append({"type": t, "unit": u, "page": unit["page"], "period": per or tag.get("period", ""),
                          "basis": tag.get("basis", "na"), "fields": fields, "section": " / ".join(headers),
                          "quote": text, "quote_by": "script", "from_table": a,
                          **({"to": last} if last != u else {}),
                          "_allowed": sorted(set(number_tokens(span_text))),   # headings print the years and units
                          "_where": "%s (table %s, row %s%s)" % (tag.get("_where", ""), a, u, ", " + per if per else "")})
    return items, errs


def check(run_dir: Path, chunk_id: str, role: str, write: bool = True) -> rl.Result:
    """Verify a reader's output. When the reader wrote parts, they are read in order and (with `write`) assembled
    into the extraction file, each anchored item carrying the quote the script attached; errors name the part."""
    res, rows, from_parts = _check(run_dir, chunk_id, role)
    if from_parts and write and rows is not None:
        out = extraction_path(run_dir, chunk_id, role)
        text = "".join(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False) + "\n"
                       for r in rows)
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
    return res


def _check(run_dir: Path, chunk_id: str, role: str) -> Tuple[rl.Result, Optional[List[dict]], bool]:
    res = rl.Result("%s.%s" % (chunk_id, role))
    path = extraction_path(run_dir, chunk_id, role)
    parts = part_files(run_dir, chunk_id, role)
    if not parts and not path.exists():
        res.error("no extraction: write the items in parts to %s/ (01.jsonl, 02.jsonl, ...)" % repo_path(
            run_dir, parts_dir(run_dir, chunk_id, role)))
        return res, None, False
    try:
        store = chunk_cache(run_dir, chunk_id)
    except FileNotFoundError as exc:
        res.error(str(exc))
        return res, None, False
    store["_after"] = {}
    order = store.get("order", [])
    for i, a in enumerate(order):              # a quote may run on into the passages that follow on the same page
        pg_a = store["units"][a]["page"]
        store["_after"][a] = [b for b in order[i + 1:i + 1 + QUOTE_SPAN] if store["units"][b]["page"] == pg_a]
    sch = schema()
    if parts:
        rows = [r for pf in parts for r in read_jsonl(pf, res, pf.name)]
    else:
        rows = read_jsonl(path, res)
    receipts = [r for r in rows if r.get("type") == "chunk_receipt"]
    pages_rc = [r for r in rows if r.get("type") == "page_receipt"]
    resolutions = [r for r in rows if r.get("type") == "resolution"]
    items = [r for r in rows if r.get("type") not in ("chunk_receipt", "page_receipt", "resolution")]
    if len(receipts) != 1:
        res.error("expected exactly one chunk_receipt, found %d" % len(receipts))
    else:
        rc = receipts[0]
        if rc.get("chunk") != chunk_id:
            res.error("chunk_receipt.chunk %r is not %s" % (rc.get("chunk"), chunk_id))
        if rc.get("role") != role:
            res.error("chunk_receipt.role %r is not %s" % (rc.get("role"), role))
        if not str(rc.get("model") or "").strip():
            res.error("chunk_receipt.model is empty (copy the model id from your system context)")
        if role != "resolved":
            if rc.get("units_read") != store["new_units"]:
                res.error("chunk_receipt.units_read %r but the chunk has %d passages" % (rc.get("units_read"), store["new_units"]))
            need = set(view_pages(store))
            got = set(rc.get("pages_viewed") or [])
            if need - got:
                res.error("pages_viewed lacks the VIEW REQUIRED pages %s" % sorted(need - got))
    if role == "resolved":
        dis = load_json(run_dir / READING / "disagreements" / ("%s.json" % chunk_id), {"disagreements": []})["disagreements"]
        want = {d["id"] for d in dis}
        got = Counter(r.get("id") for r in resolutions)
        for d in sorted(want - set(got)):
            res.error("disagreement %s has no resolution" % d)
        for d, n in got.items():
            if d not in want:
                res.error("resolution for unknown disagreement %r" % d)
            elif n > 1:
                res.error("disagreement %s resolved %d times" % (d, n))
        for r in resolutions:
            if r.get("decision") not in ("A", "B", "both", "neither", "corrected"):
                res.error("resolution %s: decision must be A, B, both, neither or corrected" % r.get("id"))
            if not str(r.get("reason") or "").strip():
                res.error("resolution %s: reason is required" % r.get("id"))
            for k, it in enumerate(r.get("items") or [], 1):
                check_item(it, store, sch, res, "%s: resolution %s item %d" % (r["_where"], r.get("id"), k))
        return res, rows, bool(parts)
    tables = [it for it in items if it.get("type") == "table"]
    items = [it for it in items if it.get("type") != "table"]
    covered = {str(it.get("unit")) for it in items}
    expanded: Dict[int, List[dict]] = {}
    for tg in tables:
        where = tg["_where"]
        unit = store["units"].get(str(tg.get("unit", "")))
        if unit is None or unit.get("visual"):
            res.error("%s (table): unit %r is not a text passage of this chunk" % (where, tg.get("unit")))
            continue
        if tg.get("page") != unit["page"]:
            res.error("%s (table): page %r but passage %s is on page %d" % (where, tg.get("page"), tg.get("unit"), unit["page"]))
        a = norm_quote(str(tg.get("anchor") or ""))
        if not a or a not in norm_quote(unit["text"]):
            res.error("%s (table): anchor %r is not printed in passage %s (copy a few words of the table's first row or "
                      "title)" % (where, str(tg.get("anchor") or "")[:60], tg.get("unit")))
        rows_, errs = expand_table(tg, store, sch, covered)
        for e in errs:
            res.error("%s (table %s): %s" % (where, tg.get("unit"), e))
        expanded[id(tg)] = rows_
        items += rows_
    for it in items:
        check_item(it, store, sch, res, it["_where"])
    if expanded:                       # the assembled extraction carries every expanded row after its table tag
        rows = [x for r in rows for x in [r] + expanded.get(id(r), [])]
    need_pages = set(store["pages"])
    rc_by_page = defaultdict(list)
    for r in pages_rc:
        rc_by_page[r.get("page")].append(r)
    cited = Counter(it.get("page") for it in items + tables)
    for pg in sorted(need_pages):
        rcs = rc_by_page.get(pg, [])
        if len(rcs) != 1:
            res.error("page %d: expected one page_receipt, found %d" % (pg, len(rcs)))
            continue
        r = rcs[0]
        if r.get("status") not in ("items", "no_items"):
            res.error("page %d: page_receipt.status must be items or no_items" % pg)
        elif r["status"] == "items" and not cited.get(pg):
            res.error("page %d: receipt says items but no item cites the page" % pg)
        elif r["status"] == "no_items" and cited.get(pg):
            res.error("page %d: receipt says no_items but %d item(s) cite the page" % (pg, cited[pg]))
        elif r["status"] == "no_items" and not str(r.get("reason") or "").strip():
            res.error("page %d: a no_items receipt needs a reason" % pg)
        if pg in set(view_pages(store)) and r.get("viewed") is not True:
            res.error("page %d is VIEW REQUIRED: its receipt must say \"viewed\": true" % pg)
    extra = set(rc_by_page) - need_pages
    if extra:
        res.error("page receipts for pages outside this chunk: %s" % sorted(extra))
    return res, rows, bool(parts)


# --------------------------------------------------------------------------------------------------------------
# Compare the two reads of a chunk
# --------------------------------------------------------------------------------------------------------------

KEY_FIELDS = {"audit_opinion": ("opinion",), "ifc_opinion": ("opinion",), "caro_clause": ("clause", "adverse"),
              "credit_rating": ("rating",), "shareholder_resolution": ("outcome",)}


def items_of(run_dir: Path, chunk_id: str, role: str) -> List[dict]:
    path = extraction_path(run_dir, chunk_id, role)
    if not path.exists():
        return []
    res = rl.Result("")
    return [r for r in read_jsonl(path, res) if r.get("type") not in ("chunk_receipt", "page_receipt", "resolution", "table")]


def item_sig(it: dict, sch: dict) -> tuple:
    """What two reads must agree on: each amount in its own field (a current-year value given as the prior year's is a
    disagreement), and the key answers (opinion, CARO answer, rating, outcome)."""
    spec = sch["types"].get(it.get("type"), {"amounts": []})
    f = it.get("fields") or {}
    amounts = tuple((a, norm_amount(f.get(a, ""))) for a in spec.get("amounts", []) if str(f.get(a, "")).strip())
    keys = tuple(norm_quote(str(f.get(k, ""))).lower() for k in KEY_FIELDS.get(it.get("type"), ()))
    return amounts, keys


def compare_chunk(run_dir: Path, chunk_id: str, write: bool = True) -> List[dict]:
    sch = schema()
    a, b = items_of(run_dir, chunk_id, "critical"), items_of(run_dir, chunk_id, "reader")
    ga, gb = defaultdict(list), defaultdict(list)
    for it in a:
        ga[(it.get("unit"), it.get("type"))].append(it)
    for it in b:
        gb[(it.get("unit"), it.get("type"))].append(it)
    dis = []
    for key in sorted(set(ga) | set(gb), key=lambda k: (str(k[0]), str(k[1]))):
        xa, xb = ga.get(key, []), gb.get(key, [])
        if not xa or not xb:
            kind = "only_A" if xa else "only_B"
        else:
            sa = sorted(item_sig(i, sch) for i in xa)
            sb = sorted(item_sig(i, sch) for i in xb)
            if sa == sb:
                continue
            kind = "differ"
        page = (xa or xb)[0].get("page")
        dis.append({"id": "%s-d%03d" % (chunk_id, len(dis) + 1), "kind": kind, "unit": key[0], "type": key[1], "page": page,
                    "A": [{k: v for k, v in i.items() if not k.startswith("_")} for i in xa],
                    "B": [{k: v for k, v in i.items() if not k.startswith("_")} for i in xb]})
    if write:
        store = load_json(run_dir / CACHE / "chunks" / ("%s.json" % chunk_id), {"units": {}})
        for d in dis:
            u = store["units"].get(str(d["unit"]), {})
            d["passage"] = u.get("text", "")
        data = {"chunk": chunk_id, "count": len(dis), "disagreements": dis,
                "agreed": sum(1 for k in set(ga) & set(gb) if sorted(item_sig(i, sch) for i in ga[k]) == sorted(item_sig(i, sch) for i in gb[k]))}
        path = run_dir / READING / "disagreements" / ("%s.json" % chunk_id)
        if load_json(path) != data:
            write_json(path, data)
    return dis


def final_items(run_dir: Path, chunk: dict, policy: Optional[dict] = None) -> List[dict]:
    roles = required_roles(chunk, policy)
    if roles == ["reader"]:
        return items_of(run_dir, chunk["id"], "reader")
    sch = schema()
    a, b = items_of(run_dir, chunk["id"], "critical"), items_of(run_dir, chunk["id"], "reader")
    ga, gb = defaultdict(list), defaultdict(list)
    for it in a:
        ga[(it.get("unit"), it.get("type"))].append(it)
    for it in b:
        gb[(it.get("unit"), it.get("type"))].append(it)
    out = []
    for k in set(ga) & set(gb):
        if sorted(item_sig(i, sch) for i in ga[k]) == sorted(item_sig(i, sch) for i in gb[k]):
            out.extend(ga[k])
    path = extraction_path(run_dir, chunk["id"], "resolved")
    if path.exists():
        for r in read_jsonl(path, rl.Result("")):
            if r.get("type") == "resolution":
                out.extend(r.get("items") or [])
    return out


# --------------------------------------------------------------------------------------------------------------
# Dossiers and packs
# --------------------------------------------------------------------------------------------------------------

SERIES_TYPES = ("statement_line", "segment_data", "kpi", "esg_metric", "revenue_disaggregation", "csr",
                "subsidiary_financials", "auditor_fee", "dividend", "remuneration", "contingent_liability", "commitment",
                "rpt_transaction", "rpt_balance", "borrowing", "debt_maturity", "provision_movement", "exceptional_item",
                "market_or_industry_data", "disclosed_number")
PACK_BUDGET = 150000          # tokens of must-read dossiers one specialist session reads comfortably (reported, not cut)
NOTE_REF_RE = re.compile(r"\((?:refer(?:\s+to)?\s+)?notes?\s*[^)]*\)|\bnotes?\s+\d[\d.()a-z]*\s*$", re.I)


def series_key(it: dict, spec: dict, doc_key: str = "") -> Tuple[tuple, str]:
    """(key, label) of the series an item belongs to: its type, basis, unit and label fields (and the headings it sits
    under), compared without note references, case or punctuation. Labels worded differently stay separate series; an
    item with no label at all is a series of its own (nothing identifies it across years)."""
    f = it.get("fields") or {}
    parts = [str(f.get(k, "")) for k in spec.get("key", spec["fields"])
             if k not in spec["amounts"] and not k.startswith("unit_of") and k != "period_label"]
    if it.get("section"):
        parts = [str(it["section"])] + parts
    label = " · ".join(norm_space(x) for x in parts if str(x).strip()) or "(no label)"
    unit = str(f.get("unit_of_amount") or f.get("unit_of_value") or "")
    norm = tuple(re.sub(r"[^a-z0-9%]+", " ", NOTE_REF_RE.sub(" ", x).lower()).strip() for x in parts)
    if not any(norm):
        norm = ("(no label)", doc_key, str(it.get("unit")), str(it.get("to") or ""))
    return (it.get("type"), it.get("basis", ""), unit.lower().strip(), norm), label


def series_cells(it: dict, spec: dict, doc: dict) -> List[Tuple[str, str, str]]:
    """[(period, value as printed, current|prior|single)]: an annual report's current and prior columns are its own
    fiscal year and the one before (the prior column is that year as compared a year later)."""
    f = it.get("fields") or {}
    am = spec["amounts"]
    fy = fiscal_year(doc["period"]) if doc["doc_type"] == "annual_report" else 0
    cur = [a for a in am if a.endswith("_current")]
    if cur and fy:
        out = []
        for a in cur:
            base = a[:-len("_current")]
            lab = "" if len(cur) == 1 else base + " "
            if str(f.get(a, "")).strip():
                out.append(("FY%d" % fy, lab + str(f[a]), "current"))
            if str(f.get(base + "_prior", "")).strip():
                out.append(("FY%d" % (fy - 1), lab + str(f[base + "_prior"]), "prior"))
        return out
    vals = "; ".join(("%s %s" % (a, f[a]) if len(am) > 1 else str(f[a])) for a in am if str(f.get(a, "")).strip())
    if not vals:
        return []
    per = str(f.get("period_label") or it.get("period") or ("FY%d" % fy if fy else doc["period"]))
    return [(per, vals, "single")]


def period_order(per: str) -> tuple:
    years = [int(y) for y in re.findall(r"(?:19|20)\d\d", per)]
    q = re.search(r"Q([1-4])", per)
    return (max(years) if years else 0, int(q.group(1)) if q else 9, per)


def dossier_line(r: dict, docs: dict) -> str:
    fields = "; ".join("%s: %s" % (k, v) for k, v in (r.get("fields") or {}).items() if str(v).strip())
    extra = " (also in: %s)" % ", ".join(r["also_in"][:8]) + (" …" if len(r["also_in"]) > 8 else "") if r.get("also_in") else ""
    src = " [rendered page]" if r.get("source") == "rendered" else ""
    span = "%s–%s" % (r.get("unit"), r["to"]) if r.get("to") else str(r.get("unit"))
    quote = norm_space(r.get("quote", ""))
    return "- **%s** · p.%s · %s · %s%s%s `[%s %s p.%s]`%s" % (
        r["type"], r.get("page"), r.get("period") or "-", fields or "-", src, " — \"%s\"" % quote if quote else "",
        r["doc"], span, r.get("page"), extra)


def dossiers(run_dir: Path, log=print) -> dict:
    """Topic dossiers from the verified items, in three parts. **Series**: every number of every recurring line
    (statement lines, segments, KPIs, contingent liabilities, related-party amounts, ESG metrics ...) on one line across
    all years and documents, with the page of each value; where a later report prints a different comparative for a year
    than the report of that year, both are shown and flagged (restated or reclassified?). **Material items**: every item
    of a material type, with its whole printed text. **Reference** (`<topic>.reference.md`): every other item, with its
    text. A specialist's pack lists the series and material part of each topic it owns as must-read (the reading audit
    checks it) and the reference part as searchable, with the token size of each."""
    p = load_json(run_dir / READING / "plan.json")
    if not p:
        raise SystemExit("no plan")
    sch = schema()
    pol = run_policy(run_dir)
    docs = {d["key"]: d for d in p["documents"]}
    order = {d["key"]: i for i, d in enumerate(p["documents"])}
    also = defaultdict(list)
    for d in p["documents"]:
        uf = load_json(run_dir / CACHE / "units" / ("%s.json" % d["key"]), {"pages": {}})
        for pg, units in uf["pages"].items():
            for u in units:
                if u.get("status") in ("repeat", "context"):
                    also[u["repeat_of"]].append("%s p.%s" % (d["key"], pg))
    series = defaultdict(dict)                         # topic -> key -> {label, type, basis, unit, cells}
    material, reference = defaultdict(list), defaultdict(list)
    unusual = 0
    n_items = 0
    for c in p["chunks"]:
        units = load_json(run_dir / CACHE / "chunks" / ("%s.json" % c["id"]), {"units": {}})["units"]
        doc = docs[c["doc"]]
        for it in final_items(run_dir, c, pol):
            spec = sch["types"].get(it.get("type"))
            if not spec or it.get("type") == "table":
                continue
            n_items += 1
            gid = units.get(str(it.get("unit")), {}).get("gid", "")
            rec = dict(it, doc=c["doc"], chunk=c["id"], also_in=also.get(gid, []))
            topic = spec["topic"]
            cells = series_cells(it, spec, doc) if it.get("type") in SERIES_TYPES else []
            if cells:
                key, label = series_key(it, spec, c["doc"])
                s = series[topic].setdefault(key, {"label": label, "type": it["type"], "basis": it.get("basis", ""),
                                                   "unit": key[2], "cells": defaultdict(list),
                                                   "quote": norm_space(it.get("quote", "")) if label == "(no label)" else ""})
                for per, val, kind in cells:
                    s["cells"][per].append((val, kind, c["doc"], it.get("page"), it.get("unit"), it.get("source")))
            elif spec.get("material"):
                material[topic].append(rec)
            else:
                reference[topic].append(rec)
            unusual += it.get("type") == "unusual"
    out_dir = run_dir / DOSSIERS
    out_dir.mkdir(parents=True, exist_ok=True)
    index_rows, flags_total = [], 0
    head = ("Run %s · built by `scripts/reading.py dossiers` from quote-verified reader extractions (critical sections read "
            "twice and reconciled; tables expanded row by row from the page by script). **A finding aid, not a source:** "
            "cite the document and page, and confirm decision-critical items on the page (`doc_text.py page|verify`) before "
            "citing them. Text printed word for word in other years or sections is read once and listed once, with "
            "`also in`. Items marked [rendered page] were read from the page image." % p["run_id"])
    for topic, meta in sch["topics"].items():
        ss = sorted(series.get(topic, {}).values(), key=lambda s: (s["type"], s["label"].lower()))
        flags = []
        lines = ["# Dossier: %s" % meta["title"], "", head, ""]
        if ss:
            lines += ["## Series — every value across years (%d series)" % len(ss), "",
                      "One line per recurring line item: each period's value as printed, with its document and page. "
                      "An annual report's prior-year column is that year as compared a year later; `≠` marks a year "
                      "whose value differs between reports (restated or reclassified?: check both pages).", ""]
            for s in ss:
                parts = []
                for per in sorted(s["cells"], key=period_order, reverse=True):
                    vals = sorted(s["cells"][per], key=lambda v: (order.get(v[2], 999), v[1] != "prior"))  # latest report first
                    by_doc = {}                    # document -> its distinct values for this period (in order)
                    where = defaultdict(list)       # value -> where it is printed
                    for val, kind, dk, pg, u, src in vals:
                        nv = norm_amount(val)
                        by_doc.setdefault(dk, [])
                        if nv not in by_doc[dk]:
                            by_doc[dk].append(nv)
                        where[nv].append("%s p.%s%s" % (dk, pg, " [rendered]" if src == "rendered" else ""))
                    printed = {norm_amount(v[0]): v[0] for v in vals}
                    groups = []                     # one group per distinct set of values; reports that agree share it
                    for dk, nvs in by_doc.items():
                        if tuple(nvs) not in [g for g in groups]:
                            groups.append(tuple(nvs))
                    shown = [" | ".join("%s (%s)" % (printed[nv], ", ".join(dict.fromkeys(where[nv]))) for nv in g)
                             for g in groups]
                    if len(groups) > 1:            # two reports print different values for the same year
                        flags.append("%s · %s: %s" % (s["label"], per, " ≠ ".join(shown)))
                    parts.append("%s %s" % (per, " ≠ ".join(shown)))
                lines.append("- **%s** · %s · %s%s: %s%s" % (s["label"], s["type"], s["basis"] or "-",
                                                           " · " + s["unit"] if s["unit"] else "", " · ".join(parts),
                                                           " — \"%s\"" % s["quote"] if s["quote"] else ""))
            lines.append("")
        if flags:
            lines[4:4] = ["## Changed comparatives (%d)" % len(flags), "",
                          "Years whose value differs between two reports of the same company (a later report's "
                          "comparative against the report of that year): restatements, reclassifications or regrouping "
                          "to check on both pages.", ""] + ["- %s" % f for f in flags] + [""]
            flags_total += len(flags)
        mat = sorted(material.get(topic, []), key=lambda r: (order.get(r["doc"], 999), r.get("page", 0)))
        lines += ["## Material items (%d), with their full printed text" % len(mat), ""]
        cur = None
        for r in mat:
            if r["doc"] != cur:
                cur = r["doc"]
                lines += ["", "### %s — `%s`" % (docs[cur]["label"], docs[cur]["pdf"]), ""]
            lines.append(dossier_line(r, docs))
        text = "\n".join(lines) + "\n"
        (out_dir / ("%s.md" % topic)).write_text(text, encoding="utf-8")
        ref = sorted(reference.get(topic, []), key=lambda r: (order.get(r["doc"], 999), r.get("page", 0)))
        rlines = ["# Reference dossier: %s" % meta["title"], "", head, "",
                  "Every other verified item of this topic (types the schema does not mark material), with its printed "
                  "text: search it and read the parts your method needs (`grep`, or Read with offset/limit).", ""]
        cur = None
        for r in ref:
            if r["doc"] != cur:
                cur = r["doc"]
                rlines += ["", "## %s — `%s`" % (docs[cur]["label"], docs[cur]["pdf"]), ""]
            rlines.append(dossier_line(r, docs))
        rtext = "\n".join(rlines) + "\n"
        (out_dir / ("%s.reference.md" % topic)).write_text(rtext, encoding="utf-8")
        index_rows.append((topic, meta["title"], len(ss), len(mat), len(ref), est_tokens(len(text)), est_tokens(len(rtext)),
                           meta["owners"]))
    idx = ["# Dossier index — run %s" % p["run_id"], "",
           "%d verified items; %d changed comparatives flagged. Every in-scope page's reading status is in "
           "`corpus/reading/COVERAGE.md`." % (n_items, flags_total), "",
           "| Dossier | Contents | Series | Material items | ≈ tokens | Reference items | ≈ tokens | Owners |",
           "|---|---|---|---|---|---|---|---|"]
    idx += ["| [%s](%s.md) | %s | %d | %d | %d | %d | %d | %s |" % (t_, t_, title, ns, nm, tok, nr, rtok, ", ".join(own))
            for t_, title, ns, nm, nr, tok, rtok, own in index_rows]
    idx += ["", "## Documents", "", "| Key | Document | PDF |", "|---|---|---|"]
    idx += ["| %s | %s | `%s` |" % (d["key"], d["label"], d["pdf"]) for d in p["documents"]]
    packs = out_dir / "packs"
    packs.mkdir(exist_ok=True)
    sizes = {}
    for name in rl.SPECIALISTS:
        mine = [r for r in index_rows if name in r[7]]
        must = sum(r[5] for r in mine)
        sizes[name] = must
        lines = ["# Reading pack — %s (run %s)" % (name, p["run_id"]), "",
                 "**Read in full** (the reading audit checks it): the series and material items of every topic you own. "
                 "Then verify every decision-critical item on its page, and go beyond the dossiers wherever your method "
                 "needs it: open any page of any document (`doc_text.py page`, `search`) and research the web as your "
                 "definition requires.", "",
                 "| Dossier (read in full) | Contents | Series | Material items | ≈ tokens |", "|---|---|---|---|---|"]
        lines += ["| `corpus/dossiers/%s.md` | %s | %d | %d | %d |" % (r[0], r[1], r[2], r[3], r[5]) for r in mine]
        lines += ["", "Must-read total ≈ %s tokens%s." % (format(must, ","), (
            ": more than one session reads comfortably (%s). Read it in order across your sessions, recording in your "
            "workpapers what each dossier established; a fresh session continues from those notes" % format(PACK_BUDGET, ","))
            if must > PACK_BUDGET else ""), "",
                  "Reference (search it and read what your method needs; not required in full):", ""]
        lines += ["- corpus/dossiers/%s.reference.md — %d items, ≈ %s tokens" % (r[0], r[4], format(r[6], ",")) for r in mine]
        lines += ["", "Unusual items flagged by the readers (all topics): %d, in `corpus/dossiers/other.md`." % unusual,
                  "Reading coverage (pages read, repeat, structured, out of scope): `corpus/reading/COVERAGE.md`."]
        (packs / ("%s.md" % name)).write_text("\n".join(lines) + "\n", encoding="utf-8")
    idx += ["", "## Packs: must-read size per specialist", "", "| Specialist | ≈ tokens | Over %s? |" % format(PACK_BUDGET, ","),
            "|---|---|---|"] + ["| %s | %s | %s |" % (n, format(v, ","), "yes" if v > PACK_BUDGET else "no") for n, v in sizes.items()]
    (out_dir / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    over = {n: v for n, v in sizes.items() if v > PACK_BUDGET}
    log("dossiers: %d items in %d topics (%d series, %d changed comparatives) -> %s%s" % (
        n_items, len(index_rows), sum(r[2] for r in index_rows), flags_total, rel(run_dir, out_dir),
        "; packs above %s tokens: %s" % (format(PACK_BUDGET, ","), ", ".join("%s %s" % (n, format(v, ",")) for n, v in over.items()))
        if over else ""))
    return {"items": n_items, "topics": len(index_rows), "changed_comparatives": flags_total, "pack_tokens": sizes}


# --------------------------------------------------------------------------------------------------------------
# Status: the page ledger
# --------------------------------------------------------------------------------------------------------------

def chunk_state(run_dir: Path, c: dict, pol: dict, write: bool = True) -> Tuple[str, List[str]]:
    """("read" | "pending", errors). `write=False` changes nothing on disk (an earlier run's reading is only read)."""
    errs = []
    roles = required_roles(c, pol)
    for role in roles:
        r = check(run_dir, c["id"], role, write=write)
        if not r.ok:
            errs.append("%s: %s" % (role, r.errors[0] if r.errors else "failed"))
    if not errs and roles == ["critical", "reader"]:
        dis = compare_chunk(run_dir, c["id"], write=write)
        if dis:
            r = check(run_dir, c["id"], "resolved", write=write)
            if not r.ok:
                errs.append("resolved: %s" % (r.errors[0] if r.errors else "failed"))
    return ("read" if not errs else "pending"), errs


def status(run_dir: Path, log=print) -> dict:
    p = load_json(run_dir / READING / "plan.json")
    if not p:
        raise SystemExit("no plan: run reading.py plan first")
    pol = run_policy(run_dir)
    cstate = {}
    for c in p["chunks"]:
        cstate[c["id"]] = chunk_state(run_dir, c, pol) + (required_roles(c, pol),)
    rows, per_doc = [], []
    tot = Counter()
    chunks_by_id = {c["id"]: c for c in p["chunks"]}
    for d in p["documents"]:
        cnt = Counter()
        for r in d["page_records"]:
            st = r["status"]
            if r.get("needs_read"):
                st = cstate.get(r["chunk"], ("pending", ["not in a chunk"], []))[0]
            cnt[st] += 1
            viewed = ""
            if st == "read" and r.get("chunk"):
                ch = chunks_by_id.get(r["chunk"], {})
                if r["page"] in ch.get("visual_pages", []):
                    viewed = "no_text"
                elif r["page"] in ch.get("image_pages", []):
                    viewed = "images"
                elif r["page"] in ch.get("verify_pages", []):
                    viewed = "numbers"
            if viewed:
                cnt["viewed"] += 1
                cnt["viewed_" + viewed] += 1
            roles = cstate.get(r.get("chunk"), ("", [], []))[2] if r.get("chunk") else []
            if r.get("reused_from") and st == "read":
                cnt["reused"] += 1
            rows.append({"doc": d["key"], "page": r["page"], "printed": r.get("printed", ""), "class": r["class"], "status": st,
                         "chunk": r.get("chunk", ""), "reads": "+".join(roles), "visual": int(bool(r.get("visual"))),
                         "viewed": viewed, "new_passages": r.get("new", 0), "repeat_passages": r.get("repeat", 0),
                         "context_passages": r.get("context", 0), "reason": r.get("reason", ""),
                         "read_in_run": r.get("reused_from") or (p["run_id"] if st == "read" else "")})
        cnt["pages"] = len(d["page_records"])
        per_doc.append((d, cnt))
        tot.update(cnt)
    ledger = run_dir / READING / "ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["doc"])
        w.writeheader()
        w.writerows(rows)
    pending = [(c["id"], cstate[c["id"]][1]) for c in p["chunks"] if cstate[c["id"]][0] != "read"]
    acc = accepted_gaps(run_dir)
    gaps = p.get("gaps", [])
    open_gaps = [g for g in gaps if g["key"] not in acc]
    sc = p.get("scope", {})
    lines = ["# Reading coverage — run %s" % p["run_id"], ""]
    if sc.get("full_fys") is not None:
        lines += ["Scope: every page of the annual reports of %s; the core sections (auditor's reports, CARO, IFC, "
                  "statements, all notes, Board's report and its statutory annexures, MD&A) of %s; the latest %d "
                  "quarters of transcripts and %d of presentations; the exchange filings in the plan." % (
                      ", ".join("FY%d" % y for y in sc["full_fys"]) or "no year", ", ".join("FY%d" % y for y in sc["core_fys"])
                      or "no year", sc.get("quarters", 0), sc.get("ppt_quarters", 0)), ""]
    lines += [
             "Generated by `scripts/reading.py status` from the page ledger (`corpus/reading/ledger.csv`); do not edit. "
             "*read* = every passage on the page was read and its extraction passed the quote and number checks "
             "(critical pages by two independent readers, disagreements resolved), and the page was viewed on the rendered "
             "PDF page when it has no reliable text, raster images or numbers to confirm; *repeat* = every passage on the "
             "page is text of 60 characters or more (or a whole table) printed word for word elsewhere and read there "
             "(labels, values, headings and shorter text are always read); *structured* = covered by the exchange filing "
             "named in the ledger; *out of scope* = a section outside the core of a core-year report; *pending* = not "
             "yet read. A document *read in run X* was read, checked and audited in that earlier run of the company "
             "and is the same file (SHA-256); its extractions were copied here unchanged.", "",
             "| Document | Pages | Read | Repeat | Structured | Out of scope | Pending | Viewed on the image | Read in |",
             "|---|---|---|---|---|---|---|---|---|"]
    for d, cnt in per_doc:
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %d | %s |" % (
            d["label"], cnt["pages"], cnt["read"], cnt["repeat"], cnt["structured"], cnt["out_of_scope"], cnt["pending"],
            cnt["viewed"], "run %s" % d["reused_from"] if d.get("reused_from") else "this run"))
    lines.append("| **Total** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | %d pages reused |" % (
        tot["pages"], tot["read"], tot["repeat"], tot["structured"], tot["out_of_scope"], tot["pending"], tot["viewed"],
        tot["reused"]))
    lines += ["", "Viewed on the rendered page: %d pages (no reliable text %d, raster images %d, numbers confirmed %d)." % (
        tot["viewed"], tot["viewed_no_text"], tot["viewed_images"], tot["viewed_numbers"])]
    unchecked = [d["label"] for d in p["documents"] if d.get("images_checked") is False]
    if unchecked:
        lines += ["", "**Images not checked** (poppler was unavailable when the plan was made, so pages with raster "
                      "images were not marked for viewing): %s." % "; ".join(unchecked)]
    lines += ["", "Chunks: %d (%d critical, read twice); reader launches recorded: %d." % (
        len(p["chunks"]), sum(1 for c in p["chunks"] if c["critical"]),
        len(load_json(launches_path(run_dir), {"launches": []})["launches"]))]
    if gaps:
        lines += ["", "**In-scope annual reports not read (missing from the document map):**", ""]
        lines += ["- %s (%s years): %s" % (g["label"], g["scope"], "accepted: %s" % acc[g["key"]]["reason"]
                                           if g["key"] in acc else "NOT ACCEPTED: find it or record why it cannot be had")
                  for g in gaps]
    if p.get("excluded"):
        lines += ["", "Not in reading scope (searchable with `doc_text.py search`, not read by the readers):", ""]
        lines += ["- %s: %s" % (e["label"], e["reason"]) for e in p["excluded"]]
    done = not tot["pending"] and not open_gaps
    lines += ["", "**%s**" % ("Every in-scope page has been read or accounted for." if done else
                             "%d page(s) pending in %d chunk(s); %d in-scope report(s) missing without an accepted reason."
                             % (tot["pending"], len(pending), len(open_gaps)))]
    cov = "\n".join(lines) + "\n"
    (run_dir / rl.READING_COVERAGE).write_text(cov, encoding="utf-8")
    st = {"run_id": p["run_id"], "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
          "pages": tot["pages"], "read": tot["read"], "repeat": tot["repeat"], "structured": tot["structured"],
          "out_of_scope": tot["out_of_scope"], "pending": tot["pending"], "viewed": tot["viewed"],
          "chunks": len(p["chunks"]), "pending_chunks": [{"chunk": c, "errors": e[:3]} for c, e in pending],
          "reused_pages": tot["reused"], "open_gaps": [g["key"] for g in open_gaps],
          "complete": done, "coverage_sha256": hashlib.sha256(cov.encode()).hexdigest()}
    write_json(run_dir / rl.READING_STATUS, st)
    log("pages %d: read %d, repeat %d, structured %d, out of scope %d, pending %d (viewed as image %d)" % (
        tot["pages"], tot["read"], tot["repeat"], tot["structured"], tot["out_of_scope"], tot["pending"], tot["viewed"]))
    return st


def coverage_block(run_dir: Path) -> str:
    """The text a report must carry between <!-- READING_COVERAGE:BEGIN --> and <!-- READING_COVERAGE:END -->."""
    path = run_dir / rl.READING_COVERAGE
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


# --------------------------------------------------------------------------------------------------------------
# Exchange filings to read (announcements)
# --------------------------------------------------------------------------------------------------------------

def fetch_filings(run_dir: Path, types: List[str], years: int, log=print) -> int:
    import doc_text  # noqa: E402
    import exchange_index as ei  # noqa: E402
    import fetch_source as fs  # noqa: E402
    _, _, cutoff = _manifest_context(run_dir)
    start = dt.date(cutoff.year - years, cutoff.month, min(cutoff.day, 28))
    rows = [r for r in ei.read_index(run_dir) if r.get("doc_type") in types and r.get("url")
            and r.get("source") in ("NSE", "BSE") and r.get("date")]
    rows = [r for r in rows if start.isoformat() <= r["date"] <= cutoff.isoformat()]
    # NSE and BSE carry the same filing: keep NSE when both have one of the same type within a day
    picked = []
    for r in sorted(rows, key=lambda r: (r["date"], 0 if r["source"] == "NSE" else 1)):
        d = dt.date.fromisoformat(r["date"])
        dup = [q for q in picked if q["doc_type"] == r["doc_type"] and q["source"] != r["source"]
               and abs((dt.date.fromisoformat(q["date"]) - d).days) <= 1]
        if not dup:
            picked.append(r)
    out_rows, pdfs = [], []
    log("filings to fetch: %d (%s)" % (len(picked), ", ".join("%s %d" % kv for kv in Counter(r["doc_type"] for r in picked).items())))
    for n, r in enumerate(picked, 1):
        key = "FIL-%s-%s-%03d" % (r["doc_type"], r["date"], n)
        res = fs.retrieve(run_dir, r["url"], "cio", "Exchange filing %s %s" % (r["doc_type"], r["date"]),
                          alts=[r["alt_url"]] if r.get("alt_url") else None, wayback=False)
        path = res.get("path")
        if path is not None and not str(path).lower().endswith(".pdf"):
            pdf_members = [m for m in (res.get("members") or []) if m.get("kind") == "pdf"]
            path = (run_dir / pdf_members[0]["path"]) if pdf_members else None
        row = {"key": key, "doc_type": r["doc_type"], "date": r["date"], "source": r["source"], "title": r.get("title", ""),
               "url": r["url"], "cached_path": rel(run_dir, path) if path else "", "text_path": "",
               "error": "" if path else (res.get("error") or "download failed")[:200]}
        out_rows.append(row)
        if path:
            row["_pdf"] = str(path)
            pdfs.append(Path(path))
    if pdfs and doc_text.tool("pdftotext"):
        idx = doc_text.convert_many(run_dir, pdfs, log=lambda m: None)
        for row in out_rows:
            e = idx.get(row.get("_pdf", ""))
            if e:
                row["text_path"] = rel(run_dir, e["text"])
    for row in out_rows:
        row.pop("_pdf", None)
    out = run_dir / READING / "filings.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else ["key"])
        w.writeheader()
        w.writerows(out_rows)
    failed = [r for r in out_rows if not r["text_path"]]
    log("filings: %d fetched and converted, %d failed -> %s" % (len(out_rows) - len(failed), len(failed), rel(run_dir, out)))
    return 0 if out_rows else 1


# --------------------------------------------------------------------------------------------------------------
# Calibration bake-off
# --------------------------------------------------------------------------------------------------------------

def bakeoff_plan(run_dir: Path, n: int, log=print) -> List[str]:
    """Pick calibration chunks: one per non-critical section class first (those are the classes a single Sonnet read
    could cover), the rest spread over the critical classes for reference, each near a typical chunk size."""
    p = load_json(run_dir / READING / "plan.json")
    crit = critical_classes(schema())
    by_class = defaultdict(list)
    for c in p["chunks"]:
        if c.get("reused"):
            continue
        cls = next((x for x in c["classes"] if x not in crit), c["classes"][0] if c["classes"] else "narrative")
        by_class[(cls in crit, cls)].append(c)
    picked, covered = [], set()

    def features(c):      # page kinds the calibration must also cover: images, numbers to confirm, no text layer
        return {f for f, k in (("images", "image_pages"), ("verify", "verify_pages"), ("visual", "visual_pages")) if c.get(k)}

    keys = sorted(by_class, key=lambda k: (k[0], k[1]))          # non-critical classes first
    while len(picked) < n and any(by_class.values()):
        for k in keys:
            if by_class[k] and len(picked) < n:
                lst = sorted(by_class[k], key=lambda c: (-len(features(c) - covered), abs(c["est_tokens"] - CHUNK_TOKENS * 0.7)))
                c = lst[0]
                by_class[k].remove(c)
                picked.append(c["id"])
                covered |= features(c)
    for c in p["chunks"]:
        if c["id"] in picked:
            c["bakeoff"] = True
    write_json(run_dir / READING / "plan.json", p)
    write_json(run_dir / READING / "bakeoff.json", {"chunks": picked, "created_at": dt.datetime.now(dt.timezone.utc).isoformat()})
    log("bake-off chunks (%d): %s" % (len(picked), ", ".join(picked)))
    return picked


def bakeoff_score(run_dir: Path, log=print) -> dict:
    p = load_json(run_dir / READING / "plan.json")
    sch = schema()
    picked = set(load_json(run_dir / READING / "bakeoff.json", {"chunks": []})["chunks"])
    agg = defaultdict(lambda: Counter())
    misses = []

    def key(i):          # an item is found only with the same passage, type, amounts and key answers
        return (str(i.get("unit")), i.get("type"), item_sig(i, sch))

    for c in p["chunks"]:
        if c["id"] not in picked:
            continue
        units = chunk_cache(run_dir, c["id"]).get("units", {})
        final = Counter(key(i) for i in final_items(run_dir, dict(c, bakeoff=True)))
        for role, label in (("critical", "opus"), ("reader", "sonnet")):
            got = Counter(key(i) for i in items_of(run_dir, c["id"], role))
            for k in set(final) | set(got):
                cls = units.get(k[0], {}).get("class") or (c["classes"][0] if c["classes"] else "narrative")
                found = min(final[k], got[k])
                agg[(cls, label)]["final"] += final[k]
                agg[(cls, label)]["found"] += found
                agg[(cls, label)]["items"] += got[k]
                if final[k] > found and sch["types"].get(k[1], {}).get("material"):
                    agg[(cls, label)]["material_miss"] += final[k] - found
                    misses.append({"chunk": c["id"], "model": label, "class": cls, "unit": k[0], "type": k[1],
                                   "missing": final[k] - found})
    rows = []
    for (cls, label), cnt in sorted(agg.items()):
        recall = cnt["found"] / cnt["final"] if cnt["final"] else 1.0
        precision = cnt["found"] / cnt["items"] if cnt["items"] else 1.0
        rows.append({"class": cls, "model": label, "final_items": cnt["final"], "recall": round(recall, 4),
                     "precision": round(precision, 4), "material_misses": cnt["material_miss"]})
    eligible = sorted({r["class"] for r in rows if r["model"] == "sonnet" and r["material_misses"] == 0 and r["recall"] >= 0.98
                       and r["final_items"] >= BAKEOFF_MIN_ITEMS and not sch["classes"].get(r["class"], {}).get("critical")})
    out = {"rows": rows, "material_misses": misses, "eligible_single_read_classes": eligible}
    write_json(run_dir / READING / "bakeoff_score.json", out)
    lines = ["# Bake-off result — run %s" % p["run_id"], "", "| Class | Model | Final items | Recall | Precision | Material misses |",
             "|---|---|---|---|---|---|"]
    lines += ["| %s | %s | %d | %.3f | %.3f | %d |" % (r["class"], r["model"], r["final_items"], r["recall"], r["precision"],
                                                      r["material_misses"]) for r in rows]
    lines += ["", "Eligible for a single Sonnet read (non-critical, at least %d adjudicated items, zero material misses, recall ≥ 0.98): %s"
              % (BAKEOFF_MIN_ITEMS, ", ".join(eligible) or "none"),
              "", "Recall is measured against the adjudicated union of both reads: an item both models missed is invisible here, "
              "which is why the auditor's per-run sample of Sonnet-read pages remains."]
    (run_dir / READING / "BAKEOFF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines))
    return out


def reference_dir(run_dir: Path) -> Path:
    return run_dir / READING / "reference"


def reference_save(run_dir: Path, chunk_ids: List[str], log=print) -> List[str]:
    """Freeze the current extractions of these chunks as the reference a later read is scored against (a calibration
    or a change of reading format). Copies, never moves; the plan marks the chunks `bakeoff` so the engine's --bakeoff
    reads exactly them."""
    out = reference_dir(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for cid in chunk_ids:
        for role in ROLES:
            src = extraction_path(run_dir, cid, role)
            if src.exists():
                shutil.copy2(str(src), str(out / src.name))
                saved.append(src.name)
    p = load_json(run_dir / READING / "plan.json")
    for c in p["chunks"]:
        c["bakeoff"] = c["id"] in chunk_ids
    write_json(run_dir / READING / "plan.json", p)
    write_json(out / "reference.json", {"chunks": chunk_ids, "files": saved, "saved_at": now_iso()})
    log("reference: %d file(s) of %d chunk(s) -> %s" % (len(saved), len(chunk_ids), rel(run_dir, out)))
    return saved


def reference_score(run_dir: Path, log=print) -> dict:
    """Recall of the current reads against the reference, per section class and model: a reference item is found when
    a current item of the same type, with the same amounts and key answers, cites its passage or a span that covers it
    (a table row expanded by script counts like a row written by hand). Every material item missed is listed, and so
    is every current item the reference lacks (to review: a miss of the reference, or an error)."""
    ref = load_json(reference_dir(run_dir) / "reference.json")
    if not ref:
        raise SystemExit("no reference: run reading.py reference RUN_DIR save --chunks ...")
    sch = schema()
    launches = load_json(launches_path(run_dir), {"launches": []})["launches"]
    p = load_json(run_dir / READING / "plan.json")
    est = {c["id"]: c["est_tokens"] for c in p["chunks"]}
    agg, misses, extras, costs = defaultdict(Counter), [], [], defaultdict(Counter)
    for l in launches:
        cost = sum((a.get("cost_usd") or 0) for s in l.get("sessions", []) for a in s.get("attempts", []))
        mins = sum((s.get("usage") or {}).get("minutes_first_to_last", 0) or 0 for s in l.get("sessions", []))
        tot = sum(est.get(c, 0) for c in l["chunks"]) or 1
        for c in l["chunks"]:
            if c in ref["chunks"] and l.get("outcome") == "pass":
                costs[(c, l["role"])]["usd"] += cost * est.get(c, 0) / tot
                costs[(c, l["role"])]["min"] += mins * est.get(c, 0) / tot
    for cid in ref["chunks"]:
        st = chunk_cache(run_dir, cid)
        order = st.get("order", [])
        pos = {u: i for i, u in enumerate(order)}
        rpath = reference_dir(run_dir) / ("%s.critical.jsonl" % cid)
        if not rpath.exists():
            continue
        ref_items = [r for r in read_jsonl(rpath, rl.Result("")) if r.get("type") not in
                     ("chunk_receipt", "page_receipt", "resolution", "table")]
        for role, label in (("critical", "opus"), ("reader", "sonnet")):
            cur = items_of(run_dir, cid, role)
            if not cur:
                continue
            cover = defaultdict(set)                      # (type, sig) -> passages covered
            for it in cur:
                u, to = str(it.get("unit")), str(it.get("to") or it.get("unit"))
                span = order[pos[u]:pos[to] + 1] if u in pos and to in pos else [u]
                cover[(it.get("type"), item_sig(it, sch))].update(span)
            matched = set()
            for r in ref_items:
                cls = st["units"].get(str(r.get("unit")), {}).get("class") or (st.get("classes") or ["?"])[0]
                k = (r.get("type"), item_sig(r, sch))
                ok = str(r.get("unit")) in cover.get(k, set())
                mat = sch["types"].get(r.get("type"), {}).get("material")
                agg[(cls, label)]["ref"] += 1
                agg[(cls, label)]["found"] += ok
                agg[(cls, label)]["ref_material"] += bool(mat)
                agg[(cls, label)]["found_material"] += bool(mat and ok)
                if ok:
                    matched.add(k)
                elif mat:
                    misses.append({"chunk": cid, "model": label, "unit": r.get("unit"), "type": r.get("type"),
                                   "fields": r.get("fields")})
            agg[("all", label)]["current_items"] += len(cur)
            ref_keys = {(r.get("type"), item_sig(r, sch)) for r in ref_items}
            extras += [{"chunk": cid, "model": label, "unit": it.get("unit"), "type": it.get("type")}
                       for it in cur if (it.get("type"), item_sig(it, sch)) not in ref_keys][:50]
    rows = []
    for (cls, label), c in sorted(agg.items()):
        if cls == "all":
            continue
        rows.append({"class": cls, "model": label, "reference_items": c["ref"], "recall": round(c["found"] / c["ref"], 4) if c["ref"] else 1.0,
                     "material_items": c["ref_material"], "material_recall": round(c["found_material"] / c["ref_material"], 4)
                     if c["ref_material"] else 1.0})
    out = {"rows": rows, "material_misses": misses, "extras_sample": extras,
           "cost": {"%s %s" % k: {"usd": round(v["usd"], 2), "minutes": round(v["min"], 1)} for k, v in costs.items()}}
    write_json(run_dir / READING / "reference_score.json", out)
    lines = ["# Reading against the reference — run %s" % p["run_id"], "",
             "| Class | Model | Reference items | Recall | Material items | Material recall |", "|---|---|---|---|---|---|"]
    lines += ["| %s | %s | %d | %.3f | %d | %.3f |" % (r["class"], r["model"], r["reference_items"], r["recall"],
                                                    r["material_items"], r["material_recall"]) for r in rows]
    lines += ["", "Material items missed: %d" % len(misses)] + ["- %s %s %s %s: %s" % (
        m["chunk"], m["model"], m["unit"], m["type"], json.dumps(m["fields"], ensure_ascii=False)[:160]) for m in misses[:60]]
    lines += ["", "| Chunk · role | Cost $ | Minutes |", "|---|---|---|"] + [
        "| %s | %.2f | %.1f |" % (k, v["usd"], v["minutes"]) for k, v in sorted(out["cost"].items())]
    (run_dir / READING / "REFERENCE_SCORE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("\n".join(lines[:40]))
    return out


def sample(run_dir: Path, n: int, out: Path, seed: str = "auditor") -> List[dict]:
    """A reproducible sample of read pages for the auditor to re-read on the rendered page: pages that only one
    (Sonnet) read covered first, then non-critical double-read pages, then critical ones; at least a third of the
    sample is pages receipted `no_items` (omission is the risk a quote check cannot catch)."""
    import random
    p = load_json(run_dir / READING / "plan.json")
    pol = run_policy(run_dir)
    tiers = {0: [], 1: [], 2: []}
    for c in p["chunks"]:
        roles = required_roles(c, pol)
        tier = 0 if roles == ["reader"] else (2 if c["critical"] else 1)
        items = final_items(run_dir, c, pol)
        path = extraction_path(run_dir, c["id"], "reader")
        receipts = {r.get("page"): r for r in (read_jsonl(path, rl.Result("")) if path.exists() else [])
                    if r.get("type") == "page_receipt"}
        for pg in c["pages"]:
            on = [i for i in items if i.get("page") == pg]
            tiers[tier].append({"chunk": c["id"], "doc": c["doc"], "pdf": c["pdf"], "page": pg,
                                "receipt": receipts.get(pg, {}).get("status", ""), "items": on})
    rng = random.Random(hashlib.sha1(("%s|%s" % (p["run_id"], seed)).encode()).hexdigest())
    pool = tiers[0] if len(tiers[0]) >= n else tiers[0] + tiers[1] + (tiers[2] if len(tiers[0]) + len(tiers[1]) < n else [])
    empty = [r for r in pool if r["receipt"] == "no_items" or not r["items"]]
    full = [r for r in pool if r not in empty]
    k_empty = min(len(empty), max(1, n // 3))
    picked = rng.sample(empty, k_empty) + rng.sample(full, min(len(full), n - k_empty))
    picked.sort(key=lambda r: (r["doc"], r["page"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc", "pdf", "page", "chunk", "receipt", "items_extracted", "result", "missed_items", "notes"])
        for r in picked:
            w.writerow([r["doc"], r["pdf"], r["page"], r["chunk"], r["receipt"],
                        " || ".join("%s: %s" % (i.get("type"), norm_space(i.get("quote", ""))[:120]) for i in r["items"]) or "-",
                        "", "", ""])
    return picked


# --------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------
# Page images (render): a larger or upright view of a page the Read tool shows too small or sideways
# --------------------------------------------------------------------------------------------------------------

def pgm_parse(data: bytes) -> Tuple[int, int, bytes]:
    """(width, height, grey bytes) of a binary PGM (P5, 8-bit), as `pdftoppm -gray` writes it."""
    if not data.startswith(b"P5"):
        raise ValueError("not a binary PGM image")
    fields, pos = [], 2
    while len(fields) < 3:
        while data[pos:pos + 1].isspace():
            pos += 1
        if data[pos:pos + 1] == b"#":
            while data[pos:pos + 1] not in (b"\n", b""):
                pos += 1
            continue
        start = pos
        while data[pos:pos + 1] and not data[pos:pos + 1].isspace():
            pos += 1
        fields.append(int(data[start:pos]))
    pos += 1
    w, h, maxval = fields
    if maxval > 255:
        raise ValueError("16-bit PGM is not supported")
    pix = data[pos:pos + w * h]
    if len(pix) != w * h:
        raise ValueError("truncated PGM image")
    return w, h, pix


def rotate_gray(w: int, h: int, pix: bytes, deg: int) -> Tuple[int, int, bytes]:
    """Rotate a grey image clockwise by 0, 90, 180 or 270 degrees."""
    deg %= 360
    if deg == 0:
        return w, h, pix
    if deg == 180:
        return w, h, pix[::-1]
    if deg == 90:                 # new row j = old column j, bottom to top
        return h, w, b"".join(pix[j::w][::-1] for j in range(w))
    if deg == 270:                # new row j = old column w-1-j, top to bottom
        return h, w, b"".join(pix[w - 1 - j::w] for j in range(w))
    raise ValueError("rotate must be 0, 90, 180 or 270")


def split_gray(w: int, h: int, pix: bytes, n: int) -> List[Tuple[int, int, bytes]]:
    """n overlapping parts along the longer side (a wide table: left to right), so each is shown large enough."""
    if n <= 1:
        return [(w, h, pix)]
    out = []
    if w >= h:
        step, ov = w / n, int(w * 0.03)
        for i in range(n):
            c0, c1 = max(0, int(i * step) - ov), min(w, int((i + 1) * step) + ov)
            out.append((c1 - c0, h, b"".join(pix[r * w + c0:r * w + c1] for r in range(h))))
    else:
        step, ov = h / n, int(h * 0.03)
        for i in range(n):
            r0, r1 = max(0, int(i * step) - ov), min(h, int((i + 1) * step) + ov)
            out.append((w, r1 - r0, pix[r0 * w:r1 * w]))
    return out


def png_gray(w: int, h: int, pix: bytes) -> bytes:
    raw = b"".join(b"\x00" + pix[r * w:(r + 1) * w] for r in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def render(run_dir: Path, chunk_id: str, page: int, dpi: int = RENDER_DPI, rotate: int = 0, parts: int = 1) -> List[Path]:
    """Render one page of a chunk's PDF to PNG under RUN_DIR/_cache/reading/render/ (named <doc>-p<page>-<dpi>dpi...,
    which the reading audit counts as a view of that page)."""
    store = chunk_cache(run_dir, chunk_id)
    if page not in store["pages"]:
        raise SystemExit("page %d is not in chunk %s (pages %s)" % (page, chunk_id, page_ranges(store["pages"])))
    tool = poppler("pdftoppm")
    if not tool:
        raise SystemExit("pdftoppm (poppler) is not installed: open the page with the Read tool (pages: \"%d\")" % page)
    dpi, parts = max(50, min(int(dpi), 300)), max(1, min(int(parts), 4))
    data = subprocess.run([tool, "-gray", "-r", str(dpi), "-f", str(page), "-l", str(page), str(pdf_path(store["pdf"]))],
                          capture_output=True, timeout=180).stdout
    w, h, pix = rotate_gray(*pgm_parse(data), rotate)
    out_dir = run_dir / CACHE / "render"
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces = split_gray(w, h, pix, parts)
    paths = []
    for i, (pw, ph, pp) in enumerate(pieces, 1):
        path = out_dir / ("%s-p%d-%ddpi%s%s.png" % (store["doc"], page, dpi, "-r%d" % (rotate % 360) if rotate % 360 else "",
                                                    "-part%dof%d" % (i, len(pieces)) if len(pieces) > 1 else ""))
        path.write_bytes(png_gray(pw, ph, pp))
        paths.append(path)
    return paths


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch-filings")
    f.add_argument("run_dir")
    f.add_argument("--types", default=",".join(DEFAULT_FILING_TYPES))
    f.add_argument("--years", type=int, default=10)
    pl = sub.add_parser("plan")
    pl.add_argument("run_dir")
    pl.add_argument("--years", type=int, default=DEFAULT_YEARS, help="fiscal years whose annual reports are read in full")
    pl.add_argument("--core-years", type=int, default=DEFAULT_CORE_YEARS,
                    help="fiscal years before them whose core sections are read")
    pl.add_argument("--quarters", type=int, default=24)
    pl.add_argument("--ppt-quarters", type=int, default=12)
    pl.add_argument("--no-reuse", action="store_true", help="read every document afresh, even one an earlier run read")
    pl.add_argument("--no-calibration", action="store_true",
                    help="no in-run calibration: every chunk is read by both models (the most expensive read)")
    pl.add_argument("--replan", default="", metavar="REASON",
                    help="replace a plan that readers already worked on (its extractions move to superseded/)")
    ag = sub.add_parser("accept-gap")
    ag.add_argument("run_dir")
    ag.add_argument("key", help="the gap's key as plan prints it, for example AR-FY2019")
    ag.add_argument("--reason", required=True)
    nx = sub.add_parser("next")
    nx.add_argument("run_dir")
    nx.add_argument("--json", action="store_true")
    nx.add_argument("--bakeoff", action="store_true", help="only the calibration chunks (bakeoff plan)")
    nx.add_argument("--restart", default="", metavar="REASON",
                    help="the last launch's agent cannot be resumed: close it as abandoned and issue a fresh launch")
    nx.add_argument("--force", action="store_true", help="issue a launch even while the engine runs")
    ck = sub.add_parser("check")
    ck.add_argument("run_dir")
    ck.add_argument("chunk")
    ck.add_argument("--role", choices=ROLES, required=True)
    rd = sub.add_parser("render")
    rd.add_argument("run_dir")
    rd.add_argument("chunk")
    rd.add_argument("page", type=int)
    rd.add_argument("--dpi", type=int, default=RENDER_DPI)
    rd.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270], help="clockwise degrees")
    rd.add_argument("--parts", type=int, default=1, help="split along the longer side into this many parts (1-4)")
    cp = sub.add_parser("compare")
    cp.add_argument("run_dir")
    cp.add_argument("chunks", nargs="*")
    ds = sub.add_parser("dossiers")
    ds.add_argument("run_dir")
    stp = sub.add_parser("status")
    stp.add_argument("run_dir")
    stp.add_argument("--strict", action="store_true")
    rf = sub.add_parser("reference", help="freeze reads as a reference (save --chunks) or score current reads against it")
    rf.add_argument("run_dir")
    rf.add_argument("mode", choices=["save", "score"])
    rf.add_argument("--chunks", default="")
    bk = sub.add_parser("bakeoff")
    bk.add_argument("mode", choices=["plan", "score"])
    bk.add_argument("run_dir")
    bk.add_argument("--n", type=int, default=12)
    sp = sub.add_parser("sample")
    sp.add_argument("run_dir")
    sp.add_argument("--n", type=int, default=15)
    sp.add_argument("--out")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "fetch-filings":
        types = [t.strip() for t in a.types.split(",") if t.strip() and t.strip() != "none"]
        return fetch_filings(run_dir, types, a.years) if types else 0
    if a.cmd == "plan":
        plan(run_dir, a.years, a.quarters, a.ppt_quarters, a.core_years, replan=a.replan, reuse=not a.no_reuse,
             calibrate=not a.no_calibration)
        return 0
    if a.cmd == "accept-gap":
        accept_gap(run_dir, a.key, a.reason)
        print("accepted gap %s: %s (re-run plan)" % (a.key, a.reason))
        return 0
    if a.cmd == "next":
        owner = driver_owner(run_dir)
        if owner and not a.force:
            print("the engine runs for this run (pid %s on %s, since %s): it issues the launches. Wait for it, or "
                  "stop it first." % (owner.get("pid"), owner.get("host"), owner.get("started_at")))
            return 1
        act = next_action(run_dir, a.bakeoff, restart=a.restart)
        if a.json:
            print(json.dumps(act, ensure_ascii=False))
        elif act["action"] == "launch":
            print("Launch agent `%s` (role %s, launch %s, chunks %s; pinned %s at %s)\n  description: %s\n  prompt:\n%s" % (
                act["agent"], act["role"], act["launch"], ", ".join(act["chunks"]), act["model"], act["effort"],
                act["description"], act["prompt"]))
        else:
            print(act["message"])
        return 0 if act["action"] in ("launch", "done") else 1
    if a.cmd == "check":
        res = check(run_dir, a.chunk, a.role)
        print(res.render())
        return 0 if res.ok else 1
    if a.cmd == "render":
        for pth in render(run_dir, a.chunk, a.page, a.dpi, a.rotate, a.parts):
            print("Read this image: %s" % pth.resolve())
        return 0
    if a.cmd == "compare":
        p = load_json(run_dir / READING / "plan.json", {"chunks": []})
        ids = a.chunks or [c["id"] for c in p["chunks"] if required_roles(c) == ["critical", "reader"]]
        total = 0
        for cid in ids:
            if extraction_path(run_dir, cid, "critical").exists() and extraction_path(run_dir, cid, "reader").exists():
                n = len(compare_chunk(run_dir, cid))
                total += n
                print("%s: %d disagreement(s)" % (cid, n))
        print("total disagreements: %d" % total)
        return 0
    if a.cmd == "dossiers":
        dossiers(run_dir)
        return 0
    if a.cmd == "status":
        st = status(run_dir)
        return 1 if (a.strict and not st["complete"]) else 0
    if a.cmd == "sample":
        out = Path(a.out) if a.out else run_dir / "audit" / "reading_sample.csv"
        rows = sample(run_dir, a.n, out)
        print("reading sample: %d pages (%d receipted no_items) -> %s" % (len(rows), sum(1 for r in rows if r["receipt"] == "no_items"), out))
        print("Open each page on the rendered PDF, list every fact of the schema's types, compare with items_extracted and fill "
              "result (Complete | Minor omission | Material omission) and missed_items.")
        return 0 if rows else 1
    if a.cmd == "reference":
        if a.mode == "save":
            reference_save(run_dir, [x.strip() for x in a.chunks.split(",") if x.strip()])
        else:
            reference_score(run_dir)
        return 0
    if a.cmd == "bakeoff":
        if a.mode == "plan":
            bakeoff_plan(run_dir, a.n)
        else:
            bakeoff_score(run_dir)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
