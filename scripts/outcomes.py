#!/usr/bin/env python3
"""The outcome loop (methodology 3.1.0): what the system decided, whether it came true, and what that says about its
judgment.

  python3 scripts/outcomes.py backfill RUN_DIR             # add a finished run's decision and predictions (read only)
  python3 scripts/outcomes.py watch   [--date D] [--offline]  # covered companies: price vs triggers, review dates,
                                                              # predictions due -> research/outcomes/WATCH.md
  python3 scripts/outcomes.py resolve [--date D] [--offline]  # resolve due price predictions from exchange closes;
                                                              # list the ones the CIO resolves with evidence
  python3 scripts/outcomes.py record RUN_ID PID hit|miss|void --actual X --evidence E [--by cio]
  python3 scripts/outcomes.py due --ticker T --cutoff YYYY-MM-DD  # a company's earlier predictions due by a cutoff
  python3 scripts/outcomes.py score [--date D] [--offline]    # Brier score, hit rate by probability, verdict outcomes,
                                                              # attribution -> docs/CALIBRATION_LOG.md
Common option: --root DIR (the research directory holding companies/ and outcomes/; default research/).

Records in research/outcomes/ (written by `finalize_run.py` and this script, never by an agent):
  decisions.csv    one row per finished run: date, price, verdict, layer, BQ, IA, hurdle, triggers, review date
  predictions.csv  every prediction of every finished run, in its resolvable form (SCORING.md §10)
  resolutions.csv  each prediction's outcome (hit, miss or void), the actual value and the evidence; append-only,
                   the latest row of a prediction counts
  WATCH.md         the latest watch

Why. Until 2026-10-23 a run recorded predictions, price triggers and a review date, and nothing ever checked them:
`compare_runs.py` listed due predictions, docs/CALIBRATION_LOG.md was written by nothing, and the scoreboard kept only
the two scores. Without outcomes the system cannot learn whether its judgment is any good. Honest limit: the hit
rate by probability means little until dozens of predictions resolve; the watch (triggers crossed, reviews due) is
useful from the first run. Specialists never see any of this (independence): it informs the CIO and the owner.

Prices are NSE bhavcopy closes (`market_data.py`), not adjusted for splits or bonuses since the decision: a close
less than half or more than twice the decision price is flagged for the CIO to check corporate actions.
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DECISION_COLS = ("run_id", "ticker", "company", "exchange", "as_of_date", "price", "currency", "verdict",
                 "primary_layer", "business_quality", "investment_attractiveness", "hurdle_rate", "buy_below",
                 "strong_buy_below", "avoid_above", "next_review_due", "methodology_version")
PREDICTION_COLS = ("run_id", "ticker", "id", "statement", "metric", "comparator", "threshold", "unit", "period",
                   "resolution_source", "resolution_rule", "due", "probability", "claim_ids", "structured")
RESOLUTION_COLS = ("run_id", "ticker", "id", "outcome", "actual", "evidence", "resolved_on", "resolved_by")
OUTCOMES = ("hit", "miss", "void")
BUY_SIDE = ("STRONG BUY", "BUY", "SPECULATIVE BUY")
SELL_SIDE = ("AVOID", "STRONG AVOID")
BUCKETS = ((0.05, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.951))
LOG_BEGIN, LOG_END = "<!-- OUTCOMES:BEGIN -->", "<!-- OUTCOMES:END -->"
MIN_MONTHS = 6                  # a verdict is judged on price only after six months

Quote = Callable[[str, dt.date], Optional[dict]]


def research_root(run_dir: Path) -> Path:
    """<root>/research for a run at <root>/research/companies/<TICKER>/runs/<RUN_ID>."""
    return Path(run_dir).resolve().parents[3]


def out_dir(root: Path) -> Path:
    return Path(root) / "outcomes"


def read_rows(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, cols, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cols), extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def _num(x) -> Optional[float]:
    try:
        return float(str(x).replace(",", "")) if str(x).strip() not in ("", "None") else None
    except ValueError:
        return None


def _date(x) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------------------------
# Recording decisions
# --------------------------------------------------------------------------------------------------------------

def record_decision(run_dir: Path, root: Optional[Path] = None) -> Tuple[dict, List[dict]]:
    """Add (or replace) a finished run's decision and predictions. Reads the run; never writes in it."""
    run_dir = Path(run_dir)
    root = Path(root) if root else research_root(run_dir)
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    sc = rl.load_json(run_dir / "cio" / "scorecard.json")
    if sc.get("assessment_status") != "complete":
        return {}, []
    trig = sc.get("decision_triggers") or {}
    hurdle = sc.get("hurdle_rate")
    dec = {"run_id": m.get("run_id", run_dir.name), "ticker": m.get("ticker") or sc.get("ticker"),
           "company": m.get("company", ""), "exchange": m.get("exchange", ""),
           "as_of_date": sc.get("as_of_date") or m.get("research_cutoff", ""),
           "price": (sc.get("price") or {}).get("value", ""), "currency": sc.get("currency") or m.get("currency", ""),
           "verdict": sc.get("verdict") or "", "primary_layer": sc.get("primary_layer") or "",
           "business_quality": (sc.get("business_quality") or {}).get("final", ""),
           "investment_attractiveness": (sc.get("investment_attractiveness") or {}).get("final", ""),
           "hurdle_rate": hurdle.get("value") if isinstance(hurdle, dict) else hurdle,
           "buy_below": trig.get("buy_below"), "strong_buy_below": trig.get("strong_buy_below"),
           "avoid_above": trig.get("avoid_above"), "next_review_due": sc.get("next_review_due", ""),
           "methodology_version": m.get("methodology_version", "")}
    dec = {k: ("" if v is None else v) for k, v in dec.items()}
    preds = []
    for p in sc.get("predictions") or []:
        th = p.get("threshold")
        preds.append({"run_id": dec["run_id"], "ticker": dec["ticker"], "id": p.get("id", ""),
                      "statement": p.get("statement", ""), "metric": p.get("metric", ""),
                      "comparator": p.get("comparator", ""), "threshold": json.dumps(th) if isinstance(th, list) else
                      ("" if th is None else th), "unit": p.get("unit", ""), "period": p.get("period", ""),
                      "resolution_source": p.get("resolution_source", ""), "resolution_rule": p.get("resolution_rule", ""),
                      "due": p.get("due", ""), "probability": p.get("probability", ""),
                      "claim_ids": " ".join(p.get("claim_ids") or []), "structured": "Y" if p.get("comparator") else "N"})
    od = out_dir(root)
    decisions = [r for r in read_rows(od / "decisions.csv") if r["run_id"] != dec["run_id"]] + [dec]
    write_rows(od / "decisions.csv", DECISION_COLS, sorted(decisions, key=lambda r: (r["ticker"], r["run_id"])))
    rows = [r for r in read_rows(od / "predictions.csv") if r["run_id"] != dec["run_id"]] + preds
    write_rows(od / "predictions.csv", PREDICTION_COLS, sorted(rows, key=lambda r: (r["ticker"], r["run_id"], r["id"])))
    return dec, preds


