"""Tests for the claim graph (scripts/claim_graph.py) and its use in the verification loop."""

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import claim_graph as cg  # noqa: E402
import research_lib as rl  # noqa: E402
import verify  # noqa: E402


def write_ledger(path: Path, rows):
    cols = rl.ledger_columns()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def claim(cid, tag, value="", inputs="", url="https://example.com/ar.pdf"):
    return {"claim_id": cid, "author": "financials", "claim": "claim %s" % cid, "tag": tag, "value": value,
            "unit": "INR mn", "period": "FY2025", "basis": "consolidated", "source_url_or_id": url, "locator": "p.12",
            "formula_or_inputs": inputs}


class GraphRun(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="eqr-graph-"))
        write_ledger(self.dir / "specialists" / "financials_ledger.csv", [
            claim("FIN-C001", "FACT", "1,000"), claim("FIN-C002", "FACT", "250"),
            claim("FIN-C003", "CALCULATION", "25%", "FIN-C002 / FIN-C001"),
            claim("FIN-C004", "FACT", "7"), claim("FIN-C005", "FACT", "9")])
        (self.dir / "specialists" / "financials.md").write_text(
            "# Financials\n\n## Domain Conclusion\n\nMargins are 25 % [CALCULATION] (FIN-C003).\n\n## Other\n\n"
            "Something else (FIN-C004).\n", encoding="utf-8")
        write_ledger(self.dir / "cio" / "cio_ledger.csv", [claim("CIO-C001", "CALCULATION", "x", "FIN-C003 and FIN-C005")])
        (self.dir / "cio" / "scorecard.json").write_text(json.dumps({"business_quality": {"dimensions": [
            {"name": "Returns", "claim_ids": ["CIO-C001"]}, {"name": "Growth", "claim_ids": ["FIN-C999"]}]}}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestClaimGraph(GraphRun):
    def test_links_are_read_from_the_records_and_broken_ones_are_errors(self):
        g = cg.build(self.dir)
        self.assertTrue((self.dir / "qc" / "claim_graph.json").exists())
        self.assertEqual(g["inputs"]["FIN-C003"], ["FIN-C002", "FIN-C001"])
        errs = cg.errors(g)
        self.assertTrue(any("FIN-C999" in e and "scorecard" in e for e in errs), "a scorecard ID no ledger holds")
        write_ledger(self.dir / "specialists" / "financials_ledger.csv", [claim("FIN-C001", "FACT", "1"),
                                                                          claim("FIN-C003", "CALCULATION", "2", "sum")])
        self.assertIn("FIN-C003", cg.build(self.dir, write=False)["errors"]["calculation_without_inputs"])

    def test_down_reaches_everything_built_on_a_claim_and_up_reaches_the_facts(self):
        g = cg.build(self.dir, write=False)
        down = cg.down(g, ["FIN-C001"])
        self.assertIn("FIN-C003", down)
        self.assertIn("CIO-C001", down, "transitively, through the calculation")
        self.assertTrue(any(n.startswith("scorecard:business_quality.dimensions[0]") for n in down))
        self.assertIn("specialists/financials.md:5", down, "the report line citing the calculation")
        self.assertNotIn("FIN-C004", down)
        sc = [n for n in g["inputs"] if n.startswith("scorecard:") and "Returns" in n]
        self.assertEqual(cg.fact_inputs(g, sc), ["FIN-C001", "FIN-C002", "FIN-C005"])

    def test_cycles_are_found(self):
        write_ledger(self.dir / "specialists" / "financials_ledger.csv", [
            claim("FIN-C001", "CALCULATION", "1", "FIN-C002"), claim("FIN-C002", "CALCULATION", "2", "FIN-C001")])
        self.assertTrue(cg.build(self.dir, write=False)["errors"]["cycles"])

    def test_the_verifier_samples_the_facts_a_conclusion_rests_on(self):
        rows = [claim("FIN-C001", "FACT", "1,000"), claim("FIN-C002", "FACT", "250"),
                claim("FIN-C003", "CALCULATION", "25%", "FIN-C002 / FIN-C001")]
        rows += [claim("FIN-C%03d" % i, "FACT", "12,345") for i in range(10, 22)]
        write_ledger(self.dir / "specialists" / "financials_ledger.csv", rows)
        picked = [r["claim_id"] for r in verify.sample(self.dir, "financials", n=4)]
        self.assertEqual(len(picked), 4)
        self.assertTrue({"FIN-C001", "FIN-C002"} <= set(picked),
                        "the conclusion cites a calculation; the facts under it are checked first, not left to chance")

    def test_what_is_built_on_a_corrected_claim_must_be_reviewed_by_its_owner(self):
        g = cg.build(self.dir, write=False)
        todo = verify.unreviewed(self.dir, g, "financials", ["FIN-C001"])
        self.assertEqual(todo, ["FIN-C003 (built on FIN-C001)"])
        cio = verify.unreviewed(self.dir, g, "cio", ["FIN-C001"])
        self.assertIn("CIO-C001 (built on FIN-C001)", cio)
        self.assertTrue(any(x.startswith("scorecard:") for x in cio), "the scorecard input is the CIO's to review")
        prop = verify.propagation_path(self.dir, "financials")
        prop.parent.mkdir(parents=True, exist_ok=True)
        prop.write_text("claim,dependent,action,reason\nFIN-C001,FIN-C003,unaffected,\n", encoding="utf-8")
        self.assertEqual(verify.unreviewed(self.dir, g, "financials", ["FIN-C001"]), ["FIN-C003 (built on FIN-C001)"],
                         "a row without its reason does not count")
        prop.write_text("claim,dependent,action,reason\nFIN-C001,FIN-C003,updated,recomputed: 25.0%\n", encoding="utf-8")
        self.assertEqual(verify.unreviewed(self.dir, g, "financials", ["FIN-C001"]), [])




import datetime as dt  # noqa: E402
import outcomes  # noqa: E402


class TestOutcomeLoop(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="eqr-out-")) / "research"
        self.run = self.root / "companies" / "ACME" / "runs" / "20260101T090000Z"
        (self.run / "cio").mkdir(parents=True)
        rl.write_json(self.run / rl.RUN_MANIFEST, {"run_id": "20260101T090000Z", "ticker": "ACME", "company": "Acme Ltd",
                                                   "exchange": "NSE", "research_cutoff": "2026-01-01",
                                                   "methodology_version": "3.1.0", "currency": "INR"})
        self.sc = {"run_id": "20260101T090000Z", "ticker": "ACME", "assessment_status": "complete", "as_of_date": "2026-01-01",
                   "price": {"value": 1000}, "verdict": "BUY", "primary_layer": "Layer 1 — Bedrock Compounder",
                   "business_quality": {"final": 70}, "investment_attractiveness": {"final": 66}, "hurdle_rate": 0.12,
                   "decision_triggers": {"buy_below": 900, "strong_buy_below": None, "avoid_above": 1400},
                   "next_review_due": "2026-06-30",
                   "predictions": [
                       {"id": "P1", "statement": "Close >= 1100 on 2026-06-30", "metric": "price", "comparator": ">=",
                        "threshold": 1100, "unit": "INR", "period": "2026-06-30", "resolution_source": "price",
                        "due": "2026-06-30", "probability": 0.6, "claim_ids": []},
                       {"id": "P2", "statement": "FY2027 revenue growth >= 12%", "metric": "revenue_growth",
                        "comparator": ">=", "threshold": 12, "unit": "%", "period": "FY2027",
                        "resolution_source": "results_xbrl", "due": "2026-06-30", "probability": 0.8, "claim_ids": []},
                       {"id": "P3", "statement": "No dilution", "metric": "other:dilution", "comparator": "event",
                        "resolution_rule": "hit if shares up at most 2%", "resolution_source": "filing",
                        "due": "2027-12-31", "probability": 0.7, "claim_ids": []}]}
        rl.write_json(self.run / "cio" / "scorecard.json", self.sc)
        self.prices = {}

    def tearDown(self):
        shutil.rmtree(self.root.parent, ignore_errors=True)

    def quote(self, ticker, day):
        close = self.prices.get((ticker, day.isoformat()))
        return {"close": close, "trade_date": day.isoformat(), "url": "https://nse/x.csv", "sha256": "ab" * 32} \
            if close is not None else None

    def test_a_decision_is_recorded_without_touching_the_run(self):
        before = sorted(p.name for p in self.run.rglob("*"))
        dec, preds = outcomes.record_decision(self.run)
        self.assertEqual((dec["ticker"], dec["verdict"], dec["buy_below"]), ("ACME", "BUY", 900))
        self.assertEqual([p["structured"] for p in preds], ["Y", "Y", "Y"])
        self.assertEqual(sorted(p.name for p in self.run.rglob("*")), before, "the run is only read")
        outcomes.record_decision(self.run)
        self.assertEqual(len(outcomes.read_rows(self.root / "outcomes" / "decisions.csv")), 1, "re-recording replaces")

    def test_the_watch_says_why_a_rerun_is_due(self):
        outcomes.record_decision(self.run)
        self.prices[("ACME", "2026-07-15")] = 880
        rows = outcomes.watch(self.root, dt.date(2026, 7, 15), self.quote)
        reasons = " ".join(rows[0]["reasons"])
        self.assertIn("buy_below 900", reasons)
        self.assertIn("review date 2026-06-30 reached", reasons)
        self.assertIn("P1, P2", reasons)
        self.assertTrue((self.root / "outcomes" / "WATCH.md").exists())
        self.prices[("ACME", "2026-07-16")] = 250
        rows = outcomes.watch(self.root, dt.date(2026, 7, 16), self.quote)
        self.assertTrue(any("splits and bonuses" in n for n in rows[0]["notes"]), "a 4x move is flagged, not trusted")

    def test_price_predictions_resolve_by_script_and_the_rest_wait_for_evidence(self):
        outcomes.record_decision(self.run)
        self.prices[("ACME", "2026-06-30")] = 1150
        done, waiting = outcomes.resolve(self.root, dt.date(2026, 7, 1), self.quote)
        self.assertEqual([(r["id"], r["outcome"], r["resolved_by"]) for r in done], [("P1", "hit", "script")])
        self.assertIn("NSE close 1150", done[0]["evidence"])
        self.assertEqual([p["id"] for p in waiting], ["P2"], "a results prediction waits for the CIO; P3 is not due")
        with self.assertRaises(SystemExit):
            outcomes.record(self.root, "20260101T090000Z", "P2", "miss", "9.1", "")
        outcomes.record(self.root, "20260101T090000Z", "P2", "miss", "9.1", "CIO-C014 (FY2027 results)")
        rows = outcomes.due(self.root, "ACME", dt.date(2026, 12, 31), before_run="20270101T000000Z")
        self.assertEqual({p["id"]: (p["resolution"] or {}).get("outcome") for p in rows}, {"P1": "hit", "P2": "miss"})

    def test_score_reports_brier_buckets_and_the_verdict(self):
        outcomes.record_decision(self.run)
        outcomes.record(self.root, "20260101T090000Z", "P1", "hit", "1150", "close")
        outcomes.record(self.root, "20260101T090000Z", "P2", "miss", "9.1", "results")
        self.prices[("ACME", "2026-10-01")] = 1200
        log = self.root / "CALIBRATION_LOG.md"
        log.write_text("# Calibration Log\n\nkept\n", encoding="utf-8")
        out = outcomes.score(self.root, dt.date(2026, 10, 1), self.quote, log)
        self.assertAlmostEqual(out["brier"], ((0.6 - 1) ** 2 + (0.8 - 0) ** 2) / 2)
        self.assertEqual([b["n"] for b in out["buckets"]], [0, 0, 0, 1, 1])
        v = out["verdicts"][0]
        self.assertEqual(v["judged"], "right", "a BUY that returned 20 % in 9 months beat the pro-rata hurdle")
        text = log.read_text(encoding="utf-8")
        self.assertIn("kept", text)
        self.assertIn(outcomes.LOG_BEGIN, text)
        outcomes.score(self.root, dt.date(2026, 10, 1), self.quote, log)
        self.assertEqual(log.read_text(encoding="utf-8").count(outcomes.LOG_BEGIN), 1, "the block is replaced, not added")

    def test_predictions_must_be_resolvable_and_one_due_within_the_review(self):
        p = self.run / "cio" / "scorecard.json"
        sc = json.loads(p.read_text())
        errs = []
        res = rl.Result("x")
        rl._validate_prediction_structure({"id": "P9", "comparator": "about"}, "P9", res)
        errs += res.errors
        res = rl.Result("x")
        rl._validate_prediction_structure({"comparator": "event", "resolution_source": "filing"}, "P8", res)
        errs += res.errors
        res = rl.Result("x")
        rl._validate_prediction_structure({"comparator": "between", "threshold": [5], "resolution_source": "price",
                                           "metric": "price", "unit": "INR", "period": "x"}, "P7", res)
        errs += res.errors
        self.assertTrue(any("comparator must be one of" in e for e in errs))
        self.assertTrue(any("resolution_rule" in e for e in errs))
        self.assertTrue(any("[low, high]" in e for e in errs))
        sc["next_review_due"] = "2026-03-31"
        res = rl.Result("x")
        rl._validate_decision_outputs(sc, res)
        self.assertTrue(any("on or before next_review_due" in e for e in res.errors), res.errors)




import entities  # noqa: E402


def item(t, fields, unit="a1", page=10):
    return {"type": t, "fields": fields, "unit": unit, "page": page, "quote": ""}


class TestEntityGraph(unittest.TestCase):
    def test_names_merge_only_when_they_are_the_same_entity(self):
        c = entities.canonical
        self.assertEqual(c("XYZ Private Limited"), c("M/s. XYZ Pvt. Ltd."))
        self.assertEqual(c("XYZ (P) Ltd"), c("XYZ Pvt Ltd"))
        self.assertEqual(c("Nxtra Data Limited (Subsidiary, S. No 6)"), c("Nxtra Data Ltd"))
        self.assertEqual(c("Mr. Sunil Bharti Mittal"), c("Sunil Bharti Mittal"))
        self.assertEqual(c("A & B Ltd"), c("A and B Limited"))
        self.assertNotEqual(c("Bharti Airtel (India) Ltd"), c("Bharti Airtel Ltd"), "a word in brackets is kept")

    def test_cin_and_formerly_merge_close_names_are_only_listed(self):
        g = entities.EntityGraph()
        g.add(item("related_party", {"name": "Nxtra Data Limited U72200DL2013PLC254747", "relationship": "Subsidiary"}), "AR-FY2025", "AR", 2025)
        g.add(item("subsidiary_or_associate", {"name": "Nxtra Data Ltd (CIN U72200DL2013PLC254747)", "relationship": "subsidiary"}), "AR-FY2026", "AR", 2026)
        g.add(item("related_party", {"name": "Airtel Digital Limited (formerly known as Wynk Limited)", "relationship": "Fellow subsidiary"}), "AR-FY2026", "AR", 2026)
        g.add(item("rpt_transaction", {"party": "Wynk Limited", "nature": "services", "amount_current": "12"}), "AR-FY2026", "AR", 2026)
        g.add(item("related_party", {"name": "Bharti Telemedia Limited", "relationship": "Subsidiary"}), "AR-FY2026", "AR", 2026)
        g.add(item("related_party", {"name": "Bharti Telemedia Limitd", "relationship": "Subsidiary"}), "AR-FY2026", "AR", 2026)
        g.finish()
        nx = [k for k in g.entities if k.startswith("nxtra")]
        self.assertEqual(len(nx), 1, "the same CIN is one entity")
        self.assertEqual(len(g.entities[nx[0]]["appearances"]), 2)
        ad = g.key_of(entities.canonical("Wynk Limited"))
        self.assertEqual(ad, entities.canonical("Airtel Digital Limited"), "a printed 'formerly' joins the two names")
        self.assertEqual({a["type"] for a in g.entities[ad]["appearances"]}, {"related_party", "rpt_transaction"})
        near = g.near_matches()
        self.assertTrue(any("telemedia" in a and "telemedia" in b for a, b, _ in near), "a typo is listed to confirm")
        self.assertEqual(len([k for k in g.entities if "telemedia" in k]), 2, "and never merged")

    def test_flags_are_leads_for_the_specialists(self):
        g = entities.EntityGraph()
        g.add(item("related_party", {"name": "Alpha Ltd", "relationship": "Subsidiary"}), "AR-FY2024", "AR", 2024)
        g.add(item("related_party", {"name": "Alpha Ltd", "relationship": "Associate"}), "AR-FY2025", "AR", 2025)
        g.add(item("related_party", {"name": "Beta Ltd", "relationship": "Joint venture"}), "AR-FY2025", "AR", 2025)
        g.add(item("rpt_transaction", {"party": "Gamma Pvt Ltd", "nature": "purchase", "amount_current": "50"}), "AR-FY2025", "AR", 2025)
        g.add(item("guarantee", {"beneficiary": "Delta Ltd", "amount": "100"}), "AR-FY2025", "AR", 2025)
        g.finish()
        flags = {(k, f.split(" (")[0].split(" in FY")[0]) for k, f in g.flags([{"event_id": "E001", "date": "2025-01-01",
                                                                             "entities": "Beta Limited", "event": "JV formed"}])}
        text = " | ".join("%s: %s" % kf for kf in flags)
        self.assertIn("alpha ltd: relationship changes from subsidiary", text)
        self.assertIn("beta ltd: first listed as a related party or group entity", text)
        self.assertIn("gamma pvt ltd: related-party transaction", text, "a counterparty missing from that year's list")
        self.assertIn("delta ltd: loan, guarantee or investment to an entity with no disclosed relationship", text)
        self.assertIn("beta ltd: named in event E001", text)
        md = g.markdown("R1", "head", [])
        self.assertIn("### Alpha Ltd", md)
        self.assertIn("`[AR-FY2025 a1 p.10]`", md, "every appearance cites its page")


if __name__ == "__main__":
    unittest.main()
