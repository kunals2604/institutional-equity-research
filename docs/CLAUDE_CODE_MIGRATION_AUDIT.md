# Claude Code Migration Audit

**Audit date:** 2026-10-12
**Branch:** `claude-code-migration` (created from `main` @ `8beb994`)
**Auditor:** Claude Code (Opus 5.5), acting as research-systems architect
**Scope:** every tracked file in the repository plus the untracked `research/companies/BAJFINANCE/raw_financials.md` (read only; left untouched and uncommitted).

This document records what the pre-migration system did well, what failed, and why the replacement architecture looks the way it does. Every failure claim below cites the file and line or a reproducible search so it can be checked.

---

## 0. Repository state before migration

| Item | Finding |
|---|---|
| Branch / remote | `main`, tracking `origin` = `github.com/kunals2604/institutional-equity-research` |
| Working tree | Clean except untracked `research/companies/BAJFINANCE/` (one Screener-style data paste). Preserved as-is. |
| `.gitignore` | Absent. Nothing was being excluded, so no research output was accidentally ignored. |
| Commits | 4: init, framework, TVS Motor V1, Bharti Airtel + "master CIO report" |
| Claude Code | 2.1.296 (VS Code extension, native binary). User setting `"model": "opus"`, which resolves to `claude-opus-5-5`. |
| Python | 3.9.6, so validation scripts avoid 3.10+ syntax. |
| Empty files | `README.md` (0 lines), `companies/_template/COMPANY_BRIEF.md` (0 lines) |

Governing documents: `MASTER_RESEARCH_FRAMEWORK.md` (2,654 lines, read in full), `PROJECT_INSTRUCTIONS.md` (249), `agents/README.md` (20), `agents/cio/master_cio.md` (337), nine `agents/specialists/*.md` (273–348 each, all read in full), and ten `.agents/agents/*.md` Antigravity wrappers (71–266).

Research outputs: TVSMOTOR (9 specialist reports + final, 5,210 lines) and BHARTIARTL (9 + final + raw data, 5,946 lines). Both final reports were read in full. Specialist reports were audited with targeted reads and reproducible searches; the searches are listed in §5.

---

## 1. What the original framework does well (preserved)

1. **The four-layer idea is right.** The framework's central rule, "analyze all four lenses first, classify second" (`MASTER_RESEARCH_FRAMEWORK.md` §0), is the strongest design decision in the repo. It guards directly against anchoring on an archetype. It is kept and made enforceable.
2. **The two scores are separate.** §7–8 keep Business/Opportunity Quality apart from Current Investment Attractiveness, with worked examples (95/48, 75/89, and so on). This distinction is preserved word for word in spirit.
3. **Coverage checklists are deep.** §§11–49 cover annual-report deep dives, promise-to-delivery tracking, resignations, the Graham net-net test (including "do not mechanically interpret"), reverse valuation, and sector playbooks for banks, NBFCs, manufacturing and IT. These are thorough and are kept as the research specification.
4. **Fact and inference are kept apart.** The six-tag vocabulary (FACT / MANAGEMENT STATEMENT / CALCULATION / ESTIMATE / INFERENCE / JUDGMENT) already existed. Only its enforcement was missing.
5. **Several specialist ideas are strong.** These are kept in the new agents:
   - Moat specialist: "Brand awareness ≠ moat", "market share ≠ moat", the 11-question mechanism test, and the "affection vs. incarceration" switching-cost test.
   - Special-situations specialist: catalyst tiers (Hard / Probable / Soft / Narrative-only), and the rule that a catalyst needs a value-closing mechanism.
   - Management specialist: management quality, governance quality and promise delivery are scored as three separate pillars.
   - Filings specialist: a five-tier trustworthiness classification, and "do not label trustworthy because of an unmodified opinion" (implied).
   - Valuation specialist: a mandatory reverse DCF, and an explicit expectations classification (Pessimistic → Euphoric).
   - Bear-case specialist: the hidden-assumption audit, the permanent-loss vs. temporary-volatility distinction, and the failure tree.
