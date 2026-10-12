#!/usr/bin/env python3
"""Download a source document with provenance (SHA-256, time, status) for a research run.

  python3 scripts/fetch_source.py URL --run RUN_DIR --author financials --name "Annual Report FY2024"

Saves the file under RUN_DIR/_cache/<author>/ (git-ignored: licensing and size)
and appends one row to RUN_DIR/source_retrievals.csv (committed), including for
FAILED attempts, so missing evidence is documented honestly.

Prints the local path. For PDFs it also prints an approximate page count; read
PDFs with the Read tool using page ranges (TOC first). Re-fetching a URL whose
cached copy has the same SHA-256 reuses the cached file.

Exit: 0 downloaded/reused, 1 failed (row still logged), 2 usage error.
"""

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import os
import re
import ssl
import sys
import tempfile
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

    req = urllib.request.Request(a.url, headers={"User-Agent": a.user_agent, "Accept": "*/*",
                                                 "Accept-Language": "en-IN,en;q=0.9"})
    fd, tmp = tempfile.mkstemp(dir=str(cache), prefix=".part-")
    out = os.fdopen(fd, "wb")
    sha = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=a.timeout, context=ssl.create_default_context()) as resp:
            row["http_status"] = resp.status
            row["final_url"] = resp.geturl()
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            row["content_type"] = ctype
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise ValueError("exceeds --max-mb %.0f" % a.max_mb)
                sha.update(chunk)
                out.write(chunk)
        out.close()
    except (urllib.error.URLError, ValueError, OSError) as exc:
        out.close()
        if os.path.exists(tmp):
            os.unlink(tmp)
        row["http_status"] = getattr(exc, "code", "") or row.get("http_status", "")
        row["error"] = "%s: %s" % (type(exc).__name__, exc)
        log_row(run_dir, row)
        print("FAILED: %s (logged in source_retrievals.csv; record it as missing evidence if no alternative)" % row["error"],
              file=sys.stderr)
        return 1

    digest = sha.hexdigest()
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
