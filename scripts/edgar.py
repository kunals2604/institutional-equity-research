#!/usr/bin/env python3
"""The US path (v4.0): SEC EDGAR for filings and reported facts, Nasdaq for prices, the Treasury for the risk-free rate.

  python3 scripts/edgar.py index --run RUN_DIR --cik CIK [--years 15]   # EDGAR submissions -> the run's exchange index
  python3 scripts/edgar.py facts --run RUN_DIR [--cik CIK]              # XBRL company facts -> calc/xbrl_facts.csv
  python3 scripts/edgar.py prices SYMBOL [--run RUN_DIR] [--years 10]   # daily closes (Nasdaq quote API, unofficial)
  python3 scripts/edgar.py treasury --date YYYY-MM-DD                   # the 10-year par yield that day
  python3 scripts/edgar.py cik TICKER                                   # needs a declared user agent (below)

What was measured on 2026-11-04 (config/jurisdictions/US.json): data.sec.gov serves submissions and company facts to
any client; www.sec.gov, which holds the ticker list and the filing documents, answers 403 unless the client declares
who it is. SEC's fair-access policy asks for that anyway: set EQUITY_RESEARCH_USER_AGENT to a name and contact address
(netfetch.py sends it to sec.gov only). Stooq now sits behind a JavaScript bot check and is not used. Nasdaq's quote
API serves ten years of daily closes, adjusted for splits but not for dividends; it is unofficial and may change. The
Treasury's daily par yield curve is official. No free S&P 500 total-return series was found.

The facts are what `xbrl_facts.py extract` writes for an Indian run, in the same columns and units (USD million), so
the reconciliation, the forecasting tools and the warehouse take them unchanged. Every value keeps the date its filing
was filed: that is when the market could know it.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

SUBMISSIONS = "https://data.sec.gov/submissions/CIK%010d.json"
SUBMISSIONS_PAGE = "https://data.sec.gov/submissions/%s"
FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/%d/%s/"
TICKERS = "https://www.sec.gov/files/company_tickers.json"
NASDAQ = "https://api.nasdaq.com/api/quote/%s/historical?assetclass=%s&fromdate=%s&limit=9999&todate=%s"
TREASURY = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/%d/all"
            "?type=daily_treasury_yield_curve&field_tdr_date_value=%d&page&_format=csv")
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A", "10-KT")
UNIT = "USD million"

# us-gaap concepts per metric key (methodology/METRIC_DEFINITIONS.md). Each entry is a list of alternatives tried in
# order, never added together (revenue was SalesRevenueNet before 2018, measured on Apple); each alternative is a list
# of concepts that are added (capex is plant plus intangibles).
CONCEPTS: Dict[str, List[List[str]]] = {
    "revenue": [["RevenueFromContractWithCustomerExcludingAssessedTax"], ["Revenues"], ["SalesRevenueNet"],
                ["RevenueFromContractWithCustomerIncludingAssessedTax"]],
    "cogs": [["CostOfGoodsAndServicesSold"], ["CostOfRevenue"], ["CostOfGoodsSold"]],
    "depreciation": [["DepreciationDepletionAndAmortization"], ["DepreciationAndAmortization"], ["Depreciation"]],
    "ebit": [["OperatingIncomeLoss"]],
    "interest_expense": [["InterestExpense"], ["InterestExpenseNonoperating"], ["InterestExpenseDebt"]],
    "pbt": [["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
            ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]],
    "tax": [["IncomeTaxExpenseBenefit"]],
    "pat": [["ProfitLoss"], ["NetIncomeLoss"]],
    "pat_attributable": [["NetIncomeLoss"], ["NetIncomeLossAvailableToCommonStockholdersBasic"]],
    "total_assets": [["Assets"]],
    "current_assets": [["AssetsCurrent"]],
    "current_liabilities": [["LiabilitiesCurrent"]],
    "cash_and_equivalents": [["CashAndCashEquivalentsAtCarryingValue"], ["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]],
    "total_equity": [["StockholdersEquity"]],
    "minority_interest_bs": [["MinorityInterest"]],
    "total_debt": [["LongTermDebt", "CommercialPaper", "ShortTermBorrowings"],
                   ["LongTermDebtNoncurrent", "LongTermDebtCurrent", "CommercialPaper", "ShortTermBorrowings"]],
    "inventories": [["InventoryNet"]],
    "trade_receivables": [["AccountsReceivableNetCurrent"]],
    "trade_payables": [["AccountsPayableCurrent"]],
    "net_fixed_assets": [["PropertyPlantAndEquipmentNet"]],
    "goodwill_intangibles": [["Goodwill", "IntangibleAssetsNetExcludingGoodwill"]],
    "cfo": [["NetCashProvidedByUsedInOperatingActivities"]],
    "capex": [["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireIntangibleAssets"],
              ["PaymentsToAcquireProductiveAssets"]],
    "dividends_paid": [["PaymentsOfDividends"], ["PaymentsOfDividendsCommonStock"]],
    "buybacks": [["PaymentsForRepurchaseOfCommonStock"]],
    "equity_issued": [["ProceedsFromIssuanceOfCommonStock"]],
    "acquisitions": [["PaymentsToAcquireBusinessesNetOfCashAcquired"]],
    "shares_diluted": [["WeightedAverageNumberOfDilutedSharesOutstanding"]],
    "shares_basic": [["WeightedAverageNumberOfSharesOutstandingBasic"]],
    "shares_outstanding": [["CommonStockSharesOutstanding"]],
    # Lenders: banks file the same taxonomy with their own lines.
    "interest_income": [["InterestAndDividendIncomeOperating"], ["InterestIncomeOperating"]],
    "deposits": [["Deposits"]],
    "advances": [["LoansAndLeasesReceivableNetReportedAmount"], ["FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"]],
    "provisions": [["ProvisionForLoanLeaseAndOtherLosses"], ["ProvisionForLoanAndLeaseLosses"], ["ProvisionForCreditLosses"]],
}
SHARE_ITEMS = ("shares_diluted", "shares_basic", "shares_outstanding")


# ------------------------------------------------------------------------------------------------------------------
# fetching
# ------------------------------------------------------------------------------------------------------------------

def declared() -> bool:
    return bool(os.environ.get("EQUITY_RESEARCH_USER_AGENT", "").strip())


def need_declared(url: str) -> None:
    if "www.sec.gov" in url and not declared():
        raise SystemExit("www.sec.gov refuses clients that do not say who they are (HTTP 403, measured 2026-11-04). Set "
                         "EQUITY_RESEARCH_USER_AGENT to a name and contact address, as SEC's fair-access policy asks, "
                         "then run this again.")


def get_json(url: str, dest: Path):
    import netfetch as nf
    need_declared(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        nf.fetch(url, str(dest), expect="json", retries=3, timeout=90)
    return json.loads(dest.read_text(encoding="utf-8"))


def cik_for(ticker: str, cache: Path) -> int:
    data = get_json(TICKERS, cache / "company_tickers.json")
    for row in data.values():
        if str(row.get("ticker", "")).upper() == ticker.upper():
            return int(row["cik_str"])
    raise ValueError("%s is not in SEC's ticker list" % ticker)


# ------------------------------------------------------------------------------------------------------------------
# filings index
# ------------------------------------------------------------------------------------------------------------------

def doc_type(form: str, items: str) -> str:
    f = form.upper()
    if f in ANNUAL_FORMS:
        return "annual_report"
    if f.startswith("10-Q"):
        return "results"
    if f.startswith("8-K") or f.startswith("6-K"):
        its = set(re.findall(r"\d\.\d\d", items or ""))
        for item, kind in (("2.02", "results"), ("5.07", "voting_results"), ("4.01", "auditor"), ("4.02", "auditor"),
                           ("5.02", "kmp_change"), ("1.01", "acquisition"), ("2.01", "acquisition"), ("1.03", "penalty_order"),
                           ("3.01", "penalty_order"), ("7.01", "press_release"), ("8.01", "press_release")):
            if item in its:
                return kind
        return "other"
    if f in ("DEF 14A", "DEFA14A", "DEFM14A", "PRE 14A"):
        return "agm_egm"
    if f in ("3", "4", "5", "3/A", "4/A", "5/A") or f.startswith("SC 13D") or f.startswith("SC 13G") or f.startswith("SCHEDULE 13"):
        return "insider_sast"
    if f.startswith("S-1") or f.startswith("S-3") or f.startswith("S-8") or f.startswith("424B"):
        return "capital"
    return "other"


def filing_rows(sub: dict, years: int = 15, cutoff: Optional[str] = None, fy_end_month: int = 12) -> List[dict]:
    """Every filing in a submissions record within the window, as the run's exchange index rows."""
    import exchange_index as ei
    cik = int(sub["cik"])
    end = dt.date.fromisoformat(cutoff) if cutoff else dt.date.today()
    start = dt.date(end.year - years, 1, 1)
    recent = sub["filings"]["recent"]
    out = []
    for i, form in enumerate(recent["form"]):
        filed = recent["filingDate"][i]
        if not filed or not (start.isoformat() <= filed <= end.isoformat()):
            continue
        accn = recent["accessionNumber"][i]
        doc = recent["primaryDocument"][i]
        items = recent.get("items", [""] * len(recent["form"]))[i] or ""
        title = "%s %s%s" % (form, recent.get("primaryDocDescription", [""] * len(recent["form"]))[i] or "",
                             (" (items %s)" % items) if items else "")
        url = ARCHIVE % (cik, accn.replace("-", ""), doc) if doc else FILING_INDEX % (cik, accn.replace("-", ""))
        dtype = doc_type(form, items)
        period = ""
        report = recent.get("reportDate", [""] * len(recent["form"]))[i]
        if dtype == "annual_report" and report:
            period = "FY%d" % fiscal_year(dt.date.fromisoformat(report), fy_end_month)
        out.append(ei.row("EDGAR", dtype, filed, title, "SEC %s" % form, url, fy_end_month, ref=accn, period=period))
    return out


