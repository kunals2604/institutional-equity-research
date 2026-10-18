#!/usr/bin/env python3
"""Reliable HTTP retrieval for the research system (library; used by fetch_source.py, exchange_index.py,
document_map.py, market_data.py and xbrl_facts.py).

Why this exists. Python 3.9 on macOS links LibreSSL 2.8.3, which fails intermittently with
`DECRYPTION_FAILED_OR_BAD_RECORD_MAC` and connection resets under load: the first BHARTIARTL run lost most of
its failed downloads to that client-side bug, and a 12-download stress test on 2026-10-17 failed 3 of 12 with
urllib against 12 of 12 successes with the system curl (SecureTransport, HTTP/2). So:

  * the system **curl is the primary transport**; urllib is the fallback when curl is absent;
  * each host gets a **request profile**: NSE's JSON API needs JSON accept headers and an nseindia.com referer;
    BSE's API (api.bseindia.com) answers 403 unless the request is HTTP/2 with a browser's full header set;
    SEC EDGAR requires a declared user agent; everything else gets a browser-like profile;
  * transient failures (timeouts, resets, TLS errors, HTTP 408/425/429/5xx) are retried with backoff;
  * every payload is **validated** before it is accepted: an HTML "Access Denied" page saved as `report.pdf`,
    a truncated PDF or a corrupt ZIP is a failed retrieval, not a document;
  * dead or moved URLs fall back to the **Internet Archive** (availability API, then CDX), fetching the raw
    archived bytes (`id_` mode), which are the same document the issuer published.

Standard library only (plus the curl binary and, optionally, poppler's pdfinfo). Python 3.9 compatible.
"""

import hashlib
import http.cookiejar
import json
import os
import re
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CHROME_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/126.0.0.0 Safari/537.36")
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}
# curl exit codes worth retrying: resolve/connect failures, partial transfer, timeout, TLS handshake,
# empty reply, send/receive errors, HTTP/2 stream errors.
TRANSIENT_CURL = {5, 6, 7, 16, 18, 28, 35, 52, 55, 56, 92}
ERROR_PAGE_RE = re.compile(
    r"access denied|request rejected|you don't have permission|403 forbidden|404 not found|page not found|"
    r"the page you (are looking for|requested)|service unavailable|bad gateway|gateway time-?out|"
    r"captcha|are you a robot|just a moment\.\.\.|enable javascript and cookies|attention required|"
    r"error occurred while processing|session expired|too many requests",
    re.I,
)

# Request profiles. `match` is tested against the host; the first match wins.
PROFILES = [
    {"name": "nse-api", "match": r"(^|\.)www\.nseindia\.com$", "path": r"^/api/", "http2": False,
     "headers": {"Accept": "application/json, text/plain, */*", "Accept-Language": "en-IN,en;q=0.9",
                 "Referer": "https://www.nseindia.com/"}},
    {"name": "nse-archive", "match": r"(^|\.)(nsearchives|archives)\.nseindia\.com$", "http2": False,
     "headers": {"Accept": "*/*", "Referer": "https://www.nseindia.com/"}},
    {"name": "bse-api", "match": r"^api\.bseindia\.com$", "http2": True,
     "headers": {"accept": "application/json, text/plain, */*", "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                 "origin": "https://www.bseindia.com", "referer": "https://www.bseindia.com/",
                 "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
                 "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"macOS"', "sec-fetch-dest": "empty",
                 "sec-fetch-mode": "cors", "sec-fetch-site": "same-site"}},
    {"name": "bse-file", "match": r"(^|\.)bseindia\.com$", "http2": True,
     "headers": {"accept": "*/*", "referer": "https://www.bseindia.com/"}},
    {"name": "sec", "match": r"(^|\.)sec\.gov$", "http2": False, "declared_ua": True,
     "headers": {"Accept": "*/*"}},
    {"name": "wayback", "match": r"(^|\.)(web\.)?archive\.org$", "http2": False, "headers": {"Accept": "*/*"}},
    {"name": "default", "match": r".*", "http2": False,
     "headers": {"Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9"}},
]


