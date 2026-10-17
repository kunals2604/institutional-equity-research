"""Moat quantified-advantage metrics for BHARTIARTL run 20261012T132311Z.
Inputs: calc/moat_roce_reported.csv, calc/moat_segment_inputs.csv, calc/moat_trai_wireless_share.csv,
plus constants below, each with its source claim in the moat ledger. Run: python3 calc/moat_metrics.py"""
import csv, os, statistics as st
D = os.path.dirname(os.path.abspath(__file__))
rd = lambda f: list(csv.DictReader(open(os.path.join(D, f))))
out = []
def emit(k, v, note=""):
    out.append((k, v, note)); print(f"{k},{v},{note}")

# ---------- 1. Return spread x duration (consolidated, company-reported pre-tax ROCE) ----------
TAX = 0.2517            # Indian statutory rate (new regime) used to convert pre-tax to post-tax (ESTIMATE)
WACC = {"low": 0.10, "central": 0.11, "high": 0.12}   # ESTIMATE range; valuation specialist owns the run WACC
roce = {r["period"]: float(r["roce_pct_reported"]) / 100 for r in rd("moat_roce_reported.csv")}
yrs10 = [f"FY{y}" for y in range(2017, 2027)]
yrs_all = sorted(roce)
for lab, w in WACC.items():
    hurdle = w / (1 - TAX)
    emit(f"pretax_hurdle_{lab}", round(hurdle * 100, 2), "WACC/(1-tax)")
    emit(f"years_roce_above_hurdle_last10_{lab}", sum(roce[y] > hurdle for y in yrs10), "FY2017-FY2026")
    emit(f"years_roce_above_hurdle_all_{lab}", sum(roce[y] > hurdle for y in yrs_all), f"{yrs_all[0]}-{yrs_all[-1]} n={len(yrs_all)}")
    sp = [roce[y] * (1 - TAX) - w for y in yrs10]
    emit(f"median_posttax_spread_last10_pp_{lab}", round(st.median(sp) * 100, 2), "ROCE*(1-t)-WACC")
emit("roce_median_last10_pct", round(st.median([roce[y] for y in yrs10]) * 100, 2))
emit("roce_min_last10_pct", round(min(roce[y] for y in yrs10) * 100, 2), min(yrs10, key=lambda y: roce[y]))
emit("roce_mean_FY2013_FY2016_pct", round(st.mean([roce[y] for y in ["FY2013","FY2014","FY2015","FY2016"]]) * 100, 2), "pre-Jio")
emit("roce_FY2026_posttax_pct", round(roce["FY2026"] * (1 - TAX) * 100, 2))

# ---------- 2. Segment returns (pre-tax segment result / average segment assets) ----------
seg = {}
for r in rd("moat_segment_inputs.csv"):
    seg.setdefault(r["segment"], {})[r["period"]] = r
def f(x): return float(x) if x not in ("", None) else None
for s in ["mobile_india", "africa", "airtel_business", "homes", "dth", "passive_infra"]:
    rows = seg[s]
    for p in sorted(rows):
        y = int(p[2:]); prev = rows.get(f"FY{y-1}")
        res, a1 = f(rows[p]["segment_result_inr_mn"]), f(rows[p]["segment_assets_close_inr_mn"])
        if res is None or prev is None or f(prev["segment_assets_close_inr_mn"]) is None: continue
        a0 = f(prev["segment_assets_close_inr_mn"]); l1 = f(rows[p]["segment_liab_close_inr_mn"]); l0 = f(prev["segment_liab_close_inr_mn"])
        r_ga = res / ((a0 + a1) / 2); r_na = res / (((a0 - l0) + (a1 - l1)) / 2)
        rev = f(rows[p]["revenue_inr_mn"]); dep = f(rows[p]["dep_amort_inr_mn"]); cap = f(rows[p]["capex_inr_mn"])
        emit(f"{s}_return_on_avg_gross_assets_{p}_pct", round(r_ga * 100, 2), "segment result/avg segment assets")
        emit(f"{s}_return_on_avg_net_assets_{p}_pct", round(r_na * 100, 2), "segment result/avg(assets-liabilities)")
        if s == "mobile_india":
            emit(f"{s}_ebitda_margin_proxy_{p}_pct", round((res + dep) / rev * 100, 2), "(result+D&A)/revenue")
            emit(f"{s}_capex_to_revenue_{p}_pct", round(cap / rev * 100, 2))
