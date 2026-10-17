#!/usr/bin/env python3
"""Build specialists/financials_workpapers/financial_history.csv (INR crore, crore shares)
from line items transcribed (INR million / '000 shares) out of the cited filings.

Run:  python3 calc/financials_build_history.py   (from the run directory or anywhere)

Conventions (see financials report, Data Basis section):
- Basis: consolidated, as presented in the latest audited presentation available for that year
  (generally the following year's annual-report comparatives); FY2011-FY2015 from IFRS
  consolidated statements published in Airtel's Q4 Quarterly Reports (tier 3, verified=N).
- other_income = other income (+ finance income - non-operating expenses where presented
  separately, FY2011-FY2020 formats). interest_expense = finance costs (gross).
- ebitda = revenue - total operating expenses (excludes other income; post Ind AS 116 from FY2020).
- capex = purchase of PP&E/CWIP + non-spectrum intangibles. Spectrum cash (upfront + deferred
  instalments) is kept in a separate column (other:spectrum_paid) and NOT in capex. FY2011,
  FY2014-FY2018: the 'purchase of intangible assets' line is treated as spectrum (it includes the
  spectrum upfront payments); FY2012-FY2013 intangibles are treated as capex (no auction).
- total_debt = borrowings (current + non-current) incl. deferred payment liabilities to DoT
  (spectrum; and AGR from FY2022 after the moratorium conversion), excluding lease liabilities.
  IFRS years: long-term + short-term borrowings + 'deferred payment liability' per the company's
  net-debt schedule.
- cash_and_equivalents = balance-sheet 'cash and cash equivalents' only (other bank balances excluded:
  they include restricted mobile-money trust balances and margin money). current_investments =
  current investments.
- trade_payables: IFRS years report 'trade & other payables' (broader).
- dividends_paid = dividend to the Company's shareholders (statement of changes in equity / IFRS CF
  line 'to Company's shareholders'); dividends to NCI excluded.
- shares: weighted-average basic ('000) and year-end issued shares ('000, incl. partly paid),
  adjusted for the bonus element of the 2019 and 2021 rights issues (factors from the company's
  own EPS restatements). IFRS-years basic shares derived as pat_attributable / basic EPS.
"""
import csv
from pathlib import Path

RUN = Path(__file__).resolve().parent.parent
OUT = RUN / "specialists" / "financials_workpapers" / "financial_history.csv"

F19 = 4284371 / 3995772   # FY2019 weighted basic restated (AR FY2020) / original (AR FY2019)
F21 = 5480917 / 5454335   # FY2021 weighted basic restated (AR FY2022) / original (AR FY2021)

