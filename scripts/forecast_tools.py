#!/usr/bin/env python3
"""Deterministic forecasting math for the `forecasting` specialist (methodology 3.2.0): the analyst sets the drivers,
the code does the arithmetic.

  model         --inputs F [--out O]   a driver-tree operating model: bear/base/bull, year by year; the base year must
                                       tie to the reported figures (the driver tree reproduces them)
  consensus     --inputs F [--out O]   consensus snapshots -> revisions by metric and period (first, last, change,
                                       dispersion)
  surprise      --inputs F [--out O]   reported vs. consensus by quarter -> surprise %, hit rate, mean and spread
  peers         --inputs F [--out O]   peer table -> median, quartiles and the company's percentile per metric
  to-valuation  --model M --scenario base --kind fcff|ri [--extra E] --out O
                                       the model's path as inputs for valuation_tools.py dcf (fcff) or residual-income (ri)
  reconcile     --forecast M --valuation V [--out O]
                                       the forecast's base case against the valuation specialist's inputs: growth,
                                       margin or ROE, reinvestment or payout (the CIO's Stage-3 integration check)

`model` inputs (JSON, saved under RUN_DIR/calc/forecasting_*.json, every number with a claim ID in `_sources`):
  {"base_year": "FY2026", "horizon": 10, "units": "INR crore",
   "base": {"aum": 509975, "equity": 98000, "shares": 622.6},            # reported values of the base year
   "base_prev": {"aum": 418000},                                        # the year before (for averages); optional
   "base_drivers": {"aum_growth": 0.22, "nim": 0.0935},                 # the base year's actual drivers; optional
   "drivers": {"aum_growth": {"bear": 0.12, "base": [0.22, 0.04], "bull": [0.25, 0.20, 0.18]},
               "nim": {"bear": 0.085, "base": 0.093, "bull": 0.095}},
   "lines": [{"name": "aum", "formula": "aum_prev * (1 + aum_growth)"},
             {"name": "nii", "formula": "(aum + aum_prev) / 2 * nim"}, ...],
   "ties": {"nii": 37000}, "tie_tolerance": 0.02,                       # base-year reported values the lines must reproduce
   "outputs": ["aum", "pat", "eps", "bvps", "roe"]}
A driver is a number (constant), [start, end] (a linear glide over the horizon), or a list (year by year; the last value
repeats). A formula is arithmetic over the drivers, the lines computed above it, `<name>_prev` (last year's value) and
`t` (the year, 1..horizon), with min, max and abs. Nothing else is evaluated.
Exit: 0 ok, 1 a check failed (a base-year tie outside tolerance, a formula error), 2 usage.
"""

import argparse
import ast
import json
import math
import operator
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional

