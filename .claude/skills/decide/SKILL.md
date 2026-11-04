---
name: decide
description: Record the owner's own decision on a finished run — buy, add, hold, trim, exit, pass or wait — with the owner's reason, apart from the system's verdict. Use only when the owner states a decision.
argument-hint: "<RUN_DIR> --action buy|add|hold|trim|exit|pass|wait --reason \"...\" [--price P] [--size S]"
---

# /decide

**Arguments:** `$ARGUMENTS`

1. Show the run's one-page Decision Memo: `python3 scripts/decide.py memo <RUN_DIR>`.
2. The decision and its reason are the owner's. If either is missing from the arguments, ask for it; never infer it
   from the verdict, and never suggest one.
3. `python3 scripts/decide.py record <RUN_DIR> --action <a> --reason "<the owner's words>" [--price P] [--size S]`. It
   appends to `research/outcomes/owner_decisions.csv`; where the owner's call differs from the verdict, both stand.
