#!/usr/bin/env python3
"""Cross-ledger numeric reconciliation: same metric, period, basis and unit -> same number.

  python3 scripts/reconcile_numbers.py RUN_DIR [--tolerance 0.01]

Groups quantitative FACT / CALCULATION / ESTIMATE claims from every ledger in the run by
(metric, period, basis, unit) and flags groups whose values differ by more than the
tolerance (relative). Writes RUN_DIR/qc/numeric_conflicts.csv. The CIO must adjudicate
each conflict in cio/contradiction_log.md (cite the claim IDs); validate_run.py --stage
final fails while a flagged conflict's claim IDs are absent from the log.
Exit 0 always; the count is printed.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def norm_unit(u: str) -> str:
    u = (u or "").strip().lower().replace("₹", "inr ").replace("rs.", "inr ").replace("rupees", "inr")
    u = re.sub(r"\brs\b", "inr", u)
    u = re.sub(r"\bcrores?\b|\bcr\b", "crore", u)
    u = re.sub(r"\bmn\b|\bmillions\b", "million", u)
    u = re.sub(r"\bbn\b|\bbillions\b", "billion", u)
    u = re.sub(r"\bpercent\b|\bpct\b", "%", u)
    return re.sub(r"\s+", " ", u).strip()


def norm_period(p: str) -> str:
    p = (p or "").strip().upper().replace(" ", "")
    m = re.fullmatch(r"FY'?(\d{2})", p)
    if m:
        return "FY20" + m.group(1)
    m = re.fullmatch(r"Q([1-4])FY'?(\d{2})", p)
    if m:
        return "Q%sFY20%s" % (m.group(1), m.group(2))
    return p


def conflicts(run_dir: Path, tol: float = 0.01) -> List[dict]:
    groups = defaultdict(list)
    for lp in rl.run_ledger_paths(run_dir):
        _, rows = rl.read_csv(lp)
        for r in rows:
            if (r.get("tag") or "").strip() not in ("FACT", "CALCULATION", "ESTIMATE"):
                continue
            metric = (r.get("metric") or "").strip()
            try:
                value = float((r.get("value") or "").replace(",", ""))
            except ValueError:
                continue
            if not metric:
                continue
            key = (metric, norm_period(r.get("period")), (r.get("basis") or "").strip().lower(), norm_unit(r.get("unit")))
            groups[key].append((r["claim_id"], (r.get("author") or "").strip(), value, (r.get("tag") or "").strip()))
    out = []
    for (metric, period, basis, unit), items in sorted(groups.items()):
        vals = [v for _, _, v, _ in items]
        if len(items) < 2:
            continue
        lo, hi = min(vals), max(vals)
        scale = max(abs(lo), abs(hi))
        if scale == 0 or (hi - lo) / scale <= tol:
            continue
        out.append({"metric": metric, "period": period, "basis": basis, "unit": unit,
                    "min": lo, "max": hi, "relative_gap": (hi - lo) / scale,
                    "claims": "; ".join("%s(%s)=%s [%s]" % (c, a, v, t) for c, a, v, t in items),
                    "claim_ids": "; ".join(c for c, _, _, _ in items)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--tolerance", type=float, default=0.01)
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    found = conflicts(run_dir, a.tolerance)
    (run_dir / "qc").mkdir(exist_ok=True)
    cols = ["metric", "period", "basis", "unit", "min", "max", "relative_gap", "claims", "claim_ids"]
    with (run_dir / "qc" / "numeric_conflicts.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(found)
    print("%d numeric conflict(s) across ledgers (tolerance %.1f%%)." % (len(found), 100 * a.tolerance))
    for c in found:
        print("- %s %s [%s, %s]: %s..%s (gap %.1f%%) -> %s" % (c["metric"], c["period"], c["basis"], c["unit"],
                                                           c["min"], c["max"], 100 * c["relative_gap"], c["claims"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
