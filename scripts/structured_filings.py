#!/usr/bin/env python3
"""Structured exchange filings → exact facts (Stage 0, methodology 3.1.0): what companies must file as data.

  python3 scripts/structured_filings.py fetch   RUN_DIR [--symbol SYM] [--years 10]
  python3 scripts/structured_filings.py summary RUN_DIR

Regulators make listed companies file many key facts in machine-readable form. They are primary and exact, so they
replace reading where they cover a topic and cross-check the reports elsewhere (`methodology/SOURCE_GUIDE.md` §0c).
Verified on NSE for BHARTIARTL on 2026-10-18:

  BRSR XBRL          /api/corporate-bussiness-sustainabilitiy?index=equities&symbol=S&from_date=..&to_date=..
                     (sic: NSE's spelling) one XBRL instance per year since FY2022 (BRSR taxonomy, dimensional)
  AGM / postal-ballot voting results XBRL   /api/corporate-voting-results?index=equities&symbol=S&from_date=..&to_date=..
                     votes polled, for and against by shareholder category for every resolution
  Integrated Filing (Financial), from Q3 FY2025, exchange-rendered view of the XBRL (`exchange_index.py nse` indexes
                     it): the year-end filing states the audit opinion ("Declaration of unmodified opinion" or the
                     statement on the impact of audit qualifications) and names the audit firms
  Integrated Filing (Governance), from Q3 FY2025: board composition (category, appointment, tenure, cessation)

Related-party disclosures under Reg. 23(9) are filed half-yearly as PDF announcements; `reading.py fetch-filings`
fetches them and the readers read them (they are a critical class). The ministry's own XBRL of the accounts (with
CARO answers) sits behind the MCA portal's login and paid document view, so it is out of reach of these scripts.

Writes RUN_DIR/corpus/structured/{brsr_facts.csv, voting_results.csv, audit_opinions.csv, governance_board.csv} and
RUN_DIR/corpus/STRUCTURED.md (committed); raw filings in RUN_DIR/_cache/structured/. `reading.py plan` uses the
BRSR facts to mark an annual-report BRSR page `structured` when the filing carries that page's numbers and text.
Exit: 0 ok (even if a feed is empty; see the summary), 1 nothing fetched at all, 2 usage.
"""

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

NSE_API = "https://www.nseindia.com/api"
OUT = "corpus/structured"
CACHE = "_cache/structured"
YEAR_RE = re.compile(r"^(19[5-9]\d|20[0-4]\d)$")
NUM_TOKEN_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?%?")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _prefix(tag: str, nsmap: Dict[str, str]) -> str:
    if tag.startswith("{"):
        uri = tag[1:].split("}", 1)[0]
        for k, v in nsmap.items():
            if v == uri:
                return k
    return ""


# --------------------------------------------------------------------------------------------------------------
# Generic XBRL instance
# --------------------------------------------------------------------------------------------------------------

def parse_instance(path: Path) -> Tuple[Dict[str, dict], List[dict]]:
    """(contexts, facts). A context gives its period and its dimensions (explicit members and typed values)."""
    nsmap = {}
    for _, (k, v) in ET.iterparse(str(path), events=["start-ns"]):
        nsmap.setdefault(k, v)
    root = ET.parse(str(path)).getroot()
    contexts = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        start = end = instant = None
        dims = {}
        for x in c.iter():
            t = _local(x.tag)
            if t == "startDate":
                start = (x.text or "").strip()
            elif t == "endDate":
                end = (x.text or "").strip()
            elif t == "instant":
                instant = (x.text or "").strip()
            elif t == "explicitMember":
                dims[(x.get("dimension") or "").split(":")[-1]] = (x.text or "").strip().split(":")[-1]
            elif t == "typedMember":
                val = " ".join((y.text or "").strip() for y in x.iter() if y is not x and (y.text or "").strip())
                dims[(x.get("dimension") or "").split(":")[-1]] = val
        contexts[c.get("id")] = {"start": start, "end": end, "instant": instant, "dims": dims}
    facts = []
    for el in root.iter():
        cid = el.get("contextRef")
        if not cid:
            continue
        facts.append({"concept": _local(el.tag), "prefix": _prefix(el.tag, nsmap), "context": cid,
                      "unit": el.get("unitRef") or "", "decimals": el.get("decimals") or "",
                      "value": (el.text or "").strip()})
    return contexts, facts


def fact_rows(contexts: Dict[str, dict], facts: List[dict], extra: dict) -> List[dict]:
    rows = []
    for f in facts:
        c = contexts.get(f["context"], {})
        rows.append(dict(extra, concept=f["concept"], context=f["context"],
                         period=c.get("instant") or "%s..%s" % (c.get("start") or "", c.get("end") or ""),
                         dims="; ".join("%s=%s" % kv for kv in sorted(c.get("dims", {}).items())),
                         unit=f["unit"], decimals=f["decimals"], value=re.sub(r"\s+", " ", html.unescape(f["value"]))[:4000]))
    return rows


