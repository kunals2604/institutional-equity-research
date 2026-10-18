#!/usr/bin/env python3
"""Text layer for large PDFs (annual reports, transcripts, presentations): read cheaply, cite exactly, lose nothing.

  python3 scripts/doc_text.py convert RUN_DIR [--all | PDF ...]      # page-anchored text + page index (once per file)
  python3 scripts/doc_text.py toc     RUN_DIR PDF                     # sections → PDF pages → line ranges to Read
  python3 scripts/doc_text.py page    RUN_DIR PDF PAGE [--to PAGE]    # the exact text of one page (or a range)
  python3 scripts/doc_text.py search  RUN_DIR "<regex>" [--type annual_report] [--period FY2025] [--max 40]
  python3 scripts/doc_text.py verify  RUN_DIR PDF PAGE "<value or phrase>"

Why. A 300-page annual report is roughly 400k tokens as text and far more as rendered pages, so agents must not
read it end to end; but a figure read from a bad conversion is worse than no figure. This layer is built for both:

* **Spreads are split.** Many annual reports are laid out as two A4 pages per landscape PDF page. When no text crosses
  the centre gutter, each half is converted separately (otherwise a Balance Sheet row and a P&L row land on one line).
* **Prose is read in reading order** (poppler's word boxes, ordered by an XY-cut: horizontal bands top to bottom,
  columns left to right). **Tables keep their rows** (poppler's layout mode, cropped to the half-page, with wide
  gaps marked `│`). A region is a table when numbers are a large share of its words.
* **Every page carries its anchor**: `<<<PAGE n/N ...>>>` with the PDF page number (the citation locator), the printed
  page number(s) when found, the view used and any flags. `meta.json` gives each page's line range, so an agent can
  Read exactly page n of the text file (`offset`/`limit`).
* **Fidelity flags** tell you when the text cannot be trusted and the rendered page must be read instead:
  `image_only` (no text layer: scanned or a graphic), `table_numbers_mismatch` (the table view lost or added a number
  compared with poppler's word list), `encoding_suspect` (undecodable glyphs), `spread_split`.
* **Section index** (`toc`): statement and note anchors (standalone vs. consolidated financial statements, auditor's
  report, CARO, notes, related parties, contingent liabilities, segments, MD&A, board's report, governance, BRSR,
  AOC-1/2, secretarial audit) and, for transcripts, the start of Q&A and the speakers.

The rule that keeps accuracy at 100 % is procedural (`methodology/RESEARCH_PLAYBOOK.md` §4): navigate and read in
this text layer; for every decision-critical number, and every page with a flag, confirm it on the rendered PDF page
(Read tool, `pages: "n"`) and with `verify`; financial statements are also reconciled to exchange XBRL.

Output: RUN_DIR/_cache/text/<sha12>/ (pages.md, meta.json); an index RUN_DIR/_cache/text/index.json. Git-ignored.
Requires poppler (pdftotext, pdfinfo, pdfimages). Exit: 0 ok, 1 error, 2 usage.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

NUM_RE = re.compile(r"^\(?[-−–]?\d[\d,]*(?:\.\d+)?\)?%?$")
WORD_RE = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', re.S)
SECTION_PATTERNS = [
    ("independent_auditors_report", r"independent auditor[’'`s]* report"),
    ("caro_annexure", r"annexure\s*['‘’\"]?[ab]['’\"]?\s*to the independent auditor|companies \(auditor[’'`s]* report\) order"),
    ("ifc_report", r"internal financial controls with reference to"),
    ("standalone_balance_sheet", r"standalone balance sheet|balance sheet as at.{0,60}standalone"),
    ("consolidated_balance_sheet", r"consolidated balance sheet"),
    ("standalone_pnl", r"standalone statement of profit and loss"),
    ("consolidated_pnl", r"consolidated statement of profit and loss"),
    ("standalone_cash_flow", r"standalone (statement of )?cash flows?"),
    ("consolidated_cash_flow", r"consolidated (statement of )?cash flows?"),
    ("standalone_notes", r"notes to (the )?standalone financial statements"),
    ("consolidated_notes", r"notes to (the )?consolidated financial statements"),
    ("related_parties", r"related party (transactions|disclosures)"),
    ("contingent_liabilities", r"contingent liabilities"),
    ("segment_information", r"segment (information|reporting)|operating segments"),
    ("mdna", r"management discussion (and|&) analysis"),
    ("boards_report", r"board[’'`s]* report|directors[’'`]* report"),
    ("corporate_governance", r"report on corporate governance|corporate governance report"),
    ("brsr", r"business responsibility (and|&) sustainability report"),
    ("aoc_1", r"form\s*aoc[- ]?1"),
    ("aoc_2", r"form\s*(no\.\s*)?aoc[- ]?2"),
    ("secretarial_audit", r"secretarial audit report|form (no\.\s*)?mr[- ]?3"),
    ("remuneration", r"remuneration of (directors|key managerial)|particulars of employees"),
    ("agm_notice", r"notice of (the )?\w+ annual general meeting"),
    ("qa_session", r"question[- ]and[- ]answer session|we will now begin the question"),
]
SECTION_RES = [(k, re.compile(p, re.I)) for k, p in SECTION_PATTERNS]


def tool(name: str) -> Optional[str]:
    return shutil.which(name) or (Path("/opt/homebrew/bin/%s" % name).exists() and "/opt/homebrew/bin/%s" % name) or None


def run(cmd: List[str], timeout: int = 300) -> str:
    return subprocess.run(cmd, capture_output=True, timeout=timeout).stdout.decode("utf-8", "replace")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Block:
    __slots__ = ("x0", "y0", "x1", "y1", "lines")

    def __init__(self, x0, y0, x1, y1, lines):
        self.x0, self.y0, self.x1, self.y1, self.lines = x0, y0, x1, y1, lines


def parse_bbox(xhtml: str):
    """[(page width, height, [Block]) ...] from `pdftotext -bbox-layout` output (parsed leniently: it is not always
    well-formed XML). Each block's lines are lists of (word, xMin, yMin, xMax, yMax)."""
    pages = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xhtml, re.S):
        w, h, body = float(pm.group(1)), float(pm.group(2)), pm.group(3)
        blocks = []
        for bm in re.finditer(r'<block xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</block>', body, re.S):
            lines = []
            for lm in re.finditer(r"<line[^>]*>(.*?)</line>", bm.group(5), re.S):
                words = [(html.unescape(t).strip(), float(a), float(b), float(c), float(d))
                         for a, b, c, d, t in WORD_RE.findall(lm.group(1))]
                words = [x for x in words if x[0]]
                if words:
                    lines.append(words)
            if lines:
                blocks.append(Block(float(bm.group(1)), float(bm.group(2)), float(bm.group(3)), float(bm.group(4)), lines))
        pages.append((w, h, blocks))
    return pages