6. **Execution is continuous.** The "do not stop between phases" rule addresses a real failure mode of agentic research. It is kept, but stated once instead of in eleven places.
7. **Behavioral rules are sound.** §57 says not to bias toward buying, to say plainly when a business is average, and not to force every company into the compounder frame. These are kept.

---

## 2. Instructions that remain valuable but needed correction

| Instruction | Problem | Correction |
|---|---|---|
| Layer-specific "Score: X/100" (§§1–4) | No anchors, and nothing says whether the score measures *fit* or *attractiveness* | Layer-fit score on an anchored 0–100 scale that explicitly excludes price; a separate current-price assessment for each plausible layer |
| §5 "Four-Layer Comparative Assessment" | The heading at line 390 is immediately followed by the SME block (lines 391–644). The comparative table sits *inside* the SME section, so the document structure is broken. | Restored the comparative section; moved SME to its own section |
| SME Research Mode (§5, §9 Phase 4, "FINAL SME OVERRIDE") | Treats SME companies as **Layer 4 by default** and says *not* to spend equal effort on Layers 1–3. This contradicts the framework's own analyze-before-classifying rule. | Replaced with **SME Enhanced-Scrutiny Mode**: all four layers are still evaluated, plus mandatory governance, dilution, liquidity and exit tests and an attractiveness cap tied to exit liquidity |
| §50 "Final Weighted Scorecard" | Mixes quality categories (moat, governance) with price categories (valuation, market expectations, risk/reward) into **one** weighted number, which creates a third, undefined score. Bharti's final report produced "75.73 / 100" this way. | Removed. Two separate scorecards with fixed dimensions, weights and anchors (`methodology/SCORING.md`) |
| Verdict vocabulary | The framework lists 7 verdicts (§53). `master_cio.md` lists a *different* 6 with its own numeric thresholds (MoS > 35 %, IRR > 18 %) that appear nowhere in the framework. TVS used "REDUCE / SELL", which is in neither list. | One canonical verdict list with a documented mapping from scores to verdict; overrides must be justified |
| Layer 3 label | `PROJECT_INSTRUCTIONS.md:68`, `agents/README.md:20`, `master_cio.md` and every specialist wrapper call Layer 3 "Cyclical / Event-Driven / **Special Situation / Deep Value**". The framework calls it "Cyclical / Event-Driven Opportunity". The label drifted at the source. | Canonical names in one place (`.claude/skills/investment-constitution/SKILL.md`), mirrored in code constants and enforced by tests |

---

## 3. Agent definitions: vagueness, overlap, duplication

### 3.1 Three copies of every agent

Every role existed in up to three places:
- `agents/specialists/<x>.md` (the mandate),
- `.agents/agents/<x>.md` (an Antigravity wrapper that **re-lists the full section structure**),
- section lists repeated again inside `agents/cio/master_cio.md` and `.agents/agents/cio.md`.

The CIO itself had two divergent definitions: `master_cio.md` (25 phases) and `.agents/agents/cio.md` (17 steps plus waves). Any edit to one copy silently diverged from the others.

### 3.2 Overlapping mandates (the same question owned by several agents)

| Question | Owned by (old) | Consequence |
|---|---|---|
| Promise → delivery tracking | `management.md` §2 & §5–6 **and** `concalls.md` §4–7 | Two promise databases with different delivery scales (Yes/Partial/No vs. 6-level) |
| Pricing power and moat evidence | `industry.md` §10–11 **and** `moat.md` §4, 7 | Duplicate moat verdicts |
| SOTP | `valuation.md` §11 **and** `special_situations.md` §9 | Two SOTP values (TVS: ₹2,736 in valuation; special situations used a different TVS Credit framing) |
| Forensic accounting | `financials.md` §10 **and** `filings.md` §12 **and** `bear_case.md` §5 | Triple coverage, no single owner |
| Bull/base/bear | `industry.md` §18, `valuation.md` §14, `bear_case.md` §16 | Three probability sets |

