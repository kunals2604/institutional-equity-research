#!/usr/bin/env python3
"""Build specialists/concalls_ledger.csv: MANAGEMENT STATEMENT rows from the promise database + outcome FACTs,
CALCULATIONs (from calc/concalls_stats.py and arithmetic below) and key JUDGMENTs.
Usage: python3 -I calc/concalls_ledger_build.py RUN_DIR
"""
import csv
import sys
from pathlib import Path

COLS = ["claim_id", "author", "claim", "tag", "metric", "value", "unit", "period", "basis", "source_title", "source_issuer",
        "source_url_or_id", "source_date", "retrieved_date", "locator", "source_tier", "primary", "confidence",
        "corroborated_by", "contradicted_by", "formula_or_inputs", "notes"]
RET = "2026-10-12"
ISS = "Bharti Airtel Limited"
FF = "FilingForge:"
R_Q3FY19 = (FF + "16609b54-18cb-4a9b-9cf0-624572bc7d35", "Financial results incl. Quarterly Report Q3FY2019", "2019-01-31")
R_Q1FY20 = (FF + "3a9e77b3-8615-489c-a795-c27d0dfa8254", "Financial results incl. Quarterly Report Q1FY2020", "2019-08-01")
R_Q4FY20 = (FF + "0f5ab988-303b-4e2d-88f0-5e7d421f0cea", "Financial results incl. Quarterly Report Q4FY2020", "2020-05-19")
R_Q3FY21 = (FF + "9c2cf62e-a150-4971-84e2-303b7ecfc693", "Financial results incl. Quarterly Report Q3FY2021", "2021-02-03")
R_Q3FY23 = (FF + "979fa9c6-746f-4f5c-a503-8a3c0aa1346e", "Financial results incl. Quarterly Report Q3FY2023", "2023-02-07")
R_Q4FY23 = (FF + "7a06ce79-f617-42fd-b45d-cd73b8094367", "Financial results incl. Quarterly Report Q4FY2023", "2023-05-16")
R_Q1FY24 = (FF + "18075121-f12f-4418-aec3-6788a94248cd", "Financial results incl. Quarterly Report Q1FY2024", "2023-08-03")
R_Q4FY24 = (FF + "4f6dbf86-d480-4b6c-bbb4-a1c773c70560", "Financial results incl. Quarterly Report Q4FY2024", "2024-05-14")
R_Q2FY25 = (FF + "89f465d1-ee73-46a7-b90c-ecc6f49fcad8", "Financial results incl. Quarterly Report Q2FY2025", "2024-10-28")
R_Q3FY25 = (FF + "80518aeb-92f4-49ca-a67a-6bb2ab44826d", "Financial results incl. Quarterly Report Q3FY2025", "2025-02-06")
R_Q1FY26 = (FF + "49e04d6d-7721-4e07-a2c5-1a4eff6c1322", "Financial results incl. Quarterly Report Q1FY2026", "2025-08-05")
R_Q4FY26 = (FF + "b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1", "Financial results incl. Quarterly Report Q4FY2026", "2026-05-13")
PR_Q2FY26 = ("https://assets.airtel.in/static-assets/cms/investor/docs/quarterly_results/2025-26/Q2/Press-Release.pdf", "Press release Q2FY2026", "2025-11")
IR = ("https://www.airtel.in/about-bharti/equity/results", "Airtel IR results archive", "2026-10-12")


def L(cid, claim, tag, metric="", value="", unit="", period="", basis="", src=None, loc="", tier="4", conf="H",
      corr="", contra="", formula="", notes=""):
    s = src or ("", "", "")
    prim = "Y" if tier and int(tier) <= 4 else ("N" if tier else "")
    return dict(zip(COLS, [cid, "concalls", claim, tag, metric, value, unit, period, basis, s[1], ISS if s[0] else "",
                           s[0], s[2], RET if s[0] else "", loc, tier, prim, conf, corr, contra, formula, notes]))


def fact(cid, claim, metric, value, unit, period, basis, src, loc, tier=1, conf="H", notes="", corr=""):
    return L(cid, claim, "FACT", metric, value, unit, period, basis, src, loc, str(tier), conf, corr, "", "", notes)


