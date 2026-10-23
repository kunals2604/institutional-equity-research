#!/usr/bin/env python3
"""Download a source document with provenance (SHA-256, time, status) for a research run.

  python3 scripts/fetch_source.py URL --run RUN_DIR --author financials --name "Annual Report FY2024" \
      [--alt MIRROR_URL ...] [--expect pdf|zip|json|html|xml|csv|any] [--no-wayback] [--no-reuse]

Saves the file under RUN_DIR/_cache/<author>/ (git-ignored: licensing and size) and appends one row to
RUN_DIR/source_retrievals.csv (committed), including for FAILED attempts, so missing evidence is documented
honestly. Prints the local path; for PDFs also the page count. Read PDFs with the Read tool using page ranges
(table of contents first).

Retrieval order (scripts/netfetch.py does the transport):
  1. **reuse**: a URL already downloaded successfully in this run by ANY agent (or by the CIO's Stage-0
     acquisition, see scripts/document_map.py) is reused from the cache, unless --no-reuse. Source documents
     only; independence rules forbid reading another agent's analysis;
  2. the URL itself, via the system curl with a host-specific request profile (NSE, BSE, SEC, default), with
     retries on transient failures, then urllib;
  3. each --alt mirror in order (for example the BSE copy of an NSE filing, or the company-IR copy);
  4. the Internet Archive's raw capture of the URL (and of each mirror), unless --no-wayback.
Every payload is validated: an HTML error or bot-check page, a truncated PDF or a corrupt ZIP is a failure, not a
document. ZIP archives (exchanges publish older annual reports as ZIPs) are unpacked next to the archive, and each
member's SHA-256 is printed and recorded in a `.members.json` sidecar.

Rendered pages (scripts/browser.py, headless Chrome): `--snapshot` saves the page as Chrome prints it (a PDF with the
URL and date on every page) and `--dom` the page after its JavaScript ran (for scripts/html_tables.py). Use a snapshot
for any web page you cite: it is the copy you saw, citable by page, and the verifier re-opens the same file. WebFetch
only paraphrases a page through a model.

Exit: 0 downloaded/reused, 1 failed (row still logged), 2 usage error.
"""

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import browser  # noqa: E402
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

COLUMNS = ["retrieved_at_utc", "author", "name", "url", "final_url", "http_status", "content_type",
           "bytes", "sha256", "local_path", "error", "method", "validation"]
USER_AGENT = nf.CHROME_UA
EXT_BY_KIND = {"pdf": ".pdf", "zip": ".zip", "html": ".html", "json": ".json", "xml": ".xml", "csv": ".csv",
               "text": ".txt"}
EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json", "text/csv": ".csv",
               "application/zip": ".zip", "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx"}
TRANSIENT_HTTP = nf.TRANSIENT_HTTP


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:60] or "document"


def log_row(run_dir: Path, row: dict) -> None:
    """Append one retrieval row under a lock. An existing log keeps its own header (older runs have fewer columns)."""
    log = run_dir / "source_retrievals.csv"
    lock = run_dir / "_cache" / ".retrievals.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        new = not log.exists() or log.stat().st_size == 0
        columns = COLUMNS
        if not new:
            with log.open(newline="", encoding="utf-8") as f:
                header = next(csv.reader(f), None)
            if header:
                columns = header
                if "method" not in header and row.get("method"):
                    row = dict(row, name=("%s [%s]" % (row.get("name", ""), row["method"])).strip())
        with log.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL, extrasaction="ignore")
            if new:
                w.writeheader()
            w.writerow({c: row.get(c, "") for c in columns})
        fcntl.flock(lf, fcntl.LOCK_UN)


RENDER_METHODS = ("chrome-snapshot", "chrome-dom")


def prior_success(run_dir: Path, url: str, method: str = ""):
    """Return (author, local Path) of an earlier successful download of the same URL in this run, if the file exists.
    `method` asks for a rendered copy (chrome-snapshot | chrome-dom); without it, rendered copies are not reused for
    a download of the document itself."""
    log = run_dir / "source_retrievals.csv"
    if not log.exists():
        return None
    with log.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m = r.get("method") or ""
            if method and m != method or not method and m in RENDER_METHODS:
                continue
            if r.get("url") == url and str(r.get("http_status")) == "200" and not r.get("error") and r.get("local_path"):
                path = run_dir / r["local_path"]
                if path.exists() and path.stat().st_size > 0:
                    return r.get("author", ""), path
    return None


