#!/usr/bin/env python3
"""Build cio/scorecard.json from the CIO's judgments, then validate it.

  python3 scripts/build_scorecard.py RUN_DIR [--inputs RUN_DIR/cio/scorecard_inputs.json] [--out RUN_DIR/cio/scorecard.json]

The CIO writes only judgments in `cio/scorecard_inputs.json` (schema: `templates/scorecard.example.json`): dimension
scores, each with its own confidence, rationale and claim IDs; layer fits; classifications; scenarios; the decision
drivers; decision outputs. Everything computed is left out (or null): `weighted_raw`, `final`, `effective_score`,
`gates_triggered` beyond any the CIO adds, `decision`, `mapped_verdict`, `verdict`.

For methodology 3.0.0 scorecards (SCORING.md §§0, 1, 3a–3c, 5) this script:
  * caps a dimension's confidence at Medium when one of its evidence owners has a primary-source share below 0.50 or
    a NOT_LOCATED share above 0.15 in `qc/evidence_stats.json` (run `evidence_stats.py` first);
  * fills `price_metrics` (margin of safety, E[IRR], hurdle, hurdle-adjusted asymmetry) at the scorecard price from
    `scenario_inputs` (a path, relative to RUN_DIR, to the scenario-build or scenario-irr inputs) unless given;
  * runs the robustness grid (`valuation_tools.robustness`) to set `price_metrics.robust`, an input to conviction;
  * applies the weight profile of the primary layer (hybrid: the mean of two), the effective scores (uncertainty never
    rewarded), the gates, the must-pass tests, the required margin of safety and conviction, and maps the verdict;
  * applies an optional one-notch `override_verdict` with `override_reason`.
Scorecards for earlier methodology versions keep the 2.x arithmetic (fixed Base weights, the 2.x mapping).

It writes scorecard.json and runs the validator. No score arithmetic is done by hand anywhere in the system.
Exit 0 = valid scorecard written, 1 = validation errors (file still written so they can be fixed), 2 = usage.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def compute_legacy(sc: dict) -> dict:
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
    sc["mapped_verdict"] = rl.mapped_verdict(finals["BQ"], finals["IA"], sc["investment_attractiveness"].get("confidence", "Medium"),
                                             sorted(gates_all), sc.get("primary_layer") or "None")
    return sc


def cap_confidence_by_owners(sc: dict, run_dir: Path) -> list:
    """SCORING.md §3b evidence ceiling. Returns the notes of every cap applied."""
    stats_path = run_dir / "qc" / "evidence_stats.json"
    if not stats_path.exists():
        return []
    stats = rl.load_json(stats_path).get("by_author") or {}
    owners = rl.dimension_owners()
    notes = []
    for key in ("business_quality", "investment_attractiveness"):
        for d in sc[key]["dimensions"]:
            if d.get("confidence") != "High":
                continue
            weak = []
            for o in owners.get(d["id"], []):
                st = stats.get(o) or {}
                ps, nl = st.get("primary_share"), st.get("not_located_share")
                if (ps is not None and ps < 0.50) or (nl is not None and nl > 0.15):
                    weak.append("%s (primary %.2f, not located %.2f)" % (o, ps or 0, nl or 0))
            if weak:
                d["confidence"] = "Medium"
                d["confidence_note"] = "capped at Medium by the evidence ceiling: %s" % "; ".join(weak)
                notes.append("%s: %s" % (d["id"], d["confidence_note"]))
    return notes


def fill_price_metrics(sc: dict, run_dir: Path) -> None:
    pm = dict(sc.get("price_metrics") or {})
    src = sc.get("scenario_inputs")
    if not src:
        sc["price_metrics"] = pm
        return
    import valuation_tools as vt
    inp = json.loads((run_dir / src).read_text(encoding="utf-8"))
    built = vt.scenario_build(inp) if any("value_today" in v for v in inp.get("scenarios", {}).values()) else inp
    price = float(sc["price"]["value"])
    res = vt.scenarios(built, price)
    pm.setdefault("margin_of_safety", res["margin_of_safety"])
    pm.setdefault("expected_irr", res["expected_irr"])
    pm.setdefault("hurdle_rate", float(built.get("hurdle_rate", sc.get("hurdle_rate"))))
    pm.setdefault("asymmetry_ratio", res["asymmetry_ratio"] if res["asymmetry_ratio"] != float("inf") else 99.0)
    pm["source"] = "valuation_tools.py on %s at %s" % (src, price)
    sc["price_metrics"] = pm
    if pm.get("robust") is None and any("value_today" in v for v in inp.get("scenarios", {}).values()):
        provisional = json.loads(json.dumps(sc))
        provisional["price_metrics"]["robust"] = False
        apply_v3(provisional)
        rob = vt.robustness(inp, provisional, price)
        pm["robust"] = bool(rob["robust"])
        pm["robustness_verdicts"] = rob["verdicts"]
        pm["robustness_ia_range"] = rob["ia_range"]


def apply_v3(sc: dict) -> dict:
    ev = rl.evaluate_v3(sc)
    for kind, key in (("BQ", "business_quality"), ("IA", "investment_attractiveness")):
        block = sc[key]
        for d in block["dimensions"]:
            d["effective_score"] = round(ev["effective"][d["id"]], 2)
        block["weight_profile"] = ev["weight_profile"]
        block["weighted_raw"] = ev[kind]["weighted_raw"]
        block["base_profile_raw"] = ev[kind]["base_profile_raw"]
        block["gates_triggered"] = ev[kind]["gates"]
        block["final"] = ev[kind]["final"]
    sc["decision"] = {"layer_codes": ev["layer_codes"], "weight_profile": ev["weight_profile"],
                      "must_pass": ev["must_pass"], "buy_permitted_at_confidence": ev["buy_permitted_at_confidence"],
                      "required_margin_of_safety": ev["required_margin_of_safety"],
                      "margin_of_safety": ev["margin_of_safety"], "edge_over_hurdle": ev["edge"],
                      "conviction": ev["conviction"], "conviction_points": ev["conviction_points"],
                      "verdict_path": ev["verdict_path"]}
    sc["mapped_verdict"] = ev["mapped_verdict"]
    return sc


def compute(inp: dict, run_dir: Path = None) -> dict:
    sc = json.loads(json.dumps(inp))
    sc.pop("_comment", None)
    if sc.get("assessment_status") == "insufficient_evidence":
        for key in ("business_quality", "investment_attractiveness"):
            sc.setdefault(key, {})["final"] = None
        sc["mapped_verdict"] = None
        sc["verdict"] = None
        return sc
    sc.setdefault("methodology_version", rl.methodology_version())
    v3 = rl.version_tuple(sc["methodology_version"]) >= rl.V3
    if v3:
        notes = cap_confidence_by_owners(sc, run_dir) if run_dir else []
        if notes:
            sc.setdefault("build_notes", []).extend(notes)
        if run_dir:
            fill_price_metrics(sc, run_dir)
        apply_v3(sc)
    else:
        compute_legacy(sc)
    mapped = sc["mapped_verdict"]
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
        sc = compute(json.loads(src.read_text(encoding="utf-8")), run)
    except (KeyError, ValueError) as exc:
        print("ERROR: %s" % exc)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sc, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    bq, ia = sc["business_quality"], sc["investment_attractiveness"]
    dec = sc.get("decision") or {}
    print("BQ raw %s -> %s | IA raw %s -> %s | profile %s | gates %s | conviction %s | mapped %s | verdict %s"
          % (bq.get("weighted_raw"), bq.get("final"), ia.get("weighted_raw"), ia.get("final"), dec.get("weight_profile", "Base (2.x)"),
             sorted(set(bq.get("gates_triggered") or []) | set(ia.get("gates_triggered") or [])), dec.get("conviction", "-"),
             sc.get("mapped_verdict"), sc.get("verdict")))
    if dec:
        print("  path: %s" % dec.get("verdict_path"))
        for t in dec.get("must_pass", []):
            print("  must-pass %-12s %-8s effective %6.1f  %s" % (t["test"], t["kind"], t["effective"], "pass" if t["passed"] else "FAIL"))
        rm = dec.get("required_margin_of_safety")
        print("  margin of safety %s vs required %s" % (
            "n/a" if dec.get("margin_of_safety") is None else "%.1f %%" % (dec["margin_of_safety"] * 100),
            "none (no buy at this confidence)" if rm is None else "%.0f %%" % (rm * 100)))
    for n in sc.get("build_notes", []):
        print("  note: %s" % n)
    res = rl.validate_scorecard(out)
    print(res.render())
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
