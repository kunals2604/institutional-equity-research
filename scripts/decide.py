#!/usr/bin/env python3
"""The owner's decision, kept apart from the system's verdict.

  python3 scripts/decide.py record RUN_DIR --action buy|add|hold|trim|exit|pass|wait --reason "..." [--price 1775] [--size 500000]
  python3 scripts/decide.py memo RUN_DIR       # prints the one-page Decision Memo

The system gives a verdict; the owner decides what to do. Keeping the two apart is what lets the outcome record show whether
the owner's judgment added to the system's or took from it. research/outcomes/owner_decisions.csv is never rewritten.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import outcomes  # noqa: E402
import research_lib as rl  # noqa: E402

ACTIONS = ("buy", "add", "hold", "trim", "exit", "pass", "wait")
RESEARCH = rl.ROOT / "research"
COLUMNS = ["decided_on", "ticker", "run_id", "system_verdict", "action", "price", "size", "reason"]


def record(run: Path, action: str, reason: str, price=None, size=None, root: Path = RESEARCH) -> dict:
    if action not in ACTIONS:
        raise SystemExit("action must be one of %s" % ", ".join(ACTIONS))
    if not reason.strip():
        raise SystemExit("say why: the record is what makes this worth keeping")
    m = rl.load_json(run / rl.RUN_MANIFEST)
    sc = rl.load_json(run / "cio" / "scorecard.json") if (run / "cio" / "scorecard.json").exists() else {}
    row = {"decided_on": dt.date.today().isoformat(), "ticker": m.get("ticker"), "run_id": m.get("run_id"), "system_verdict": sc.get("verdict"),
           "action": action, "price": price if price is not None else "", "size": size if size is not None else "", "reason": reason}
    path = outcomes.out_dir(root) / "owner_decisions.csv"
    rows = outcomes.read_rows(path) if path.exists() else []
    outcomes.write_rows(path, COLUMNS, rows + [row])
    return row


def memo(run: Path) -> str:
    """One page: what to do, at what price, why, what would change it, and what the run did not do."""
    import switches
    m = rl.load_json(run / rl.RUN_MANIFEST)
    sc = rl.load_json(run / "cio" / "scorecard.json")
    reasoning = sc.get("verdict_reasoning") or {}
    t = sc.get("decision_triggers") or {}
    pm = sc.get("price_metrics") or {}
    drivers = sc.get("decision_drivers") or []
    lines = ["# Decision memo: %s" % m.get("company"), "",
             "**%s** at %s (%s). Run %s, preset %s." % (sc.get("verdict"), (sc.get("price") or {}).get("value"), sc.get("as_of_date"),
                                                        m.get("run_id"), m.get("profile") or "(set by hand)"), ""]
    if m.get("held"):
        lines += ["**You own this.** Action on the position: **%s**." % sc.get("held_action"), ""]
    lines += ["| | |", "|---|---|", "| Business Quality | %s |" % (sc.get("business_quality") or {}).get("final"),
              "| Investment Attractiveness | %s |" % (sc.get("investment_attractiveness") or {}).get("final"),
              "| Primary layer | %s |" % sc.get("primary_layer"), "| Expected return | %s against a hurdle of %s |" % (pm.get("expected_irr"), pm.get("hurdle_rate")),
              "| Buy below | %s |" % t.get("buy_below"), "| Avoid above | %s |" % t.get("avoid_above"), "| Next review | %s |" % sc.get("next_review_due"),
              "| Computed guide | %s |" % sc.get("mapped_verdict"), ""]
    lines += ["## The case for", "", str(reasoning.get("for") or ""), "", "## The case against", "", str(reasoning.get("against") or ""), "",
              "## How they were weighed", "", str(reasoning.get("judgment") or ""), ""]
    if drivers:
        lines += ["## What decides it", ""] + ["- **%s:** %s (signpost: %s)" % (d.get("driver"), d.get("our_view"), d.get("signpost")) for d in drivers[:5]] + [""]
    lines += ["## What this run left out", "", switches.disclosure(m)]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("run_dir")
    r.add_argument("--action", required=True, choices=ACTIONS)
    r.add_argument("--reason", required=True)
    r.add_argument("--price", type=float)
    r.add_argument("--size", type=float)
    sub.add_parser("memo").add_argument("run_dir")
    a = ap.parse_args(argv)
    run = Path(a.run_dir)
    if a.cmd == "memo":
        print(memo(run))
        return 0
    print(record(run, a.action, a.reason, a.price, a.size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
