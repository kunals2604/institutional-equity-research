---
name: switches
description: The depth switches and presets — what each buys, what turning it down loses, what it may cost in confidence, and the estimated cost of each preset. Read-only. Use when the owner asks how deep a run is, how to go deeper or what a run will cost.
argument-hint: "[<switch name> | --profile <lean|standard|deep|max>]"
---

# /switches

**Arguments:** `$ARGUMENTS`

1. With no argument: `python3 scripts/switches.py show`, then point to `docs/SWITCHES.md` (generated from
   `config/switches.json`, so it cannot drift).
2. With a switch name: `python3 scripts/switches.py explain <name>`.
3. With `--profile <p>`: `python3 scripts/orchestrate.py plan --profile <p>` (the steps it runs and the estimate; writes
   nothing).
4. Say how far to trust each estimate, as the presets file states it (lean is an unmeasured target; standard and deep
   are estimates). No switch caps a verdict or a confidence level: a lighter run states what it did not do.
