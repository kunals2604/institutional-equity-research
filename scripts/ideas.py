#!/usr/bin/env python3
"""X or Y? Every company's latest decision, on one table.

  python3 scripts/ideas.py rank [--held research/holdings.csv]

Ranks by expected return over the hurdle, with quality and the verdict beside it. It compares; it never decides, and it adds no
position limit. Scores compare only within a methodology version, so the version is shown. research/holdings.csv is optional
(ticker per line, with a header).
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional, Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def rows(root: Path = rl.ROOT, held: Optional[Set[str]] = None) -> List[dict]:
    out = []
    for pointer in sorted((root / "research" / "companies").glob("*/" + rl.LATEST_POINTER)):
        run = pointer.parent / "runs" / pointer.read_text(encoding="utf-8").strip()
        card = run / "cio" / "scorecard.json"
        if not card.exists():
            continue
        sc = rl.load_json(card)
        pm = sc.get("price_metrics") or {}
        irr, hurdle = pm.get("expected_irr", sc.get("expected_irr_5y")), pm.get("hurdle_rate", sc.get("hurdle_rate"))
        irr = irr.get("point") if isinstance(irr, dict) else irr
        out.append({"ticker": sc.get("ticker"), "verdict": sc.get("verdict"), "bq": (sc.get("business_quality") or {}).get("final"),
                    "ia": (sc.get("investment_attractiveness") or {}).get("final"), "expected_irr": irr, "hurdle": hurdle,
                    "edge": irr - hurdle if isinstance(irr, (int, float)) and isinstance(hurdle, (int, float)) else None,
                    "as_of": sc.get("as_of_date"), "methodology": rl.load_json(run / rl.RUN_MANIFEST).get("methodology_version"),
                    "held": bool(held and sc.get("ticker") in held)})
    return sorted(out, key=lambda r: (r["edge"] is None, -(r["edge"] or 0)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rank")
    r.add_argument("--held")
    a = ap.parse_args(argv)
    held = None
    if a.held and Path(a.held).exists():
        with open(a.held, encoding="utf-8", newline="") as f:
            held = {x.get("ticker", "").strip() for x in csv.DictReader(f)}
    print("| Ticker | Held | Verdict | BQ | IA | E[IRR] | Hurdle | Edge | As of | Methodology |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for x in rows(held=held):
        print("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (x["ticker"], "yes" if x["held"] else "", x["verdict"], x["bq"], x["ia"], x["expected_irr"],
                                                                        x["hurdle"], "-" if x["edge"] is None else "%.1f pts" % (100 * x["edge"]), x["as_of"], x["methodology"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
