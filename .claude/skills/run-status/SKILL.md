---
name: run-status
description: Where a research run is, what it has spent and how to go deeper. Read-only. Use when the owner asks how a run is going, what comes next, or what a run did not do.
argument-hint: "<TICKER> | <RUN_DIR>"
---

# /run-status

**Arguments:** `$ARGUMENTS`

1. Resolve the run: a run directory as given, or for a ticker the newest directory under
   `research/companies/<TICKER>/runs/` (say which you picked, and that `latest_run.txt` points only to finished runs).
2. Run `python3 scripts/orchestrate.py status <RUN_DIR>` and show its output as it is: the current step, the steps done,
   the spend so far (API-equivalent; sleep aborts and retries are not in it), the switches, and the Depth Disclosure with
   the exact deepen command.
3. If the engine is running (`_cache/engine/engine.lock`), say so and show the last lines of
   `_cache/engine/engine.log`. If `engine/early_stop.json` holds an open pause, show the flag and say the run waits for
   the owner: `python3 scripts/orchestrate.py decide-early <RUN_DIR> continue|stop --reason "..."`.
4. Change nothing. Never start a step from this skill.
