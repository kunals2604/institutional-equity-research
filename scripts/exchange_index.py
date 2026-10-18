#!/usr/bin/env python3
"""Index a company's filings from the exchanges, its IR site and the Internet Archive (Stage 0 acquisition).

  python3 scripts/exchange_index.py all     --run RUN_DIR --symbol BHARTIARTL [--scrip 532454] \
                                             [--ir https://www.company.com/investors ...] [--wayback-prefix host/path/ ...]
  python3 scripts/exchange_index.py nse     --run RUN_DIR --symbol BHARTIARTL
  python3 scripts/exchange_index.py bse     --run RUN_DIR (--scrip 532454 | --symbol BHARTIARTL) [--years 15]
  python3 scripts/exchange_index.py ir      --run RUN_DIR --url https://www.company.com/investors [--max-pages 60]
  python3 scripts/exchange_index.py wayback --run RUN_DIR --prefix assets.company.com/investor/
  python3 scripts/exchange_index.py show    --run RUN_DIR [--type transcript] [--period FY2025] [--source NSE]

What each source gives (verified from this environment on 2026-10-17; see methodology/SOURCE_GUIDE.md §6):
  NSE  (www.nseindia.com/api, JSON; archives on nsearchives.nseindia.com):
       annual reports since about FY2010 (older ones as ZIPs of PDFs); the full announcement history (transcripts,
       presentations, results, board outcomes, credit ratings, penalties, schemes, KMP changes ...); results with
       XBRL links; quarterly shareholding; board meetings; corporate actions; insider (PIT) and SAST disclosures.
  BSE  (api.bseindia.com, JSON; requires HTTP/2 with a browser header set, which scripts/netfetch.py sends):
       annual reports back to the early 2000s; announcements by year (paged); scrip-code and ISIN lookup.
  IR   the company's investor-relations pages: document links found by a bounded same-site crawl.
  Wayback  every archived document under an IR folder prefix (finds files that moved or were removed, and works
       for JavaScript-only IR sites whose links a crawl cannot see).

Writes the raw responses to RUN_DIR/_cache/index/raw/ and the merged, de-duplicated, classified index to
RUN_DIR/_cache/index/exchange_index.csv (both git-ignored: large and reproducible), plus a committed summary
RUN_DIR/corpus/index_summary.json (counts by source, type and year, and every failed endpoint). Classification and
period labels are heuristics: the document map (scripts/document_map.py) and the reader confirm them.
Exit: 0 at least one source indexed, 1 nothing indexed, 2 usage.
"""

import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.parse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

INDEX_COLUMNS = ["source", "doc_type", "date", "fiscal_period", "title", "category", "url", "alt_url", "size", "ref"]
NSE_API = "https://www.nseindia.com/api"
BSE_API = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_ATTACH = "https://www.bseindia.com/xml-data/corpfiling/%s/%s"
DOC_EXT_RE = re.compile(r"\.(pdf|zip|xlsx?|docx?|pptx?|mp3|mp4|m4a|xml|csv)(?:$|\?)", re.I)

