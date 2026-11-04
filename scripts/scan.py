#!/usr/bin/env python3
"""Scan: every company in the warehouse on one table, by script, as known on a date. A lead list for triage, never a
decision.

  python3 scripts/scan.py run --date YYYY-MM-DD [--exchange NSE] [--top 50] [--min-traded-inr 10000000]

Writes research/funnel/scan/<date>_<exchange>.csv (every company and every measure) and SCAN_<date>_<exchange>.md (the
ranked table, the flags, and what the numbers can and cannot say). Outside runs/; it never touches the scoreboard.

Measures (each from the warehouse's facts as known on the date, consolidated where filed):
- **Value:** earnings yield (owners' profit ÷ market value) and book to price. Market value is the latest filed share
  count, adjusted for every split or bonus since its filing (NSE adjusts the previous close on an ex-date, so the ratio
  of a day's previous close to the day before's close is the factor), times the close on the date.
- **Quality and growth:** return on average equity; three-year revenue CAGR (interest income for lenders).
- **Price:** one-year return, the worst fall from a high within that year, and the median daily traded value over the
  last 60 sessions (a measure of whether a position could be built).
- **Forensic flags** (non-lenders): three-year operating cash flow below half of profit; receivables growing 20 points
  faster than revenue; debt above twice equity. For all: a loss; shares up more than 30 % in three years; values the
  warehouse rejected as filed.
- **Rank:** the mean percentile of earnings yield, return on equity and growth among the companies that have each. It
  orders the list; it does not say what to buy. Flags are listed, never netted off the rank.

Survivor-biased like everything built on the warehouse, and the facts are as filed: a number in a scan is a lead, and a
run opens the filing before it is cited.
"""

import argparse
import csv
import datetime as dt
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import base_rates as br  # noqa: E402
import research_lib as rl  # noqa: E402
import warehouse as wh  # noqa: E402

OUT = rl.ROOT / "research" / "funnel" / "scan"
METRICS = ("revenue", "interest_income", "pat", "pat_attributable", "total_equity", "cfo", "trade_receivables",
           "total_debt", "shares_outstanding", "advances")
COLUMNS = ["symbol", "close", "market_cap_cr", "earnings_yield", "book_to_price", "roe", "growth_3y", "return_1y",
           "max_drawdown_1y", "median_traded_inr_60d", "latest_fy", "lender", "rank_score", "flags"]


def prices(con, exchange: str, day: str) -> Dict[str, List[tuple]]:
    start = (dt.date.fromisoformat(day) - dt.timedelta(days=400)).isoformat()
    out: Dict[str, List[tuple]] = {}
    for sym, d, close, prev, value in con.execute("""SELECT symbol, date, close, prev_close, value_inr FROM prices
                                                    WHERE exchange = ? AND date > ? AND date <= ? ORDER BY symbol, date""",
                                                 (exchange, start, day)):
        out.setdefault(sym, []).append((d, close, prev, value))
    return out


def action_factor(series: List[tuple], since: str) -> float:
    """The product of split and bonus factors on the days after `since`: a day whose previous close differs from the
    close before it by more than 2 % was an ex-date."""
    f = 1.0
    for (d0, c0, _p0, _v0), (d1, _c1, p1, _v1) in zip(series, series[1:]):
        if d1 > since and c0 and p1 and abs(c0 / p1 - 1) > 0.02:
            f *= c0 / p1
    return f


def price_measures(series: List[tuple], day: str) -> dict:
    closes = [(d, c) for d, c, _p, _v in series if c]
    if not closes or closes[-1][0] != day:
        return {}
    year_ago = (dt.date.fromisoformat(day) - dt.timedelta(days=365)).isoformat()
    window = [(d, c) for d, c in closes if d >= year_ago]
    adj = adjusted(series)
    start = next((c for d, c in adj if d >= year_ago), None)
    peak, dd = 0.0, 0.0
    for d, c in adj:
        if d >= year_ago:
            peak = max(peak, c)
            dd = min(dd, c / peak - 1)
    traded = [v for _d, _c, _p, v in series[-60:] if v]
    return {"close": closes[-1][1], "return_1y": (adj[-1][1] / start - 1) if start and len(window) > 200 else None,
            "max_drawdown_1y": dd if len(window) > 200 else None,
            "median_traded_inr_60d": statistics.median(traded) if traded else None}


