"""v4.0 Step 7: the warehouse, base rates and the lender mapping of the shared XBRL extraction.

Hermetic: every file is built here with the headers and element names of the real exchange files (measured on
2026-11-04 against NSE's and BSE's bhavcopies and HDFC Bank's, Bajaj Finance's and Castrol India's results filings).
One test reads the real bhavcopies when they are on disk.
"""

import csv
import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agent_driver as ad  # noqa: E402
import base_rates as br  # noqa: E402
import reading_audit as ra  # noqa: E402
import research_lib as rl  # noqa: E402
import warehouse as wh  # noqa: E402
import xbrl_facts as xf  # noqa: E402

UDIFF = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,"
         "FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,"
         "TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4")


def udiff_row(src, isin, sym, series, name, close, vol=1000, day="2026-10-23"):
    return ",".join([day, day, "CM", src, "STK", "1", isin, sym, series, "", "", "", "", name, "1", "2", "0.5", str(close),
                     str(close), "1", "", str(close), "", "", str(vol), str(vol * close), "10", "F1", "1", "", "", "", "", ""])


def nse_udiff():
    return "\n".join([UDIFF,
                      udiff_row("NSE", "INE397D01024", "BHARTIARTL", "EQ", "BHARTI AIRTEL LIMITED", 1892.1),
                      udiff_row("NSE", "INF204KB14I2", "NIFTYBEES", "EQ", "NIP IND ETF NIFTY BEES", 280.5),
                      udiff_row("NSE", "IN0020200104", "SGBJUN28", "GB", "2.5%GOLDBONDS2028SR-III", 14004.25)]) + "\n"


def bse_udiff():
    return "\r\n".join([UDIFF,
                        udiff_row("BSE", "INE397D01024", "BHARTIARTL", "A", "BHARTI AIRTEL LTD.", 1970.0, day="2026-10-30"),
                        udiff_row("BSE", "INE183W23014", "IRBINVIT", "IF", "IRB InvIT Fund", 60.0, day="2026-10-30"),
                        udiff_row("BSE", "INE532F07HQ1", "1003EFSL35", "F", "EFSL-10.03%-NCD", 1000.0, day="2026-10-30"),
                        udiff_row("BSE", "IN0020130053", "92GS2030", "G", "920GOI2030", 104.0, day="2026-10-30")]) + "\r\n"


def sec_full(close=1892.1):
    return ("SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, "
            "TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER\n"
            "BHARTIARTL, EQ, 23-Oct-2026, 1880.00, 1885.00, 1900.00, 1870.00, 1892.00, %s, 1890.10, 9870903, 186662.32, "
            "250000, 5000000, 50.65\n"
            "SOMEBOND, N1, 23-Oct-2026, 100, 100, 100, 100, 100, 100, 100, 10, 0.01, 1, 10, 100\n" % close)


def cm_hist():
    text = ("SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,\n"
            "BHARTIARTL,EQ,330,335,328,332.5,332,331,100000,33250000,23-OCT-2019,5000,INE397D01024,\n")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("cm23OCT2019bhav.csv", text)
    return buf.getvalue()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eqr-wh-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = wh.HOME
        wh.HOME = self.tmp / "warehouse"
        self.addCleanup(setattr, wh, "HOME", self.home)
        self.con = wh.connect(self.tmp / "t.sqlite")
        self.addCleanup(self.con.close)

    def write(self, rel, text):
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