class FetchError(Exception):
    """A retrieval that did not produce a valid payload. `status` is the last HTTP status (or 0)."""

    def __init__(self, message: str, status: int = 0, attempts: Optional[List[str]] = None):
        super().__init__(message)
        self.status = status
        self.attempts = attempts or []


def profile_for(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    host, path = parsed.netloc.lower().split(":")[0], parsed.path
    for prof in PROFILES:
        if re.search(prof["match"], host) and re.search(prof.get("path", ""), path):
            return prof
    return PROFILES[-1]


def user_agent_for(prof: dict, override: Optional[str] = None) -> str:
    if override:
        return override
    if prof.get("declared_ua"):
        declared = os.environ.get("EQUITY_RESEARCH_USER_AGENT", "")
        if declared:
            return declared
    return CHROME_UA


def _sha256_file(path: str) -> Tuple[int, str]:
    sha, size = hashlib.sha256(), 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            sha.update(chunk)
            size += len(chunk)
    return size, sha.hexdigest()


def _curl_once(url: str, dest: str, prof: dict, ua: str, timeout: float, max_bytes: int,
               cookie_jar: Optional[str], extra_headers: Optional[Dict[str, str]]) -> Tuple[int, str, str]:
    curl = shutil.which("curl")
    if not curl:
        raise OSError("curl not available")
    cmd = [curl, "-sS", "-L", "--compressed", "-m", str(int(timeout)), "--max-filesize", str(max_bytes),
           "-A", ua, "-o", dest, "-w", "%{http_code}\t%{content_type}\t%{url_effective}"]
    if prof.get("http2"):
        cmd.insert(1, "--http2")
    headers = dict(prof.get("headers") or {})
    headers.update(extra_headers or {})
    for k, v in headers.items():
        cmd += ["-H", "%s: %s" % (k, v)]
    if cookie_jar:
        cmd += ["-b", cookie_jar, "-c", cookie_jar]
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 30)
    out = (proc.stdout.split("\t") + ["", "", ""])[:3]
    status = int(out[0]) if out[0].strip().isdigit() else 0
    if proc.returncode != 0:
        err = OSError("curl exit %d: %s" % (proc.returncode, proc.stderr.strip()[:200]))
        err.curl_code = proc.returncode  # type: ignore[attr-defined]
        err.http_status = status  # type: ignore[attr-defined]
        raise err
    return status, (out[1] or "").split(";")[0].strip().lower(), out[2] or url


def _urllib_once(url: str, dest: str, prof: dict, ua: str, timeout: float, max_bytes: int,
                 cookie_jar: Optional[str], extra_headers: Optional[Dict[str, str]]) -> Tuple[int, str, str]:
    headers = {"User-Agent": ua}
    headers.update({k.title(): v for k, v in (prof.get("headers") or {}).items() if not k.lower().startswith("sec-")})
    headers.update(extra_headers or {})
    handlers = []
    if cookie_jar:
        jar = http.cookiejar.MozillaCookieJar(cookie_jar)
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except (OSError, http.cookiejar.LoadError):
            pass
        handlers.append(urllib.request.HTTPCookieProcessor(jar))
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()), *handlers)
    req = urllib.request.Request(url, headers=headers)
    size = 0
    try:
        with opener.open(req, timeout=timeout) as resp, open(dest, "wb") as out:
            status, final = resp.status, resp.geturl()
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            for chunk in iter(lambda: resp.read(1 << 16), b""):
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("exceeds the size limit (%d bytes)" % max_bytes)
                out.write(chunk)
    except urllib.error.HTTPError as exc:
        return exc.code, (exc.headers.get("Content-Type") or "").split(";")[0].strip().lower() if exc.headers else "", url
    return status, ctype, final