SRC = {
    "AR26": ("1", "https://www.airtel.in/airtel-annual-report-2025-26/files/pdfs/Consolidated-Financial-Statements.pdf",
             "AR FY2026 consolidated BS/P&L/SOCE/CF printed pp.424-428", "Y"),
    "AR25": ("1", "FilingForge:ef981e1b-4d0f-478c-ae63-5e3f2ca4316f",
             "AR FY2025 consolidated BS/P&L/CF printed pp.392-399 (MD lines 24812-25140)", "Y"),
    "AR24": ("1", "FilingForge:fa581014-8329-4051-a7b5-54eddb9ab932",
             "AR FY2024 consolidated BS/P&L/CF printed pp.360-367 (MD lines 12047-12354)", "Y"),
    "AR23": ("1", "FilingForge:80756f27-cb0a-4847-9f7b-019ba8be2275",
             "AR FY2023 consolidated BS/P&L/CF printed pp.330-336 (MD lines 10357-10646)", "Y"),
    "AR22": ("1", "FilingForge:1c7c2552-7d96-4a40-ae4b-afed2435fdcf",
             "AR FY2022 consolidated BS/P&L/CF (MD lines 23545-23898); FY2021 EPS rights-adjusted", "Y"),
    "AR21": ("1", "FilingForge:3e7fff81-d3bf-4662-8dd5-8c18db7db532",
             "AR FY2021 consolidated BS/P&L/CF printed pp.326-330 (MD lines 12671-13025)", "Y"),
    "AR20": ("1", "FilingForge:49889f5f-b097-41be-8be7-8bad6d949760",
             "AR FY2020 consolidated BS/P&L/CF printed pp.302-307 (MD lines 20807-21136)", "Y"),
    "AR18": ("1", "FilingForge:AR-532454-2018",
             "AR FY2018 consolidated BS/P&L/CF printed pp.233-236 (MD lines 12175-12624)", "Y"),
    "AR17": ("1", "FilingForge:AR-532454-2017",
             "AR FY2017 consolidated BS/P&L/CF printed pp.188-191 (MD lines 10187-10488)", "Y"),
    "QR15": ("3", "https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/Bharti-Airtel-Limited_Quarterly-Report_March-31-2015_58F1A60F8EFCFAB5737D217D19E517EF.pdf",
             "Quarterly Report Q4FY2015 s.7.1.1-7.1.4 and 7.3.1 (IFRS) pp.30-36", "N"),
    "QR14": ("3", "https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/Bharti-Airtel-Limited_Quarterly-Report_March-31-2014_0B103C981978C62E5AA959323553CE28.pdf",
             "Quarterly Report Q4FY2014 s.7.1.1-7.1.4 and 7.3.1 (IFRS, IFRS 11 restated FY2013) pp.28-31", "N"),
    "QR12": ("3", "https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/Quarterly_report_Q4_12_277C906E244186D07013C9178DB9FF1C_1518506254188.pdf",
             "Quarterly Report Q4FY2012 s.7.1.1-7.1.4 (IFRS, proportionate consolidation of Indus) pp.27-28", "N"),
    "QR11": ("3", "https://assets.airtel.in/static-assets/cms/investor/docs/bsy/iportal/images/Quarterly_report_Q1FY12_73455812CF99BC2097413F337CBD72F5_1518501594125.pdf",
             "Quarterly Report Q4FY2011 A.1.3 consolidated cash flow (IFRS) p.31", "N"),
}