# Ordered: the first match wins. The text is category + title + the file name.
_CLASSES = [
    ("trading_window", r"trading window"),
    ("newspaper", r"newspaper|news paper|copy of (the )?advertisement"),
    ("share_certificate", r"loss of share certificate|duplicate share certificate|issue of duplicate|transmission of shares"),
    ("agm_transcript", r"transcript.{0,60}(\bagm\b|annual general meeting)|(\bagm\b|annual general meeting).{0,60}transcript"),
    ("transcript", r"transcript"),
    ("audio_recording", r"audio|recording|webcast|video link|earnings? call outcome"),
    ("call_schedule", r"schedule of (analyst|investor|earnings|meet)|intimation of (earnings|analyst|investor) (call|meet)|"
                      r"analyst.{0,40}meet.{0,40}(intimation|schedule)|investor meet|earnings? call intimation"),
    ("investor_presentation", r"investor presentation|earnings presentation|analyst presentation|presentation|investor deck|factsheet|fact sheet"),
    ("annual_report", r"annual report|integrated report|integrated annual"),
    ("brsr", r"business responsibility|brsr|sustainability report|esg report"),
    ("credit_rating", r"credit rating|rating rationale|\brating\b"),
    ("shareholding", r"shareholding pattern"),
    ("voting_results", r"voting results|scrutini[sz]er|results of (e-?voting|postal ballot)"),
    ("results", r"financial results|quarterly results|audited results|unaudited|results for the|outcome of board meeting.{0,80}result|"
                r"consolidated result|standalone result|quarterly report|earnings release"),
    ("scheme", r"scheme of arrangement|amalgamation|merger|demerger|composite scheme"),
    ("rpt", r"related party"),
    ("auditor", r"statutory auditor|auditor"),
    ("kmp_change", r"resignation|appointment|change in (director|management|key managerial)|cessation|re-appointment"),
    ("penalty_order", r"penalt|show cause|demand notice|order(s)? passed|action\(s\) taken|adjudication|litigation|dispute|tax demand"),
    ("insider_sast", r"insider trading|takeover|\bsast\b|regulation 29|regulation 31|encumbrance|pledge"),
    ("capital", r"allotment|preferential|rights issue|\bqip\b|warrant|buy-?back|bonus|split|esop|esos|\bncd\b|debenture|commercial paper"),
    ("agm_egm", r"annual general meeting|\bagm\b|\begm\b|extra-?ordinary general|postal ballot|book closure|record date"),
    ("board_meeting", r"board meeting|outcome of board"),
    ("press_release", r"press release|media release"),
    ("acquisition", r"acquisition|investment in|stake"),
    ("dividend", r"dividend"),
]
CLASS_RES = [(k, re.compile(p, re.I)) for k, p in _CLASSES]
NOISE_TYPES = {"trading_window", "newspaper", "share_certificate"}


def classify(*parts: str) -> str:
    text = " ".join(p for p in parts if p)
    for name, rx in CLASS_RES:
        if rx.search(text):
            return name
    return "other"


def parse_date(s: str) -> Optional[dt.date]:
    s = (s or "").strip()
    if not s:
        return None
    s = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?(\.\d+)?$", "", s.replace("T", " ").split(" to ")[0]).strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%Y%m%d", "%b %d, %Y"):
        try:
            return dt.datetime.strptime(s.title() if "%b" in fmt or "%B" in fmt else s, fmt).date()
        except ValueError:
            continue
    m = re.match(r"(\d{4})(\d{2})(\d{2})", s)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def fiscal_year(d: dt.date, fy_end_month: int = 3) -> int:
    """FY label year: for an April-March year, FY2026 = 1-Apr-2025 to 31-Mar-2026."""
    if fy_end_month == 12:
        return d.year
    return d.year + 1 if d.month > fy_end_month else d.year


def quarter_label(period_end: dt.date, fy_end_month: int = 3) -> str:
    """QnFYyyyy for the fiscal quarter ending on (or in the month of) period_end."""
    months_after_fy_start = (period_end.month - fy_end_month - 1) % 12
    return "Q%dFY%d" % (months_after_fy_start // 3 + 1, fiscal_year(period_end, fy_end_month))


def month_end(year: int, month: int) -> dt.date:
    return dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)


def last_quarter_end_before(d: dt.date, fy_end_month: int = 3, lag_days: int = 10) -> dt.date:
    """The most recent fiscal-quarter end at least `lag_days` before d (calls discuss the quarter just ended)."""
    ref = d - dt.timedelta(days=lag_days)
    months = sorted({(fy_end_month - 1 + 3 * k) % 12 + 1 for k in range(4)})
    ends = [month_end(y, m) for y in (ref.year - 1, ref.year) for m in months]
    return max(e for e in ends if e <= ref)


QUARTERLY_TYPES = ("transcript", "audio_recording", "investor_presentation", "results", "results_xbrl", "shareholding",
                   "call_schedule", "press_release")
Q_FY_RE = re.compile(r"(?<![A-Za-z0-9])Q\s*([1-4])\s*[-']?\s*FY\s*'?(\d{4}|\d{2})(?!\d)", re.I)
N_Q_FY_RE = re.compile(r"(?<![A-Za-z0-9])([1-4])\s*Q\s*[-']?\s*FY\s*'?(\d{4}|\d{2})(?!\d)", re.I)
ORD_Q = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
QUARTER_ENDED_RE = re.compile(r"quarter\s+end(?:ed|ing)?\s+(?:on\s+)?([A-Za-z]{3,9})[\s-]+(\d{1,2})(?:st|nd|rd|th)?[\s,-]+(20\d{2})",
                              re.I)