def xy_cut(blocks: List[Block], depth: int = 0, ytol: float = 2.0, xtol: float = 4.0) -> List[Block]:
    """Reading order: split into horizontal bands where no block spans the gap, else into columns, recursively."""
    if len(blocks) <= 1 or depth > 40:
        return sorted(blocks, key=lambda b: (round(b.y0), b.x0))
    for axis in ("y", "x"):
        key0, key1, tol = (("y0", "y1", ytol) if axis == "y" else ("x0", "x1", xtol))
        bs = sorted(blocks, key=lambda b: getattr(b, key0))
        groups, cur, cur_max = [], [bs[0]], getattr(bs[0], key1)
        for b in bs[1:]:
            if getattr(b, key0) > cur_max + tol:
                groups.append(cur)
                cur, cur_max = [b], getattr(b, key1)
            else:
                cur.append(b)
                cur_max = max(cur_max, getattr(b, key1))
        groups.append(cur)
        if len(groups) > 1:
            return [x for g in groups for x in xy_cut(g, depth + 1, ytol, xtol)]
    return sorted(blocks, key=lambda b: (round(b.y0), b.x0))


def is_spread(width: float, height: float, blocks: List[Block]) -> bool:
    if width <= height * 1.2 or len(blocks) < 2:
        return False
    mid, band = width / 2.0, width * 0.012
    crossing = [b for b in blocks if b.x0 < mid - band and b.x1 > mid + band]
    left = [b for b in blocks if b.x1 <= mid + band]
    right = [b for b in blocks if b.x0 >= mid - band]
    return not crossing and len(left) >= 1 and len(right) >= 1


