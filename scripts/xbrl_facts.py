#!/usr/bin/env python3
"""Exchange XBRL results → financial-history rows (tier 1, machine-readable), and reconciliation with the history.

  python3 scripts/xbrl_facts.py extract   --run RUN_DIR [--basis consolidated|standalone] [--unit "INR crore"]
                                          [--quarterly] [--out RUN_DIR/calc/xbrl_facts.csv]
  python3 scripts/xbrl_facts.py reconcile --run RUN_DIR --history specialists/financials_workpapers/financial_history.csv
                                          [--facts RUN_DIR/calc/xbrl_facts.csv] [--tolerance 0.01] [--out ...csv]

`extract` reads the NSE results indices saved by `exchange_index.py nse` (RUN_DIR/_cache/index/raw/): the XBRL
results feed (`nse_results_*.json`, XML filings to FY2024) and the Integrated Filing feed (`nse_integrated_results.json`,
SEBI's format from 2025, published as an exchange-rendered table of the XBRL values), downloads each filing (cached in
RUN_DIR/_cache/xbrl/), and writes rows in the financial_history.csv format: fiscal-year values from the 12-month context of each Q4 (or annual) filing, balance-sheet values at the
year-end instant, cash flow from the 12-month context, and with --quarterly the 3-month values as QnFYyyyy rows.
Values are converted from rupees to --unit (crore 1e7, lakh 1e5, million 1e6, billion 1e9).

Mapping (Ind AS taxonomy used by NSE; `methodology/METRIC_DEFINITIONS.md` keys):
  revenue RevenueFromOperations · other_income OtherIncome · employee_cost EmployeeBenefitExpense ·
  interest_expense FinanceCosts · depreciation DepreciationDepletionAndAmortisationExpense ·
  exceptional_items ExceptionalItemsBeforeTax · pbt ProfitBeforeTax · tax TaxExpense · pat ProfitLossForPeriod ·
  pat_attributable ProfitOrLossAttributableToOwnersOfParent · cfo CashFlowsFromUsedInOperatingActivities ·
  capex PurchaseOfPropertyPlantAndEquipment… + PurchaseOfIntangibleAssets… · dividends_paid · acquisitions ·
  equity_issued · buybacks · total_equity EquityAttributableToOwnersOfParent · minority_interest_bs NonControllingInterest ·
  total_debt BorrowingsNoncurrent + BorrowingsCurrent (leases excluded) · cash_and_equivalents · current_investments ·
  inventories · trade_receivables (current + non-current) · trade_payables (current + non-current) · current_assets ·
  current_liabilities · total_assets Assets · net_fixed_assets PropertyPlantAndEquipment · cwip CapitalWorkInProgress ·
  goodwill_intangibles Goodwill + OtherIntangibleAssets + IntangibleAssetsUnderDevelopment.
Sign convention follows METRIC_DEFINITIONS: cash outflows (capex, dividends, acquisitions, buybacks) are positive.

`reconcile` compares every (item, period, basis) present in both files and writes the gaps; any gap above the
tolerance is a discrepancy the financials specialist must explain (restatement, reclassification, scope, error).
Exit: 0 ok, 1 nothing extracted / discrepancies found (reconcile), 2 usage.
"""

import argparse
import csv
import datetime as dt
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

