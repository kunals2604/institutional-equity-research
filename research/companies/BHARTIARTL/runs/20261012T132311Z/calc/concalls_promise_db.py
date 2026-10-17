#!/usr/bin/env python3
"""Bharti Airtel promise-to-delivery database (concalls specialist, run 20261012T132311Z).

Writes specialists/concalls_workpapers/promise_database.csv. Variances are computed here from the
target and outcome values recorded per row (no mental arithmetic). Assessment date = 2026-10-12.
Usage: python3 -I calc/concalls_promise_db.py RUN_DIR
Classification vocabulary (agent definition): Exceeded | Delivered | Mostly delivered | Partially delivered |
Delayed | Missed | Abandoned/withdrawn | Not yet due | Cannot be determined.
Capex-level rule (spend guidance, not achievement): |variance| <= 5% or below a ceiling -> Delivered;
overspend >5% to 10% vs guided level (top of range) -> Partially delivered; >10% or opposite direction -> Missed.
stats=N marks reaffirmations of an earlier row (kept for goalpost tracking, excluded from rates).
"""
import csv
import sys
from pathlib import Path

ASSESS = "2026-10-12"
FF = "FilingForge:"
W = "https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/"
SC = "https://assets.airtel.in/teams/simplycms/web/docs/"
SRC = {
    "Q3FY2016": (W + "Transcript-of-Bharti-Airtel-Limited-Third-Quarter-Earnings-Conference-Call-Final-Cut_4EA7F76FA58423FD565F50E914C68FC9.pdf", "2016-01-29"),
    "Q4FY2016": (W + "Transcript-of-web-cast_1FDD2458C264A8E8D8A14B68ABC12351.pdf", "2016-04-28"),
    "Q2FY2017": (W + "Transcript-of-Bharti-Airtel-Limited-Second-Quarter-ended-September-30th-2016-Earnings-Conference-Call-held-October-26th-2016-hrs_0EC37C4DA035CB6B810FA95C38F1E68B_1518161275056.pdf", "2016-10-26"),
    "Q3FY2017": (W + "Transcript-of-Bharti-Airtel-Limited-Third-Quarter-Ended-December-31-2016-Earnings-Conference-Call-held-on-January-25-2017-Final_048526FBBB380FCA4516C7DF04E98FCD_1518160369297.pdf", "2017-01-25"),
    "Q4FY2017": (W + "Transcript-of-Bharti-Airtel-Limited-Fourth-Quarter-Ended-March-31st-2017-Earnings-Conference-Call-held-on-May-10th-2017-Final_1B2C95B4807C13256CDCA0E63B3A1CEA_1518159193576.pdf", "2017-05-10"),
    "Q1FY2018": (W + "Transcript-of-Bharti-Airtel-Limited-First-Quarter-ended-June-30-2017-Earnings-Conference-Call-held-on-July-26-2017-at-1430-hrs_F290617A4FEC42CABF1C2873E4C7AC5D_1518157110564.pdf", "2017-07-26"),
    "Q2FY2018": (W + "Transcript-of-Bharti-Airtel-Limited-Second-Quarter-Ended-September-30th_9B88DCBC2B426546BF9D88E79CE04D1B.pdf", "2017-11-01"),
    "Q3FY2018": (W + "Transcript-of-Bharti-Airtel-Limited-Third-Quarter-ended-December-31-2017_F0AFBEE40FAE49F6C11B898C7BC81A93.pdf", "2018-01-19"),
    "Q1FY2019": (W + "Transcript-of-Bharti-Airtel-Limited-First-Quarter-Ended-June-30-2018-held-on-July-27-2018_0AABECC8422FE7C2AE5FEA68AC9CF98E.pdf", "2018-07-27"),
    "Q2FY2019": (W + "Final-Cut-Transcript-of-Bharti-Airtel-Limited-Second-Quarter-Ended-September-30-2018-Earnings-Conference-Call-held-on-October-26-2018-1430-hrs_A754244B1EE4375B219038194BA6E267.pdf", "2018-10-26"),
    "Q3FY2019": (W + "Final-Cut-Transcript-Bharti-Airtel-Limited-Third-Quarter-Ended-December-31-2018-Earnings-Conference-Call-held-February_DE34C10517AB9EF284E07DDDD8862BA9.pdf", "2019-02-01"),
    "Q4FY2019": (W + "Transcript-of-Bharti-Airtel-Limited-Fourth-Quarter-Full-Year-Ended-March_CDC139CAD16CCEA3930BF2285C551871.pdf", "2019-05"),
    "Q2FY2020": (W + "Earnings-Call-Transcript_C4B11DB7852551CEC21E37A918D1A167.pdf", "2019-10-30"),
    "Q3FY2020": ("https://assets.airtel.in/static-assets/cms/Transcript_of_Bharti_Airtel_Limited_Third_Quarter_Ended_December312019_Earnings_ConferenceCall-17022020.pdf", "2020-02-05"),
    "Q4FY2020": (SC + "Transcript_of_Bharti_Airtel_Limited_Fourth_Quarte_Ended_March_31_2020_01062020.pdf", "2020-05-19"),
    "Q1FY2021": (SC + "Transcript_of_Bharti_Airtel_Limited_First_Quarter_Ended_June_30_2020_Earnings_Conference_Call.pdf", "2020-07-30"),
    "Q2FY2021": (SC + "Transcript-of-Bharti-Airtel-Limited-Second-Quarter-Ended-September30-2020-Earnings-Conference-Call.pdf", "2020-10"),
    "Q3FY2021": (SC + "Transcript_of_Bharti_Airtel_Limited_Third_Quarter_Ended_December312020Earnings_Conference_Call_010321.pdf", "2021-02"),
    "Q4FY2021": (SC + "Transcript_Earnings_Call_Q4Y21_2_010621.pdf", "2021-05-18"),
    "Q1FY2022": (SC + "Transcript-of-Bharti-Airtel-Limited-First-Quarter-FY2022-Earnings-Conference-Call-11082021.pdf", "2021-08-04"),
    "Q2FY2022": (SC + "Transcript-of-Bharti-Airtel-Limited-Second-Quarter-Ended-September-302021-Earnings-Conference-Call-6dec.pdf", "2021-11-03"),
    "Q3FY2022": (SC + "Equity_Results_Earnings_Call_Transcript_01032022.pdf", "2022-02-09"),
    "Q4FY2022": (SC + "Transcript_of_Bharti_Airtel_Limited_Q4_2022_Earnings_Call-052422.pdf", "2022-05-18"),
    "Q1FY2023": (SC + "Transcript-of-bharti-airtel-limited-first-quarter-ended-june-30-2022-earnings-conference-call-u-17082022.pdf", "2022-08-09"),
    "Q2FY2023": (FF + "9b74c67a-338a-450a-bb72-040300c02814", "2022-11-01"),
    "Q3FY2023": (FF + "fa591d96-dbad-4607-9a1c-595b9a0f814e", "2023-02-08"),
    "Q4FY2023": (FF + "e5705279-7516-4dd6-b751-767d37118285", "2023-05-17"),
    "Q1FY2024": (FF + "30e022d6-0fe1-49f8-a6a7-503f300b4fa0", "2023-08-04"),
    "Q2FY2024": (FF + "15fbc749-977d-4c71-8a2f-7630ef50ff43", "2023-11-01"),
    "Q3FY2024": (FF + "5f889b5d-9331-4871-a5fc-0b787cd54d46", "2024-02-06"),
    "Q4FY2024": (FF + "955dc315-72cd-44b0-8a72-d08b49e69982", "2024-05-15"),
    "Q1FY2025": (FF + "b6f3d368-252f-4257-b0f4-2ec587baaf07", "2024-08-06"),
    "Q2FY2025": (FF + "9a7c6df2-bb49-4e60-95bc-89bbf247bfc8", "2024-10-29"),
    "Q3FY2025": (FF + "40b11be9-a786-4e48-8a7b-7bedcfca314c", "2025-02-07"),
    "Q4FY2025": (FF + "8e8cf451-ebf8-4b2e-b70f-e7026d32e12c", "2025-05-14"),
    "Q1FY2026": (FF + "b9941a72-7d3b-466c-b01d-abc2d2dfb52a", "2025-08-06"),
    "Q2FY2026": (FF + "ba4a97f1-0054-42d7-b24b-151c74e4a78f", "2025-11-04"),
    "Q3FY2026": (FF + "bccb6f0b-0ac6-4ecc-ad71-c50ee10d52fe", "2026-02-06"),
    "Q4FY2026": ("https://assets.airtel.in/static-assets/cms/investor/docs/quarterly_results/2025-26/Q4/Transcript-of-Bharti-Airtel-Limited-and-Bharti-Hexacom-Limited-4Q-ended-March-31-2026-Earnings-Webinar.pdf", "2026-05-14"),
    "Q1FY2027": (FF + "a46861ad-47c4-4fb1-9001-f56835e1a897", "2026-08-05"),
}
# Outcome documents (tier 1 results incl. quarterly-report trend tables, FilingForge corpus)
R_Q3FY19 = FF + "16609b54-18cb-4a9b-9cf0-624572bc7d35"   # results 31-Jan-2019
R_Q4FY20 = FF + "0f5ab988-303b-4e2d-88f0-5e7d421f0cea"   # results 19-May-2020
R_Q3FY21 = FF + "9c2cf62e-a150-4971-84e2-303b7ecfc693"   # results 3-Feb-2021
R_Q4FY23 = FF + "7a06ce79-f617-42fd-b45d-cd73b8094367"   # results 16-May-2023
R_Q1FY24 = FF + "18075121-f12f-4418-aec3-6788a94248cd"   # results 3-Aug-2023
R_Q4FY24 = FF + "4f6dbf86-d480-4b6c-bbb4-a1c773c70560"   # results 14-May-2024 (headline mislabelled FY2023)
R_Q2FY25 = FF + "89f465d1-ee73-46a7-b90c-ecc6f49fcad8"
R_Q3FY25 = FF + "80518aeb-92f4-49ca-a67a-6bb2ab44826d"
R_Q1FY26 = FF + "49e04d6d-7721-4e07-a2c5-1a4eff6c1322"
R_Q4FY26 = FF + "b5c6beda-7ade-4dd3-ad4f-bff5e5efe4c1"   # results 13-May-2026
R_Q3FY23 = FF + "979fa9c6-746f-4f5c-a503-8a3c0aa1346e"
R_Q4FY20b = R_Q4FY20

