#!/usr/bin/env python3
"""The `reading_transport` switch set to `batch`: one-shot reads through the Message Batches API at half the list price.

  python3 scripts/batch_transport.py pending RUN_DIR        # batches submitted and not yet collected

What changes, and what does not. A one-shot read (one chunk, no tools: the message carries the chunk and its rendered
pages) is the same request either way. With `plan` the engine sends it through the `claude` CLI on the owner's
subscription; with `batch` it sends the same system prompt and the same message, at the model and effort the policy pins,
as a one-request batch, waits for it, and hands the answer to the same code: the same part file, the same reading check,
the same fix rounds (each fix a fresh call on the same blocks), the same fallback to the agentic reader. Each call is
written as a transcript in the run (`_cache/engine/batch/<session>.jsonl`) in the CLI's format, so the reading audit and
the usage records read it unchanged.

It spends real money: it needs ANTHROPIC_API_KEY, and the engine refuses the switch without one. The rates are half the
API list prices (Opus 5.5 $2 / $10 per million input / output tokens, Sonnet 5.5 $1 / $5, Haiku 5.5 $0.05 / $0.25;
cache writes 1.25 and reads 0.1 times input). Most batches finish within an hour; the API allows 24. A submitted batch is
recorded before it is waited for, so an interrupted engine collects it rather than paying for it twice. Tested against a
fake API only, until the owner turns it on (docs/V4_DEFECT_REGISTER.md).
"""

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

API = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
VERSION = "2026-10-21"
MODEL_IDS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
# Batch rates, USD per million tokens (half the list price): input, output.
BATCH_PRICE = {"opus": (2.0, 10.0), "sonnet": (1.0, 5.0), "haiku": (0.05, 0.25)}
MAX_TOKENS = 64000                  # asynchronous, so no HTTP timeout applies; a short cap would truncate a chunk's items
POLL_S = 30
LIMIT_S = 24 * 3600


class BatchError(Exception):
    pass


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise BatchError("reading_transport is batch, which reads through the API with real money: set ANTHROPIC_API_KEY, "
                         "or set the switch back to plan (python3 scripts/manifest.py RUN_DIR mode reading_transport plan)")
    return key