# --------------------------------------------------------------------------------------------------------------
# Exchange-rendered Integrated Filing views (HTML tables of the XBRL values)
# --------------------------------------------------------------------------------------------------------------

def html_cells(text: str) -> List[List[str]]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", td))).strip()
                 for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
        if any(cells):
            rows.append(cells)
    return rows


def audit_opinion_from_view(text: str) -> dict:
    """The declaration (unmodified opinion or impact of qualifications) and the audit firms in a year-end view."""
    rows = html_cells(text)
    out = {"declaration": "", "firms": [], "qualification_rows": []}
    in_aq, in_firms = False, False
    for cells in rows:
        joined = " | ".join(cells)
        low = joined.lower()
        if "declaration of unmodified opinion or statement on impact of audit qualification" in low and len(cells) >= 2:
            out["declaration"] = cells[-1]
        if "impact of audit qualification" in low:
            in_aq = True
        if len(cells) >= 2 and cells[1].lower().startswith("audit firm"):
            in_firms = True                   # the "Sr No. | Audit firm's name | peer review ..." grid
            continue
        if in_firms:
            if len(cells) >= 2 and re.fullmatch(r"\d{1,2}\.?", cells[0]):
                out["firms"].append(cells[1])
                continue
            in_firms = False
        if in_aq and re.search(r"qualification|basis for qualified|adverse|disclaimer", low) and "declaration" not in low:
            out["qualification_rows"].append(joined[:300])
    out["firms"] = sorted(set(out["firms"]))
    return out


def board_from_governance_view(text: str) -> List[dict]:
    rows = html_cells(text)
    header, out = None, []
    for cells in rows:
        low = [c.lower() for c in cells]
        if "name of the director" in low:
            header = low
            continue
        if header and len(cells) == len(header):
            rec = dict(zip(header, cells))
            name = rec.get("name of the director", "")
            if name and not name.lower().startswith(("title", "name")):
                out.append({"director": name, "category": next((v for k, v in rec.items() if "category" in k), ""),
                            "initial_appointment": rec.get("initial date of appointment", ""),
                            "reappointment": rec.get("date of re-appointment", ""), "cessation": rec.get("date of cessation", ""),
                            "tenure_months": rec.get("tenure of director (in months)", "")})
        elif header and len(cells) < 3:
            header = None
    return out


# --------------------------------------------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------------------------------------------

def _get_json(url: str, work: str):
    import netfetch as nf  # noqa: E402
    try:
        return nf.get_json(url, work), ""
    except nf.FetchError as exc:
        return None, "HTTP %s" % exc.status


def _download(run_dir: Path, url: str, name: str, expect: str) -> Optional[Path]:
    import fetch_source as fs  # noqa: E402
    res = fs.retrieve(run_dir, url, "cio", name, expect=expect, wayback=False)
    return Path(res["path"]) if res.get("path") else None