def index(run_dir: Path, cik: int, years: int = 15) -> int:
    """EDGAR's filings for the company, merged into the run's exchange index like any other source."""
    import exchange_index as ei
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    fy = rl.fy_end_month(m)
    cache = run_dir / "_cache" / "index" / "raw"
    sub = get_json(SUBMISSIONS % cik, cache / ("edgar_submissions_%010d.json" % cik))
    for extra in sub["filings"].get("files", []):        # older filings, in pages of their own
        page = get_json(SUBMISSIONS_PAGE % extra["name"], cache / extra["name"])
        for k, v in page.items():
            sub["filings"]["recent"].setdefault(k, []).extend(v)
    ix = ei.Indexer(run_dir, fy)
    ix.rows = filing_rows(sub, years, m.get("research_cutoff"), fy)
    ix.endpoints.append({"label": "edgar_submissions", "url": SUBMISSIONS % cik, "ok": True})
    ix.write()
    return len(ix.rows)


# ------------------------------------------------------------------------------------------------------------------
# reported facts
# ------------------------------------------------------------------------------------------------------------------

def fiscal_year(end: dt.date, fy_end_month: int) -> int:
    """The fiscal year a period ending on `end` belongs to. A 52-53-week year can end a few days into the next month
    (a September year ending on 1 October), so an end in the first week counts as the month before."""
    if end.day <= 7:
        end = end - dt.timedelta(days=7)
    return end.year + (1 if end.month > fy_end_month else 0)