**Fix:** each question now has exactly one owner, and the others reference it via the crosswalk or CIO follow-up. Promise→delivery goes to `concalls`. `management` covers integrity, incentives, capital allocation and governance, and *uses* delivery evidence only as a cross-check. Pricing power goes to `industry` as economic evidence, and the moat verdict goes to `moat`. SOTP mechanics go to `valuation`. Whether a value-realization mechanism exists goes to `special-situations`.

### 3.3 Company-specific content inside generic agents

- `agents/specialists/industry.md:175–184` hard-codes an "Automotive / Two-Wheeler Deep Dive" naming TVS, Bajaj, Hero, Eicher, Apache, Jupiter, Raider and iQube.
- `bear_case.md:126` uses an EV/automotive example as a standard attack vector.
- Specialist files link with machine-specific absolute paths (`file:///Users/kunalsingla/...`), which break on any other machine and point to the *agent definition* rather than the report.

### 3.4 Prompt style

The old prompts are long but mostly *descriptive* (lists of topics and section headers) rather than *procedural*. They say what a report must contain, not how to establish that a claim is true, how to handle conflicting sources, or when to stop and record uncertainty. Every specialist repeated the same ~60 lines of boilerplate (runtime inputs, `mkdir`, continuous execution, a scope-prohibition list). The new definitions put shared rules in one constitution and spend each agent's prompt on **method** for that domain.

---

## 4. The orchestration design itself caused correlated errors

`.agents/agents/cio.md` ran specialists in **three dependent waves**. Wave 2 (moat, valuation) read Wave 1. Wave 3 (bear-case, special-situations) read everything. Each specialist file also had a mandatory "Reconciliation with existing specialist reports" section.

Consequences:
- **Anchoring.** The moat specialist inherited the financials specialist's ROCE framing, and the valuation specialist inherited growth narratives. Errors propagated instead of being caught independently. Example: the 38.1 % standalone ROCE appears 14 times across TVS reports, but nothing shows any agent recomputed it independently.
- **Groupthink bear case.** The bear-case agent attacked other agents' *conclusions* rather than building an independent case from primary sources.
- **Antigravity-only mechanics.** `invoke_subagent`, `"Workspace": "inherit"`, `subagent: false` and the JSON `Subagents` array are not Claude Code constructs. The orchestration could not run under Claude Code as written.

**Fix:** all nine specialists launch concurrently from the CIO parent session through the native Agent tool. They are barred from reading each other's reports (or prior-run conclusions) until their initial reports are complete. Cross-examination is the CIO's job (Stage 3), with targeted specialist follow-ups.

---

## 5. What the TVS Motor and Bharti Airtel runs reveal

### 5.1 The four canonical layers were silently redefined (TVS: severe)

`research/companies/TVSMOTOR/final_report.md:309–333` presents a "Four Investment Layers Taxonomy" that is *not* the framework's:

| Layer | Framework (canonical) | TVS final report |
|---|---|---|
| 1 | Bedrock Compounder | "Deep Value / Cyclical / Special Situation" |
| 2 | High-Growth Business | "Capital-Intensive Low-Moat Commodity" |
| 3 | Cyclical / Event-Driven | "Enduring High-ROIC Economic Compounder" (**PRIMARY**) |
| 4 | Venture-Style / Optionality | "Structural Growth at Excessive Price (Valuation Multiple Headwind / Trap)" |

The final classification "Layer 3: Enduring High-ROIC Compounder (Trading in Layer 4 Valuation Trap)" (`:394`) is therefore meaningless under the framework. It also turns Layer 4 into a *price* judgment, which is exactly the conflation the framework forbids. No CIO quality check caught it. Bharti used the correct names (`BHARTIARTL/final_report.md:139–156`), so nothing enforced consistency; it held or failed by chance.

