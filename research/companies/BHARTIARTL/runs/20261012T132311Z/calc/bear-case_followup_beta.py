"""Regression betas of BHARTIARTL.NS vs NIFTY 50 (Yahoo chart API, adjusted closes), data truncated at the 2026-10-12 cutoff.
Run: python3 calc/bear-case_followup_beta.py > calc/bear-case_followup_beta.out"""
import json, glob, datetime
CUT = "2026-10-12"
def load(pattern):
    f = sorted(glob.glob("_cache/bear-case/" + pattern))[-1]
    d = json.load(open(f))["chart"]["result"][0]
    adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose") or d["indicators"]["quote"][0]["close"]
    out = {}
    for t, a in zip(d["timestamp"], adj):
        if a is None: continue
        day = (datetime.datetime.utcfromtimestamp(t) + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
        if day <= CUT: out[day] = a
    return out
def beta(s, m, start, label):
    keys = sorted(k for k in s if k in m and k >= start)
    rs = [s[b] / s[a] - 1 for a, b in zip(keys, keys[1:])]
    rm = [m[b] / m[a] - 1 for a, b in zip(keys, keys[1:])]
    n = len(rs); ms = sum(rs) / n; mm = sum(rm) / n
    cov = sum((x - ms) * (y - mm) for x, y in zip(rs, rm)) / (n - 1)
    var = sum((y - mm) ** 2 for y in rm) / (n - 1)
    vs = sum((x - ms) ** 2 for x in rs) / (n - 1)
    b = cov / var; r2 = cov ** 2 / (var * vs)
    blume = 0.67 * b + 0.33
    print(f"{label}: n={n} beta={b:.2f} R2={r2:.2f} Blume-adjusted={blume:.2f}")
    return b
wk_s = load("*Yahoo-weekly-BHARTIARTL-NS-10y.json"); wk_m = load("*Yahoo-weekly-NIFTY-50-10y.json")
mo_s = load("*Yahoo-monthly-price-history-BHARTIARTL-NS.json"); mo_m = load("*Yahoo-monthly-NIFTY-50-index.json")
beta(wk_s, wk_m, "2024-10-12", "Weekly 2y")
beta(wk_s, wk_m, "2021-10-12", "Weekly 5y")
beta(wk_s, wk_m, "2016-10-12", "Weekly 10y")
beta(mo_s, mo_m, "2021-10-01", "Monthly 5y")
beta(mo_s, mo_m, "2016-10-01", "Monthly 10y")
# Cost-of-equity sensitivity using the draft's structure Ke = rf - 1.87% + beta x 7.08%
for rf in (0.0739, 0.069):
    for b in (0.87, 0.75, 0.65):
        print(f"rf {rf:.2%} beta {b:.2f} -> Ke {rf - 0.0187 + b * 0.0708:.2%}")