def annual_values(facts: dict, fy_end_month: int, cutoff: Optional[str] = None) -> List[dict]:
    """Every annual value of every mapped metric, one row per filing that reports it: comparatives and restatements
    are kept as versions, each with the date it was filed."""
    gaap = (facts.get("facts") or {}).get("us-gaap", {})
    cik = int(facts.get("cik") or 0)
    # (concept, period end, accession) -> value, for the concepts in each period of each filing
    seen: Dict[Tuple[str, str, str], dict] = {}
    for concept in {c for alts in CONCEPTS.values() for alt in alts for c in alt}:
        for unit, rows in (gaap.get(concept, {}).get("units") or {}).items():
            for r in rows:
                if r.get("form") not in ANNUAL_FORMS or (cutoff and r.get("filed", "") > cutoff):
                    continue
                start, end = r.get("start"), r.get("end")
                if start:
                    days = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days
                    if not 350 <= days <= 380:
                        continue
                seen[(concept, end, r["accn"])] = dict(r, unit=unit, concept=concept)
    out = []
    keys = {(end, accn) for (_c, end, accn) in seen}
    for item, alts in CONCEPTS.items():
        for end, accn in keys:
            for alt in alts:
                got = [seen.get((c, end, accn)) for c in alt]
                if not got[0]:
                    continue
                parts = [g for g in got if g]
                value = sum(g["val"] for g in parts)
                first = parts[0]
                out.append({"item": item, "period": "FY%d" % fiscal_year(dt.date.fromisoformat(end), fy_end_month),
                            "value": round(value if item in SHARE_ITEMS else value / 1e6, 4),
                            "unit": "shares" if item in SHARE_ITEMS else UNIT, "basis": "consolidated",
                            "filed": first["filed"], "form": first["form"], "end": end, "accn": accn,
                            "source_url_or_id": FILING_INDEX % (cik, accn.replace("-", "")),
                            "locator": "XBRL us-gaap:%s (%s, %s filed %s)" % ("+".join(g["concept"] for g in parts),
                                                                           ("%s..%s" % (first["start"], end)) if first.get("start") else end,
                                                                           first["form"], first["filed"])})
                break
    return sorted(out, key=lambda r: (r["item"], r["period"], r["filed"]))