class PricesTests(Tmp):
    def test_the_formats_agree_on_the_same_day(self):
        a = {r["symbol"]: r for r in wh.parse_day(sec_full().encode(), "NSE")}
        b = {r["symbol"]: r for r in wh.parse_day(nse_udiff().encode(), "NSE")}
        self.assertEqual(a["BHARTIARTL"]["close"], b["BHARTIARTL"]["close"])
        self.assertEqual(a["BHARTIARTL"]["date"], b["BHARTIARTL"]["date"])
        self.assertAlmostEqual(a["BHARTIARTL"]["value_inr"], 186662.32 * 1e5, places=0)
        self.assertEqual(a["BHARTIARTL"]["delivery_pct"], 50.65)
        self.assertNotIn("SOMEBOND", a, "series outside the equity series are left out")
        self.assertNotIn("SGBJUN28", b)

    def test_the_historical_zip_format(self):
        rows = wh.parse_day(cm_hist(), "NSE")
        self.assertEqual((rows[0]["date"], rows[0]["close"], rows[0]["isin"]), ("2019-10-23", 332.5, "INE397D01024"))

    def test_bse_uses_the_same_parser_and_keeps_its_groups(self):
        rows = {r["symbol"]: r for r in wh.parse_day(bse_udiff().encode(), "BSE")}
        self.assertEqual(rows["BHARTIARTL"]["close"], 1970.0)
        self.assertEqual(rows["BHARTIARTL"]["series"], "A")

    def test_an_unknown_file_is_refused(self):
        with self.assertRaises(ValueError):
            wh.parse_day(b"a,b,c\n1,2,3\n", "NSE")

    def test_isin_kinds_and_the_equity_universe(self):
        self.assertEqual([wh.isin_kind(i) for i in ("INE397D01024", "INF204KB14I2", "IN0020200104", "INE183W23014",
                                                    "INE637H20024", "INE532F07HQ1", "IN9397D01014", "", "XYZ")],
                         ["equity", "fund", "government", "trust_units", "rights", "debt", "partly_paid", "unknown", "unknown"])
        wh.ingest_day(self.con, "NSE", nse_udiff().encode(), "n")
        wh.ingest_day(self.con, "BSE", bse_udiff().encode(), "b")
        self.assertEqual(wh.universe(self.con, "2026-10-23", "NSE"), ["BHARTIARTL"], "the ETF is not a company")
        self.assertEqual(wh.universe(self.con, "2026-10-30", "BSE"), ["BHARTIARTL"])

    def test_a_symbol_whose_isin_was_never_seen_stays_in_the_universe(self):
        wh.ingest_day(self.con, "NSE", sec_full().encode(), "s")
        self.assertEqual(wh.universe(self.con, "2026-10-23", "NSE"), ["BHARTIARTL"])

    def test_the_isin_learnt_on_one_day_serves_every_day(self):
        wh.ingest_day(self.con, "NSE", sec_full().encode(), "s")
        wh.ingest_day(self.con, "NSE", nse_udiff().encode(), "n")
        self.assertEqual(self.con.execute("SELECT isin, kind FROM securities WHERE symbol = 'BHARTIARTL'").fetchone(),
                         ("INE397D01024", "equity"))

    def test_a_range_is_resumable_and_holidays_are_remembered(self):
        import datetime as dt
        calls = []

        def fetch(exchange, day, cache):
            calls.append(day)
            if day == dt.date(2026, 10, 21):
                return None                                   # a holiday: no file
            return "u", sec_full().replace("23-Oct-2026", day.strftime("%d-%b-%Y")).encode()

        got = wh.ingest_range(self.con, "NSE", dt.date(2026, 10, 19), dt.date(2026, 10, 25), sleep=0, fetch=fetch, log=lambda *_: None)
        self.assertEqual(len(calls), 5, "weekends are never fetched")
        self.assertEqual((got["days"], got["no_file"]), (4, 1))
        calls.clear()
        wh.ingest_range(self.con, "NSE", dt.date(2026, 10, 19), dt.date(2026, 10, 25), sleep=0, fetch=fetch, log=lambda *_: None)
        self.assertEqual(calls, [], "a day done, or known to have no file, is not fetched again")


BANK_XBRL = """<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-bse-fin="http://example/fin">
<xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="s">BANKCO</xbrli:identifier></xbrli:entity>
<xbrli:period><xbrli:endDate>2023-03-31</xbrli:endDate></xbrli:period></xbrli:context>
<in-bse-fin:NatureOfReportStandaloneConsolidated contextRef="OneD">{basis}</in-bse-fin:NatureOfReportStandaloneConsolidated>
<in-bse-fin:DateOfStartOfFinancialYear contextRef="OneD">2022-04-01</in-bse-fin:DateOfStartOfFinancialYear>
<in-bse-fin:DateOfEndOfReportingPeriod contextRef="OneD">2023-03-31</in-bse-fin:DateOfEndOfReportingPeriod>
<in-bse-fin:DateOfEndOfReportingPeriod contextRef="FourD">2023-03-31</in-bse-fin:DateOfEndOfReportingPeriod>
<in-bse-fin:InterestEarned contextRef="FourD">1615855500000</in-bse-fin:InterestEarned>
<in-bse-fin:InterestExpended contextRef="FourD">774800000000</in-bse-fin:InterestExpended>
<in-bse-fin:ProfitLossFromOrdinaryActivitiesBeforeTax contextRef="FourD">587400000000</in-bse-fin:ProfitLossFromOrdinaryActivitiesBeforeTax>
<in-bse-fin:ProfitLossForThePeriod contextRef="FourD">441087100000</in-bse-fin:ProfitLossForThePeriod>
<in-bse-fin:ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates contextRef="FourD">441087100000</in-bse-fin:ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates>
<in-bse-fin:ProvisionsOtherThanTaxAndContingencies contextRef="FourD">119196000000</in-bse-fin:ProvisionsOtherThanTaxAndContingencies>
<in-bse-fin:PurchaseOfTangibleAssetsClassifiedAsInvestingActivities contextRef="FourD">30000000000</in-bse-fin:PurchaseOfTangibleAssetsClassifiedAsInvestingActivities>
<in-bse-fin:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities contextRef="FourD">0</in-bse-fin:PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities>
<in-bse-fin:GrossNonPerformingAssets contextRef="FourD">{gnpa}</in-bse-fin:GrossNonPerformingAssets>
<in-bse-fin:PercentageOfGrossNpa contextRef="FourD">{gnpa_pct}</in-bse-fin:PercentageOfGrossNpa>
<in-bse-fin:CET1Ratio contextRef="FourD">0.188</in-bse-fin:CET1Ratio>
<in-bse-fin:Advances contextRef="OneI">16005859000000</in-bse-fin:Advances>
<in-bse-fin:Deposits contextRef="OneI">18833947000000</in-bse-fin:Deposits>
<in-bse-fin:Capital contextRef="OneI">5579000000</in-bse-fin:Capital>
<in-bse-fin:ReservesAndSurplus contextRef="OneI">2795102000000</in-bse-fin:ReservesAndSurplus>
<in-bse-fin:Assets contextRef="OneI">24660815000000</in-bse-fin:Assets>
</xbrli:xbrl>"""

