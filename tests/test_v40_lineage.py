"""v4.0 Step 8: child runs (`new_run.py --deepen` and `--refresh`, scripts/lineage.py).

A child reuses its parent's work by copy and never refers to it, so the parent stays as it was (CLAUDE.md rule 5) and
the child's agents read only their own run. Measured on a scratch copy of the BAJFINANCE run (2026-11-04): 499 files and
853 mentions of the parent rewritten for a deepen, 349 files for a refresh, the parent byte-identical afterwards.
"""

import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import lineage  # noqa: E402
import new_run  # noqa: E402
import orchestrate as oc  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import switches  # noqa: E402

PARENT = "20261023T164051Z"


def make_parent(root: Path, profile="standard", cutoff="2026-10-23") -> Path:
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        new_run.main(["--ticker", "ACME", "--company", "Acme Industries Limited", "--exchange", "NSE", "--segment", "main",
                      "--fy-end", "03-31", "--isin", "INE000A01011", "--cutoff", cutoff, "--profile", profile,
                      "--run-id", PARENT, "--root", str(root)])
    run = root / out.getvalue().strip()
    rel = "research/companies/ACME/runs/%s" % PARENT
    (run / "research_brief.md").write_text("# Brief\nRun ID: %s\nPrice ₹100 [CIO-C001]; segment mix [CIO-C002].\n" % PARENT,
                                           encoding="utf-8")
    (run / "engine").mkdir(exist_ok=True)
    (run / "engine" / "identity.md").write_text("ACME, run %s\n" % PARENT, encoding="utf-8")
    (run / "engine" / "key_questions.md").write_text("1. Can margins hold?\n2. Is growth durable?\n3. Is the balance sheet safe?\n",
                                                     encoding="utf-8")
    (run / "engine" / "jobs.json").write_text("{}", encoding="utf-8")
    for rel_file, text in (("corpus/DOCUMENT_MAP.md", "| AR FY2026 | `%s/_cache/cio/ar.pdf` |\n" % rel),
                           ("corpus/STRUCTURED.md", "structured\n"), ("corpus/events.csv", "event_id\n"),
                           ("corpus/EVENTS.md", "events\n"), ("corpus/reading/COVERAGE.md", "read\n"),
                           ("corpus/facts/FACTS.md", "facts\n"), ("_cache/text/index.json", json.dumps({"p": rel + "/_cache/cio/ar.pdf"})),
                           ("_cache/index/raw/nse_results_annual.json", "[]"), ("_cache/financials/scratch.md", "a specialist's own"),
                           ("_cache/engine/canaries/financials.json", "{}"), ("_cache/reading/x.md", "reading work")):
        p = run / rel_file
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    pdf = run / "_cache" / "cio" / "ar.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 " + PARENT.encode() + b" binary")
    with (run / "source_retrievals.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["retrieved_at_utc", "author", "name", "url", "http_status", "local_path", "sha256"])
        w.writerow(["t", "cio", "AR FY2026", "https://x/ar.pdf", "200", "_cache/cio/ar.pdf", "s"])
        w.writerow(["t", "financials", "a page", "https://x/p.html", "200", "_cache/financials/scratch.md", "s"])
    with (run / "cio" / "cio_ledger.csv").open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rl.ledger_columns(), quoting=csv.QUOTE_ALL, extrasaction="ignore")
        for cid in ("CIO-C001", "CIO-C002", "CIO-C050"):
            w.writerow({"claim_id": cid, "author": "cio", "claim": "claim %s" % cid, "tag": "FACT"})
    rl.update_json(run / rl.RUN_MANIFEST, lambda m: m.update(
        price={"value": 100.0, "timestamp": "close of 23-Oct-2026", "claim_id": "CIO-C001"}, sector_modules=["nbfc"],
        status="complete"))
    return run


def digest(path: Path) -> dict:
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()
            and not p.name.endswith(".lock")}


class LineageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="eqr-lineage-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.parent = make_parent(self.root)
        self.before = digest(self.parent)

    def child(self, *args, run_id="20261104T120000Z"):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = new_run.main(list(args) + ["--run-id", run_id, "--root", str(self.root)])
            except SystemExit as exc:
                rc = exc.code
        return rc, (self.root / out.getvalue().strip()) if rc == 0 else None, err.getvalue()

    def test_a_deepen_inherits_stage_0_and_rewrites_every_mention_of_the_parent(self):
        rc, run, _ = self.child("--deepen", PARENT, "--profile", "deep")
        self.assertEqual(rc, 0)
        m = rl.load_json(run / rl.RUN_MANIFEST)
        self.assertEqual((m["parent_run"]["run_id"], m["parent_run"]["relation"]), (PARENT, "deepen"))
        self.assertEqual(m["research_cutoff"], "2026-10-23")
        self.assertEqual(m["price"]["value"], 100.0)
        self.assertEqual(m["sector_modules"], ["nbfc"])
        self.assertEqual((m["company"], m["isin"]), ("Acme Industries Limited", "INE000A01011"))
        self.assertEqual(m["switches"]["reading"], "on")
        for f in ("corpus/DOCUMENT_MAP.md", "corpus/STRUCTURED.md", "corpus/EVENTS.md", "_cache/cio/ar.pdf",
                  "_cache/text/index.json", "_cache/index/raw/nse_results_annual.json", "engine/identity.md",
                  "engine/key_questions.md"):
            self.assertTrue((run / f).exists(), f)
        for f in ("corpus/reading/COVERAGE.md", "corpus/facts/FACTS.md", "_cache/financials/scratch.md",
                  "_cache/engine/canaries/financials.json", "_cache/reading/x.md", "engine/jobs.json"):
            self.assertFalse((run / f).exists(), "%s is redone at the new depth, or belongs to the parent's agents" % f)
        texts = [p for p in run.rglob("*") if p.is_file() and p.suffix in (".md", ".csv", ".json") and p.name != rl.RUN_MANIFEST
                 and p.name != "inherited.csv"]
        self.assertEqual([str(p) for p in texts if PARENT in p.read_text(encoding="utf-8") and "inherited from run" not in
                          p.read_text(encoding="utf-8")], [])
        self.assertIn("runs/20261104T120000Z/_cache/cio/ar.pdf", (run / "corpus/DOCUMENT_MAP.md").read_text(encoding="utf-8"))
        self.assertEqual((run / "_cache/cio/ar.pdf").read_bytes(), (self.parent / "_cache/cio/ar.pdf").read_bytes(),
                         "a binary file is copied as it is")

    def test_the_parent_is_left_exactly_as_it_was(self):
        self.child("--deepen", PARENT, "--profile", "deep")
        self.child("--refresh", PARENT, "--cutoff", "2026-11-04", run_id="20261104T130000Z")
        self.assertEqual(digest(self.parent), self.before)

    def test_a_deepen_takes_only_the_claims_its_inherited_files_rest_on(self):
        _, run, _ = self.child("--deepen", PARENT, "--profile", "deep")
        with (run / "cio" / "cio_ledger.csv").open(encoding="utf-8") as f:
            self.assertEqual([r["claim_id"] for r in csv.DictReader(f)], ["CIO-C001", "CIO-C002"],
                             "CIO-C050 is a later claim, part of the parent's conclusions")

    def test_the_downloads_are_reusable_by_url_and_nothing_else_is(self):
        _, run, _ = self.child("--refresh", PARENT, "--cutoff", "2026-11-04")
        import fetch_source
        hit = fetch_source.prior_success(run, "https://x/ar.pdf")
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1], run / "_cache/cio/ar.pdf")
        self.assertIsNone(fetch_source.prior_success(run, "https://x/p.html"), "an agent's own download is not inherited")

    def test_a_refresh_redoes_everything_for_the_new_cutoff(self):
        rc, run, _ = self.child("--refresh", PARENT, "--cutoff", "2026-11-04")
        self.assertEqual(rc, 0)
        m = rl.load_json(run / rl.RUN_MANIFEST)
        self.assertIsNone(m["price"]["value"])
        self.assertIsNone(m["sector_modules"])
        self.assertEqual(m["profile"], "standard")
        self.assertEqual(m["switches"], rl.load_json(self.parent / rl.RUN_MANIFEST)["switches"])
        self.assertFalse((run / "corpus/DOCUMENT_MAP.md").exists())
        self.assertEqual(oc.next_step(run)["id"], "identity")

    def test_what_a_child_may_not_be(self):
        cases = [(("--deepen", PARENT), "at least one depth switch deeper"),
                 (("--deepen", PARENT, "--profile", "lean"), "lighter"),
                 (("--deepen", PARENT, "--profile", "deep", "--cutoff", "2026-11-04"), "keeps the parent's cutoff"),
                 (("--refresh", PARENT, "--cutoff", "2026-10-01"), "after the parent's"),
                 (("--deepen", "20990101T000000Z", "--profile", "deep"), "no run 20990101T000000Z"),
                 (("--deepen", PARENT, "--refresh", PARENT), "not allowed with")]
        for args, msg in cases:
            rc, _, err = self.child(*args)
            self.assertNotEqual(rc, 0, args)
            self.assertIn(msg, err, args)

    def test_a_replay_has_no_children(self):
        rl.update_json(self.parent / rl.RUN_MANIFEST, lambda m: m.update(replay=True))
        rc, _, err = self.child("--deepen", PARENT, "--profile", "deep")
        self.assertNotEqual(rc, 0)
        self.assertIn("replay", err)

    def test_the_child_is_independent_for_the_audit(self):
        _, run, _ = self.child("--deepen", PARENT, "--profile", "deep")
        calls, _ = ra.independence_patterns("financials", "20261104T120000Z")
        with (run / "engine" / "inherited.csv").open(encoding="utf-8") as f:
            paths = [r["path"] for r in csv.DictReader(f) if "#" not in r["path"]]
        for rel in paths:
            if Path(rel).suffix in (".md", ".csv", ".json"):
                text = (run / rel).read_text(encoding="utf-8")
                self.assertIsNone(calls.search(text.replace("inherited from run %s" % PARENT, "")),
                                  "an inherited file sends an agent to another run: %s" % rel)

    def test_parent_run_is_protected(self):
        import manifest
        self.assertIn("parent_run", manifest.PROTECTED)


class DepthRankTests(unittest.TestCase):
    def test_depth_comes_from_the_presets(self):
        self.assertLess(switches.rank("reading", "off"), switches.rank("reading", "on"))
        self.assertLess(switches.rank("effort", "xhigh"), switches.rank("effort", "max"))
        self.assertLess(switches.rank("history_years", 10), switches.rank("history_years", 15))

    def test_deeper_than_deep_is_not_left_out(self):
        values = switches.resolve("max")["values"]
        self.assertEqual(switches.below(values), [])
        self.assertIn("deepest", switches.disclosure({"profile": "max", "switches": values, "reading_mode": "on"}))

    def test_a_lighter_switch_is_left_out(self):
        values = switches.resolve("standard")["values"]
        self.assertIn("reading", [o["name"] for o in switches.below(values)])

    def test_the_deepen_command_the_disclosure_prints_is_accepted(self):
        self.assertIn("--deepen", switches.deepen_command({"run_id": PARENT}))
        self.assertNotIn("--deepen", switches.registry().get("not_yet_wired", {}))


if __name__ == "__main__":
    unittest.main()