### 5.2 Four-layer analysis was not actually done four times

- TVS: no layer-fit scores at all. The table assigns "Secondary / Rejected / PRIMARY / CURRENT STATUS".
- Bharti: fit is given as adjectives ("EXTREMELY HIGH", "MODERATE", "LOW"), with no scores despite framework §§1–4 requiring X/100.
- **Specialists never addressed the layers.** `grep -c "Layer [1-4]"` returns **0** for all nine TVS specialist reports, and 0 for six of nine Bharti reports. The CIO had no layer-specific evidence to adjudicate, so "four independent analyses" were written in a single pass at synthesis time.

### 5.3 Inferences and estimates reported as facts

- `TVSMOTOR/industry.md:557`: "EV Dilution on Blended EBITDA Margins `[FACT]`… the iQube generates ~4–6%". TVS does not disclose a segment margin for iQube. The same report (`:580`) lists the unsubsidized iQube margin as an *unresolved question*. The CIO then resolved Contradiction 3 "in favor of margin dilution" (`final_report.md:109–110`) on the strength of this estimate.
- `TVSMOTOR/moat.md:9`: ROCE "38.1 % in FY26 (`[FACT]`)". This is a calculation, and its formula and inputs are never shown.
- `TVSMOTOR/final_report.md:49`: "Unprecedented cross-vertical market share gains across Indian automotive history" in a row tagged `[FACT]`.
- `final_report.md:149–150`: "35–45 % dealer ROIC and < 1 % annual dealer churn … (`[FACT]`)" and "passing 12 price hikes without volume attrition (`[FACT]`)". No source is given, and dealer ROIC is not a disclosed figure.
- `BHARTIARTL/final_report.md:140`: "Wide, **structurally impenetrable** moat … `[FACT]`".

### 5.4 Spurious precision and unsupported probabilities

- Fair values to the paisa (₹2,736.49, ₹2,128.50), margin of safety "−52.99 %", and a "consensed base fair value" of ₹2,600 with no stated method for "consensing".
- TVS scenario probabilities of 25 / 55 / 20 (`bear_case.md:489–491`) are justified only by narrative, with no reference class.
- Bharti: "We assign an **80 % probability** that the ₹8,414 Cr demand will be permanently set aside" (`final_report.md:132`), with no base rate for appellate outcomes.
- TVS's reverse DCF "Impossibility Verdict" (`final_report.md:259`) rests on a chain of assumptions (12.5 % WACC, 5 % terminal growth, an assumed ₹1,30,000 FY36 ASP) yet is described as "**mathematically disproves**" (`:56`).

### 5.5 Untraceable sources

- **0 URLs** in all 20 reports (`grep -c -E "https?://"` = 0 everywhere).
- Page, note or table locators: 0–5 per report. Most reports have none.
- "Sources" sections are generic category lists. Example: `TVSMOTOR/financials.md` §22 lists "Audited Annual Reports & Financial Statements (FY15 – FY25)" and "Screener.in" with no document titles, dates, pages or retrieval dates.
- The same financials source list labels FY26 data "Unaudited Financial Results", while the final report presents FY26 figures as `[FACT]` and claims resolution "via audited statutory facts" (`final_report.md:389`).
- Raw data files have no provenance: `BHARTIARTL/raw_financials.md` has no source, retrieval date or row labels on several rows. The untracked `BAJFINANCE/raw_financials.md` is titled "AUDITED CONSOLIDATED FINANCIAL BASELINE" but contains unaudited quarterly data in what looks like an aggregator layout, with no source line.

### 5.6 Inconsistent numbers across reports for the same company

