#!/usr/bin/env python3
"""Price, TSR, drawdown, beta and ADTV analysis for BHARTIARTL (valuation specialist).

Inputs (downloaded with scripts/fetch_source.py; see source_retrievals.csv):
  _cache/valuation/*BHARTIARTL-NS*.json   Yahoo chart API, daily, split- and rights-adjusted close; adjclose = dividend-adjusted
  _cache/valuation/*CRSLDX*.json          Nifty 500 price index
  _cache/valuation/*NSEI*.json            Nifty 50 price index
Outputs: calc/valuation_price_history.json and workpaper CSVs.
Run: python3 -I calc/valuation_price_history.py RUN_DIR
"""
import csv, datetime as dt, glob, json, math, sys
from pathlib import Path

RUN = Path(sys.argv[1])
CUTOFF = dt.date(2026, 10, 12)


def load(pattern):
    f = sorted(glob.glob(str(RUN / "_cache/valuation" / pattern)))[-1]
    r = json.load(open(f))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    adj = r["indicators"].get("adjclose", [{}])[0].get("adjclose")
    out = []
    for i, t in enumerate(r["timestamp"]):
        c = q["close"][i]
        if c is None:
            continue
        d = (dt.datetime.utcfromtimestamp(t) + dt.timedelta(hours=5, minutes=30)).date()
        if d > CUTOFF:
            continue
        out.append({"date": d, "close": c, "adj": adj[i] if adj else c, "vol": q["volume"][i] or 0,
                    "high": q["high"][i], "low": q["low"][i]})
    # de-duplicate dates (keep last)
    dd = {}
    for row in out:
        dd[row["date"]] = row
    return [dd[k] for k in sorted(dd)], f


stk, f_stk = load("*BHARTIARTL-NS*.json")
n500, f_n500 = load("*CRSLDX*.json")
n50, f_n50 = load("*NSEI*.json")


def on_or_before(series, d):
    best = None
    for r in series:
        if r["date"] <= d:
            best = r
        else:
            break
    return best


def cagr(a, b, years):
    return (b / a) ** (1 / years) - 1


last = stk[-1]
res = {"inputs": {"stock": f_stk, "nifty500": f_n500, "nifty50": f_n50}, "last": {"date": str(last["date"]), "close": last["close"]}}

# --- fiscal-year-end closes (last trading day on or before 31-Mar) and calendar year-end
fy = []
for y in range(2003, 2027):
    r = on_or_before(stk, dt.date(y, 3, 31))
    i5 = on_or_before(n500, dt.date(y, 3, 31))
    fy.append({"fy": "FY%d" % y, "date": str(r["date"]), "close_adj_split_rights": round(r["close"], 2), "tr_index": round(r["adj"], 4),
               "nifty500": round(i5["close"], 2) if i5 and i5["date"].year == y else None})
# yearly high/low per FY
for row in fy:
    y = int(row["fy"][2:])
    seg = [r for r in stk if dt.date(y - 1, 4, 1) <= r["date"] <= dt.date(y, 3, 31)]
    row["fy_high"] = round(max(r["close"] for r in seg), 2) if seg else None
    row["fy_low"] = round(min(r["close"] for r in seg), 2) if seg else None
res["fy_end"] = fy

# --- TSR windows ending at the last date
tsr = {}
for yrs in (1, 3, 5, 10, 15, 20):
    start = dt.date(last["date"].year - yrs, last["date"].month, last["date"].day)
    s = on_or_before(stk, start)
    i0 = on_or_before(n500, start)
    i1 = n500[-1]
    j0 = on_or_before(n50, start)
    tsr["%dy" % yrs] = {
        "start": str(s["date"]),
        "stock_tsr_cagr": cagr(s["adj"], last["adj"], yrs),
        "stock_price_cagr": cagr(s["close"], last["close"], yrs),
        "nifty500_price_cagr": cagr(i0["close"], i1["close"], yrs) if i0 else None,
        "nifty50_price_cagr": cagr(j0["close"], n50[-1]["close"], yrs) if j0 else None,
    }
res["tsr"] = tsr

# --- drawdowns on the price (split/rights adjusted close) series
def drawdowns(series, key="close", min_depth=0.25):
    eps, peak, peak_d, trough, trough_d, in_dd = [], series[0][key], series[0]["date"], None, None, False
    for r in series:
        v = r[key]
        if v >= peak:
            if in_dd and trough is not None:
                eps.append({"peak_date": str(peak_d), "peak": peak, "trough_date": str(trough_d), "trough": trough,
                            "depth": trough / peak - 1, "recovery_date": str(r["date"])})
            peak, peak_d, trough, trough_d, in_dd = v, r["date"], None, None, False
        else:
            in_dd = True
            if trough is None or v < trough:
                trough, trough_d = v, r["date"]
    if in_dd and trough is not None:
        eps.append({"peak_date": str(peak_d), "peak": peak, "trough_date": str(trough_d), "trough": trough,
                    "depth": trough / peak - 1, "recovery_date": None, "current_from_peak": series[-1][key] / peak - 1})
    return [e for e in eps if e["depth"] <= -min_depth]

