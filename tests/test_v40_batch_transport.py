"""v4.0 Step 10: the `reading_transport` switch at `batch` (scripts/batch_transport.py).

Against a fake Message Batches API only: the transport spends real money, so it is first run live by the owner. What is
proved here: the request is the one-shot read's (system prompt, message, pinned model and effort), the answer reaches
the same code as a CLI answer, the engine's check-fix-close loop runs unchanged, a crash after submitting collects the
batch instead of paying twice, refusals and errors are failures, and the transcript is one the reading audit reads.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import batch_transport as bt  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402


class FakeAPI:
    """POST /v1/messages/batches, GET the batch (processing, then ended), GET its results as JSONL."""

    def __init__(self, answers, polls=1, crash_after_post=False):
        self.answers = list(answers)       # each: text, or a dict {"stop_reason": ...} or {"error": ...}
        self.polls, self.crash = polls, crash_after_post
        self.batches, self.posts, self.bodies = {}, 0, []

    def __call__(self, method, url, key, body=None, raw=False):
        if method == "POST":
            self.posts += 1
            self.bodies.append(body)
            bid = "msgbatch_%d" % self.posts
            self.batches[bid] = {"left": self.polls, "custom_id": body["requests"][0]["custom_id"],
                                 "answer": self.answers.pop(0), "model": body["requests"][0]["params"]["model"]}
            if self.crash:
                self.crash = False
                bt.pending_path  # the pending record is written by the caller after this returns
                return {"id": bid, "processing_status": "in_progress"}
            return {"id": bid, "processing_status": "in_progress"}
        if url.endswith("/results"):
            bid = url.split("/")[-2]
            b = self.batches[bid]
            ans = b["answer"]
            if isinstance(ans, dict) and "error" in ans:
                res = {"type": "errored", "error": ans["error"]}
            else:
                text = ans if isinstance(ans, str) else ans.get("text", "")
                res = {"type": "succeeded", "message": {
                    "id": "msg_%s" % uuid.uuid4().hex[:8], "model": b["model"], "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                    "stop_reason": ans.get("stop_reason", "end_turn") if isinstance(ans, dict) else "end_turn",
                    "stop_details": ans.get("stop_details") if isinstance(ans, dict) else None,
                    "usage": {"input_tokens": 1000, "cache_creation_input_tokens": 20000, "cache_read_input_tokens": 0,
                              "output_tokens": 3000}}}
            return json.dumps({"custom_id": b["custom_id"], "result": res}) + "\n"
        bid = url.rsplit("/", 1)[-1]
        b = self.batches[bid]
        if self.crash is None:
            raise bt.BatchError("network down")
        if b["left"] > 0:
            b["left"] -= 1
            return {"id": bid, "processing_status": "in_progress"}
        return {"id": bid, "processing_status": "ended", "results_url": "https://api.example/v1/messages/batches/%s/results" % bid}


def line(text, image=False):
    content = [{"type": "text", "text": text}]
    if image:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgo="}})
    return json.dumps({"type": "user", "message": {"role": "user", "content": content}}) + "\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-batch-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        rl.write_json(self.tmp / rl.RUN_MANIFEST, {"run_id": "20261104T150000Z", "switches": {"reading_transport": "batch"}})
        self.system = self.tmp / "system.md"
        self.system.write_text("You read chunks.", encoding="utf-8")
        old = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        self.addCleanup(lambda: os.environ.__setitem__("ANTHROPIC_API_KEY", old) if old is not None else os.environ.pop("ANTHROPIC_API_KEY", None))
        sid = str(uuid.uuid4())
        self.sess = {"session_id": sid, "transcript": str(self.tmp / "_cache" / "engine" / "batch" / ("%s.jsonl" % sid))}

    def call(self, api, kind="start", text="chunk C1", **kw):
        return bt.call(self.tmp, "opus", "high", self.system, kind, line(text, image=True), self.sess, log=lambda m: None,
                       http_fn=api, sleep=lambda s: None, **kw)


class CallTests(Base):
    def test_the_request_is_the_one_shot_read(self):
        api = FakeAPI(['{"type":"chunk_receipt"}'])
        self.call(api)
        p = api.bodies[0]["requests"][0]["params"]
        self.assertEqual(p["model"], "claude-opus-5-5")
        self.assertEqual(p["output_config"], {"effort": "high"})
        self.assertEqual(p["system"][0]["text"], "You read chunks.")
        self.assertEqual(p["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual([b["type"] for b in p["messages"][0]["content"]], ["text", "image"])
        self.assertNotIn("thinking", p, "adaptive by default on these models; budget_tokens would be a 400")

    def test_the_answer_comes_back_as_a_cli_result(self):
        got = self.call(FakeAPI(['{"type":"chunk_receipt"}'], polls=3))
        self.assertEqual((got["rc"], got["timed_out"]), (0, False))
        self.assertEqual(got["result"]["result"], '{"type":"chunk_receipt"}')
        self.assertFalse(got["result"]["is_error"])
        # 1,000 input + 20,000 cache-write tokens x 1.25 at $2/M, 3,000 output at $10/M
        self.assertAlmostEqual(got["result"]["total_cost_usd"], (1000 + 25000) * 2 / 1e6 + 3000 * 10 / 1e6)

    def test_the_transcript_is_one_the_audit_and_the_meter_read(self):
        self.call(FakeAPI(["answer"]))
        entries = [json.loads(l) for l in Path(self.sess["transcript"]).read_text(encoding="utf-8").splitlines()]
        prof = ra.profile(entries)
        self.assertEqual(prof["models"], {"claude-opus-5-5": 1})
        self.assertEqual(prof["efforts"], {"high": 2})
        self.assertIn("chunk C1", ra.prompt_text(entries), "the audit sees the chunk the read was given")
        use = ad.transcript_usage(Path(self.sess["transcript"]))
        self.assertEqual((use["api_turns"], use["output"], use["cache_write"]), (1, 3000, 20000))

    def test_a_crash_after_submitting_collects_instead_of_paying_twice(self):
        api = FakeAPI(["answer"], polls=2)
        api.crash = None                                       # every poll fails: the engine dies while waiting
        with self.assertRaises(bt.BatchError):
            self.call(api)
        self.assertTrue(bt.pending_path(self.tmp, self.sess["session_id"]).exists())
        api.crash = False
        got = self.call(api)
        self.assertEqual(api.posts, 1, "the batch submitted before the crash is the one collected")
        self.assertEqual(got["result"]["result"], "answer")
        self.assertFalse(bt.pending_path(self.tmp, self.sess["session_id"]).exists())

    def test_a_fix_in_the_same_session_carries_the_conversation(self):
        api = FakeAPI(["first answer", "fixed answer"])
        self.call(api)
        self.call(api, kind="fix", text="FIX. E3 is wrong")
        msgs = api.bodies[1]["requests"][0]["params"]["messages"]
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual(msgs[1]["content"][0]["text"], "first answer")

    def test_a_fresh_fix_starts_its_own_conversation(self):
        api = FakeAPI(["first answer", "fixed answer"])
        self.call(api)
        self.call(api, kind="fixfresh", text="chunk C1 then FIX")
        self.assertEqual(len(api.bodies[1]["requests"][0]["params"]["messages"]), 1)

    def test_a_refusal_and_an_error_are_failures(self):
        got = self.call(FakeAPI([{"text": "", "stop_reason": "refusal", "stop_details": {"category": "cyber"}}]))
        self.assertTrue(got["result"]["is_error"])
        self.assertIn("refused", got["result"]["result"])
        got = self.call(FakeAPI([{"error": {"type": "overloaded_error"}}]))
        self.assertTrue(got["result"]["is_error"])
        self.assertEqual(got["rc"], 1)

    def test_no_key_no_call(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        api = FakeAPI(["x"])
        with self.assertRaises(bt.BatchError) as cm:
            self.call(api)
        self.assertIn("real money", str(cm.exception))
        self.assertEqual(api.posts, 0)


class EngineTests(Base):
    def test_the_engine_runs_a_one_shot_read_through_batch_with_its_own_check_and_fix(self):
        part = self.tmp / "part.jsonl"
        api = FakeAPI(["bad line", '{"ok": true}'])
        bt_http = bt.http
        bt.http = api
        self.addCleanup(setattr, bt, "http", bt_http)
        orig = bt.call

        def call(*a, **kw):
            kw.setdefault("sleep", lambda s: None)
            kw["http_fn"] = api
            return orig(*a, **kw)
        bt.call = call
        self.addCleanup(setattr, bt, "call", orig)

        def on_result(kind, text):
            part.write_text(text, encoding="utf-8")

        def message(kind, text):
            return line("chunk C1" if kind in ("start", "fixfresh") else text)

        def check():
            return [] if part.exists() and part.read_text(encoding="utf-8").startswith("{") else ["not JSON"]
        a = ad.Assignment(kind="reader", agent="critical-reader", model="opus", effort="high", prompt="", label="L001",
                          tools=[], allowed=[], denied=[], dirs=[], check=check, oneshot=True, system_file=self.system,
                          message=message, on_result=on_result, fix_builder=lambda errs, fresh=False: "FIX: " + "; ".join(errs),
                          record="job", stage="0b", fix_rounds=2)
        eng = ad.Engine(self.tmp, "", ad.options(), log=lambda m: None)
        self.assertEqual(eng.transport, "batch")
        a.label = eng.new_job(a)["id"]
        self.assertEqual(eng.run(a), "pass")
        self.assertEqual(api.posts, 2, "the start, then one fix")
        rec = eng.get_record(a)
        self.assertTrue(all(s["runner"] == "batch" for s in rec["sessions"]))
        self.assertTrue(all(Path(s["transcript"]).parent == self.tmp / "_cache" / "engine" / "batch" for s in rec["sessions"]))
        self.assertGreater(ad.job_cost(rec["sessions"]), 0)

    def test_without_a_key_the_engine_stops_instead_of_running_on_the_plan(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        a = ad.Assignment(kind="reader", agent="critical-reader", model="opus", effort="high", prompt="", label="L002",
                          tools=[], allowed=[], denied=[], dirs=[], check=lambda: ["x"], oneshot=True, system_file=self.system,
                          message=lambda k, t: line("c"), on_result=lambda k, t: None, record="job", stage="0b")
        eng = ad.Engine(self.tmp, "", ad.options(), log=lambda m: None)
        a.label = eng.new_job(a)["id"]
        self.assertEqual(eng.run(a), "paused")
        self.assertIn("ANTHROPIC_API_KEY", eng.stop)

    def test_the_switch_is_wired(self):
        import switches
        self.assertEqual(switches.registry()["not_yet_wired"], {}, "the release gate needs this list empty")


if __name__ == "__main__":
    unittest.main()
