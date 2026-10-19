#!/usr/bin/env python3
"""Stage-0 document map: what exists, where, and whether the two evidence channels agree.

  python3 scripts/document_map.py build RUN_DIR [--years 15] [--quarters 24] [--download core|none] [--sleep 0.5]
  python3 scripts/document_map.py status RUN_DIR
  python3 scripts/document_map.py add    RUN_DIR --type annual_report --period FY2014 --url URL [--alt URL ...] [--note "..."]

Inputs: the exchange / IR / archive index (`scripts/exchange_index.py all ...`, in RUN_DIR/_cache/index/) and the
local FilingForge catalog (`scripts/corpus.py catalog`, in RUN_DIR/corpus/catalog.csv), if the company is there.

For every required document of the depth standard (annual reports for `--years` fiscal years; earnings-call
transcripts and investor presentations for `--quarters` quarters; results and shareholding filings by quarter) it
records the local copy, every exchange / IR / archive copy, and a status: `both`, `exchange_only`, `local_only` or
`missing`. With `--download core` it downloads the exchange copy of every annual report, transcript and
presentation (fetch_source.py: validated, SHA-256 logged, ZIPs unpacked, mirrors and archive fallback) once, for
the whole run; specialists then reuse these files instead of re-downloading.

Cross-check of the two channels (the owner's local library vs. the original filings):
  page_count_mismatch   the local PDF and the exchange PDF differ in length (truncated download, different version)
  content_mismatch      their first pages share little text (a different document under the same label)
  period_label_mismatch a local document's period label disagrees with the exchange filing of the same date
  duplicate_period_label two local documents claim the same period (one of them is mislabelled)
  local_quality:<flag>  the local catalog flagged the Markdown (for example thin-extraction): read the PDF instead
  short_document        under 4 pages: possibly a cover letter that only links to the real document
  local_only / missing  no exchange copy found / no copy anywhere: search the IR site and the web, then record a gap

Writes RUN_DIR/corpus/document_map.csv and RUN_DIR/corpus/DOCUMENT_MAP.md (both committed).
Exit: 0 written, 1 no index (run exchange_index.py first), 2 usage.
"""

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doc_text  # noqa: E402
import exchange_index as ei  # noqa: E402
import fetch_source as fs  # noqa: E402
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

MAP_COLUMNS = ["doc_type", "period", "status", "local_doc_id", "local_path", "local_pages", "primary_source",
               "primary_url", "alt_urls", "filed", "cached_path", "cached_sha256", "cached_pages", "text_path",
               "text_flags", "flags"]
CORE_TYPES = ("annual_report", "transcript", "investor_presentation")
QUARTERLY_REQUIRED = ("transcript", "investor_presentation", "results", "shareholding")
LOCAL_TYPE = {"annual_report": "annual_report", "concall_transcript": "transcript", "investor_ppt": "investor_presentation",
              "results": "results"}
SOURCE_RANK = {"NSE": 0, "BSE": 1, "IR": 2, "WAYBACK": 3}
LABEL = {"annual_report": "Annual report", "transcript": "Earnings-call transcript",
         "investor_presentation": "Investor presentation", "results": "Results filing", "shareholding": "Shareholding pattern"}


def quarter_end(label: str, fy_end_month: int = 3) -> Optional[dt.date]:
    m = re.fullmatch(r"Q([1-4])FY(\d{4})", label or "")
    if not m:
        return None
    q, fy = int(m.group(1)), int(m.group(2))
    month = (fy_end_month + 3 * q - 1) % 12 + 1
    year = fy if (fy_end_month == 12 or month <= fy_end_month) else fy - 1
    return ei.month_end(year, month)


def fy_end_date(label: str, fy_end_month: int = 3) -> Optional[dt.date]:
    m = re.fullmatch(r"FY(\d{4})", label or "")
    return ei.month_end(int(m.group(1)), fy_end_month) if m else None


def previous_quarters(latest: str, n: int, fy_end_month: int = 3) -> List[str]:
    out, end = [], quarter_end(latest, fy_end_month)
    while end and len(out) < n:
        out.append(ei.quarter_label(end, fy_end_month))
        end = ei.month_end(end.year - (end.month <= 3), (end.month - 4) % 12 + 1)
    return out


