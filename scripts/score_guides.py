#!/usr/bin/env python3
"""Quantitative-guide bands for BQ1, BQ4 and BQ5 (methodology/SCORING.md §2), computed from the audited financials.

  python3 scripts/score_guides.py --metrics calc/financials_metrics.csv --history specialists/financials_workpapers/financial_history.csv \
      --wacc 0.1103 [--years 10] [--end FY2026] [--lender --coe 0.13] [--out calc/cio_score_guides.json]

Inputs are the outputs of `fin_metrics.py` (`--metrics`) and the financials specialist's verified history (`--history`,
needed for cumulative CFO/PAT). The script prints the guide band per dimension, the numbers behind it, and the flags that
the anchors say justify moving one band down. It never sets a score: the CIO starts from the band and writes the reason
for any deviation in the scorecard rationale. Missing years are reported, never filled.
"""

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Band = Tuple[str, str]


def _fy(period: str) -> Optional[int]:
    p = (period or "").strip().upper()
    if p.startswith("FY") and p[2:].isdigit():
        return int(p[2:])
    if p.isdigit() and len(p) == 4:
        return int(p)
    return None


def load(path: Path, key_col: str) -> Dict[Tuple[str, int], float]:
    out = {}
    with path.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            y = _fy(r.get("period", ""))
            try:
                v = float(r.get("value", ""))
            except (TypeError, ValueError):
                continue
            if y is not None:
                out[(r.get(key_col) or "").strip(), y] = v
    return out


def band(value: float, table: List[Tuple[float, str]], below: str) -> str:
    for threshold, label in table:
        if value >= threshold:
            return label
    return below


def bq1(m, years, wacc, lender, coe) -> dict:
    key, bar = ("roe", coe) if lender else ("roic", wacc)
    series = {y: m.get((key, y)) for y in years}
    vals = [v for v in series.values() if v is not None]
    res = {"metric": key, "series": series, "years_available": len(vals), "years_missing": [y for y, v in series.items() if v is None]}
    if not vals:
        res["band"] = "no data"
        return res
    med = statistics.median(vals)
    spread = (med - bar) * 100
    if lender:
        guide = band(spread, [(8, "90-100"), (4, "75-89"), (1, "60-74"), (-1, "45-59")], "0-44")
    else:
        guide = band(spread, [(15, "90-100"), (8, "75-89"), (3, "60-74"), (0, "45-59"), (-5, "30-44")], "0-29")
    flags = []
    inc = m.get(("incremental_roic_5y", years[-1]))
    if not lender and inc is not None and inc < med / 2:
        flags.append("incremental_roic_5y %.4f < half the median %.4f: adjust within band or one band down" % (inc, med))
    top = sorted(vals, reverse=True)
    if len(top) >= 3 and top[0] > bar and all(v <= bar for v in top[2:]):
        flags.append("returns above the hurdle in at most two years: check for dependence on a peak period")
    res.update({"median": round(med, 4), "hurdle": bar, "spread_pp": round(spread, 2), "years_above_hurdle": sum(1 for v in vals if v > bar),
                "incremental_roic_5y": inc, "band": guide, "flags": flags})
    return res


def bq4(m, h, years) -> dict:
    cfo = [h.get(("cfo", y)) for y in years]
    pat = [h.get(("pat", y)) for y in years]
    fcf = {y: m.get(("fcf", y)) for y in years}
    complete = [(c, p) for c, p in zip(cfo, pat) if c is not None and p is not None]
    res = {"years_with_cfo_and_pat": len(complete), "fcf": fcf,
           "fcf_positive_years": sum(1 for v in fcf.values() if v is not None and v > 0),
           "fcf_years_available": sum(1 for v in fcf.values() if v is not None)}
    psum = sum(p for _, p in complete)
    if not complete or psum <= 0:
        res["band"] = "not meaningful (no complete years or cumulative PAT <= 0): judge CFO/EBITDA after tax and say so"
        return res
    ratio = sum(c for c, _ in complete) / psum
    guide = band(ratio, [(0.85, "70-84"), (0.7, "50-69"), (0.5, "30-49")], "0-29")
    if ratio >= 1.0 and res["fcf_positive_years"] >= 0.8 * len(years):
        guide = "85-100"
    flags = []
    acc = [m.get(("accruals_ratio", y)) for y in years[-3:]]
    if all(v is not None for v in acc) and acc[0] < acc[1] < acc[2]:
        flags.append("accruals_ratio rising for 3 years: subtract up to one band unless explained")
    rg = [(m.get(("dso", y)), m.get(("revenue_growth", y))) for y in years[-3:]]
    dso_up = [rg[i][0] is not None and rg[i - 1][0] is not None and rg[i][1] is not None
              and (rg[i][0] / rg[i - 1][0] - 1) > rg[i][1] for i in range(1, len(rg))]
    if len(dso_up) >= 2 and all(dso_up):
        flags.append("dso growing faster than revenue for 2+ years: subtract up to one band unless explained")
    losses = [y for y, p in zip(years, pat) if p is not None and p <= 0]
    if losses or ratio > 2.0:
        flags.append("cumulative CFO/PAT %.2f is distorted by depressed or negative PAT (loss years: %s): cross-check CFO/EBITDA after tax"
                     % (ratio, ", ".join("FY%d" % y for y in losses) or "none"))
    oi = m.get(("other_income_share_pbt", years[-1]))
    if oi is not None and oi > 0.25:
        flags.append("other_income_share_pbt %.2f > 0.25: subtract up to one band unless explained" % oi)
    if ratio >= 1.0 and guide != "85-100":
        flags.append("cumulative CFO/PAT >= 1.0 but FCF positive in only %d of %d years: 70-84 unless heavy growth capex is shown (then judge CFO/EBITDA after tax)"
                     % (res["fcf_positive_years"], len(years)))
    res.update({"cum_cfo_to_pat": round(ratio, 3), "band": guide, "flags": flags})
    return res