NBFC_XBRL = """<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in="http://example/in">
<in:NatureOfReportStandaloneConsolidated contextRef="OneD">Consolidated</in:NatureOfReportStandaloneConsolidated>
<in:DateOfStartOfReportingPeriod contextRef="FourD">2019-04-01</in:DateOfStartOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="FourD">2020-03-31</in:DateOfEndOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="OneD">2020-03-31</in:DateOfEndOfReportingPeriod>
<in:InterestEarned contextRef="FourD">230000000000</in:InterestEarned>
<in:RevenueFromOperations contextRef="FourD">263850000000</in:RevenueFromOperations>
<in:FinanceCosts contextRef="FourD">94730000000</in:FinanceCosts>
<in:ImpairmentOnFinancialInstruments contextRef="FourD">39290000000</in:ImpairmentOnFinancialInstruments>
<in:ProfitBeforeTax contextRef="FourD">70000000000</in:ProfitBeforeTax>
<in:ProfitLossForPeriod contextRef="FourD">52637600000</in:ProfitLossForPeriod>
<in:ProfitOrLossAttributableToOwnersOfParent contextRef="FourD">0</in:ProfitOrLossAttributableToOwnersOfParent>
<in:Loans contextRef="OneI">1473700000000</in:Loans>
<in:DebtSecurities contextRef="OneI">500000000000</in:DebtSecurities>
<in:Borrowings contextRef="OneI">400000000000</in:Borrowings>
<in:SubordinatedLiabilities contextRef="OneI">40000000000</in:SubordinatedLiabilities>
<in:EquityShareCapital contextRef="OneI">1200000000</in:EquityShareCapital>
<in:OtherEquity contextRef="OneI">366000000000</in:OtherEquity>
<in:Assets contextRef="OneI">1800000000000</in:Assets>
</xbrli:xbrl>"""


def integrated(rows_pl, rows_bs, basis="Standalone"):
    def table(rows, cols):
        head = ("<tr><td>A</td><td>Date of start of reporting period</td>%s</tr>"
                "<tr><td>B</td><td>Date of end of reporting period</td>%s</tr>" % (
                    "".join("<td>%s</td>" % s for s, _ in cols), "".join("<td>%s</td>" % e for _, e in cols)))
        return "<table>%s%s</table>" % (head, "".join("<tr><td></td><td>%s</td>%s</tr>" % (
            label, "".join("<td>%s</td>" % v for v in vals)) for label, vals in rows))
    return ("<html><body><table><tr><td>Level of rounding used in financial results</td><td>Lakhs</td></tr>"
            "<tr><td>Nature of report standalone or consolidated</td><td>%s</td></tr></table>%s%s</body></html>" % (
                basis, table(rows_pl, [("01-01-2026", "31-03-2026"), ("01-04-2025", "31-03-2026")]),
                table(rows_bs, [("01-04-2025", "31-03-2026")])))


