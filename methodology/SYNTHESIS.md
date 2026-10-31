# Synthesis — how the final report integrates every piece of evidence (methodology 3.2.0)

The CIO decides; the synthesis pipeline makes sure the decision rests on **all** the evidence the run produced, not on
what one context could hold. In run BHARTIARTL 20261012T132311Z the final report cited a quarter of the specialists'
claims, dropped material findings its own notes recorded (a liquidity gap, a regulator's penalty, an emphasis of matter
restated as an unmodified opinion), left a disagreement between two specialists unadjudicated and stated one number
three ways. Nothing checked any of it. From 3.2.0 the final stage is a pipeline in which every finding has a recorded
fate, and scripts check that nothing material was dropped, mis-cited or restated inconsistently.

## The pipeline (`cio.md` Stage 3)

1. **Registry** (`scripts/synthesis.py registry`, a script): every specialist's Key Findings, crosswalk rows, domain
   conclusions, questions for the CIO, assumptions, missing evidence, checklist gaps and internal conflicts; every ledger
   claim; every numeric conflict, open verification finding and forecast-valuation gap; every reading-stage item (reading
   on) or web-digest item (reading off); every historian event. Each item gets a stable id (`R-…`), the dimensions and
   theme it bears on, and a materiality. Uncited ledger claims and non-material corpus items are grouped into clusters.
2. **Theme analysts** (`theme-analyst`, Opus, one per theme, independent of each other): each reads its slice (and the
   report sections and sources it needs), integrates the evidence, finds where specialists agree because they share a
   source, lists contradiction candidates with both sides, and gives **every item of its slice a disposition**.
