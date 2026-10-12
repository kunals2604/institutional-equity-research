#!/usr/bin/env python3
"""Compare two runs of the same company (scores, dimensions, layer fits, verdict, price, method).

  python3 scripts/compare_runs.py OLD_RUN_DIR NEW_RUN_DIR

Prints a markdown table the CIO pastes into 'Change Since Prior Run' and explains.
Flags a methodology-version change, which makes scores not directly comparable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def load(run_dir: Path):
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    sc_path = run_dir / "cio" / "scorecard.json"
    return m, (rl.load_json(sc_path) if sc_path.exists() else {})


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print(__doc__)
        return 2
    (mo, so), (mn, sn) = load(Path(args[0])), load(Path(args[1]))
    if mo.get("ticker") != mn.get("ticker"):
        print("ERROR: runs are for different companies")
        return 1
    rows = [("run_id", mo.get("run_id"), mn.get("run_id")),
            ("research_cutoff", mo.get("research_cutoff"), mn.get("research_cutoff")),
            ("methodology_version", mo.get("methodology_version"), mn.get("methodology_version")),
            ("status", mo.get("status"), mn.get("status")),
            ("price", (so.get("price") or {}).get("value"), (sn.get("price") or {}).get("value")),
            ("primary_layer", so.get("primary_layer"), sn.get("primary_layer")),
            ("verdict", so.get("verdict"), sn.get("verdict")),
            ("valuation_status", so.get("valuation_status"), sn.get("valuation_status"))]
    for i in range(1, 5):
        rows.append(("L%d fit" % i, (so.get("layer_fit", {}).get("L%d" % i) or {}).get("score"),
                     (sn.get("layer_fit", {}).get("L%d" % i) or {}).get("score")))
    for key, label in (("business_quality", "BQ"), ("investment_attractiveness", "IA")):
        ob, nb = so.get(key) or {}, sn.get(key) or {}
        rows.append((label + " final", ob.get("final"), nb.get("final")))
        od = {d["id"]: d.get("score") for d in ob.get("dimensions", [])}
        nd = {d["id"]: d.get("score") for d in nb.get("dimensions", [])}
        for did in sorted(set(od) | set(nd)):
            rows.append(("  " + did, od.get(did), nd.get(did)))
    print("| Item | Prior | Current | Changed |\n|---|---|---|---|")
    for item, a, b in rows:
        print("| %s | %s | %s | %s |" % (item, a, b, "**yes**" if a != b else ""))
    if mo.get("methodology_version") != mn.get("methodology_version"):
        print("\nNOTE: methodology version changed; scores are not directly comparable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