def calc(cid, claim, metric, value, unit, period, basis, formula, notes=""):
    return L(cid, claim, "CALCULATION", metric, value, unit, period, basis, ("calc/concalls_stats.out", "concalls calculation", RET),
             "calc/concalls_stats.py; calc/concalls_promise_db.py", "4", "H", "", "", formula, notes)


EXTRA = [
    calc("CON-C001", "Transcript coverage: 40 distinct quarters of original earnings-call transcripts were retrieved and read (Q3FY2016-Q1FY2027; missing Q1FY2017, Q4FY2018, Q1FY2020).",
         "other:transcript_quarters", "40", "quarters", "Q3FY2016-Q1FY2027", "n/a",
         "inputs CON-C002, CON-C004; count of distinct quarter labels in calc/concalls_transcript_index.csv (25 web downloads via fetch_source.py + 15 FilingForge corpus; duplicates Q1FY2025, Q4FY2023, Q2FY2020 counted once)"),
    fact("CON-C002", "The FilingForge library holds a Q1FY2025 transcript (call 6-Aug-2024, doc b6f3d368) that the run CATALOG.md omits; the IR copy is identical in content.",
         "", "", "", "Q1FY2025", "n/a", (FF + "b6f3d368-252f-4257-b0f4-2ec587baaf07", "Transcript Q1FY2025 earnings webinar", "2024-08-12"), "p.1", tier=4, conf="H"),
    fact("CON-C003", "The 14-May-2024 corpus results document headed 'year ended March 31, 2023' is the Q4FY2024 filing: it recommends the FY24 dividend of Rs 8 per share.",
         "", "", "", "FY2024", "n/a", R_Q4FY24, "p.28", conf="H"),
    fact("CON-C004", "Airtel's IR results archive links earnings-call transcripts back to FY2010 and quarterly reports back to FY2011, so a 40-quarter promise window was retrievable.",
         "", "", "", "FY2010-FY2027", "n/a", IR, "results page HTML (links list)", tier=3, conf="H"),
    # capex outcomes
    fact("CON-C100", "FY2016 consolidated capex was US$3,145 Mn.", "other:capex_reported_consol_usd_mn", "3145", "US$ Mn", "FY2016", "consolidated", R_Q3FY19, "p.22"),
    fact("CON-C101", "FY2017 consolidated capex was US$2,959 Mn.", "other:capex_reported_consol_usd_mn", "2959", "US$ Mn", "FY2017", "consolidated", R_Q3FY19, "p.22"),
    fact("CON-C102", "FY2018 consolidated capex was US$4,162 Mn.", "other:capex_reported_consol_usd_mn", "4162", "US$ Mn", "FY2018", "consolidated", R_Q3FY19, "p.22"),
    fact("CON-C103", "FY2018 consolidated capex was Rs268,176 Mn (Rs26,818 crore).", "other:capex_reported_consol_inr_cr", "26817.6", "INR crore", "FY2018", "consolidated", R_Q3FY19, "p.22",
         notes="Rs Mn / 10 = Rs crore"),
    fact("CON-C104", "FY2019 consolidated capex was Rs287,427 Mn.", "other:capex_reported_consol_inr_cr", "28742.7", "INR crore", "FY2019", "consolidated", R_Q4FY20, "p.36"),
    fact("CON-C105", "FY2020 consolidated capex was Rs253,586 Mn (as reported, incl. Infratel).", "other:capex_reported_consol_inr_cr", "25358.6", "INR crore", "FY2020", "consolidated", R_Q4FY20, "p.36"),
    fact("CON-C106", "FY2020 consolidated capex recast after Infratel deconsolidation was Rs244,866 Mn.", "other:capex_reported_consol_inr_cr", "24486.6", "INR crore", "FY2020",
         "consolidated (recast ex-Infratel)", R_Q3FY21, "p.28", notes="Basis break: FY2018-FY2020 recast to 256,870 / 278,319 / 244,866 Rs Mn"),
    fact("CON-C107", "FY2021 consolidated capex was Rs241,685 Mn.", "other:capex_reported_consol_inr_cr", "24168.5", "INR crore", "FY2021", "consolidated", R_Q4FY23, "p.37"),
    fact("CON-C108", "FY2022 consolidated capex was Rs256,616 Mn.", "other:capex_reported_consol_inr_cr", "25661.6", "INR crore", "FY2022", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C109", "FY2023 consolidated capex was Rs341,947 Mn.", "other:capex_reported_consol_inr_cr", "34194.7", "INR crore", "FY2023", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C110", "FY2024 consolidated capex was Rs394,821 Mn (pre-Indus basis).", "other:capex_reported_consol_inr_cr", "39482.1", "INR crore", "FY2024", "consolidated (pre-Indus)", R_Q4FY24, "p.33"),
    fact("CON-C111", "India & South Asia capex was Rs207,725 Mn in FY2022.", "other:capex_reported_india_inr_cr", "20772.5", "INR crore", "FY2022", "segment:India & South Asia", R_Q4FY24, "p.34"),
    fact("CON-C112", "India & South Asia capex was Rs281,547 Mn in FY2023.", "other:capex_reported_india_inr_cr", "28154.7", "INR crore", "FY2023", "segment:India & South Asia", R_Q4FY24, "p.34"),
    fact("CON-C113", "India & South Asia capex was Rs333,793 Mn in FY2024.", "other:capex_reported_india_inr_cr", "33379.3", "INR crore", "FY2024", "segment:India & South Asia", R_Q4FY24, "p.34"),
    fact("CON-C114", "India segment capex was Rs333,526 Mn in FY2024 versus Rs280,567 Mn in FY2023 (+19%).", "other:capex_reported_india_seg_inr_cr", "33352.6", "INR crore", "FY2024", "segment:India", R_Q4FY24, "p.42"),
    fact("CON-C115", "Recast consolidated capex (incl. Indus) was Rs489,268 Mn in FY2024.", "other:capex_reported_consol_recast_inr_cr", "48926.8", "INR crore", "FY2024", "consolidated (recast incl. Indus)", R_Q4FY26, "p.32"),
    fact("CON-C116", "Consolidated capex (incl. Indus, recast) was Rs422,904 Mn in FY2025.", "other:capex_reported_consol_recast_inr_cr", "42290.4", "INR crore", "FY2025", "consolidated (recast incl. Indus)", R_Q4FY26, "p.32"),
    fact("CON-C117", "Consolidated capex was Rs475,218 Mn in FY2026 (+12% YoY).", "other:capex_reported_consol_recast_inr_cr", "47521.8", "INR crore", "FY2026", "consolidated", R_Q4FY26, "p.32"),
    fact("CON-C118", "India (without passive infrastructure) capex was Rs302,722 Mn in FY2025.", "other:capex_reported_india_expassive_inr_cr", "30272.2", "INR crore", "FY2025", "segment:India without passive infrastructure", R_Q4FY26, "p.41"),
    fact("CON-C119", "India (without passive infrastructure) capex was Rs310,068 Mn in FY2026 (+2% YoY).", "other:capex_reported_india_expassive_inr_cr", "31006.8", "INR crore", "FY2026", "segment:India without passive infrastructure", R_Q4FY26, "p.41"),
    fact("CON-C120", "Homes capex was Rs68,127 Mn in FY2026 versus Rs43,105 Mn in FY2025 (+58%).", "other:capex_reported_homes_inr_cr", "6812.7", "INR crore", "FY2026", "segment:Homes", R_Q4FY26, "p.42"),
    fact("CON-C121", "Passive infrastructure (Indus) capex was Rs88,263 Mn in FY2026 versus Rs68,745 Mn in FY2025 (+28%).", "other:capex_reported_passive_inr_cr", "8826.3", "INR crore", "FY2026", "segment:Passive infrastructure", R_Q4FY26, "p.43"),
    fact("CON-C122", "Airtel restated prior-period capex, net debt and P&L after consolidating Indus ('Previous periods' figures have been re-casted ... to make it comparable').", "", "", "", "Q3FY2025", "n/a", R_Q3FY25, "p.29-p.30"),
    # ARPU outcomes
    fact("CON-C130", "India mobile ARPU was Rs123 in Q3FY2018.", "other:arpu_india_mobile", "123", "INR/month", "Q3FY2018", "segment:Mobile India", R_Q3FY19, "p.34"),
    fact("CON-C131", "India mobile ARPU was Rs100 in Q2FY2019 and Rs104 in Q3FY2019 (exit ARPU Rs118 on the new subscriber definition).", "other:arpu_india_mobile", "100", "INR/month", "Q2FY2019", "segment:Mobile India", R_Q3FY19, "p.34"),
    fact("CON-C132", "India mobile ARPU was Rs129 in Q1FY2020 and Rs123 in Q4FY2019.", "other:arpu_india_mobile", "129", "INR/month", "Q1FY2020", "segment:Mobile India", R_Q1FY20, "p.29"),
    fact("CON-C133", "India mobile ARPU was Rs135 in Q3FY2020.", "other:arpu_india_mobile", "135", "INR/month", "Q3FY2020", "segment:Mobile India", R_Q4FY20, "p.47"),
    fact("CON-C134", "India mobile ARPU was Rs154 in Q4FY2020.", "other:arpu_india_mobile", "154", "INR/month", "Q4FY2020", "segment:Mobile India", R_Q4FY20, "p.47"),
    fact("CON-C135", "India mobile ARPU was Rs193 in Q3FY2023.", "other:arpu_india_mobile", "193", "INR/month", "Q3FY2023", "segment:Mobile India", R_Q3FY23, "p.40"),
    fact("CON-C136", "India mobile ARPU first reached Rs200 in Q1FY2024 (Q4FY2023 Rs193).", "other:arpu_india_mobile", "200", "INR/month", "Q1FY2024", "segment:Mobile India", R_Q1FY24, "p.38"),
    fact("CON-C137", "India mobile ARPU was Rs233 in Q2FY2025 (Q1FY2025 Rs211).", "other:arpu_india_mobile", "233", "INR/month", "Q2FY2025", "segment:Mobile India", R_Q2FY25, "p.45"),
    fact("CON-C138", "India mobile ARPU was Rs245 in Q3FY2025.", "other:arpu_india_mobile", "245", "INR/month", "Q3FY2025", "segment:Mobile India", R_Q3FY25, "p.43"),
    fact("CON-C139", "India mobile ARPU was Rs257 in Q4FY2026 (Q3FY2026 Rs259; Q4FY2025 Rs245).", "other:arpu_india_mobile", "257", "INR/month", "Q4FY2026", "segment:Mobile India", R_Q4FY26, "p.46"),
    fact("CON-C140", "India mobile ARPU was Rs256 in Q2FY2026 versus Rs233 in Q2FY2025.", "other:arpu_india_mobile", "256", "INR/month", "Q2FY2026", "segment:Mobile India", PR_Q2FY26, "p.1-p.2", tier=3),
    L("CON-C141", "Management reported India mobile ARPU of Rs264 for Q1FY2027, flattered by one extra day.", "MANAGEMENT STATEMENT", "other:arpu_india_mobile", "264", "INR/month", "Q1FY2027",
      "segment:Mobile India", (FF + "a46861ad-47c4-4fb1-9001-f56835e1a897", "Transcript Q1FY2027 earnings webinar", "2026-08-10"), "p.4", "4", "M",
      notes="Q1FY2027 quarterly report not retrieved (IR download failed SSL); figure as stated on call"),
    fact("CON-C142", "India mobile ARPU was Rs250 in Q1FY2026.", "other:arpu_india_mobile", "250", "INR/month", "Q1FY2026", "segment:Mobile India", R_Q1FY26, "p.39"),
    # leverage / debt / dividend
    fact("CON-C150", "Reported consolidated net debt (incl. leases) to annualised EBITDA was 2.76x at FY2022.", "other:net_debt_incl_leases_to_ebitda_reported", "2.76", "x", "FY2022", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C151", "Reported consolidated net debt to EBITDA was 2.97x at FY2023.", "other:net_debt_incl_leases_to_ebitda_reported", "2.97", "x", "FY2023", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C152", "Reported consolidated net debt to EBITDA was 2.59x at FY2024 (pre-Indus).", "other:net_debt_incl_leases_to_ebitda_reported", "2.59", "x", "FY2024", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C153", "Consolidated net debt to EBITDA (annualised) was 1.86x at March 2025.", "other:net_debt_incl_leases_to_ebitda_reported", "1.86", "x", "Q4FY2025", "consolidated", R_Q4FY26, "p.32"),
    fact("CON-C154", "Consolidated net debt to EBITDA (annualised) was 1.29x at March 2026.", "other:net_debt_incl_leases_to_ebitda_reported", "1.29", "x", "Q4FY2026", "consolidated", R_Q4FY26, "p.32"),
    fact("CON-C155", "Consolidated net debt (incl. leases) was Rs2,131,264 Mn at March 2023.", "net_debt_incl_leases", "213126.4", "INR crore", "FY2023", "consolidated", R_Q4FY24, "p.33"),
    fact("CON-C156", "Consolidated net debt (incl. leases) was Rs2,046,461 Mn at March 2024 (pre-Indus).", "net_debt_incl_leases", "204646.1", "INR crore", "FY2024", "consolidated (pre-Indus)", R_Q4FY24, "p.33"),
    fact("CON-C157", "Recast consolidated net debt was Rs1,943,799 Mn at March 2024 and Rs2,038,384 Mn at March 2025.", "net_debt_incl_leases", "203838.4", "INR crore", "FY2025", "consolidated (recast incl. Indus)", R_Q4FY26, "p.32"),
    fact("CON-C158", "Consolidated net debt was Rs1,647,888 Mn at March 2026 (-19% YoY).", "net_debt_incl_leases", "164788.8", "INR crore", "FY2026", "consolidated", R_Q4FY26, "p.32"),
    fact("CON-C160", "The Board recommended a final dividend of Rs4 per fully paid share for FY2023.", "dps", "4", "INR/share", "FY2023", "standalone", R_Q4FY23, "p.32"),
    fact("CON-C161", "The Board recommended a final dividend of Rs8 per fully paid share for FY2024.", "dps", "8", "INR/share", "FY2024", "standalone", R_Q4FY24, "p.28"),
    L("CON-C162", "Management stated the Board recommended a dividend of Rs24 per share for FY2026 versus Rs16 for FY2025.", "MANAGEMENT STATEMENT", "dps", "24", "INR/share", "FY2026",
      "standalone", ("https://assets.airtel.in/static-assets/cms/investor/docs/quarterly_results/2025-26/Q4/Transcript-of-Bharti-Airtel-Limited-and-Bharti-Hexacom-Limited-4Q-ended-March-31-2026-Earnings-Webinar.pdf",
                     "Transcript Q4FY2026 earnings webinar", "2026-05-14"), "p.2", "4", "H"),
    # calculations
    calc("CON-C200", "Of 56 resolved commitments (Q3FY2016-Q1FY2027), 31 (55%) were exceeded, delivered or mostly delivered; 5 partially delivered, 10 delayed, 10 missed or withdrawn.",
         "other:promise_on_target_share", "55", "%", "Q3FY2016-Q1FY2027", "n/a", "on-target / resolved = 31/56 from promise_database.csv (stats=Y rows); inputs CON-C010 to CON-C095 with outcomes CON-C100 to CON-C162"),
    calc("CON-C201", "Capex-level guidance (n=11) ran over: median variance +7.6%, mean +19.1%; 9 of 11 above the guided level.",
         "other:capex_guidance_variance_median", "7.6", "%", "FY2016-FY2025", "mixed (as guided)", "variance = actual/guided - 1 per row for P01,P02,P04,P05,P06,P10,P11,P12,P13,P14,P18 (P03 reaffirmation excluded); inputs CON-C010..CON-C027 vs CON-C100..CON-C119"),
    calc("CON-C202", "Capex statements made from FY2023 onward overshot by a median 18.6% (n=3), versus 6.9% for FY2016-FY2022 statements (n=8).",
         "other:capex_guidance_variance_median_fy23plus", "18.6", "%", "FY2023-FY2025", "mixed", "median of P12, P13, P14 variances (CON-C020, CON-C021, CON-C022) vs median of P01,P02,P04,P05,P06,P10,P11,P18"),
    calc("CON-C203", "Directional 'capex lower next year' calls were right 3 times out of 4 (FY2020, FY2021, FY2025) and wrong for FY2026.",
         "other:capex_direction_hit_rate", "75", "%", "FY2020-FY2026", "consolidated", "P07 (CON-C015 vs CON-C104/C105), P09 (CON-C017 vs CON-C106/C107), P15 (CON-C023 vs CON-C115/C116) delivered; P16 (CON-C024 vs CON-C116/C117) missed"),
    calc("CON-C204", "Balance-sheet commitments (leverage band, leverage ~2x, net debt reduction, prepayment, dividend step-up) were 6 of 6 on target.",
         "other:promise_on_target_share_balance_sheet", "100", "%", "FY2021-FY2026", "consolidated", "P54-P59 classifications: CON-C070..CON-C075 vs CON-C150..CON-C162"),
    calc("CON-C205", "Dated operational and corporate milestones (5G launch, VoLTE, 3G shutdown, FWA, SA, Telenor, Robi, cloud, rights call, Nxtra renewables) slipped 10 times among 56 resolved items; none was early.",
         "other:promise_delayed_count", "10", "count", "Q3FY2016-Q1FY2027", "n/a", "count of classification=Delayed: CON-C033, CON-C040, CON-C044, CON-C045, CON-C047, CON-C050, CON-C051, CON-C054, CON-C057, CON-C081"),
    calc("CON-C206", "Reaching Rs300 ARPU from Q1FY2027's Rs264 requires a further 13.6% increase; management's 'within five years' window from May-2022 ends around May-2027.",
         "other:arpu_gap_to_target", "13.6", "%", "Q1FY2027", "segment:Mobile India", "300/264 - 1; inputs CON-C141, CON-C036"),
    calc("CON-C207", "India capex FY2023-FY2025 totalled about Rs91,806 crore against a 'same three-year level' of about Rs70,500 crore (+30%).",
         "other:capex_reported_india_3yr_inr_cr", "91806.2", "INR crore", "FY2023-FY2025", "segment:India", "CON-C112 + CON-C113 + CON-C118 vs 3 x 23,500 (CON-C020 basis)",
         notes="FY2025 on 'India without passive infrastructure' basis"),
    calc("CON-C208", "FY2026 capex rose 12.4% consolidated and 2.4% for India ex-passive infrastructure, against guidance that it would fall.",
         "other:capex_reported_consol_growth", "12.4", "%", "FY2026", "consolidated", "CON-C117/CON-C116 - 1; CON-C119/CON-C118 - 1"),
    calc("CON-C209", "FY2024 India capex of Rs33,353 crore ran 7.6% above the top of the Rs28,000-31,000 crore guidance.",
         "other:capex_guidance_variance", "7.6", "%", "FY2024", "segment:India", "CON-C114 / 31,000 - 1"),
    calc("CON-C210", "Home passes reached 33.5 million by Oct-2024 against the 35 million three-year target set in Aug-2021 (96%).",
         "other:home_passes_achievement", "95.7", "%", "Q2FY2025", "segment:Homes", "33.5/35; inputs CON-C061 and Q2FY2025 p.5"),
    calc("CON-C211", "FY2018 capex finished 38.7% above the original ~US$3bn guidance and 7.3% above the raised Rs25,000 crore guidance.",
         "other:capex_guidance_variance", "38.7", "%", "FY2018", "consolidated", "CON-C102/3000 - 1; CON-C103/25000 - 1"),
    # judgments
    L("CON-C300", "Forecast accuracy classification: Inconsistent - accurate on balance-sheet and ARPU direction, persistently optimistic on capex restraint and on dated technology milestones.", "JUDGMENT",
      formula="", notes="Rests on CON-C200 to CON-C211"),
    L("CON-C301", "Execution against commitments: Mixed overall; Reliable for deleveraging and capital return.", "JUDGMENT", notes="CON-C200, CON-C204"),
    L("CON-C302", "Transparency: Standard - capex overruns and timeline slips were usually disclosed in the next call, but formal capex guidance was withdrawn in May-2019 and definitions and bases changed three times.", "JUDGMENT"),
    L("CON-C303", "Strategic consistency: Consistent - the Rs200/Rs300 ARPU thesis, quality-customer focus and deleveraging priorities have been stated in the same terms since FY2020.", "JUDGMENT"),
]


def main():
    run = Path(sys.argv[1])
    db = list(csv.DictReader(open(run / "specialists/concalls_workpapers/promise_database.csv")))
    rows, seen = [], set()
    for r in db:
        cid = r["claim_id"]
        if not cid or cid in seen:
            continue
        seen.add(cid)
        src = r["source"]
        title = "Earnings call transcript %s" % r["quarter"]
        stmt = r["statement"].replace("\n", " ")
        claim = "Management (%s call) stated: %s" % (r["quarter"], stmt[:400])
        metric = r["metric"] if r["target_value"] else ""
        rows.append(L(cid, claim, "MANAGEMENT STATEMENT", metric, r["target_value"] if metric else "", "", r["deadline"], "n/a",
                      (src, title, r["statement_date"]), r["locator"], "4", "H",
                      notes="Promise %s; topic %s; outcome classified %s" % (r["promise_id"], r["topic"], r["classification"])))
    extra_ms = [
        ("CON-C028", "Q2FY2026", "p.7; p.9", "Management (Q2FY2026 call) stated: 'You will see some amount of elevated capex in the near future'; homes capex is 'built into our overall guidance of moderating on capex ... There could be some bump-up because of the investment in Nxtra'."),
        ("CON-C029", "Q1FY2027", "p.7", "Management (Q1FY2027 call) stated: 'there is going to be a period of rapid capex spend' as Nxtra scales from 120-130 MW to 1 GW and 'as a Company, we will not hold back on capex'."),
        ("CON-C066", "Q3FY2023", "p.4", "Management (Q3FY2023 call) stated: 'We have 24 - 25 million home passes and we are on track to actually get to 30 million home passes.'"),
        ("CON-C096", "Q4FY2026", "p.8", "Management (Q4FY2026 call, CFO) described wireless capex as about 16% of sales, 'one of the lowest as percentage sales', and said Airtel would not shy away from higher 5G densification if needed."),
        ("CON-C097", "Q3FY2026", "p.13", "Management (Q3FY2026 call) stated Airtel is 'on track to ... generate Rs.50,000 crores of free cash flow from India business' after normal capex."),
        ("CON-C098", "Q1FY2023", "p.3", "Management (Q1FY2023 call) stated the total commitment in the Aug-2022 spectrum auction was Rs43,040 crore."),
        ("CON-C099", "Q3FY2019", "p.3", "Management (Q3FY2019 call) introduced a 'more stringent' subscriber definition and quoted exit-December ARPU of Rs118 on that basis."),
        ("CON-C067", "Q4FY2019", "p.5", "Management (Q4FY2019 call) stated: 'Historically, we have been giving capex guidance for the coming year. We normally do not give guidance on revenue or profit ..., so we are not going to give guidance on capex as well.'"),
        ("CON-C068", "Q1FY2022", "p.11", "Management (Q1FY2022 call) stated: 'Guidance on ARPU is like a guidance and revenue so I am afraid I cannot give you a guidance on that.'"),
        ("CON-C069", "Q2FY2020", "p.4; p.10", "Management (Q2FY2020 call) disclosed a 60-day extension of the Indus-Infratel long-stop date and said 'there can be no assurance that this can be completed within the due time'."),
        ("CON-C084", "Q4FY2025", "p.8", "Management (Q4FY2025 call) said Airtel had been 'modest in terms of our data center aspirations' and that 'aspirations on data centers need to be stepped up'."),
        ("CON-C085", "Q3FY2026", "p.4", "Management (Q3FY2026 call) stated that in the absence of tariff repair Airtel would 'continue to sweat ARPU growth' via smartphone and postpaid upgrades, data monetisation and international roaming."),
    ]
    import importlib.util
    spec = importlib.util.spec_from_file_location("db", str(run / "calc/concalls_promise_db.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for cid, q, loc, claim in extra_ms:
        src, date = m.SRC[q]
        rows.append(L(cid, claim, "MANAGEMENT STATEMENT", src=(src, "Earnings call transcript %s" % q, date), loc=loc, tier="4", conf="H"))
    rows.extend(EXTRA)
    out = run / "specialists/concalls_ledger.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["claim_id"]):
            w.writerow(r)
    print("ledger rows:", len(rows))


if __name__ == "__main__":
    main()
