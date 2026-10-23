#!/usr/bin/env python3
"""Headless Chrome for the research system: a rendered, citable copy of a public web page (library and CLI).

  python3 scripts/browser.py check                    # is Chrome available (and which binary)
  python3 scripts/browser.py snapshot URL OUT.pdf     # the page as Chrome prints it: a PDF with the URL and date on
                                                      # every page, citable by page, re-opened as is by the verifier
  python3 scripts/browser.py dom URL OUT.html         # the DOM after JavaScript ran (tables: scripts/html_tables.py)

Why. WebFetch returns a model's rendering of a page, not the page (EVIDENCE_STANDARDS.md); netfetch.py gets the raw
HTML, which on JavaScript-built pages (many IR sites, regulators' listings) holds no content. Chrome renders the page
as a reader's browser does, and the snapshot is the evidence an agent saw. In a run, call it through
`scripts/fetch_source.py URL --snapshot` (cached, logged in source_retrievals.csv, reused across agents).

Policy (owner, 2026-10-23: a real browser plus mirrors): public pages only. A fresh profile per call (no cookies or
logins carried), no CAPTCHA solving, no paywall bypass, and at least EQR_BROWSER_MIN_INTERVAL seconds (default 3)
between two calls to the same host. Standard library only, plus the Chrome binary (EQR_CHROME overrides the path).
"""

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netfetch as nf  # noqa: E402

CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary")
CHROME_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
PACE_FILE = Path(tempfile.gettempdir()) / "eqr-browser-pace.json"


class BrowserError(Exception):
    pass


def find_chrome() -> Optional[str]:
    env = os.environ.get("EQR_CHROME")
    if env:
        return env if Path(env).exists() else None
    for p in CHROME_PATHS:
        if Path(p).exists():
            return p
    for n in CHROME_NAMES:
        found = shutil.which(n)
        if found:
            return found
    return None


def chrome_version(chrome: str) -> str:
    try:
        return subprocess.run([chrome, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _pace(url: str, sleep=time.sleep) -> None:
    """Wait until EQR_BROWSER_MIN_INTERVAL seconds have passed since the last call to this host (any process)."""
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    gap = float(os.environ.get("EQR_BROWSER_MIN_INTERVAL", "3"))
    PACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(str(PACE_FILE) + ".lock", "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            seen = json.loads(PACE_FILE.read_text()) if PACE_FILE.exists() else {}
        except ValueError:
            seen = {}
        wait = seen.get(host, 0) + gap - time.time()
        if wait > 0:
            sleep(wait)
        seen[host] = time.time()
        PACE_FILE.write_text(json.dumps(seen))
        fcntl.flock(lf, fcntl.LOCK_UN)


def _base_cmd(chrome: str, profile: str, budget_ms: int) -> list:
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", "--disable-sync", "--disable-background-networking", "--mute-audio",
           "--hide-scrollbars", "--user-data-dir=%s" % profile, "--virtual-time-budget=%d" % budget_ms]
    if os.environ.get("EQR_BROWSER_UA"):       # Chrome's own (headless) user agent unless the owner sets one
        cmd.append("--user-agent=%s" % os.environ["EQR_BROWSER_UA"])
    return cmd


def _check_url(url: str) -> None:
    if not url.lower().startswith(("http://", "https://")) or not nf.is_public_host(url):
        raise BrowserError("not a public http(s) URL: %s" % url)


def _run(cmd: list, timeout: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise BrowserError("Chrome did not finish within %ds" % timeout)
    except OSError as exc:
        raise BrowserError("Chrome could not start: %s" % exc)


def snapshot(url: str, out: str, *, timeout: float = 120.0, budget_ms: int = 15000, chrome: Optional[str] = None,
             sleep=time.sleep) -> dict:
    """Print the rendered page to `out` (PDF, with Chrome's header and footer: date, title, URL, page numbers).
    Returns {"pages", "bytes", "sha256", "chrome"}; raises BrowserError when nothing usable was produced."""
    _check_url(url)
    chrome = chrome or find_chrome()
    if not chrome:
        raise BrowserError("Chrome not found (install Google Chrome or set EQR_CHROME)")
    _pace(url, sleep)
    profile = tempfile.mkdtemp(prefix="eqr-chrome-")
    tmp = out + ".part"
    try:
        proc = _run(_base_cmd(chrome, profile, budget_ms) + ["--print-to-pdf=%s" % tmp, url], timeout)
        if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            raise BrowserError("Chrome printed nothing (exit %s): %s" % (
                proc.returncode, proc.stderr.decode("utf-8", "replace").strip()[-200:]))
        kind, problems, info = nf.validate_payload(tmp, "pdf")
        if problems:
            raise BrowserError("; ".join(problems))
        text = _pdf_text(tmp)
        if text is not None and nf.ERROR_PAGE_RE.search(text[:3000]) and len(text.split()) < 400:
            raise BrowserError("the page is an error or bot-check page: %r" % " ".join(text.split())[:120])
        os.replace(tmp, out)
        size, digest = nf._sha256_file(out)
        return {"pages": info.get("pages"), "bytes": size, "sha256": digest, "chrome": chrome}
    finally:
        shutil.rmtree(profile, ignore_errors=True)
        if os.path.exists(tmp):
            os.unlink(tmp)


def dump_dom(url: str, out: str, *, timeout: float = 120.0, budget_ms: int = 15000, chrome: Optional[str] = None,
             sleep=time.sleep) -> dict:
    """Write the DOM after JavaScript ran to `out`. Returns {"bytes", "sha256", "chrome"}."""
    _check_url(url)
    chrome = chrome or find_chrome()
    if not chrome:
        raise BrowserError("Chrome not found (install Google Chrome or set EQR_CHROME)")
    _pace(url, sleep)
    profile = tempfile.mkdtemp(prefix="eqr-chrome-")
    try:
        proc = _run(_base_cmd(chrome, profile, budget_ms) + ["--dump-dom", url], timeout)
        html = proc.stdout or b""
        if len(html) < 200:
            raise BrowserError("Chrome returned no page (exit %s): %s" % (
                proc.returncode, proc.stderr.decode("utf-8", "replace").strip()[-200:]))
        Path(out).write_bytes(html)
        kind, problems, _ = nf.validate_payload(out, "any")
        if problems:
            os.unlink(out)
            raise BrowserError("; ".join(problems))
        size, digest = nf._sha256_file(out)
        return {"bytes": size, "sha256": digest, "chrome": chrome}
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _pdf_text(path: str) -> Optional[str]:
    tool = shutil.which("pdftotext")
    if not tool:
        return None
    try:
        return subprocess.run([tool, "-l", "2", path, "-"], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    for name in ("snapshot", "dom"):
        p = sub.add_parser(name)
        p.add_argument("url")
        p.add_argument("out")
        p.add_argument("--timeout", type=float, default=120.0)
        p.add_argument("--budget-ms", type=int, default=15000, help="how long the page may run its scripts")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        c = find_chrome()
        print("chrome: %s%s" % (c or "not found", (" (%s)" % chrome_version(c)) if c else ""))
        return 0 if c else 1
    try:
        fn = snapshot if a.cmd == "snapshot" else dump_dom
        res = fn(a.url, a.out, timeout=a.timeout, budget_ms=a.budget_ms)
    except BrowserError as exc:
        print("FAILED: %s" % exc)
        return 1
    print("%s -> %s (%s bytes%s; sha256 %s)" % (a.url, a.out, res["bytes"],
                                                ", %s pages" % res["pages"] if res.get("pages") else "", res["sha256"][:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