def _transient(exc) -> bool:
    """Kept for callers and tests: is this urllib-style exception worth retrying?"""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in TRANSIENT_HTTP
    return isinstance(exc, (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError, OSError)) \
        and not isinstance(exc, ValueError)


def pdf_pages(path: Path) -> int:
    pages, _, _ = nf.pdf_info(str(path))
    return pages or 0


def candidate_urls(url: str, alts, wayback: bool, work_dir: str):
    """Yield (label, url) in retrieval order. Wayback lookups run lazily, only if the direct sources fail."""
    for i, u in enumerate([url] + list(alts or [])):
        yield ("primary" if i == 0 else "mirror %d" % i), u
    if wayback:
        for i, u in enumerate([url] + list(alts or [])):
            if nf.is_public_host(u):
                for cap in nf.wayback_candidates(u, work_dir, limit=2):
                    yield ("wayback of %s" % ("primary" if i == 0 else "mirror %d" % i)), cap


def retrieve(run_dir: Path, url: str, author: str, name: str = "", alts=None, expect: str = "",
             wayback: bool = True, reuse: bool = True, timeout: float = 90.0, retries: int = 4,
             max_mb: float = 200.0, user_agent: str = "") -> dict:
    """Library entry point (used by document_map.py). Returns the logged row plus `path` and `members`."""
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    row = {"retrieved_at_utc": now.isoformat(), "author": author, "name": name, "url": url}
    cache = run_dir / "_cache" / author
    cache.mkdir(parents=True, exist_ok=True)
    if reuse:
        prior = prior_success(run_dir, url)
        if prior:
            src_author, path = prior
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            row.update({"name": (name + " [reused: downloaded earlier in this run by %s]" % src_author).strip(),
                        "final_url": url, "http_status": 200, "bytes": path.stat().st_size, "sha256": sha,
                        "local_path": str(path.relative_to(run_dir)), "method": "reuse"})
            log_row(run_dir, row)
            return dict(row, path=path, reused_from=src_author, members=_members(path))
    expect = expect or nf.expected_kind(url, name)
    fd, tmp = tempfile.mkstemp(dir=str(cache), prefix=".part-")
    os.close(fd)
    attempts, result, source_label = [], None, ""
    work = str(run_dir / "_cache" / ".net")
    for label, cand in candidate_urls(url, alts, wayback, work):
        try:
            result = nf.fetch(cand, tmp, expect=expect, timeout=timeout, retries=retries,
                              max_bytes=int(max_mb * 1024 * 1024), ua=user_agent or None)
            source_label = label
            attempts.extend(result["attempts"])
            break
        except nf.FetchError as exc:
            attempts.extend(["%s %s -> %s" % (label, cand, a) for a in exc.attempts[-3:]] or
                            ["%s %s -> %s" % (label, cand, exc)])
            row["http_status"] = exc.status or row.get("http_status", "")
    if result is None:
        if os.path.exists(tmp):
            os.unlink(tmp)
        row["error"] = "FetchError: no valid copy from %d source(s): %s" % (
            1 + len(alts or []), " | ".join(attempts[-6:])[:900])
        row["method"] = "failed"
        log_row(run_dir, row)
        return dict(row, path=None, members=[])
    digest, kind = result["sha256"], result["kind"]
    ext = EXT_BY_KIND.get(kind) or EXT_BY_TYPE.get(result.get("content_type", ""), "") or \
        (Path(urllib.parse.urlparse(url).path).suffix.lower()[:6] or ".bin")
    existing = list(cache.glob("*-%s-*" % digest[:12]))
    if existing:
        os.unlink(tmp)
        final = existing[0]
    else:
        final = cache / ("%s-%s-%s%s" % (now.strftime("%Y%m%d"), digest[:12], slug(name or Path(urllib.parse.urlparse(url).path).stem), ext))
        os.replace(tmp, final)
    validation = "ok"
    if result["info"].get("pages"):
        validation = "ok; %s pages" % result["info"]["pages"]
    if result["info"].get("warning"):
        validation += "; " + result["info"]["warning"]
    method = result["method"] + ("" if source_label == "primary" else " via %s" % source_label)
    row.update({"http_status": result["status"], "final_url": result["final_url"], "content_type": result["content_type"],
                "bytes": result["bytes"], "sha256": digest, "local_path": str(final.relative_to(run_dir)),
                "method": method, "validation": validation})
    if source_label != "primary":
        row["name"] = (name + " [%s]" % source_label).strip()
    members = []
    if kind == "zip":
        members = nf.extract_zip(str(final), str(final.with_suffix("")) + "_unzipped")
        sidecar = final.with_suffix(".members.json")
        sidecar.write_text(json.dumps([dict(m, path=str(Path(m["path"]).relative_to(run_dir))) for m in members],
                                      indent=2), encoding="utf-8")
        row["validation"] += "; zip with %d member(s)" % len(members)
    log_row(run_dir, row)
    return dict(row, path=final, members=members, pages=result["info"].get("pages"))