def adjusted(series: List[tuple]) -> List[tuple]:
    """Closes on today's share basis: every close before an ex-date divided by that day's factor."""
    out, f = [], 1.0
    for i in range(len(series) - 1, -1, -1):
        d, c, p, _v = series[i]
        out.append((d, c / f if c else c))
        if i > 0:
            c0 = series[i - 1][1]
            if c0 and p and abs(c0 / p - 1) > 0.02:
                f *= c0 / p
    return list(reversed(out))


def latest_known(con, ticker: str, metric: str, day: str) -> Optional[tuple]:
    row = con.execute("""SELECT value, known_at, period FROM facts WHERE ticker = ? AND metric = ? AND known_at <= ?
                         ORDER BY CASE basis WHEN 'consolidated' THEN 0 ELSE 1 END, period DESC, known_at DESC LIMIT 1""",
                      (ticker, metric, day)).fetchone()
    return row


def issuance(con, sym: str, y: int, day: str, years: int = 3) -> Optional[float]:
    """Growth in the share count over `years`, net of splits and bonuses, which issue nothing. None when the daily prices
    do not cover the span, so a bonus is never mistaken for dilution."""
    def at(fy):
        return con.execute("""SELECT value, known_at FROM facts WHERE ticker = ? AND metric = 'shares_outstanding' AND period = ?
                              AND known_at <= ? ORDER BY CASE basis WHEN 'consolidated' THEN 0 ELSE 1 END, known_at DESC
                              LIMIT 1""", (sym, "FY%d" % fy, day)).fetchone()
    end, start = at(y), at(y - years)
    if not end or not start or not start[0]:
        return None
    series = con.execute("""SELECT date, close, prev_close, value_inr FROM prices WHERE symbol = ? AND date >= ? AND date <= ?
                            ORDER BY date""", (sym, start[1], end[1])).fetchall()
    first = con.execute("SELECT MIN(date) FROM prices WHERE symbol = ?", (sym,)).fetchone()[0]
    if not series or not first or first > start[1]:
        return None
    return end[0] / (start[0] * action_factor(series, start[1])) - 1


def cagr(s: Dict[int, float], y: int, n: int) -> Optional[float]:
    a, b = s.get(y - n), s.get(y)
    return (b / a) ** (1.0 / n) - 1 if a and b and a > 0 and b > 0 else None


def company(con, sym: str, day: str, data: Dict[str, Dict[str, Dict[int, float]]], series: List[tuple], rejected: set) -> dict:
    s = {m: data[m].get(sym, {}) for m in METRICS}
    owners = s["pat_attributable"] or s["pat"]
    row = {"symbol": sym, "flags": []}
    row.update(price_measures(series, day))
    if not owners:
        return row
    y = max(owners)
    lender = bool(s["advances"] or s["interest_income"])
    row.update(latest_fy="FY%d" % y, lender=lender)
    sh = latest_known(con, sym, "shares_outstanding", day)
    if sh and row.get("close"):
        row["market_cap_cr"] = sh[0] * action_factor(series, sh[1]) * row["close"] / 1e7
    mc = row.get("market_cap_cr")
    if mc:
        row["earnings_yield"] = owners[y] / mc
        if s["total_equity"].get(y):
            row["book_to_price"] = s["total_equity"][y] / mc
    eq = s["total_equity"]
    if eq.get(y) and eq.get(y - 1):
        row["roe"] = owners[y] / ((eq[y] + eq[y - 1]) / 2)
    row["growth_3y"] = cagr(s["interest_income"] if lender else s["revenue"], y, 3)
    if owners[y] < 0:
        row["flags"].append("loss")
    growth = issuance(con, sym, y, day)
    if growth is not None and growth > 0.3:
        row["flags"].append("shares +%d%% in 3 years, after splits and bonuses" % round(growth * 100))
    if not lender:
        cf = [s["cfo"].get(t) for t in (y, y - 1, y - 2)]
        pt = [s["pat"].get(t) for t in (y, y - 1, y - 2)]
        if all(v is not None for v in cf + pt) and sum(pt) > 0 and sum(cf) < 0.5 * sum(pt):
            row["flags"].append("cash flow below half of profit (3y)")
        rec, rev = s["trade_receivables"], s["revenue"]
        if all(rec.get(t) and rev.get(t) for t in (y, y - 1)) and rec[y] / rec[y - 1] - rev[y] / rev[y - 1] > 0.20:
            row["flags"].append("receivables outgrowing revenue")
        if s["total_debt"].get(y) and eq.get(y) and eq[y] > 0 and s["total_debt"][y] > 2 * eq[y]:
            row["flags"].append("debt above twice equity")
    if sym in rejected:
        row["flags"].append("values rejected as filed")
    return row


