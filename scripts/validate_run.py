#!/usr/bin/env python3
"""Run-level QC: completion barrier (Stage 2) and final automated checks (Stage 4).

  python3 scripts/validate_run.py RUN_DIR --stage specialists
  python3 scripts/validate_run.py RUN_DIR --stage final

--stage specialists : every initial specialist report + ledger the run's methodology version requires exists and
                      validates (ten specialists from 2.4.0: scuttlebutt joined; nine before);
                      updates run_manifest.json specialist statuses.
--stage final       : everything above + follow-ups, CIO ledger, merged ledger
                      freshness, scorecard, final report, contradiction log,
                      QC record; from 2.4.0 also the document map, the
                      independent audit and the CIO's audit resolutions.
                      Writes RUN_DIR/qc/auto_checks.json.

A run is validated against the contract of the methodology version recorded in its manifest (checks added in
2.3.0 are skipped for older runs). A finalized run (status complete or insufficient_evidence) is
validated read-only: neither its manifest nor its QC files are rewritten.

Exit code 0 only if there are no errors.
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402
import evidence_stats  # noqa: E402
import reconcile_numbers  # noqa: E402


FINALIZED = ("complete", "insufficient_evidence")  # qc_failed stays writable: it is fixed and re-validated


def check_specialists(run_dir: Path, manifest: dict, results: list, legacy: bool = False,
                      version: tuple = None, segment: str = "") -> set:
    all_ids = set()
    expected = {"ticker": manifest.get("ticker"), "run_id": manifest.get("run_id")}
    v = rl.effective_version(legacy, version)
    for name, prefix in rl.specialists_for(v).items():
        report = run_dir / "specialists" / ("%s.md" % name)
        ledger = run_dir / "specialists" / ("%s_ledger.csv" % name)
        lres, ids = rl.validate_ledger(ledger, prefix)
        all_ids |= ids
        rres = rl.validate_specialist_report(report, ids, expected, version=v, segment=segment)
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


def check_followups(run_dir: Path, ids: set, results: list, version: tuple = None) -> None:
    for fu in sorted((run_dir / "specialists").glob("*_followup_*.md")):
        results.append(rl.validate_specialist_report(fu, ids, None, followup=True, version=version))


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
    version = rl.version_tuple(manifest.get("methodology_version"))
    legacy = rl.is_legacy(manifest.get("methodology_version"))
    segment = str(manifest.get("listing_segment") or manifest.get("segment") or "")
    read_only = manifest.get("status") in FINALIZED
    if version < rl.current_version():
        print("note: run recorded under methodology %s; validating against that contract (later additions skipped)"
              % manifest.get("methodology_version"))
    if read_only:
        print("note: run is finalized (status %s); validating read-only, nothing in the run is written" % manifest.get("status"))
    ids = check_specialists(run_dir, manifest, results, version=version, segment=segment)

    if a.stage == "specialists":
        check_followups(run_dir, ids | rl.validate_ledger(run_dir / "cio" / "cio_ledger.csv")[1], results, version)
    else:
        cio_ledger = run_dir / "cio" / "cio_ledger.csv"
        cres, cids = rl.validate_ledger(cio_ledger, rl.CIO_PREFIX)
        results.append(cres)
        ids |= cids
        if version >= rl.V24:
            for led in sorted((run_dir / "audit").glob("*_ledger.csv")):
                ares, aids = rl.validate_ledger(led, rl.AUDITOR_PREFIX)
                results.append(ares)
                ids |= aids
        check_followups(run_dir, ids, results, version)
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
        results.append(rl.validate_final_report(run_dir / "cio" / "final_report.md", sc, ids, version=version,
                                                segment=segment))
        if version >= rl.V24:
            ares, findings = rl.validate_audit_report(run_dir / rl.AUDIT_REPORT, ids,
                                                      {"ticker": manifest.get("ticker"), "run_id": manifest.get("run_id")})
            rl.check_audit_resolutions(run_dir, findings, ares)
            results.append(ares)
        # Evidence statistics (warnings) and cross-ledger numeric conflicts (must be adjudicated).
        stats = evidence_stats.compute(run_dir)
        if not read_only:
            (run_dir / "qc").mkdir(exist_ok=True)
            rl.write_json(run_dir / "qc" / "evidence_stats.json", stats)
        sres = rl.Result(str(run_dir / "qc" / "evidence_stats.json"))
        for w in stats["warnings"]:
            sres.warn(w)
        results.append(sres)
        found = reconcile_numbers.conflicts(run_dir)
        cres2 = rl.Result(str(run_dir / "qc" / "numeric_conflicts.csv"))
        log_path = run_dir / "cio" / "contradiction_log.md"
        log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        for c in found:
            ids_in_conflict = [x.strip() for x in c["claim_ids"].split(";")]
            if not any(cid in log_text for cid in ids_in_conflict):
                cres2.error("unadjudicated numeric conflict: %s %s %s..%s (%s) — cite these claim IDs in cio/contradiction_log.md"
                            % (c["metric"], c["period"], c["min"], c["max"], c["claim_ids"]))
        results.append(cres2)
        files = ["cio/contradiction_log.md"] + ([] if legacy else list(rl.V23_CIO_FILES)) + \
            (list(rl.V24_CIO_FILES) if version >= rl.V24 else []) + [rl.QC_RECORD]
        for rel in files:
            fp = run_dir / rel
            r = rl.Result(str(fp))
            if not fp.exists():
                r.error("missing")
            elif rel.endswith("contradiction_log.md") and "<question>" in fp.read_text(encoding="utf-8"):
                r.warn("contradiction log still contains the template placeholder block")
            elif rel.endswith("gap_register.md") and not re.search(r"^\|\s*\d+\s*\|", fp.read_text(encoding="utf-8"), re.M):
                r.warn("gap register has no rows: list every checklist gap and how it was closed, or state that none existed")
            elif rel.endswith("cio_analysis.md") and len(fp.read_text(encoding="utf-8").split()) < 400:
                r.warn("CIO independent analysis looks like the unfilled template (< 400 words)")
            results.append(r)

    errors = sum(len(r.errors) for r in results)
    warnings = sum(len(r.warnings) for r in results)
    for r in results:
        if r.errors or r.warnings:
            print(r.render())
    passed = errors == 0
    print("\n%s stage: %s  (%d errors, %d warnings, %d targets)"
          % (a.stage, "PASS" if passed else "FAIL", errors, warnings, len(results)))

    if read_only:
        return 0 if passed else 1
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