def rotated_share(blocks: List[Block]) -> float:
    """Share of multi-letter words whose box is taller than wide: text printed sideways (a rotated table)."""
    ws = [w for b in blocks for ln in b.lines for w in ln if len(w[0]) >= 4]
    if not ws:
        return 0.0
    tall = sum(1 for w in ws if (w[4] - w[2]) > 1.5 * (w[3] - w[1]))
    return tall / float(len(ws))


def words_of(blocks: List[Block]) -> List[str]:
    return [w[0] for b in blocks for ln in b.lines for w in ln]


def norm_num(tok: str) -> str:
    return tok.replace(",", "").replace("(", "").replace(")", "").replace("−", "-").replace("–", "-").rstrip("%")


def numbers(tokens: List[str]) -> Counter:
    return Counter(norm_num(t) for t in tokens if NUM_RE.match(t) and any(ch.isdigit() for ch in t))


def horizontal_bands(blocks: List[Block], ytol: float = 2.0) -> List[List[Block]]:
    """Group blocks into horizontal bands (top to bottom) separated by vertical gaps no block spans."""
    bs = sorted(blocks, key=lambda b: b.y0)
    if not bs:
        return []
    bands, cur, cur_max = [], [bs[0]], bs[0].y1
    for b in bs[1:]:
        if b.y0 > cur_max + ytol:
            bands.append(cur)
            cur, cur_max = [b], b.y1
        else:
            cur.append(b)
            cur_max = max(cur_max, b.y1)
    bands.append(cur)
    return bands


def side_by_side(blocks: List[Block]) -> int:
    """How many blocks of a band sit next to each other (non-overlapping x ranges): column headers or table cells."""
    xs = sorted((b.x0, b.x1) for b in blocks)
    n, end = 0, -1e9
    for x0, x1 in xs:
        if x0 > end:
            n += 1
        end = max(end, x1)
    return n


def numeric_lines(blocks: List[Block]) -> Tuple[int, int]:
    """(lines that are mostly numbers, all lines). Table rows are; prose lines with a figure inside are not."""
    n = total = 0
    for b in blocks:
        for ln in b.lines:
            toks = [w[0] for w in ln]
            total += 1
            k = sum(1 for t in toks if is_numberish(t))
            if k >= 1 and k >= 0.5 * len(toks):
                n += 1
    return n, total


def words_per_block(blocks: List[Block]) -> float:
    return sum(len(words_of([b])) for b in blocks) / float(max(1, len(blocks)))


def band_is_table(blocks: List[Block]) -> bool:
    n, total = numeric_lines(blocks)
    if total and n >= 3 and n / float(total) >= 0.3:
        return True
    nums = sum(1 for t in words_of(blocks) if is_numberish(t))
    return side_by_side(blocks) >= 3 and words_per_block(blocks) <= 6 and nums >= 4


def render_region(blocks: List[Block], width: float) -> Tuple[str, str, int, int]:
    """Text for one region: prose bands in reading order, table bands rebuilt from coordinates. A header band
    (several side-by-side blocks) directly above a table band is rendered with it, so column names stay attached.
    Returns (text, view: prose|table|mixed, number of table bands, unaligned numbers)."""
    bands = horizontal_bands(blocks)
    kinds = [band_is_table(b) for b in bands]
    for i in range(len(bands) - 1):        # a header band of short cells sits directly above its table
        if not kinds[i] and kinds[i + 1] and side_by_side(bands[i]) >= 3 and words_per_block(bands[i]) <= 8:
            kinds[i] = True
    parts, unaligned, merged = [], 0, []
    for band, is_tab in zip(bands, kinds):
        if merged and merged[-1][0] == is_tab and is_tab:
            merged[-1][1].extend(band)
        else:
            merged.append((is_tab, list(band)))
    n_tab = 0
    for is_tab, band in merged:
        if is_tab:
            n_tab += 1
            text, un = table_from_words(band, width)
            unaligned += un
            parts.append(text)
        else:
            parts.append(prose_text(band))
    view = "table" if n_tab and n_tab == len(merged) else ("mixed" if n_tab else "prose")
    return "\n\n".join(p for p in parts if p), view, n_tab, unaligned