def bq5(m, years) -> dict:
    nde = {y: m.get(("net_debt_to_ebitda", y)) for y in years}
    cov = {y: m.get(("interest_coverage", y)) for y in years}
    latest = nde.get(years[-1])
    nd = m.get(("net_debt", years[-1]))
    vals = [v for v in nde.values() if v is not None]
    res = {"net_debt_to_ebitda": nde, "interest_coverage": cov, "latest_net_debt_to_ebitda": latest,
           "median_net_debt_to_ebitda": round(statistics.median(vals), 3) if vals else None}
    if latest is None:
        res["band"] = "no data"
        return res
    if nd is not None and nd <= 0:
        guide = "90-100"
    else:
        guide = band(-latest, [(-1.0, "75-89"), (-2.5, "55-74"), (-4.0, "35-54")], "0-34")
    covs = [v for v in cov.values() if v is not None]
    trough = min(covs) if covs else None
    flags = ["the guide uses mid-cycle EBITDA: if the latest year is not mid-cycle, re-run the band on a normalized EBITDA and say so",
             "debt maturing within 24 months without committed refinancing (> 40 %) is not in this dataset: check filings"]
    if trough is not None and trough < 3:
        flags.append("trough interest_coverage %.2f < 3x: subtract one band" % trough)
    res.update({"trough_interest_coverage": trough, "band": guide, "flags": flags})
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--metrics", required=True, help="fin_metrics.py output CSV (metric,period,value,...)")
    ap.add_argument("--history", help="financial_history.csv (item,period,value,...); needed for BQ4")
    ap.add_argument("--wacc", type=float, help="the run's WACC (decimal), required for non-financials")
    ap.add_argument("--lender", action="store_true", help="use the lender guides (ROE vs cost of equity)")
    ap.add_argument("--coe", type=float, help="cost of equity (decimal), required with --lender")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--end", help="last fiscal year, e.g. FY2026 (default: latest in metrics)")
    ap.add_argument("--out", help="also write the result as JSON")
    a = ap.parse_args(argv)
    if a.lender and a.coe is None or not a.lender and a.wacc is None:
        ap.error("--wacc is required (or --lender with --coe)")
    m = load(Path(a.metrics), "metric")
    h = load(Path(a.history), "item") if a.history else {}
    end = _fy(a.end) if a.end else max((y for _, y in m), default=None)
    if end is None:
        print("no fiscal years found in %s" % a.metrics)
        return 2
    years = list(range(end - a.years + 1, end + 1))
    out = {"window": "FY%d-FY%d" % (years[0], years[-1]), "BQ1": bq1(m, years, a.wacc, a.lender, a.coe)}
    if not a.lender:
        out["BQ4"] = bq4(m, h, years) if h else {"band": "needs --history"}
        out["BQ5"] = bq5(m, years)
    else:
        out["BQ4"] = {"band": "lenders: judge internal capital generation vs advances growth and provisioning adequacy (SCORING.md BQ4)"}
        out["BQ5"] = {"band": "lenders: judge Tier-1 headroom and ALM gaps (SCORING.md BQ5)"}
    print("Window %s" % out["window"])
    for d in ("BQ1", "BQ4", "BQ5"):
        r = out[d]
        keys = [k for k in ("median", "spread_pp", "years_above_hurdle", "cum_cfo_to_pat", "fcf_positive_years",
                            "latest_net_debt_to_ebitda", "trough_interest_coverage") if k in r]
        print("%s guide band: %s  %s" % (d, r["band"], "  ".join("%s=%s" % (k, r[k]) for k in keys)))
        for f in r.get("flags", []):
            print("    flag: %s" % f)
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
