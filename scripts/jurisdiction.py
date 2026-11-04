#!/usr/bin/env python3
"""Jurisdictions: where a run's sources, units and words come from (config/jurisdictions/<CODE>.json).

  python3 scripts/jurisdiction.py show [IN|US]
  python3 scripts/jurisdiction.py of RUN_DIR

The methodology is written in India's words (promoter, SEBI, Ind AS, crore). A run in another jurisdiction keeps the
same method and the same contracts; its brief says what each word means there and which sources stand in for the
Indian ones. A run's jurisdiction follows from its exchange and is frozen in its manifest; a run without the field is
Indian, as every run before v4.0 was.
"""

import json
import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

DIR = rl.ROOT / "config" / "jurisdictions"
DEFAULT = "IN"


def load(code: str = DEFAULT) -> dict:
    path = DIR / ("%s.json" % code.upper())
    if not path.exists():
        raise ValueError("no jurisdiction %r (config/jurisdictions/: %s)" % (code, ", ".join(sorted(p.stem for p in DIR.glob("*.json")))))
    return json.loads(path.read_text(encoding="utf-8"))


def all_codes() -> list:
    return sorted(p.stem for p in DIR.glob("*.json"))


def for_exchange(exchange: str) -> str:
    ex = (exchange or "").strip().upper()
    for code in all_codes():
        if ex in load(code)["exchanges"]:
            return code
    raise ValueError("exchange %r belongs to no jurisdiction in config/jurisdictions/" % exchange)


def of_manifest(m: Dict) -> str:
    return (m.get("jurisdiction") or DEFAULT).upper()


def of_run(run_dir: Path) -> dict:
    return load(of_manifest(rl.load_json(run_dir / rl.RUN_MANIFEST)))


def brief_text(code: str) -> str:
    """What the specialist brief says about the jurisdiction. Empty for India: the methodology already speaks its words."""
    if code.upper() == DEFAULT:
        return ""
    j = load(code)
    v, f, s = j["vocabulary"], j["filings"], j["sources"]
    return ("JURISDICTION: %s. The methodology is written in India's words; here they mean: promoter = %s; promoter group = "
            "%s; SEBI = %s; NFRA = %s; Ind AS = %s; related-party approval = %s. The filings: annual report = %s; results = "
            "%s; announcements = %s; governance = %s; shareholding and insider disclosures = %s. Amounts in %s. Sources: "
            "filings index %s; reported facts %s; prices %s. Risk-free rate: %s (%s). Benchmark: %s (%s). Where the "
            "methodology names an Indian source with no equivalent here, say so in your report and use the closest primary "
            "source, never a weaker one in its place without saying so." % (
                j["name"], v["controlling_holder"], v["promoter_group"], j["regulators"]["securities"], j["regulators"]["audit"],
                j["accounting"], v["related_party_approval"], f["annual_report"], f["results"], f["events"], f["governance"],
                f["ownership"], j["unit"], s["index"], s["facts"], s["prices"], j["risk_free"]["series"], j["risk_free"]["source"],
                j["benchmark"]["name"], j["benchmark"]["kind"]))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("show", "of"):
        print(__doc__)
        return 2
    if argv[0] == "show":
        print(json.dumps(load(argv[1] if len(argv) > 1 else DEFAULT), indent=1, ensure_ascii=False))
    else:
        print(json.dumps(of_run(Path(argv[1])), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