res["drawdowns_price_ge25pct"] = drawdowns(stk, "close")
res["drawdowns_tr_ge25pct"] = drawdowns(stk, "adj")
res["drawdowns_nifty500_ge25pct"] = drawdowns(n500, "close")
for e in res["drawdowns_price_ge25pct"]:
    p, t = dt.date.fromisoformat(e["peak_date"]), dt.date.fromisoformat(e["trough_date"])
    e["months_peak_to_trough"] = round((t - p).days / 30.44, 1)
    if e["recovery_date"]:
        e["months_trough_to_recovery"] = round((dt.date.fromisoformat(e["recovery_date"]) - t).days / 30.44, 1)
# all-time high and current drawdown
ath = max(stk, key=lambda r: r["close"])
res["all_time_high"] = {"date": str(ath["date"]), "close": ath["close"], "current_vs_ath": last["close"] / ath["close"] - 1}
w52 = [r for r in stk if r["date"] > last["date"] - dt.timedelta(days=365)]
res["52w"] = {"high_close": max(r["close"] for r in w52), "low_close": min(r["close"] for r in w52),
              "high_intraday": max(r["high"] for r in w52 if r["high"]), "low_intraday": min(r["low"] for r in w52 if r["low"])}

# --- beta: weekly (Friday or last day of ISO week) log returns vs indices
def weekly(series):
    wk = {}
    for r in series:
        k = r["date"].isocalendar()[:2]
        wk[k] = r
    return {k: v for k, v in wk.items()}

def beta(stock, index, years, freq="weekly"):
    end = last["date"]; start = end - dt.timedelta(days=int(365.25 * years))
    if freq == "weekly":
        a, b = weekly([r for r in stock if r["date"] >= start]), weekly([r for r in index if r["date"] >= start])
    else:
        a = {}; b = {}
        for r in stock:
            if r["date"] >= start: a[(r["date"].year, r["date"].month)] = r
        for r in index:
            if r["date"] >= start: b[(r["date"].year, r["date"].month)] = r
    keys = sorted(set(a) & set(b))
    xs, ys = [], []
    for k0, k1 in zip(keys, keys[1:]):
        ys.append(math.log(a[k1]["adj"] / a[k0]["adj"])); xs.append(math.log(b[k1]["close"] / b[k0]["close"]))
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    vx = sum((x - mx) ** 2 for x in xs) / (n - 1); vy = sum((y - my) ** 2 for y in ys) / (n - 1)
    bt = cov / vx
    return {"beta": bt, "r2": cov * cov / (vx * vy), "n": n, "start": str(start), "end": str(end), "freq": freq,
            "adjusted_beta_blume": 0.67 * bt + 0.33}

res["beta"] = {
    "nifty50_weekly_2y": beta(stk, n50, 2), "nifty50_weekly_3y": beta(stk, n50, 3), "nifty50_weekly_5y": beta(stk, n50, 5),
    "nifty500_weekly_2y": beta(stk, n500, 2), "nifty500_weekly_5y": beta(stk, n500, 5),
    "nifty50_monthly_5y": beta(stk, n50, 5, "monthly"), "nifty500_monthly_5y": beta(stk, n500, 5, "monthly"),
    "nifty50_weekly_10y": beta(stk, n50, 10),
}

# --- ADTV approximation (close x volume) over the last 90 / 60 / 20 trading days
for nwin in (20, 60, 90, 250):
    seg = stk[-nwin:]
    tv = [r["close"] * r["vol"] for r in seg]
    res["adtv_%dd_inr_crore_approx" % nwin] = sum(tv) / len(tv) / 1e7
    res["adtv_%dd_window" % nwin] = [str(seg[0]["date"]), str(seg[-1]["date"])]
    res["median_dtv_%dd_inr_crore_approx" % nwin] = sorted(tv)[len(tv) // 2] / 1e7

# --- annualized volatility (daily log returns, 1y and 5y)
def vol(series, days):
    seg = series[-days:]
    rs = [math.log(b["adj"] / a["adj"]) for a, b in zip(seg, seg[1:])]
    m = sum(rs) / len(rs)
    return math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1) * 250)
res["volatility"] = {"stock_1y": vol(stk, 250), "stock_5y": vol(stk, 1250), "nifty500_1y": vol(n500, 250), "nifty500_5y": vol(n500, 1250)}

# workpaper CSV (FY-end)
wp = RUN / "specialists/valuation_workpapers"
wp.mkdir(parents=True, exist_ok=True)
with open(wp / "price_fy_end.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(fy[0].keys()), quoting=csv.QUOTE_ALL)
    w.writeheader(); w.writerows(fy)
# monthly closes for reference
with open(wp / "price_monthly.csv", "w", newline="") as fh:
    w = csv.writer(fh, quoting=csv.QUOTE_ALL); w.writerow(["month_end_date", "close_adj_split_rights", "tr_index", "volume"])
    mm = {}
    for r in stk:
        mm[(r["date"].year, r["date"].month)] = r
    for k in sorted(mm):
        r = mm[k]; w.writerow([r["date"], round(r["close"], 2), round(r["adj"], 4), r["vol"]])

def clean(o):
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (dt.date,)):
        return str(o)
    return o
(RUN / "calc/valuation_price_history.json").write_text(json.dumps(clean(res), indent=2))
print(json.dumps(clean({k: v for k, v in res.items() if k not in ("fy_end",)}), indent=1))
for r in fy:
    print(r)