def fetch(run_dir: Path, symbol: str, years: int, log=print) -> dict:
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    try:
        cutoff = dt.date.fromisoformat(str(m.get("research_cutoff")))
    except ValueError:
        cutoff = dt.date.today()
    work = str(run_dir / "_cache" / ".net")
    out_dir = run_dir / OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"symbol": symbol, "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
               "feeds": {}}
    # BRSR ------------------------------------------------------------------------------------------------------
    url = "%s/corporate-bussiness-sustainabilitiy?index=equities&symbol=%s&from_date=01-01-%d&to_date=%s" % (
        NSE_API, symbol, cutoff.year - years, cutoff.strftime("%d-%m-%Y"))
    data, err = _get_json(url, work)
    rows, files = [], []
    for r in (data or {}).get("data", []) if isinstance(data, dict) else []:
        x = r.get("xbrlFile") or ""
        fy = "FY%s" % r.get("fyTo") if r.get("fyTo") else ""
        if not x.lower().endswith(".xml") or not fy:
            continue
        path = _download(run_dir, x, "BRSR XBRL %s" % fy, "xml")
        time.sleep(0.4)
        if not path:
            files.append({"fy": fy, "url": x, "ok": False})
            continue
        try:
            ctx, facts = parse_instance(path)
        except ET.ParseError as exc:
            files.append({"fy": fy, "url": x, "ok": False, "error": str(exc)[:120]})
            continue
        rows += fact_rows(ctx, facts, {"fy": fy, "filed": r.get("submissionDate", ""), "source_url": x})
        files.append({"fy": fy, "url": x, "ok": True, "facts": len(facts)})
    _write_csv(out_dir / "brsr_facts.csv", rows, ["fy", "filed", "concept", "context", "period", "dims", "unit", "decimals", "value", "source_url"])
    summary["feeds"]["brsr"] = {"endpoint": url, "error": err, "filings": files, "facts": len(rows)}
    log("BRSR: %d filings, %d facts%s" % (sum(1 for f in files if f["ok"]), len(rows), " (%s)" % err if err else ""))
    # Voting results ------------------------------------------------------------------------------------------
    url = "%s/corporate-voting-results?index=equities&symbol=%s&from_date=01-01-%d&to_date=%s" % (
        NSE_API, symbol, cutoff.year - years, cutoff.strftime("%d-%m-%Y"))
    data, err = _get_json(url, work)
    vrows, vfiles = [], []
    for r in data if isinstance(data, list) else []:
        md = r.get("metadata") or {}
        x = md.get("vrXbrlFilename") or ""
        if not x.lower().endswith(".xml"):
            continue
        path = _download(run_dir, x, "Voting results XBRL %s %s" % (md.get("vrMeetingType", ""), md.get("vrTimestamp", "")), "xml")
        time.sleep(0.4)
        if not path:
            vfiles.append({"meeting": md.get("vrTimestamp", ""), "ok": False})
            continue
        try:
            ctx, facts = parse_instance(path)
        except ET.ParseError:
            vfiles.append({"meeting": md.get("vrTimestamp", ""), "ok": False})
            continue
        vrows += fact_rows(ctx, facts, {"meeting_type": md.get("vrMeetingType", ""), "meeting_date": md.get("vrTimestamp", ""),
                                        "source_url": x})
        vfiles.append({"meeting": md.get("vrTimestamp", ""), "type": md.get("vrMeetingType", ""), "ok": True, "facts": len(facts)})
    _write_csv(out_dir / "voting_results.csv", vrows, ["meeting_type", "meeting_date", "concept", "context", "period", "dims",
                                                        "unit", "decimals", "value", "source_url"])
    summary["feeds"]["voting_results"] = {"endpoint": url, "error": err, "meetings": vfiles, "facts": len(vrows)}
    log("Voting results: %d meetings, %d facts%s" % (sum(1 for f in vfiles if f["ok"]), len(vrows), " (%s)" % err if err else ""))
    # Integrated filings (audit opinion, governance) ---------------------------------------------------------
    raw = run_dir / "_cache" / "index" / "raw" / "nse_integrated_results.json"
    integ = json.loads(raw.read_text(encoding="utf-8")).get("data", []) if raw.exists() else []
    if not integ:
        data, err = _get_json("%s/integrated-filing-results?index=equities&symbol=%s" % (NSE_API, symbol), work)
        integ = (data or {}).get("data", []) if isinstance(data, dict) else []
    arows, grows = [], []
    for r in integ:
        url = r.get("ixbrl") or ""
        qe = r.get("qe_Date") or ""
        if not url:
            continue
        is_gov = "GOVERNANCE" in url.upper()
        if not is_gov and not qe.upper().startswith("31-MAR"):
            continue                          # the audit opinion is stated in the year-end filing
        path = _download(run_dir, url, "Integrated Filing %s %s" % ("governance" if is_gov else "financial", qe), "any")
        time.sleep(0.4)
        if not path:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if is_gov:
            for b in board_from_governance_view(text):
                grows.append(dict(b, quarter_end=qe, source_url=url))
        else:
            a = audit_opinion_from_view(text)
            arows.append({"period_end": qe, "basis": r.get("consolidated") or "", "declaration": a["declaration"],
                          "firms": "; ".join(a["firms"]), "qualification_rows": " || ".join(a["qualification_rows"])[:1500],
                          "source_url": url})
    _write_csv(out_dir / "audit_opinions.csv", arows, ["period_end", "basis", "declaration", "firms", "qualification_rows", "source_url"])
    _write_csv(out_dir / "governance_board.csv", grows, ["quarter_end", "director", "category", "initial_appointment",
                                                          "reappointment", "cessation", "tenure_months", "source_url"])
    summary["feeds"]["integrated_filing"] = {"year_end_filings": len(arows), "governance_rows": len(grows),
                                             "note": "Integrated Filings exist from Q3 FY2025; earlier audit opinions are in the "
                                                     "auditor's report on the annual results (a results PDF, read by the readers)"}
    log("Integrated filings: %d year-end audit statements, %d board rows" % (len(arows), len(grows)))
    rl.write_json(out_dir / "summary.json", summary)
    write_summary(run_dir, summary)
    return summary