class LenderMappingTests(Tmp):
    def rows(self, text, basis, name="f.xml"):
        p = self.write(name, text)
        return {r["item"]: r for r in xf.rows_from_filing(str(p), "u", basis, "INR crore", 3, False)}

    def test_a_bank_filing_before_fy2024_parses_through_the_financial_year_start(self):
        got = self.rows(BANK_XBRL.format(basis="Standalone", gnpa="180190338000", gnpa_pct="0.0112"), "standalone")
        self.assertEqual(got["pat"]["period"], "FY2023")
        self.assertEqual(got["pat"]["value"], 44108.71)
        self.assertEqual(got["interest_income"]["value"], 161585.55)
        self.assertEqual(got["deposits"]["value"], 1883394.7)
        self.assertEqual(got["total_equity"]["value"], 280068.1, "capital + reserves and surplus")
        self.assertEqual(got["capex"]["value"], 3000.0, "a bank's capex is its tangible plus intangible purchases")
        self.assertEqual(got["gnpa"]["value"], 18019.0338)
        self.assertEqual((got["other:gnpa_ratio_reported"]["value"], got["other:gnpa_ratio_reported"]["unit"]), (0.0112, "fraction"))
        self.assertNotIn("tier1_ratio", got, "the filed CET1 ratio carried the total capital ratio, so it is not mapped")

    def test_a_consolidated_bank_filing_with_zero_asset_quality_records_none(self):
        got = self.rows(BANK_XBRL.format(basis="Consolidated", gnpa="0", gnpa_pct="0"), "consolidated")
        self.assertNotIn("gnpa", got)
        self.assertNotIn("other:gnpa_ratio_reported", got)
        self.assertIn("pat", got)

    def test_an_nbfc_keeps_the_general_items_and_gains_the_lender_ones(self):
        got = self.rows(NBFC_XBRL, "consolidated")
        self.assertEqual(xf.lender_format(n for n, _ in xf.parse_xbrl(str(self.tmp / "f.xml"))[1]), "nbfc")
        self.assertEqual(got["revenue"]["value"], 26385.0)
        self.assertEqual(got["interest_expense"]["value"], 9473.0, "finance costs, from the general map")
        self.assertEqual(got["pat"]["value"], 5263.76)
        self.assertEqual(got["provisions"]["value"], 3929.0)
        self.assertEqual(got["advances"]["value"], 147370.0)
        self.assertEqual(got["borrowings"]["value"], 94000.0, "debt securities + borrowings + subordinated liabilities")
        self.assertEqual(got["total_equity"]["value"], 36720.0)

    def test_an_owners_share_filed_as_zero_is_not_a_fact(self):
        self.assertNotIn("pat_attributable", self.rows(NBFC_XBRL, "consolidated"))

    def test_a_standalone_owners_share_filed_as_zero_is_the_profit(self):
        text = NBFC_XBRL.replace("Consolidated", "Standalone")
        got = self.rows(text, "standalone")
        self.assertEqual(got["pat_attributable"]["value"], got["pat"]["value"])
        self.assertIn("filed as 0", got["pat_attributable"]["locator"])

    def test_a_non_lender_filing_is_not_a_lender(self):
        self.assertEqual(xf.lender_format(["RevenueFromOperations", "InterestEarned", "Loans"]), "")

    def test_a_bank_integrated_filing(self):
        html = integrated([("total interest earned", ["7,661,002.00", "30,752,208.00"]),
                           ("other income", ["1", "6,253,257.00"]), ("total income", ["1", "37,005,465.00"]),
                           ("interest expenses", ["1", "17,883,604.00"]),
                           ("operating profit before provision and contingencies", ["1", "11,855,828.00"]),
                           ("provisions other than tax and contingencies", ["1", "2,338,959.00"]),
                           ("net profit (loss) for the period", ["1", "7,467,129.00"]),
                           ("amount of gross non-performing assets", ["1", "3,406,119.00"]),
                           ("% of gross npas", ["1", "1.15"]), ("cet 1 ratio", ["1", "19.71"])],
                          [("capital", ["153,934.00"]), ("reserves and surplus", ["55,681,645.00"]),
                           ("deposits", ["310,525,048.00"]), ("advances", ["293,716,626.00"]),
                           ("total capital liabilities", ["436,488,632.00"]), ("total assets", ["436,488,632.00"])])
        p = self.write("INTEGRATED_FILING_BANKING_1_iXBRL_WEB.html", html)
        got = {r["item"]: r for r in xf.rows_from_integrated(str(p), "u", "standalone", "INR crore", 3, False)}
        self.assertEqual(got["interest_income"]["value"], 307522.08)
        self.assertEqual(got["pat"]["value"], 74671.29)
        self.assertEqual(got["deposits"]["value"], 3105250.48)
        self.assertEqual(got["total_equity"]["value"], 558355.79)
        self.assertEqual((got["other:gnpa_ratio_reported"]["value"], got["other:gnpa_ratio_reported"]["unit"]), (0.0115, "fraction"),
                         "a percent in the rendering is stored as the fraction the XBRL files use")
        self.assertNotIn("tier1_ratio", got)

    def test_an_nbfc_integrated_filing_reads_total_revenue_from_operations(self):
        html = integrated([("interest income", ["1", "4,000,000.00"]), ("total revenue from operations", ["1", "5,000,000.00"]),
                           ("total income", ["1", "5,010,000.00"]), ("impairment on financial instruments", ["1", "600,000.00"]),
                           ("total profit (loss) for period", ["1", "1,900,000.00"])],
                          [("loans", ["40,000,000.00"]), ("total assets", ["56,000,000.00"]),
                           ("total equity and liabilites", ["56,000,000.00"])], basis="Consolidated")
        p = self.write("INTEGRATED_FILING_NBFC_INDAS_1_iXBRL_WEB.html", html)
        got = {r["item"]: r["value"] for r in xf.rows_from_integrated(str(p), "u", "consolidated", "INR crore", 3, False)}
        self.assertEqual(got["revenue"], 50000.0)
        self.assertEqual(got["interest_income"], 40000.0)
        self.assertEqual(got["provisions"], 6000.0)
        self.assertEqual(got["advances"], 400000.0)


