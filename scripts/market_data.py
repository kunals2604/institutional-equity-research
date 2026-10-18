#!/usr/bin/env python3
"""Exchange-verified market data from NSE bhavcopy files (tier 1): price, liquidity, long price history.

  python3 scripts/market_data.py close   --run RUN_DIR --symbol BHARTIARTL --date 2026-10-12 [--out calc/x.json]
  python3 scripts/market_data.py adtv    --run RUN_DIR --symbol BHARTIARTL --end 2026-10-12 [--days 90] [--out ...]
  python3 scripts/market_data.py history --run RUN_DIR --symbol BHARTIARTL --end 2026-10-12 [--years 20]
                                         [--frequency monthly|weekly] [--out calc/valuation_price_history.json]

Bhavcopy formats (verified 2026-10-17): `sec_bhavdata_full_DDMMYYYY.csv` (2020 onward, with delivery data);
`cmDDMONYYYYbhav.csv.zip` (historical, 2012 and earlier through mid-2024); `BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`
(UDiFF, from July 2024). The right format is chosen by date, with the others as fallbacks. A non-trading day returns
404, and the tool steps back to the previous trading day.

`history` samples the last trading day of each month (or week), adjusts for face-value splits and bonus issues
using NSE's corporate-action feed (rights issues are listed but not adjusted: say so where they matter), and reports
CAGR, total return with dividends, maximum drawdown with its dates, and recovery. Month-end sampling understates
intramonth extremes: use `--frequency weekly` where drawdown precision matters.

Every exchange file used is listed in the output with its URL and SHA-256; files are cached in
RUN_DIR/_cache/market/ and reused. Exit: 0 ok, 1 no data, 2 usage.
"""

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

ARCH = "https://nsearchives.nseindia.com"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
UDIFF_START = dt.date(2024, 7, 8)
SEC_FULL_START = dt.date(2020, 1, 1)


def urls_for(d: dt.date) -> List[Tuple[str, str]]:
    sec = ("sec_full", "%s/products/content/sec_bhavdata_full_%s.csv" % (ARCH, d.strftime("%d%m%Y")))
    hist = ("cm_hist", "%s/content/historical/EQUITIES/%d/%s/cm%02d%s%dbhav.csv.zip" % (ARCH, d.year, MONTHS[d.month - 1],
                                                                                       d.day, MONTHS[d.month - 1], d.year))
    udiff = ("udiff", "%s/content/cm/BhavCopy_NSE_CM_0_0_0_%s_F_0000.csv.zip" % (ARCH, d.strftime("%Y%m%d")))
    if d >= SEC_FULL_START:
        return [sec, udiff, hist] if d >= UDIFF_START else [sec, hist]
    return [hist]