def resolutions(root: Path) -> Dict[Tuple[str, str], dict]:
    out = {}
    for r in read_rows(out_dir(root) / "resolutions.csv"):
        out[(r["run_id"], r["id"])] = r
    return out


def record(root: Path, run_id: str, pid: str, outcome: str, actual: str, evidence: str, by: str = "cio",
           on: Optional[str] = None) -> dict:
    pred = next((p for p in read_rows(out_dir(root) / "predictions.csv") if p["run_id"] == run_id and p["id"] == pid), None)
    if pred is None:
        raise SystemExit("no prediction %s of run %s in %s" % (pid, run_id, out_dir(root) / "predictions.csv"))
    if outcome not in OUTCOMES:
        raise SystemExit("outcome must be one of %s" % ", ".join(OUTCOMES))
    if not evidence.strip():
        raise SystemExit("a resolution needs its evidence (a claim ID of the run that resolves it, or the source)")
    row = {"run_id": run_id, "ticker": pred["ticker"], "id": pid, "outcome": outcome, "actual": actual,
           "evidence": evidence, "resolved_on": on or dt.date.today().isoformat(), "resolved_by": by}
    path = out_dir(root) / "resolutions.csv"
    write_rows(path, RESOLUTION_COLS, read_rows(path) + [row])
    return row