FOLDER_FY_RE = re.compile(r"(?<!\d)(20\d{2})\s*[-_–/]\s*(\d{2})(?!\d)")
FOLDER_Q_RE = re.compile(r"(?:^|[/ ])q([1-4])(?:[/ ]|$)", re.I)
FY_RE = re.compile(r"(?<![A-Za-z0-9])FY\s*'?(\d{4}|\d{2})(?!\d)", re.I)
TITLE_Q_RE = Q_FY_RE          # kept for older callers
TITLE_FY_RE = FY_RE


def _yy(s: str) -> int:
    n = int(s)
    return n + 2000 if n < 100 else n


def period_from_text(text: str, quarterly: bool, fy_end_month: int = 3) -> str:
    """A fiscal period stated in a title, file name or URL path, or '' if none is stated."""
    t = re.sub(r"[_+]+", " ", urllib.parse.unquote(text or ""))
    t = re.sub(r"(?<=[A-Za-z])-(?=[A-Za-z0-9])|(?<=\d)-(?=[A-Za-z])", " ", t)
    if quarterly:
        for rx in (Q_FY_RE, N_Q_FY_RE):
            m = rx.search(t)
            if m:
                return "Q%sFY%d" % (m.group(1), _yy(m.group(2)))
        m = QUARTER_ENDED_RE.search(t)
        if m:
            d = parse_date("%s-%s-%s" % (m.group(2), m.group(1)[:3], m.group(3)))
            if d:
                return quarter_label(d, fy_end_month)
        f, q = FOLDER_FY_RE.search(t), FOLDER_Q_RE.search(t)
        if f and q:
            return "Q%sFY%d" % (q.group(1), _yy(f.group(2)))
        return ""
    m = FY_RE.search(t)
    if m:
        return "FY%d" % _yy(m.group(1))
    f = FOLDER_FY_RE.search(t)
    if f:
        return "FY%d" % _yy(f.group(2))
    m = re.search(r"(?<!\d)(20\d{2})\s*[-–/]\s*(20\d{2})(?!\d)", t)
    if m:
        return "FY%d" % int(m.group(2))
    return ""


def infer_period(doc_type: str, date: Optional[dt.date], title: str, fy_end_month: int = 3) -> str:
    """Best-effort fiscal period: QnFYyyyy for quarterly documents, FYyyyy for annual ones."""
    quarterly = doc_type in QUARTERLY_TYPES
    stated = period_from_text(title, quarterly, fy_end_month)
    if stated:
        return stated
    if doc_type in ("annual_report", "brsr"):
        if date:   # an annual report is published within ~6 months after the fiscal year it covers
            return "FY%d" % fiscal_year(date - dt.timedelta(days=200), fy_end_month)
        return ""
    if date is None:
        return ""
    if quarterly:
        return quarter_label(last_quarter_end_before(date, fy_end_month), fy_end_month)
    return "FY%d" % fiscal_year(date, fy_end_month)


def row(source, doc_type, date, title, category, url, fy_end_month, alt_url="", size="", ref="", period=""):
    d = date if isinstance(date, dt.date) else parse_date(date)
    title = re.sub(r"\s+", " ", html.unescape(title or "")).strip()[:300]
    return {"source": source, "doc_type": doc_type, "date": d.isoformat() if d else "",
            "fiscal_period": period or infer_period(doc_type, d, title + " " + (url or ""), fy_end_month),
            "title": title, "category": (category or "")[:120], "url": url or "", "alt_url": alt_url or "",
            "size": size or "", "ref": ref or ""}