def render(run_dir: Path, url: str, author: str, name: str = "", mode: str = "snapshot", reuse: bool = True,
           timeout: float = 120.0) -> dict:
    """A rendered copy of a public page (mode snapshot -> PDF, dom -> HTML) through headless Chrome, cached and logged
    like a download. Returns the logged row plus `path` (None on failure) and `pages`."""
    method = "chrome-%s" % mode
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    row = {"retrieved_at_utc": now.isoformat(), "author": author, "name": name, "url": url, "method": method}
    cache = run_dir / "_cache" / author
    cache.mkdir(parents=True, exist_ok=True)
    if reuse:
        prior = prior_success(run_dir, url, method)
        if prior:
            src_author, path = prior
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            row.update({"name": (name + " [reused: rendered earlier in this run by %s]" % src_author).strip(),
                        "final_url": url, "http_status": 200, "bytes": path.stat().st_size, "sha256": sha,
                        "local_path": str(path.relative_to(run_dir)), "method": method})
            log_row(run_dir, row)
            return dict(row, path=path, reused_from=src_author, pages=pdf_pages(path) if path.suffix == ".pdf" else 0)
    ext = ".pdf" if mode == "snapshot" else ".html"
    fd, tmp = tempfile.mkstemp(dir=str(cache), prefix=".part-", suffix=ext)
    os.close(fd)
    try:
        res = (browser.snapshot if mode == "snapshot" else browser.dump_dom)(url, tmp, timeout=timeout)
    except browser.BrowserError as exc:
        if os.path.exists(tmp):
            os.unlink(tmp)
        row.update({"error": "BrowserError: %s" % exc, "method": method + " failed"})
        log_row(run_dir, row)
        return dict(row, path=None, pages=0)
    final = cache / ("%s-%s-%s-%s%s" % (now.strftime("%Y%m%d"), res["sha256"][:12],
                                         slug(name or urllib.parse.urlparse(url).netloc + urllib.parse.urlparse(url).path),
                                         mode, ext))
    os.replace(tmp, final)
    row.update({"final_url": url, "http_status": 200, "content_type": "application/pdf" if ext == ".pdf" else "text/html",
                "bytes": res["bytes"], "sha256": res["sha256"], "local_path": str(final.relative_to(run_dir)),
                "validation": ("ok; %s pages; rendered by %s" % (res.get("pages"), Path(res["chrome"]).name)
                               if ext == ".pdf" else "ok; rendered DOM")})
    log_row(run_dir, row)
    return dict(row, path=final, pages=res.get("pages") or 0)


def _members(path: Path):
    sidecar = path.with_suffix(".members.json")
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except ValueError:
            return []
    return []