def results_row(xbrl, to_date, broadcast, basis="Consolidated", relating="Annual"):
    return {"xbrl": xbrl, "toDate": to_date, "broadCastDate": broadcast, "consolidated": basis, "relatingTo": relating}


NONLENDER = """<?xml version="1.0"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in="http://example/in">
<in:NatureOfReportStandaloneConsolidated contextRef="OneD">Consolidated</in:NatureOfReportStandaloneConsolidated>
<in:DateOfStartOfReportingPeriod contextRef="FourD">{start}</in:DateOfStartOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="FourD">{end}</in:DateOfEndOfReportingPeriod>
<in:DateOfEndOfReportingPeriod contextRef="OneD">{end}</in:DateOfEndOfReportingPeriod>
<in:RevenueFromOperations contextRef="FourD">{revenue}</in:RevenueFromOperations>
<in:ProfitLossForPeriod contextRef="FourD">10000000000</in:ProfitLossForPeriod>
<in:ProfitOrLossAttributableToOwnersOfParent contextRef="FourD">9000000000</in:ProfitOrLossAttributableToOwnersOfParent>
<in:EquityAttributableToOwnersOfParent contextRef="OneI">60000000000</in:EquityAttributableToOwnersOfParent>
<in:NonControllingInterest contextRef="OneI">{nci}</in:NonControllingInterest>
<in:Assets contextRef="OneI">100000000000</in:Assets>
</xbrli:xbrl>"""


