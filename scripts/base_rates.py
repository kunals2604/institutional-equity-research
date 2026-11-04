#!/usr/bin/env python3
"""Reference classes from the warehouse: how often companies actually did what a forecast assumes.

  python3 scripts/base_rates.py cagr --metric revenue --years 5 --threshold 0.20 [--as-of YYYY-MM-DD] [--run RUN_DIR]
  python3 scripts/base_rates.py dist --metric roe --period FY2024 [--as-of YYYY-MM-DD] [--run RUN_DIR]
  python3 scripts/base_rates.py metrics

Every figure is computed here, from the warehouse's facts as known at `--as-of` (with `--run`, the run's cutoff), so a
replay never draws on what was filed later. With `--run` the result is written to RUN_DIR/corpus/facts/base_rates/,
where the run's agents may read it: they never read the database itself.

**Survivor-biased, always.** The warehouse holds the companies whose results NSE still indexes, and machine-readable
results start around FY2018. Companies that failed, merged or delisted before then are missing, and they are the ones a
base rate most needs. Every result says so, and gives its sample size and the years it covers: read a base rate as an
upper bound on how often good things happen, and a lower bound on how often bad things do.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import warehouse as wh  # noqa: E402

CAVEAT = ("Survivor-biased: only companies whose results NSE still indexes, machine-readable from about FY2018; failed, "
          "merged and delisted companies are largely missing. Treat a share of successes as an upper bound and a share of "
          "failures as a lower bound.")
# Derived metrics, each from reported facts of the same company, period and basis.
DERIVED = {
    "roe": "pat_attributable / average total_equity",
    "pat_margin": "pat / revenue",
    "asset_turnover": "revenue / average total_assets",
}


def fy(period: str) -> Optional[int]:
    return int(period[2:]) if period.startswith("FY") and period[2:].isdigit() else None


def series(con, metric: str, as_of: str) -> Dict[str, Dict[int, float]]:
    """{ticker: {fiscal year: value}} as known at `as_of`: for each company, period and basis the latest version filed
    by then, and for each company one basis (consolidated where it files one, else standalone)."""
    rows = con.execute("""SELECT ticker, period, basis, value, known_at FROM facts WHERE metric = ? AND known_at <= ?
                          ORDER BY known_at""", (metric, as_of)).fetchall()
    latest: Dict[tuple, float] = {}
    for ticker, period, basis, value, _known in rows:
        y = fy(period)
        if y is not None:
            latest[(ticker, basis, y)] = value          # ordered by known_at, so the last write is the latest version
    by: Dict[str, Dict[str, Dict[int, float]]] = {}
    for (ticker, basis, y), v in latest.items():
        by.setdefault(ticker, {}).setdefault(basis, {})[y] = v
    return {t: b.get("consolidated") or b["standalone"] for t, b in by.items() if b.get("consolidated") or b.get("standalone")}


def derived(con, metric: str, as_of: str) -> Dict[str, Dict[int, float]]:
    if metric not in DERIVED:
        return series(con, metric, as_of)

    def avg(s, y):
        return (s[y] + s[y - 1]) / 2 if y in s and y - 1 in s else None

    if metric == "roe":
        num, den = series(con, "pat_attributable", as_of), series(con, "total_equity", as_of)
        return {t: {y: v / avg(den[t], y) for y, v in s.items() if avg(den.get(t, {}), y)}
                for t, s in num.items() if t in den}
    if metric == "pat_margin":
        num, den = series(con, "pat", as_of), series(con, "revenue", as_of)
        return {t: {y: v / den[t][y] for y, v in s.items() if den.get(t, {}).get(y)} for t, s in num.items() if t in den}
    num, den = series(con, "revenue", as_of), series(con, "total_assets", as_of)
    return {t: {y: v / avg(den[t], y) for y, v in s.items() if avg(den.get(t, {}), y)} for t, s in num.items() if t in den}


def pct(values: List[float]) -> dict:
    if len(values) < 5:
        return {"n": len(values)}
    q = statistics.quantiles(values, n=20)
    return {"n": len(values), "p10": q[1], "p25": q[4], "median": statistics.median(values), "p75": q[14], "p90": q[17]}


def cagr(con, metric: str, years: int, threshold: float, as_of: str, end_year: Optional[int] = None) -> dict:
    """Among companies with the metric positive at both ends of a `years`-long window, how many compounded at least
    `threshold` a year. The window ends at `end_year`, or at each company's latest fiscal year known at `as_of`."""
    data = derived(con, metric, as_of)
    rates, hits, windows = [], 0, []
    for t, s in data.items():
        end = end_year or max(s)
        start = end - years
        if s.get(start, 0) > 0 and s.get(end, 0) > 0:
            r = (s[end] / s[start]) ** (1.0 / years) - 1
            rates.append(r)
            hits += r >= threshold
            windows.append(end)
    return {"kind": "cagr", "metric": metric, "years": years, "threshold": threshold, "as_of": as_of,
            "companies": len(rates), "share_at_or_above": hits / len(rates) if rates else None,
            "fiscal_years_ending": sorted(set(windows)), "distribution": pct(rates), "caveat": CAVEAT}


def dist(con, metric: str, period: str, as_of: str) -> dict:
    data = derived(con, metric, as_of)
    y = fy(period)
    vals = [s[y] for s in data.values() if y in s]
    return {"kind": "distribution", "metric": metric, "period": period, "as_of": as_of, "companies": len(vals),
            "distribution": pct(vals), "caveat": CAVEAT}


def write(run_dir: Path, result: dict) -> Path:
    out = run_dir / "corpus" / "facts" / "base_rates"
    out.mkdir(parents=True, exist_ok=True)
    name = ("%s_%s_%sy_%s" % (result["kind"], result["metric"], result.get("years", ""), result.get("threshold", ""))
            if result["kind"] == "cagr" else "%s_%s_%s" % (result["kind"], result["metric"], result["period"]))
    path = out / ("%s.json" % name.replace(".", "p"))
    rl.write_json(path, result)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cagr")
    c.add_argument("--metric", required=True)
    c.add_argument("--years", type=int, required=True)
    c.add_argument("--threshold", type=float, required=True)
    c.add_argument("--end-year", type=int)
    d = sub.add_parser("dist")
    d.add_argument("--metric", required=True)
    d.add_argument("--period", required=True)
    for p in (c, d):
        p.add_argument("--as-of")
        p.add_argument("--run")
    sub.add_parser("metrics")
    a = ap.parse_args(argv)
    if a.cmd == "metrics":
        for k, v in DERIVED.items():
            print("%-15s %s" % (k, v))
        print("and any reported metric key the warehouse holds (methodology/METRIC_DEFINITIONS.md)")
        return 0
    run = Path(a.run) if a.run else None
    as_of = rl.load_json(run / rl.RUN_MANIFEST)["research_cutoff"] if run else (a.as_of or wh.now()[:10])
    if run and a.as_of and a.as_of != as_of:
        print("--as-of must equal the run's cutoff (%s)" % as_of, file=sys.stderr)
        return 2
    con = wh.connect()
    res = cagr(con, a.metric, a.years, a.threshold, as_of, a.end_year) if a.cmd == "cagr" else dist(con, a.metric, a.period, as_of)
    print(json.dumps(res, indent=1))
    if run:
        print(write(run, res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