def percentile(values: Dict[str, float]) -> Dict[str, float]:
    order = sorted(values, key=lambda k: values[k])
    n = len(order)
    return {k: (i + 0.5) / n for i, k in enumerate(order)} if n else {}


def scan(con, day: str, exchange: str = "NSE", min_traded: float = 0.0) -> List[dict]:
    universe = wh.universe(con, day, exchange)
    data = {m: br.series(con, m, day) for m in METRICS}
    px = prices(con, exchange, day)
    rejected = {t for (t,) in con.execute("SELECT DISTINCT ticker FROM rejected")}
    rows = [company(con, sym, day, data, px.get(sym, []), rejected) for sym in universe]
    if min_traded:
        rows = [r for r in rows if (r.get("median_traded_inr_60d") or 0) >= min_traded]
    ranks = [percentile({r["symbol"]: r[k] for r in rows if r.get(k) is not None}) for k in ("earnings_yield", "roe", "growth_3y")]
    for r in rows:
        got = [p[r["symbol"]] for p in ranks if r["symbol"] in p]
        r["rank_score"] = sum(got) / len(got) if len(got) >= 2 else None
    return sorted(rows, key=lambda r: (r.get("rank_score") is None, -(r.get("rank_score") or 0)))


def fmt(v, kind="") -> str:
    if v is None or v == "":
        return ""
    if kind == "pct":
        return "%.1f%%" % (v * 100)
    if isinstance(v, float):
        return "%.2f" % v if abs(v) < 1000 else "{:,.0f}".format(v)
    return str(v)


def write(rows: List[dict], day: str, exchange: str, top: int, out: Path = None) -> Path:
    out = out or OUT
    out.mkdir(parents=True, exist_ok=True)
    stem = "%s_%s" % (day, exchange)
    with (out / ("%s.csv" % stem)).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, flags="; ".join(r.get("flags") or [])))
    ranked = [r for r in rows if r.get("rank_score") is not None]
    with_facts = [r for r in rows if r.get("latest_fy")]
    flags: Dict[str, int] = {}
    for r in rows:
        for fl in r.get("flags") or []:
            key = fl.split(" +")[0]
            flags[key] = flags.get(key, 0) + 1
    lines = ["# Scan — %s, %s" % (exchange, day), "",
             "%d companies traded; %d have results in the warehouse; %d have enough to rank. A lead list for triage "
             "(`python3 scripts/triage.py prepare SYMBOL --date %s`), never a decision." % (len(rows), len(with_facts), len(ranked), day),
             "", "| # | Symbol | Rank | Earnings yield | ROE | Growth 3y | Book/price | Market cap (cr) | 1y return | Worst fall 1y | Flags |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(ranked[:top], 1):
        lines.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            i, r["symbol"], fmt(r["rank_score"]), fmt(r.get("earnings_yield"), "pct"), fmt(r.get("roe"), "pct"),
            fmt(r.get("growth_3y"), "pct"), fmt(r.get("book_to_price")), fmt(r.get("market_cap_cr")),
            fmt(r.get("return_1y"), "pct"), fmt(r.get("max_drawdown_1y"), "pct"), "; ".join(r.get("flags") or [])))
    lines += ["", "**Flags across the universe:** %s." % (", ".join("%s %d" % kv for kv in sorted(flags.items())) or "none"), "",
              "**What these numbers can and cannot say.** %s Facts are as filed, from exchange XBRL; a lender's growth is its "
              "interest income and it carries no cash-flow or leverage flags, because those tests do not fit a lender. A "
              "market value uses the last filed share count, adjusted for splits and bonuses seen in the daily prices since." % br.CAVEAT]
    (out / ("SCAN_%s.md" % stem)).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / ("SCAN_%s.md" % stem)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--date", required=True)
    r.add_argument("--exchange", default="NSE")
    r.add_argument("--top", type=int, default=50)
    r.add_argument("--min-traded-inr", type=float, default=0.0)
    a = ap.parse_args(argv)
    con = wh.connect()
    rows = scan(con, a.date, a.exchange, a.min_traded_inr)
    if not rows:
        print("no prices for %s on %s in the warehouse: python3 scripts/warehouse.py ingest-prices first" % (a.exchange, a.date),
              file=sys.stderr)
        return 1
    print(write(rows, a.date, a.exchange, a.top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