class Indexer:
    def __init__(self, run_dir: Path, fy_end_month: int = 3, sleep: float = 0.4):
        self.run = run_dir
        self.dir = run_dir / "_cache" / "index"
        self.raw = self.dir / "raw"
        self.raw.mkdir(parents=True, exist_ok=True)
        self.work = str(self.dir / ".work")
        self.fy_end = fy_end_month
        self.sleep = sleep
        self.rows: List[dict] = []
        self.failures: List[dict] = []
        self.endpoints: List[dict] = []

    def get_json(self, label: str, url: str):
        try:
            data = nf.get_json(url, self.work)
            (self.raw / ("%s.json" % re.sub(r"[^A-Za-z0-9_.-]+", "_", label))).write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
            self.endpoints.append({"label": label, "url": url, "ok": True})
            return data
        except nf.FetchError as exc:
            self.failures.append({"label": label, "url": url, "status": exc.status, "attempts": exc.attempts[-3:]})
            self.endpoints.append({"label": label, "url": url, "ok": False})
            return None
        finally:
            time.sleep(self.sleep)

    # --- NSE ------------------------------------------------------------------------------------------------
    def nse(self, symbol: str, years: int = 15, cutoff: Optional[dt.date] = None) -> int:
        n0 = len(self.rows)
        sym = urllib.parse.quote(symbol)
        fy = self.fy_end
        ar = self.get_json("nse_annual_reports", "%s/annual-reports?index=equities&symbol=%s" % (NSE_API, sym))
        for r in (ar or {}).get("data", []) if isinstance(ar, dict) else []:
            to_year = str(r.get("toYr") or "").strip()
            period = "FY%s" % to_year if to_year.isdigit() else ""
            self.rows.append(row("NSE", "annual_report", r.get("broadcast_dttm"), "Annual Report %s-%s" % (r.get("fromYr"), to_year),
                                 "Annual Report", r.get("fileName"), fy, size=r.get("attFileSize") or "", period=period))
        ann = self.get_json("nse_announcements", "%s/corporate-announcements?index=equities&symbol=%s" % (NSE_API, sym))
        if not isinstance(ann, list):        # fall back to one request per year
            ann = []
            end = cutoff or dt.date.today()
            for y in range(end.year - years, end.year + 1):
                part = self.get_json("nse_announcements_%d" % y, "%s/corporate-announcements?index=equities&symbol=%s"
                                     "&from_date=01-01-%d&to_date=31-12-%d" % (NSE_API, sym, y, y))
                ann.extend(part or [])
        for r in ann:
            url = r.get("attchmntFile") or ""
            text = r.get("attchmntText") or ""
            dtype = classify(r.get("desc", ""), text, url.rsplit("/", 1)[-1])
            self.rows.append(row("NSE", dtype, r.get("an_dt") or r.get("sort_date"), text, r.get("desc"), url, fy,
                                 size=r.get("attFileSize") or "", ref=r.get("seq_id") or ""))
        for period_kind in ("Quarterly", "Annual"):
            res = self.get_json("nse_results_%s" % period_kind.lower(),
                                "%s/corporates-financial-results?index=equities&symbol=%s&period=%s" % (NSE_API, sym, period_kind))
            for r in res if isinstance(res, list) else []:
                to_d = parse_date(r.get("toDate"))
                basis = "consolidated" if str(r.get("consolidated", "")).lower().startswith("consolidated") else "standalone"
                label = quarter_label(to_d, fy) if to_d else ""
                title = "Results %s %s %s (%s)" % (r.get("relatingTo", ""), r.get("financialYear", ""), basis, r.get("audited", ""))
                xbrl = r.get("xbrl") or ""
                self.rows.append(row("NSE", "results_xbrl" if xbrl.lower().endswith(".xml") else "results",
                                     r.get("broadCastDate") or r.get("filingDate"), title, "Financial results %s" % basis,
                                     xbrl, fy, ref="%s|%s|%s|%s" % (r.get("seqNumber", ""), basis, r.get("fromDate", ""), r.get("toDate", "")),
                                     period=label))
        integ = self.get_json("nse_integrated_results",
                              "%s/integrated-filing-results?index=equities&symbol=%s" % (NSE_API, sym))
        for r in (integ or {}).get("data", []) if isinstance(integ, dict) else []:
            qe = parse_date(r.get("qe_Date"))
            basis = str(r.get("consolidated") or "").lower() or "governance/other"
            url = r.get("ixbrl") or ""
            pdf = r.get("pdf_attach") or ""
            self.rows.append(row("NSE", "results_xbrl" if "INDAS" in url.upper() else "governance_filing",
                                 r.get("broadcast_Date") or r.get("creation_Date"),
                                 "Integrated Filing %s results, quarter ended %s (%s)" % (basis, r.get("qe_Date"), r.get("audited")),
                                 "Integrated Filing", url, fy, alt_url="" if pdf.endswith("/null") else pdf,
                                 ref="%s|%s" % (r.get("seq_Id", ""), basis), period=quarter_label(qe, fy) if qe else ""))
        shp = self.get_json("nse_shareholding", "%s/corporate-share-holdings-master?index=equities&symbol=%s" % (NSE_API, sym))
        for r in shp if isinstance(shp, list) else []:
            d = parse_date(r.get("date"))
            title = "Shareholding as of %s: promoter and promoter group %s%%, public %s%%, employee trusts %s%%" % (
                r.get("date"), r.get("pr_and_prgrp"), r.get("public_val"), r.get("employeeTrusts"))
            self.rows.append(row("NSE", "shareholding", r.get("broadcastDate"), title, "Shareholding pattern",
                                 r.get("xbrl") or "", fy, ref=r.get("recordId") or "",
                                 period=quarter_label(d, fy) if d else ""))
        bm = self.get_json("nse_board_meetings", "%s/corporate-board-meetings?index=equities&symbol=%s" % (NSE_API, sym))
        for r in bm if isinstance(bm, list) else []:
            self.rows.append(row("NSE", "board_meeting", r.get("bm_date"), "%s: %s" % (r.get("bm_purpose", ""), r.get("bm_desc", "")),
                                 "Board meeting", r.get("attachment") or "", fy))
        ca = self.get_json("nse_corporate_actions", "%s/corporates-corporateActions?index=equities&symbol=%s" % (NSE_API, sym))
        for r in ca if isinstance(ca, list) else []:
            self.rows.append(row("NSE", "corporate_action", r.get("exDate"), "%s (record date %s)" % (r.get("subject", ""), r.get("recDate", "")),
                                 "Corporate action", "", fy))
        end = cutoff or dt.date.today()
        for y in range(end.year - min(years, 12), end.year + 1):
            pit = self.get_json("nse_pit_%d" % y, "%s/corporates-pit?index=equities&symbol=%s&from_date=01-01-%d&to_date=31-12-%d"
                                % (NSE_API, sym, y, y))
            for r in (pit or {}).get("data", []) if isinstance(pit, dict) else []:
                title = "%s (%s): %s %s shares, %s%% -> %s%% (%s)" % (
                    r.get("acqName", ""), r.get("personCategory", ""), r.get("tdpTransactionType") or r.get("acqMode", ""),
                    r.get("secAcq", ""), r.get("befAcqSharesPer", ""), r.get("afterAcqSharesPer", ""), r.get("acqMode", ""))
                self.rows.append(row("NSE", "insider_trade", r.get("acqfromDt") or r.get("date"), title, "Insider trading (PIT)",
                                     r.get("xbrl") or "", fy))
        sast = self.get_json("nse_sast", "%s/corporate-sast-reg29?index=equities&symbol=%s" % (NSE_API, sym))
        for r in (sast or {}).get("data", []) if isinstance(sast, dict) else []:
            att = r.get("attachement") or ""
            title = "%s: %s %s (sold %s, acquired %s, after %s)" % (
                r.get("acquirerName", "").strip(), r.get("acqSaleType", ""), r.get("acqType", ""), r.get("noOfShareSale", ""),
                r.get("noOfShareAcq", ""), r.get("noOfShareAft", ""))
            self.rows.append(row("NSE", "sast", (r.get("acquirerDate") or r.get("timestamp") or "").split(" to ")[0], title,
                                 "SAST Regulation 29", "" if att.endswith("/null") else att, fy))
        return len(self.rows) - n0

    # --- BSE ------------------------------------------------------------------------------------------------
    def bse_lookup(self, text: str) -> Optional[dict]:
        url = "%s/PeerSmartSearch/w?Type=SS&text=%s" % (BSE_API, urllib.parse.quote(text))
        tmp = str(self.dir / ".work" / "bse_search.txt")
        Path(tmp).parent.mkdir(parents=True, exist_ok=True)
        try:
            nf.fetch(url, tmp, expect="any", retries=3)
        except nf.FetchError as exc:
            self.failures.append({"label": "bse_lookup", "url": url, "status": exc.status, "attempts": exc.attempts[-3:]})
            return None
        body = Path(tmp).read_text(encoding="utf-8", errors="ignore")
        hits = []
        for m in re.finditer(r"liclick\('(\d+)','([^']*)'\).*?<strong>([^<]*)</strong>(.*?)</span>", body, re.S):
            rest = re.sub(r"&nbsp;|\s+", " ", m.group(4))
            isin = re.search(r"\b(IN[A-Z0-9]{10})\b", rest)
            hits.append({"scrip": m.group(1), "name": html.unescape(m.group(2)), "symbol": m.group(3).strip(),
                         "isin": isin.group(1) if isin else ""})
        exact = [h for h in hits if h["symbol"].upper() == text.upper()]
        return (exact or hits or [None])[0]

    def bse(self, scrip: str, years: int = 15, cutoff: Optional[dt.date] = None) -> int:
        n0 = len(self.rows)
        fy = self.fy_end
        ar = self.get_json("bse_annual_reports", "%s/AnnualReport_New/w?scripcode=%s" % (BSE_API, scrip))
        for r in (ar or {}).get("Table", []) if isinstance(ar, dict) else []:
            year = str(r.get("Year") or "").strip()
            self.rows.append(row("BSE", "annual_report", r.get("Fld_AuthoriseDate") or r.get("REV_DT") or "",
                                 "Annual Report %s" % year, "Annual Report", r.get("PDFDownload") or "", fy,
                                 period="FY%s" % year if year.isdigit() else ""))
        end = cutoff or dt.date.today()
        today = dt.date.today()
        for y in range(end.year - years, end.year + 1):
            # BSE returns nothing when the end date lies in the future, so cap it at today.
            to_date = min(dt.date(y, 12, 31), today).strftime("%Y%m%d")
            page, seen = 1, 0
            while True:
                url = ("%s/AnnSubCategoryGetData/w?pageno=%d&strCat=-1&strPrevDate=%d0101&strScrip=%s&strSearch=P"
                       "&strToDate=%s&strType=C&subcategory=-1" % (BSE_API, page, y, scrip, to_date))
                data = self.get_json("bse_announcements_%d_p%d" % (y, page), url)
                table = (data or {}).get("Table") or [] if isinstance(data, dict) else []
                for r in table:
                    att = (r.get("ATTACHMENTNAME") or "").strip()
                    title = r.get("HEADLINE") or r.get("NEWSSUB") or ""
                    cat = "%s / %s" % (r.get("CATEGORYNAME") or "", r.get("SUBCATNAME") or "")
                    dtype = classify(cat, title, r.get("NEWSSUB") or "", att)
                    self.rows.append(row("BSE", dtype, r.get("NEWS_DT") or r.get("DT_TM"), title, cat,
                                         BSE_ATTACH % ("AttachHis", att) if att else "", fy,
                                         alt_url=BSE_ATTACH % ("AttachLive", att) if att else "",
                                         size=str(r.get("Fld_Attachsize") or ""), ref=r.get("NEWSID") or ""))
                seen += len(table)
                total = int(((data or {}).get("Table1") or [{}])[0].get("ROWCNT") or 0) if isinstance(data, dict) else 0
                if not table or seen >= total or page >= 60:
                    break
                page += 1
        return len(self.rows) - n0

    # --- Company IR site ------------------------------------------------------------------------------------
    def ir(self, start_urls: Iterable[str], max_pages: int = 60, extra_hosts: Iterable[str] = ()) -> int:
        n0 = len(self.rows)
        starts = list(start_urls)
        hosts = {urllib.parse.urlparse(u).netloc.lower() for u in starts} | {h.lower() for h in extra_hosts}
        base_domains = {".".join(h.split(".")[-2:]) for h in hosts}
        queue, seen_pages, seen_docs = list(starts), set(), set()
        while queue and len(seen_pages) < max_pages:
            page = queue.pop(0)
            if page in seen_pages:
                continue
            seen_pages.add(page)
            tmp = str(self.dir / ".work" / "page.html")
            Path(tmp).parent.mkdir(parents=True, exist_ok=True)
            try:
                nf.fetch(page, tmp, expect="any", retries=2, timeout=45)
            except nf.FetchError as exc:
                self.failures.append({"label": "ir_page", "url": page, "status": exc.status, "attempts": exc.attempts[-2:]})
                continue
            finally:
                time.sleep(self.sleep)
            if nf.sniff(tmp) != "html":
                continue
            for href, text in extract_links(Path(tmp).read_text(encoding="utf-8", errors="ignore"), page):
                host = urllib.parse.urlparse(href).netloc.lower()
                if ".".join(host.split(".")[-2:]) not in base_domains:
                    continue
                if DOC_EXT_RE.search(urllib.parse.urlparse(href).path):
                    if href not in seen_docs:
                        seen_docs.add(href)
                        name = urllib.parse.unquote(href.rsplit("/", 1)[-1])
                        dtype = classify(text, name)
                        self.rows.append(row("IR", dtype, guess_date(text + " " + name), text or name, "IR site", href, self.fy_end))
                elif host in hosts and re.search(r"investor|financial|result|report|share|governance|disclosure|"
                                                 r"filing|presentation|transcript|earnings|annual|quarter", href, re.I):
                    if href not in seen_pages and href not in queue:
                        queue.append(href)
        self.endpoints.append({"label": "ir_crawl", "url": ", ".join(starts), "ok": True, "pages": len(seen_pages),
                               "documents": len(seen_docs)})
        return len(self.rows) - n0

    # --- Internet Archive -----------------------------------------------------------------------------------
    def wayback(self, prefix: str, limit: int = 20000) -> int:
        n0 = len(self.rows)
        try:
            caps = nf.cdx_prefix(prefix, self.work, mimetype=None, limit=limit)
        except nf.FetchError as exc:
            self.failures.append({"label": "wayback_cdx", "url": prefix, "status": exc.status, "attempts": exc.attempts[-3:]})
            return 0
        self.endpoints.append({"label": "wayback_cdx", "url": prefix, "ok": True, "captures": len(caps)})
        for c in caps:
            path = urllib.parse.urlparse(c["url"]).path
            if not DOC_EXT_RE.search(path) and "pdf" not in (c.get("mimetype") or ""):
                continue
            name = urllib.parse.unquote(path.rsplit("/", 1)[-1])
            dtype = classify(name.replace("_", " ").replace("-", " "))
            ts = c.get("timestamp", "")
            d = guess_date(name)                     # the capture time is not the document date
            period = infer_period(dtype, d, urllib.parse.unquote(path), self.fy_end)
            self.rows.append(row("WAYBACK", dtype, d, name, "Internet Archive capture (first captured %s)" % ts[:8],
                                 c["capture_url"], self.fy_end, alt_url=c["url"], size=c.get("length") or "",
                                 ref=ts, period=period))
        return len(self.rows) - n0

    # --- Output ---------------------------------------------------------------------------------------------
    def write(self) -> Path:
        path = self.dir / "exchange_index.csv"
        existing = []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                existing = list(csv.DictReader(f))
        merged, seen = [], set()
        for r in self.rows + existing:            # newest indexing wins
            key = (r.get("source"), r.get("url") or r.get("title"), r.get("date"), r.get("ref"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
        merged.sort(key=lambda r: (r.get("date") or "", r.get("source") or ""), reverse=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=INDEX_COLUMNS, extrasaction="ignore")
            w.writeheader()
            w.writerows(merged)
        summary = {"indexed_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                   "rows": len(merged),
                   "by_source_type": dict(Counter("%s/%s" % (r["source"], r["doc_type"]) for r in merged)),
                   "by_type_year": dict(Counter("%s/%s" % (r["doc_type"], (r.get("date") or "")[:4]) for r in merged
                                                if r["doc_type"] not in NOISE_TYPES)),
                   "endpoints": self.endpoints, "failures": self.failures}
        (self.run / "corpus").mkdir(exist_ok=True)
        (self.run / "corpus" / "index_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                                                encoding="utf-8")
        return path


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def extract_links(page_html: str, base: str):
    p = _LinkParser()
    try:
        p.feed(page_html)
    except Exception:  # noqa: BLE001 - malformed HTML still yields the links parsed so far
        pass
    out = []
    for href, text in p.links:
        href = (href or "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        out.append((urllib.parse.urljoin(base, href), text))
    return out


def guess_date(text: str) -> Optional[dt.date]:
    """A document date written in a title or file name (digit-bounded, so long numeric IDs are not misread)."""
    m = re.search(r"(?<!\d)(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)", text or "")
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(?<!\d)(0[1-9]|[12]\d|3[01])[-_.](0[1-9]|1[0-2])[-_.](20\d{2})(?!\d)", text or "")
    if m:
        try:
            return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def read_index(run_dir: Path) -> List[dict]:
    path = run_dir / "_cache" / "index" / "exchange_index.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def manifest_context(run_dir: Path):
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    fy_end = str(m.get("fiscal_year_end") or "03-31")
    try:
        month = int(fy_end.split("-")[0])
    except ValueError:
        month = 3
    cutoff = parse_date(m.get("research_cutoff") or "") or dt.date.today()
    return m, month, cutoff


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("all", "nse", "bse", "ir", "wayback", "show"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
        if name in ("all", "nse", "bse"):
            s.add_argument("--symbol", help="NSE symbol (and BSE lookup text)")
            s.add_argument("--years", type=int, default=15)
        if name in ("all", "bse"):
            s.add_argument("--scrip", help="BSE scrip code (looked up from --symbol if omitted)")
        if name in ("all", "ir"):
            s.add_argument("--ir" if name == "all" else "--url", action="append", default=[],
                           help="investor-relations page(s) to crawl")
            s.add_argument("--extra-host", action="append", default=[], help="also accept documents on this host")
            s.add_argument("--max-pages", type=int, default=60)
        if name in ("all", "wayback"):
            s.add_argument("--wayback-prefix" if name == "all" else "--prefix", action="append", default=[],
                           help="host/path prefix of an IR document folder")
        if name == "show":
            s.add_argument("--type")
            s.add_argument("--period")
            s.add_argument("--source")
            s.add_argument("--limit", type=int, default=60)
    a = ap.parse_args(argv)
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    m, fy_end, cutoff = manifest_context(run_dir)

    if a.cmd == "show":
        rows = [r for r in read_index(run_dir)
                if (not a.type or r["doc_type"] == a.type) and (not a.period or r["fiscal_period"] == a.period)
                and (not a.source or r["source"] == a.source.upper())]
        for r in rows[: a.limit]:
            print("%s | %-4s | %-21s | %-10s | %s | %s" % (r["date"], r["source"], r["doc_type"], r["fiscal_period"],
                                                           r["title"][:70], r["url"]))
        print("%d row(s)%s" % (len(rows), "" if len(rows) <= a.limit else " (showing %d)" % a.limit))
        return 0

    ix = Indexer(run_dir, fy_end)
    counts = {}
    symbol = getattr(a, "symbol", None) or m.get("ticker")
    if a.cmd in ("all", "nse") and symbol:
        counts["NSE"] = ix.nse(symbol, a.years, cutoff)
    if a.cmd in ("all", "bse"):
        scrip = getattr(a, "scrip", None)
        if not scrip and symbol:
            hit = ix.bse_lookup(symbol)
            if hit:
                scrip = hit["scrip"]
                print("BSE lookup: %s -> scrip %s (%s, %s)" % (symbol, scrip, hit["name"], hit["isin"] or "ISIN n/a"))
        if scrip:
            counts["BSE"] = ix.bse(scrip, a.years, cutoff)
        else:
            print("BSE: no scrip code (pass --scrip)", file=sys.stderr)
    urls = getattr(a, "ir", None) if a.cmd == "all" else getattr(a, "url", None)
    if a.cmd in ("all", "ir") and urls:
        counts["IR"] = ix.ir(urls, a.max_pages, a.extra_host)
    prefixes = getattr(a, "wayback_prefix", None) if a.cmd == "all" else getattr(a, "prefix", None)
    if a.cmd in ("all", "wayback"):
        for p in prefixes or []:
            counts["WAYBACK %s" % p] = ix.wayback(p)
    path = ix.write()
    total = sum(counts.values())
    print("indexed: %s -> %s" % (", ".join("%s %d" % kv for kv in counts.items()) or "nothing", path))
    for f in ix.failures:
        print("FAILED %s: %s (HTTP %s) %s" % (f["label"], f["url"], f.get("status"), (f.get("attempts") or [""])[-1][:120]),
              file=sys.stderr)
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