DURATION_MAP = {
    "revenue": ["RevenueFromOperations"],
    "other_income": ["OtherIncome"],
    "employee_cost": ["EmployeeBenefitExpense"],
    "interest_expense": ["FinanceCosts"],
    "depreciation": ["DepreciationDepletionAndAmortisationExpense"],
    "exceptional_items": ["ExceptionalItemsBeforeTax"],
    "pbt": ["ProfitBeforeTax"],
    "tax": ["TaxExpense"],
    "pat": ["ProfitLossForPeriod"],
    "pat_attributable": ["ProfitOrLossAttributableToOwnersOfParent"],
    "cfo": ["CashFlowsFromUsedInOperatingActivities"],
    "capex": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
              "PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"],
    "dividends_paid": ["DividendsPaidClassifiedAsFinancingActivities"],
    "acquisitions": ["CashFlowsUsedInObtainingControlOfSubsidiariesOrOtherBusinessesClassifiedAsInvestingActivities"],
    "equity_issued": ["ProceedsFromIssuingSharesClassifiedAsFinancingActivities"],
    "buybacks": ["PaymentsToAcquireOrRedeemEntitysShares"],
    # Components kept so that reconcile can name the usual definitional differences.
    "other:share_of_associates_jv": ["ShareOfProfitLossOfAssociatesAndJointVenturesAccountedForUsingEquityMethod"],
    "other:capex_ppe": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
    "other:capex_intangibles": ["PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"],
    "other:interest_paid_financing": ["InterestPaidClassifiedAsFinancingActivities"],
    "other:lease_payments": ["PaymentsOfLeaseLiabilitiesClassifiedAsFinancingActivities"],
}
INSTANT_MAP = {
    "total_equity": ["EquityAttributableToOwnersOfParent"],
    "minority_interest_bs": ["NonControllingInterest"],
    "total_debt": ["BorrowingsNoncurrent", "BorrowingsCurrent"],
    "cash_and_equivalents": ["CashAndCashEquivalents"],
    "current_investments": ["CurrentInvestments"],
    "inventories": ["Inventories"],
    "trade_receivables": ["TradeReceivablesCurrent", "TradeReceivablesNoncurrent"],
    "trade_payables": ["TradePayablesCurrent", "TradePayablesNoncurrent"],
    "current_assets": ["CurrentAssets"],
    "current_liabilities": ["CurrentLiabilities"],
    "total_assets": ["Assets"],
    "net_fixed_assets": ["PropertyPlantAndEquipment"],
    "cwip": ["CapitalWorkInProgress"],
    "goodwill_intangibles": ["Goodwill", "OtherIntangibleAssets", "IntangibleAssetsUnderDevelopment"],
}
# For a standalone filing, NSE tags the owners' equity simply as Equity (no non-controlling interest).
STANDALONE_FALLBACK = {"total_equity": ["Equity"], "pat_attributable": ["ProfitLossForPeriod"]}
SCALE = {"crore": 1e7, "lakh": 1e5, "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9}


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


BASE_CONTEXT_RE = re.compile(r"(One|Two|Three|Four|Five|Six|Seven|Eight)[DI]")


def parse_xbrl(path: str) -> Tuple[Dict[str, dict], Dict[Tuple[str, str], float], Dict[str, str]]:
    """(contexts, facts keyed by (element, context id) for contexts without dimensions, text facts).

    Two quirks of NSE results XBRL are handled (both seen in BHARTIARTL filings, 2019-2024):
      * the year-to-date context (`FourD`) declares the quarter's dates in xbrli:period, while the filing's own
        DateOfStartOfReportingPeriod / DateOfEndOfReportingPeriod facts for that context give the true 12 months;
      * older `_WEB.xml` filings never define the base contexts (`OneD`, `FourD`, `OneI`) the facts refer to.
    So each context's period is taken from those reporting-period facts where they exist, undefined base contexts
    are treated as dimension-free, and an undefined instant context takes the reporting period's end date."""
    root = ET.parse(path).getroot()
    contexts = {}
    for c in root.iter():
        if _local(c.tag) != "context":
            continue
        start = end = instant = None
        dims = False
        for x in c.iter():
            t = _local(x.tag)
            if t == "startDate":
                start = x.text
            elif t == "endDate":
                end = x.text
            elif t == "instant":
                instant = x.text
            elif t in ("explicitMember", "typedMember"):
                dims = True
        contexts[c.get("id")] = {"start": start, "end": end, "instant": instant, "dims": dims}
    raw = []
    for el in root.iter():
        cid = el.get("contextRef")
        if cid:
            raw.append((_local(el.tag), cid, (el.text or "").strip()))
    for name, cid, val in raw:
        if cid not in contexts:
            contexts[cid] = {"start": None, "end": None, "instant": None, "dims": not BASE_CONTEXT_RE.fullmatch(cid)}
        if name == "DateOfStartOfReportingPeriod" and val:
            contexts[cid]["start"] = val
        elif name == "DateOfEndOfReportingPeriod" and val:
            contexts[cid]["end"] = val
    durations = {cid: c for cid, c in contexts.items() if c["end"] and not c["dims"]}
    for cid, c in contexts.items():
        if cid.endswith("I") and not c["dims"] and not c["instant"]:
            same = durations.get(cid[:-1] + "D") or durations.get("OneD") or durations.get("FourD")
            if same:
                c["instant"] = same["end"]
    facts, text = {}, {}
    for name, cid, val in raw:
        c = contexts[cid]
        if c["dims"]:
            continue
        try:
            facts[(name, cid)] = float(val)
        except ValueError:
            if val:
                text[name] = val
    return contexts, facts, text


def ei_parse(s: str) -> Optional[dt.date]:
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s.strip().title(), fmt).date()
        except ValueError:
            continue
    return None