def _f(x) -> Optional[float]:
    try:
        return float(str(x).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_bhavcopy(fmt: str, data: bytes, symbol: str, series=("EQ", "BE", "BZ", "SM", "ST")) -> Optional[dict]:
    """The symbol's row from one bhavcopy file, normalized. Prefers the EQ series."""
    if fmt in ("cm_hist", "udiff"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            text = zf.read(name).decode("utf-8", errors="ignore")
    else:
        text = data.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for r in reader:
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        sym = r.get("SYMBOL") or r.get("TckrSymb")
        ser = r.get("SERIES") or r.get("SctySrs")
        if sym == symbol and ser in series:
            rows.append((series.index(ser), ser, r))
    if not rows:
        return None
    _, ser, r = sorted(rows, key=lambda t: t[0])[0]
    if fmt == "sec_full":
        turnover = _f(r.get("TURNOVER_LACS"))
        return {"series": ser, "close": _f(r.get("CLOSE_PRICE")), "open": _f(r.get("OPEN_PRICE")), "high": _f(r.get("HIGH_PRICE")),
                "low": _f(r.get("LOW_PRICE")), "prev_close": _f(r.get("PREV_CLOSE")), "volume": _f(r.get("TTL_TRD_QNTY")),
                "traded_value_inr": turnover * 1e5 if turnover is not None else None, "trades": _f(r.get("NO_OF_TRADES")),
                "delivery_qty": _f(r.get("DELIV_QTY")), "delivery_pct": _f(r.get("DELIV_PER")), "date": r.get("DATE1")}
    if fmt == "cm_hist":
        return {"series": ser, "close": _f(r.get("CLOSE")), "open": _f(r.get("OPEN")), "high": _f(r.get("HIGH")),
                "low": _f(r.get("LOW")), "prev_close": _f(r.get("PREVCLOSE")), "volume": _f(r.get("TOTTRDQTY")),
                "traded_value_inr": _f(r.get("TOTTRDVAL")), "trades": _f(r.get("TOTALTRADES")), "delivery_qty": None,
                "delivery_pct": None, "date": r.get("TIMESTAMP"), "isin": r.get("ISIN")}
    return {"series": ser, "close": _f(r.get("ClsPric")), "open": _f(r.get("OpnPric")), "high": _f(r.get("HghPric")),
            "low": _f(r.get("LwPric")), "prev_close": _f(r.get("PrvsClsgPric")), "volume": _f(r.get("TtlTradgVol")),
            "traded_value_inr": _f(r.get("TtlTrfVal")), "trades": _f(r.get("TtlNbOfTxsExctd")), "delivery_qty": None,
            "delivery_pct": None, "date": r.get("TradDt"), "isin": r.get("ISIN")}


class Market:
    def __init__(self, run_dir: Path):
        self.cache = run_dir / "_cache" / "market"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.work = str(self.cache / ".work")
        self.sources: List[dict] = []
        self.misses = 0

    def file_for(self, d: dt.date) -> Optional[Tuple[str, str, bytes]]:
        """(format, url, bytes) of the bhavcopy for date d, or None if the market was closed / no file exists."""
        for fmt, url in urls_for(d):
            local = self.cache / url.rsplit("/", 1)[-1]
            miss = local.with_suffix(local.suffix + ".missing")
            if local.exists() and local.stat().st_size > 0:
                return fmt, url, local.read_bytes()
            if miss.exists():
                continue
            try:
                nf.fetch(url, str(local), expect="zip" if url.endswith(".zip") else "csv", retries=2, timeout=60)
                return fmt, url, local.read_bytes()
            except nf.FetchError as exc:
                if exc.status == 404:
                    miss.write_text("404\n")
                self.misses += 1
        return None

    def quote(self, symbol: str, d: dt.date, back: int = 10) -> Optional[dict]:
        for k in range(back + 1):
            day = d - dt.timedelta(days=k)
            if day.weekday() >= 5:
                continue
            got = self.file_for(day)
            if not got:
                continue
            fmt, url, data = got
            row = parse_bhavcopy(fmt, data, symbol)
            if row is None:
                continue
            row.update({"trade_date": day.isoformat(), "requested_date": d.isoformat(), "format": fmt, "url": url,
                        "sha256": hashlib.sha256(data).hexdigest()})
            self.sources.append({"date": day.isoformat(), "url": url, "sha256": row["sha256"]})
            return row
        return None


def corporate_actions(run_dir: Path, symbol: str) -> List[dict]:
    """Splits, bonuses, dividends and rights from NSE's corporate-action feed (raw copy saved by exchange_index.py)."""
    raw = run_dir / "_cache" / "index" / "raw" / "nse_corporate_actions.json"
    data = None
    if raw.exists():
        try:
            data = json.loads(raw.read_text(encoding="utf-8"))
        except ValueError:
            data = None
    if data is None:
        try:
            data = nf.get_json("https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol=%s" % symbol,
                               str(run_dir / "_cache" / "market" / ".work"))
        except nf.FetchError:
            data = []
    out = []
    for r in data or []:
        subj = r.get("subject") or ""
        try:
            ex = dt.datetime.strptime(r.get("exDate", ""), "%d-%b-%Y").date()
        except ValueError:
            continue
        ev = {"ex_date": ex.isoformat(), "subject": subj, "factor": 1.0, "dividend": 0.0, "kind": "other"}
        split = re.search(r"(?:split|sub-?division).*?rs\.?\s*(\d+(?:\.\d+)?).*?rs\.?\s*(\d+(?:\.\d+)?)", subj, re.I)
        bonus = re.search(r"bonus\s*(\d+)\s*:\s*(\d+)", subj, re.I)
        div = re.findall(r"(?:dividend|div)[^0-9]*?(?:rs\.?|re\.?)\s*(\d+(?:\.\d+)?)", subj, re.I)
        if split and float(split.group(2)) > 0:
            ev.update(kind="split", factor=float(split.group(1)) / float(split.group(2)))
        elif bonus:
            a, b = float(bonus.group(1)), float(bonus.group(2))
            ev.update(kind="bonus", factor=(a + b) / b)
        elif div:
            ev.update(kind="dividend", dividend=sum(float(x) for x in div))
        elif re.search(r"rights", subj, re.I):
            ev.update(kind="rights")
        out.append(ev)
    return sorted(out, key=lambda e: e["ex_date"])


def sample_dates(end: dt.date, years: int, frequency: str) -> List[dt.date]:
    start = dt.date(end.year - years, end.month, 1)
    out = []
    if frequency == "weekly":
        d = end
        while d >= start:
            out.append(d)
            d -= dt.timedelta(days=7)
        return sorted(out)
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        last = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
        out.append(min(last, end))
        y, m = y + (m == 12), m % 12 + 1
    return out


def history(market: Market, run_dir: Path, symbol: str, end: dt.date, years: int, frequency: str) -> dict:
    events = corporate_actions(run_dir, symbol)
    points = []
    for d in sample_dates(end, years, frequency):
        q = market.quote(symbol, d, back=8)
        if q and q.get("close"):
            points.append({"date": q["trade_date"], "close": q["close"], "volume": q.get("volume"),
                           "traded_value_inr": q.get("traded_value_inr")})
    if not points:
        return {"error": "no exchange prices found"}
    # Adjust earlier closes for splits and bonuses that went ex after them (so the series is comparable today).
    for p in points:
        f = 1.0
        for e in events:
            if e["kind"] in ("split", "bonus") and p["date"] < e["ex_date"]:
                f *= e["factor"]
        p["adj_factor"] = f
        p["adj_close"] = p["close"] / f
    peak, peak_date, mdd, mdd_peak, mdd_trough = -1.0, None, 0.0, None, None
    for p in points:
        if p["adj_close"] > peak:
            peak, peak_date = p["adj_close"], p["date"]
        dd = p["adj_close"] / peak - 1
        if dd < mdd:
            mdd, mdd_peak, mdd_trough = dd, peak_date, p["date"]
    recovery = None
    if mdd_trough:
        target = next(p["adj_close"] for p in points if p["date"] == mdd_peak)
        recovery = next((p["date"] for p in points if p["date"] > mdd_trough and p["adj_close"] >= target), None)
    first, last = points[0], points[-1]
    span = (dt.date.fromisoformat(last["date"]) - dt.date.fromisoformat(first["date"])).days / 365.25
    cagr = (last["adj_close"] / first["adj_close"]) ** (1 / span) - 1 if span > 0 else None
    divs = [e for e in events if e["kind"] == "dividend" and first["date"] < e["ex_date"] <= last["date"]]
    # Total return: reinvest each dividend at the sampled close on or before its ex-date (adjusted per-share basis).
    units = 1.0
    for e in divs:
        px = max((p for p in points if p["date"] <= e["ex_date"]), key=lambda p: p["date"], default=None)
        if px:
            f = next((p["adj_factor"] for p in points if p["date"] >= e["ex_date"]), 1.0)
            units *= 1 + (e["dividend"] / f) / px["adj_close"]
    tr = (last["adj_close"] * units / first["adj_close"]) ** (1 / span) - 1 if span > 0 else None
    annual = {}
    for p in points:
        annual[p["date"][:4]] = p["adj_close"]
    return {"symbol": symbol, "frequency": frequency, "points": points, "annual_last_close": annual,
            "start": first["date"], "end": last["date"], "years": round(span, 2), "price_cagr": cagr,
            "total_return_cagr_with_dividends": tr, "max_drawdown": mdd, "max_drawdown_peak": mdd_peak,
            "max_drawdown_trough": mdd_trough, "recovered_on": recovery, "corporate_actions": events,
            "notes": ["Splits and bonuses adjusted from NSE's corporate-action feed; rights issues are not adjusted.",
                      "Sampled at %s closes: intraperiod highs and lows are not captured." % frequency]}


def adtv(market: Market, symbol: str, end: dt.date, days: int) -> dict:
    rows, d, scanned = [], end, 0
    while len(rows) < days and scanned < days * 2 + 30:
        if d.weekday() < 5:
            got = market.file_for(d)
            if got:
                fmt, url, data = got
                r = parse_bhavcopy(fmt, data, symbol)
                if r and r.get("traded_value_inr") is not None:
                    r.update({"trade_date": d.isoformat(), "url": url})
                    rows.append(r)
                    market.sources.append({"date": d.isoformat(), "url": url, "sha256": hashlib.sha256(data).hexdigest()})
        d -= dt.timedelta(days=1)
        scanned += 1
    if not rows:
        return {"error": "no exchange data"}
    vals = sorted(r["traded_value_inr"] for r in rows)
    deliv = [r["delivery_pct"] for r in rows if r.get("delivery_pct") is not None]
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return {"symbol": symbol, "end": rows[0]["trade_date"], "start": rows[-1]["trade_date"], "trading_days": n,
            "adtv_inr_mean": sum(vals) / n, "adtv_inr_median": median,
            "avg_volume_shares": sum(r["volume"] or 0 for r in rows) / n,
            "avg_delivery_pct": (sum(deliv) / len(deliv)) if deliv else None,
            "note": "Mean and median daily traded value on NSE (EQ series) over the window; BSE volume is not included."}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("close", "adtv", "history"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
        s.add_argument("--symbol", required=True)
        s.add_argument("--out")
        if name == "close":
            s.add_argument("--date", required=True)
        else:
            s.add_argument("--end", required=True)
        if name == "adtv":
            s.add_argument("--days", type=int, default=90)
        if name == "history":
            s.add_argument("--years", type=int, default=20)
            s.add_argument("--frequency", choices=["monthly", "weekly"], default="monthly")
    a = ap.parse_args(argv)
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    mk = Market(run_dir)
    sym = a.symbol.upper()
    if a.cmd == "close":
        res = mk.quote(sym, dt.date.fromisoformat(a.date)) or {"error": "no exchange quote within 10 days of %s" % a.date}
    elif a.cmd == "adtv":
        res = adtv(mk, sym, dt.date.fromisoformat(a.end), a.days)
    else:
        res = history(mk, run_dir, sym, dt.date.fromisoformat(a.end), a.years, a.frequency)
    res["exchange_files"] = mk.sources
    res["source"] = "NSE bhavcopy archives (tier 1), %s" % ARCH
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    if "error" in res:
        print("ERROR: %s" % res["error"])
        return 1
    show = {k: v for k, v in res.items() if k not in ("points", "exchange_files", "corporate_actions", "annual_last_close")}
    print(json.dumps(show, indent=2, default=str))
    if a.cmd == "history":
        print("annual closes (split/bonus adjusted): %s" % ", ".join("%s %.1f" % kv for kv in sorted(res["annual_last_close"].items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
