#!/usr/bin/env python3
"""The warehouse: what the framework knows across companies and across time, so a run no longer starts from zero.

  python3 scripts/warehouse.py init
  python3 scripts/warehouse.py ingest-file PATH --exchange NSE|BSE          # one bhavcopy, any of the three formats
  python3 scripts/warehouse.py ingest-prices --exchange NSE|BSE --from YYYY-MM-DD --to YYYY-MM-DD [--sleep 0.5]
  python3 scripts/warehouse.py crawl-xbrl --symbols FILE|universe:YYYY-MM-DD [--sleep 1.0]  # annual results, resumable
  python3 scripts/warehouse.py promote RUN_DIR                              # a finished run's verified facts
  python3 scripts/warehouse.py facts RUN_DIR                                # what a run may read, as of its cutoff
  python3 scripts/warehouse.py universe --date YYYY-MM-DD [--exchange NSE]
  python3 scripts/warehouse.py knowledge                                    # company files and sector knowledge
  python3 scripts/warehouse.py archive-cache RUN_DIR
  python3 scripts/warehouse.py status

research/warehouse/eqr.sqlite (stdlib sqlite3, gitignored: everything in it can be fetched again). Three rules:

- **Point in time.** Every fact carries `known_at`, the day the market could have known it (a filing's broadcast date, a
  source's date). A run reads only what was known at its cutoff, so a replay cannot see the future through the data.
- **Facts, never judgments.** Only facts are promoted: FACT claims of tier 1 to 3, with a metric and a value, from a run
  that finished and whose verification passed. Conclusions, scores and verdicts never enter, so a specialist that reads
  what the warehouse holds still works independently.
- **Agents never read the database.** `facts` writes a run's corpus/facts/ from it; the engine denies research/warehouse/.

Survivorship: daily bhavcopies are a point-in-time universe, including companies that later disappeared. The database
cannot say whether a vanished symbol merged or failed, and machine-readable results start around 2018, so reference classes
built on it are labelled survivor-biased (scripts/base_rates.py).
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import time
import urllib.parse
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

HOME = rl.ROOT / "research" / "warehouse"
DB = HOME / "eqr.sqlite"
EQUITY_SERIES = ("EQ", "BE", "BZ", "SM", "ST")        # NSE; BSE's equity groups are kept as they come
BSE_URL = "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_%s_F_0000.CSV"
PROMOTE_TIERS = ("1", "2", "3")
SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (exchange TEXT, symbol TEXT, isin TEXT, name TEXT, series TEXT, jurisdiction TEXT,
    first_seen TEXT, last_seen TEXT, kind TEXT, PRIMARY KEY (exchange, symbol));
CREATE TABLE IF NOT EXISTS prices (exchange TEXT, symbol TEXT, date TEXT, series TEXT, open REAL, high REAL, low REAL,
    close REAL, prev_close REAL, volume REAL, value_inr REAL, trades REAL, delivery_pct REAL, source_url TEXT,
    source_sha256 TEXT, PRIMARY KEY (exchange, symbol, date));
CREATE TABLE IF NOT EXISTS ingested (exchange TEXT, date TEXT, format TEXT, source TEXT, sha256 TEXT, rows INTEGER,
    status TEXT, at TEXT, PRIMARY KEY (exchange, date));
CREATE TABLE IF NOT EXISTS facts (ticker TEXT, metric TEXT, period TEXT, basis TEXT, value REAL, unit TEXT, known_at TEXT,
    source TEXT, locator TEXT, tier TEXT, origin TEXT, PRIMARY KEY (ticker, metric, period, basis, known_at, origin));
CREATE TABLE IF NOT EXISTS crawled (symbol TEXT PRIMARY KEY, status TEXT, rows INTEGER, at TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS rejected (ticker TEXT, metric TEXT, period TEXT, basis TEXT, value REAL, source TEXT, reason TEXT,
    at TEXT);
CREATE INDEX IF NOT EXISTS prices_by_date ON prices (date);
"""


def connect(db: Path = None) -> sqlite3.Connection:
    db = db or DB
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(SCHEMA)
    return con


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ------------------------------------------------------------------------------------------------------------------
# prices: every security of a day, from one bhavcopy
# ------------------------------------------------------------------------------------------------------------------

def _text(data: bytes) -> str:
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            data = zf.read(name)
    return data.decode("utf-8", errors="ignore")


