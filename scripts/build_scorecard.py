#!/usr/bin/env python3
"""Build cio/scorecard.json from the CIO's judgments, then validate it.

  python3 scripts/build_scorecard.py RUN_DIR [--inputs RUN_DIR/cio/scorecard_inputs.json] [--out RUN_DIR/cio/scorecard.json]

The CIO writes only judgments in `cio/scorecard_inputs.json`, which has the same schema as
`templates/scorecard.example.json`. The judgments are dimension scores with rationales and claim IDs, layer fits,
scenarios, decision outputs and so on. Leave out (or set to null) everything that is computed:
`weighted_raw`, `final`, `gates_triggered` (beyond any the CIO adds), `mapped_verdict` and `verdict`.

This script then:
  * adds the gates implied by the filings/governance classifications (SCORING.md gates G1-G3), plus any listed;
  * computes the weighted raw scores from the fixed weights in SCORING.md;
  * caps the finals at the gate limits and rounds half up (research_lib.round_half_up), as the validator does;
  * maps the verdict (SCORING.md §5) and applies an optional one-notch `override_verdict` with `override_reason`.

It writes scorecard.json and runs the validator. No score arithmetic is done by hand anywhere in the system.
Exit 0 = valid scorecard written, 1 = validation errors (file still written so they can be fixed), 2 = usage.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def compute(inp: dict) -> dict:
    sc = json.loads(json.dumps(inp))
    sc.pop("_comment", None)
    if sc.get("assessment_status") == "insufficient_evidence":
        for key in ("business_quality", "investment_attractiveness"):
            sc.setdefault(key, {})["final"] = None
        sc["mapped_verdict"] = None
        sc["verdict"] = None
        return sc
    implied = set()
    cls = sc.get("classifications") or {}
    for (field, value), gate in rl._CLASSIFICATION_GATES.items():
        if str(cls.get(field, "")).strip().lower() == value:
            implied.add(gate)
    finals, gates_all = {}, set()
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc[key]
        weights = {d: w for d, _, w in rl.dimension_weights(kind)}
        scores = {d["id"]: d["score"] for d in block["dimensions"]}
        missing = set(weights) - set(scores)
        if missing:
            raise ValueError("%s is missing dimensions %s" % (key, sorted(missing)))
        raw = sum(scores[d] * w for d, w in weights.items()) / 100.0
        table = rl.gates(kind)
        hit = sorted((set(block.get("gates_triggered") or []) | implied) & set(table))
        caps = [table[g][1] for g in hit if table[g][1] is not None]
        block["weighted_raw"] = round(raw, 2)
        block["gates_triggered"] = hit
        block["final"] = min([rl.round_half_up(raw)] + caps)
        finals[kind] = block["final"]
        gates_all |= set(hit)
    mapped = rl.mapped_verdict(finals["BQ"], finals["IA"], sc["investment_attractiveness"].get("confidence", "Medium"),
                               sorted(gates_all), sc.get("primary_layer") or "None")
    sc["mapped_verdict"] = mapped
    override = sc.pop("override_verdict", None)
    if override:
        if abs(rl.NOTCH.get(override, 99) - rl.NOTCH.get(mapped, -99)) > 1:
            raise ValueError("override %r is more than one notch from the mapped verdict %r" % (override, mapped))
        if not (sc.get("override_reason") or "").strip():
            raise ValueError("override_verdict requires override_reason")
        sc["verdict"] = override
    else:
        sc["verdict"] = mapped
        sc.setdefault("override_reason", None)
    return sc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--inputs")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    run = Path(a.run_dir)
    src = Path(a.inputs) if a.inputs else run / "cio" / "scorecard_inputs.json"
    out = Path(a.out) if a.out else run / "cio" / "scorecard.json"
    if not src.exists():
        print("inputs not found: %s (write the CIO judgments there; schema: templates/scorecard.example.json)" % src)
        return 2
    try:
        sc = compute(json.loads(src.read_text(encoding="utf-8")))
    except (KeyError, ValueError) as exc:
        print("ERROR: %s" % exc)
        return 1
    out.write_text(json.dumps(sc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    bq, ia = sc["business_quality"], sc["investment_attractiveness"]
    print("BQ raw %s -> %s | IA raw %s -> %s | gates %s | mapped %s | verdict %s"
          % (bq.get("weighted_raw"), bq.get("final"), ia.get("weighted_raw"), ia.get("final"),
             sorted(set(bq.get("gates_triggered") or []) | set(ia.get("gates_triggered") or [])), sc.get("mapped_verdict"), sc.get("verdict")))
    res = rl.validate_scorecard(out)
    print(res.render())
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