| Item | Value A | Value B |
|---|---|---|
| iQube FY26 volume | 371,000 units (`TVSMOTOR/industry.md:22`) | ">450k units FY26" (`final_report.md:197`) |
| "17.2 % ROCE" | *Standalone* ROCE in **FY21** (`moat.md:9`) | *Consolidated* ROCE **now** (`final_report.md:73, 101–102`) |
| WACC | 11.0 % (moat; used for the "ROCE spread" in `final_report.md:38, 50`) | 12.5 % (reverse DCF in `final_report.md:252`) |

The final report used *two different costs of capital* in the same document without reconciling them. The "17.2 %" contradiction may stem from one number being reused in two meanings. Either way, the CIO "resolved" it rather than detecting it.

### 5.7 Contradictions were "resolved" rather than adjudicated

- Contradiction 5 in TVS pits "Consensus: 50x P/E justified" against Valuation. "Consensus" is not a specialist position and is never sourced. It is a strawman.
- Each resolution picks a side in prose. None records what the CIO independently verified, the evidence for each side, or the confidence level.

### 5.8 Business quality was confused with price, and scope crept

- TVS Layer 4 = "Structural Growth at Excessive Price" puts a valuation judgment inside an archetype.
- The TVS final report gives position-sizing and trading advice ("reduce position size by 50 % to 75 %", "short leg in a market-neutral pairs trade against long Bajaj Auto", `final_report.md:341–346`). This sits outside the framework's verdict vocabulary and rests on comparative work about Bajaj that was never done.
- Bharti's "TOTAL FINAL WEIGHTED SCORE 75.73 / 100" blends quality and price categories (see §2).

### 5.9 Decorative scores

- TVS Business Quality 84 and Investment Attractiveness 24 have no dimension breakdown. Nothing explains why 84 rather than 78 or 90.
- Bharti's 87 / 50 has a category table, but the 87 appears *as one row inside the table* that also feeds the weighted total. That is circular.
- Neither run states the score's confidence, what prevents a higher score, or which evidence would change it.

### 5.10 Language that should not survive review

A count of unqualified superlatives across the 20 TVS and Bharti reports (`grep -o -i -h -E "unassailable|impenetrable|pristine|flawless|insurmountable|decisively fails|mathematically (proves|disproves|impossible)|unprecedented|impossible to replicate|zero earnings|fortress" | wc -l`): **78 occurrences**. Breakdown: "pristine" 17, "flawless" 16, "impenetrable" 12, "unprecedented" 8, "insurmountable" 8, "unassailable" 6, "mathematically impossible/disproves" 5, "zero earnings" (inflation) 2. The original prompts never prohibited such language, and the CIO never challenged it.

---

## 6. Answers to the audit questions

1. **What the framework does well:** see §1. The four-layer principle, the two-score separation, deep checklists, the epistemic tag vocabulary, and several strong specialist tests.
2. **Valuable instructions to keep:** framework §§0–4 checklists, §§11–49 coverage, §§57–59 behavioral rules and master check, the specialist tests listed in §1.5.
3. **Vague, repetitive, overlapping or ineffective definitions:** see §3. There were three copies of each agent, four overlapping ownership areas, company-specific hard-coding, and descriptive rather than procedural prompts.
4. **Duplicated instructions at risk of diverging:** the layer names (diverged), verdict lists (diverged), CIO definitions (two versions), section structures (wrapper vs. mandate), and the continuous-execution boilerplate (11 copies).
5. **TVS execution failures:** §§5.1–5.9. Layers redefined, no layer evidence from specialists, inferences as facts, inconsistent numbers, no traceable sources, out-of-scope trading advice.
6. **Insufficiently controlled claims, numbers, assumptions and citations:** §§5.3–5.6. There was no claim ledger, no locators, no formulas, no price timestamp linked to a source, and two WACCs in one report.
7. **Were all four archetypes evaluated independently?** **No.** Specialists produced no layer evidence (§5.2). The CIO wrote the four lenses in one pass. TVS redefined the lenses entirely.
8. **Scoring rules needing calibration:** layer scores without anchors, a final weighted score mixing quality and price, verdict thresholds that differed between documents, no confidence, and no caps for governance or accounting failures (§§2, 5.9).
9. **What had to be redesigned for Claude Code:** agent registration (`.claude/agents/` with valid frontmatter), orchestration (native parallel Agent calls from the parent session; the Antigravity waves were removed), a skill-based entry point, a shared constitution preloaded via the `skills:` frontmatter field, deterministic validation scripts, and a run archive.
10. **Final architecture:** see §7.