# INR million unless noted. Keys mirror METRIC_DEFINITIONS; extra keys handled below.
D = {
 "FY2026": dict(src="AR26", revenue=2109728, other_income=28173, opex_total=912983, employee_cost=75813,
   depreciation=527108, interest_expense=215553, share_jv=3645, exceptional_items=-34175, pbt=451727, tax=113499,
   pat=338228, pat_attributable=266952, eps_basic=45.96, total_assets=5521516, current_assets=902154,
   current_liabilities=1745057, inventories=6009, current_investments=137006, trade_receivables=79776,
   cash_and_equivalents=137222, other_bank=166546, total_equity=1490566, minority_interest_bs=469068,
   total_debt=1000849+215865, lease_liabilities=644996+92407, trade_payables=450152,
   net_fixed_assets=1570659, cwip=126131, rou=673244, goodwill_intangibles=566859+1252604+3250,
   cfo=1222296, capex=451756+15386, spectrum_paid=8546, acquisitions=0, dividends_paid=92738,
   lease_paid=67197, interest_paid=148876, equity_issued=156949, buybacks=0,
   shares_basic_k=5808741, shares_ye_k=6094393, adj=1.0),
 "FY2025": dict(src="AR25", revenue=1729852, other_income=15737, opex_total=798260, employee_cost=63089,
   depreciation=455703, interest_expense=217539, share_jv=37030, exceptional_items=72868, pbt=383985, tax=9172,
   pat=374813, pat_attributable=335561, eps_basic=58.00, total_assets=5143604, current_assets=675888,
   current_liabilities=1804402, inventories=4517, current_investments=16532, trade_receivables=74557,
   cash_and_equivalents=61056, other_bank=106143, total_equity=1136719, minority_interest_bs=397958,
   total_debt=1048638+434485, lease_liabilities=556701+96597, trade_payables=381537,
   net_fixed_assets=1432724, cwip=105962, rou=602415, goodwill_intangibles=516974+1332569+4027,
   cfo=983322, capex=379077+17722, spectrum_paid=213487, acquisitions=0, dividends_paid=46303,
   lease_paid=71538, interest_paid=175476, equity_issued=0, buybacks=0,
   shares_basic_k=5785462, shares_ye_k=6094393, adj=1.0),
 "FY2024": dict(src="AR25", revenue=1499824, other_income=14354, opex_total=716906, employee_cost=53231,
   depreciation=395376, interest_expense=226477, share_jv=27094, exceptional_items=-75723, pbt=126790, tax=41210,
   pat=85580, pat_attributable=74670, eps_basic=13.09, total_assets=4445310, current_assets=582761,
   current_liabilities=1386678, inventories=3639, current_investments=2695, trade_receivables=47277,
   cash_and_equivalents=69155, other_bank=94244, total_equity=820188, minority_interest_bs=235451,
   total_debt=1309626+209539, lease_liabilities=539271+97487, trade_payables=351325,
   net_fixed_assets=1066121, cwip=89077, rou=559367, goodwill_intangibles=265017+1142526+79964,
   cfo=788982, capex=381915+18600, spectrum_paid=121547, acquisitions=6428, dividends_paid=22752,
   lease_paid=78552, interest_paid=140263, equity_issued=0, buybacks=0,
   shares_basic_k=5703364, shares_ye_k=6047375, adj=1.0),
 "FY2023": dict(src="AR24", revenue=1391448, other_income=9366, opex_total=678713, employee_cost=48308,
   depreciation=364318, interest_expense=192999, share_jv=7521, exceptional_items=-6698, pbt=165607, tax=42733,
   pat=122874, pat_attributable=83459, eps_basic=14.80, total_assets=4466332, current_assets=575013,
   current_liabilities=1219638, inventories=2576, current_investments=47045, trade_receivables=39815,
   cash_and_equivalents=71794, other_bank=62392, total_equity=775629, minority_interest_bs=288814,
   total_debt=1515686+139762, lease_liabilities=508295+96460, trade_payables=328946,
   net_fixed_assets=952241, cwip=110293, rou=546466, goodwill_intangibles=337741+937490+383961,
   cfo=653246, capex=260566+4819, spectrum_paid=123684, acquisitions=0, dividends_paid=16976,
   lease_paid=75986, interest_paid=66893, equity_issued=52242, buybacks=0,
   shares_basic_k=5640723, shares_ye_k=5967422, adj=1.0),
 "FY2022": dict(src="AR23", revenue=1165469, other_income=5343, opex_total=590130, employee_cost=44333,
   depreciation=330907, interest_expense=166162, share_jv=24232, exceptional_items=16986, pbt=124831, tax=41779,
   pat=83052, pat_attributable=42549, eps_basic=7.67, total_assets=3636560, current_assets=520279,
   current_liabilities=1140260, inventories=3750, current_investments=8614, trade_receivables=40562,
   cash_and_equivalents=60959, other_bank=73984, total_equity=665543, minority_interest_bs=253807,
   total_debt=1135350+193795, lease_liabilities=290562+77072, trade_payables=292741,
   net_fixed_assets=905725, cwip=42386, rou=322286, goodwill_intangibles=338313+874509+17161,
   cfo=550166, capex=265406+8593, spectrum_paid=174482, acquisitions=0, dividends_paid=0,
   lease_paid=76427, interest_paid=131588, equity_issued=52226, buybacks=0,
   shares_basic_k=5546320, shares_ye_k=5884315, adj=1.0),
 "FY2021": dict(src="AR22", revenue=1006158, other_income=6428, opex_total=552441, employee_cost=41146,
   depreciation=294044, interest_expense=150910, share_jv=-928, exceptional_items=-159145, pbt=-144882, tax=89325,
   pat=-123640, pat_attributable=-150835, eps_basic=-27.52, total_assets=3460278, current_assets=547529,
   current_liabilities=1116359, inventories=2660, current_investments=40781, trade_receivables=36377,
   cash_and_equivalents=80859, other_bank=53802, total_equity=589527, minority_interest_bs=222739,
   total_debt=1105603+192296, lease_liabilities=251086+78867, trade_payables=278721,
   net_fixed_assets=858046, cwip=43665, rou=288117, goodwill_intangibles=329064+759569+13600,
   cfo=482050, capex=248143+24433, spectrum_paid=63240, acquisitions=0, dividends_paid=10907,
   lease_paid=64206, interest_paid=71294, equity_issued=0, buybacks=0,
   shares_basic_k=5480917, shares_ye_k=5492027, adj_basic=1.0, adj=F21,
   note="P&L lines continuing operations (Infratel deconsolidated 19-Nov-2020); pat incl. discontinued profit 110567 mn (incl. deemed-disposal gain 94496 mn); pbt/tax are continuing ops"),
 "FY2020": dict(src="AR20", revenue=875390, other_income=3248+16098-1272, opex_total=509295, employee_cost=38072,
   depreciation=276896, interest_expense=139918, share_jv=6524, exceptional_items=-402344, pbt=-428465, tax=-121823,
   pat=-306642, pat_attributable=-321832, eps_basic=-63.41, total_assets=3607790, current_assets=766432,
   current_liabilities=1314876, inventories=1569, current_investments=137679, trade_receivables=46058,
   cash_and_equivalents=135507, other_bank=23420, total_equity=771448, minority_interest_bs=249847,
   total_debt=910792+167034+98364, lease_liabilities=243678+62413, trade_payables=250199,
   net_fixed_assets=877573, cwip=39972, rou=259049, goodwill_intangibles=346192+809741+2851,
   cfo=181287, capex=191902+15266, spectrum_paid=15424, acquisitions=1345, dividends_paid=0,
   lease_paid=47740, interest_paid=109993, equity_issued=248759+143055, buybacks=0,
   shares_basic_k=5075636, shares_ye_k=5455557, adj=F21,
   note="As originally reported incl. Infratel (AR FY2021 restated P&L to continuing ops: revenue 846765 mn); first Ind AS 116 year"),
 "FY2019": dict(src="AR20", revenue=807802, other_income=3463+10328-1894, opex_total=550164, employee_cost=37975,
   depreciation=213475, interest_expense=106222, share_jv=3556, exceptional_items=29288, pbt=-17318, tax=-34193,
   pat=16875, pat_attributable=4095, eps_basic=0.96, total_assets=2751560, current_assets=328642,
   current_liabilities=930134, inventories=884, current_investments=46232, trade_receivables=43006,
   cash_and_equivalents=62121, other_bank=18519, total_equity=714222, minority_interest_bs=135258,
   total_debt=824901+310097+71732, lease_liabilities=47553, trade_payables=263138,
   net_fixed_assets=815228, cwip=88433, rou=0, goodwill_intangibles=332562+860525+7909,
   cfo=200702, capex=260971+33804, spectrum_paid=11720, acquisitions=5083, dividends_paid=24096,
   lease_paid=5077, interest_paid=76171, equity_issued=0, buybacks=0,
   shares_basic_k=4284371, shares_ye_k=3997400, adj_basic=F21, adj=F19 * F21,
   note="AR FY2020 comparatives; pre-Ind AS 116 (lease_liabilities = finance leases); EPS rights-adjusted"),
 "FY2018": dict(src="AR18", revenue=836879, other_income=2488+12540-141, opex_total=536088, employee_cost=39771,
   depreciation=192431, interest_expense=93255, share_jv=10609, exceptional_items=-7931, pbt=32670, tax=10835,
   pat=21835, pat_attributable=10990, eps_basic=2.75, total_assets=2505816, current_assets=334990,
   current_liabilities=782399, inventories=693, current_investments=68978, trade_receivables=58830,
   cash_and_equivalents=47886, other_bank=18820, total_equity=695344, minority_interest_bs=88139,
   total_debt=849420+129569+134346, lease_liabilities=0, trade_payables=277675,
   net_fixed_assets=706079, cwip=52089, rou=0, goodwill_intangibles=328070+837855+45423,
   cfo=298538, capex=245259, spectrum_paid=17749+9909, acquisitions=19498, dividends_paid=18475,
   lease_paid=3932, interest_paid=44041, equity_issued=0, buybacks=0,
   shares_basic_k=3996067, shares_ye_k=3997400, adj_basic=F19 * F21, adj=F19 * F21,
   note="As reported in AR FY2018 (finance leases inside borrowings)"),
 "FY2017": dict(src="AR18", revenue=954683, other_income=1206+18492-1319, opex_total=601385, employee_cost=43032,
   depreciation=197730, interest_expense=95466, share_jv=10449, exceptional_items=-11697, pbt=77233, tax=34819,
   pat=42414, pat_attributable=37998, eps_basic=9.51, total_assets=2332652, current_assets=182038,
   current_liabilities=634597, inventories=488, current_investments=16923, trade_receivables=47402,
   cash_and_equivalents=12817, other_bank=38166, total_equity=674563, minority_interest_bs=68750,
   total_debt=896373+129442+47062, lease_liabilities=0, trade_payables=268537,
   net_fixed_assets=620088, cwip=23942, rou=0, goodwill_intangibles=338082+824181+84443,
   cfo=282799, capex=223030, spectrum_paid=155673+9804, acquisitions=283, dividends_paid=6543,
   lease_paid=3899, interest_paid=58566, equity_issued=0, buybacks=0,
   shares_basic_k=3995817, shares_ye_k=3997400, adj_basic=F19 * F21, adj=F19 * F21,
   note="AR FY2018 comparatives (AR FY2017 original: CFO 292309, TA 2327502 - reclassification of dividends received and bank balances)"),
 "FY2016": dict(src="AR17", revenue=965321, other_income=871+16326-1024, opex_total=625479, employee_cost=49108,
   depreciation=174498, interest_expense=85461, share_jv=10666, exceptional_items=21741, pbt=128463, tax=59533,
   pat=68930, pat_attributable=60767, eps_basic=15.21, total_assets=2257232, current_assets=228552,
   current_liabilities=586604, inventories=1692, current_investments=16159, trade_receivables=55039,
   cash_and_equivalents=37087, other_bank=13900, total_equity=667693, minority_interest_bs=54981,
   total_debt=892686+57238+54602, lease_liabilities=0, trade_payables=255806,
   net_fixed_assets=610508, cwip=47304, rou=0, goodwill_intangibles=428381+684039+9716,
   cfo=279423, capex=193313, spectrum_paid=81452, acquisitions=135, dividends_paid=10679,
   lease_paid=2593, interest_paid=32890, equity_issued=0, buybacks=0,
   shares_basic_k=3995870, shares_ye_k=3997400, adj_basic=F19 * F21, adj=F19 * F21,
   note="Ind AS comparatives in AR FY2017 (first Ind AS year; transition date 1-Apr-2015); CFO includes dividends received from JV"),
 "FY2015": dict(src="QR15", revenue=920394, other_income=957+24788-1669, opex_total=607468,
   depreciation=155311, interest_expense=73252, share_jv=7223, exceptional_items=-7960, pbt=107130, tax=54047,
   pat=53083, pat_attributable=51835, eps_basic=12.97, total_assets=1957818, current_assets=267655,
   current_liabilities=634435, inventories=1339, current_investments=92840, trade_receivables=67252,
   cash_and_equivalents=11719, total_equity=619564, minority_interest_bs=48525,
   total_debt=452283+211389+143167, lease_liabilities=0, trade_payables=339670,
   net_fixed_assets=579157, goodwill_intangibles=922283,
   cfo=276018, capex=146411, spectrum_paid=65970, acquisitions=358, dividends_paid=16034,
   interest_paid=33887, equity_issued=0, buybacks=0,
   shares_ye_k=3997400, adj_basic=F19 * F21, adj=F19 * F21,
   note="IFRS; total_debt incl. deferred payment liability 143167 per net-debt schedule; receivables/payables are 'trade and other'; CFO incl. dividends from JV 16407"),
 "FY2014": dict(src="QR15", revenue=857461, other_income=1174+11680-660, opex_total=580205,
   depreciation=156496, interest_expense=60060, share_jv=5211, exceptional_items=538, pbt=78643, tax=48449,
   pat=30194, pat_attributable=27727, eps_basic=7.02, total_assets=1831772, current_assets=223857,
   current_liabilities=568050, inventories=1422, current_investments=62265, trade_receivables=62441,
   cash_and_equivalents=49808, total_equity=597560, minority_interest_bs=42102,
   total_debt=549919+209039+1026, lease_liabilities=0, trade_payables=283981,
   net_fixed_assets=596429, goodwill_intangibles=809716,
   cfo=262326, capex=114159, spectrum_paid=64860, acquisitions=6044, dividends_paid=4439,
   interest_paid=37620, equity_issued=67956, buybacks=0,
   shares_ye_k=3997400, adj_basic=F19 * F21, adj=F19 * F21,
   note="IFRS (Q4FY2015 comparatives); equity_issued = Qatar Foundation Endowment preferential allotment"),
 "FY2013": dict(src="QR14", revenue=769045, other_income=425+5103, opex_total=536891,
   depreciation=148147, interest_expense=45187, share_jv=3506, exceptional_items=0, pbt=47854, tax=25184,
   pat=22669, pat_attributable=22757, eps_basic=6.00, total_assets=1592253, current_assets=196906,
   current_liabilities=420547, inventories=1109, current_investments=65546, trade_receivables=67824,
   cash_and_equivalents=16078, total_equity=503217, minority_interest_bs=40886,
   total_debt=569137+98226, lease_liabilities=0, trade_payables=259902,
   net_fixed_assets=638277, goodwill_intangibles=648386,
   cfo=227699, capex=125722+5744, spectrum_paid=0, acquisitions=0, dividends_paid=4412,
   interest_paid=34339, equity_issued=0, buybacks=0,
   shares_ye_k=3797530, adj_basic=F19 * F21, adj=F19 * F21,
   note="IFRS restated for IFRS 11 (Indus equity-accounted) in Q4FY2014 report"),
 "FY2012": dict(src="QR12", revenue=714508, other_income=550+2643, opex_total=477935,
   depreciation=133681, interest_expense=40828, share_jv=-74, exceptional_items=0, pbt=65183, tax=22602,
   pat=42581, pat_attributable=42594, eps_basic=11.22, total_assets=1570616, current_assets=148084,
   current_liabilities=488873, inventories=1308, current_investments=18132, trade_receivables=63735,
   cash_and_equivalents=20300, total_equity=506113, minority_interest_bs=27695,
   total_debt=497154+193078, lease_liabilities=0, trade_payables=232650,
   net_fixed_assets=674932, goodwill_intangibles=660889,
   cfo=225252, capex=143363+6921, spectrum_paid=0, acquisitions=24985, dividends_paid=4411,
   interest_paid=32352, equity_issued=0, buybacks=0,
   shares_ye_k=3797530, adj_basic=F19 * F21, adj=F19 * F21,
   note="IFRS pre-IFRS 11 (Indus 42% proportionately consolidated): scope break vs FY2013+"),
 "FY2011": dict(src="QR12", revenue=595383, other_income=635+3536, opex_total=395300,
   depreciation=102066, interest_expense=25349, share_jv=-57, exceptional_items=0, pbt=76782, tax=17790,
   pat=58992, pat_attributable=60467, eps_basic=15.93, total_assets=1465064, current_assets=112077,
   current_liabilities=369845, inventories=2139, current_investments=6224, trade_receivables=54929,
   cash_and_equivalents=9575, total_equity=487668, minority_interest_bs=28563,
   total_debt=532338+84370, lease_liabilities=0, trade_payables=239684,
   net_fixed_assets=651426, goodwill_intangibles=637317,
   cfo=188513, capex=109169, spectrum_paid=167925, acquisitions=373991, dividends_paid=4428,
   interest_paid=21595, equity_issued=0, buybacks=0, cf_src="QR11",
   shares_ye_k=3797530, adj_basic=F19 * F21, adj=F19 * F21,
   note="IFRS pre-IFRS 11 (Q4FY2012 comparatives); cash flow from Q4FY2011 report; first year with Zain Africa (acquired Jun-2010)"),
}