class CrawlTests(Tmp):
    def company(self, symbol, filings):
        """A fake index and fake downloads: filings is [(url, to_date, broadcast, xml)]."""
        def index(work, sym):
            raw = work / "_cache" / "index" / "raw"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "nse_results_annual.json").write_text(json.dumps(
                [results_row(u, t, b) for u, t, b, _ in filings]), encoding="utf-8")
        texts = {u: x for u, _, _, x in filings}

        def download(url, dest):
            Path(dest).write_text(texts[url], encoding="utf-8")
        return index, download

    def test_each_filing_is_a_version_with_its_own_known_at(self):
        f1 = NONLENDER.format(start="2023-04-01", end="2024-03-31", revenue="100000000000", nci="0")
        f2 = NONLENDER.format(start="2023-04-01", end="2024-03-31", revenue="98000000000", nci="0")   # a later restatement
        index, dl = self.company("ACME", [("https://x/a1.xml", "31-Mar-2024", "25-Apr-2024 21:15:01", f1),
                                          ("https://x/a2.xml", "31-Mar-2024", "20-May-2024 10:00:00", f2)])
        wh.crawl_symbol(self.con, "ACME", index=index, download=dl, pause=0)
        got = self.con.execute("SELECT value, known_at FROM facts WHERE metric = 'revenue' ORDER BY known_at").fetchall()
        self.assertEqual(got, [(10000.0, "2024-04-25"), (9800.0, "2024-05-20")])
        self.assertEqual(br.series(self.con, "revenue", "2024-05-01")["ACME"][2024], 10000.0, "what was known on 1 May")
        self.assertEqual(br.series(self.con, "revenue", "2024-06-01")["ACME"][2024], 9800.0)
        self.assertNotIn("ACME", br.series(self.con, "revenue", "2024-04-24"), "nothing before the first broadcast")

    def test_a_filing_with_no_broadcast_date_gives_no_fact(self):
        f = NONLENDER.format(start="2023-04-01", end="2024-03-31", revenue="1", nci="0")
        index, dl = self.company("ACME", [("https://x/a.xml", "31-Mar-2024", "", f)])
        self.assertEqual(wh.crawl_symbol(self.con, "ACME", index=index, download=dl, pause=0), 0)

    def test_an_implausible_value_is_rejected_and_recorded(self):
        f = NONLENDER.format(start="2023-04-01", end="2024-03-31", revenue="1", nci="2986520000000000")
        index, dl = self.company("ACME", [("https://x/a.xml", "31-Mar-2024", "25-Apr-2024 21:15:01", f)])
        wh.crawl_symbol(self.con, "ACME", index=index, download=dl, pause=0)
        self.assertIsNone(self.con.execute("SELECT 1 FROM facts WHERE metric = 'minority_interest_bs'").fetchone())
        self.assertEqual(self.con.execute("SELECT metric FROM rejected").fetchall(), [("minority_interest_bs",)])
        self.assertIsNotNone(self.con.execute("SELECT 1 FROM facts WHERE metric = 'total_equity'").fetchone())

    def test_the_fiscal_year_comes_from_the_company(self):
        f = NONLENDER.format(start="2023-01-01", end="2023-12-31", revenue="5", nci="0")
        index, dl = self.company("CASTROL", [("https://x/c.xml", "31-Dec-2023", "12-Feb-2024 15:00:00", f)])
        wh.crawl_symbol(self.con, "CASTROL", index=index, download=dl, pause=0)
        self.assertEqual(self.con.execute("SELECT DISTINCT period FROM facts").fetchall(), [("FY2023",)])

    def test_a_crawl_resumes_and_retries_failures(self):
        f = NONLENDER.format(start="2023-04-01", end="2024-03-31", revenue="1", nci="0")
        good = self.company("ACME", [("https://x/a.xml", "31-Mar-2024", "25-Apr-2024 21:15:01", f)])
        calls = []

        def index(work, sym):
            calls.append(sym)
            if sym == "BAD":
                raise RuntimeError("results index: nse_results_annual")
            good[0](work, sym)
        got = wh.crawl(self.con, ["ACME", "BAD"], sleep=0, log=lambda *_: None, index=index, download=good[1], pause=0)
        self.assertEqual((got["symbols"], got["failed"]), (1, 1))
        calls.clear()
        wh.crawl(self.con, ["ACME", "BAD"], sleep=0, log=lambda *_: None, index=index, download=good[1], pause=0)
        self.assertEqual(calls, ["BAD"], "a symbol done is skipped; a failed one is tried again")

    def test_annual_and_fourth_quarter_rows_are_read_once(self):
        work = self.tmp / "w"
        raw = work / "_cache" / "index" / "raw"
        raw.mkdir(parents=True)
        (raw / "nse_results_annual.json").write_text(json.dumps([results_row("https://x/a.xml", "31-Mar-2024", "25-Apr-2024 21:15:01")]))
        (raw / "nse_results_quarterly.json").write_text(json.dumps([
            results_row("https://x/a.xml", "31-Mar-2024", "25-Apr-2024 21:15:01", relating="Fourth Quarter"),
            results_row("https://x/q3.xml", "31-Dec-2023", "20-Jan-2024 21:15:01", relating="Third Quarter"),
            results_row("https://x/q4.xml", "31-Mar-2021", "19-Apr-2021 21:15:01", relating="Fourth Quarter")]))
        got = wh.annual_filings(work)
        self.assertEqual(sorted(f["url"] for f in got), ["https://x/a.xml", "https://x/q4.xml"])
        self.assertEqual({f["fy"] for f in got}, {3}, "quarter ends do not vote on the fiscal year")