mi = seg["mobile_india"]
for a, b in [("FY2021", "FY2026"), ("FY2016", "FY2026")]:
    dres = f(mi[b]["segment_result_inr_mn"]) - f(mi[a]["segment_result_inr_mn"])
    dass = f(mi[b]["segment_assets_close_inr_mn"]) - f(mi[a]["segment_assets_close_inr_mn"])
    emit(f"mobile_india_incremental_pretax_return_{a}_{b}_pct", round(dres / dass * 100, 1) if dass else "n/a", "d(result)/d(segment assets)")
emit("mobile_india_revenue_cagr_FY2016_FY2026_pct", round(((f(mi["FY2026"]["revenue_inr_mn"]) / f(mi["FY2016"]["revenue_inr_mn"])) ** (1/10) - 1) * 100, 2))
emit("mobile_india_revenue_decline_FY2016_FY2019_pct", round((f(mi["FY2019"]["revenue_inr_mn"]) / f(mi["FY2016"]["revenue_inr_mn"]) - 1) * 100, 1))
emit("mobile_india_result_swing_FY2016_FY2019_inr_mn", f(mi["FY2019"]["segment_result_inr_mn"]) - f(mi["FY2016"]["segment_result_inr_mn"]))
ga = [st_ for st_ in []]

# ---------- 3. Margin stability (consolidated EBITDA margin as gross-margin proxy) ----------
em = {r["period"]: float(r["ebitda_margin_pct"]) for r in rd("moat_roce_reported.csv") if r["ebitda_margin_pct"]}
vals = [em[k] for k in sorted(em)]
emit("consol_ebitda_margin_stdev_pp", round(st.pstdev(vals), 2), f"{min(em)}-{max(em)} n={len(vals)} mixed IFRS/IndAS/IndAS116 bases")
emit("consol_ebitda_margin_min_pct", min(vals), min(em, key=em.get))
emit("consol_ebit_margin_min_pct", min(float(r["ebit_margin_pct"]) for r in rd("moat_roce_reported.csv")), "FY2019")
mim = [round((f(mi[p]["segment_result_inr_mn"]) + f(mi[p]["dep_amort_inr_mn"])) / f(mi[p]["revenue_inr_mn"]) * 100, 2) for p in sorted(mi) if f(mi[p]["revenue_inr_mn"])]
emit("mobile_india_ebitda_margin_proxy_stdev_pp", round(st.pstdev(mim), 2), "FY2016-FY2026 n=%d" % len(mim))
emit("mobile_india_ebitda_margin_proxy_min_pct", min(mim))

# ---------- 4. Pricing vs inflation ----------
ARPU = {"Q4FY2015": 198, "Q4FY2016": 194, "Q2FY2017": 188, "Q3FY2018": 123, "Q2FY2019": 100, "Q4FY2019": 123,
        "Q4FY2020": 154, "Q3FY2021": 166, "Q4FY2022": 178, "Q4FY2023": 193, "Q4FY2024": 209, "Q4FY2025": 245, "Q4FY2026": 257}
CPI = {2015: 146.790501522573, 2016: 154.054013105393, 2025: 233.063138328863}   # World Bank FP.CPI.TOTL (2010=100), calendar-year average
arpu_x = ARPU["Q4FY2026"] / ARPU["Q4FY2016"]
emit("arpu_change_Q4FY2016_Q4FY2026_pct", round((arpu_x - 1) * 100, 1))
emit("arpu_cagr_10y_pct", round((arpu_x ** 0.1 - 1) * 100, 2))
for a in (2015, 2016):
    cx = CPI[2025] / CPI[a]
    emit(f"cpi_change_CY{a}_CY2025_pct", round((cx - 1) * 100, 1))
    emit(f"real_arpu_change_vs_CY{a}_pct", round((arpu_x / cx - 1) * 100, 1))