COLS = ["promise_id", "quarter", "statement_date", "source", "locator", "topic", "statement", "metric", "target",
        "target_value", "deadline", "outcome", "outcome_value", "outcome_source", "outcome_locator", "assessment_date",
        "classification", "variance_pct", "variance_basis", "resolved", "stats", "goalpost_link", "claim_id", "notes"]


def row(pid, q, loc, topic, stmt, metric, target, tval, deadline, outcome, oval, osrc, oloc, cls,
        vbasis="", stats="Y", goal="", claim="", notes=""):
    src, date = SRC[q]
    var = ""
    if tval not in ("", None) and oval not in ("", None):
        var = "%.1f" % ((float(oval) / float(tval) - 1.0) * 100.0)
    resolved = "N" if cls in ("Not yet due", "Cannot be determined") else "Y"
    return dict(zip(COLS, [pid, q, date, src, loc, topic, stmt, metric, target, tval, deadline, outcome, oval, osrc,
                           oloc, ASSESS, cls, var, vbasis, resolved, stats, goal, claim, notes]))


ROWS = [
    # ---------------- CAPEX ----------------
    row("P01", "Q3FY2016", "p.4", "capex", "Our initial CapEx guidance for the full year was $ 3 billion, which we upped to $3.2 to $3.4 billion subject to doability.",
        "other:capex_reported_consol_usd_mn", "FY2016 US$3.2-3.4bn (low end used)", 3200, "FY2016",
        "FY2016 consolidated capex US$3,145 Mn", 3145, R_Q3FY19, "p.22 (Consolidated summary, Capex US$ Mn)", "Mostly delivered",
        "vs low end of range", goal="G1", claim="CON-C010", notes="Guidance raised mid-year from $3.0bn; outcome 1.7% below low end"),
    row("P02", "Q4FY2016", "p.6; p.19", "capex", "we expect to do another $3 bn over the next year ... approximately $2.2 billion ... India, South Asia; ... $700-800 [million] Africa",
        "other:capex_reported_consol_usd_mn", "FY2017 ~US$3.0bn", 3000, "FY2017", "FY2017 consolidated capex US$2,959 Mn", 2959, R_Q3FY19,
        "p.22", "Delivered", "vs point guidance", claim="CON-C011"),
    row("P03", "Q3FY2017", "p.5", "capex", "I think we will be a shade below $3 billion for this year, consolidated across India and Africa.",
        "other:capex_reported_consol_usd_mn", "FY2017 just under US$3.0bn", 3000, "FY2017", "US$2,959 Mn", 2959, R_Q3FY19, "p.22", "Delivered",
        "reaffirmation of P02", stats="N"),
    row("P04", "Q4FY2017", "p.4; p.6", "capex", "our capex guidance for FY'18 stands similar to FY'17 spends at ~$3bn ... about $2.5bn in India and about 500 million Africa",
        "other:capex_reported_consol_usd_mn", "FY2018 ~US$3.0bn", 3000, "FY2018", "FY2018 consolidated capex US$4,162 Mn", 4162, R_Q3FY19, "p.22",
        "Missed", "vs original guidance", goal="G1", claim="CON-C012",
        notes="Raised mid-year to Rs25,000 cr (P05) to 'tactically advance' capex against Jio; disclosed and explained"),
    row("P05", "Q2FY2018", "p.5", "capex", "Consequently our capex forecast for the year is being upped from the initial guidance of Rs 20,000 cr to Rs 25,000 cr.",
        "other:capex_reported_consol_inr_cr", "FY2018 Rs25,000 cr", 25000, "FY2018", "FY2018 consolidated capex Rs268,176 Mn = Rs26,818 cr", 26817.6,
        R_Q3FY19, "p.22 (Capex Rs Mn)", "Partially delivered", "vs revised guidance", goal="G1", claim="CON-C013"),
    row("P06", "Q1FY2019", "p.5", "capex", "Capex at Rs 82.1billion is slightly front loaded, even as we continue to maintain our overall guidance of Rs 270 billion for the full year",
        "other:capex_reported_consol_inr_cr", "FY2019 Rs270bn", 27000, "FY2019", "FY2019 consolidated capex Rs287,427 Mn", 28742.7, R_Q4FY20, "p.36",
        "Partially delivered", "vs guidance", claim="CON-C014", notes="Reaffirmed Q2FY2019 p.4 and Q3FY2019 p.5 ('in line')"),
    row("P07", "Q4FY2019", "p.5; p.11", "capex", "the peak level of capex was seen last year. The capex will be lower in the course of this year.",
        "other:capex_reported_consol_inr_cr", "FY2020 < FY2019 (Rs287,427 Mn)", 28742.7, "FY2020", "FY2020 Rs253,586 Mn", 25358.6, R_Q4FY20, "p.36",
        "Delivered", "direction", claim="CON-C015"),
    row("P08", "Q3FY2019", "p.7", "guidance policy", "On the investments in the Capex, I think, we will come back to you next quarter with guidance.",
        "", "Capex guidance for FY2020 next quarter", "", "Q4FY2019 call", "Q4FY2019 p.5: 'we are not going to give guidance on capex as well'", "",
        SRC["Q4FY2019"][0], "p.5", "Abandoned/withdrawn", goal="G2", claim="CON-C016"),
    row("P09", "Q4FY2020", "p.5; p.14", "capex", "we expect the overall capex for this year to be more moderated than it was for the last year",
        "other:capex_reported_consol_inr_cr", "FY2021 < FY2020 (recast ex-Infratel Rs244,866 Mn)", 24486.6, "FY2021", "FY2021 Rs241,685 Mn", 24168.5,
        R_Q4FY23, "p.37 (FY2021 column); FY2020 recast: " + R_Q3FY21 + " p.28", "Delivered", "direction (recast basis)", claim="CON-C017"),
    row("P10", "Q4FY2021", "p.7", "capex", "FY2022, we will see capex around the same level as FY2021",
        "other:capex_reported_consol_inr_cr", "FY2022 ~ FY2021 (Rs241,685 Mn)", 24168.5, "FY2022", "FY2022 Rs256,616 Mn", 25661.6, R_Q4FY23, "p.37",
        "Delivered", "level (+/-10%)", claim="CON-C018"),
    row("P11", "Q3FY2021", "p.6; p.8", "capex", "we do not believe that with a 5G introduction ... we are going to see any material change in the capex profile; the incremental capex that we put in will in no way actually go up simply because of 5G",
        "other:capex_reported_india_inr_cr", "No material change vs FY2022 India&SA capex Rs207,725 Mn", 20772.5, "5G cycle (FY2023-FY2024)",
        "India&SA capex FY2024 Rs333,793 Mn (FY2023 Rs281,547 Mn)", 33379.3, R_Q4FY24, "p.34", "Missed", "FY2024 vs FY2022", goal="G1",
        claim="CON-C019"),
    row("P12", "Q1FY2023", "p.4-p.6", "capex", "While our 3-year capex will remain around the same levels this rapid roll out could see some advancing of capex on an in year basis ... in an 18 months period it will normalize",
        "other:capex_reported_india_inr_cr", "3-yr FY2023-25 ~3 x Rs23,500 cr (Q2FY2023 p.12: 'Rs 23,000 Crore to 24,000 Crore number per year')", 70500, "FY2023-FY2025",
        "India capex FY2023 Rs281,547 Mn + FY2024 Rs333,793 Mn + FY2025 (India ex-passive) Rs302,722 Mn", 91806.2,
        R_Q4FY24 + "; " + R_Q4FY26, "p.34; p.41", "Missed", "3-year sum", goal="G1", claim="CON-C020",
        notes="FY2025 on post-Indus 'India without passive infrastructure' basis; FY2023-24 as reported India & South Asia"),
    row("P13", "Q4FY2023", "p.6", "capex", "we have reason to believe that the full year capex for 2023-2024 will be in the same ballpark as what we had in the current year",
        "other:capex_reported_india_inr_cr", "FY2024 ~ FY2023 (India&SA Rs281,547 Mn)", 28154.7, "FY2024", "FY2024 India&SA Rs333,793 Mn", 33379.3, R_Q4FY24, "p.34",
        "Missed", "level", goal="G1", claim="CON-C021"),
    row("P14", "Q1FY2024", "p.3", "capex", "the full year capex is more or less in line with the Rs 28,000 to Rs 31,000 Crore guidance that we have given for the year",
        "other:capex_reported_india_inr_cr", "FY2024 India Rs28,000-31,000 cr (top end used)", 31000, "FY2024", "FY2024 India capex Rs333,526 Mn", 33352.6, R_Q4FY24,
        "p.42 (3.3.2 India)", "Partially delivered", "vs top of range", goal="G1", claim="CON-C022",
        notes="Q2FY2024 p.7 and Q3FY2024 p.10 reaffirmed 'same ballpark'"),
    row("P15", "Q2FY2024", "p.7", "capex", "the peak year of capex will really be in this fiscal ... you should see a moderation of capex in the coming year",
        "other:capex_reported_consol_inr_cr", "FY2025 < FY2024 (recast Rs489,268 Mn)", 48926.8, "FY2025", "FY2025 recast Rs422,904 Mn", 42290.4, R_Q4FY26, "p.32",
        "Delivered", "direction (recast incl. Indus)", claim="CON-C023", notes="Reaffirmed Q3FY2024 p.5, Q4FY2024 p.6, Q1FY2025 p.12; Q4FY2025 p.3 'lower than 2024, as we had guided'"),
    row("P16", "Q4FY2025", "p.5", "capex", "I want to reiterate that our FY2026 capex will be lower than FY2025",
        "other:capex_reported_consol_inr_cr", "FY2026 < FY2025 (Rs422,904 Mn)", 42290.4, "FY2026", "FY2026 consolidated Rs475,218 Mn; India ex-passive Rs310,068 Mn vs Rs302,722 Mn (+2.4%)", 47521.8,
        R_Q4FY26, "p.32; p.41 (3.3.2 India without passive)", "Missed", "direction", goal="G1", claim="CON-C024",
        notes="Q2FY2026 p.7/p.9 pre-signalled 'some amount of elevated capex' and a possible Nxtra bump-up; homes capex +58%, passive infra +28%"),
    row("P17", "Q3FY2018", "p.6", "capex", "these are probably the most elevated levels of Capex this year and probably next year",
        "other:capex_reported_consol_inr_cr", "FY2018/FY2019 peak; FY2020 lower", 28742.7, "FY2020", "FY2020 Rs253,586 Mn", 25358.6, R_Q4FY20, "p.36", "Delivered",
        "FY2020 vs FY2019", claim="CON-C026"),
    row("P18", "Q2FY2021", "p.5", "capex", "the peak levels of capex that we saw for Airtel are now behind us so we are unlikely to see those levels of capex",
        "other:capex_reported_consol_inr_cr", "Below FY2019 peak Rs287,427 Mn", 28742.7, "medium term", "FY2023 Rs341,947 Mn; FY2024 Rs394,821 Mn", 39482.1, R_Q4FY24,
        "p.33", "Missed", "FY2024 vs FY2019 peak", goal="G1", claim="CON-C027"),
    row("P19", "Q4FY2026", "p.7", "capex", "while we do not give guidance typically, our sense is that we will be in the ballpark of this year, give or take a little bit",
        "other:capex_reported_consol_inr_cr", "FY2027 ~ FY2026 (Rs475,218 Mn)", 47521.8, "FY2027", "Q1FY2027 p.7: 'a period of rapid capex spend' on data centres", "",
        SRC["Q1FY2027"][0], "p.7", "Not yet due", claim="CON-C025"),
    # ---------------- ARPU / TARIFF ----------------
    row("P20", "Q3FY2018", "p.5", "ARPU", "the kind of ARPU erosion that you have seen, we are unlikely to see this kind of ARPU erosion going forward",
        "other:arpu_india_mobile", "No further material erosion from Q3FY2018 ARPU Rs123", 123, "next 3-4 quarters", "Q2FY2019 ARPU Rs100", 100, R_Q3FY19, "p.34",
        "Missed", "Q2FY2019 vs Q3FY2018", claim="CON-C030"),
    row("P21", "Q2FY2019", "p.10", "ARPU", "overall, we feel confident about the ARPU trajectory moving northward positively from here on",
        "other:arpu_india_mobile", "ARPU above Q2FY2019 Rs100", 100, "next 2-3 quarters", "Q1FY2020 ARPU Rs129 (Q4FY2019 Rs123)", 129,
        FF + "3a9e77b3-8615-489c-a795-c27d0dfa8254", "p.29", "Delivered", "direction", goal="G3", claim="CON-C031",
        notes="Rise partly reflects subscriber-definition change (Q3FY2019 p.3) and minimum-recharge plans"),
    row("P22", "Q3FY2020", "p.8", "ARPU", "Like I said, I think, Q4 ARPU will certainly be better than Q3.", "other:arpu_india_mobile", "Q4FY2020 > Q3FY2020 Rs135", 135,
        "Q4FY2020", "Q4FY2020 ARPU Rs154", 154, R_Q4FY20, "p.47", "Delivered", "direction", claim="CON-C032"),
    row("P23", "Q4FY2020", "p.3", "ARPU", "remain hopeful that ARPUs will get to Rs 200 in the short term and eventually to Rs 300",
        "other:arpu_india_mobile", "Rs200 'in the short term' (from Rs154)", 200, "short term (~FY2021-22)", "Rs200 first reached Q1FY2024 (Jun-2023)", 200,
        R_Q1FY24, "p.38", "Delayed", "time to target ~13 quarters", goal="G4", claim="CON-C033"),
    row("P24", "Q3FY2022", "p.9", "ARPU", "we hope that the ARPU of the industry to get to 200 soon preferably in 2022 itself",
        "other:arpu_india_mobile", "Rs200 in CY2022", 200, "Dec-2022", "Q3FY2023 (Dec-2022) ARPU Rs193", 193, R_Q3FY23, "p.40", "Mostly delivered",
        "vs target at deadline", goal="G4", claim="CON-C034"),
    row("P25", "Q3FY2022", "p.9", "tariff", "I do expect a tariff hike sometime in 2022.", "", "Industry tariff hike in CY2022", "", "Dec-2022",
        "No headline hike in 2022; entry-plan Rs99->Rs155 repricing piloted then extended (Q3FY2023 p.4, p.6); headline repair Jul-2024 (Q1FY2025 p.4)", "",
        SRC["Q3FY2023"][0], "p.4; p.6", "Partially delivered", goal="G4", claim="CON-C035",
        notes="Q4FY2022 p.6 repeated 'should start seeing some tariff increases during the course of this year, while I cannot commit that'"),
    row("P26", "Q4FY2022", "p.12", "ARPU", "our ARPUs on mobility should be close to Rs 300, in fact it should be around that level in the next five years",
        "other:arpu_india_mobile", "~Rs300 by ~May-2027", 300, "~FY2027/early FY2028", "Q1FY2027 ARPU Rs264", 264, SRC["Q1FY2027"][0], "p.4",
        "Not yet due", "progress to date", goal="G4", claim="CON-C036"),
    row("P27", "Q1FY2025", "p.4", "tariff", "The early signs from this repair are encouraging with the full flow through expected in two quarters.",
        "other:arpu_india_mobile", "Full flow-through by Q3FY2025 (from Q1FY2025 Rs211)", "", "Q3FY2025", "ARPU Q2FY2025 Rs233; Q3FY2025 Rs245", 245, R_Q3FY25,
        "p.43", "Delivered", claim="CON-C037"),
    row("P28", "Q3FY2020", "p.5; p.7", "ARPU", "in the end stage we need to see an ARPU of Rs.300 ... Rs.300 ARPU is the level at which we will return close to 15% return on capital",
        "other:arpu_india_mobile", "Rs300 (no date)", 300, "none", "Q1FY2027 Rs264", 264, SRC["Q1FY2027"][0], "p.4", "Not yet due", stats="N", goal="G4",
        claim="CON-C036"),
    # ---------------- NETWORK / 5G ----------------
    row("P29", "Q1FY2023", "p.4", "5G launch", "We intend to launch 5G starting August and extending to a Pan India roll out very soon.", "", "Launch Aug-2022", "", "Aug-2022",
        "Q2FY2023 p.4 (1-Nov-2022): 'We have now commenced our Airtel 5G plus launch starting with key cities'", "", SRC["Q2FY2023"][0], "p.4", "Delayed",
        claim="CON-C040", notes="Exact commercial launch date not located in this run; not in August"),
    row("P30", "Q1FY2023", "p.4", "5G coverage", "By March 2024 we believe we will be able to cover every town and key rural areas as well with 5G.", "", "All towns + key rural by Mar-2024",
        "", "Mar-2024", "Q4FY2023 p.3: ~3,500 of 7,000 cities/towns by May-2023; completion statement for Mar-2024 not located", "", SRC["Q4FY2023"][0], "p.3",
        "Cannot be determined", claim="CON-C041", notes="Reaffirmed Q2FY2023 p.4, Q3FY2023 p.5/p.10"),
    row("P31", "Q4FY2022", "p.6", "5G pace", "I would expect a more moderated rollout of 5G in the coming year and perhaps a more accelerated rollout in subsequent years",
        "", "Moderate 5G rollout in FY2023", "", "FY2023", "Plan switched to rapid pan-India rollout (Q1FY2023 p.4: 5,000 towns planned; Q4FY2023 p.3: 35-40 cities a day)", "",
        SRC["Q4FY2023"][0], "p.3", "Missed", goal="G1", claim="CON-C042", notes="Direction reversed within one quarter after Aug-2022 auction; disclosed"),
    row("P32", "Q1FY2023", "p.4", "spectrum", "With this auction, we are fully confident that we will not be required to spend any material amount on spectrum for many years to come.",
        "", "No material spectrum spend for many years", "", "multi-year", "Jun-2024 auction: renewals + mid-band 'total purchase of about Rs.6,850 Crores' (Q1FY2025 p.3)", "",
        SRC["Q1FY2025"][0], "p.3", "Delivered", claim="CON-C043", notes="Rs6,850 cr vs Rs43,040 cr Aug-2022 commitment (Q1FY2023 p.3)"),
    row("P33", "Q1FY2018", "p.8", "VoLTE", "towards the end of the fiscal year, we should pretty much be taking VoLTE everywhere ... national ... in the next 6 to 9 months",
        "", "National VoLTE by ~Mar/Apr-2018", "", "Apr-2018", "Q1FY2019 p.10 (Jul-2018): 'drive VoLTE very hard in the next 6 months'", "", SRC["Q1FY2019"][0],
        "p.10", "Delayed", goal="G5", claim="CON-C044", notes="Q2FY2018 p.4: 'across major cities by end of FY18'"),
    row("P34", "Q2FY2020", "p.8", "3G shutdown", "by March 2020 ... we will progressively shutdown our 3G networks", "", "3G shut/2100 refarmed by Mar-2020", "", "Mar-2020",
        "Q4FY2020 p.14: 'refarmed about 25 megahertz of 3G spectrum and there is still more to be refarmed in the coming quarter'", "", SRC["Q4FY2020"][0], "p.14",
        "Delayed", claim="CON-C045", notes="Q3FY2020 p.6/p.11: 2100 band 'all refarmed by March'"),
    row("P35", "Q1FY2025", "p.5", "5G SA/FWA", "We are ready and are planning to go live with SA technology for FWA within this quarter that we are in.", "", "SA on FWA by Sep-2024",
        "", "Sep-2024", "Q2FY2025 p.11: 'by December'; Q4FY2025 p.7: 'at the right point in time ... first port of call will be to move SA on fixed wireless access'", "",
        SRC["Q4FY2025"][0], "p.7", "Abandoned/withdrawn", goal="G6", claim="CON-C046"),
    row("P36", "Q3FY2023", "p.9", "FWA", "working on fixed wireless access, attending to trials and pilots and then be ready in the next six months", "", "FWA ready ~Aug-2023", "", "Aug-2023",
        "Q2FY2024 p.5: testing in key cities, 'rolling out in full by the end of this calendar year'; Q4FY2024 p.8: 'in Q2 you should see the full scale impact'", "",
        SRC["Q4FY2024"][0], "p.8", "Delayed", goal="G6", claim="CON-C047"),
    row("P37", "Q4FY2024", "p.5", "network", "We expect to rollout over 25000 sites lower than last year in the next couple of quarters.", "other:network_sites_added", "~25,000 sites FY2025", 25000,
        "FY2025", "Q4FY2025 p.4: 'added about 25,000 new sites in the full year FY2025'", 25000, SRC["Q4FY2025"][0], "p.4", "Delivered", claim="CON-C048",
        notes="Q4FY2025 p.3 also cites 19,858 network sites; definitions differ (5G sites vs network sites)"),
    row("P38", "Q2FY2018", "p.4", "Africa 4G", "We plan to expand our 4G broadband network across 8 countries by the end of this year.", "", "4G in 8 Africa opcos", 8, "FY2018",
        "Q2FY2019 p.4: 'LTE in 10 Opcos'", 10, SRC["Q2FY2019"][0], "p.4", "Exceeded", claim="CON-C049", notes="Date of reaching 8 not located; 10 by Oct-2018"),
    # ---------------- M&A / CORPORATE ----------------
    row("P39", "Q3FY2016", "p.3", "M&A", "The proposed transaction [Robi-Airtel Bangladesh] ... is expected to complete in the first half of 2016.", "", "Complete H1 CY2016", "", "Jun-2016",
        "Q3FY2017 p.3 (25-Jan-2017): 'Airtel announced completion of the merger'", "", SRC["Q3FY2017"][0], "p.3", "Delayed", claim="CON-C050"),
    row("P40", "Q2FY2018", "p.4", "M&A", "Approvals from Telenor merger are progressing and we expect the transaction to be completed by Q4'18.", "", "Telenor India by Mar-2018", "", "Mar-2018",
        "Q1FY2019 p.4: 'we completed the acquisition of Telenor India on 14th May 2018'", "", SRC["Q1FY2019"][0], "p.4", "Delayed", claim="CON-C051",
        notes="Q3FY2018 p.4 reaffirmed 'by this quarter'; slip ~6 weeks on regulatory approvals"),
    row("P41", "Q2FY2019", "p.4", "Africa IPO", "Airtel Africa subsequently intends an IPO and use the proceeds primarily for further reduction of debt.", "", "Airtel Africa IPO", "", "~2019",
        "Q2FY2020 p.14: refers to 'our listed Africa board and management'", "", SRC["Q2FY2020"][0], "p.14", "Delivered", claim="CON-C052"),
    row("P42", "Q2FY2021", "p.6", "M&A", "We expect in the next maybe 10 to 20 days ... the merger to be through.", "", "Indus-Infratel close in 10-20 days", "", "Nov-2020",
        "Q3FY2021 p.4: 'merger of Indus Towers Limited and Bharti Infratel, which was completed on November 19, 2020'", "", SRC["Q3FY2021"][0], "p.4", "Delivered",
        goal="G7", claim="CON-C053", notes="Earlier long-stop extensions: Q2FY2020 p.4/p.10, Q3FY2020 p.4"),
    row("P43", "Q1FY2023", "p.9", "rights issue", "Rs 15,000+ Crores of residual calls are pending and really in the coming few months, we need to evaluate ... at what point in time should we call for it.",
        "", "Decide on residual call within months", "", "~early 2023", "Q1FY2024 p.10/Q3FY2024 p.9: 'no need to call'; Q3FY2026 p.6: called because 'timeframe of 3 years ... is now over, we have no provision to foreclose'", "",
        SRC["Q3FY2026"][0], "p.6-p.7", "Delayed", goal="G8", claim="CON-C054"),
    row("P44", "Q3FY2025", "p.3", "towers", "we are planning to transfer about 16,100 telecom towers ... to Indus Towers", "", "Transfer ~16,100 towers", 16100, "n/s",
        "Completion not located in transcripts read", "", "", "", "Cannot be determined", claim="CON-C055"),
    row("P45", "Q2FY2025", "p.3", "leadership", "Shashwat will be appointed CEO designate and will take over the role of MD & CEO on January 01, 2026.", "", "MD&CEO succession 1-Jan-2026", "", "Jan-2026",
        "Q3FY2026 (6-Feb-2026) participant list: 'Shashwat Sharma - Managing Director & CEO (Airtel India)'", "", SRC["Q3FY2026"][0], "p.2-p.3", "Delivered", claim="CON-C056"),
    row("P46", "Q2FY2025", "p.7", "cloud", "We have now signed off an investment ... which we will take to market in the next few months", "", "Cloud launch in a few months", "", "~Q4FY2025",
        "Q1FY2026 p.5 (6-Aug-2025): 'We have launched Airtel Cloud'", "", SRC["Q1FY2026"][0], "p.5", "Delayed", claim="CON-C057",
        notes="Q3FY2025 p.5 repeated 'in the next few months'"),
    row("P47", "Q3FY2025", "p.4", "B2B", "We have made a decision to exit this low-margin business, which will have an impact on the topline in the coming quarters.", "", "Guided B2B revenue decline", "", "FY2026",
        "Q1FY2026 p.3: 'in line with our guidance ... to peel off our low margin revenue in B2B'", "", SRC["Q1FY2026"][0], "p.3", "Delivered", claim="CON-C058"),
    # ---------------- HOMES ----------------
    row("P48", "Q4FY2021", "p.10", "homes", "in another couple of years ... we would like to see ourselves in about 20 to 25 million home passes", "other:home_passes_mn", "20-25 mn (low end)", 20, "~May-2023",
        "Q3FY2023 p.4: '24 - 25 million home passes'", 24, SRC["Q3FY2023"][0], "p.4", "Delivered", goal="G9", claim="CON-C060"),
    row("P49", "Q1FY2022", "p.3", "homes", "take our network to over 2000 towns across India and cover over 35 million home passes in the next 3 years", "other:home_passes_mn", "35 mn by ~Aug-2024", 35,
        "Aug-2024", "Q2FY2025 p.5 (Oct-2024): 'over 33.5 million home passes'", 33.5, SRC["Q2FY2025"][0], "p.5", "Mostly delivered", goal="G9", claim="CON-C061",
        notes="Q3FY2023 p.4 lowered to '30 million'; Q2FY2024 p.5 raised to '40 million targeted'"),
    row("P50", "Q2FY2024", "p.5", "homes", "we are on track to reach 40 million targeted home passes", "other:home_passes_mn", "40 mn (no date)", 40, "n/s",
        "Q4FY2026 p.4: 'rolled out upwards of 8 million home passes to cross 45 million'", 45, SRC["Q4FY2026"][0], "p.4", "Exceeded", goal="G9", claim="CON-C062"),
    row("P51", "Q3FY2021", "p.5", "homes", "hundreds of local cable operators in over 120 cities and planning to get to about 1,000 cities in a year", "other:homes_cities", "1,000 cities by ~Feb-2022", 1000,
        "Feb-2022", "Q3FY2022 p.3 (Feb-2022): 'presence has now expanded to 672 towns'", 672, SRC["Q3FY2022"][0], "p.3", "Partially delivered", claim="CON-C063"),
    row("P52", "Q1FY2025", "p.13", "homes", "We will roll out one and a half million home passes every quarter", "other:home_passes_mn", "1.5 mn/quarter (6.0 mn/yr)", 6.0, "FY2025",
        "Q4FY2025 p.3: 'nearly 7.2 million home passes added'", 7.2, SRC["Q4FY2025"][0], "p.3", "Exceeded", claim="CON-C064"),
    row("P53", "Q3FY2021", "p.3", "homes", "in a year or so, we will shut down our copper infrastructure and have only fiber-to-the-home", "", "Copper shutdown ~Feb-2022", "", "~Feb-2022",
        "No later statement located", "", "", "", "Cannot be determined", claim="CON-C065"),
    # ---------------- BALANCE SHEET / CAPITAL RETURN ----------------
    row("P54", "Q3FY2021", "p.6", "leverage", "We have historically guided for staying between 2x and 3x and that continues as our strategy.", "other:net_debt_incl_leases_to_ebitda_reported", "2.0x-3.0x (top end)", 3.0, "FY2022-FY2024",
        "Consolidated net debt/EBITDA FY2022 2.76x, FY2023 2.97x, FY2024 2.59x", 2.97, R_Q4FY24, "p.33", "Delivered", "peak vs ceiling", claim="CON-C070"),
    row("P55", "Q1FY2024", "p.10", "leverage", "our target is not very hard-coded, but still are closer to two on an overall consolidated basis not closer to three", "other:net_debt_incl_leases_to_ebitda_reported", "~2.0x", 2.0,
        "Q3FY2024 p.9: 'next four to six quarters'", "Mar-2025 1.86x; Mar-2026 1.29x (consolidated, annualised)", 1.86, R_Q4FY26, "p.32", "Delivered", "Mar-2025 vs target",
        claim="CON-C071"),
    row("P56", "Q3FY2023", "p.3", "debt", "Looking ahead, we expect our net debt go down further in the coming year.", "net_debt_incl_leases", "FY2024 < FY2023 (Rs2,131,264 Mn)", 213126.4, "FY2024",
        "Mar-2024 Rs2,046,461 Mn", 204646.1, R_Q4FY24, "p.33", "Delivered", "direction", claim="CON-C072"),
    row("P57", "Q4FY2024", "p.3", "debt", "We expect further debt reduction going forward.", "net_debt_incl_leases", "Below Mar-2024 (recast Rs1,943,799 Mn)", 194379.9, "FY2025-FY2026",
        "Mar-2025 Rs2,038,384 Mn (+4.9%, Indus consolidated); Mar-2026 Rs1,647,888 Mn", 164788.8, R_Q4FY26, "p.32", "Delivered", "Mar-2026 vs Mar-2024 recast",
        claim="CON-C073", notes="Consolidated net debt rose in FY2025 on the recast basis before falling 19% in FY2026"),
    row("P58", "Q3FY2022", "p.3", "debt", "we have decided to prepay the high cost spectrum debt liability of over 15000 crores", "", "Prepay >Rs15,000 cr", 15000, "FY2022",
        "Q3FY2022 p.8: 'the sum total of 15 odd thousand Crores that was paid out'", "", SRC["Q3FY2022"][0], "p.8", "Delivered", claim="CON-C074"),
    row("P59", "Q3FY2025", "p.6", "dividend", "There will be a step-up of dividend for sure", "dps", "DPS above FY2024 Rs8", 8, "FY2025-FY2026",
        "FY2025 Rs16; FY2026 Rs24 (Q4FY2026 p.2)", 24, SRC["Q4FY2026"][0], "p.2", "Delivered", claim="CON-C075",
        notes="FY2023 Rs4 (R_Q4FY23 line 39); FY2024 Rs8 (R_Q4FY24)"),
    # ---------------- INDUSTRY CALLS / OTHER ----------------
    row("P60", "Q3FY2017", "p.7", "industry", "Our sense is that this will rapidly consolidate in the next 12 months to 15 months", "", "Consolidation by ~Apr-2018", "", "Apr-2018",
        "Q1FY2019 p.4/p.7 (Jul-2018): Telenor completed May-2018; Vodafone-Idea merger approvals 'have come through'", "", SRC["Q1FY2019"][0], "p.4; p.7", "Mostly delivered",
        claim="CON-C080", notes="~18 months vs 12-15"),
    row("P61", "Q3FY2018", "p.6", "industry", "by let us say March 2019 you are going to have a completely revised industry structure with three operators", "", "3 private operators by Mar-2019", "", "Mar-2019",
        "Q1FY2019 p.7: Vodafone-Idea merger approvals came through (Jul-2018)", "", SRC["Q1FY2019"][0], "p.7", "Delivered", claim="CON-C083"),
    row("P62", "Q1FY2021", "p.8", "5G timing", "we believe that this will be at least a couple of years out before 5G has any meaningful significance in India", "", "5G >= ~2 years away", "", "~2022",
        "5G launch commenced by Nov-2022 (Q2FY2023 p.4)", "", SRC["Q2FY2023"][0], "p.4", "Delivered", claim="CON-C039"),
    row("P63", "Q2FY2023", "p.3", "ESG", "Nxtra is committed to achieving 50% of its power requirements through renewable energy sources in the next 12 months.", "", "50% renewable by ~Nov-2023", 50, "Nov-2023",
        "Q1FY2026 p.3 (Aug-2025): 'nearly half the electricity consumed at our data centers comes from renewable sources'", "", SRC["Q1FY2026"][0], "p.3", "Delayed", claim="CON-C081",
        notes="Q4FY2022 p.4 had said 34% and '50% very soon'"),
    row("P64", "Q4FY2016", "p.10", "Africa", "With regard to Africa at this point no plans for any disposal ... nothing more on the cards as of now.", "", "No further Africa disposals", "", "n/s",
        "Q3FY2017 p.7 analyst cites Chairman on ~US$1bn Africa asset sales in next 12 months", "", SRC["Q3FY2017"][0], "p.7", "Cannot be determined", claim="CON-C082"),
    # ---------------- NOT YET DUE (current guidance) ----------------
    row("P65", "Q3FY2025", "p.13", "postpaid", "There is no reason why we should not get upwards of 50 million over the next few years on postpaid", "", ">50 mn postpaid", 50, "next few years",
        "n/a", "", "", "", "Not yet due", claim="CON-C090"),
    row("P66", "Q3FY2026", "p.5; p.6", "data centres", "Our plan is to reach 1 gigawatt capacity in the next three to four years ... from about 120 to 130 megawatts", "", "1 GW by ~FY2029-30", 1000,
        "~2029-2030", "Q1FY2027 p.7: still 'building out from the 120 to 130 megawatts'", "", SRC["Q1FY2027"][0], "p.7", "Not yet due", claim="CON-C091"),
    row("P67", "Q1FY2026", "p.11", "data centres", "we can continue to grow to 3x growth on the topline and in the EBITDA in the next two-three years and have possibly a listing of the data center entity",
        "", "Nxtra 3x revenue/EBITDA in 2-3 yrs", "", "~FY2028", "n/a", "", "", "", "Not yet due", claim="CON-C095"),
    row("P68", "Q1FY2027", "p.4", "Africa mobile money", "Airtel Money is now preparing for a London listing in the second half of 2026.", "", "Listing H2 CY2026", "", "Dec-2026",
        "n/a", "", "", "", "Not yet due", claim="CON-C092"),
    row("P69", "Q4FY2026", "p.7", "edge DCs", "we are focused right now on building in the next 18 to 24 months- 56 world class edge data centers", "", "56 edge DCs by ~2028", 56, "~May-2028",
        "n/a", "", "", "", "Not yet due", claim="CON-C093"),
    row("P70", "Q4FY2026", "p.9", "promoter", "3.6% over the next three years or so, let us say, three to four years ... hopefully, in the next couple of years, some buybacks in addition to the dividend",
        "", "BTL +3.6% in 3-4 yrs; buybacks in ~2 yrs", "", "~2028-2030", "n/a", "", "", "", "Not yet due", claim="CON-C094", notes="Chairman (Sunil Bharti Mittal)"),
]


def main():
    run = Path(sys.argv[1])
    out = run / "specialists/concalls_workpapers/promise_database.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for r in ROWS:
            w.writerow(r)
    print("wrote %d rows -> %s" % (len(ROWS), out))


if __name__ == "__main__":
    main()