def sniff(path: str) -> str:
    """Payload kind from magic bytes: pdf | zip | html | json | xml | csv | text | binary | empty."""
    try:
        with open(path, "rb") as f:
            head = f.read(2048)
    except OSError:
        return "empty"
    if not head:
        return "empty"
    if head.startswith(b"%PDF-") or b"%PDF-" in head[:1024]:
        return "pdf"
    if head.startswith(b"PK\x03\x04"):
        return "zip"
    low = head.lstrip()[:600].lower()
    if low.startswith(b"<!doctype html") or low.startswith(b"<html") or b"<html" in low[:300] or b"<head" in low[:300]:
        return "html"
    if low.startswith(b"<?xml") or low.startswith(b"<xbrl") or b"<xbrli:" in low:
        return "xml"
    if low[:1] in (b"{", b"["):
        return "json"
    try:
        text = head.decode("utf-8")
    except UnicodeDecodeError:
        return "binary"
    first = text.splitlines()[0] if text.splitlines() else ""
    return "csv" if first.count(",") >= 2 else "text"


def _pdf_structure(path: str) -> Tuple[Optional[int], Optional[str]]:
    """Structural check: an end-of-file marker near the end, and the page objects counted."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 65536))
            tail = f.read()
            f.seek(0)
            data = f.read()
    except OSError as exc:
        return None, str(exc)
    if b"%%EOF" not in tail:
        return None, "no %%EOF marker: the PDF is truncated or incomplete"
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", data)) or None, None


def pdf_info(path: str) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """(pages, error, warning). Uses poppler's pdfinfo when installed; when pdfinfo cannot parse a file that is
    structurally complete (end-of-file marker present), the file is accepted with a warning. Truncated files fail."""
    tool = shutil.which("pdfinfo")
    if tool:
        try:
            proc = subprocess.run([tool, path], capture_output=True, text=True, timeout=60)
            m = re.search(r"^Pages:\s+(\d+)", proc.stdout, re.M)
            if proc.returncode == 0 and m:
                return int(m.group(1)), None, None
            reason = proc.stderr.strip()[:160] or "no page count"
        except (OSError, subprocess.TimeoutExpired) as exc:
            reason = str(exc)
        pages, err = _pdf_structure(path)
        if err:
            return None, "pdfinfo cannot parse the file (%s) and %s" % (reason, err), None
        return pages, None, "pdfinfo could not parse the file (%s); structural check passed" % reason
    pages, err = _pdf_structure(path)
    return pages, err, None


def is_public_host(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if not host or "." not in host or host == "localhost" or host.endswith(".local"):
        return False
    return not re.fullmatch(r"[\d.]+|[0-9a-f:]+", host)


def validate_payload(path: str, expect: str = "any", ctype: str = "") -> Tuple[str, List[str], Dict[str, object]]:
    """Return (kind, problems, info). Any problem means the retrieval must not be accepted as the document."""
    kind = sniff(path)
    problems: List[str] = []
    info: Dict[str, object] = {}
    size = os.path.getsize(path) if os.path.exists(path) else 0
    if size == 0 or (size < 64 and kind not in ("json", "csv", "xml")):
        problems.append("empty or near-empty response (%d bytes)" % size)   # a valid small JSON (no records) is fine
    if kind == "html" or (kind == "text" and size < 20000):
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")[:20000]
        except OSError:
            text = ""
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        snippet = (title.group(1) if title else text[:400]).strip()
        if ERROR_PAGE_RE.search(snippet) or (size < 6000 and ERROR_PAGE_RE.search(text)):
            problems.append("server returned an error or bot-check page: %r" % re.sub(r"\s+", " ", snippet)[:100])
    if expect in ("pdf", "zip", "json", "xml", "csv") and kind != expect:
        if not (expect == "pdf" and kind == "zip"):        # exchanges publish older annual reports as ZIPs of PDFs
            problems.append("expected %s but received %s%s" % (expect, kind, " (%s)" % ctype if ctype else ""))
    if kind == "pdf":
        pages, err, warning = pdf_info(path)
        info["pages"] = pages
        if err:
            problems.append(err)
        if warning:
            info["warning"] = warning
    elif kind == "zip":
        try:
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                info["members"] = [m.filename for m in zf.infolist() if not m.is_dir()]
            if bad:
                problems.append("corrupt ZIP member: %s" % bad)
        except zipfile.BadZipFile as exc:
            problems.append("corrupt ZIP: %s" % exc)
    elif kind == "json":
        try:
            json.loads(Path(path).read_text(encoding="utf-8", errors="strict"))
        except (ValueError, OSError) as exc:
            problems.append("invalid JSON: %s" % str(exc)[:80])
    return kind, problems, info


def expected_kind(url: str, name: str = "") -> str:
    path = urllib.parse.urlparse(url).path.lower()
    for ext, kind in ((".pdf", "pdf"), (".zip", "zip"), (".json", "json"), (".xml", "xml"), (".csv", "csv")):
        if path.endswith(ext):
            return kind
    if "/api/" in path or "bseindiaapi" in path:
        return "json"
    return "any"


def fetch(url: str, dest: str, *, expect: str = "any", timeout: float = 90.0, max_bytes: int = 200 * 1024 * 1024,
          retries: int = 4, ua: Optional[str] = None, cookie_jar: Optional[str] = None,
          extra_headers: Optional[Dict[str, str]] = None, sleep=time.sleep) -> dict:
    """Download `url` to `dest` with retries and validation. Returns a result dict or raises FetchError.

    Result keys: url, final_url, status, content_type, bytes, sha256, kind, info, method, attempts.
    """
    prof = profile_for(url)
    agent = user_agent_for(prof, ua)
    attempts: List[str] = []
    transports = []
    if shutil.which("curl"):
        transports.append(("curl", _curl_once))
    transports.append(("urllib", _urllib_once))
    last_status = 0
    for tname, fn in transports:
        for i in range(retries):
            label = "%s#%d[%s]" % (tname, i + 1, prof["name"])
            try:
                status, ctype, final = fn(url, dest, prof, agent, timeout, max_bytes, cookie_jar, extra_headers)
            except ValueError as exc:                       # size limit: not retryable
                raise FetchError(str(exc), 0, attempts + ["%s: %s" % (label, exc)])
            except Exception as exc:  # noqa: BLE001 - classified below
                code = getattr(exc, "curl_code", None)
                last_status = getattr(exc, "http_status", 0) or last_status
                attempts.append("%s: %s: %s" % (label, type(exc).__name__, str(exc)[:160]))
                transient = (code in TRANSIENT_CURL) if code is not None else isinstance(
                    exc, (urllib.error.URLError, ssl.SSLError, ConnectionError, TimeoutError, OSError))
                if code is None and str(exc).startswith("curl not available"):
                    break
                if transient and i + 1 < retries:
                    sleep(min(2 ** i * 1.5, 12))
                    continue
                break
            last_status = status
            if status >= 400 or status == 0:
                attempts.append("%s: HTTP %s" % (label, status))
                if status in TRANSIENT_HTTP and i + 1 < retries:
                    sleep(min(2 ** i * 2, 15))
                    continue
                break                                        # 4xx: a different transport may still succeed
            kind, problems, info = validate_payload(dest, expect, ctype)
            if problems:
                attempts.append("%s: HTTP %s but invalid payload: %s" % (label, status, "; ".join(problems)))
                if any("bot-check" in p or "error" in p for p in problems) and i + 1 < retries:
                    sleep(min(2 ** i * 2, 15))
                    continue
                break
            size, digest = _sha256_file(dest)
            return {"url": url, "final_url": final, "status": status, "content_type": ctype, "bytes": size,
                    "sha256": digest, "kind": kind, "info": info, "method": label, "attempts": attempts}
    if os.path.exists(dest):
        os.unlink(dest)
    raise FetchError("all transports failed for %s" % url, last_status, attempts)


def get_json(url: str, work_dir: str, *, timeout: float = 60.0, retries: int = 4, cookie_jar: Optional[str] = None):
    """Fetch and parse a JSON API response (NSE / BSE / Wayback)."""
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    tmp = os.path.join(work_dir, ".json-%s.part" % hashlib.sha1(url.encode()).hexdigest()[:12])
    try:
        fetch(url, tmp, expect="json", timeout=timeout, retries=retries, cookie_jar=cookie_jar)
        with open(tmp, encoding="utf-8") as f:
            return json.load(f)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# --- Internet Archive fallback ------------------------------------------------------------------------

def wayback_candidates(url: str, work_dir: str, timestamp: Optional[str] = None, limit: int = 3) -> List[str]:
    """Raw-capture URLs (web.archive.org/web/<ts>id_/<url>) for a document, newest first."""
    out: List[str] = []
    q = "https://archive.org/wayback/available?url=%s" % urllib.parse.quote(url, safe="")
    if timestamp:
        q += "&timestamp=%s" % timestamp
    try:
        data = get_json(q, work_dir, timeout=40, retries=2)
        snap = ((data or {}).get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("available") and str(snap.get("status", "200")).startswith("2"):
            out.append(raw_capture_url(snap["timestamp"], url))
    except FetchError:
        pass
    cdx = ("https://web.archive.org/cdx/search/cdx?url=%s&output=json&filter=statuscode:200&limit=-%d"
           "&fl=timestamp,original" % (urllib.parse.quote(url, safe=""), limit))
    try:
        rows = get_json(cdx, work_dir, timeout=60, retries=2) or []
        for ts, original in reversed(rows[1:]):
            cand = raw_capture_url(ts, original)
            if cand not in out:
                out.append(cand)
    except (FetchError, ValueError, TypeError):
        pass
    return out[:limit]


def raw_capture_url(timestamp: str, original: str) -> str:
    return "https://web.archive.org/web/%sid_/%s" % (timestamp, original)


def cdx_prefix(prefix: str, work_dir: str, mimetype: Optional[str] = "application/pdf", limit: int = 20000) -> List[dict]:
    """All archived URLs under a host/path prefix (e.g. an IR site's document folder), one row per URL."""
    q = ("https://web.archive.org/cdx/search/cdx?url=%s*&output=json&collapse=urlkey&limit=%d"
         "&fl=timestamp,original,statuscode,mimetype,length" % (urllib.parse.quote(prefix, safe="/:"), limit))
    if mimetype:
        q += "&filter=mimetype:%s" % mimetype
    rows = get_json(q, work_dir, timeout=120, retries=3) or []
    out = []
    for r in rows[1:]:
        ts, original, status, mime, length = (list(r) + [""] * 5)[:5]
        if status and not str(status).startswith("2"):
            continue
        out.append({"timestamp": ts, "url": original, "mimetype": mime, "length": length,
                    "capture_url": raw_capture_url(ts, original)})
    return out


# --- ZIP handling -------------------------------------------------------------------------------------

def extract_zip(path: str, out_dir: str) -> List[dict]:
    """Extract a ZIP safely (no absolute paths or traversal). Returns members with size and SHA-256."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    members = []
    with zipfile.ZipFile(path) as zf:
        for m in zf.infolist():
            if m.is_dir():
                continue
            name = Path(m.filename).name
            if not name or name.startswith("."):
                continue
            target = out / re.sub(r"[^A-Za-z0-9._-]+", "_", name)
            with zf.open(m) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            size, digest = _sha256_file(str(target))
            members.append({"member": m.filename, "path": str(target), "bytes": size, "sha256": digest,
                            "kind": sniff(str(target))})
    return members
