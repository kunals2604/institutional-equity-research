#!/usr/bin/env python3
"""Download a source document with provenance (SHA-256, time, status) for a research run.

  python3 scripts/fetch_source.py URL --run RUN_DIR --author financials --name "Annual Report FY2024"

Saves the file under RUN_DIR/_cache/<author>/ (git-ignored: licensing and size)
and appends one row to RUN_DIR/source_retrievals.csv (committed), including for
FAILED attempts, so missing evidence is documented honestly.

Prints the local path. For PDFs it also prints an approximate page count; read
PDFs with the Read tool using page ranges (TOC first). Re-fetching a URL whose
cached copy has the same SHA-256 reuses the cached file.

Robust retrieval (a run on Bharti Airtel lost 41 of 52 failed downloads to transient TLS errors):
  * transient failures (TLS/SSL errors, connection resets, timeouts, HTTP 429/5xx) are retried with backoff;
  * if Python's TLS stack still fails, or the server answers 403, the download is retried with the system
    `curl` (a different TLS implementation and request fingerprint);
  * a URL already downloaded successfully in this run by ANY agent is reused from that agent's cache
    (source documents only; independence rules forbid reading other agents' analysis), unless --no-reuse.
Every attempt that ends in failure is still logged, so missing evidence stays documented.

Exit: 0 downloaded/reused, 1 failed (row still logged), 2 usage error.
"""

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research_lib as rl  # noqa: E402

COLUMNS = ["retrieved_at_utc", "author", "name", "url", "final_url", "http_status", "content_type",
           "bytes", "sha256", "local_path", "error"]
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124.0 Safari/537.36 equity-research-provenance/1.0")
EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json", "text/csv": ".csv",
               "application/zip": ".zip", "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"}


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:60] or "document"


def log_row(run_dir: Path, row: dict) -> None:
    log = run_dir / "source_retrievals.csv"
    lock = run_dir / "_cache" / ".retrievals.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        new = not log.exists() or log.stat().st_size == 0
        with log.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
            if new:
                w.writeheader()
            w.writerow({c: row.get(c, "") for c in COLUMNS})
        fcntl.flock(lf, fcntl.LOCK_UN)


TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}


def prior_success(run_dir: Path, url: str):
    """Return (author, local Path) of an earlier successful download of the same URL in this run, if the file exists."""
    log = run_dir / "source_retrievals.csv"
    if not log.exists():
        return None
    with log.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("url") == url and str(r.get("http_status")) == "200" and not r.get("error") and r.get("local_path"):
                path = run_dir / r["local_path"]
                if path.exists() and path.stat().st_size > 0:
                    return r.get("author", ""), path
    return None


def _urllib_once(url, ua, timeout, tmp, limit):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9"})
    sha, size = hashlib.sha256(), 0
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp, open(tmp, "wb") as out:
        status, final_url = resp.status, resp.geturl()
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise ValueError("exceeds --max-mb limit")
            sha.update(chunk)
            out.write(chunk)
    return status, final_url, ctype, size, sha.hexdigest()