def _f(x) -> Optional[float]:
    try:
        return float(str(x).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def _iso(text: str) -> str:
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_day(data: bytes, exchange: str) -> List[dict]:
    """Every equity row of one bhavcopy: NSE's full and historical formats and the UDiFF format NSE and BSE both use.
    The format is read from the header, never assumed from the file name."""
    reader = csv.DictReader(io.StringIO(_text(data)))
    out = []
    for raw in reader:
        r = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        if "TckrSymb" in r:                                            # UDiFF (NSE from July 2024, BSE)
            if r.get("FinInstrmTp") not in ("STK", "") or (exchange == "NSE" and r.get("SctySrs") not in EQUITY_SERIES):
                continue
            row = {"symbol": r["TckrSymb"], "series": r.get("SctySrs"), "isin": r.get("ISIN"), "name": r.get("FinInstrmNm"),
                   "date": _iso(r.get("TradDt", "")), "open": _f(r.get("OpnPric")), "high": _f(r.get("HghPric")),
                   "low": _f(r.get("LwPric")), "close": _f(r.get("ClsPric")), "prev_close": _f(r.get("PrvsClsgPric")),
                   "volume": _f(r.get("TtlTradgVol")), "value_inr": _f(r.get("TtlTrfVal")), "trades": _f(r.get("TtlNbOfTxsExctd")),
                   "delivery_pct": None}
        elif "CLOSE_PRICE" in r:                                       # NSE sec_bhavdata_full (2020 onward)
            if r.get("SERIES") not in EQUITY_SERIES:
                continue
            lacs = _f(r.get("TURNOVER_LACS"))
            row = {"symbol": r["SYMBOL"], "series": r["SERIES"], "isin": None, "name": None, "date": _iso(r.get("DATE1", "")),
                   "open": _f(r.get("OPEN_PRICE")), "high": _f(r.get("HIGH_PRICE")), "low": _f(r.get("LOW_PRICE")),
                   "close": _f(r.get("CLOSE_PRICE")), "prev_close": _f(r.get("PREV_CLOSE")), "volume": _f(r.get("TTL_TRD_QNTY")),
                   "value_inr": lacs * 1e5 if lacs is not None else None, "trades": _f(r.get("NO_OF_TRADES")),
                   "delivery_pct": _f(r.get("DELIV_PER"))}
        elif "TOTTRDQTY" in r:                                         # NSE historical cm..bhav
            if r.get("SERIES") not in EQUITY_SERIES:
                continue
            row = {"symbol": r["SYMBOL"], "series": r["SERIES"], "isin": r.get("ISIN"), "name": None, "date": _iso(r.get("TIMESTAMP", "")),
                   "open": _f(r.get("OPEN")), "high": _f(r.get("HIGH")), "low": _f(r.get("LOW")), "close": _f(r.get("CLOSE")),
                   "prev_close": _f(r.get("PREVCLOSE")), "volume": _f(r.get("TOTTRDQTY")), "value_inr": _f(r.get("TOTTRDVAL")),
                   "trades": _f(r.get("TOTALTRADES")), "delivery_pct": None}
        else:
            raise ValueError("not a bhavcopy this tool knows: %s" % ", ".join(list(r)[:6]))
        if row["date"] and row["close"] is not None:
            out.append(row)
    return out


def isin_kind(isin: Optional[str]) -> str:
    """What an Indian ISIN says the security is. Both exchanges list ETFs, and BSE's equity file also carries government
    bonds, gold bonds, InvIT units and rights entitlements (measured on 30 October 2026), so a company universe needs it."""
    i = (isin or "").strip().upper()
    if len(i) != 12 or not i.startswith("IN"):
        return "unknown"
    if i[2] == "F":
        return "fund"
    if i[2] == "9":
        return "partly_paid"
    if i[2].isdigit():
        return "government"
    if i[2] != "E":
        return "other"
    return {"01": "equity", "20": "rights", "23": "trust_units", "07": "debt", "08": "debt", "09": "debt"}.get(i[7:9], "other")


def ingest_day(con: sqlite3.Connection, exchange: str, data: bytes, source: str) -> int:
    rows = parse_day(data, exchange)
    if not rows:
        return 0
    sha = hashlib.sha256(data).hexdigest()
    day = rows[0]["date"]
    for r in rows:
        con.execute("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exchange, r["symbol"], r["date"], r["series"], r["open"], r["high"], r["low"], r["close"], r["prev_close"],
                     r["volume"], r["value_inr"], r["trades"], r["delivery_pct"], source, sha))
        kind = isin_kind(r["isin"]) if r["isin"] else None
        con.execute("""INSERT INTO securities VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(exchange, symbol) DO UPDATE SET
                       isin = COALESCE(excluded.isin, securities.isin), name = COALESCE(excluded.name, securities.name),
                       kind = COALESCE(excluded.kind, securities.kind),
                       first_seen = MIN(securities.first_seen, excluded.first_seen), last_seen = MAX(securities.last_seen, excluded.last_seen)""",
                    (exchange, r["symbol"], r["isin"], r["name"], r["series"], "IN", r["date"], r["date"], kind))
    con.execute("INSERT OR REPLACE INTO ingested VALUES (?,?,?,?,?,?,?,?)", (exchange, day, "", source, sha, len(rows), "ok", now()))
    con.commit()
    return len(rows)