emit("arpu_peak_to_trough_pct", round((ARPU["Q2FY2019"] / ARPU["Q4FY2016"] - 1) * 100, 1), "Q4FY2016->Q2FY2019")
emit("arpu_trough_to_Q4FY2026_pct", round((ARPU["Q4FY2026"] / ARPU["Q2FY2019"] - 1) * 100, 1))
JIO_ARPU = {"Q4FY2026": 214.0, "Q4FY2025": 206.2, "Q4FY2019": 126.2}
VIL_ARPU = {"Q4FY2026": 190}  # customer ARPU ex-M2M, tier-6 report of VIL release
emit("airtel_arpu_premium_vs_jio_Q4FY2026_pct", round((257 / 214.0 - 1) * 100, 1))
emit("airtel_arpu_premium_vs_jio_Q4FY2025_pct", round((245 / 206.2 - 1) * 100, 1))
emit("airtel_arpu_premium_vs_jio_Q4FY2019_pct", round((123 / 126.2 - 1) * 100, 1), "Jio figure tier-6")
emit("airtel_arpu_premium_vs_vil_Q4FY2026_pct", round((257 / 190 - 1) * 100, 1), "VIL figure tier-6")

# ---------- 5. Share stability ----------
sh = rd("moat_trai_wireless_share.csv")
comp = [float(r["bharti_share_pct"]) for r in sh if r["period"] <= "FY2025" and r["period"].startswith("FY")]
emit("bharti_wireless_share_stdev_FY2014_FY2025_pp", round(st.pstdev(comp), 2), "n=%d" % len(comp))
s = {r["period"]: float(r["bharti_share_pct"]) for r in sh}
emit("bharti_share_change_FY2016_FY2019_pp", round(s["FY2019"] - s["FY2016"], 2), "includes Telenor acquisition")
emit("bharti_share_change_FY2016_FY2025_pp", round(s["FY2025"] - s["FY2016"], 2), "includes Telenor + Tata Tele acquisitions")
emit("bharti_share_change_FY2017_FY2018_pp", round(s["FY2018"] - s["FY2017"], 2))
AGR = {"QE-Mar-25": (29464.67, 26324.20, 7653.53, 2239.54), "QE-Sep-25": (31767.11, 28497.45, 8176.62, 2003.48),
       "QE-Mar-26": (32467.88, 28773.59, 8195.12, 2100.96), "QE-Jun-26": (33226.12, 29803.04, 8448.09, 2117.44)}
for q, (j, b, v, bs) in AGR.items():
    t = j + b + v + bs
    emit(f"bharti_access_agr_share_top4_{q}_pct", round(b / t * 100, 2), f"Jio {round(j/t*100,2)} VIL {round(v/t*100,2)} BSNL {round(bs/t*100,2)}")

# ---------- 6. Retention ----------
CHURN = [3.3, 3.7, 3.3, 4.1, 7.3, 2.6, 2.1, 2.6, 2.6, 1.7, 1.9, 3.3, 3.0, 2.8, 2.8, 2.9, 2.9, 2.4, 2.8, 3.2, 2.5, 2.3, 2.7, 2.6, 2.4]
emit("airtel_monthly_churn_mean_pct", round(st.mean(CHURN), 2), "n=%d quarters Q4FY2016-Q4FY2026 (gaps)" % len(CHURN))
emit("airtel_monthly_churn_median_pct", round(st.median(CHURN), 2))
emit("airtel_implied_avg_life_months_Q4FY2026", round(1 / 0.024, 1), "1/monthly churn")
emit("jio_implied_avg_life_months_Q4FY2026", round(1 / 0.017, 1))

with open(os.path.join(D, "moat_metrics.out"), "w") as fh:
    fh.write("metric,value,note\n")
    for k, v, n in out: fh.write(f'"{k}","{v}","{n}"\n')