def due(root: Path, ticker: str, cutoff: dt.date, before_run: str = "") -> List[dict]:
    """A company's predictions from earlier runs due on or before the cutoff, each with its resolution (or none)."""
    res = resolutions(root)
    out = []
    for p in read_rows(out_dir(root) / "predictions.csv"):
        d = _date(p["due"])
        if p["ticker"] == ticker and d and d <= cutoff and (not before_run or p["run_id"] < before_run):
            out.append(dict(p, resolution=res.get((p["run_id"], p["id"]))))
    return out


# --------------------------------------------------------------------------------------------------------------
# Prices, the watch and price predictions
# --------------------------------------------------------------------------------------------------------------

def market_quote(root: Path) -> Quote:
    """Exchange closes (NSE bhavcopy, tier 1), cached under research/outcomes/_cache/market/."""
    import market_data
    mk = market_data.Market(out_dir(root))

    def q(ticker: str, day: dt.date) -> Optional[dict]:
        return mk.quote(ticker.upper(), day)
    return q


def latest_decisions(root: Path) -> Dict[str, dict]:
    out = {}
    for r in read_rows(out_dir(root) / "decisions.csv"):
        if r["ticker"] not in out or r["run_id"] > out[r["ticker"]]["run_id"]:
            out[r["ticker"]] = r
    return out


def compare(comp: str, actual: float, threshold) -> bool:
    if comp == "between":
        lo, hi = threshold
        return lo <= actual <= hi
    return {">=": actual >= threshold, "<=": actual <= threshold, ">": actual > threshold, "<": actual < threshold}[comp]


def resolve(root: Path, today: dt.date, quote: Optional[Quote]) -> Tuple[List[dict], List[dict]]:
    """(resolved by script now, due and waiting for the CIO's resolution with evidence)."""
    res = resolutions(root)
    done, waiting = [], []
    for p in read_rows(out_dir(root) / "predictions.csv"):
        d = _date(p["due"])
        if not d or d > today or (p["run_id"], p["id"]) in res:
            continue
        auto = (p["resolution_source"] == "price" and p["comparator"] in (">=", "<=", ">", "<", "between")
                and quote is not None)
        if auto:
            q = quote(p["ticker"], d)
            th = json.loads(p["threshold"]) if p["comparator"] == "between" else _num(p["threshold"])
            if q and q.get("close") is not None and th is not None:
                hit = compare(p["comparator"], float(q["close"]), th)
                done.append(record(root, p["run_id"], p["id"], "hit" if hit else "miss", str(q["close"]),
                                   "NSE close %s on %s (%s, sha256 %s)" % (q["close"], q.get("trade_date"), q.get("url"),
                                                                         str(q.get("sha256", ""))[:16]), by="script",
                                   on=today.isoformat()))
                continue
        waiting.append(p)
    return done, waiting