def _curl_once(url, ua, timeout, tmp, limit):
    curl = shutil.which("curl")
    if not curl:
        raise OSError("curl not available")
    parsed = urllib.parse.urlparse(url)
    referer = "%s://%s/" % (parsed.scheme, parsed.netloc)
    cmd = [curl, "-sS", "-L", "--compressed", "-m", str(int(timeout)), "--max-filesize", str(limit), "-A", ua,
           "-H", "Accept: */*", "-H", "Accept-Language: en-IN,en;q=0.9", "-e", referer, "-o", tmp,
           "-w", "%{http_code}\t%{content_type}\t%{url_effective}", url]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    if proc.returncode != 0:
        raise OSError("curl exit %d: %s" % (proc.returncode, proc.stderr.strip()[:160]))
    code, ctype, final_url = (proc.stdout.split("\t") + ["", "", ""])[:3]
    status = int(code or 0)
    if status >= 400 or status == 0:
        err = urllib.error.HTTPError(url, status, "HTTP %s via curl" % status, None, None)
        raise err
    sha, size = hashlib.sha256(), 0
    with open(tmp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            sha.update(chunk)
            size += len(chunk)
    return status, final_url or url, (ctype or "").split(";")[0].strip().lower(), size, sha.hexdigest()


def _transient(exc) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in TRANSIENT_HTTP
    return isinstance(exc, (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError, OSError)) \
        and not isinstance(exc, ValueError)


def robust_download(url, ua, timeout, tmp, limit, retries=3):
    """urllib with backoff on transient errors, then curl. Returns (result tuple, method note) or raises the last error."""
    errors = []
    for i in range(retries):
        try:
            return _urllib_once(url, ua, timeout, tmp, limit), ("urllib" if i == 0 else "urllib, attempt %d" % (i + 1))
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 - classified below
            errors.append("%s: %s" % (type(exc).__name__, str(exc)[:120]))
            if isinstance(exc, urllib.error.HTTPError) and exc.code == 403:
                break                      # try curl's request fingerprint
            if not _transient(exc):
                if isinstance(exc, urllib.error.HTTPError):
                    raise
                break
            time.sleep(min(2 ** i * 2, 10))
    try:
        res = _curl_once(url, ua, timeout, tmp, limit)
        return res, "curl fallback after %d urllib error(s): %s" % (len(errors), errors[-1][:80] if errors else "")
    except Exception as exc:  # noqa: BLE001
        errors.append("curl %s: %s" % (type(exc).__name__, str(exc)[:120]))
        last = urllib.error.URLError("; ".join(errors))
        last.code = getattr(exc, "code", "")
        raise last


def pdf_pages(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("--run", required=True, help="run directory")
    p.add_argument("--author", required=True, help="agent name (e.g. financials, cio)")
    p.add_argument("--name", default="", help="human label, e.g. 'Annual Report FY2024'")
    p.add_argument("--max-mb", type=float, default=150.0)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--no-reuse", action="store_true", help="download again even if another agent already fetched this URL")
    p.add_argument("--retries", type=int, default=3, help="urllib attempts before the curl fallback")
    p.add_argument("--user-agent", default=os.environ.get("EQUITY_RESEARCH_USER_AGENT", USER_AGENT),
                   help="override the User-Agent (e.g. SEC EDGAR requires 'Name contact@email'); "
                        "default from $EQUITY_RESEARCH_USER_AGENT or a browser-like string")
    a = p.parse_args(argv)

    if a.author not in rl.SPECIALISTS and a.author != "cio":
        p.error("--author must be a specialist name or cio")
    parsed = urllib.parse.urlparse(a.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        p.error("only absolute http(s) URLs are allowed")
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        p.error("%s is not a run directory (no %s)" % (run_dir, rl.RUN_MANIFEST))
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    row = {"retrieved_at_utc": now.isoformat(), "author": a.author, "name": a.name, "url": a.url}
    cache = run_dir / "_cache" / a.author
    cache.mkdir(parents=True, exist_ok=True)
    limit = int(a.max_mb * 1024 * 1024)

    if not a.no_reuse:
        prior = prior_success(run_dir, a.url)
        if prior:
            src_author, path = prior
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            row.update({"name": (a.name + " [reused: downloaded earlier in this run by %s]" % src_author).strip(),
                        "final_url": a.url, "http_status": 200, "bytes": path.stat().st_size, "sha256": sha,
                        "local_path": str(path.relative_to(run_dir))})
            log_row(run_dir, row)
            print(path)
            if path.suffix == ".pdf":
                print("PDF, approx. %d pages. Read with the Read tool, e.g. pages \"1-6\" for the table of contents." % pdf_pages(path))
            print("reused (sha256 %s); source document only - do not read the other agent's analysis" % sha)
            return 0

    fd, tmp = tempfile.mkstemp(dir=str(cache), prefix=".part-")
    os.close(fd)
    try:
        (status, final_url, ctype, size, digest), method = robust_download(a.url, a.user_agent, a.timeout, tmp, limit, a.retries)
        row.update({"http_status": status, "final_url": final_url, "content_type": ctype})
        if method != "urllib":
            row["name"] = (a.name + " [%s]" % method).strip()
    except (urllib.error.URLError, ValueError, OSError) as exc:
        if os.path.exists(tmp):
            os.unlink(tmp)
        row["http_status"] = getattr(exc, "code", "") or row.get("http_status", "")
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
        log_row(run_dir, row)
        print("FAILED after retries and curl fallback: %s (logged in source_retrievals.csv; try an alternative source "
              "per methodology/SOURCE_GUIDE.md, then record it as missing evidence)" % row["error"], file=sys.stderr)
        return 1

    ext = EXT_BY_TYPE.get(row.get("content_type", ""), "") or (Path(parsed.path).suffix.lower()[:6] or ".bin")
    if row.get("content_type") == "application/octet-stream" and parsed.path.lower().endswith(".pdf"):
        ext = ".pdf"
    final = cache / ("%s-%s-%s%s" % (now.strftime("%Y%m%d"), digest[:12], slug(a.name or Path(parsed.path).stem), ext))
    existing = list(cache.glob("*-%s-*" % digest[:12]))
    if existing:
        os.unlink(tmp)
        final = existing[0]
    else:
        os.replace(tmp, final)
    row.update({"bytes": size, "sha256": digest, "local_path": str(final.relative_to(run_dir))})
    log_row(run_dir, row)
    print(final)
    if ext == ".pdf":
        n = pdf_pages(final)
        print("PDF, approx. %d pages. Read with the Read tool, e.g. pages \"1-6\" for the table of contents." % n)
    print("sha256 %s, %d bytes, HTTP %s" % (digest, size, row["http_status"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
