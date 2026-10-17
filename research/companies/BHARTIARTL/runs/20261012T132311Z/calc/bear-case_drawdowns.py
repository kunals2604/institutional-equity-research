"""Timestamps converted to IST (bars start 00:00 IST). Drawdown analysis of BHARTIARTL.NS monthly closes (Yahoo chart API, adjusted close).
Input: _cache/bear-case/*Yahoo-monthly-price-history*.json. Output: calc/bear-case_drawdowns.out"""
import json, glob, datetime, sys
f = sorted(glob.glob("_cache/bear-case/*Yahoo-monthly-price-history-BHARTIARTL-NS.json"))[-1]
d = json.load(open(f))["chart"]["result"][0]
ts = d["timestamp"]; q = d["indicators"]["quote"][0]["close"]
adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose", q)
rows = [((datetime.datetime.utcfromtimestamp(t) + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m"), c, a) for t, c, a in zip(ts, q, adj) if c is not None]
print("first", rows[0], "last", rows[-1], "n", len(rows))
# yearly closes (last month of each calendar year) for context
peak = None; peak_m = None; maxdd = 0; episodes = []
cur_peak = (rows[0][0], rows[0][2]); trough = cur_peak
for m, c, a in rows:
    if a > cur_peak[1]:
        if trough[1] / cur_peak[1] - 1 < -0.30:
            episodes.append((cur_peak, trough, (m, a)))
        cur_peak = (m, a); trough = (m, a)
    elif a < trough[1]:
        trough = (m, a)
if trough[1] / cur_peak[1] - 1 < -0.30:
    episodes.append((cur_peak, trough, None))
print("\nDrawdowns >30% (monthly adjusted close):")
for p, t, r in episodes:
    print(f"peak {p[0]} {p[1]:.1f} -> trough {t[0]} {t[1]:.1f} = {100*(t[1]/p[1]-1):.1f}% ; recovered to new high {r[0] if r else 'not yet'}")
print("\nMarch closes (fiscal year-end), unadjusted and adjusted:")
for m, c, a in rows:
    if m.endswith("-03") or m == rows[-1][0]:
        print(m, round(c, 1), round(a, 1))
# price CAGR 2007-12 peak to 2016 etc
def get(m):
    for r in rows:
        if r[0] == m: return r
for a_, b_ in [("2007-12","2016-12"),("2007-12","2019-12"),("2016-06","2026-09"),("2008-03","2018-03")]:
    x, y = get(a_), get(b_)
    if x and y:
        yrs = (int(b_[:4]) + int(b_[5:])/12) - (int(a_[:4]) + int(a_[5:])/12)
        print(f"{a_}->{b_}: adj {x[2]:.1f}->{y[2]:.1f} total {100*(y[2]/x[2]-1):.1f}% CAGR {100*((y[2]/x[2])**(1/yrs)-1):.1f}%")