def finished_run(root: Path, status="complete", verification="PASS", replay=False, flagged=()):
    run = root / "companies" / "ACME" / "runs" / "20261101T000000Z"
    (run / "specialists").mkdir(parents=True)
    (run / "qc" / "verification").mkdir(parents=True)
    rl.write_json(run / rl.RUN_MANIFEST, {"run_id": "20261101T000000Z", "ticker": "ACME", "exchange": "NSE", "status": status,
                                          "replay": replay, "research_cutoff": "2026-10-31", "sector_modules": ["lenders"]})
    rl.write_json(run / "qc" / "verification.json", {"status": verification, "run_findings": []})
    rl.write_json(run / "qc" / "verification" / "financials.json", {"tier_a": [
        {"check": "NUMBER_NOT_SEEN", "claims": ["%s (value 1)" % c for c in flagged], "waived": {"reason": "image"}}]})
    cols = ["claim_id", "tag", "metric", "value", "unit", "period", "basis", "source_url_or_id", "source_date", "locator", "source_tier"]
    rows = [["FIN-C001", "FACT", "revenue", "1,234.5", "INR crore", "FY2026", "consolidated", "https://x/ar.pdf", "2026-05-01", "p 12", "1"],
            ["FIN-C002", "FACT", "pat", "200", "INR crore", "FY2026", "consolidated", "https://x/ar.pdf", "2027-01-01", "p 13", "2"],
            ["FIN-C003", "FACT", "revenue", "999", "INR crore", "FY2025", "consolidated", "https://news.example", "", "", "6"],
            ["FIN-C004", "ESTIMATE", "revenue", "1500", "INR crore", "FY2028", "consolidated", "model", "", "", "1"],
            ["FIN-C005", "FACT", "", "7", "", "FY2026", "", "https://x/ar.pdf", "", "", "1"],
            ["FIN-C006", "FACT", "ebitda", "300", "INR crore", "FY2026", "consolidated", "https://x/ar.pdf", "2026-05-01", "p 14", "1"]]
    with (run / "specialists" / "financials_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    return run


class PromoteTests(Tmp):
    def test_only_verified_tier_1_to_3_facts_are_promoted(self):
        run = finished_run(self.tmp / "research", flagged=["FIN-C006"])
        self.assertEqual([r["claim_id"] for r in wh.promotable(run)], ["FIN-C001", "FIN-C002"])
        self.assertEqual(wh.promote(self.con, run), 2)
        got = dict(self.con.execute("SELECT metric, known_at FROM facts").fetchall())
        self.assertEqual(got["revenue"], "2026-05-01")
        self.assertEqual(got["pat"], "2026-10-31", "a source dated after the cutoff is known no earlier than the cutoff")
        self.assertEqual(self.con.execute("SELECT origin FROM facts WHERE metric = 'revenue'").fetchone()[0],
                         "20261101T000000Z:FIN-C001")

    def test_nothing_is_promoted_from_an_unfinished_failed_or_replayed_run(self):
        for kw in ({"status": "stage_3"}, {"verification": "FAIL"}, {"replay": True}):
            tmp = Path(tempfile.mkdtemp(prefix="eqr-wh-run-"))
            self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
            self.assertEqual(wh.promotable(finished_run(tmp, **kw)), [], kw)

    def test_a_run_reads_only_what_was_known_at_its_cutoff(self):
        wh.add_fact(self.con, "ACME", "revenue", "FY2026", "consolidated", 1234.5, "INR crore", "2026-05-01", "s", "", "1", "xbrl")
        wh.add_fact(self.con, "ACME", "revenue", "FY2027", "consolidated", 1500.0, "INR crore", "2027-05-01", "s", "", "1", "xbrl")
        wh.ingest_day(self.con, "NSE", sec_full().replace("BHARTIARTL", "ACME").encode(), "s")
        wh.ingest_day(self.con, "BSE", bse_udiff().replace("BHARTIARTL", "ACME").encode(), "b")
        self.con.execute("INSERT INTO rejected VALUES ('ACME','minority_interest_bs','FY2026','consolidated',9e9,'u','larger than total assets (1)','t')")
        run = finished_run(self.tmp / "research")
        out = wh.materialise(self.con, run)
        with (out / "facts.csv").open(encoding="utf-8") as f:
            facts = list(csv.DictReader(f))
        self.assertEqual([r["period"] for r in facts], ["FY2026"])
        with (out / "prices.csv").open(encoding="utf-8") as f:
            prices = list(csv.DictReader(f))
        self.assertEqual([(p["date"], p["close"]) for p in prices], [("2026-10-23", "1892.1")], "the run's exchange only")
        text = (out / "FACTS.md").read_text(encoding="utf-8")
        self.assertIn("cite the source each one names", text)
        self.assertIn("minority_interest_bs", text)

    def test_the_knowledge_layers_hold_promoted_facts_only(self):
        root = self.tmp / "repo"
        run = finished_run(root / "research")
        (run.parent.parent / rl.LATEST_POINTER).write_text(run.name, encoding="utf-8")
        wh.promote(self.con, run)
        wh.add_fact(self.con, "ACME", "revenue", "FY2024", "consolidated", 1.0, "", "2024-05-01", "s", "", "1", "xbrl")
        paths = wh.knowledge(self.con, root)
        company = root / "research" / "companies" / "ACME" / "file" / "facts.csv"
        sector = root / "research" / "knowledge" / "sectors" / "lenders" / "facts.csv"
        self.assertEqual(set(paths), {company, sector})
        with company.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(sorted(r["metric"] for r in rows), ["ebitda", "pat", "revenue"])
        self.assertNotIn("FY2024", [r["period"] for r in rows], "exchange XBRL stays in the warehouse")


class BaseRateTests(Tmp):
    def test_cagr_share_and_the_caveat(self):
        for t, start, end in (("A", 100, 300), ("B", 100, 120), ("C", 100, 250), ("D", 0, 50)):
            wh.add_fact(self.con, t, "revenue", "FY2020", "consolidated", start, "", "2020-05-01", "s", "", "1", "xbrl")
            wh.add_fact(self.con, t, "revenue", "FY2025", "consolidated", end, "", "2025-05-01", "s", "", "1", "xbrl")
        got = br.cagr(self.con, "revenue", 5, 0.15, "2026-01-01")
        self.assertEqual(got["companies"], 3, "a company with no positive start is left out")
        self.assertAlmostEqual(got["share_at_or_above"], 2 / 3)
        self.assertIn("Survivor-biased", got["caveat"])
        self.assertEqual(br.cagr(self.con, "revenue", 5, 0.15, "2024-01-01")["companies"], 0, "FY2025 was not yet known")

    def test_consolidated_is_preferred_and_roe_uses_average_equity(self):
        for basis, pat in (("standalone", 50.0), ("consolidated", 60.0)):
            wh.add_fact(self.con, "A", "pat_attributable", "FY2025", basis, pat, "", "2025-05-01", "s", "", "1", "xbrl")
            for y, eq in (("FY2024", 400.0), ("FY2025", 600.0)):
                wh.add_fact(self.con, "A", "total_equity", y, basis, eq, "", "2025-05-01", "s", "", "1", "xbrl")
        self.assertAlmostEqual(br.derived(self.con, "roe", "2026-01-01")["A"][2025], 60.0 / 500.0)

    def test_a_run_gets_its_base_rate_in_its_corpus(self):
        run = finished_run(self.tmp / "research")
        path = br.write(run, br.cagr(self.con, "revenue", 5, 0.15, "2026-10-31"))
        self.assertEqual(path.parent, run / "corpus" / "facts" / "base_rates")


class IndependenceTests(unittest.TestCase):
    def test_agents_are_denied_the_warehouse_and_the_knowledge_layers(self):
        for d in ("research/warehouse/**", "research/knowledge/**", "research/companies/*/file/**"):
            self.assertTrue(any(r.endswith(d + ")") for r in ad.DENY_TRANSCRIPTS), d)
        for s in ("warehouse.py", "base_rates.py"):
            self.assertIn("Bash(python3 scripts/%s:*)" % s, ad.shell_denies())
        self.assertIn("Bash(sqlite3:*)", ad.shell_denies())

    def test_the_audit_flags_a_specialist_that_reaches_for_them(self):
        calls, _ = ra.independence_patterns("moat", "R")
        for cmd in ("sqlite3 research/warehouse/eqr.sqlite 'select 1'", "python3 scripts/base_rates.py cagr --metric revenue",
                    "cat research/companies/ACME/file/facts.csv", "ls research/knowledge/sectors"):
            self.assertIsNotNone(calls.search(cmd), cmd)
        self.assertIsNone(calls.search("cat corpus/facts/facts.csv"), "the materialised facts are the run's own")


NSE_FULL = ROOT / "research" / "outcomes" / "_cache" / "market" / "sec_bhavdata_full_23102026.csv"
NSE_UDIFF = sorted(ROOT.glob("research/companies/BAJFINANCE/runs/*/_cache/cio/*unzipped/BhavCopy_NSE_CM_0_0_0_20261023_F_0000.csv"))


@unittest.skipUnless(NSE_FULL.exists() and NSE_UDIFF, "the real 23 October 2026 bhavcopies are not on disk")
class RealFilesTests(unittest.TestCase):
    def test_the_two_real_nse_formats_agree_for_every_equity(self):
        a = {r["symbol"]: r["close"] for r in wh.parse_day(NSE_FULL.read_bytes(), "NSE")}
        b = {r["symbol"]: r["close"] for r in wh.parse_day(NSE_UDIFF[0].read_bytes(), "NSE")}
        self.assertEqual(len(a), 3425)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
