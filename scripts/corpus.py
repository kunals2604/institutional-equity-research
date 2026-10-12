#!/usr/bin/env python3
"""Local filing corpus (FilingForge library) → catalog, coverage, search and PDF page locators.

FilingForge (a separate desktop app) downloads a company's exchange filings and saves each
PDF next to a Markdown conversion in  <library>/<TICKER>/<category>/<year>/<date>_<headline>__<id>.{pdf,md}.
Downloads are triggered manually in the app (it exposes no external API); this script makes
the downloaded library usable by the research agents. It never modifies the library.

  python3 scripts/corpus.py status   [--ticker T]                   # what is in the library, coverage vs depth standard
  python3 scripts/corpus.py catalog  --ticker T --run RUN_DIR       # writes RUN_DIR/corpus/catalog.csv + CATALOG.md
  python3 scripts/corpus.py search   --ticker T "regex" [--types annual_report,results] [--from-fy 2015] [--max 40]
  python3 scripts/corpus.py locate   --run RUN_DIR DOC.md "exact text"   # PDF page number(s) for a passage (poppler)
  python3 scripts/corpus.py pages    --run RUN_DIR DOC.md               # page-marked text of the sibling PDF

Library path: --library, else $FILINGFORGE_LIBRARY, else config/data_sources.json.
Reading strategy: Markdown is ~25x smaller than the PDF. Search first, then Read the Markdown
with offset/limit around the hit; use `locate` to get the PDF page number for the citation.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DATA_SOURCES = rl.ROOT / "config" / "data_sources.json"
CATEGORY_TYPES = {
    "annual-reports": "annual_report", "annual_report": "annual_report",
    "concalls": "concall", "concall": "concall",
    "investor-ppts": "investor_ppt", "investor_ppt": "investor_ppt",
    "quarterly": "results", "result": "results", "results": "results", "integrated-filing": "results",
    "analyst-meets": "analyst_meet", "analyst_meet": "analyst_meet",
    "corp-actions": "corporate_action", "corp-action": "corporate_action",
    "insider-trading-sast": "insider_sast", "agm-egm": "agm_egm", "board-meeting": "board_meeting",
    "company-update": "company_update", "others": "other", "research_report": "third_party_report",
}
# Headline patterns decide value; transcripts are recognised wherever they are filed.
TRANSCRIPT_RE = re.compile(r"transcript", re.I)
NOISE_RE = re.compile(r"intimation of (the )?schedule|schedule of analyst|trading window|newspaper|news paper|"
                      r"loss of share certificate|duplicate share|audio recording|recording of|"
                      r"change in (the )?(name|address) of (the )?(rta|registrar)|certificate under regulation 74|"
                      r"reg(ulation)? ?74\(5\)|compliance certificate|closure of trading", re.I)
CORE_TYPES = {"annual_report", "results", "concall_transcript", "investor_ppt"}
TIER = {"annual_report": 1, "results": 1, "concall_transcript": 4, "investor_ppt": 3, "corporate_action": 1,
        "insider_sast": 1, "agm_egm": 1, "board_meeting": 1, "company_update": 3, "analyst_meet": 3,
        "concall": 4, "other": 3, "third_party_report": 6}
CSV_COLS = ["doc_id", "doc_type", "value", "quality", "date", "fiscal_period", "period_basis", "headline", "md_path", "pdf_path",
            "md_lines", "approx_tokens", "extracted", "md_sha256", "pdf_sha256", "source_tier", "source_id"]


def library_path(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg).expanduser()
    if os.environ.get("FILINGFORGE_LIBRARY"):
        return Path(os.environ["FILINGFORGE_LIBRARY"]).expanduser()
    if DATA_SOURCES.exists():
        cfg = json.loads(DATA_SOURCES.read_text(encoding="utf-8"))
        if cfg.get("filingforge_library"):
            return Path(cfg["filingforge_library"]).expanduser()
    return Path("~/Documents/FilingForgeLibrary").expanduser()


def front_matter(md: Path) -> Dict[str, str]:
    out = {}
    with md.open(encoding="utf-8", errors="replace") as f:
        if f.readline().strip() != "---":
            return out
        for _ in range(40):
            line = f.readline()
            if not line or line.strip() == "---":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def fy_from_text(text: str) -> Optional[int]:
    m = re.search(r"\b(20\d{2})\s*[-–/]\s*(20)?(\d{2})\b", text)
    if m:
        start, end2 = int(m.group(1)), int(m.group(3))
        if (start + 1) % 100 == end2:
            return start + 1
    m = re.search(r"\bF\.?Y\.?\s*'?(20\d{2}|\d{2})\b", text, re.I)
    if m:
        y = int(m.group(1))
        return y + 2000 if y < 100 else y
    return None


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def quarter_from_text(text: str) -> Optional[str]:
    m = re.search(r"(?:quarter|period|half[- ]year|year)\s+ended\s+(?:on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9}),?\s+(20\d{2})", text, re.I)
    if not m:
        return None
    mon = _MONTHS.get(m.group(2)[:3].lower())
    year = int(m.group(3))
    if mon is None:
        return None
    q = {6: 1, 9: 2, 12: 3, 3: 4}.get(mon)
    if q is None:
        return None
    fy = year + 1 if mon in (6, 9, 12) else year
    return "Q%dFY%d" % (q, fy)


def infer_period(doc_type: str, date: str, headline: str, body_head: str) -> (str, str):
    y, mo = int(date[:4]), int(date[5:7])
    if doc_type == "annual_report":
        # Annual reports are filed after the year they cover: filed Apr-Dec of Y -> FY Y; Jan-Mar -> FY Y-1.
        by_date = y if mo >= 4 else y - 1
        fy = fy_from_text(headline)  # headline only: body text quotes many other years
        if fy and abs(fy - by_date) <= 1:
            return "FY%d" % fy, "stated"
        return "FY%d" % by_date, "inferred-from-filing-date"
    if doc_type in ("results", "concall_transcript", "investor_ppt", "concall"):
        q = quarter_from_text(headline) or quarter_from_text(body_head[:6000])
        if q:
            return q, "stated"
        held = re.search(r"held on\s+(?:\d{1,2}(?:st|nd|rd|th)?\s+)?([A-Za-z]{3,9})\s*(\d{1,2})?,?\s+(20\d{2})", headline)
        if held and _MONTHS.get(held.group(1)[:3].lower()):
            mo, y = _MONTHS[held.group(1)[:3].lower()], int(held.group(3))
        # filings follow the quarter they report: Jan-Mar -> Q3 of FY(y); Apr-Jun -> Q4 FY(y);
        # Jul-Sep -> Q1 FY(y+1); Oct-Dec -> Q2 FY(y+1)
        q, fy = ((3, y) if mo <= 3 else (4, y) if mo <= 6 else (1, y + 1) if mo <= 9 else (2, y + 1))
        return "Q%dFY%d" % (q, fy), "inferred-from-filing-date"
    return "", ""


def sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(lib: Path, ticker: str, hashes: bool = False) -> List[dict]:
    root = lib / ticker
    if not root.is_dir():
        return []
    docs = []
    for md in sorted(root.rglob("*.md")):
        if md.name == "INDEX.md" or md.parent == root:
            continue
        rel = md.relative_to(root)
        category = rel.parts[0]
        fm = front_matter(md)
        headline = fm.get("headline") or md.stem
        m = re.match(r"(\d{4}-\d{2}-\d{2})_", md.name)
        date = fm.get("date") or (m.group(1) if m else "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
            continue
        doc_type = CATEGORY_TYPES.get(category, "other")
        if TRANSCRIPT_RE.search(headline):
            doc_type = "concall_transcript"
        size = md.stat().st_size
        with md.open(encoding="utf-8", errors="replace") as f:
            head = f.read(8000)
        noise = bool(NOISE_RE.search(headline)) and doc_type != "concall_transcript"
        value = "core" if (doc_type in CORE_TYPES and not noise) else ("noise" if noise or size < 1500 else "supporting")
        if doc_type == "results" and re.search(r"outcome of board meeting", headline, re.I) and not re.search(r"result", head, re.I):
            value = "supporting"
        period, basis = infer_period(doc_type, date, headline, head)
        thin = (fm.get("extracted", "ok") not in ("ok", "")) or (doc_type == "annual_report" and size < 40000) or size < 1500
        quality = "thin-extraction: read the PDF" if thin else "ok"
        lines = sum(1 for _ in md.open(encoding="utf-8", errors="replace"))
        pdf = md.with_suffix(".pdf")
        news_id = fm.get("news_id") or md.stem.split("__")[-1]
        docs.append({
            "doc_id": news_id, "doc_type": doc_type, "value": value, "quality": quality, "date": date, "fiscal_period": period,
            "period_basis": basis, "headline": headline[:160], "md_path": str(md), "pdf_path": str(pdf) if pdf.exists() else "",
            "md_lines": lines, "approx_tokens": size // 4, "extracted": fm.get("extracted", ""),
            "md_sha256": sha256(md) if hashes else "", "pdf_sha256": sha256(pdf) if hashes else "",
            "source_tier": TIER.get(doc_type, 3), "source_id": "FilingForge:%s" % news_id,
        })
    return docs


def period_key(p: str):
    m = re.fullmatch(r"(?:Q([1-4]))?FY(\d{4})", p or "")
    return (int(m.group(2)), int(m.group(1) or 0)) if m else (0, 0)


def coverage(docs: List[dict]) -> dict:
    core = [d for d in docs if d["value"] == "core"]
    per = lambda t: sorted({d["fiscal_period"] for d in core if d["doc_type"] == t and d["fiscal_period"]}, key=period_key)  # noqa: E731
    ar, res, tr, ppt = per("annual_report"), per("results"), per("concall_transcript"), per("investor_ppt")
    mins = rl.depth_minimums()
    return {"annual_reports": ar, "results_quarters": res, "transcript_quarters": tr, "presentation_quarters": ppt,
            "gaps": {
                "annual_reports": max(0, mins.get("financials.fiscal_years", 10) - len(ar)),
                "transcript_quarters": max(0, mins.get("concalls.quarters", 12) - len(tr)),
                "results_quarters": max(0, 12 - len(res))}}


def write_catalog(docs: List[dict], run_dir: Path, ticker: str, lib: Path) -> Path:
    out = run_dir / "corpus"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "catalog.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(docs)
    cov = coverage(docs)
    rl.write_json(out / "coverage.json", cov)
    lines = ["# Local filing corpus — %s" % ticker, "",
             "Library: `%s` (FilingForge; read-only). Markdown is text extracted from the PDF; it has **no page markers**." % lib,
             "Cite as `source_url_or_id = FilingForge:<doc_id>`, tier per row, locator = PDF page from "
             "`python3 scripts/corpus.py locate --run RUN_DIR <md_path> \"<text>\"` (or `MD line N` if the PDF is unavailable).",
             "", "**This corpus is one of two channels at par with full web research, never a limit.** It may be incomplete or contain "
             "download glitches: a document missing here is not missing evidence, and decision-critical numbers are cross-checked "
             "against the exchange or IR original (`methodology/SOURCE_GUIDE.md` §0).",
             "", "## Coverage vs Historical Depth Standard", "",
             "- Annual reports: %d fiscal years (%s)" % (len(cov["annual_reports"]), ", ".join(cov["annual_reports"]) or "none"),
             "- Results: %d quarters" % len(cov["results_quarters"]),
             "- Concall transcripts: %d quarters (%s)" % (len(cov["transcript_quarters"]), ", ".join(cov["transcript_quarters"][-12:]) or "none"),
             "- Investor presentations: %d periods" % len(cov["presentation_quarters"]),
             "- **Gaps to fill from the web or a FilingForge re-download:** annual reports −%d, transcripts −%d, results −%d"
             % (cov["gaps"]["annual_reports"], cov["gaps"]["transcript_quarters"], cov["gaps"]["results_quarters"]), ""]
    for t in ("annual_report", "results", "concall_transcript", "investor_ppt"):
        rows = sorted((d for d in docs if d["doc_type"] == t and d["value"] == "core"), key=lambda d: d["date"], reverse=True)
        if not rows:
            continue
        lines += ["## %s (%d)" % (t.replace("_", " ").title(), len(rows)), "",
                  "| period | date | headline | ~tokens | lines | quality | md path |", "|---|---|---|---|---|---|---|"]
        lines += ["| %s | %s | %s | %s | %s | %s | `%s` |" % (d["fiscal_period"] + ("*" if d["period_basis"].startswith("inferred") else ""),
                                                           d["date"], d["headline"][:70].replace("|", "/"), d["approx_tokens"], d["md_lines"],
                                                           d["quality"], d["md_path"])
                  for d in rows]
        lines.append("")
    sup = [d for d in docs if d["value"] == "supporting"]
    noise = sum(1 for d in docs if d["value"] == "noise")
    lines += ["## Supporting documents (%d) — governance, corporate actions, insider/SAST, AGM, updates" % len(sup), "",
              "Listed in `catalog.csv` (filter `value=supporting`). %d low-value notices (meeting schedules, trading-window "
              "closures, newspaper ads, recordings) are excluded from reading lists." % noise,
              "", "`*` = period inferred from the filing date; confirm in the document."]
    (out / "CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "CATALOG.md"


def pdftotext_bin() -> Optional[str]:
    return shutil.which("pdftotext") or (Path("/opt/homebrew/bin/pdftotext").exists() and "/opt/homebrew/bin/pdftotext") or None


def page_text(md_path: Path, run_dir: Path) -> Path:
    pdf = md_path.with_suffix(".pdf")
    if not pdf.exists():
        raise FileNotFoundError("no sibling PDF for %s" % md_path)
    tool = pdftotext_bin()
    if not tool:
        raise RuntimeError("pdftotext (poppler) not installed: brew install poppler")
    out = run_dir / "_cache" / "corpus" / (md_path.stem[:80] + ".pages.txt")
    if out.exists() and out.stat().st_mtime >= pdf.stat().st_mtime:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = subprocess.run([tool, "-layout", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")
    pages = raw.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    out.write_text("".join("\n=== PAGE %d ===\n%s" % (i, p) for i, p in enumerate(pages, 1)), encoding="utf-8")
    return out


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def locate(md_path: Path, run_dir: Path, text: str) -> List[int]:
    pages = page_text(md_path, run_dir).read_text(encoding="utf-8").split("\n=== PAGE ")
    needle = norm(text)
    if len(needle) < 8:
        raise ValueError("search text too short to locate reliably (use >= 8 alphanumeric characters)")
    hits = []
    for chunk in pages[1:]:
        num, _, body = chunk.partition(" ===\n")
        if needle in norm(body):
            hits.append(int(num))
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "catalog", "search", "locate", "pages"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--ticker")
    ap.add_argument("--run")
    ap.add_argument("--library")
    ap.add_argument("--types", help="comma list of doc types (annual_report,results,concall_transcript,investor_ppt,...)")
    ap.add_argument("--from-fy", type=int)
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--per-doc", type=int, default=6, help="max hits per document (so every year is represented)")
    ap.add_argument("--all-values", action="store_true", help="search supporting and noise documents too")
    a = ap.parse_intermixed_args(argv)
    lib = library_path(a.library)

    if a.command == "status":
        if not lib.is_dir():
            print("FilingForge library not found at %s (set config/data_sources.json or --library)." % lib)
            return 1
        tickers = [a.ticker.upper()] if a.ticker else sorted(p.name for p in lib.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
        for t in tickers:
            docs = scan(lib, t)
            if not docs:
                print("%s: not in library — download it in FilingForge (annual reports, results, concalls, investor presentations)." % t)
                continue
            cov = coverage(docs)
            core = sum(1 for d in docs if d["value"] == "core")
            print("%s: %d documents (%d core); annual reports %d FY, results %d Q, transcripts %d Q; gaps AR -%d, transcripts -%d"
                  % (t, len(docs), core, len(cov["annual_reports"]), len(cov["results_quarters"]),
                     len(cov["transcript_quarters"]), cov["gaps"]["annual_reports"], cov["gaps"]["transcript_quarters"]))
        return 0

    if a.command == "catalog":
        if not (a.ticker and a.run):
            ap.error("catalog needs --ticker and --run")
        docs = scan(lib, a.ticker.upper(), hashes=True)
        if not docs:
            print("No FilingForge library for %s at %s. Agents will acquire documents from the web (fetch_source.py)." % (a.ticker, lib))
            return 2
        path = write_catalog(docs, Path(a.run), a.ticker.upper(), lib)
        cov = coverage(docs)
        print("Catalog: %s (%d documents, %d core). Annual reports %d FY; transcripts %d Q; results %d Q."
              % (path, len(docs), sum(1 for d in docs if d["value"] == "core"), len(cov["annual_reports"]),
                 len(cov["transcript_quarters"]), len(cov["results_quarters"])))
        return 0

    if a.command == "search":
        if not (a.ticker and a.args):
            ap.error('search needs --ticker and a pattern')
        pat = re.compile(a.args[0], re.I)
        types = set(a.types.split(",")) if a.types else None
        n = 0
        for d in sorted(scan(lib, a.ticker.upper()), key=lambda d: d["date"], reverse=True):
            if types and d["doc_type"] not in types:
                continue
            if not a.all_values and d["value"] != "core" and not types:
                continue
            fy = re.search(r"FY(\d{4})", d["fiscal_period"] or "")
            if a.from_fy and fy and int(fy.group(1)) < a.from_fy:
                continue
            per = 0
            with open(d["md_path"], encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    if pat.search(line) and per < a.per_doc:
                        per += 1
                        print("%s | %s | %s | line %d | %s" % (d["fiscal_period"], d["doc_type"], Path(d["md_path"]).name[:60], i, line.strip()[:160]))
                        n += 1
                        if n >= a.max:
                            print("... (--max %d reached; narrow the pattern or raise --max)" % a.max)
                            return 0
        print("%d hit(s)." % n)
        return 0

    if not (a.run and a.args):
        ap.error("%s needs --run and a document path" % a.command)
    md = Path(a.args[0]).expanduser()
    try:
        if a.command == "pages":
            p = page_text(md, Path(a.run))
            print(p)
            print("%d pages (markers '=== PAGE n ==='); grep it or Read with offset/limit." % p.read_text(encoding="utf-8").count("=== PAGE "))
        else:
            if len(a.args) < 2:
                ap.error('locate needs a document path and "text"')
            hits = locate(md, Path(a.run), a.args[1])
            print("PDF page(s): %s" % (", ".join(map(str, hits)) if hits else "not found (text may differ between MD and PDF; try a shorter distinctive phrase)"))
            return 0 if hits else 1
    except (FileNotFoundError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print("ERROR: %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