def _write_csv(path: Path, rows: List[dict], cols: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_summary(run_dir: Path, s: dict) -> None:
    f = s.get("feeds", {})
    lines = ["# Structured exchange filings — %s" % s.get("symbol", ""), "",
             "Fetched %s by `scripts/structured_filings.py` (primary, tier 1; exact values as filed). Use them before any "
             "reading of the same facts, and to cross-check the annual reports." % s.get("fetched_at", ""), "",
             "| Feed | Coverage | Records | File | Notes |", "|---|---|---|---|---|"]
    b = f.get("brsr", {})
    lines.append("| BRSR XBRL | %s | %d facts | `corpus/structured/brsr_facts.csv` | %s |" % (
        ", ".join(x["fy"] for x in b.get("filings", []) if x.get("ok")) or "none", b.get("facts", 0), b.get("error") or ""))
    v = f.get("voting_results", {})
    lines.append("| Voting results XBRL | %s | %d facts | `corpus/structured/voting_results.csv` | %s |" % (
        ", ".join("%s %s" % (x.get("type", ""), x["meeting"]) for x in v.get("meetings", []) if x.get("ok")) or "none",
        v.get("facts", 0), v.get("error") or ""))
    i = f.get("integrated_filing", {})
    lines.append("| Integrated Filing: audit opinion | from FY2025 | %d year-end filings | `corpus/structured/audit_opinions.csv` | %s |" % (
        i.get("year_end_filings", 0), i.get("note", "")))
    lines.append("| Integrated Filing: board composition | from Q3 FY2025 | %d rows | `corpus/structured/governance_board.csv` | |" % (
        i.get("governance_rows", 0)))
    lines += ["", "Related-party disclosures (Reg. 23(9), half-yearly) are PDF announcements: `corpus/reading/filings.csv` and "
                  "the reading stage. Results XBRL: `calc/xbrl_facts.csv` (`xbrl_facts.py`)."]
    (run_dir / rl.STRUCTURED_SUMMARY).write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------------------------------
# BRSR page coverage (used by reading.py plan)
# --------------------------------------------------------------------------------------------------------------

def _numbers(text: str) -> List[float]:
    out = []
    for tok in NUM_TOKEN_RE.findall(text or ""):
        t = tok.strip("()%").replace(",", "")
        if not t or not re.search(r"\d", t):
            continue
        try:
            v = float(t)
        except ValueError:
            continue
        if YEAR_RE.match(t) or (v.is_integer() and abs(v) < 32 and "." not in t):
            continue                      # years, day numbers, note and page references
        out.append(v)
    return out


def _norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def brsr_coverage_tester(run_dir: Path) -> Optional[Callable[[int, List[str]], Tuple[bool, str]]]:
    path = run_dir / OUT / "brsr_facts.csv"
    if not path.exists():
        return None
    nums, texts, src = defaultdict(set), defaultdict(list), {}
    with path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fy = r["fy"]
            src[fy] = r.get("source_url", "")
            v = r["value"]
            try:
                x = float(v)
                for y in (x, x * 100):
                    nums[fy].add(round(y, 2))
            except ValueError:
                if len(v) >= 3:
                    texts[fy].append(_norm_text(v))
    blobs = {fy: " | ".join(t) for fy, t in texts.items()}

    def test(fy: int, passages: List[str]) -> Tuple[bool, str]:
        key = "FY%d" % fy
        if key not in nums:
            return False, ""
        page_nums = [round(x, 2) for p in passages for x in _numbers(p)]
        long_text = [_norm_text(p) for p in passages if len(re.sub(r"[\d,.%()\s|-]", "", p)) >= 60]
        if not page_nums and not long_text:
            return False, ""
        n_ok = sum(1 for x in page_nums if x in nums[key])
        t_ok = sum(len(t) for t in long_text if t and t in blobs.get(key, ""))
        t_all = sum(len(t) for t in long_text)
        num_share = n_ok / len(page_nums) if page_nums else 1.0
        text_share = t_ok / t_all if t_all else 1.0
        if num_share >= 0.9 and text_share >= 0.9 and (len(page_nums) >= 5 or t_all >= 300):
            return True, "covered by the BRSR XBRL filing for %s (%d of %d numbers, %.0f%% of the text found): %s" % (
                key, n_ok, len(page_nums), 100 * text_share, src.get(key, ""))
        return False, ""

    return test


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("run_dir")
    f.add_argument("--symbol")
    f.add_argument("--years", type=int, default=10)
    s = sub.add_parser("summary")
    s.add_argument("run_dir")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.cmd == "fetch":
        sym = a.symbol or rl.load_json(run_dir / rl.RUN_MANIFEST).get("ticker", "")
        res = fetch(run_dir, sym, a.years)
        got = res["feeds"]["brsr"]["facts"] + res["feeds"]["voting_results"]["facts"] + res["feeds"]["integrated_filing"]["year_end_filings"]
        return 0 if got else 1
    data = rl.load_json(run_dir / OUT / "summary.json") if (run_dir / OUT / "summary.json").exists() else {}
    if not data:
        print("no structured filings fetched yet")
        return 1
    write_summary(run_dir, data)
    print((run_dir / rl.STRUCTURED_SUMMARY).read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