def text_layer_hint(run_dir: Path, pdf: Path) -> str:
    """The run's shared text layer of this PDF (doc_text.py builds it once per file, keyed by SHA-256, for every
    agent), or the command that builds it. Converting a document privately duplicates that work."""
    h = hashlib.sha256()
    with pdf.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    pages = run_dir / "_cache" / "text" / h.hexdigest()[:12] / "pages.md"
    if pages.exists():
        return "text layer (shared, page-anchored): %s; navigate with doc_text.py toc / page / search" % pages
    return ("text layer: python3 scripts/doc_text.py convert %s %s (built once per run and shared; do not convert "
            "the PDF yourself)" % (run_dir, pdf))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url")
    p.add_argument("--run", required=True, help="run directory")
    p.add_argument("--author", required=True, help="agent name (a specialist, cio or auditor)")
    p.add_argument("--name", default="", help="human label, e.g. 'Annual Report FY2024'")
    p.add_argument("--alt", action="append", default=[], help="mirror URL for the same document (repeatable)")
    p.add_argument("--expect", default="", choices=["", "pdf", "zip", "json", "html", "xml", "csv", "any"],
                   help="payload type to require (default: inferred from the URL)")
    p.add_argument("--no-wayback", action="store_true", help="do not fall back to the Internet Archive")
    p.add_argument("--max-mb", type=float, default=200.0)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--no-reuse", action="store_true", help="download again even if another agent already fetched this URL")
    p.add_argument("--retries", type=int, default=4, help="attempts per transport for transient failures")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--snapshot", action="store_true", help="save the page as rendered by Chrome, as a citable PDF")
    mode.add_argument("--dom", action="store_true", help="save the page's DOM after JavaScript ran (HTML)")
    p.add_argument("--user-agent", default=os.environ.get("EQUITY_RESEARCH_USER_AGENT", ""),
                   help="override the User-Agent (SEC EDGAR requires 'Name contact@email'); default: the host profile")
    a = p.parse_args(argv)

    if a.author not in rl.AGENT_NAMES:
        p.error("--author must be one of: %s" % ", ".join(sorted(rl.AGENT_NAMES)))
    for u in [a.url] + a.alt:
        parsed = urllib.parse.urlparse(u)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            p.error("only absolute http(s) URLs are allowed: %s" % u)
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        p.error("%s is not a run directory (no %s)" % (run_dir, rl.RUN_MANIFEST))

    if a.snapshot or a.dom:
        res = render(run_dir, a.url, a.author, a.name, "snapshot" if a.snapshot else "dom", reuse=not a.no_reuse,
                     timeout=max(a.timeout, 120.0))
        if res.get("path") is None:
            print("FAILED: %s (logged in source_retrievals.csv). Try the raw page (without --%s), a mirror or the "
                  "Internet Archive, or record it as missing evidence." % (res["error"], "snapshot" if a.snapshot else "dom"),
                  file=sys.stderr)
            return 1
        print(res["path"])
        if a.snapshot:
            print("PDF snapshot, %d pages, rendered %s: cite it as [<this file> p.N]; Read it with page ranges." % (
                res.get("pages") or 0, res["retrieved_at_utc"]))
        else:
            print("rendered DOM; tables: python3 scripts/html_tables.py %s" % res["path"])
        print("sha256 %s, %s bytes, %s" % (res["sha256"], res["bytes"], res["method"]))
        return 0
    res = retrieve(run_dir, a.url, a.author, a.name, alts=a.alt, expect="" if a.expect == "any" else a.expect,
                   wayback=not a.no_wayback, reuse=not a.no_reuse, timeout=a.timeout, retries=a.retries,
                   max_mb=a.max_mb, user_agent=a.user_agent)
    if res.get("path") is None:
        print("FAILED: %s (logged in source_retrievals.csv). Next: the alternatives in methodology/RESEARCH_PLAYBOOK.md "
              "§1a (other exchange, IR site, document map, exchange_index.py), then record it as missing evidence."
              % res["error"], file=sys.stderr)
        return 1
    path = res["path"]
    print(path)
    pages = res.get("pages") or (pdf_pages(path) if path.suffix == ".pdf" else 0)
    if path.suffix == ".pdf":
        print("PDF, approx. %d pages. Read with the Read tool, e.g. pages \"1-6\" for the table of contents." % pages)
        print(text_layer_hint(run_dir, path))
    for m in res.get("members") or []:
        print("  zip member: %s (%s, %d bytes, sha256 %s)" % (m["path"], m.get("kind", ""), m["bytes"], m["sha256"][:16]))
    if res.get("method") == "reuse":
        print("reused (sha256 %s); source document only - do not read the other agent's analysis" % res["sha256"])
    else:
        print("sha256 %s, %s bytes, HTTP %s, %s" % (res["sha256"], res["bytes"], res["http_status"], res["method"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