def prose_text(blocks: List[Block]) -> str:
    out = []
    for b in xy_cut(blocks):
        out.append("\n".join(" ".join(w[0] for w in ln) for ln in b.lines))
    return "\n\n".join(out)


NIL_TOKENS = {"-", "–", "—", "nil", "Nil", "NIL"}


def is_numberish(tok: str) -> bool:
    if tok.endswith(","):                     # "31," in "March 31, 2025" is part of a date, not a value
        return False
    return tok in NIL_TOKENS or bool(NUM_RE.match(tok) and any(ch.isdigit() for ch in tok))


def table_from_words(blocks: List[Block], width: float) -> Tuple[str, int]:
    """Rebuild a financial table from word coordinates: rows by vertical position; numeric columns by the right edges
    of numbers (financial tables right-align them); every number goes to its column and empty cells stay empty, so a
    missing note number can never shift a value into the wrong column. Returns (pipe-table text, unaligned count)."""
    words = [w for b in blocks for ln in b.lines for w in ln]
    if not words:
        return "", 0
    heights = sorted(w[4] - w[2] for w in words)
    hmed = heights[len(heights) // 2] or 8.0
    rows: List[List[tuple]] = []
    for w in sorted(words, key=lambda w: ((w[2] + w[4]) / 2, w[1])):
        yc = (w[2] + w[4]) / 2
        if rows and abs(yc - rows[-1][0][0]) <= 0.45 * hmed:
            rows[-1].append((yc, w))
        else:
            rows.append([(yc, w)])
    gap = 0.9 * hmed
    cell_rows = []
    left_zone = min(w[1] for w in words) + 0.12 * width   # a dash this far left is a list bullet, not a nil value
    for r in rows:
        ws = sorted((w for _, w in r), key=lambda w: w[1])
        if len(ws) > 1 and ws[0][0] in NIL_TOKENS and ws[0][1] < left_zone:
            ws = [(ws[0][0] + " " + ws[1][0],) + ws[1][1:]] + ws[2:] if ws[1][1] - ws[0][3] < 3 * hmed else ws
        cells, cur = [], [ws[0]]
        for w in ws[1:]:
            if w[1] - cur[-1][3] <= gap and not (is_numberish(w[0]) or is_numberish(cur[-1][0])):
                cur.append(w)
            else:
                cells.append(cur)
                cur = [w]
        cells.append(cur)
        cell_rows.append([(" ".join(x[0] for x in c), c[0][1], c[-1][3]) for c in cells])
    edges = sorted(c[2] for row in cell_rows for c in row if is_numberish(c[0]))
    tol = max(6.0, 0.012 * width)
    anchors: List[float] = []
    for e in edges:
        if anchors and e - anchors[-1] <= tol:
            continue
        anchors.append(e)
    # merge anchors used by very few cells into neighbours (stray numbers in text)
    counts = {a: sum(1 for e in edges if abs(e - a) <= tol) for a in anchors}
    anchors = [a for a in anchors if counts[a] >= 2] or anchors
    out, unaligned = [], 0
    for row in cell_rows:
        label, cols = [], [""] * len(anchors)
        for text, x0, x1 in row:
            idx = min(range(len(anchors)), key=lambda k: abs(anchors[k] - x1)) if anchors else None
            if idx is not None and abs(anchors[idx] - x1) <= tol and (is_numberish(text) or x0 > anchors[0] - 0.25 * width):
                cols[idx] = (cols[idx] + " " + text).strip()
            elif is_numberish(text) and anchors and x0 > min(anchors) - 0.3 * width:
                unaligned += 1
                label.append(text)
            else:
                label.append(text)
        if not any(cols) and not label:
            continue
        out.append("| " + " ".join(label) + " | " + " | ".join(cols) + " |" if anchors else " ".join(label))
    return "\n".join(out), unaligned


def layout_crop(pdf: Path, page: int, x: float, w: float, h: float) -> str:
    t = run([tool("pdftotext"), "-layout", "-enc", "UTF-8", "-f", str(page), "-l", str(page), "-x", str(int(x)), "-y", "0",
             "-W", str(int(w + 1)), "-H", str(int(h + 1)), str(pdf), "-"])
    t = re.sub(r"[ \t]+\n", "\n", t.replace("\f", ""))
    t = re.sub(r" {2,}", lambda m: "  " if len(m.group(0)) < 6 else " │ ", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip("\n")


def printed_page(blocks: List[Block], height: float) -> str:
    cands = [b for b in blocks if len(b.lines) == 1 and len(b.lines[0]) == 1 and re.fullmatch(r"\d{1,4}", b.lines[0][0][0])
             and (b.y0 > height * 0.9 or b.y1 < height * 0.07)]
    return cands[0].lines[0][0][0] if cands else ""


def headings(blocks: List[Block], text: str) -> List[str]:
    """Section anchors found in the region: known statement/report names, plus visually large short lines."""
    found = []
    head = "\n".join(text.splitlines()[:40]).lower()
    for key, rx in SECTION_RES:
        if rx.search(head):
            found.append(key)
    heights = sorted(ln[0][4] - ln[0][2] for b in blocks for ln in b.lines)
    if heights:
        median = heights[len(heights) // 2]
        for b in blocks:
            for ln in b.lines[:1]:
                h = ln[0][4] - ln[0][2]
                words = [w[0] for w in ln]
                if h >= median * 1.35 and 1 <= len(words) <= 12 and not all(NUM_RE.match(x) for x in words):
                    found.append("heading: " + " ".join(words)[:90])
    out, seen = [], set()
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out[:12]


def convert(pdf: Path, out_root: Path, label: str = "") -> Path:
    """Convert one PDF; returns the output directory. Re-uses an existing conversion of the same file (SHA-256)."""
    digest = sha256(pdf)
    out = out_root / digest[:12]
    if (out / "meta.json").exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    info = run([tool("pdfinfo"), str(pdf)], 60)
    m = re.search(r"^Pages:\s+(\d+)", info, re.M)
    n_pages = int(m.group(1)) if m else 0
    bbox = parse_bbox(run([tool("pdftotext"), "-bbox-layout", "-enc", "UTF-8", str(pdf), "-"], 900))
    img_pages = set()
    if tool("pdfimages"):
        for ln in run([tool("pdfimages"), "-list", str(pdf)], 300).splitlines()[2:]:
            parts = ln.split()
            if parts and parts[0].isdigit():
                img_pages.add(int(parts[0]))
    all_text = " ".join(w[0] for _, _, bl in bbox for b in bl for ln in b.lines for w in ln)
    rupee_as_c = "₹" not in all_text and len(re.findall(r"(?<![A-Za-z])C\d[\d,]*", all_text)) >= 20
    lines_out = ["# Text layer — %s" % (label or pdf.name), "",
                 "Source PDF: `%s` · SHA-256 `%s` · %d pages · converted by `scripts/doc_text.py` (poppler)." % (pdf, digest, n_pages),
                 "Cite the **PDF page** in each `<<<PAGE n/N>>>` anchor. Confirm decision-critical numbers on the rendered page "
                 "(Read tool, `pages: \"n\"`), and read flagged pages visually.", ""]
    if rupee_as_c:
        lines_out += ["**Font note:** this PDF's rupee sign is extracted as the letter `C` (for example `C58,557` = ₹58,557). "
                      "The text is left exactly as extracted; read `C` before a figure as ₹.", ""]
    meta_pages = []
    for i, (w, h, blocks) in enumerate(bbox, 1):
        regions = []
        if is_spread(w, h, blocks):
            mid = w / 2.0
            regions = [("L", 0.0, mid, [b for b in blocks if b.x1 <= mid + w * 0.012]),
                       ("R", mid, w - mid, [b for b in blocks if b.x0 >= mid - w * 0.012])]
        else:
            regions = [("", 0.0, w, blocks)]
        page_flags, parts, region_meta = [], [], []
        for side, x, rw, rblocks in regions:
            toks = words_of(rblocks)
            nums = numbers(toks)
            n_num = sum(nums.values())
            flags = []
            view = "none"
            if len(toks) < 8:
                flags.append("image_only" if i in img_pages else "blank_or_graphic")
                text = ""
            elif rotated_share(rblocks) >= 0.3:
                flags.append("rotated_text")      # sideways table: coordinates cannot give rows; read the rendered page
                view = "rotated"
                text = ("(rotated content: the table on this %s is printed sideways; read the rendered PDF page. Its words, "
                        "for search only, not for reading values:)\n%s" % ("half" if side else "page", " ".join(toks)))
            else:
                text, view, n_tab, unaligned = render_region(rblocks, rw)
                got = numbers([t for c in re.split(r"[|]", text) for t in c.split() if t])
                if sum((nums - got).values()) + sum((got - nums).values()) > 0:
                    flags.append("table_numbers_mismatch")          # a number was lost or invented: read the page
                if n_tab and unaligned > max(2, 0.05 * n_num):
                    flags.append("table_alignment_uncertain")      # numbers off every column: read the page
            table = view in ("table", "mixed")
            bad = sum(1 for ch in text if ch == "�" or (ord(ch) < 32 and ch not in "\n\t"))
            if text and bad > 0.02 * len(text):
                flags.append("encoding_suspect")
            pp = printed_page(rblocks, h)
            parts.append((side, pp, view, text, flags))
            region_meta.append({"side": side or "full", "printed_page": pp, "view": view,
                                "words": len(toks), "numbers": n_num, "flags": flags,
                                "sections": headings(rblocks, text)})
            page_flags += flags
        if len(regions) == 2:
            page_flags.append("spread_split")
        printed = "/".join(p[1] for p in parts if p[1])
        anchor = "<<<PAGE %d/%d%s | %s%s>>>" % (
            i, n_pages, " | printed %s" % printed if printed else "",
            " ".join("%s=%s" % (p[0] or "view", p[2]) for p in parts),
            " | flags: " + ", ".join(sorted(set(page_flags))) if page_flags else "")
        start = len(lines_out) + 1
        lines_out.append(anchor)
        for side, pp, view, text, flags in parts:
            if side:
                lines_out.append("[%s half%s]" % (side, ", printed p.%s" % pp if pp else ""))
            if text:
                lines_out += text.splitlines()
            else:
                lines_out.append("(no text layer on this %s: read the rendered page)" % ("half" if side else "page"))
        lines_out.append("")
        meta_pages.append({"page": i, "start_line": start, "end_line": len(lines_out), "printed": printed,
                           "flags": sorted(set(page_flags)), "regions": region_meta})
    (out / "pages.md").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    # Section ranges: consecutive pages carrying the same anchor (running headers repeat it) collapse into one range.
    toc = []
    open_ranges: Dict[str, dict] = {}
    for p in meta_pages:
        here = {s for r in p["regions"] for s in r["sections"] if not s.startswith("heading: ")}
        for s in list(open_ranges):
            if s not in here:
                toc.append(open_ranges.pop(s))
        for s in sorted(here):
            if s in open_ranges:
                open_ranges[s]["to_page"] = p["page"]
            else:
                pr = next((r["printed_page"] for r in p["regions"] if s in r["sections"]), "")
                open_ranges[s] = {"section": s, "page": p["page"], "to_page": p["page"], "printed": pr,
                                  "line": p["start_line"]}
    toc += open_ranges.values()
    toc.sort(key=lambda e: (e["page"], e["section"]))
    meta = {"source": str(pdf), "sha256": digest, "label": label, "pages": n_pages, "text_file": str(out / "pages.md"),
            "rupee_sign_extracted_as_C": rupee_as_c,
            "flagged_pages": {f: [p["page"] for p in meta_pages if f in p["flags"]]
                              for f in ("image_only", "rotated_text", "table_numbers_mismatch",
                                        "table_alignment_uncertain", "encoding_suspect", "blank_or_graphic")},
            "spread_pages": sum(1 for p in meta_pages if "spread_split" in p["flags"]),
            "toc": toc, "page_index": meta_pages}
    (out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def index_path(run_dir: Path) -> Path:
    return run_dir / "_cache" / "text" / "index.json"


def load_index(run_dir: Path) -> Dict[str, dict]:
    p = index_path(run_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def save_index(run_dir: Path, idx: Dict[str, dict]) -> None:
    index_path(run_dir).parent.mkdir(parents=True, exist_ok=True)
    index_path(run_dir).write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")


def map_rows(run_dir: Path) -> Dict[str, dict]:
    """PDF path → {doc_type, period} from the document map (exchange and local copies)."""
    out = {}
    path = run_dir / "corpus" / "document_map.csv"
    if not path.exists():
        return out
    import csv
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for key in ("cached_path", "local_path"):
                v = r.get(key) or ""
                if v.lower().endswith(".pdf"):
                    full = v if Path(v).is_absolute() else str(run_dir / v)
                    out[full] = {"doc_type": r["doc_type"], "period": r["period"], "channel": "exchange" if key == "cached_path" else "local"}
    return out


def convert_many(run_dir: Path, pdfs: List[Path], log=print) -> Dict[str, dict]:
    idx = load_index(run_dir)
    mapping = map_rows(run_dir)
    root = run_dir / "_cache" / "text"
    for pdf in pdfs:
        try:
            info = mapping.get(str(pdf), {})
            label = "%s %s (%s copy)" % (info.get("doc_type", "document"), info.get("period", ""), info.get("channel", "")) if info else pdf.name
            out = convert(pdf, root, label)
            meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
            idx[str(pdf)] = {"text": str(out / "pages.md"), "meta": str(out / "meta.json"), "pages": meta["pages"],
                             "doc_type": info.get("doc_type", ""), "period": info.get("period", ""),
                             "channel": info.get("channel", ""),
                             "flags": {k: len(v) for k, v in meta["flagged_pages"].items() if v}}
            log("converted %s -> %s (%d pages%s)" % (pdf.name, out / "pages.md", meta["pages"],
                                                   "; flags " + str(idx[str(pdf)]["flags"]) if idx[str(pdf)]["flags"] else ""))
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            log("FAILED %s: %s" % (pdf, exc))
    save_index(run_dir, idx)
    return idx


def resolve(run_dir: Path, arg: str) -> Path:
    p = Path(arg)
    if not p.is_absolute() and not p.exists():
        p = run_dir / arg
    return p


def meta_for(run_dir: Path, pdf: Path) -> dict:
    out = convert(pdf, run_dir / "_cache" / "text")
    return json.loads((out / "meta.json").read_text(encoding="utf-8"))


def page_text(meta: dict, first: int, last: int) -> str:
    lines = Path(meta["text_file"]).read_text(encoding="utf-8").splitlines()
    pi = {p["page"]: p for p in meta["page_index"]}
    a, b = pi[first]["start_line"], pi[last]["end_line"]
    return "\n".join(lines[a - 1:b])


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9.%-]", "", s.lower().replace(",", ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert")
    c.add_argument("run_dir")
    c.add_argument("pdfs", nargs="*")
    c.add_argument("--all", action="store_true", help="every PDF in the document map and in _cache/")
    t = sub.add_parser("toc")
    t.add_argument("run_dir")
    t.add_argument("pdf")
    pg = sub.add_parser("page")
    pg.add_argument("run_dir")
    pg.add_argument("pdf")
    pg.add_argument("page", type=int)
    pg.add_argument("--to", type=int)
    pg.add_argument("--view", choices=["text", "layout"], default="text",
                    help="layout = poppler layout mode for the page (the alternative view of a table)")
    s = sub.add_parser("search")
    s.add_argument("run_dir")
    s.add_argument("pattern")
    s.add_argument("--type")
    s.add_argument("--period")
    s.add_argument("--max", type=int, default=40)
    v = sub.add_parser("verify")
    v.add_argument("run_dir")
    v.add_argument("pdf")
    v.add_argument("page", type=int)
    v.add_argument("value")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if not tool("pdftotext") or not tool("pdfinfo"):
        print("poppler is required: brew install poppler", file=sys.stderr)
        return 1
    if a.cmd == "convert":
        pdfs = [resolve(run_dir, x) for x in a.pdfs]
        if a.all or not pdfs:
            found = set(map_rows(run_dir)) | {str(p) for p in (run_dir / "_cache").rglob("*.pdf")}
            pdfs = sorted(Path(p) for p in found if Path(p).exists())
        convert_many(run_dir, pdfs)
        return 0
    if a.cmd == "search":
        idx = load_index(run_dir)
        rx = re.compile(a.pattern, re.I)
        hits = 0
        for pdf, e in sorted(idx.items(), key=lambda kv: (kv[1].get("doc_type", ""), kv[1].get("period", ""))):
            if (a.type and e.get("doc_type") != a.type) or (a.period and e.get("period") != a.period):
                continue
            meta = json.loads(Path(e["meta"]).read_text(encoding="utf-8"))
            lines = Path(e["text"]).read_text(encoding="utf-8").splitlines()
            bounds = [(p["start_line"], p["end_line"], p["page"]) for p in meta["page_index"]]
            for n, line in enumerate(lines, 1):
                if rx.search(line):
                    page = next((pg_ for s0, e0, pg_ in bounds if s0 <= n <= e0), "?")
                    print("%s %s | p.%s | line %d | %s" % (e.get("doc_type") or "doc", e.get("period", ""), page, n, line.strip()[:160]))
                    hits += 1
                    if hits >= a.max:
                        print("(stopped at --max %d)" % a.max)
                        return 0
        print("%d hit(s)" % hits)
        return 0
    pdf = resolve(run_dir, a.pdf)
    if not pdf.exists():
        ap.error("no such PDF: %s" % pdf)
    meta = meta_for(run_dir, pdf)
    if a.cmd == "toc":
        print("%s · %d pages · text %s" % (pdf.name, meta["pages"], meta["text_file"]))
        flagged = {k: v for k, v in meta["flagged_pages"].items() if v}
        if flagged:
            print("Pages to read on the rendered PDF: %s" % json.dumps(flagged))
        for e in meta["toc"]:
            rng = "p.%s" % e["page"] if e.get("to_page", e["page"]) == e["page"] else "p.%s-%s" % (e["page"], e["to_page"])
            print("%-10s printed %-5s line %-7s %s" % (rng, e["printed"] or "-", e["line"], e["section"]))
        return 0
    if a.cmd == "page":
        last = a.to or a.page
        if a.view == "layout":
            for n in range(a.page, last + 1):
                print("<<<PAGE %d (layout view)>>>" % n)
                print(run([tool("pdftotext"), "-layout", "-enc", "UTF-8", "-f", str(n), "-l", str(n), str(pdf), "-"]))
            return 0
        print(page_text(meta, a.page, last))
        return 0
    text = page_text(meta, a.page, a.page)
    target = squash(a.value)
    found_text = target and target in squash(text)
    raw = run([tool("pdftotext"), "-raw", "-enc", "UTF-8", "-f", str(a.page), "-l", str(a.page), str(pdf), "-"])
    found_raw = target and target in squash(raw)
    flags = meta["page_index"][a.page - 1]["flags"]
    print("value %r on PDF page %d: text layer %s, raw extraction %s%s" % (
        a.value, a.page, "FOUND" if found_text else "not found", "FOUND" if found_raw else "not found",
        "; page flags: %s" % ", ".join(flags) if flags else ""))
    print("Now confirm it on the rendered page (Read tool, pages: \"%d\") before citing it as decision-critical." % a.page)
    return 0 if (found_text and found_raw) else 1


if __name__ == "__main__":
    sys.exit(main())
