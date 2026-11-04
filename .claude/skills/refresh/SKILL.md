---
name: refresh
description: A child run of an existing run at a later cutoff, after new results — it inherits only the downloaded documents, rebuilds everything else for the new date, and leaves the parent untouched. Spends research capacity. Runs only when the owner invokes it.
argument-hint: "<RUN_ID> [--cutoff YYYY-MM-DD] [--profile ...]"
disable-model-invocation: true
---

# /refresh

**Arguments:** `$ARGUMENTS`

1. Say what has happened since the parent's cutoff that warrants a refresh (new results, a filing, a price move) and the
   estimate for the parent's preset (`python3 scripts/orchestrate.py plan --profile <its preset>`). Ask the owner to
   confirm the spend.
2. `python3 scripts/new_run.py --refresh <RUN_ID> [--cutoff <date, default today>] [--profile ...]`. Unchanged filings
   are not downloaded again; the verified facts of finished runs reach it through the warehouse (`corpus/facts/`).
3. Continue the child as a run: `/research-company --resume <TICKER> <CHILD_RUN_ID>`.