---

## 7. The architecture being implemented and why

> **Update (v2.1, same day):** after Parts XI–XVI of the brief were received, run IDs became UTC (`YYYYMMDDTHHMMSSZ`), the manifest became `run_manifest.json`, the scoreboard was reduced to 11 columns written only by `scripts/finalize_run.py`, and git publishing moved to `scripts/git_publish.py`. See `docs/FRAMEWORK_CHANGES.md` v2.1.0. The table below is the original design rationale.

| Component | Path | Why |
|---|---|---|
| Investment constitution (canonical layer definitions, tags, evidence rules, crosswalk format) | `.claude/skills/investment-constitution/SKILL.md` | One source of truth. It is **preloaded** into every specialist via the `skills:` frontmatter field (verified to exist in Claude Code 2.1.296), so no agent depends on the CIO's summary. |
| CIO role | `.claude/agents/cio.md` | A main-thread agent definition. `/research-company` makes the current session the CIO. No nested CIO subagent is ever spawned (subagents cannot spawn subagents, and nesting would lose orchestration). |
| Nine specialists | `.claude/agents/{financials,filings,management,industry,moat,concalls,valuation,bear-case,special-situations}.md` | One operative definition each, `model: opus`, no Agent tool, write access only to their own run paths |
| One-command workflow | `.claude/skills/research-company/SKILL.md` | User-invoked only (`disable-model-invocation: true`) so the expensive workflow never auto-triggers |
| Methodology depth | `methodology/SCORING.md`, `EVIDENCE_STANDARDS.md`, `INVESTOR_LENSES.md`, `REPORT_CONTRACTS.md` | Read on demand, so it does not load into every session |
| Research spec | `MASTER_RESEARCH_FRAMEWORK.md` (revised, not replaced) | Preserves the valuable checklists. Fixes the SME override, the broken §5, the mixed scorecard and verdict drift. Changes are logged in `docs/FRAMEWORK_CHANGES.md`. |
| Global rules | `PROJECT_INSTRUCTIONS.md` (rewritten) | Concise and authoritative, with no layer-label drift |
| Session memory | `CLAUDE.md` (compact) | Pointers and non-negotiables only |
| Archive | `research/companies/<TICKER>/runs/<RUN_ID>/…` with `manifest.json`, per-specialist claim ledgers, CIO outputs, QC record | Timestamped, reproducible runs. Legacy TVS and Bharti outputs were moved (via `git mv`, history kept) to `runs/legacy-antigravity-v1/` with a notice. |
| Scoreboard | `COMPANY_SCOREBOARD.csv` | Updated only by `scripts/update_scoreboard.py`, which refuses runs that did not pass QC. Legacy runs are deliberately **not** loaded, because they fail QC (§5). |
| Deterministic checks | `scripts/*.py` (stdlib only) + `tests/` | Enforce canonical layer names, the tag vocabulary, claim-ID traceability, scorecard arithmetic, verdict mapping and completion barriers. They catch the TVS-class failures mechanically instead of relying on prompts. |
| Old definitions | `archive/antigravity/` | Kept for reference and marked **non-operative** |

**What is not technically enforced (stated honestly):** Claude Code cannot restrict which files a subagent *reads* on a per-agent basis without custom hooks. Specialist independence in Stage 1 is enforced by instruction, by an attestation in each report header, and by CIO audit, not by a sandbox. Likewise, "specialists must not run git" is an instruction; it is not blocked, because blocking it would also block the CIO.
