#!/usr/bin/env python3
"""Run-level QC: completion barrier (Stage 2) and final automated checks (Stage 4).

  python3 scripts/validate_run.py RUN_DIR --stage specialists
  python3 scripts/validate_run.py RUN_DIR --stage final

--stage specialists : all nine initial reports + ledgers exist and validate;
                      updates run_manifest.json specialist statuses.
--stage final       : everything above + follow-ups, CIO ledger, merged ledger
                      freshness, scorecard, final report, contradiction log,
                      QC record. Writes RUN_DIR/qc/auto_checks.json.

Exit code 0 only if there are no errors.
"""

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def check_specialists(run_dir: Path, manifest: dict, results: list) -> set:
    all_ids = set()
    expected = {"ticker": manifest.get("ticker"), "run_id": manifest.get("run_id")}
    for name, prefix in rl.SPECIALISTS.items():
        report = run_dir / "specialists" / ("%s.md" % name)
        ledger = run_dir / "specialists" / ("%s_ledger.csv" % name)
        lres, ids = rl.validate_ledger(ledger, prefix)
        all_ids |= ids
        rres = rl.validate_specialist_report(report, ids, expected)
        results.extend([lres, rres])
        entry = manifest.setdefault("specialists", {}).setdefault(name, {})
        if not report.exists() or not ledger.exists():
            entry["status"] = "missing"
        elif rres.ok and lres.ok:
            entry["status"] = "complete"
        else:
            entry["status"] = "failed_validation"
    for led in sorted((run_dir / "specialists").glob("*_followup_*_ledger.csv")):
        lres, ids = rl.validate_ledger(led, rl.prefix_for_ledger(led))
        results.append(lres)
        all_ids |= ids
    return all_ids


def check_followups(run_dir: Path, ids: set, results: list) -> None:
    for fu in sorted((run_dir / "specialists").glob("*_followup_*.md")):
        results.append(rl.validate_specialist_report(fu, ids, None, followup=True))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir")
    p.add_argument("--stage", choices=["specialists", "final"], required=True)
    a = p.parse_args(argv)
    run_dir = Path(a.run_dir)
    mpath = run_dir / rl.RUN_MANIFEST
    if not mpath.exists():
        print("ERROR: no %s in %s" % (rl.RUN_MANIFEST, run_dir))
        return 1
    manifest = rl.load_json(mpath)
    results = []
    ids = check_specialists(run_dir, manifest, results)

    if a.stage == "specialists":
        check_followups(run_dir, ids | rl.validate_ledger(run_dir / "cio" / "cio_ledger.csv")[1], results)
    else:
        cio_ledger = run_dir / "cio" / "cio_ledger.csv"
        cres, cids = rl.validate_ledger(cio_ledger, rl.CIO_PREFIX)
        results.append(cres)
        ids |= cids
        check_followups(run_dir, ids, results)
        merged = run_dir / "evidence_ledger.csv"
        mres = rl.Result(str(merged))
        if not merged.exists():
            mres.error("Merged ledger missing: run scripts/merge_ledgers.py")
        else:
            _, mrows = rl.read_csv(merged)
            if {r["claim_id"] for r in mrows} != ids:
                mres.error("Merged ledger is stale (claim IDs differ from source ledgers): re-run merge_ledgers.py")
        results.append(mres)
        sc_path = run_dir / "cio" / "scorecard.json"
        sc = None
        if sc_path.exists():
            sres = rl.validate_scorecard(sc_path)
            results.append(sres)
            try:
                sc = rl.load_json(sc_path)
            except Exception:
                sc = None
            if sc and sc.get("run_id") != manifest.get("run_id"):
                sres.error("scorecard run_id does not match manifest")
        else:
            missing = rl.Result(str(sc_path))
            missing.error("scorecard.json missing")
            results.append(missing)
        results.append(rl.validate_final_report(run_dir / "cio" / "final_report.md", sc, ids))
        for rel in ("cio/contradiction_log.md", rl.QC_RECORD):
            fp = run_dir / rel
            r = rl.Result(str(fp))
            if not fp.exists():
                r.error("missing")
            elif rel.endswith("contradiction_log.md") and "<question>" in fp.read_text(encoding="utf-8"):
                r.warn("contradiction log still contains the template placeholder block")
            results.append(r)

    errors = sum(len(r.errors) for r in results)
    warnings = sum(len(r.warnings) for r in results)
    for r in results:
        if r.errors or r.warnings:
            print(r.render())
    passed = errors == 0
    print("\n%s stage: %s  (%d errors, %d warnings, %d targets)"
          % (a.stage, "PASS" if passed else "FAIL", errors, warnings, len(results)))

    manifest["status"] = {
        ("specialists", True): "specialists_complete",
        ("specialists", False): "specialists_incomplete",
        ("final", True): "qc_auto_passed",
        ("final", False): "qc_auto_failed",
    }[(a.stage, passed)]
    rl.write_json(mpath, manifest)
    if a.stage == "final":
        (run_dir / "qc").mkdir(exist_ok=True)
        rl.write_json(run_dir / "qc" / "auto_checks.json", {
            "run_id": manifest.get("run_id"),
            "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
            "methodology_version": rl.methodology_version(),
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
            "results": [r.to_dict() for r in results],
        })
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