def latest(values: List[dict]) -> Tuple[List[dict], List[str]]:
    """One value per metric and year, from the latest filing (as xbrl_facts.extract does), and every restatement."""
    best: Dict[Tuple[str, str], dict] = {}
    problems = []
    for r in values:                                   # sorted by filed, so the last one wins
        key = (r["item"], r["period"])
        if key in best and abs(best[key]["value"] - r["value"]) > 1e-6 * max(1.0, abs(r["value"])):
            problems.append("restatement or comparative difference: %s %s %s (filed %s) vs %s (filed %s)" % (
                r["item"], r["period"], best[key]["value"], best[key]["filed"], r["value"], r["filed"]))
        best[key] = r
    return sorted(best.values(), key=lambda r: (r["item"], r["period"])), problems


COLUMNS = ["item", "period", "value", "unit", "basis", "source_tier", "source_url_or_id", "locator", "verified", "note"]


def write_facts(run_dir: Path, facts: dict, out: Optional[Path] = None) -> Tuple[Path, List[str]]:
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    rows, problems = latest(annual_values(facts, rl.fy_end_month(m), m.get("research_cutoff")))
    out = out or run_dir / "calc" / "xbrl_facts.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(dict(r, source_tier="1", verified="Y", note="SEC EDGAR XBRL company facts (data.sec.gov), as filed"))
    return out, problems


# ------------------------------------------------------------------------------------------------------------------
# prices and the risk-free rate
# ------------------------------------------------------------------------------------------------------------------

def parse_nasdaq(data: dict) -> List[dict]:
    """Daily rows from Nasdaq's quote API: closes adjusted for splits, not for dividends."""
    rows = ((data.get("data") or {}).get("tradesTable") or {}).get("rows") or []

    def num(x):
        try:
            return float(str(x).replace("$", "").replace(",", ""))
        except ValueError:
            return None
    out = []
    for r in rows:
        d = dt.datetime.strptime(r["date"], "%m/%d/%Y").date().isoformat()
        out.append({"date": d, "open": num(r.get("open")), "high": num(r.get("high")), "low": num(r.get("low")),
                    "close": num(r.get("close")), "volume": num(r.get("volume"))})
    return sorted(out, key=lambda r: r["date"])


