#!/usr/bin/env python3
"""Serialized, scoped git commits (and optional push) for a research run (CIO only).

  python3 scripts/git_publish.py RUN_DIR --batch specialists [--push]
  python3 scripts/git_publish.py RUN_DIR --batch final [--push]

Policy (PROJECT_INSTRUCTIONS.md §6, docs/OPERATIONS.md):
  * Stages and commits ONLY the run directory (+ scoreboard, latest_run.txt and the
    outcome loop's ledgers in research/outcomes/ for the final batch). Other staged or
    unstaged user changes are untouched.
  * Commit messages state the true status (missing specialists, QC outcome).
  * Pushes the current branch to its remote with a plain `git push`. Never
    forces, never merges, never pulls. Refuses on detached HEAD.
  * If the push fails, the local commit is kept and the error is reported (exit 4).

Exit: 0 ok, 1 error, 2 nothing to commit, 4 committed locally but push failed.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402


def git(root: Path, *args, check=True):
    r = subprocess.run(["git", "-C", str(root)] + list(args), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir")
    p.add_argument("--batch", choices=["specialists", "final"], required=True)
    p.add_argument("--push", action="store_true")
    p.add_argument("--remote", default="origin")
    a = p.parse_args(argv)
    run_dir = Path(a.run_dir).resolve()
    try:
        root = Path(git(run_dir, "rev-parse", "--show-toplevel").stdout.strip())
        branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    except RuntimeError as exc:
        print("ERROR: %s (detached HEAD or not a repository)" % exc, file=sys.stderr)
        return 1
    m = rl.load_json(run_dir / rl.RUN_MANIFEST)
    ticker, run_id = m["ticker"], m["run_id"]

    paths = [str(run_dir.relative_to(root.resolve()))]
    if a.batch == "specialists":
        expected = list(rl.specialists_for(rl.version_tuple(m.get("methodology_version"))))
        done = [n for n, s in m["specialists"].items() if s.get("status") == "complete" and n in expected]
        missing = [n for n in expected if n not in done]
        msg = "research(%s): %s specialists batch — %d/%d complete" % (ticker, run_id, len(done), len(expected))
        if missing:
            msg += "; NOT complete: %s" % ", ".join(missing)
    else:
        outcomes = root / "research" / "outcomes"           # finalize_run.py records the decision and its predictions
        for extra in [root / rl.SCOREBOARD.name, run_dir.parent.parent / rl.LATEST_POINTER] + [
                outcomes / n for n in ("decisions.csv", "predictions.csv", "resolutions.csv", "WATCH.md")]:
            if extra.exists():
                paths.append(str(extra.resolve().relative_to(root.resolve())))
        sc_path = run_dir / "cio" / "scorecard.json"
        sc = rl.load_json(sc_path) if sc_path.exists() else {}
        status = m.get("status")
        if status == "complete":
            msg = "research(%s): %s final — %s, BQ %s, IA %s, QC PASS" % (
                ticker, run_id, sc.get("verdict"), sc["business_quality"]["final"], sc["investment_attractiveness"]["final"])
        else:
            msg = "research(%s): %s final — outcome %s (scoreboard unchanged)" % (ticker, run_id, status)

    git(root, "add", "--", *paths)
    staged = git(root, "diff", "--cached", "--name-only", "--", *paths).stdout.split()
    if not staged:
        print("Nothing to commit for %s batch." % a.batch)
        return 2
    git(root, "commit", "--quiet", "-m", msg, "--", *paths)
    sha = git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    print("Committed %s on %s: %s (%d files)" % (sha, branch, msg, len(staged)))

    rc = 0
    if a.push:
        url = git(root, "remote", "get-url", a.remote, check=False).stdout.strip()
        if not url:
            print("PUSH SKIPPED: remote %r not configured; commit kept locally." % a.remote, file=sys.stderr)
            rc = 4
        else:
            print("Pushing %s -> %s (%s)" % (branch, a.remote, url))
            r = git(root, "push", a.remote, branch, check=False)
            if r.returncode != 0:
                print("PUSH FAILED (commit kept locally, no force/merge attempted):\n%s" % r.stderr.strip(), file=sys.stderr)
                rc = 4
            else:
                print("Pushed.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
