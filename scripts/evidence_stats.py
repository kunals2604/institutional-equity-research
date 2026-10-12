#!/usr/bin/env python3
"""Evidence-quality statistics for a run, checked against EVIDENCE_STANDARDS.md thresholds.

  python3 scripts/evidence_stats.py RUN_DIR [--json]

Reads every ledger in the run (specialists, follow-ups, CIO). Writes RUN_DIR/qc/evidence_stats.json
and prints a table: claims, tags, primary share, tier mix, NOT_LOCATED share, low-tier FACTs.
The CIO uses these numbers to justify score confidence (SCORING.md §4) and IA8.
Exit 0 always (threshold breaches are reported as warnings for the CIO to address).
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def compute(run_dir: Path) -> dict:
    per = defaultdict(list)
    for lp in rl.run_ledger_paths(run_dir):
        _, rows = rl.read_csv(lp)
        for r in rows:
            per[(r.get("author") or lp.stem.replace("_ledger", "")).strip()].append(r)
    th = rl.evidence_thresholds()

    def stats(rows):
        n = len(rows)
        tags = Counter((r.get("tag") or "").strip() for r in rows)
        tiers = Counter((r.get("source_tier") or "").strip() or "none" for r in rows)
        sourced = [r for r in rows if (r.get("source_tier") or "").strip()]
        primary = sum(1 for r in sourced if (r.get("primary") or "").strip() == "Y")
        facts = [r for r in rows if (r.get("tag") or "").strip() == "FACT"]
        low = sum(1 for r in facts if (r.get("source_tier") or "").strip() in ("6", "7"))
        notloc = sum(1 for r in rows if (r.get("locator") or "").strip().upper() == "NOT_LOCATED")
        return {"claims": n, "tags": dict(tags), "tiers": dict(tiers),
                "primary_share": (primary / len(sourced)) if sourced else None,
                "not_located_share": (notloc / n) if n else None,
                "low_tier_fact_share": (low / len(facts)) if facts else None,
                "confidence": dict(Counter((r.get("confidence") or "").strip() for r in rows))}

    out = {"by_author": {a: stats(rows) for a, rows in sorted(per.items())},
           "overall": stats([r for rows in per.values() for r in rows]), "thresholds": th, "warnings": []}
    w = out["warnings"]
    for a, s in out["by_author"].items():
        if a in rl.SPECIALISTS and s["claims"] < th["min_claims_per_specialist"]:
            w.append("%s: only %d claims (< %d): evidence base may be thin" % (a, s["claims"], th["min_claims_per_specialist"]))
        if a in rl.SPECIALISTS and s["primary_share"] is not None and s["primary_share"] < th["min_primary_share_per_specialist"]:
            w.append("%s: primary share %.0f%% < %.0f%%" % (a, 100 * s["primary_share"], 100 * th["min_primary_share_per_specialist"]))
        if s["not_located_share"] is not None and s["not_located_share"] > th["max_not_located_share"]:
            w.append("%s: %.0f%% of claims NOT_LOCATED" % (a, 100 * s["not_located_share"]))
        if s["low_tier_fact_share"] is not None and s["low_tier_fact_share"] > th["max_low_tier_fact_share"]:
            w.append("%s: %.0f%% of FACTs rest only on tier 6-7 sources" % (a, 100 * s["low_tier_fact_share"]))
    o = out["overall"]
    if o["primary_share"] is not None and o["primary_share"] < th["min_primary_share_overall"]:
        w.append("overall primary share %.0f%% < %.0f%%" % (100 * o["primary_share"], 100 * th["min_primary_share_overall"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    res = compute(run_dir)
    (run_dir / "qc").mkdir(exist_ok=True)
    rl.write_json(run_dir / "qc" / "evidence_stats.json", res)
    if a.json:
        print(json.dumps(res, indent=2))
        return 0
    pct = lambda x: "–" if x is None else "%.0f%%" % (100 * x)  # noqa: E731
    print("| author | claims | FACT | CALC | MGMT | EST | INF | JUDG | primary | NOT_LOCATED | low-tier FACT |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for a_, s in list(res["by_author"].items()) + [("ALL", res["overall"])]:
        t = s["tags"]
        print("| %s | %d | %d | %d | %d | %d | %d | %d | %s | %s | %s |" % (
            a_, s["claims"], t.get("FACT", 0), t.get("CALCULATION", 0), t.get("MANAGEMENT STATEMENT", 0),
            t.get("ESTIMATE", 0), t.get("INFERENCE", 0), t.get("JUDGMENT", 0),
            pct(s["primary_share"]), pct(s["not_located_share"]), pct(s["low_tier_fact_share"])))
    for w in res["warnings"]:
        print("warn: " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
