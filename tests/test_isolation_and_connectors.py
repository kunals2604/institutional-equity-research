"""Tests for session isolation, the context and efficiency sensors, the network denies, the librarian's browser,
Chrome snapshots (scripts/browser.py, fetch_source.py --snapshot) and the free connectors (scripts/connectors.py).
No test touches the network: transports are replaced by canned replies."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_driver  # noqa: E402
import browser  # noqa: E402
import connectors  # noqa: E402
import fetch_source  # noqa: E402
import netfetch  # noqa: E402
import reading_audit  # noqa: E402
import research_lib as rl  # noqa: E402
import test_v31_reading_stage as t31  # noqa: E402

MINI_PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 10 10]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n")


def instructions(*files):
    return {"type": "attachment", "attachment": {"type": "instructions", "files": [
        {"path": p, "type": t} for p, t in files]}}


class TestContextSensor(unittest.TestCase):
    project = (str(rl.ROOT / "CLAUDE.md"), "Project")

    def test_project_claude_md_alone_is_clean(self):
        self.assertEqual(reading_audit.context_breaches([instructions(self.project)]), [])

    def test_auto_memory_user_claude_md_and_hooks_are_breaches(self):
        mem = str(Path.home() / ".claude/projects/x/memory/MEMORY.md")
        user = str(Path.home() / ".claude/CLAUDE.md")
        hook = {"type": "attachment", "attachment": {"type": "hook_success", "hookName": "SessionStart:startup",
                                                     "content": "You have superpowers"}}
        got = reading_audit.context_breaches([instructions(self.project, (mem, "AutoMem"), (user, "User")), hook])
        self.assertTrue(any("MEMORY.md (AutoMem)" in g for g in got), got)
        self.assertTrue(any("CLAUDE.md (User)" in g for g in got), got)
        self.assertTrue(any(g.startswith("hook output SessionStart:startup") for g in got), got)


class TestEfficiencySensor(unittest.TestCase):
    def entries(self):
        def use(i, name, inp):
            return {"type": "assistant", "message": {"id": "m%d" % i, "usage": {"input_tokens": 10, "output_tokens": 5,
                    "cache_read_input_tokens": 1000 * i}, "content": [{"type": "tool_use", "id": "t%d" % i, "name": name,
                                                                       "input": inp}]}}

        def res(i, text, err=False):
            return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t%d" % i,
                                                              "content": text, "is_error": err}]}}
        rows = []
        for i in range(3):                                   # the same range read three times: repeated
            rows += [use(i, "Read", {"file_path": "/r/a.md", "offset": 1, "limit": 50}), res(i, "x" * 10)]
        rows += [use(10, "Bash", {"command": "grep -n foo big.md"}), res(10, "y" * 5000),
                 use(11, "Bash", {"command": "grep -n foo big.md"}), res(11, "y"),
                 use(12, "Bash", {"command": "python3 scripts/validate_report.py r.md"}), res(12, "ok"),
                 use(13, "Bash", {"command": "python3 scripts/validate_report.py r.md"}), res(13, "ok"),
                 use(14, "Bash", {"command": "curl https://x"}), res(14, "Permission to use Bash has been denied", True),
                 use(15, "Read", {"file_path": "/r/missing.md"}), res(15, "File does not exist.", True)]
        return rows

    def test_repeats_failures_and_denials(self):
        e = reading_audit.efficiency(self.entries())
        self.assertEqual(e["repeated_reads"], ["/r/a.md [1+50] x3"])
        self.assertEqual(e["repeated_commands"], ["grep -n foo big.md x2"], "routine checks are exempt")
        self.assertEqual(len(e["denied"]), 1)
        self.assertEqual(len(e["failed"]), 1)
        self.assertTrue(e["largest_results"][0].startswith("5000 chars: Bash"))

    def test_a_write_between_reads_resets_the_count(self):
        rows = self.entries()[:4] + [{"type": "assistant", "message": {"id": "w", "content": [
            {"type": "tool_use", "id": "tw", "name": "Edit", "input": {"file_path": "/r/a.md"}}]}}] + self.entries()[4:6]
        self.assertEqual(reading_audit.efficiency(rows)["repeated_reads"], [])


class TestIsolationAndTools(t31.EngineCase):
    def test_every_headless_command_is_isolated(self):
        eng = self.engine()
        act = {"agent": "critical-reader", "model": "opus", "effort": "xhigh", "chunks": [], "role": "critical",
               "launch": "L001", "prompt": "p"}
        agentic = eng.command(agent_driver.reader_assignment(self.fx.dir, act), "sid", "prompt", False, 0)
        oneshot = agent_driver.Assignment(kind="reader", agent="critical-reader", model="opus", effort="high", prompt="p",
                                          label="L1", tools=[], allowed=[], denied=[], dirs=[], check=lambda: [],
                                          oneshot=True, system_file=self.fx.tmp / "sys.md")
        for cmd in (agentic, eng.command(oneshot, "sid", "", False, 0)):
            i = cmd.index("--setting-sources")
            self.assertEqual(cmd[i + 1], "project")
            settings = json.loads(cmd[cmd.index("--settings") + 1])
            self.assertTrue(settings["disableAllHooks"])
            self.assertFalse(settings["autoMemoryEnabled"])
            self.assertIn("--strict-mcp-config", cmd)
        self.assertEqual(agent_driver.child_env().get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "1")
        with mock.patch.object(agent_driver.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout="", returncode=0)
            agent_driver.probe_usage("claude")
        self.assertIn("--setting-sources", run.call_args[0][0], "the usage probe is isolated too")

    def test_agents_cannot_run_network_clients(self):
        denies = agent_driver.shell_denies()
        for c in ("curl", "wget", "nc", "ssh", "scp", "rsync"):
            self.assertIn("Bash(%s:*)" % c, denies)

    def test_only_the_librarian_gets_the_browser(self):
        eng = self.engine()
        lib = eng.command(agent_driver.librarian_assignment(self.fx.dir, "p"), "sid", "p", False, 0)
        cfg = Path(lib[lib.index("--mcp-config") + 1])
        server = json.loads(cfg.read_text())["mcpServers"]["playwright"]
        self.assertIn(agent_driver.PLAYWRIGHT_MCP, server["args"], "the server version is pinned")
        self.assertIn("--isolated", server["args"])
        allowed = lib[lib.index("--allowedTools") + 1:lib.index("--disallowedTools")]
        self.assertEqual(sorted(t for t in allowed if t.startswith("mcp__")), sorted(agent_driver.BROWSER_TOOLS))
        self.assertNotIn("mcp__playwright__browser_evaluate", allowed)
        self.assertFalse(any(t.startswith("mcp__") for t in lib[lib.index("--tools") + 1].split(",")),
                         "--tools carries built-in tools only")
        act = {"agent": "critical-reader", "model": "opus", "effort": "xhigh", "chunks": [], "role": "critical",
               "launch": "L001", "prompt": "p"}
        reader = eng.command(agent_driver.reader_assignment(self.fx.dir, act), "sid", "p", False, 0)
        self.assertNotIn("--mcp-config", reader)
        self.assertFalse(any(t.startswith("mcp__") for t in reader))

    def test_the_engine_stops_when_a_session_carries_outside_context(self):
        a = agent_driver.specialist_assignment(self.fx.dir, "filings", "You are the filings specialist for run %s." % self.fx.run_id)
        report = self.fx.dir / "specialists" / "filings.md"
        a.check = lambda: [] if report.exists() and "DONE" in report.read_text() else ["filings.md does not exist yet"]
        with self.env(FAKE_UNITS="2"), mock.patch.object(
                reading_audit, "context_breaches", return_value=["instruction file MEMORY.md (AutoMem)"]):
            eng = self.engine()
            with agent_driver.Session(eng, "specialists"):
                agent_driver.run_jobs(eng, [(a, agent_driver.open_job(eng, a.agent, a.kind))], 1)
        self.assertTrue(eng.stop and "context from outside the brief" in eng.stop, eng.stop)
        self.assertTrue(any("ISOLATION" in m for m in self.logs), self.logs)
        job = json.loads((self.fx.dir / "engine" / "jobs.json").read_text())["jobs"][-1]
        self.assertEqual(job["sessions"][0]["attempts"][0]["context_breaches"], ["instruction file MEMORY.md (AutoMem)"])


class TestBrowser(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-browser-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.chrome = self.tmp / "chrome"
        self.chrome.write_text("#!/bin/sh\nfor a in \"$@\"; do case \"$a\" in --print-to-pdf=*) cp \"%s\" \"${a#--print-to-pdf=}\";; "
                               "--dump-dom) printf '<html><head><title>Results</title></head><body>%%0300d</body></html>' 0;; esac; done\n"
                               % (self.tmp / "page.pdf"))
        self.chrome.chmod(0o755)
        (self.tmp / "page.pdf").write_bytes(MINI_PDF)
        env = mock.patch.dict(os.environ, {"EQR_CHROME": str(self.chrome), "EQR_BROWSER_MIN_INTERVAL": "0"})
        env.start()
        self.addCleanup(env.stop)

    def test_snapshot_and_dom(self):
        res = browser.snapshot("https://example.com/ir", str(self.tmp / "out.pdf"), sleep=lambda s: None)
        self.assertEqual(res["pages"], 1)
        self.assertTrue((self.tmp / "out.pdf").read_bytes().startswith(b"%PDF"))
        res = browser.dump_dom("https://example.com/ir", str(self.tmp / "out.html"), sleep=lambda s: None)
        self.assertGreater(res["bytes"], 200)

    def test_refuses_non_public_urls(self):
        for u in ("file:///etc/passwd", "http://localhost/x", "http://192.168.1.1/"):
            with self.assertRaises(browser.BrowserError):
                browser.snapshot(u, str(self.tmp / "x.pdf"))

    def test_error_pages_are_recognised_with_curly_quotes(self):
        self.assertTrue(netfetch.ERROR_PAGE_RE.search("Access Forbidden. You don’t have permission to access this page"))

    def test_fetch_source_snapshot_is_cached_logged_and_reused(self):
        run = self.tmp / "run"
        run.mkdir()
        a = fetch_source.render(run, "https://example.com/ir", "financials", "IR page", "snapshot")
        self.assertTrue(a["path"].exists())
        b = fetch_source.render(run, "https://example.com/ir", "valuation", "IR page", "snapshot")
        self.assertEqual(b["path"], a["path"])
        self.assertIn("reused", b["name"])
        self.assertIsNone(fetch_source.prior_success(run, "https://example.com/ir"),
                          "a rendered copy is not reused as the downloaded document")


class TestConnectors(unittest.TestCase):
    def setUp(self):
        self.run = Path(tempfile.mkdtemp(prefix="eqr-conn-"))
        self.addCleanup(shutil.rmtree, self.run, True)

    def logged(self):
        import csv
        with (self.run / "source_retrievals.csv").open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_registry_is_complete_and_verified(self):
        rows = connectors.registry()
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for r in rows:
            self.assertIn(r["access"], ("free", "free-key", "manual"), r["id"])
            self.assertTrue(r.get("what") and r.get("agents"), r["id"])
            self.assertTrue(set(r["agents"]) <= set(rl.AGENT_NAMES), r["id"])
            if r.get("landing"):
                self.assertTrue(r["landing"].startswith("https://"), r["id"])
            if r["access"] == "manual":
                self.assertIn("2026-10-23", r["notes"], "a manual source says when and how access failed")
        for adapter in ("tri", "mospi", "gdelt", "openfda", "kanoon", "transcribe"):
            self.assertTrue(callable(getattr(connectors, adapter)))

    def test_tri_merges_years_logs_and_reuses(self):
        replies = [[{"Date": "29 Dec 2023", "TotalReturnsIndex": "100.0", "NTR_Value": "99.0"}],
                   [{"Date": "02 Jan 2024", "TotalReturnsIndex": "101.5", "NTR_Value": "100.4"},
                    {"Date": "01 Jan 2024", "TotalReturnsIndex": "101.0", "NTR_Value": "100.0"}]]
        with mock.patch.object(connectors, "http_post", side_effect=[(200, json.dumps(r).encode()) for r in replies]) as post:
            p = connectors.tri(self.run, "valuation", "NIFTY 500", "01-Dec-2023", "05-Jan-2024")
            self.assertEqual(post.call_count, 2, "one request per calendar year")
            body = json.loads(post.call_args_list[0][0][1])
            self.assertEqual(json.loads(body["cinfo"])["name"], "NIFTY 500")
        lines = p.read_text().splitlines()
        self.assertEqual(lines[1:], ["2023-12-29,100.0,99.0", "2024-01-01,101.0,100.0", "2024-01-02,101.5,100.4"])
        self.assertEqual(self.logged()[-1]["method"], "connector:tri")
        with mock.patch.object(connectors, "http_post", side_effect=AssertionError("not called")):
            self.assertEqual(connectors.tri(self.run, "cio", "NIFTY 500", "01-Dec-2023", "05-Jan-2024"), p)

    def test_mospi_reads_the_event_stream_and_logs_failures(self):
        ok = 'event: message\ndata: {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"{\\"data\\":[{\\"index\\":\\"206.7\\"}]}"}]}}\n'
        with mock.patch.object(connectors, "http_post", return_value=(200, ok.encode())):
            p = connectors.mospi(self.run, "industry", "get_data", {"dataset": "CPI", "filters": {"year": "2024"}})
        self.assertEqual(json.loads(p.read_text())["data"][0]["index"], "206.7")
        bad = 'data: {"jsonrpc":"2.0","id":1,"result":{"isError":true,"content":[{"type":"text","text":"bad filter"}]}}\n'
        with mock.patch.object(connectors, "http_post", return_value=(200, bad.encode())):
            with self.assertRaises(connectors.ConnectorError):
                connectors.mospi(self.run, "industry", "get_data", {"dataset": "CPI", "filters": {}})
        self.assertTrue(self.logged()[-1]["error"])
        with self.assertRaises(connectors.ConnectorError):
            connectors.mospi(self.run, "industry", "drop_tables", {})

    def test_gdelt_and_openfda(self):
        with mock.patch.object(connectors, "http_get", return_value=b'{"articles":[{"url":"https://x"}]}') as get:
            p = connectors.gdelt(self.run, "historian", '"Acme Ltd"', "2018-01-01", "2018-12-31")
            self.assertIn("startdatetime=20180101000000", get.call_args[0][0])
        self.assertIn("1 articles", self.logged()[-1]["validation"])
        self.assertTrue(p.exists())
        with mock.patch.object(connectors, "http_get", return_value=b'{"meta":{"results":{"total":3}},"results":[]}'):
            connectors.openfda(self.run, "scuttlebutt", "drug/enforcement", 'recalling_firm:"Acme"')
        self.assertIn("3 results", self.logged()[-1]["validation"])
        with self.assertRaises(connectors.ConnectorError):
            connectors.openfda(self.run, "scuttlebutt", "../../etc", "x")

    def test_kanoon_needs_a_token_and_respects_the_cap(self):
        with mock.patch.dict(os.environ, {"EQR_KANOON_TOKEN": ""}), \
                mock.patch.object(connectors.shutil, "which", return_value=None):
            with self.assertRaises(connectors.ConnectorError) as cm:
                connectors.kanoon(self.run, "filings", "search", query="Acme")
            self.assertIn("api.indiankanoon.org", str(cm.exception))
        with mock.patch.dict(os.environ, {"EQR_KANOON_TOKEN": "t"}), \
                mock.patch.object(connectors, "KANOON_RUN_CAP_INR", 0.6), \
                mock.patch.object(connectors, "http_post", return_value=(200, b'{"found":"1","docs":[]}')) as post:
            connectors.kanoon(self.run, "filings", "search", query="Acme")
            self.assertEqual(post.call_args[0][2]["Authorization"], "Token t")
            with self.assertRaises(connectors.ConnectorError):         # Rs 0.50 spent; another search would pass 0.60
                connectors.kanoon(self.run, "filings", "search", query="Other")


if __name__ == "__main__":
    unittest.main()