MONEY = ["revenue", "other_income", "employee_cost", "depreciation", "interest_expense", "exceptional_items",
         "pbt", "tax", "pat", "pat_attributable", "total_assets", "current_assets", "current_liabilities",
         "inventories", "current_investments", "trade_receivables", "cash_and_equivalents", "total_equity",
         "minority_interest_bs", "total_debt", "lease_liabilities", "trade_payables", "net_fixed_assets", "cwip",
         "goodwill_intangibles", "cfo", "capex", "acquisitions", "dividends_paid", "buybacks", "equity_issued"]
CF_ITEMS = {"cfo", "capex", "acquisitions", "dividends_paid", "buybacks", "equity_issued"}


def main():
    rows = []
    for period, d in D.items():
        tier, url, loc, ver = SRC[d["src"]]
        note = d.get("note", "")
        for k in MONEY:
            if k not in d:
                continue
            t, u, l, v = tier, url, loc, ver
            if k in CF_ITEMS and d.get("cf_src"):
                t, u, l, v = SRC[d["cf_src"]]
            rows.append([k, period, round(d[k] / 10.0, 1), "INR crore", "consolidated", t, u, l, v,
                         "INR mn/10" + ("; " + note if note else "")])
        ebitda = d["revenue"] - d["opex_total"]
        rows.append(["ebitda", period, round(ebitda / 10.0, 1), "INR crore", "consolidated", tier, url, loc, ver,
                     "revenue - total operating expenses (excl. other income)" + ("; post Ind AS 116" if int(period[2:]) >= 2020 else "; pre Ind AS 116")])
        # shares (crore shares = '000 / 10000), bonus-element adjusted
        if "shares_basic_k" in d:
            sb = d["shares_basic_k"] * d.get("adj_basic", 1.0) / 10000.0
            rows.append(["shares_basic", period, round(sb, 4), "crore shares", "consolidated", tier, url,
                         loc + "; EPS note weighted average basic", ver,
                         "'000/10000 x rights bonus factor %.5f" % d.get("adj_basic", 1.0)])
        else:
            sb = d["pat_attributable"] / d["eps_basic"] / 10.0  # INR mn / INR per share = mn shares -> crore
            rows.append(["shares_basic", period, round(sb, 4) * 1.0 * d.get("adj_basic", 1.0), "crore shares", "consolidated", tier, url,
                         loc + "; derived = pat_attributable / basic EPS", "N",
                         "derived (pat_attributable/eps_basic) x rights bonus factor %.5f" % d.get("adj_basic", 1.0)])
        sy = d["shares_ye_k"] * d.get("adj", 1.0) / 10000.0
        rows.append(["shares_diluted", period, round(sy, 4), "crore shares", "consolidated", tier, url,
                     loc + "; year-end issued shares incl. partly paid (SOCE / issued capital)", ver,
                     "YEAR-END issued shares x rights bonus factor %.5f (used for BVPS / FCF per share)" % d.get("adj", 1.0)])
    rows.sort(key=lambda r: (r[0], r[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["item", "period", "value", "unit", "basis", "source_tier", "source_url_or_id", "locator", "verified", "note"])
        w.writerows(rows)
    # side table: non-standard telecom items (INR crore)
    side = RUN / "calc" / "financials_side_items.csv"
    with open(side, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["period", "spectrum_paid", "lease_paid", "interest_paid", "rou", "other_bank", "share_jv", "opex_total", "ebitda"])
        for period, d in sorted(D.items()):
            w.writerow([period] + [round(d.get(k, 0) / 10.0, 1) if d.get(k) is not None else "" for k in
                                   ("spectrum_paid", "lease_paid", "interest_paid", "rou", "other_bank", "share_jv", "opex_total")]
                       + [round((d["revenue"] - d["opex_total"]) / 10.0, 1)])
    print("wrote", OUT, len(rows), "rows;", side)


if __name__ == "__main__":
    main()