def nse_sources(day: dt.date) -> List[Tuple[str, str]]:
    import market_data
    return market_data.urls_for(day)


def fetch_day(exchange: str, day: dt.date, cache: Path) -> Optional[Tuple[str, bytes]]:
    """(url, bytes) of one day's file, from the cache when it is there. None on a holiday or a day with no file."""
    import netfetch as nf
    urls = [u for _, u in nse_sources(day)] if exchange == "NSE" else [BSE_URL % day.strftime("%Y%m%d")]
    for url in urls:
        local = cache / exchange / url.rsplit("/", 1)[-1]
        if local.exists() and local.stat().st_size:
            return url, local.read_bytes()
        local.parent.mkdir(parents=True, exist_ok=True)
        try:
            nf.fetch(url, str(local), expect="zip" if url.lower().endswith(".zip") else "csv", retries=2, timeout=60)
            return url, local.read_bytes()
        except nf.FetchError:
            continue
    return None


def ingest_range(con: sqlite3.Connection, exchange: str, start: dt.date, end: dt.date, sleep: float = 0.5,
                 fetch=fetch_day, log=print) -> Dict[str, int]:
    """Resumable: a day already ingested, or already known to have no file, is skipped."""
    done = {d for (d,) in con.execute("SELECT date FROM ingested WHERE exchange = ?", (exchange,))}
    counts = {"days": 0, "rows": 0, "no_file": 0, "skipped": 0}
    day = start
    while day <= end:
        if day.weekday() >= 5 or day.isoformat() in done:
            counts["skipped"] += day.weekday() < 5
            day += dt.timedelta(days=1)
            continue
        got = fetch(exchange, day, HOME / "_cache")
        if got is None:
            con.execute("INSERT OR REPLACE INTO ingested VALUES (?,?,?,?,?,?,?,?)", (exchange, day.isoformat(), "", "", "", 0, "no file", now()))
            con.commit()
            counts["no_file"] += 1
        else:
            counts["rows"] += ingest_day(con, exchange, got[1], got[0])
            counts["days"] += 1
            time.sleep(sleep)
        day += dt.timedelta(days=1)
    log("%s %s..%s: %d days, %d rows, %d without a file, %d already done" % (exchange, start, end, counts["days"], counts["rows"],
                                                                           counts["no_file"], counts["skipped"]))
    return counts


def universe(con: sqlite3.Connection, day: str, exchange: str = "NSE", kinds=("equity", None)) -> List[str]:
    """The companies whose shares traded on a day: a point-in-time universe, so a screen run as of a past date sees the
    companies that existed then, including those that later disappeared. A symbol whose ISIN was never seen (NSE's
    2020-2024 format has none) has no kind yet and is kept."""
    rows = con.execute("""SELECT p.symbol, s.kind FROM prices p LEFT JOIN securities s ON s.exchange = p.exchange AND s.symbol = p.symbol
                          WHERE p.exchange = ? AND p.date = ? ORDER BY p.symbol""", (exchange, day)).fetchall()
    return [sym for sym, kind in rows if kind in kinds]


# ------------------------------------------------------------------------------------------------------------------
# facts: results XBRL across companies, and the verified facts of finished runs
# ------------------------------------------------------------------------------------------------------------------

