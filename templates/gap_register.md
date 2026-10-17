# Gap Register — {company} ({ticker}) · run {run_id}

Built by the CIO at the Stage-2 gap-closure loop (`.claude/agents/cio.md`). Sources of gaps:
- every **Partial** or **Not available** row in the specialists' Method Coverage Checklists;
- every *Missing evidence* item;
- every tier-6-only FACT on a decision-relevant claim;
- every unresolved data conflict.

A gap is closed by a specialist follow-up, or declared **unobtainable** only after the alternatives in `methodology/RESEARCH_PLAYBOOK.md` §1a have been tried and logged in `source_retrievals.csv`.

| # | Gap | Owner | Decision relevance (H/M/L) | Closable? | Attempts (follow-up file, sources tried) | Status (Closed / Unobtainable / Accepted-low-relevance) | Effect on confidence |
|---|---|---|---|---|---|---|---|