def prices(symbol: str, cache: Path, years: int = 10, end: Optional[str] = None, asset: str = "stocks") -> List[dict]:
    end = end or dt.date.today().isoformat()
    start = "%d%s" % (int(end[:4]) - years, end[4:])
    path = cache / ("nasdaq_%s_%s_%s.json" % (symbol.upper(), start, end))
    return parse_nasdaq(get_json(NASDAQ % (symbol.upper(), asset, start, end), path))


def parse_treasury(text: str) -> Dict[str, float]:
    reader = csv.DictReader(text.splitlines())
    out = {}
    for r in reader:
        try:
            out[dt.datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat()] = float(r["10 Yr"])
        except (KeyError, ValueError):
            continue
    return out


def treasury_10y(day: str, cache: Path) -> Tuple[str, float, str]:
    """(date, yield in percent, source URL) for the last published day on or before `day`."""
    import netfetch as nf
    year = int(day[:4])
    for y in (year, year - 1):
        url = TREASURY % (y, y)
        path = cache / ("treasury_%d.csv" % y)
        if not path.exists() or y == year:
            path.parent.mkdir(parents=True, exist_ok=True)
            nf.fetch(url, str(path), expect="csv", retries=3, timeout=90)
        series = parse_treasury(path.read_text(encoding="utf-8"))
        days = [d for d in series if d <= day]
        if days:
            d = max(days)
            return d, series[d], url
    raise ValueError("no Treasury yield published on or before %s" % day)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("--run", required=True)
    i.add_argument("--cik", type=int, required=True)
    i.add_argument("--years", type=int, default=15)
    f = sub.add_parser("facts")
    f.add_argument("--run", required=True)
    f.add_argument("--cik", type=int)
    f.add_argument("--out")
    p = sub.add_parser("prices")
    p.add_argument("symbol")
    p.add_argument("--run")
    p.add_argument("--years", type=int, default=10)
    p.add_argument("--asset", default="stocks", choices=["stocks", "etf", "index"])
    t = sub.add_parser("treasury")
    t.add_argument("--date", required=True)
    c = sub.add_parser("cik")
    c.add_argument("ticker")
    a = ap.parse_args(argv)
    cache = (Path(a.run) / "_cache" / "edgar") if getattr(a, "run", None) else rl.ROOT / "research" / "warehouse" / "_cache" / "edgar"
    if a.cmd == "index":
        print("%d EDGAR filings indexed" % index(Path(a.run), a.cik, a.years))
    elif a.cmd == "facts":
        run = Path(a.run)
        cik = a.cik or int(rl.load_json(run / rl.RUN_MANIFEST).get("cik") or 0)
        if not cik:
            ap.error("give --cik (or record it in the manifest)")
        facts = get_json(FACTS % cik, run / "_cache" / "index" / "raw" / ("edgar_companyfacts_%010d.json" % cik))
        out, problems = write_facts(run, facts, Path(a.out) if a.out else None)
        print("facts -> %s" % out)
        for prob in problems[:40]:
            print("  note: %s" % prob)
    elif a.cmd == "prices":
        rows = prices(a.symbol, cache, a.years, asset=a.asset)
        print("%d daily closes for %s, %s to %s (split-adjusted, not dividend-adjusted)" % (
            len(rows), a.symbol.upper(), rows[0]["date"] if rows else "-", rows[-1]["date"] if rows else "-"))
    elif a.cmd == "treasury":
        d, y, url = treasury_10y(a.date, cache)
        print("US 10-year par yield %.2f%% on %s (%s)" % (y, d, url))
    elif a.cmd == "cik":
        print(cik_for(a.ticker, cache))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