def watch(root: Path, today: dt.date, quote: Optional[Quote]) -> List[dict]:
    """One row per covered company: its latest decision against today's close, its review date and its due
    predictions; `reasons` says why a re-run is due."""
    res = resolutions(root)
    preds = read_rows(out_dir(root) / "predictions.csv")
    rows = []
    for tk, d in sorted(latest_decisions(root).items()):
        q = quote(tk, today) if quote else None
        close = _num(q.get("close")) if q else None
        p0 = _num(d["price"])
        reasons, notes = [], []
        if close is not None:
            bb, sb, aa = _num(d["buy_below"]), _num(d["strong_buy_below"]), _num(d["avoid_above"])
            if sb is not None and close <= sb:
                reasons.append("price %s at or below strong_buy_below %s" % (close, sb))
            elif bb is not None and close <= bb:
                reasons.append("price %s at or below buy_below %s" % (close, bb))
            if aa is not None and close >= aa and d["verdict"] in BUY_SIDE:
                reasons.append("price %s at or above avoid_above %s on a %s" % (close, aa, d["verdict"]))
            if p0 and not 0.5 <= close / p0 <= 2:
                notes.append("close is %.2fx the decision price: check splits and bonuses before reading the triggers"
                             % (close / p0))
        review = _date(d["next_review_due"])
        if review and review <= today:
            reasons.append("review date %s reached" % review)
        open_due = [p for p in preds if p["run_id"] == d["run_id"] and _date(p["due"]) and _date(p["due"]) <= today
                    and (p["run_id"], p["id"]) not in res]
        if open_due:
            reasons.append("%d prediction(s) due and unresolved: %s" % (len(open_due), ", ".join(p["id"] for p in open_due)))
        rows.append({"ticker": tk, "run_id": d["run_id"], "verdict": d["verdict"], "decision_price": p0, "close": close,
                     "close_date": (q or {}).get("trade_date", ""), "return_since": (close / p0 - 1) if close and p0 else None,
                     "buy_below": d["buy_below"], "avoid_above": d["avoid_above"], "review": d["next_review_due"],
                     "reasons": reasons, "notes": notes})
    lines = ["# Watch — %s" % today.isoformat(), "",
             "Generated by `scripts/outcomes.py watch`; do not edit. Prices: NSE closes (not adjusted for corporate "
             "actions since the decision). A company with a reason below is due for a re-run (`/research-company`).", "",
             "| Company | Run | Verdict | Decision price | Close (date) | Since decision | buy_below / avoid_above | Review | Re-run because |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s / %s | %s | %s |" % (
            r["ticker"], r["run_id"], r["verdict"], r["decision_price"] or "-",
            "%s (%s)" % (r["close"], r["close_date"]) if r["close"] is not None else "no quote",
            "%+.1f %%" % (100 * r["return_since"]) if r["return_since"] is not None else "-",
            r["buy_below"] or "-", r["avoid_above"] or "-", r["review"] or "-",
            "; ".join(r["reasons"] + r["notes"]) or "nothing yet"))
    od = out_dir(root)
    od.mkdir(parents=True, exist_ok=True)
    (od / "WATCH.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


# --------------------------------------------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------------------------------------------

def attribution(root: Path, resolved: List[Tuple[dict, int]]) -> Dict[str, List[Tuple[float, int]]]:
    """{specialist or cio: [(probability, outcome)]} — the agents whose claims a resolved prediction rested on
    (its claim IDs and everything they rest on, through the run's claim graph, read only)."""
    import claim_graph
    prefix_of = {v: k for k, v in rl.SPECIALISTS.items()}
    prefix_of[rl.CIO_PREFIX] = "cio"
    graphs, out = {}, defaultdict(list)
    for p, y in resolved:
        rd = Path(root) / "companies" / p["ticker"] / "runs" / p["run_id"]
        if rd not in graphs:
            graphs[rd] = claim_graph.build(rd, write=False) if rd.is_dir() else None
        ids = (p.get("claim_ids") or "").split()
        g = graphs[rd]
        every = set(ids) | (set(claim_graph.up(g, ids)) if g else set())
        for owner in sorted({prefix_of.get(c.split("-C")[0], "") for c in every} - {""}):
            out[owner].append((float(p["probability"]), y))
    return out


def brier(pairs: List[Tuple[float, int]]) -> Optional[float]:
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else None


def score(root: Path, today: dt.date, quote: Optional[Quote], log_path: Optional[Path] = None) -> dict:
    res = resolutions(root)
    preds = read_rows(out_dir(root) / "predictions.csv")
    resolved = [(p, 1 if res[(p["run_id"], p["id"])]["outcome"] == "hit" else 0) for p in preds
                if (p["run_id"], p["id"]) in res and res[(p["run_id"], p["id"])]["outcome"] in ("hit", "miss")]
    pairs = [(float(p["probability"]), y) for p, y in resolved]
    buckets = []
    for lo, hi in BUCKETS:
        b = [(q, y) for q, y in pairs if lo <= q < hi]
        buckets.append({"range": "%.2f-%.2f" % (lo, min(hi, 0.95)), "n": len(b),
                        "mean_probability": sum(q for q, _ in b) / len(b) if b else None,
                        "hit_rate": sum(y for _, y in b) / len(b) if b else None})
    verdicts = []
    for d in read_rows(out_dir(root) / "decisions.csv"):
        start = _date(d["as_of_date"])
        months = (today - start).days / 30.44 if start else 0
        row = {"ticker": d["ticker"], "run_id": d["run_id"], "verdict": d["verdict"], "months": round(months, 1),
               "return": None, "hurdle_pro_rata": None, "judged": "too early (< %d months)" % MIN_MONTHS}
        if months >= MIN_MONTHS and quote:
            q = quote(d["ticker"], today)
            p0, hurdle = _num(d["price"]), _num(d["hurdle_rate"])
            if q and q.get("close") and p0:
                ret = float(q["close"]) / p0 - 1
                need = (1 + (hurdle or 0)) ** (months / 12) - 1
                row.update({"return": ret, "hurdle_pro_rata": need})
                if d["verdict"] in BUY_SIDE:
                    row["judged"] = "right" if ret >= need else "wrong"
                elif d["verdict"] in SELL_SIDE:
                    row["judged"] = "right" if ret < need else "wrong"
                else:
                    row["judged"] = "not judged on price (%s)" % d["verdict"]
        verdicts.append(row)
    by_agent = {a: {"n": len(v), "brier": brier(v)} for a, v in sorted(attribution(root, resolved).items())}
    out = {"generated_on": today.isoformat(), "predictions": len(preds), "resolved": len(pairs),
           "void": sum(1 for r in res.values() if r["outcome"] == "void"), "brier": brier(pairs),
           "base_rate": sum(y for _, y in pairs) / len(pairs) if pairs else None, "buckets": buckets,
           "verdicts": verdicts, "by_agent": by_agent}
    write_log(out, log_path or rl.ROOT / "docs" / "CALIBRATION_LOG.md")
    return out


def fmt(x, pct=False) -> str:
    if x is None:
        return "-"
    return "%.0f %%" % (100 * x) if pct else "%.3f" % x


def write_log(out: dict, path: Path) -> None:
    lines = [LOG_BEGIN, "", "## Outcomes (generated by `scripts/outcomes.py score` on %s; do not edit)" % out["generated_on"], "",
             "Predictions recorded: %d; resolved hit or miss: %d; void: %d. Brier score: %s (0 is perfect; always "
             "saying 0.5 scores 0.25). Base rate of hits: %s." % (out["predictions"], out["resolved"], out["void"],
                                                                  fmt(out["brier"]), fmt(out["base_rate"], True)), ""]
    if out["resolved"] < 30:
        lines += ["Fewer than 30 resolved predictions: read the table below as a record, not yet as evidence of "
                  "calibration.", ""]
    lines += ["| Stated probability | Resolved | Mean stated | Came true |", "|---|---|---|---|"]
    lines += ["| %s | %d | %s | %s |" % (b["range"], b["n"], fmt(b["mean_probability"], True), fmt(b["hit_rate"], True))
              for b in out["buckets"]]
    lines += ["", "| Company | Run | Verdict | Months | Return since | Hurdle pro rata | Judged |", "|---|---|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s | %s | %s | %s |" % (v["ticker"], v["run_id"], v["verdict"], v["months"],
                                                         fmt(v["return"], True), fmt(v["hurdle_pro_rata"], True), v["judged"])
              for v in out["verdicts"]]
    if out["by_agent"]:
        lines += ["", "Resolved predictions by the agents whose claims they rested on (claim graph):", "",
                  "| Agent | Resolved | Brier |", "|---|---|---|"]
        lines += ["| %s | %d | %s |" % (a, v["n"], fmt(v["brier"])) for a, v in out["by_agent"].items()]
    lines += ["", LOG_END]
    text = path.read_text(encoding="utf-8") if path.exists() else "# Calibration Log\n"
    block = "\n".join(lines)
    if LOG_BEGIN in text and LOG_END in text:
        text = text[:text.index(LOG_BEGIN)] + block + text[text.index(LOG_END) + len(LOG_END):]
    else:
        text = text.rstrip("\n") + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(rl.ROOT / "research"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    b.add_argument("run_dir")
    for name in ("watch", "resolve", "score"):
        s = sub.add_parser(name)
        s.add_argument("--date", default=dt.date.today().isoformat())
        s.add_argument("--offline", action="store_true", help="no exchange fetch (prices only from what is cached)")
    r = sub.add_parser("record")
    r.add_argument("run_id")
    r.add_argument("pid")
    r.add_argument("outcome", choices=OUTCOMES)
    r.add_argument("--actual", default="")
    r.add_argument("--evidence", required=True)
    r.add_argument("--by", default="cio")
    d = sub.add_parser("due")
    d.add_argument("--ticker", required=True)
    d.add_argument("--cutoff", required=True)
    a = ap.parse_args(argv)
    root = Path(a.root)
    if a.cmd == "backfill":
        dec, preds = record_decision(Path(a.run_dir), root)
        print("decision %s %s %s; %d prediction(s), %d structured" % (
            dec.get("ticker"), dec.get("run_id"), dec.get("verdict"), len(preds), sum(p["structured"] == "Y" for p in preds))
              if dec else "not a complete assessment: nothing recorded")
        return 0
    if a.cmd == "record":
        print(record(root, a.run_id, a.pid, a.outcome, a.actual, a.evidence, a.by))
        return 0
    if a.cmd == "due":
        rows = due(root, a.ticker, dt.date.fromisoformat(a.cutoff))
        for p in rows:
            r_ = p["resolution"]
            print("%s %s due %s p=%s: %s -> %s" % (p["run_id"], p["id"], p["due"], p["probability"], p["statement"][:90],
                                                  "%s (%s)" % (r_["outcome"], r_["evidence"][:60]) if r_ else "UNRESOLVED"))
        print("%d prediction(s), %d unresolved" % (len(rows), sum(1 for p in rows if not p["resolution"])))
        return 0
    today = dt.date.fromisoformat(a.date)
    quote = None if a.offline else market_quote(root)
    if a.cmd == "watch":
        rows = watch(root, today, quote)
        for r_ in rows:
            print("%s %s %s: %s" % (r_["ticker"], r_["run_id"], r_["verdict"], "; ".join(r_["reasons"] + r_["notes"]) or "nothing yet"))
        print("-> %s" % (out_dir(root) / "WATCH.md"))
        return 0
    if a.cmd == "resolve":
        done, waiting = resolve(root, today, quote)
        for r_ in done:
            print("resolved by script: %s %s %s (%s)" % (r_["run_id"], r_["id"], r_["outcome"], r_["evidence"][:80]))
        for p in waiting:
            print("due, for the CIO to resolve with evidence: %s %s %s due %s: %s" % (
                p["ticker"], p["run_id"], p["id"], p["due"], p["statement"][:90]))
        return 0
    log = rl.ROOT / "docs" / "CALIBRATION_LOG.md" if root.resolve() == (rl.ROOT / "research").resolve() else \
        out_dir(root) / "CALIBRATION_LOG.md"
    out = score(root, today, quote, log)
    print("resolved %d of %d; Brier %s; verdicts judged: %d" % (out["resolved"], out["predictions"], fmt(out["brier"]),
                                                                 sum(1 for v in out["verdicts"] if v["judged"] in ("right", "wrong"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