def available_by_cutoff(r: dict, cutoff: dt.date, fy_end_month: int) -> bool:
    d = ei.parse_date(r.get("date") or "")
    if d:
        return d <= cutoff
    end = quarter_end(r.get("fiscal_period"), fy_end_month) or fy_end_date(r.get("fiscal_period"), fy_end_month)
    return bool(end and end + dt.timedelta(days=45) <= cutoff)       # undated archive copy: period ended in time


def pdf_text_tokens(path: str, pages: int = 3) -> set:
    tool = shutil.which("pdftotext")
    if not tool or not path or not Path(path).exists():
        return set()
    try:
        proc = subprocess.run([tool, "-f", "1", "-l", str(pages), "-q", path, "-"], capture_output=True, text=True,
                              timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        return set()
    return {w for w in re.findall(r"[a-z]{4,}", proc.stdout.lower())}


def jaccard(a: set, b: set) -> Optional[float]:
    if not a or not b:
        return None
    return len(a & b) / float(len(a | b))


def pages_of(path: Optional[str]) -> Optional[int]:
    if not path or not Path(path).exists():
        return None
    kind = nf.sniff(path)
    if kind == "pdf":
        return nf.pdf_info(path)[0]
    return None


def load_local(run_dir: Path) -> List[dict]:
    cat = run_dir / "corpus" / "catalog.csv"
    if not cat.exists():
        return []
    with cat.open(newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("doc_type") in LOCAL_TYPE]


def build(run_dir: Path, years: int, quarters: int, download: str, sleep: float, log=print) -> dict:
    m, fy_m, cutoff = ei.manifest_context(run_dir)
    index = [r for r in ei.read_index(run_dir) if r.get("doc_type") not in ei.NOISE_TYPES]
    if not index:
        raise SystemExit("no index: run python3 scripts/exchange_index.py all --run %s --symbol <SYMBOL> first" % run_dir)
    usable = [r for r in index if available_by_cutoff(r, cutoff, fy_m)]
    local = load_local(run_dir)

    # Required periods -------------------------------------------------------------------------------------
    ar_periods = sorted({r["fiscal_period"] for r in usable if r["doc_type"] == "annual_report" and r["fiscal_period"]})
    latest_fy = ar_periods[-1] if ar_periods else "FY%d" % (ei.fiscal_year(cutoff, fy_m) - 1)
    fy_list = ["FY%d" % y for y in range(int(latest_fy[2:]) - years + 1, int(latest_fy[2:]) + 1)]
    q_periods = sorted({r["fiscal_period"] for r in usable if r["doc_type"] in ("transcript", "results", "results_xbrl")
                        and re.fullmatch(r"Q[1-4]FY\d{4}", r["fiscal_period"] or "")},
                       key=lambda p: (p[3:], p[:2]))
    latest_q = q_periods[-1] if q_periods else ei.quarter_label(ei.last_quarter_end_before(cutoff, fy_m, 50), fy_m)
    q_list = list(reversed(previous_quarters(latest_q, quarters, fy_m)))

    by_key: Dict[tuple, List[dict]] = defaultdict(list)
    for r in usable:
        t = "results" if r["doc_type"] == "results_xbrl" else r["doc_type"]
        by_key[(t, r["fiscal_period"])].append(r)
    local_by_key: Dict[tuple, List[dict]] = defaultdict(list)
    for r in local:
        local_by_key[(LOCAL_TYPE[r["doc_type"]], r.get("fiscal_period", ""))].append(r)

    items = []
    plan = [("annual_report", p) for p in fy_list] + [(t, p) for t in QUARTERLY_REQUIRED for p in q_list]
    for dtype, period in plan:
        cands = sorted(by_key.get((dtype, period), []),
                       key=lambda r: (SOURCE_RANK.get(r["source"], 9),
                                      0 if (r.get("url") or "").lower().endswith((".pdf", ".zip", ".xml")) else 1,
                                      r.get("date") or ""))
        cands = [c for c in cands if c.get("url")] or cands
        locs = local_by_key.get((dtype, period), [])
        urls = []
        for c in cands:
            for u in (c.get("url"), c.get("alt_url") if c["source"] == "BSE" else ""):
                if u and u not in urls:
                    urls.append(u)
        item = {"doc_type": dtype, "period": period, "local_doc_id": ";".join(l["doc_id"] for l in locs),
                "local_path": (locs[0].get("pdf_path") or locs[0].get("md_path")) if locs else "",
                "local_pages": "", "primary_source": cands[0]["source"] if cands else "",
                "primary_url": urls[0] if urls else "", "alt_urls": " ".join(urls[1:6]),
                "filed": cands[0].get("date", "") if cands else "", "cached_path": "", "cached_sha256": "",
                "cached_pages": "", "flags": []}
        if len(locs) > 1 and dtype != "results":
            item["flags"].append("duplicate_period_label")
        for l in locs:
            q = (l.get("quality") or "").strip()
            if q and q != "ok":
                item["flags"].append("local_quality:%s" % q)
        items.append(item)

    # Downloads (exchange copies of the core documents) -------------------------------------------------------
    failures = []
    if download == "core":
        todo = [i for i in items if i["doc_type"] in CORE_TYPES and i["primary_url"]]
        log("downloading %d core documents (exchange / IR / archive copies)" % len(todo))
        for n, item in enumerate(todo, 1):
            alts = item["alt_urls"].split() if item["alt_urls"] else []
            name = "%s %s (%s)" % (LABEL[item["doc_type"]], item["period"], item["primary_source"])
            res = fs.retrieve(run_dir, item["primary_url"], "cio", name, alts=alts, wayback=True)
            if res.get("path") is None:
                failures.append({"item": name, "error": res.get("error", "")[:300]})
                item["flags"].append("download_failed")
                log("  [%d/%d] FAILED %s" % (n, len(todo), name))
            else:
                path = res["path"]
                members = [mm for mm in (res.get("members") or []) if mm.get("kind") == "pdf"]
                if members:                          # a ZIP of PDFs: the largest member is the report
                    best = max(members, key=lambda mm: mm["bytes"])
                    path = run_dir / best["path"] if not Path(best["path"]).is_absolute() else Path(best["path"])
                item["cached_path"] = str(Path(path).relative_to(run_dir)) if str(path).startswith(str(run_dir)) else str(path)
                item["cached_sha256"] = res.get("sha256", "")
                pages = pages_of(str(path))
                item["cached_pages"] = pages or ""
                if pages is not None and pages < 4:
                    item["flags"].append("short_document")
                log("  [%d/%d] ok %s -> %s (%s pages)" % (n, len(todo), name, item["cached_path"], pages or "?"))
            time.sleep(sleep)

    # Cross-check the two channels -------------------------------------------------------------------------
    for item in items:
        if item["local_path"] and item["local_path"].lower().endswith(".pdf"):
            lp = pages_of(item["local_path"])
            item["local_pages"] = lp or ""
            if item["cached_path"]:
                cached = str(run_dir / item["cached_path"]) if not Path(item["cached_path"]).is_absolute() else item["cached_path"]
                cp = item["cached_pages"] or pages_of(cached)
                if lp and cp and abs(lp - cp) > max(2, round(0.03 * max(lp, cp))):
                    item["flags"].append("page_count_mismatch(local %s vs exchange %s)" % (lp, cp))
                sim = jaccard(pdf_text_tokens(item["local_path"]), pdf_text_tokens(cached))
                if sim is not None and sim < 0.35:
                    item["flags"].append("content_mismatch(similarity %.2f)" % sim)
        if item["local_doc_id"] and item["primary_url"]:
            item["status"] = "both"
        elif item["primary_url"]:
            item["status"] = "exchange_only"
        elif item["local_doc_id"]:
            item["status"] = "local_only"
            item["flags"].append("local_only")
        else:
            item["status"] = "missing"
            item["flags"].append("missing")

    # Text layer (scripts/doc_text.py): every core PDF, exchange or local, gets page-anchored text and a page index.
    pdfs = []
    for item in items:
        if item["doc_type"] not in CORE_TYPES:
            continue
        for key in ("cached_path", "local_path"):
            v = item.get(key) or ""
            if v.lower().endswith(".pdf"):
                full = Path(v) if Path(v).is_absolute() else run_dir / v
                if full.exists():
                    pdfs.append(full)
    if pdfs and doc_text.tool("pdftotext"):
        idx = doc_text.convert_many(run_dir, sorted(set(pdfs)), log=lambda m: None)
        for item in items:
            for key in ("cached_path", "local_path"):
                v = item.get(key) or ""
                full = str(Path(v) if Path(v).is_absolute() else run_dir / v)
                e = idx.get(full)
                if e and not item.get("text_path"):
                    item["text_path"] = str(Path(e["text"]).relative_to(run_dir)) if e["text"].startswith(str(run_dir)) else e["text"]
                    item["text_flags"] = "; ".join("%s %d p." % kv for kv in sorted(e["flags"].items()))

    anomalies = []
    for l in local:                                  # a local label vs. the exchange filing of the same date
        ltype, ld = LOCAL_TYPE[l["doc_type"]], ei.parse_date(l.get("date") or "")
        if not ld or ltype == "results":
            continue
        near = [r for r in usable if (r["doc_type"] == ltype) and r.get("fiscal_period")
                and ei.parse_date(r.get("date") or "") and abs((ei.parse_date(r["date"]) - ld).days) <= 5]
        if near and all(r["fiscal_period"] != l.get("fiscal_period") for r in near):
            anomalies.append({"doc_id": l["doc_id"], "local_type": ltype, "local_date": l.get("date"),
                              "local_label": l.get("fiscal_period"), "exchange_labels": sorted({r["fiscal_period"] for r in near}),
                              "headline": l.get("headline", "")[:100]})
    for a in anomalies:
        for item in items:
            if a["doc_id"] in item["local_doc_id"].split(";"):
                item["flags"].append("period_label_mismatch(local %s vs exchange %s)" % (a["local_label"], "/".join(a["exchange_labels"])))

    write_outputs(run_dir, m, cutoff, items, anomalies, failures, index, local, fy_list, q_list)
    return {"items": len(items), "failures": failures, "anomalies": anomalies}


def write_outputs(run_dir, m, cutoff, items, anomalies, failures, index, local, fy_list, q_list):
    out_dir = run_dir / "corpus"
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "document_map.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MAP_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for it in items:
            w.writerow(dict(it, flags="; ".join(it["flags"])))
    mins = rl.depth_minimums()
    standard = {"annual_report": mins.get("filings.annual_report_years", 10), "transcript": mins.get("concalls.quarters", 12),
                "investor_presentation": 0, "results": 12, "shareholding": mins.get("management.shareholding_quarters", 12)}
    lines = ["# Document Map — %s (%s) · run %s" % (m.get("company"), m.get("ticker"), m.get("run_id")), "",
             "Built %s by `scripts/document_map.py` from the exchange / IR / archive index (`exchange_index.py`) and the local "
             "FilingForge catalog. Research cutoff **%s**: documents filed after it are excluded. Both channels are "
             "evidence at par; where they disagree, the flags below say which copy to trust and what to check."
             % (dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), cutoff.isoformat()), "",
             "Local corpus: %s." % ("%d core documents in corpus/catalog.csv" % len(local) if local else
                                    "**not available** (company not in the FilingForge library, or `corpus.py catalog` not run)"),
             "Index: %d documents (%s)." % (len(index), ", ".join("%s %d" % kv for kv in sorted(Counter(r["source"] for r in index).items()))),
             "", "## Coverage against the depth standard", "",
             "| Document | Periods required | Located (any channel) | Exchange / IR / archive copy | Local copy | Both | Missing | Standard |",
             "|---|---|---|---|---|---|---|---|"]
    for dtype in ("annual_report",) + QUARTERLY_REQUIRED:
        rows = [i for i in items if i["doc_type"] == dtype]
        located = sum(1 for i in rows if i["status"] != "missing")
        need = standard.get(dtype, 0)
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %s |" % (
            LABEL[dtype], len(rows), located, sum(1 for i in rows if i["primary_url"]),
            sum(1 for i in rows if i["local_doc_id"]), sum(1 for i in rows if i["status"] == "both"),
            sum(1 for i in rows if i["status"] == "missing"),
            ("met (%d ≥ %d)" % (located, need) if located >= need else "**short: %d < %d**" % (located, need)) if need else "—"))
    flagged = [i for i in items if any(not f.startswith(("missing", "local_only")) for f in i["flags"])]
    lines += ["", "## Cross-check flags (two channels)", ""]
    if flagged or anomalies:
        lines += ["| Document | Period | Flags | Local | Exchange copy |", "|---|---|---|---|---|"]
        for i in flagged:
            lines.append("| %s | %s | %s | %s | %s |" % (LABEL[i["doc_type"]], i["period"], "; ".join(i["flags"]),
                                                       i["local_doc_id"] or "—", i["cached_path"] or i["primary_url"] or "—"))
        for a in anomalies:
            lines.append("| Local %s (%s) | %s | period_label_mismatch: exchange filing of the same date is %s | %s | — |" % (
                a["local_type"], a["local_date"], a["local_label"], "/".join(a["exchange_labels"]), a["doc_id"]))
        lines += ["", "Where a flag exists, read the **exchange copy** and cite it; report the local defect in your "
                  "missing-evidence list so the owner can re-download it."]
    else:
        lines.append("No disagreements between the local corpus and the exchange copies.")
    if failures:
        lines += ["", "## Download failures (after mirrors and archive fallback)", ""]
        lines += ["- %s: %s" % (f["item"], f["error"]) for f in failures]
    for dtype in ("annual_report",) + QUARTERLY_REQUIRED:
        rows = [i for i in items if i["doc_type"] == dtype]
        lines += ["", "## %s" % LABEL[dtype], "",
                  "| Period | Status | Filed | Local (FilingForge) | Exchange copy in this run | Text layer (pages to read visually) | Source URL | Flags |",
                  "|---|---|---|---|---|---|---|---|"]
        for i in rows:
            cached = "`%s` (%s p.)" % (i["cached_path"], i["cached_pages"] or "?") if i["cached_path"] else "—"
            local_s = "`%s`%s" % (i["local_doc_id"], " (%s p.)" % i["local_pages"] if i["local_pages"] else "") if i["local_doc_id"] else "—"
            text_s = "`%s`%s" % (i["text_path"], " (%s)" % i["text_flags"] if i.get("text_flags") else "") if i.get("text_path") else "—"
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (i["period"], i["status"], i["filed"] or "—", local_s, cached,
                                                                      text_s, i["primary_url"] or "—", "; ".join(i["flags"]) or ""))
    other = Counter(r["doc_type"] for r in index if r["doc_type"] not in CORE_TYPES + QUARTERLY_REQUIRED + ("results_xbrl",))
    lines += ["", "## Other indexed filings", "",
              "Query them with `python3 scripts/exchange_index.py show --run RUN_DIR --type <type> [--period FY2025]`:", "",
              ", ".join("%s %d" % kv for kv in other.most_common()), "",
              "## How to use this map", "",
              "- **Read through the text layer** (`doc_text.py toc` for the section's pages, then Read the `pages.md` lines "
              "it gives, or `doc_text.py page`); search across all documents with `doc_text.py search`. Cite the PDF page "
              "in the `<<<PAGE n>>>` anchor (exchange documents by URL, corpus documents as `FilingForge:<doc_id>`).",
              "- **Zero-loss rule:** confirm every decision-critical number on the rendered PDF page (Read tool, "
              "`pages: \"n\"`) and with `doc_text.py verify`; read every flagged page (image-only, rotated, table "
              "mismatch or alignment-uncertain, encoding) visually, never from the text layer.",
              "- `fetch_source.py` reuses these cached files automatically when you request the same URL.",
              "- A `missing` or `local_only` row is not proof the document does not exist: try the company IR site, the "
              "other exchange and a web search (`RESEARCH_PLAYBOOK.md` §1a) before recording a gap."]
    (out_dir / "DOCUMENT_MAP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def add(run_dir: Path, dtype: str, period: str, url: str, alts: List[str], note: str, log=print) -> int:
    """Register a document found outside the indexes (the librarian's tool): download and validate it, build its
    text layer, and fill (or add) its row of the map. The file must be the document named: the librarian checks the
    first page (company, type, period) before calling this, and the row records who found it and where."""
    path = run_dir / "corpus" / "document_map.csv"
    if not path.exists():
        print("no document map: run document_map.py build first")
        return 1
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    expect = "pdf" if url.lower().split("?")[0].endswith(".pdf") else ""
    res = fs.retrieve(run_dir, url, "librarian", "%s %s (found by the librarian)" % (LABEL.get(dtype, dtype), period),
                      alts=alts or None, expect=expect, wayback=True)
    if res.get("path") is None:
        print("FAILED: %s" % (res.get("error") or "download failed")[:300])
        return 1
    pdf = Path(res["path"])
    members = [mm for mm in (res.get("members") or []) if mm.get("kind") == "pdf"]
    if members:
        best = max(members, key=lambda mm: mm["bytes"])
        pdf = run_dir / best["path"] if not Path(best["path"]).is_absolute() else Path(best["path"])
    pages = pages_of(str(pdf))
    text_path, text_flags = "", ""
    if doc_text.tool("pdftotext") and str(pdf).lower().endswith(".pdf"):
        idx = doc_text.convert_many(run_dir, [pdf], log=lambda m: None)
        e = idx.get(str(pdf))
        if e:
            text_path = str(Path(e["text"]).relative_to(run_dir)) if e["text"].startswith(str(run_dir)) else e["text"]
            text_flags = "; ".join("%s %d p." % kv for kv in sorted(e["flags"].items()))
    cached = str(pdf.relative_to(run_dir)) if str(pdf).startswith(str(run_dir)) else str(pdf)
    row = next((r for r in rows if r["doc_type"] == dtype and r["period"] == period), None)
    if row is None:
        row = {c: "" for c in MAP_COLUMNS}
        row.update(doc_type=dtype, period=period)
        rows.append(row)
    flags = [f for f in (row.get("flags") or "").split("; ") if f and f not in ("missing", "download_failed")]
    flags.append("added_by_librarian")
    if pages is not None and pages < 4:
        flags.append("short_document")
    row.update(primary_source=row.get("primary_source") or "LIBRARIAN", primary_url=row.get("primary_url") or url,
               cached_path=cached, cached_sha256=res.get("sha256", ""), cached_pages=pages or "",
               text_path=text_path or row.get("text_path", ""), text_flags=text_flags or row.get("text_flags", ""),
               status="both" if row.get("local_doc_id") else "exchange_only", flags="; ".join(flags))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MAP_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    md = run_dir / "corpus" / "DOCUMENT_MAP.md"
    text = md.read_text(encoding="utf-8") if md.exists() else ""
    if "## Added after the build (librarian)" not in text:
        text += "\n## Added after the build (librarian)\n\n| Document | Period | File | Pages | Source | Note |\n|---|---|---|---|---|---|\n"
    text += "| %s | %s | `%s` | %s | %s | %s |\n" % (LABEL.get(dtype, dtype), period, cached, pages or "?", url, note or "")
    md.write_text(text, encoding="utf-8")
    log("added %s %s: %s (%s pages, text %s)" % (dtype, period, cached, pages or "?", text_path or "not built"))
    return 0


def status(run_dir: Path) -> int:
    path = run_dir / "corpus" / "document_map.csv"
    if not path.exists():
        print("no document map: run document_map.py build first")
        return 1
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for dtype in ("annual_report",) + QUARTERLY_REQUIRED:
        sub = [r for r in rows if r["doc_type"] == dtype]
        c = Counter(r["status"] for r in sub)
        print("%-22s %s" % (dtype, ", ".join("%s %d" % kv for kv in sorted(c.items()))))
    flagged = [r for r in rows if r["flags"] and not r["flags"].startswith(("missing", "local_only"))]
    for r in flagged:
        print("  flag %s %s: %s" % (r["doc_type"], r["period"], r["flags"]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("run_dir")
    b.add_argument("--years", type=int, default=15, help="annual reports to map (fiscal years back from the latest)")
    b.add_argument("--quarters", type=int, default=24, help="quarters of transcripts, presentations, results, shareholding")
    b.add_argument("--download", choices=["core", "none"], default="core")
    b.add_argument("--sleep", type=float, default=0.5)
    s = sub.add_parser("status")
    s.add_argument("run_dir")
    ad = sub.add_parser("add")
    ad.add_argument("run_dir")
    ad.add_argument("--type", required=True, choices=list(LABEL))
    ad.add_argument("--period", required=True)
    ad.add_argument("--url", required=True)
    ad.add_argument("--alt", action="append", default=[])
    ad.add_argument("--note", default="")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "status":
        return status(run_dir)
    if a.cmd == "add":
        return add(run_dir, a.type, a.period, a.url, a.alt, a.note)
    res = build(run_dir, a.years, a.quarters, a.download, a.sleep)
    print("document map: %d items, %d download failures, %d local label anomalies -> %s" % (
        res["items"], len(res["failures"]), len(res["anomalies"]), run_dir / "corpus" / "DOCUMENT_MAP.md"))
    return status(run_dir)


if __name__ == "__main__":
    sys.exit(main())