3. **Contradictions and follow-ups:** the CIO adjudicates every contradiction candidate in `cio/contradiction_log.md`
   and sends narrow follow-ups to the specialists (Stage 3 follow-ups may read peers' work). The valuation specialist
   re-runs its valuation on the forecasting model here. The registry is then updated and the themes re-run on the delta.
4. **Layer analysts** (`layer-analyst`, Opus, one per layer, independent of each other): every crosswalk row for their
   layer from every specialist, and every theme brief's layer implications → a layer assessment with a proposed fit.
5. **The CIO decides** from a packet of bounded size (`synthesis/CIO_PACKET.md`): variant perception, key debates,
   thesis-disproof, classification, the scorecard inputs (with `key_quantities`), the scorecard, the decision outputs.
6. **Section writers** (`section-writer`, Opus): the evidence sections of the final report from the briefs, faithful to
   the cited evidence; the CIO writes the decision sections. `synthesis.py assemble` builds `cio/final_report.md` with
   the generated **Evidence Integration Register**.
7. **Integration checks** (`synthesis.py integration`, run by `validate_run.py --stage final`) and the auditor's
   **Evidence Integration Audit**.

## Themes

<!-- SYNTHESIS_THEMES:BEGIN -->
```json
{
 "T1": {"title": "Financial and accounting quality",
        "authors": ["financials", "filings"],
        "topics": ["auditor", "accounting", "contingencies", "related_parties", "debt_and_capital", "results_and_segments", "esg"],
        "dimensions": ["BQ4", "BQ5"]},
 "T2": {"title": "Business, industry, moat and ground truth",
        "authors": ["industry", "moat", "scuttlebutt"],
        "topics": [],
        "dimensions": ["BQ1", "BQ2", "BQ3", "BQ8"]},
 "T3": {"title": "Management, governance and capital allocation",
        "authors": ["management", "concalls"],
        "topics": ["governance", "transcripts"],
        "dimensions": ["BQ6", "BQ7"]},
 "T4": {"title": "Valuation, forecasts and expectations",
        "authors": ["valuation", "forecasting"],
        "topics": ["strategy_and_outlook"],
        "dimensions": ["IA1", "IA2", "IA4", "IA5", "IA7", "IA8"]},
 "T5": {"title": "Risks, bear case and special situations",
        "authors": ["bear-case", "special-situations"],
        "topics": ["structure_and_transactions", "other"],
        "dimensions": ["IA3", "IA6"]},
 "T6": {"title": "Group structure, listed subsidiaries and capital",
        "authors": [],
        "topics": ["structure_and_transactions"],
        "dimensions": [],
        "when_modules": ["listed_subsidiaries", "holding_companies"]}
}
```
<!-- SYNTHESIS_THEMES:END -->

T6 runs only when the run's sector modules include a listed-subsidiary or holding-company module; it then owns the
structure items and the special-situations findings on subsidiaries. Every item has exactly one owner theme, which
dispositions it; the other themes it bears on see it as context.

## Materiality

<!-- SYNTHESIS_MATERIALITY:BEGIN -->
```json
{
 "gating_patterns": ["\\bgoing concern\\b", "\\bemphasis of matter\\b", "\\beoms?\\b", "\\bqualified (audit )?opinion\\b",
                     "\\badverse opinion\\b", "\\bdisclaimer of opinion\\b", "\\bmaterial (weakness|uncertainty)\\b",
                     "\\bfraud(ulent)?\\b", "\\bpenalt(y|ies)\\b", "\\bshow[- ]cause\\b", "\\benforcement (action|directorate)\\b",
                     "\\bregulatory action\\b", "\\bembargo\\b", "\\b(payment|loan|debt|bond|covenant|technical) default\\b",
                     "\\bdefaulted on\\b", "\\bcovenant breach\\b", "\\bauditor (resign|resigned|resignation)\\b",
                     "\\bwhistle-?blow", "\\binvestigation (by|into)\\b", "\\binsolven", "\\bdiversion of\\b", "\\bsiphon",
                     "\\b(integrity|conduct) (lapse|concern|issue)", "\\bmisstatement\\b", "\\bprior[- ]period error\\b",
                     "\\brestate(d|ment)\\b.{0,40}\\b(error|misstatement|fraud)\\b", "\\bnon-?operating (credit|gain)s?\\b",
                     "\\blabels? \\W?exceptional\\b", "\\bflatter(s|ed|ing)?\\b", "\\bcontingent[- ]liabilit",
                     "\\brelated[- ]party (transaction|swap|deal)", "\\bpromoter[- ](group|related) (transaction|share swap|deal)",
                     "\\bpromoter-related\\b", "\\b(pledged|encumbered) shares\\b", "\\bshare pledge", "\\bdividend dependence\\b",
                     "\\bliquidity\\b.{0,60}\\b(tight|shortfall|gap|crunch|strain)", "\\bmaturity wall\\b",
                     "\\brefinanc\\w* risk\\b", "\\bdowngraded?\\b", "\\bpermanent[- ](capital )?loss\\b"],
 "gating_negation": "\\b(no|not|nothing|none|never|without|nil)\\b",
 "gating_kinds": ["key_finding", "conclusion", "followup_finding", "missing_evidence", "checklist_gap", "verification"],
 "gating_corpus_types": ["emphasis_of_matter", "material_uncertainty_going_concern", "fraud_reported", "default_or_breach",
                         "penalty_or_noncompliance", "restatement", "auditor_change", "legal_or_regulatory_matter",
                         "ifc_opinion", "secretarial_observation"],
 "material_kinds": ["key_finding", "conclusion", "cio_question", "numeric_conflict", "internal_conflict", "checklist_gap",
                    "missing_evidence", "assumption", "verification", "forecast_reconciliation", "followup_finding",
                    "unparsed"],
 "reference_kinds": ["ledger_claim"]
}
```
<!-- SYNTHESIS_MATERIALITY:END -->

- **Gating:** a red flag the reader must see. A finding of a gating kind with a sentence that states one (a gating
  pattern, in a sentence that does not negate it), and every corpus item of a gating type. Read by sentence and by
  phrase, so that "searches found nothing on fraud" or a "default-spread adjustment" is not a red flag; authorship or
  the dimension a finding bears on never makes it gating. Calibrated on the Bharti reports against the owner-confirmed
  labels in `tests/golden/gating_labels.csv`: 22 of 1,407 items, with every labelled red flag kept. A gating item can
  **never** be dispositioned `immaterial`, and unless it is `superseded` (pointing at a real item or claim, with a reason)
  or an `unverified_lead` (only a digest or historian lead can be one) it must reach the report's body through **every one
  of its distinctive claims** (its claims other than the CIO's and other than claims three or more report items cite,
  such as the price or the revenue line): citing a shared claim of the same finding does not carry the gating fact.
- **Material:** the material kinds above; crosswalk rows whose plausibility effect raises or lowers a layer; historian
  events not found in the documents; corpus items of a type the reading schema marks material.
- **Standard:** other crosswalk rows; ledger claims a Key Finding or Domain Conclusion cites.
- **Reference:** every other ledger claim, non-material corpus item and matched event, dispositioned per cluster.

## Dispositions

<!-- SYNTHESIS_DISPOSITIONS:BEGIN -->
- integrated
- contested
- superseded
- immaterial
- needs_follow_up
- unverified_lead
<!-- SYNTHESIS_DISPOSITIONS:END -->

| Disposition | Points to | Rule |
|---|---|---|
| integrated | an Integrated Finding `F#` of the brief | the finding cites the item's claim IDs or quotes it |
| contested | a Contradiction Candidate `CC-…` | both sides stated; the CIO adjudicates it in the contradiction log |
| superseded | the R-id, cluster or claim ID that replaces it (it must exist) | a later or better source says otherwise (state which; at least ten words for a gating item) |
| immaterial | a reason of at least ten words | never for a gating item |
| needs_follow_up | a Follow-up Request `FU-…` | closed (another disposition) before the final stage |
| unverified_lead | the check attempted | a digest or historian lead no primary source confirmed; never a specialist's finding |

## Consistency rules

<!-- SYNTHESIS_CONSISTENCY_RULES:BEGIN -->
```json
[
 {"id": "EOM_NOT_UNMODIFIED", "when_types": ["emphasis_of_matter"], "forbid": "\\bunmodified\\b", "unless": "emphasis",
  "message": "an emphasis of matter exists for the period: a line calling the opinion unmodified must also mention the emphasis of matter"},
 {"id": "GOING_CONCERN_NOT_CLEAN", "when_types": ["material_uncertainty_going_concern"], "forbid": "\\bclean (?:audit|opinion)\\b", "unless": "going concern",
  "message": "a material uncertainty on going concern exists: the report may not call the audit clean without stating it"},
 {"id": "PENALTY_ACKNOWLEDGED", "when_types": ["penalty_or_noncompliance"], "require_any": ["penalt", "noncompliance", "non-compliance", "regulatory action"],
  "message": "the run holds a penalty or non-compliance item: the report must mention it or list it in the Evidence Integration Register"}
]
```
<!-- SYNTHESIS_CONSISTENCY_RULES:END -->

## Required sections

<!-- THEME_BRIEF_SECTIONS:BEGIN -->
- Theme Summary for the CIO
- Integrated Findings
- Cross-Specialist Agreement and Correlated Sources
- Contradiction Candidates
- Numbers of Record
- Dimension Evidence
- Layer Implications
- Gaps and Follow-up Requests
- Disposition Register
<!-- THEME_BRIEF_SECTIONS:END -->

<!-- LAYER_DRAFT_SECTIONS:BEGIN -->
- Layer Assessment
- Proposed Layer Fit
- Crosswalk Disposition Register
<!-- LAYER_DRAFT_SECTIONS:END -->

<!-- SECTION_WRITER_GROUPS:BEGIN -->
```json
{
 "W1": {"sections": ["Business and Industry Economics", "Moat and Competitive Durability", "Ground-Truth Evidence"], "themes": ["T2"]},
 "W2": {"sections": ["Financial and Accounting Quality"], "themes": ["T1", "T6"]},
 "W3": {"sections": ["Management, Governance and Capital Allocation"], "themes": ["T3"]},
 "W4": {"sections": ["Valuation and Expectations"], "themes": ["T4"]},
 "W5": {"sections": ["Bear Case and Special Situations", "Uncertainties, Missing Evidence and Assumptions"], "themes": ["T5"]},
 "W6": {"sections": ["Contradiction and Evidence Audit", "Monitoring Dashboard"], "themes": []},
 "W7": {"sections": ["Four Independent Layer Assessments"], "themes": []}
}
```
<!-- SECTION_WRITER_GROUPS:END -->

Every section draft ends with a **Not Carried** table: each Integrated Finding of its themes the section does not cite,
with the reason. The CIO writes every other section of the final report (`cio/sections/`).

## Budgets

A theme slice is at most about 110,000 tokens; above that it is split into parts (by author, then by topic) that are read
in separate sessions, each with its own Disposition Register, and reduced into one brief. The CIO's packet is at most
about 150,000 tokens. Every agent keeps the engine's checkpoint at 250,000 tokens of context as the backstop.