def months_between(start: str, end: str) -> int:
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    return (e.year - s.year) * 12 + e.month - s.month + 1


def unit_scale(unit: str) -> float:
    for word, k in SCALE.items():
        if word in unit.lower():
            return k
    return 1.0


def fy_label(end: str, fy_end_month: int) -> str:
    d = dt.date.fromisoformat(end)
    return "FY%d" % (d.year if fy_end_month == 12 or d.month <= fy_end_month else d.year + 1)


def q_label(end: str, fy_end_month: int) -> str:
    d = dt.date.fromisoformat(end)
    months_after = (d.month - fy_end_month - 1) % 12
    fy = d.year if fy_end_month == 12 or d.month <= fy_end_month else d.year + 1
    return "Q%dFY%d" % (months_after // 3 + 1, fy)


def rows_from_filing(path: str, url: str, basis: str, unit: str, fy_end_month: int, quarterly: bool) -> List[dict]:
    contexts, facts, text = parse_xbrl(path)
    k = unit_scale(unit)
    nature = (text.get("NatureOfReportStandaloneConsolidated") or "").lower()
    if nature and basis not in nature:
        return []
    out = []
    by_ctx: Dict[str, Dict[str, float]] = {}
    for (name, cid), v in facts.items():
        by_ctx.setdefault(cid, {})[name] = v
    for cid, vals in by_ctx.items():
        c = contexts[cid]
        if c["start"] and c["end"]:
            n = months_between(c["start"], c["end"])
            if n == 12:
                period = fy_label(c["end"], fy_end_month)
            elif n == 3 and quarterly:
                period = q_label(c["end"], fy_end_month)
            else:
                continue
            mapping = DURATION_MAP
        elif c["instant"]:
            d = dt.date.fromisoformat(c["instant"])
            if d.month != fy_end_month and not quarterly:
                continue
            period = fy_label(c["instant"], fy_end_month) if d.month == fy_end_month else q_label(c["instant"], fy_end_month)
            mapping = INSTANT_MAP
        else:
            continue
        for item, elements in mapping.items():
            names = [e for e in elements if e in vals]
            if not names and basis == "standalone" and item in STANDALONE_FALLBACK:
                names = [e for e in STANDALONE_FALLBACK[item] if e in vals]
            if not names:
                continue
            value = sum(vals[e] for e in names) / k
            out.append({"item": item, "period": period, "value": round(value, 4), "unit": unit, "basis": basis,
                        "source_tier": "1", "source_url_or_id": url,
                        "locator": "XBRL %s (context %s, %s)" % ("+".join(names), cid,
                                                                c["instant"] or "%s..%s" % (c["start"], c["end"])),
                        "verified": "Y", "note": "NSE results XBRL; machine-readable exchange filing"})
    return out


# Integrated Filing (2025+): NSE publishes the XBRL values as a rendered table with the taxonomy's standard labels.
IF_DURATION = {
    "revenue": ["revenue from operations"], "other_income": ["other income"],
    "employee_cost": ["employee benefit expense"], "interest_expense": ["finance costs"],
    "depreciation": ["depreciation, depletion and amortisation expense"], "exceptional_items": ["exceptional items"],
    "pbt": ["total profit before tax"], "tax": ["total tax expenses"], "pat": ["total profit (loss) for period"],
    "pat_attributable": ["profit or loss, attributable to owners of parent"],
    "other:share_of_associates_jv": ["share of profit (loss) of associates and joint ventures accounted for using equity method"],
}
IF_CASHFLOW = {
    "cfo": ["net cash flows from (used in) operating activities"],
    "capex": ["purchase of property, plant and equipment", "purchase of intangible assets"],
    "other:capex_ppe": ["purchase of property, plant and equipment"],
    "other:capex_intangibles": ["purchase of intangible assets"],
    "dividends_paid": ["dividends paid"],
    "acquisitions": ["cash flows used in obtaining control of subsidiaries or other businesses"],
    "equity_issued": ["proceeds from issuing shares"],
    "buybacks": ["payments to acquire or redeem entity's shares"],
    "other:lease_payments": ["payments of lease liabilities"],
}
IF_INSTANT = {
    "total_equity": ["total equity attributable to owners of parent"], "minority_interest_bs": ["non controlling interest"],
    "total_debt": ["borrowings, non-current", "borrowings, current"], "lease_liabilities": ["- lease liabilities"],
    "cash_and_equivalents": ["cash and cash equivalents"], "current_investments": ["current investments"],
    "inventories": ["inventories"], "trade_receivables": ["trade receivables, current", "trade receivables, non-current"],
    "trade_payables": ["total trade payable"], "current_assets": ["total current assets"],
    "current_liabilities": ["total current liabilities"], "total_assets": ["total assets"],
    "net_fixed_assets": ["property, plant and equipment"], "cwip": ["capital work-in-progress"],
    "goodwill_intangibles": ["goodwill", "other intangible assets", "intangible assets under development"],
}
IF_STANDALONE = {"total_equity": ["total equity"], "pat_attributable": ["total profit (loss) for period"]}
ROUNDING = {"lakhs": 1e5, "lakh": 1e5, "crores": 1e7, "crore": 1e7, "millions": 1e6, "million": 1e6,
            "thousands": 1e3, "thousand": 1e3, "billions": 1e9, "actual": 1.0, "actuals": 1.0, "rupees": 1.0}


def _num(cell: str) -> Optional[float]:
    c = (cell or "").strip().replace(",", "")
    neg = c.startswith("(") and c.endswith(")")
    c = c.strip("()")
    try:
        v = float(c)
    except ValueError:
        return None
    return -v if neg else v


def parse_integrated(path: str) -> Tuple[float, str, List[dict]]:
    """(rupees per reported unit, nature, statements); each statement: {columns: [(start, end)], rows: [(label, values)]}."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import html_tables  # noqa: E402 - local deterministic table extractor
    tables = html_tables.extract(Path(path).read_text(encoding="utf-8", errors="ignore"))
    scale, nature, statements, stated = 1.0, "", [], False
    for tb in tables:
        for r in tb:
            joined = " ".join(r).lower()
            if "level of rounding" in joined and len(r) >= 2 and r[-1].strip().lower() in ROUNDING:
                scale, stated = ROUNDING[r[-1].strip().lower()], True
            m = re.search(r"presentation currency.*\(in\s+([a-z]+)\)", joined)
            if m and not stated and m.group(1).rstrip("s") + "s" in ROUNDING:
                scale, stated = ROUNDING[m.group(1).rstrip("s") + "s"], True
            if "nature of report standalone or consolidated" in joined:
                nature = r[-1].strip().lower()
    if not stated:
        statements.append({"columns": [], "rows": [], "warning": "rounding level not stated: values read as rupees"})
    for tb in tables:
        starts = next((r for r in tb if any("date of start of reporting period" in c.lower() for c in r)), None)
        ends = next((r for r in tb if any("date of end of reporting period" in c.lower() for c in r)), None)
        if not starts or not ends:
            continue
        date_re = r"\d{2}-(?:\d{2}|[A-Za-z]{3})-\d{4}"     # 01-04-2025 (2026 filings) or 01-Apr-2024 (2025 filings)
        s_vals = [c.strip() for c in starts if re.fullmatch(date_re, c.strip())]
        e_vals = [c.strip() for c in ends if re.fullmatch(date_re, c.strip())]
        if not e_vals or len(s_vals) != len(e_vals):
            continue
        k = len(e_vals)
        cols = [(ei_parse(a).isoformat(), ei_parse(b).isoformat()) for a, b in zip(s_vals, e_vals)
                if ei_parse(a) and ei_parse(b)]
        if len(cols) != k:
            continue
        rows, section = [], ""
        for r in tb:
            label = next((c for c in r[:-k] if c.strip() and not re.fullmatch(r"[A-Z0-9]{1,3}|\(?[a-z]\)?", c.strip())), "")
            vals = [_num(c) for c in r[-k:]]
            low = label.strip().lower()
            if low.startswith("net cash flows from (used in) operating"):
                section = "investing"           # rows after the operating total belong to investing, then financing
            elif low.startswith("net cash flows from (used in) investing"):
                section = "financing"
            if label and any(v is not None for v in vals):
                rows.append({"label": low, "values": vals, "section": section})
        statements.append({"columns": cols, "rows": rows})
    return scale, nature, statements


def rows_from_integrated(path: str, url: str, basis: str, unit: str, fy_end_month: int, quarterly: bool) -> List[dict]:
    scale, nature, statements = parse_integrated(path)
    if nature and basis not in nature:
        return []
    k = scale / unit_scale(unit)
    out = []
    for st in statements:
        if st.get("warning"):
            out.append({"item": "other:unit_warning", "period": "", "value": 0, "unit": unit, "basis": basis,
                        "source_tier": "1", "source_url_or_id": url, "locator": st["warning"], "verified": "N",
                        "note": "check the filing's unit before relying on its values"})
            continue
        labels = {r["label"] for r in st["rows"]}
        is_bs = "total equity and liabilites" in labels or "total equity and liabilities" in labels
        is_cf = any(l.startswith("net cash flows from (used in) operating") for l in labels)
        is_pl = "revenue from operations" in labels and "total income" in labels
        if not (is_bs or is_cf or is_pl):
            continue                                  # segment, OCI and ratio tables
        mapping = IF_INSTANT if is_bs else (IF_CASHFLOW if is_cf else IF_DURATION)
        for ci, (start, end) in enumerate(st["columns"]):
            n = months_between(start, end)
            if is_bs:
                period = fy_label(end, fy_end_month) if dt.date.fromisoformat(end).month == fy_end_month else q_label(end, fy_end_month)
                if not quarterly and dt.date.fromisoformat(end).month != fy_end_month:
                    continue
            elif n == 12:
                period = fy_label(end, fy_end_month)
            elif n == 3 and quarterly:
                period = q_label(end, fy_end_month)
            else:
                continue
            for item, labels_wanted in mapping.items():
                wanted = labels_wanted
                if basis == "standalone" and item in IF_STANDALONE and not any(r["label"] in wanted for r in st["rows"]):
                    wanted = IF_STANDALONE[item]
                vals = []
                for r in st["rows"]:
                    if r["label"] in wanted and r["values"][ci] is not None:
                        if is_cf and item in ("dividends_paid", "equity_issued", "buybacks") and r["section"] != "financing":
                            continue
                        vals.append(abs(r["values"][ci]) if is_cf and item != "cfo" else r["values"][ci])
                if not vals:
                    continue
                out.append({"item": item, "period": period, "value": round(sum(vals) * k, 4), "unit": unit, "basis": basis,
                            "source_tier": "1", "source_url_or_id": url,
                            "locator": "Integrated Filing table: %s (%s..%s)" % (" + ".join(wanted), start, end),
                            "verified": "Y", "note": "NSE Integrated Filing (exchange rendering of the XBRL values)"})
    return out


def load_integrated_index(run_dir: Path) -> List[dict]:
    f = run_dir / "_cache" / "index" / "raw" / "nse_integrated_results.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except ValueError:
        return []
    rows = data.get("data") if isinstance(data, dict) else data
    return [r for r in rows or [] if isinstance(r, dict)]


def load_results_index(run_dir: Path) -> List[dict]:
    rows = []
    for f in sorted((run_dir / "_cache" / "index" / "raw").glob("nse_results_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        rows += [r for r in data if isinstance(r, dict)]
    return rows


def extract(run_dir: Path, basis: str, unit: str, quarterly: bool, fy_end_month: int) -> Tuple[List[dict], List[str]]:
    cache = run_dir / "_cache" / "xbrl"
    cache.mkdir(parents=True, exist_ok=True)
    seen, out, problems = set(), [], []
    for r in load_results_index(run_dir):
        url = r.get("xbrl") or ""
        if not url.lower().endswith(".xml") or url in seen:
            continue
        is_cons = str(r.get("consolidated", "")).lower().startswith("consolidated")
        if (basis == "consolidated") != is_cons:
            continue
        rel = str(r.get("relatingTo", "")).lower()
        if not quarterly and not ("fourth" in rel or "annual" in rel or str(r.get("period", "")).lower() == "annual"):
            continue
        seen.add(url)
        local = cache / url.rsplit("/", 1)[-1]
        if not local.exists():
            try:
                nf.fetch(url, str(local), expect="xml", retries=3, timeout=60)
            except nf.FetchError as exc:
                problems.append("%s: %s" % (url, (exc.attempts or [str(exc)])[-1][:120]))
                continue
        try:
            out += rows_from_filing(str(local), url, basis, unit, fy_end_month, quarterly)
        except ET.ParseError as exc:
            problems.append("%s: XML parse error %s" % (url, exc))
    for r in load_integrated_index(run_dir):
        url = r.get("ixbrl") or ""
        if not url.lower().endswith(".html") or url in seen:
            continue
        is_cons = str(r.get("consolidated", "")).lower().startswith("consolidated")
        if (basis == "consolidated") != is_cons:
            continue
        qe = ei_parse(r.get("qe_Date") or "")
        if not quarterly and (not qe or qe.month != fy_end_month):
            continue
        seen.add(url)
        local = cache / url.rsplit("/", 1)[-1]
        if not local.exists():
            try:
                nf.fetch(url, str(local), expect="any", retries=3, timeout=60)
            except nf.FetchError as exc:
                problems.append("%s: %s" % (url, (exc.attempts or [str(exc)])[-1][:120]))
                continue
        out += rows_from_integrated(str(local), url, basis, unit, fy_end_month, quarterly)
    # One value per (item, period): prefer the latest filing (restated comparatives in a later year's filing are
    # kept separately so restatements are visible).
    best: Dict[tuple, dict] = {}
    restated = []
    for row in out:
        key = (row["item"], row["period"], row["basis"])
        if key in best and abs(best[key]["value"] - row["value"]) > 1e-6 * max(1.0, abs(row["value"])):
            restated.append(row)
        best.setdefault(key, row)
    for w in [r for r in out if r["item"] == "other:unit_warning"]:
        problems.append("%s: %s" % (w["source_url_or_id"].rsplit("/", 1)[-1], w["locator"]))
    best = {k: v for k, v in best.items() if k[0] != "other:unit_warning"}
    final = sorted(best.values(), key=lambda r: (r["item"], r["period"]))
    for r in restated:
        b = best[(r["item"], r["period"], r["basis"])]
        problems.append("restatement or comparative difference: %s %s %s vs %s (%s vs %s)" % (
            r["item"], r["period"], b["value"], r["value"], b["source_url_or_id"].rsplit("/", 1)[-1],
            r["source_url_or_id"].rsplit("/", 1)[-1]))
    return final, problems


def likely_cause(item: str, period: str, hv: float, xv: float, comp: Dict[tuple, float]) -> str:
    """Name a common definitional difference when the gap equals a known component (within 1 %)."""
    def close(a, b):
        return b is not None and abs(a - b) <= 0.01 * max(1.0, abs(b))
    assoc = comp.get(("other:share_of_associates_jv", period))
    ppe, intang = comp.get(("other:capex_ppe", period)), comp.get(("other:capex_intangibles", period))
    if item == "pbt" and assoc is not None and close(hv - xv, assoc):
        return "history PBT includes the share of associates/JVs; XBRL PBT is before it"
    if item == "capex" and close(hv, ppe):
        return "history capex is PP&E only; XBRL capex adds intangibles (e.g. spectrum, licences)"
    if item == "capex" and close(hv, intang):
        return "history capex is intangibles only"
    return ""


def reconcile(history: Path, facts: Path, tolerance: float) -> List[dict]:
    def load(p):
        with p.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    comp = {}
    for r in load(facts):
        if r["item"].startswith("other:"):
            try:
                comp[(r["item"], r["period"])] = float(r["value"])
            except ValueError:
                pass
    hist = {}
    for r in load(history):
        try:
            hist[(r["item"], r["period"], (r.get("basis") or "").lower())] = (float(r["value"]), r)
        except (KeyError, ValueError):
            continue
    out = []
    for r in load(facts):
        key = (r["item"], r["period"], (r.get("basis") or "").lower())
        if key not in hist:
            continue
        hv, hrow = hist[key]
        xv = float(r["value"])
        gap = (hv - xv) / abs(xv) if xv else (0.0 if hv == 0 else float("inf"))
        out.append({"item": key[0], "period": key[1], "basis": key[2], "history_value": hv, "xbrl_value": xv,
                    "gap_pct": round(gap * 100, 3), "within_tolerance": abs(gap) <= tolerance,
                    "likely_cause": likely_cause(key[0], key[1], hv, xv, comp) if abs(gap) > tolerance else "",
                    "history_source": hrow.get("source_url_or_id", ""), "xbrl_source": r["source_url_or_id"],
                    "xbrl_locator": r["locator"]})
    return sorted(out, key=lambda r: (r["within_tolerance"], r["item"], r["period"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--run", required=True)
    e.add_argument("--basis", choices=["consolidated", "standalone"], default="consolidated")
    e.add_argument("--unit", default="INR crore")
    e.add_argument("--quarterly", action="store_true", help="also write 3-month values (QnFYyyyy)")
    e.add_argument("--out")
    r = sub.add_parser("reconcile")
    r.add_argument("--run", required=True)
    r.add_argument("--history", required=True)
    r.add_argument("--facts")
    r.add_argument("--tolerance", type=float, default=0.01)
    r.add_argument("--out")
    a = ap.parse_args(argv)
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    try:
        fy_end_month = int(str(m.get("fiscal_year_end") or "03-31").split("-")[0])
    except ValueError:
        fy_end_month = 3
    if a.cmd == "extract":
        rows, problems = extract(run_dir, a.basis, a.unit, a.quarterly, fy_end_month)
        out = Path(a.out) if a.out else run_dir / "calc" / "xbrl_facts.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        cols = ["item", "period", "value", "unit", "basis", "source_tier", "source_url_or_id", "locator", "verified", "note"]
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        periods = sorted({x["period"] for x in rows})
        print("extracted %d facts for %d periods (%s) -> %s" % (len(rows), len(periods), ", ".join(periods), out))
        for p in problems:
            print("  note: %s" % p)
        return 0 if rows else 1
    hist = Path(a.history)
    hist = hist if hist.is_absolute() or hist.exists() else run_dir / hist
    facts = Path(a.facts) if a.facts else run_dir / "calc" / "xbrl_facts.csv"
    rows = reconcile(hist, facts, a.tolerance)
    if a.out:
        with Path(a.out).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["item"])
            w.writeheader()
            w.writerows(rows)
    bad = [x for x in rows if not x["within_tolerance"]]
    print("compared %d values; %d outside ±%.1f %%" % (len(rows), len(bad), a.tolerance * 100))
    for x in bad[:40]:
        print("  %s %s %s: history %s vs XBRL %s (%+.2f %%)%s" % (x["item"], x["period"], x["basis"], x["history_value"],
                                                              x["xbrl_value"], x["gap_pct"],
                                                              " — likely: " + x["likely_cause"] if x["likely_cause"] else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
