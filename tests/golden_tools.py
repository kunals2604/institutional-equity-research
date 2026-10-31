"""The golden baseline: what the one real finished run looks like, frozen at the start of the v4.0 build.

  python3 tests/golden_tools.py freeze     # writes tests/golden/bharti_baseline.json (only when deliberately re-baselining)

BHARTIARTL 20261012T132311Z is the only company that ever finished a run. Its files are the one body of real, messy
agent output the framework has, so every change is checked against them: the run's files must never change, its
validator output must stay identical, and the scripts must keep parsing it. Fixtures cannot show what real text does.
"""

import collections
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "research" / "companies" / "BHARTIARTL" / "runs" / "20261012T132311Z"
BASELINE = ROOT / "tests" / "golden" / "bharti_baseline.json"
BASE_COMMIT = "8f7e65d"


def run_files() -> Dict[str, str]:
    """{path relative to the run: SHA-256} of everything but the local download cache."""
    out = {}
    for p in sorted(RUN.rglob("*")):
        if p.is_file() and "_cache" not in p.relative_to(RUN).parts and p.name != ".DS_Store":
            out[str(p.relative_to(RUN))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def validator_output(stage: str = "final") -> List[str]:
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_run.py"), str(RUN), "--stage", stage],
                       cwd=str(ROOT), capture_output=True, text=True)
    text = (r.stdout + r.stderr).replace(str(ROOT), "<ROOT>")
    return ["exit %d" % r.returncode] + text.splitlines()


def scratch_copy(dest: Path, version: str = "3.2.0") -> Path:
    """The run in a scratch folder, its manifest moved to a newer methodology so the current scripts treat it as theirs.
    The real run is never touched."""
    run = dest / RUN.name
    shutil.copytree(str(RUN), str(run), ignore=shutil.ignore_patterns("_cache"))
    path = run / "run_manifest.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m.update({"methodology_version": version, "reading_mode": "off", "status": "synthesis"})
    path.write_text(json.dumps(m, indent=1), encoding="utf-8")
    return run


def registry_items(run: Path) -> List[dict]:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "synthesis.py"), "registry", str(run)], cwd=str(ROOT),
                   check=True, capture_output=True, text=True)
    lines = (run / "synthesis" / "registry.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in lines if l.strip()]


def registry_summary(items: List[dict]) -> dict:
    count = lambda key: dict(sorted(collections.Counter(str(i.get(key)) for i in items).items()))
    return {"items": len(items), "kind": count("kind"), "materiality": count("materiality"), "author": count("author")}


def freeze() -> dict:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="eqr-golden-") as tmp:
        items = registry_items(scratch_copy(Path(tmp)))
    data = {"base_commit": BASE_COMMIT, "run": RUN.name, "files": run_files(),
            "validator": {"specialists": validator_output("specialists"), "final": validator_output("final")},
            "registry_3_2_0": registry_summary(items)}
    BASELINE.parent.mkdir(exist_ok=True)
    BASELINE.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return data


def baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    if sys.argv[1:] != ["freeze"]:
        raise SystemExit(__doc__)
    d = freeze()
    print("frozen: %d files, %d registry items -> %s" % (len(d["files"]), d["registry_3_2_0"]["items"], BASELINE))
