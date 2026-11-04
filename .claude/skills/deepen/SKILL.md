---
name: deepen
description: A child run of an existing run at the same cutoff with deeper switches — it inherits Stage 0 and redoes everything after it at the new depth, leaving the parent untouched. Spends research capacity. Runs only when the owner invokes it.
argument-hint: "<RUN_ID> [--profile deep|max] [--set name=value ...]"
disable-model-invocation: true
---

# /deepen

**Arguments:** `$ARGUMENTS`

1. Show the parent's Depth Disclosure (`python3 scripts/switches.py disclosure <PARENT_RUN_DIR>`) and the
   estimate for the target preset (`python3 scripts/orchestrate.py plan --profile <p>`). Ask the owner to confirm the
   spend before anything is created.
2. `python3 scripts/new_run.py --deepen <RUN_ID> --profile <p> [--set ...]`. It refuses a child that is not deeper on at
   least one switch, or lighter on any, or at another cutoff (that is a refresh). Report what it inherited (files, MB,
   paths rewritten) from its message.
3. Continue the child as a run: `/research-company --resume <TICKER> <CHILD_RUN_ID>`, following
   `python3 scripts/orchestrate.py next <CHILD_RUN_DIR>`.