def http(method: str, url: str, key: str, body: Optional[dict] = None, raw: bool = False):
    """One API call (standard library only, as the project requires)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "x-api-key": key, "anthropic-version": VERSION, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise BatchError("%s %s: HTTP %s %s" % (method, url, exc.code, exc.read().decode("utf-8", "replace")[:300]))
    except (urllib.error.URLError, OSError) as exc:
        raise BatchError("%s %s: %s" % (method, url, exc))
    return text if raw else json.loads(text)


def model_id(alias: str) -> str:
    return MODEL_IDS.get(alias, alias)


def params(model: str, effort: str, system: str, messages: List[dict]) -> dict:
    """The request a one-shot read sends: the system prompt cached (it is identical for every chunk of a role), thinking
    left adaptive (these models' default), effort set explicitly (Opus 5.5 would otherwise run at medium)."""
    return {"model": model_id(model), "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": messages, "output_config": {"effort": effort}}


def cost(usage: dict, model: str) -> float:
    i, o = BATCH_PRICE.get(model, BATCH_PRICE["opus"])
    tokens_in = (usage.get("input_tokens", 0) + 1.25 * usage.get("cache_creation_input_tokens", 0)
                 + 0.1 * usage.get("cache_read_input_tokens", 0))
    return round((tokens_in * i + usage.get("output_tokens", 0) * o) / 1e6, 6)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def history(transcript: Path) -> List[dict]:
    """The conversation so far, from the call's own transcript: what a fix or a resume in the same session continues."""
    out = []
    if transcript.exists():
        for line in transcript.read_text(encoding="utf-8").splitlines():
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("type") == "user":
                out.append({"role": "user", "content": o["message"]["content"]})
            elif o.get("type") == "assistant":
                out.append({"role": "assistant", "content": [b for b in o["message"]["content"] if b.get("type") == "text"]})
    return out


def pending_path(run_dir: Path, sid: str) -> Path:
    return run_dir / "_cache" / "engine" / "batch" / ("%s.pending.json" % sid)


def call(run_dir: Path, model: str, effort: str, system_file: Path, kind: str, line: str, sess: dict, log=print,
         http_fn: Callable = http, sleep: Callable = time.sleep, poll_s: float = POLL_S) -> dict:
    """One turn of a one-shot read as a one-request batch. `line` is the stream-json user message the CLI would get.
    Returns what Engine.run_process returns, so the engine's loop treats both transports alike."""
    key = api_key()
    transcript = Path(sess["transcript"])
    transcript.parent.mkdir(parents=True, exist_ok=True)
    content = json.loads(line)["message"]["content"]
    fresh = kind in ("start", "fixfresh")
    messages = ([] if fresh else history(transcript)) + [{"role": "user", "content": content}]
    if fresh and transcript.exists():
        transcript.unlink()                          # a fresh call starts its own conversation
    pend = pending_path(run_dir, sess["session_id"])
    state = json.loads(pend.read_text(encoding="utf-8")) if pend.exists() else None
    if state and state.get("kind") != kind:
        state = None
    if not state:                                    # recorded before waiting, so a crash collects it, never pays twice
        body = {"requests": [{"custom_id": sess["session_id"], "params": params(model, effort, system_file.read_text(encoding="utf-8"), messages)}]}
        batch = http_fn("POST", API + "/v1/messages/batches", key, body)
        state = {"batch_id": batch["id"], "kind": kind, "submitted_at": now(), "model": model}
        pend.parent.mkdir(parents=True, exist_ok=True)
        pend.write_text(json.dumps(state), encoding="utf-8")
        with transcript.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "timestamp": now(), "sessionId": sess["session_id"], "effort": effort,
                                "transport": "batch", "message": {"role": "user", "content": content}}) + "\n")
        log("batch %s submitted (%s at %s)" % (batch["id"], model_id(model), effort))
    started = time.time()
    while True:
        batch = http_fn("GET", API + "/v1/messages/batches/%s" % state["batch_id"], key)
        if batch.get("processing_status") == "ended":
            break
        if time.time() - started > LIMIT_S:
            return {"rc": 1, "timed_out": True, "result": None, "pid": None, "suspended": False}
        sleep(poll_s)
    found = None
    for row in http_fn("GET", batch["results_url"], key, raw=True).splitlines():
        if row.strip():
            r = json.loads(row)
            if r.get("custom_id") == sess["session_id"]:
                found = r["result"]
    pend.unlink()
    if not found or found.get("type") != "succeeded":
        why = (found or {}).get("type", "missing") + (": %s" % json.dumps((found or {}).get("error"))[:200] if found else "")
        return {"rc": 1, "timed_out": False, "pid": None, "suspended": False,
                "result": {"type": "result", "subtype": "error_batch", "is_error": True, "result": "batch %s" % why}}
    msg = found["message"]
    with transcript.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "timestamp": now(), "sessionId": sess["session_id"], "effort": effort,
                            "transport": "batch", "batch_id": state["batch_id"], "message": {"id": msg.get("id"), "model": msg.get("model"), "role": "assistant",
                                        "content": msg.get("content", []), "usage": msg.get("usage", {}),
                                        "stop_reason": msg.get("stop_reason")}}) + "\n")
    text = "".join(b.get("text", "") for b in msg.get("content", []) if b.get("type") == "text")
    refused = msg.get("stop_reason") == "refusal"
    return {"rc": 0 if not refused else 1, "timed_out": False, "pid": None, "suspended": False,
            "result": {"type": "result", "subtype": "refusal" if refused else "success", "is_error": refused,
                       "result": ("refused: %s" % json.dumps(msg.get("stop_details"))) if refused else text,
                       "num_turns": 1, "total_cost_usd": cost(msg.get("usage", {}), model), "transport": "batch"}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pending").add_argument("run_dir")
    a = ap.parse_args(argv)
    if a.cmd == "pending":
        for p in sorted((Path(a.run_dir) / "_cache" / "engine" / "batch").glob("*.pending.json")):
            print(p.name, p.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