def add_fact(con: sqlite3.Connection, ticker: str, metric: str, period: str, basis: str, value: float, unit: str,
             known_at: str, source: str, locator: str, tier: str, origin: str) -> None:
    con.execute("INSERT OR REPLACE INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (ticker, metric, period, basis, value, unit, known_at, source, locator, tier, origin))


def results_index(work: Path, symbol: str, sleep: float = 0.4) -> None:
    """The three results indexes a crawl needs, written where xbrl_facts reads them. A run's Indexer makes about twelve
    requests per company; the crawl needs three."""
    import exchange_index as ei
    ix = ei.Indexer(work, sleep=sleep)
    sym = urllib.parse.quote(symbol)
    for kind in ("Annual", "Quarterly"):          # HDFC Bank's FY2021 results are listed only as a fourth quarter
        ix.get_json("nse_results_%s" % kind.lower(),
                    "%s/corporates-financial-results?index=equities&symbol=%s&period=%s" % (ei.NSE_API, sym, kind))
    ix.integrated(symbol)
    if ix.failures:
        raise RuntimeError("results index: %s" % "; ".join(f["label"] for f in ix.failures))


def fy_end_of(rows: List[dict]) -> int:
    """The company's fiscal year end, from its own annual results (Siemens files to September, Castrol to December)."""
    months = [d.month for d in (_date(r.get("toDate")) for r in rows) if d]
    return max(set(months), key=months.count) if months else 3


def _date(text) -> Optional[dt.date]:
    iso = _iso(str(text or "")[:11])
    return dt.date.fromisoformat(iso) if iso else None


def annual_filings(work: Path) -> List[dict]:
    """Every annual results filing in the indexes: url, kind, basis and the day it was broadcast."""
    import xbrl_facts as xf
    results = xf.load_results_index(work)
    year_end = [r for r in results if str(r.get("relatingTo", "")).lower() in ("annual", "fourth quarter")]
    fy = fy_end_of(year_end)
    out = []
    for r in results:
        rel = str(r.get("relatingTo", "")).lower()
        if (r.get("xbrl") or "").lower().endswith(".xml") and ("annual" in rel or "fourth" in rel or str(r.get("period", "")).lower() == "annual"):
            out.append({"url": r["xbrl"], "kind": "xbrl", "known_at": _iso(str(r.get("broadCastDate") or "")[:11]), "fy": fy,
                        "basis": "consolidated" if str(r.get("consolidated", "")).lower().startswith("consolidated") else "standalone"})
    for r in xf.load_integrated_index(work):
        qe = _date(r.get("qe_Date"))
        if (r.get("ixbrl") or "").lower().endswith(".html") and qe and qe.month == fy:
            out.append({"url": r["ixbrl"], "kind": "ixbrl", "known_at": _iso(str(r.get("broadcast_Date") or "")[:11]), "fy": fy,
                        "basis": "consolidated" if str(r.get("consolidated", "")).lower().startswith("consolidated") else "standalone"})
    seen, unique = set(), []
    for f in out:
        if f["url"] not in seen:
            seen.add(f["url"])
            unique.append(f)
    return unique


def instant_items() -> set:
    import xbrl_facts as xf
    keys = set(xf.INSTANT_MAP) | set(xf.IF_INSTANT) | set(xf.IF_BANK_INSTANT) | set(xf.IF_NBFC_INSTANT)
    for fmt in xf.LENDER_FORMATS.values():
        keys |= set(fmt["instant"])
    return keys - {"total_assets"}


def implausible(rows: List[dict]) -> List[Tuple[dict, str]]:
    """Values a filing cannot mean as filed, kept out of the facts and recorded in `rejected`: a balance-sheet amount
    larger than the same filing's total assets (Bajaj Finance's FY2026 Integrated Filing gives its non-controlling interest
    in rupees inside a table in lakhs). Anything subtler passes as filed; the warehouse holds leads, and a run opens the
    filing before it cites a number."""
    assets = {(r["period"], r["basis"]): abs(r["value"]) for r in rows if r["item"] == "total_assets"}
    items = instant_items()
    out = []
    for r in rows:
        ta = assets.get((r["period"], r["basis"]))
        if ta and r["item"] in items and r.get("unit") != "fraction" and abs(r["value"]) > ta * 1.01:
            out.append((r, "larger than total assets (%s)" % ta))
    return out


def share_count(path: str, kind: str) -> Optional[float]:
    """Equity shares outstanding at the filing's period end: paid-up equity capital over face value, both as filed
    (measured on HDFC Bank's FY2024 filing: 759.69 crore of capital at a face value of 1, 7.6 billion shares)."""
    import xbrl_facts as xf
    if kind == "xbrl":
        _contexts, facts, _text = xf.parse_xbrl(path)
        paid = [v for (n, c), v in facts.items() if n == "PaidUpValueOfEquityShareCapital" and c in ("OneD", "FourD", "OneI")]
        face = [v for (n, c), v in facts.items() if n == "FaceValueOfEquityShareCapital" and c in ("OneD", "FourD", "OneI")]
        scale = 1.0
    else:
        scale, _nature, statements = xf.parse_integrated(path)
        rows = [r for st in statements for r in st.get("rows", [])]
        paid = [r["values"][-1] for r in rows if r["label"] == "paid-up equity share capital" and r["values"][-1]]
        face = [r["values"][-1] for r in rows if r["label"] == "face value of equity share capital" and r["values"][-1]]
    if not paid or not face or not face[0]:
        return None
    return paid[0] * scale / face[0]


def crawl_symbol(con: sqlite3.Connection, symbol: str, index=results_index, download=None, pause: float = 0.3) -> int:
    """One company's annual results, each filing read on its own with the extraction a run uses (xbrl_facts), so a figure
    restated in a later filing is kept as a second version with its own known_at, never a silent overwrite. A filing
    with no broadcast date gives no point-in-time fact, so it is skipped."""
    import netfetch as nf
    import xbrl_facts as xf
    work = HOME / "_cache" / "symbols" / symbol
    work.mkdir(parents=True, exist_ok=True)
    index(work, symbol)
    fetch = download or (lambda url, dest: nf.fetch(url, str(dest), expect="xml" if url.lower().endswith(".xml") else "any",
                                                      retries=3, timeout=60))
    n = 0
    for f in annual_filings(work):
        if not f["known_at"]:
            continue
        local = work / "_cache" / "xbrl" / f["url"].rsplit("/", 1)[-1]
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            fetch(f["url"], local)
            time.sleep(pause)
        read = xf.rows_from_filing if f["kind"] == "xbrl" else xf.rows_from_integrated
        rows = read(str(local), f["url"], f["basis"], "INR crore", f["fy"], False)
        for r, reason in implausible(rows):
            con.execute("INSERT INTO rejected VALUES (?,?,?,?,?,?,?,?)", (symbol, r["item"], r["period"], r["basis"], r["value"],
                                                                         f["url"], reason, now()))
        bad = {id(r) for r, _ in implausible(rows)}
        for r in rows:
            if id(r) in bad or (r["item"].startswith("other:") and r["item"] not in xf.LENDER_RATIOS):
                continue
            add_fact(con, symbol, r["item"], r["period"], r["basis"], r["value"], r["unit"], f["known_at"], f["url"],
                     r["locator"], "1", "xbrl")
            n += 1
        years = sorted({r["period"] for r in rows if r["period"].startswith("FY")})
        shares = share_count(str(local), f["kind"]) if years else None
        if shares:
            add_fact(con, symbol, "shares_outstanding", years[-1], f["basis"], shares, "shares", f["known_at"], f["url"],
                     "paid-up equity share capital / face value", "1", "xbrl")
            n += 1
    con.commit()
    return n


def crawl(con: sqlite3.Connection, symbols: Iterable[str], sleep: float = 1.0, log=print, **kw) -> Dict[str, int]:
    """Resumable and throttled: a symbol crawled once is not crawled again, and one that failed is tried again on the
    next crawl. Three index requests and about two filings a year per company: for NSE's 2,700 equities, tens of thousands
    of requests, so expect days. Stop and resume at will."""
    done = {s for (s,) in con.execute("SELECT symbol FROM crawled WHERE status = 'ok'")}
    counts = {"symbols": 0, "facts": 0, "failed": 0, "skipped": 0}
    for sym in symbols:
        if sym in done:
            counts["skipped"] += 1
            continue
        try:
            n = crawl_symbol(con, sym, **kw)
            con.execute("INSERT OR REPLACE INTO crawled VALUES (?,?,?,?,?)", (sym, "ok", n, now(), ""))
            counts["symbols"] += 1
            counts["facts"] += n
        except Exception as exc:                       # one company's failure is recorded, never the end of the crawl
            con.execute("INSERT OR REPLACE INTO crawled VALUES (?,?,?,?,?)", (sym, "failed", 0, now(), repr(exc)[:300]))
            counts["failed"] += 1
        con.commit()
        time.sleep(sleep)
    log("crawl: %d symbols, %d facts, %d failed, %d already done" % (counts["symbols"], counts["facts"], counts["failed"], counts["skipped"]))
    return counts


def flagged_claims(run_dir: Path) -> set:
    """Every claim named in a verification finding of the run, open or waived, from the per-agent records (the run-level
    summary keeps no claim lists). A waived finding still names a number the scripts could not confirm."""
    out = set()
    for path in sorted((run_dir / "qc" / "verification").glob("*.json")):
        rec = rl.load_json(path)
        if not isinstance(rec, dict):
            continue
        for f in list(rec.get("tier_a") or []) + list((rec.get("tier_b") or {}).get("findings") or []):
            for c in f.get("claims") or []:
                out.update(rl.CLAIM_ID_RE.findall(str(c)))
    summary = run_dir / "qc" / "verification.json"
    for f in (rl.load_json(summary).get("run_findings") or []) if summary.exists() else []:
        for c in f.get("claims") or []:
            out.update(rl.CLAIM_ID_RE.findall(str(c)))
    return out


def key(ticker: str, juris: str = "IN") -> str:
    """The warehouse's name for a company: an Indian symbol as it is, any other with its jurisdiction (AAPL.US), so a
    US ticker never collides with an NSE symbol."""
    return ticker if (juris or "IN").upper() == "IN" else "%s.%s" % (ticker, juris.upper())


def ingest_edgar(con: sqlite3.Connection, ticker: str, facts: dict, fy_end_month: int) -> int:
    """A US company's annual facts from its EDGAR company facts, every filing's version with the date it was filed,
    and its share count from each filing's cover page (current at filing, so a later split is caught by the next one)."""
    import edgar
    k = key(ticker, "US")
    n = 0
    for r in edgar.annual_values(facts, fy_end_month):
        if r["item"] == "shares_outstanding":
            continue
        add_fact(con, k, r["item"], r["period"], r["basis"], r["value"], r["unit"], r["filed"], r["source_url_or_id"],
                 r["locator"], "1", "xbrl")
        n += 1
    cik = int(facts.get("cik") or 0)
    for unit_rows in ((facts.get("facts") or {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units") or {}).values():
        for r in unit_rows:
            if r.get("form") in edgar.ANNUAL_FORMS + ("10-Q", "10-Q/A"):
                period = "FY%d" % edgar.fiscal_year(dt.date.fromisoformat(r["end"]), fy_end_month)
                add_fact(con, k, "shares_outstanding", period, "consolidated", r["val"], "shares", r["filed"],
                         edgar.FILING_INDEX % (cik, r["accn"].replace("-", "")), "dei:EntityCommonStockSharesOutstanding (cover, %s, %s)" % (
                             r["end"], r["form"]), "1", "xbrl")
                n += 1
    con.commit()
    return n


def ingest_us_prices(con: sqlite3.Connection, ticker: str, rows: List[dict], source: str) -> int:
    """Daily closes of a US company under exchange `US`. The series is split-adjusted already, so no ex-date shows in it."""
    prev = None
    for r in rows:
        con.execute("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("US", ticker, r["date"], "", r["open"], r["high"], r["low"], r["close"], prev if prev else r["close"],
                     r["volume"], (r["volume"] or 0) * (r["close"] or 0), None, None, source, ""))
        prev = r["close"]
    if rows:
        con.execute("""INSERT INTO securities VALUES ('US',?,NULL,NULL,'',?,?,?,'equity') ON CONFLICT(exchange, symbol) DO UPDATE SET
                       first_seen = MIN(securities.first_seen, excluded.first_seen), last_seen = MAX(securities.last_seen, excluded.last_seen)""",
                    (ticker, "US", rows[0]["date"], rows[-1]["date"]))
    con.commit()
    return len(rows)


def promotable(run_dir: Path) -> List[dict]:
    """The facts of a finished run that may serve later runs: FACT claims of tier 1 to 3 with a metric, a number and a
    period, in a run that is complete, not a replay, and whose verification passed, and named in no verification finding.
    Every claim passed the script checks (number seen, source opened); the verifier re-opened a sample. Never a
    conclusion, a score or a verdict: those stay with the run, so later specialists still work independently."""
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    summary = run_dir / "qc" / "verification.json"
    if m.get("status") != "complete" or m.get("replay") or not summary.exists() or rl.load_json(summary).get("status") != "PASS":
        return []
    flagged = flagged_claims(run_dir)
    out = []
    for led in sorted((run_dir / "specialists").glob("*_ledger.csv")):
        with led.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                value = _f(r.get("value"))
                if ((r.get("tag") or "").strip().upper() == "FACT" and str(r.get("source_tier") or "").strip() in PROMOTE_TIERS
                        and (r.get("metric") or "").strip() and value is not None and (r.get("period") or "").strip()
                        and r.get("claim_id") not in flagged):
                    out.append(dict(r, _value=value, _known=_iso((r.get("source_date") or "").strip()[:11])))
    return out


def promote(con: sqlite3.Connection, run_dir: Path) -> int:
    """Adds the run's promotable facts and records what it did in RUN_DIR/qc/promoted.json, committed with the run."""
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    rows = promotable(run_dir)
    for r in rows:
        # known_at: the source's own date when it is a date and not after the cutoff, else the run's cutoff, the
        # latest day the run could have known it.
        known = r["_known"] if r["_known"] and r["_known"] <= m["research_cutoff"] else m["research_cutoff"]
        add_fact(con, key(m["ticker"], m.get("jurisdiction") or "IN"), r["metric"].strip(), r["period"].strip(), (r.get("basis") or "").strip() or "unstated",
                 r["_value"], r.get("unit", ""), known, r.get("source_url_or_id", ""), r.get("locator", ""),
                 str(r.get("source_tier")).strip(), "%s:%s" % (m["run_id"], r["claim_id"]))
    con.commit()
    if rows:
        why = ""
    elif m.get("status") != "complete" or m.get("replay"):
        why = "nothing promotable: the run is %s%s" % (m.get("status"), ", a replay" if m.get("replay") else "")
    else:
        why = "verification did not pass, or no unflagged tier 1-3 FACT has a metric, a value and a period"
    rl.write_json(run_dir / "qc" / "promoted.json", {"run_id": m["run_id"], "promoted": len(rows), "at": now(), "note": why,
                                                     "claims": sorted(r["claim_id"] for r in rows)})
    return len(rows)


def materialise(con: sqlite3.Connection, run_dir: Path) -> Path:
    """corpus/facts/: the facts this run may read, as known at its cutoff, and its prices. Shared facts, not conclusions;
    each keeps its own source, which is what a specialist cites, after opening it."""
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    juris = (m.get("jurisdiction") or "IN").upper()
    ticker, cutoff = key(m["ticker"], juris), m["research_cutoff"]
    out = run_dir / "corpus" / "facts"
    out.mkdir(parents=True, exist_ok=True)
    facts = con.execute("""SELECT metric, period, basis, value, unit, known_at, source, locator, tier, origin FROM facts
                           WHERE ticker = ? AND known_at <= ? ORDER BY metric, period, known_at""", (ticker, cutoff)).fetchall()
    exchange = "US" if juris == "US" else str(m.get("exchange") or "NSE").upper()
    prices = con.execute("""SELECT date, close, volume, value_inr FROM prices WHERE exchange = ? AND symbol = ? AND date <= ?
                            ORDER BY date""", (exchange, m["ticker"], cutoff)).fetchall()
    rejected = con.execute("SELECT metric, period, basis, value, source, reason FROM rejected WHERE ticker = ?", (ticker,)).fetchall()
    with (out / "facts.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "period", "basis", "value", "unit", "known_at", "source", "locator", "tier", "origin"])
        w.writerows(facts)
    with (out / "prices.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "volume", "value_inr"])
        w.writerows(prices)
    lines = ["# Facts known at %s for %s" % (cutoff, ticker), "",
             "From research/warehouse, built by `scripts/warehouse.py facts`: %d facts and %d daily %s closes, each known on or "
             "before the cutoff. They were gathered once, from exchange filings (origin `xbrl`, values as filed) and from the "
             "verified facts of earlier finished runs (origin `RUN:CLAIM`), never their conclusions. A figure restated later "
             "appears once per filing, each with its own known_at. Use them to find your way; cite the source each one names, "
             "after opening it, never this file." % (len(facts), len(prices), exchange), ""]
    if rejected:
        lines += ["Values the warehouse refused as filed (`warehouse.py` implausible()):", ""]
        lines += ["- %s %s %s: %s from %s (%s)" % r for r in rejected]
    (out / "FACTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def knowledge(con: sqlite3.Connection, root: Path = rl.ROOT) -> List[Path]:
    """A company file per company: every promoted fact, by metric and period, with its source. Sector knowledge joins
    the company files of each sector module a finished run selected. Facts only."""
    written = []
    companies = root / "research" / "companies"
    by_module: Dict[str, List[Tuple]] = {}
    for (ticker,) in con.execute("SELECT DISTINCT ticker FROM facts WHERE origin != 'xbrl'"):
        rows = con.execute("SELECT metric, period, basis, value, unit, known_at, source FROM facts WHERE ticker = ? AND origin != 'xbrl' "
                           "ORDER BY metric, period", (ticker,)).fetchall()
        path = companies / ticker / "file" / "facts.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["metric", "period", "basis", "value", "unit", "known_at", "source"])
            w.writerows(rows)
        written.append(path)
        pointer = companies / ticker / rl.LATEST_POINTER
        if pointer.exists():
            mods = rl.load_json(companies / ticker / "runs" / pointer.read_text(encoding="utf-8").strip() / rl.RUN_MANIFEST).get("sector_modules") or []
            for mod in mods:
                by_module.setdefault(mod, []).extend((ticker,) + tuple(r) for r in rows)
    for mod, rows in by_module.items():
        path = root / "research" / "knowledge" / "sectors" / mod / "facts.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ticker", "metric", "period", "basis", "value", "unit", "known_at", "source"])
            w.writerows(rows)
        written.append(path)
    return written


def archive_cache(run_dir: Path, root: Path = rl.ROOT) -> Path:
    """A run's download cache, zipped beside the transcripts with a checksum. The original stays: deleting it is the
    owner's call, after checking the archive."""
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    dest = root / "research" / "_archive" / "cache" / m["ticker"]
    dest.mkdir(parents=True, exist_ok=True)
    base = dest / m["run_id"]
    zpath = Path(shutil.make_archive(str(base), "zip", str(run_dir / "_cache")))
    (dest / ("%s.sha256" % m["run_id"])).write_text(hashlib.sha256(zpath.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    return zpath


def status(con: sqlite3.Connection) -> str:
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    return ("securities %d · price rows %d · days %s · facts %d (results XBRL %d, promoted %d) · symbols crawled %d" % (
        q("SELECT COUNT(*) FROM securities"), q("SELECT COUNT(*) FROM prices"),
        "%s..%s" % (q("SELECT MIN(date) FROM prices"), q("SELECT MAX(date) FROM prices")), q("SELECT COUNT(*) FROM facts"),
        q("SELECT COUNT(*) FROM facts WHERE origin = 'xbrl'"), q("SELECT COUNT(*) FROM facts WHERE origin != 'xbrl'"),
        q("SELECT COUNT(*) FROM crawled WHERE status = 'ok'")))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("knowledge")
    f = sub.add_parser("ingest-file")
    f.add_argument("path")
    f.add_argument("--exchange", choices=["NSE", "BSE"], required=True)
    p = sub.add_parser("ingest-prices")
    p.add_argument("--exchange", choices=["NSE", "BSE"], required=True)
    p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True)
    p.add_argument("--sleep", type=float, default=0.5)
    c = sub.add_parser("crawl-xbrl")
    c.add_argument("--symbols", required=True, help="a file of NSE symbols, or 'universe:YYYY-MM-DD' for every symbol that traded that day")
    c.add_argument("--sleep", type=float, default=1.0)
    e = sub.add_parser("crawl-edgar", help="US companies: a file of lines 'TICKER CIK [FY_END_MONTH]'")
    e.add_argument("--companies", required=True)
    e.add_argument("--sleep", type=float, default=0.5)
    up = sub.add_parser("ingest-us-prices", help="US daily closes (Nasdaq quote API, unofficial): a file of tickers")
    up.add_argument("--symbols", required=True)
    up.add_argument("--years", type=int, default=10)
    up.add_argument("--sleep", type=float, default=1.0)
    for name in ("promote", "facts", "archive-cache"):
        sub.add_parser(name).add_argument("run_dir")
    u = sub.add_parser("universe")
    u.add_argument("--date", required=True)
    u.add_argument("--exchange", default="NSE")
    a = ap.parse_args(argv)
    con = connect()
    if a.cmd == "ingest-file":
        print("%d rows" % ingest_day(con, a.exchange, Path(a.path).read_bytes(), str(a.path)))
    elif a.cmd == "ingest-prices":
        ingest_range(con, a.exchange, dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end), a.sleep)
    elif a.cmd == "crawl-xbrl":
        syms = (universe(con, a.symbols.split(":", 1)[1]) if a.symbols.startswith("universe:")
                else [s.strip() for s in Path(a.symbols).read_text(encoding="utf-8").split() if s.strip()])
        crawl(con, syms, a.sleep)
    elif a.cmd == "crawl-edgar":
        import edgar
        for line in Path(a.companies).read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) < 2 or line.startswith("#"):
                continue
            facts = edgar.get_json(edgar.FACTS % int(parts[1]), HOME / "_cache" / "edgar" / ("companyfacts_%010d.json" % int(parts[1])))
            print("%s: %d facts" % (parts[0], ingest_edgar(con, parts[0].upper(), facts, int(parts[2]) if len(parts) > 2 else 12)))
            time.sleep(a.sleep)
    elif a.cmd == "ingest-us-prices":
        import edgar
        for sym in Path(a.symbols).read_text(encoding="utf-8").split():
            rows = edgar.prices(sym, HOME / "_cache" / "edgar", a.years)
            print("%s: %d closes" % (sym.upper(), ingest_us_prices(con, sym.upper(), rows, "api.nasdaq.com (unofficial)")))
            time.sleep(a.sleep)
    elif a.cmd == "promote":
        print("%d facts promoted" % promote(con, Path(a.run_dir)))
    elif a.cmd == "facts":
        print(materialise(con, Path(a.run_dir)))
    elif a.cmd == "universe":
        print("\n".join(universe(con, a.date, a.exchange)))
    elif a.cmd == "knowledge":
        print("\n".join(map(str, knowledge(con))))
    elif a.cmd == "archive-cache":
        print(archive_cache(Path(a.run_dir)))
    elif a.cmd == "status":
        print(status(con))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