SCENARIOS = ("bear", "base", "bull")
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"min": min, "max": max, "abs": abs}


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def safe_eval(expr: str, env: Dict[str, float]) -> float:
    """Arithmetic only: numbers, names in `env`, + - * / **, unary minus, min/max/abs. Anything else is refused."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Num):                      # Python 3.7 compatibility
            return float(node.n)
        if isinstance(node, ast.Name):
            if node.id not in env:
                raise ValueError("unknown name %r" % node.id)
            return float(env[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
            return float(_FUNCS[node.func.id](*[ev(a) for a in node.args]))
        raise ValueError("not allowed in a formula: %s" % ast.dump(node)[:60])
    return ev(ast.parse(expr, mode="eval"))


def driver_path(spec, n: int) -> List[float]:
    if isinstance(spec, (int, float)):
        return [float(spec)] * n
    if isinstance(spec, list) and len(spec) == 2 and n != 2:
        a, b = float(spec[0]), float(spec[1])
        return [a + (b - a) * i / max(1, n - 1) for i in range(n)]
    if isinstance(spec, list) and spec:
        vals = [float(x) for x in spec]
        return (vals + [vals[-1]] * n)[:n]
    raise ValueError("a driver is a number, [start, end] or a list of values")


def model(inp: dict) -> dict:
    n = int(inp.get("horizon", 10))
    lines = inp["lines"]
    base = {k: float(v) for k, v in inp["base"].items()}
    out = {"base_year": inp.get("base_year"), "horizon": n, "units": inp.get("units", ""), "scenarios": {}, "ties": [],
           "errors": []}
    # 1. The base year: the driver tree must reproduce the reported figures.
    if inp.get("ties"):
        env = dict({"%s_prev" % k: float(v) for k, v in (inp.get("base_prev") or {}).items()},
                   **{k: float(v) for k, v in (inp.get("base_drivers") or {}).items()}, t=0.0)
        for ln in lines:
            if ln["name"] in base and ln["name"] not in inp["ties"]:
                env[ln["name"]] = base[ln["name"]]
                continue
            try:
                env[ln["name"]] = safe_eval(ln["formula"], env)
            except (ValueError, ZeroDivisionError, KeyError) as exc:
                if ln["name"] in inp["ties"]:
                    out["errors"].append("base-year %s: %s (give its inputs in base_prev or base_drivers)" % (ln["name"], exc))
                env[ln["name"]] = base.get(ln["name"], float("nan"))
        tol = float(inp.get("tie_tolerance", 0.02))
        for name, reported in inp["ties"].items():
            got = env.get(name)
            gap = None if got is None or reported == 0 or got != got else (got - reported) / abs(reported)
            ok = gap is not None and abs(gap) <= tol
            out["ties"].append({"line": name, "reported": reported, "model": got, "gap": gap, "ok": ok})
            if not ok:
                out["errors"].append("base-year tie %s: model %s vs reported %s (tolerance %.1f %%): fix the driver tree or "
                                     "the base-year drivers" % (name, "n/a" if got is None else round(got, 2), reported, 100 * tol))
    # 2. The forecast, per scenario.
    for sc in SCENARIOS:
        paths = {}
        for d, spec in inp["drivers"].items():
            s = spec.get(sc, spec.get("base")) if isinstance(spec, dict) else spec
            paths[d] = driver_path(s, n)
        prev = dict(base)
        rows = []
        for i in range(n):
            env = {"t": float(i + 1)}
            env.update({"%s_prev" % k: v for k, v in prev.items()})
            env.update({d: p[i] for d, p in paths.items()})
            for ln in lines:
                try:
                    env[ln["name"]] = safe_eval(ln["formula"], env)
                except (ValueError, ZeroDivisionError) as exc:
                    out["errors"].append("%s year %d %s: %s" % (sc, i + 1, ln["name"], exc))
                    env[ln["name"]] = float("nan")
            row = {"year": i + 1, "label": year_label(inp.get("base_year"), i + 1)}
            row.update({k: env[k] for k in [ln["name"] for ln in lines] + list(paths)})
            rows.append(row)
            prev = {k: env[k] for k in [ln["name"] for ln in lines] if env.get(k) == env.get(k)}
            prev = dict(base, **prev)
        outs = inp.get("outputs") or [ln["name"] for ln in lines]
        summary = {}
        for k in outs:
            first = base.get(k)
            last = rows[-1].get(k)
            if first and last and first > 0 and last > 0:
                summary["cagr_%s" % k] = (last / first) ** (1.0 / n) - 1
        out["scenarios"][sc] = {"rows": rows, "summary": summary}
    out["outputs"] = inp.get("outputs") or [ln["name"] for ln in lines]
    return out


def year_label(base_year: Optional[str], k: int) -> str:
    try:
        return "FY%d" % (int(str(base_year).replace("FY", "")) + k)
    except (TypeError, ValueError):
        return "Y+%d" % k


def model_markdown(res: dict) -> str:
    outs = res["outputs"]
    lines = ["# Forecast model (base year %s, %d years, %s)" % (res.get("base_year"), res["horizon"], res.get("units", "")), ""]
    if res["ties"]:
        lines += ["Base-year tie: " + "; ".join("%s model %s vs reported %s (%s)" % (
            t["line"], "n/a" if t["model"] is None else round(t["model"], 2), t["reported"], "ok" if t["ok"] else "FAIL")
            for t in res["ties"]), ""]
    for sc in SCENARIOS:
        rows = res["scenarios"][sc]["rows"]
        lines += ["## %s" % sc.capitalize(), "", "| Year | " + " | ".join(outs) + " |", "|---" * (len(outs) + 1) + "|"]
        for r in rows:
            lines.append("| %s | %s |" % (r["label"], " | ".join(fmt(r.get(k)) for k in outs)))
        s = res["scenarios"][sc]["summary"]
        if s:
            lines += ["", "CAGR: " + "; ".join("%s %.1f %%" % (k[5:], 100 * v) for k, v in s.items())]
        lines.append("")
    if res["errors"]:
        lines += ["**Errors:**"] + ["- %s" % e for e in res["errors"]]
    return "\n".join(lines)


def fmt(v) -> str:
    if v is None or v != v:
        return "-"
    if abs(v) < 1:
        return "%.4f" % v
    return "{:,.1f}".format(v)


def consensus(inp: dict) -> dict:
    """{"snapshots": [{"date", "source", "metric", "period", "mean", "high"?, "low"?, "n"?, "claim_id"}]}"""
    groups: Dict[tuple, List[dict]] = {}
    for s in inp["snapshots"]:
        groups.setdefault((s["metric"], s["period"]), []).append(s)
    rows = []
    for (metric, period), snaps in sorted(groups.items()):
        snaps = sorted(snaps, key=lambda s: s["date"])
        first, last = float(snaps[0]["mean"]), float(snaps[-1]["mean"])
        disp = None
        if snaps[-1].get("high") is not None and snaps[-1].get("low") is not None and last:
            disp = (float(snaps[-1]["high"]) - float(snaps[-1]["low"])) / abs(last)
        rows.append({"metric": metric, "period": period, "first_date": snaps[0]["date"], "first": first,
                     "last_date": snaps[-1]["date"], "last": last, "revision": (last / first - 1) if first else None,
                     "dispersion": disp, "snapshots": len(snaps), "sources": sorted({s.get("source", "") for s in snaps})})
    return {"rows": rows}


def surprise(inp: dict) -> dict:
    """{"quarters": [{"period", "metric", "actual", "consensus", "claim_ids"}]}"""
    rows, by_metric = [], {}
    for q in inp["quarters"]:
        a, c = float(q["actual"]), float(q["consensus"])
        s = (a - c) / abs(c) if c else None
        rows.append(dict(q, surprise=s))
        if s is not None:
            by_metric.setdefault(q["metric"], []).append(s)
    stats = {m: {"quarters": len(v), "mean": statistics.mean(v), "median": statistics.median(v),
                 "stdev": statistics.pstdev(v) if len(v) > 1 else 0.0, "beat_rate": sum(1 for x in v if x > 0) / len(v)}
             for m, v in by_metric.items()}
    return {"rows": rows, "stats": stats}


def peers(inp: dict) -> dict:
    """{"subject": "Co", "higher_is_better": {"roe": true, "pe": false}, "rows": [{"company": "...", "roe": 0.2, ...}]}"""
    subject = inp["subject"]
    metrics = sorted({k for r in inp["rows"] for k in r if k not in ("company", "source", "claim_ids", "period")})
    table = {}
    for m in metrics:
        vals = [(r["company"], float(r[m])) for r in inp["rows"] if isinstance(r.get(m), (int, float))]
        if len(vals) < 2:
            continue
        xs = sorted(v for _, v in vals)
        sv = next((v for c, v in vals if c == subject), None)
        pct = None
        if sv is not None:
            pct = sum(1 for x in xs if x < sv) / (len(xs) - 1) if len(xs) > 1 else None
            if inp.get("higher_is_better", {}).get(m) is False and pct is not None:
                pct = 1 - pct
        q = statistics.quantiles(xs, n=4) if len(xs) >= 4 else [xs[0], statistics.median(xs), xs[-1]]
        table[m] = {"n": len(xs), "median": statistics.median(xs), "q1": q[0], "q3": q[-1], "subject": sv,
                    "subject_percentile": pct}
    return {"subject": subject, "metrics": table}


def to_valuation(mres: dict, scenario: str, kind: str, extra: dict) -> dict:
    """The forecast path in the input format of valuation_tools.py: `fcff` (dcf: revenue growth and EBIT margin paths,
    reinvestment from the model) or `ri` (residual-income: book value, ROE and payout paths). `extra` supplies what a
    forecast does not hold (wacc or cost of equity, terminal assumptions, net debt, shares ...), each with its claim."""
    rows = mres["scenarios"][scenario]["rows"]
    n = len(rows)
    if kind == "fcff":
        need = ("revenue", "ebit")
        miss = [k for k in need if k not in rows[0]]
        if miss:
            raise ValueError("the model has no %s line (fcff needs revenue and ebit)" % ", ".join(miss))
        rev = [r["revenue"] for r in rows]
        base_rev = float(extra.get("base_revenue") or rev[0] / (1 + rows[0].get("revenue_growth", 0)))
        growth = [rev[0] / base_rev - 1] + [rev[i] / rev[i - 1] - 1 for i in range(1, n)]
        out = {"years": n, "base_revenue": base_rev, "revenue_growth": growth,
               "ebit_margin": [r["ebit"] / r["revenue"] for r in rows]}
        if "reinvestment" in rows[0] and "nopat" in rows[0]:
            out["reinvestment_rate"] = statistics.mean(r["reinvestment"] / r["nopat"] for r in rows if r["nopat"])
    elif kind == "ri":
        need = ("equity", "pat")
        miss = [k for k in need if k not in rows[0]]
        if miss:
            raise ValueError("the model has no %s line (ri needs equity and pat)" % ", ".join(miss))
        eq0 = float(extra.get("base_equity") or rows[0]["equity"] - rows[0]["pat"] + rows[0].get("dividends", 0)
                    - rows[0].get("equity_issued", 0))
        out = {"years": n, "base_equity": eq0, "profit": [r["pat"] for r in rows],
               "payout": [(rows[i].get("dividends", 0.0) / rows[i]["pat"]) if rows[i]["pat"] else 0.0 for i in range(n)]}
        if any(r.get("equity_issued") for r in rows):
            out["equity_issuance"] = [r.get("equity_issued", 0.0) for r in rows]
    else:
        raise ValueError("kind is fcff or ri")
    out.update(extra)
    out["_from"] = {"model_base_year": mres.get("base_year"), "scenario": scenario, "kind": kind}
    return out


def reconcile(fm: dict, val: dict) -> dict:
    """The forecast's base case against the valuation specialist's own inputs (dcf or residual-income): where they
    differ by more than the thresholds, a contradiction candidate for the CIO (who decides which evidence is better)."""
    rows = fm["scenarios"]["base"]["rows"]
    n = len(rows)
    flags, cmp_ = [], {}
    if "revenue_growth" in val and "revenue" in rows[0]:
        vg = val["revenue_growth"]
        vg = vg if isinstance(vg, list) else [vg]
        v_cagr = math.prod(1 + (vg[i] if i < len(vg) else vg[-1]) for i in range(n)) ** (1 / n) - 1
        f_cagr = fm["scenarios"]["base"]["summary"].get("cagr_revenue")
        cmp_["revenue_cagr"] = {"forecast": f_cagr, "valuation": v_cagr}
        if f_cagr is not None and abs(f_cagr - v_cagr) > 0.02:
            flags.append("revenue CAGR: forecast %.1f %% vs valuation %.1f %%" % (100 * f_cagr, 100 * v_cagr))
    if "ebit_margin" in val and "ebit" in rows[0] and "revenue" in rows[0]:
        vm = val["ebit_margin"]
        vm_last = vm[-1] if isinstance(vm, list) else vm
        fm_last = rows[-1]["ebit"] / rows[-1]["revenue"]
        cmp_["terminal_margin"] = {"forecast": fm_last, "valuation": vm_last}
        if abs(fm_last - vm_last) > 0.02:
            flags.append("terminal EBIT margin: forecast %.1f %% vs valuation %.1f %%" % (100 * fm_last, 100 * vm_last))
    if ("roe" in val or "profit" in val) and "pat" in rows[0] and "equity" in rows[0]:
        if "roe" in val:
            vr = val["roe"]
            vr_avg = statistics.mean(vr) if isinstance(vr, list) else vr
        else:
            vr_avg = statistics.mean(p / val.get("base_equity", rows[0]["equity"]) for p in
                                     (val["profit"] if isinstance(val["profit"], list) else [val["profit"]]))
        fr = statistics.mean(r["pat"] / r["equity"] for r in rows if r["equity"])
        cmp_["average_roe"] = {"forecast": fr, "valuation": vr_avg}
        if abs(fr - vr_avg) > 0.015:
            flags.append("average ROE: forecast %.1f %% vs valuation %.1f %%" % (100 * fr, 100 * vr_avg))
    return {"comparisons": cmp_, "flags": flags}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("model", "consensus", "surprise", "peers"):
        p = sub.add_parser(name)
        p.add_argument("--inputs", required=True)
        p.add_argument("--out")
    tv = sub.add_parser("to-valuation")
    tv.add_argument("--model", required=True)
    tv.add_argument("--scenario", default="base", choices=SCENARIOS)
    tv.add_argument("--kind", required=True, choices=["fcff", "ri"])
    tv.add_argument("--extra", help="JSON file with what the forecast does not hold (wacc, terminal assumptions, shares ...)")
    tv.add_argument("--out", required=True)
    rc = sub.add_parser("reconcile")
    rc.add_argument("--forecast", required=True)
    rc.add_argument("--valuation", required=True)
    rc.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "model":
            res = model(load(a.inputs))
            print(model_markdown(res))
        elif a.cmd == "consensus":
            res = consensus(load(a.inputs))
            print(json.dumps(res, indent=1))
        elif a.cmd == "surprise":
            res = surprise(load(a.inputs))
            print(json.dumps(res["stats"], indent=1))
        elif a.cmd == "peers":
            res = peers(load(a.inputs))
            print(json.dumps(res, indent=1))
        elif a.cmd == "to-valuation":
            res = to_valuation(load(a.model), a.scenario, a.kind, load(a.extra) if a.extra else {})
            print(json.dumps(res, indent=1))
        else:
            res = reconcile(load(a.forecast), load(a.valuation))
            print("\n".join(res["flags"]) if res["flags"] else "forecast and valuation agree within the thresholds")
    except (KeyError, ValueError) as exc:
        print("ERROR: %s" % exc)
        return 1
    out = getattr(a, "out", None)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(res, indent=2, default=str) + "\n", encoding="utf-8")
    return 1 if res.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
