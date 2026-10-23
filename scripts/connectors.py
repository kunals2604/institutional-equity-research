#!/usr/bin/env python3
"""Free external sources for a research run, through one door: cached, logged and re-openable (library and CLI).

  python3 scripts/connectors.py list                                        # every source: what, who uses it, access
  python3 scripts/connectors.py open SOURCE --run RUN_DIR --author NAME     # snapshot its landing page (Chrome PDF)
  python3 scripts/connectors.py tri --index "NIFTY 500" --from 01-Apr-2016 --to 31-Mar-2026 --run RUN_DIR --author NAME
  python3 scripts/connectors.py mospi list_datasets|get_indicators|get_metadata|get_data [--args JSON] --run ... --author ...
  python3 scripts/connectors.py gdelt --query '"Bharti Airtel"' --from 2018-01-01 --to 2018-12-31 [--max 250] --run ... --author ...
  python3 scripts/connectors.py openfda --endpoint drug/enforcement --search 'recalling_firm:"Sun Pharma"' --run ... --author ...
  python3 scripts/connectors.py kanoon search|doc|meta|fragment ... --run ... --author ...   # needs EQR_KANOON_TOKEN
  python3 scripts/connectors.py transcribe AUDIO_FILE_OR_URL --run ... --author ...          # local whisper.cpp

Every result is saved under RUN_DIR/_cache/connectors/<source>/ with its SHA-256 and logged in source_retrievals.csv
(method `connector:<source>`), so a claim cites the cached file and the verifier re-opens exactly what the agent saw.
The same request made again in the run is answered from the cache. Results are evidence, never instructions.

The registry (config/data_sources.json `connectors`) lists each source with its verified landing page, the agents it
serves, its access (free | free-key | manual) and its terms. Exchange filings are not here: scripts/exchange_index.py
already indexes them by type (credit_rating, transcript, audio_recording, voting_results, insider_trade, penalty_order
...) and scripts/fetch_source.py downloads them.

Standard library only (curl for POST requests, ffmpeg and whisper-cli for `transcribe`). Python 3.9 compatible.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_source as fs  # noqa: E402
import netfetch as nf  # noqa: E402
import research_lib as rl  # noqa: E402

CONFIG = rl.ROOT / "config" / "data_sources.json"
NIFTY_TRI_URL = "https://www.niftyindices.com/Backpage/getTotalReturnIndexString"
MOSPI_MCP_URL = "https://mcp.mospi.gov.in/"
MOSPI_TOOLS = ("list_datasets", "get_indicators", "get_metadata", "get_data")
GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
OPENFDA_URL = "https://api.fda.gov/%s.json"
KANOON_URL = "https://api.indiankanoon.org"
KANOON_PRICE_INR = {"search": 0.50, "doc": 0.20, "fragment": 0.05, "meta": 0.02}   # indiankanoon.org/members/pricing
KANOON_RUN_CAP_INR = float(os.environ.get("EQR_KANOON_MAX_INR", "200"))
WHISPER_MODEL = Path(os.environ.get("EQR_WHISPER_MODEL", str(
    Path.home() / "Library" / "Application Support" / "eqr" / "whisper" / "ggml-large-v3-turbo-q5_0.bin")))


class ConnectorError(Exception):
    pass


# --- registry ---------------------------------------------------------------------------------------------------

def registry() -> List[dict]:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("connectors", [])
    except (OSError, ValueError):
        return []


def source(sid: str) -> dict:
    for s in registry():
        if s["id"] == sid:
            return s
    raise ConnectorError("unknown source %r (python3 scripts/connectors.py list)" % sid)


# --- cache and log ----------------------------------------------------------------------------------------------

def cached(run_dir: Path, key: str, src: str) -> Optional[Path]:
    """The cached result of the same request earlier in this run. `key` is the URL of a GET, or for a POST or a
    JSON-RPC call `<endpoint>#<canonical parameters>`: it is what the retrieval log's url column records."""
    hit = fs.prior_success(run_dir, key, "connector:%s" % src)
    return hit[1] if hit else None


def save(run_dir: Path, author: str, src: str, key: str, name: str, data: bytes, ext: str, ctype: str,
         validation: str = "ok") -> Path:
    """Write a result under _cache/connectors/<src>/ and log it. Returns the path."""
    digest = hashlib.sha256(data).hexdigest()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    folder = run_dir / "_cache" / "connectors" / src
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("%s-%s-%s%s" % (now.strftime("%Y%m%d"), digest[:12], fs.slug(name), ext))
    if not path.exists():
        path.write_bytes(data)
    fs.log_row(run_dir, {"retrieved_at_utc": now.isoformat(), "author": author, "name": name, "url": key,
                         "final_url": key, "http_status": 200, "content_type": ctype, "bytes": len(data),
                         "sha256": digest, "local_path": str(path.relative_to(run_dir)),
                         "method": "connector:%s" % src, "validation": validation})
    return path


def log_failure(run_dir: Path, author: str, src: str, key: str, name: str, error: str) -> None:
    fs.log_row(run_dir, {"retrieved_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
                         "author": author, "name": name, "url": key, "error": error[:900],
                         "method": "connector:%s failed" % src})


# --- transport ------------------------------------------------------------------------------------------------------

def http_get(url: str, work: Path, headers: Optional[Dict[str, str]] = None, expect: str = "any") -> bytes:
    work.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(work), prefix=".get-")
    os.close(fd)
    try:
        nf.fetch(url, tmp, expect=expect, timeout=90, retries=3, extra_headers=headers)
        return Path(tmp).read_bytes()
    except nf.FetchError as exc:
        raise ConnectorError("GET %s failed: %s" % (url, " | ".join(exc.attempts[-2:]) or exc))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def http_post(url: str, body: str, headers: Dict[str, str], timeout: int = 120) -> Tuple[int, bytes]:
    """POST through the system curl (Python 3.9's LibreSSL is unreliable: netfetch.py). Returns (status, body)."""
    curl = shutil.which("curl")
    if not curl:
        raise ConnectorError("curl not found")
    cmd = [curl, "-sS", "-L", "-m", str(timeout), "-X", "POST", "-w", "\n%{http_code}", "--data-binary", "@-"]
    for k, v in headers.items():
        cmd += ["-H", "%s: %s" % (k, v)]
    proc = subprocess.run(cmd + [url], input=body.encode("utf-8"), capture_output=True, timeout=timeout + 30)
    if proc.returncode != 0:
        raise ConnectorError("POST %s: curl exit %d: %s" % (url, proc.returncode, proc.stderr.decode()[:200]))
    out, _, code = proc.stdout.rpartition(b"\n")
    return int(code or 0), out


# --- adapters ---------------------------------------------------------------------------------------------------------

def tri(run_dir: Path, author: str, index: str, start: str, end: str) -> Path:
    """NSE indices' total-return (and net total-return) series from niftyindices.com, year by year, as one CSV."""
    d0, d1 = (dt.datetime.strptime(x, "%d-%b-%Y").date() for x in (start, end))
    key = "%s#index=%s&from=%s&to=%s" % (NIFTY_TRI_URL, index.upper(), d0.isoformat(), d1.isoformat())
    hit = cached(run_dir, key, "tri")
    if hit:
        return hit
    headers = {"Content-Type": "application/json; charset=UTF-8", "Origin": "https://www.niftyindices.com",
               "Referer": "https://www.niftyindices.com/reports/historical-data", "X-Requested-With": "XMLHttpRequest",
               "User-Agent": nf.CHROME_UA}
    rows: Dict[str, Tuple[str, str]] = {}
    a = d0
    while a <= d1:
        b = min(dt.date(a.year, 12, 31), d1)
        info = {"name": index, "startDate": a.strftime("%d-%b-%Y"), "endDate": b.strftime("%d-%b-%Y"), "indexName": index}
        status, body = http_post(NIFTY_TRI_URL, json.dumps({"cinfo": json.dumps(info)}), headers)
        try:
            data = json.loads(body.decode("utf-8"))
        except ValueError:
            data = None
        if status != 200 or not isinstance(data, list):
            log_failure(run_dir, author, "tri", key, "TRI %s" % index, "HTTP %s, not a JSON list: %r" % (status, body[:120]))
            raise ConnectorError("niftyindices returned HTTP %s for %s %s..%s" % (status, index, a, b))
        for r in data:
            when = dt.datetime.strptime(r["Date"].strip(), "%d %b %Y").date().isoformat()
            rows[when] = (str(r.get("TotalReturnsIndex", "")).strip(), str(r.get("NTR_Value", "")).strip())
        a = dt.date(b.year + 1, 1, 1)
    if not rows:
        raise ConnectorError("no records for %s between %s and %s" % (index, start, end))
    csv_text = "date,total_return_index,net_total_return_index\n" + "".join(
        "%s,%s,%s\n" % (k, v[0], v[1]) for k, v in sorted(rows.items()))
    return save(run_dir, author, "tri", key, "TRI %s %s to %s" % (index, d0, d1), csv_text.encode(), ".csv", "text/csv",
                "ok; %d trading days; source niftyindices.com" % len(rows))


def mospi(run_dir: Path, author: str, tool: str, args: dict) -> Path:
    """One call to MoSPI's official MCP server (no key): list_datasets -> get_indicators -> get_metadata -> get_data."""
    if tool not in MOSPI_TOOLS:
        raise ConnectorError("MoSPI tool must be one of %s" % ", ".join(MOSPI_TOOLS))
    key = "%s#%s:%s" % (MOSPI_MCP_URL, tool, json.dumps(args, sort_keys=True, separators=(",", ":")))
    hit = cached(run_dir, key, "mospi")
    if hit:
        return hit
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}})
    status, raw = http_post(MOSPI_MCP_URL, body, {"Content-Type": "application/json",
                                                  "Accept": "application/json, text/event-stream"})
    text = raw.decode("utf-8", "replace")
    payload = None
    for line in text.splitlines():                      # a streamable-HTTP reply: server-sent events
        if line.startswith("data:"):
            payload = line[5:].strip()
    try:
        msg = json.loads(payload if payload is not None else text)
    except ValueError:
        log_failure(run_dir, author, "mospi", key, "MoSPI %s" % tool, "HTTP %s: %r" % (status, text[:200]))
        raise ConnectorError("MoSPI returned HTTP %s and no JSON" % status)
    if msg.get("error") or (msg.get("result") or {}).get("isError"):
        err = json.dumps(msg.get("error") or msg["result"].get("content"))[:400]
        log_failure(run_dir, author, "mospi", key, "MoSPI %s" % tool, err)
        raise ConnectorError("MoSPI %s failed: %s" % (tool, err))
    content = (msg.get("result") or {}).get("content") or []
    out = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
    try:
        out = json.dumps(json.loads(out), indent=1, ensure_ascii=False)
        ext, ctype = ".json", "application/json"
    except ValueError:
        ext, ctype = ".txt", "text/plain"
    return save(run_dir, author, "mospi", key, "MoSPI %s %s" % (tool, args.get("dataset", "")), out.encode("utf-8"),
                ext, ctype, "ok; MoSPI MCP %s" % tool)


def gdelt(run_dir: Path, author: str, query: str, start: str, end: str, maxrecords: int = 250) -> Path:
    """News articles matching a query in a date range (GDELT DOC 2.0, from 2017): url, title, date, domain, country.
    Leads only: open and cite the article (fetch_source.py --snapshot), never the list."""
    d0, d1 = (dt.datetime.strptime(x, "%Y-%m-%d") for x in (start, end))
    params = {"query": query, "mode": "artlist", "format": "json", "maxrecords": str(min(int(maxrecords), 250)),
              "sort": "datedesc", "startdatetime": d0.strftime("%Y%m%d000000"), "enddatetime": d1.strftime("%Y%m%d235959")}
    url = GDELT_DOC_URL + "?" + urllib.parse.urlencode(params)
    hit = cached(run_dir, url, "gdelt")
    if hit:
        return hit
    try:
        data = http_get(url, run_dir / "_cache" / ".net")
    except ConnectorError as exc:
        log_failure(run_dir, author, "gdelt", url, "GDELT %s" % query, str(exc))
        raise
    try:
        n = len(json.loads(data.decode("utf-8")).get("articles", []))
    except ValueError:
        log_failure(run_dir, author, "gdelt", url, "GDELT %s" % query, "not JSON: %r" % data[:200])
        raise ConnectorError("GDELT did not return JSON: %r" % data[:200])
    return save(run_dir, author, "gdelt", url, "GDELT %s %s to %s" % (query, start, end), data, ".json",
                "application/json", "ok; %d articles (leads, not evidence)" % n)


def openfda(run_dir: Path, author: str, endpoint: str, search: str, limit: int = 100, skip: int = 0) -> Path:
    """openFDA (no key at low volume): drug/enforcement (recalls), drug/drugsfda (approvals), device/... ."""
    if not re.fullmatch(r"(drug|device|food|animalandveterinary|other|tobacco)/[a-z0-9_]+", endpoint):
        raise ConnectorError("endpoint like drug/enforcement or drug/drugsfda")
    url = OPENFDA_URL % endpoint + "?" + urllib.parse.urlencode({"search": search, "limit": str(min(limit, 1000)),
                                                                  "skip": str(skip)})
    hit = cached(run_dir, url, "openfda")
    if hit:
        return hit
    try:
        data = http_get(url, run_dir / "_cache" / ".net", expect="json")
    except ConnectorError as exc:
        log_failure(run_dir, author, "openfda", url, "openFDA %s" % search, str(exc))
        raise
    meta = json.loads(data.decode("utf-8")).get("meta", {})
    total = (meta.get("results") or {}).get("total")
    return save(run_dir, author, "openfda", url, "openFDA %s %s" % (endpoint, search), data, ".json", "application/json",
                "ok; %s results in all; data updated %s" % (total, meta.get("last_updated", "?")))


def kanoon_token() -> str:
    tok = os.environ.get("EQR_KANOON_TOKEN", "")
    if not tok and shutil.which("security"):          # the macOS Keychain: security add-generic-password -s eqr-indiankanoon -a api -w <token>
        r = subprocess.run(["security", "find-generic-password", "-s", "eqr-indiankanoon", "-w"], capture_output=True, text=True)
        tok = r.stdout.strip() if r.returncode == 0 else ""
    if not tok:
        raise ConnectorError("no Indian Kanoon API token: sign up at api.indiankanoon.org (Rs 500 free credit; "
                             "non-commercial use can apply for Rs 10,000/month free), then set EQR_KANOON_TOKEN or "
                             "store it in the Keychain as service eqr-indiankanoon")
    return tok


def kanoon_spent(run_dir: Path) -> float:
    log = run_dir / "source_retrievals.csv"
    if not log.exists():
        return 0.0
    import csv
    spent = 0.0
    with log.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("method") == "connector:kanoon":
                m = re.search(r"/(search|docfragment|docmeta|doc)/", r.get("url", ""))
                if m:
                    spent += KANOON_PRICE_INR[{"docfragment": "fragment", "docmeta": "meta"}.get(m.group(1), m.group(1))]
    return spent


def kanoon(run_dir: Path, author: str, action: str, query: str = "", docid: str = "", page: int = 0,
           doctypes: str = "", fromdate: str = "", todate: str = "") -> Path:
    """Indian Kanoon API: search judgments and orders (Supreme Court, High Courts, tribunals: NCLT, NCLAT, SAT, CCI ...),
    a document, its metadata, or the fragments matching a query. Paid per request (KANOON_PRICE_INR); capped per run."""
    if action == "search":
        q = query + ("" if not doctypes else " doctypes:%s" % doctypes) + \
            ("" if not fromdate else " fromdate:%s" % fromdate) + ("" if not todate else " todate:%s" % todate)
        path = "/search/?" + urllib.parse.urlencode({"formInput": q, "pagenum": str(page)})
    elif action in ("doc", "meta", "fragment"):
        if not re.fullmatch(r"\d+", docid or ""):
            raise ConnectorError("--id DOCID (digits) required")
        path = {"doc": "/doc/%s/", "meta": "/docmeta/%s/", "fragment": "/docfragment/%s/"}[action] % docid
        if action == "fragment":
            path += "?" + urllib.parse.urlencode({"formInput": query})
    else:
        raise ConnectorError("action must be search | doc | meta | fragment")
    url = KANOON_URL + path
    hit = cached(run_dir, url, "kanoon")
    if hit:
        return hit
    price = KANOON_PRICE_INR[action]
    if kanoon_spent(run_dir) + price > KANOON_RUN_CAP_INR:
        raise ConnectorError("the run's Indian Kanoon budget (Rs %.0f, EQR_KANOON_MAX_INR) is spent" % KANOON_RUN_CAP_INR)
    status, body = http_post(url, "", {"Authorization": "Token %s" % kanoon_token(), "Accept": "application/json"})
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        data = None
    if status != 200 or not isinstance(data, dict) or data.get("errmsg"):
        err = "HTTP %s: %s" % (status, (data or {}).get("errmsg") if isinstance(data, dict) else body[:200])
        log_failure(run_dir, author, "kanoon", url, "Indian Kanoon %s" % action, err)
        raise ConnectorError("Indian Kanoon %s failed: %s" % (action, err))
    return save(run_dir, author, "kanoon", url, "Indian Kanoon %s %s" % (action, query or docid),
                json.dumps(data, indent=1, ensure_ascii=False).encode("utf-8"), ".json", "application/json",
                "ok; Rs %.2f" % price)


def transcribe(run_dir: Path, author: str, audio: str, language: str = "en") -> Path:
    """An earnings-call recording (a cached file, or a URL fetched through fetch_source.py) transcribed locally with
    whisper.cpp: a text transcript with timestamps. The recording stays the source; cite the transcript's timestamps
    against it and treat names and numbers the model heard as needing confirmation in a filing."""
    whisper = shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    ffmpeg = shutil.which("ffmpeg")
    if not (whisper and ffmpeg):
        raise ConnectorError("needs whisper.cpp and ffmpeg: brew install whisper-cpp ffmpeg")
    if not WHISPER_MODEL.exists():
        raise ConnectorError("whisper model missing at %s (python3 scripts/connectors.py setup-whisper)" % WHISPER_MODEL)
    if re.match(r"https?://", audio):
        res = fs.retrieve(run_dir, audio, author, "Earnings call recording", expect="any")
        if not res.get("path"):
            raise ConnectorError("could not download %s: %s" % (audio, res.get("error")))
        src = Path(res["path"])
    else:
        src = Path(audio)
        if not src.is_absolute():
            src = run_dir / src
    if not src.exists():
        raise ConnectorError("no such audio file: %s" % src)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    key = "transcribe:%s" % digest
    hit = cached(run_dir, key, "transcribe")
    if hit:
        return hit
    with tempfile.TemporaryDirectory(prefix="eqr-whisper-") as tmp:
        wav = Path(tmp) / "audio.wav"
        r = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(src), "-ar", "16000", "-ac", "1",
                            "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            raise ConnectorError("ffmpeg failed: %s" % r.stderr[-300:])
        out = Path(tmp) / "transcript"
        r = subprocess.run([whisper, "-m", str(WHISPER_MODEL), "-f", str(wav), "-l", language, "-otxt", "-ovtt",
                            "-of", str(out)], capture_output=True, text=True, timeout=6 * 3600)
        if r.returncode != 0 or not out.with_suffix(".vtt").exists():
            raise ConnectorError("whisper failed: %s" % (r.stderr[-300:] or r.stdout[-300:]))
        text = out.with_suffix(".vtt").read_text(encoding="utf-8", errors="replace")
    header = ("Machine transcript (whisper.cpp, %s) of %s (sha256 %s). Timestamps refer to the recording; names and "
              "numbers heard by the model need confirmation in a filing.\n\n" % (WHISPER_MODEL.name, src.name, digest[:16]))
    return save(run_dir, author, "transcribe", key, "Transcript of %s" % src.stem, (header + text).encode("utf-8"),
                ".vtt.txt", "text/plain", "ok; machine transcript")


def setup_whisper() -> Path:
    """Download the whisper.cpp model once (large-v3-turbo, 5-bit quantised, about 0.6 GB) from the whisper.cpp
    project's Hugging Face repository."""
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/%s" % WHISPER_MODEL.name
    WHISPER_MODEL.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(WHISPER_MODEL) + ".part"
    nf.fetch(url, tmp, expect="any", timeout=3600, retries=3, max_bytes=3 * 1024 ** 3)
    os.replace(tmp, WHISPER_MODEL)
    return WHISPER_MODEL


def open_source(run_dir: Path, author: str, sid: str) -> Path:
    s = source(sid)
    if not s.get("landing"):
        raise ConnectorError("%s has no landing page" % sid)
    res = fs.render(run_dir, s["landing"], author, "%s landing page" % s["name"], "snapshot")
    if not res.get("path"):
        raise ConnectorError("%s: %s%s" % (sid, res.get("error"), (" (access: %s; %s)" % (s.get("access"), s.get("notes", "")))
                                           if s.get("access") == "manual" else ""))
    return res["path"]


# --- CLI ------------------------------------------------------------------------------------------------------------------

def print_list() -> None:
    rows = registry()
    print("%-14s %-9s %-10s %s" % ("source", "access", "kind", "what (agents) - landing page"))
    for s in rows:
        print("%-14s %-9s %-10s %s (%s)%s" % (s["id"], s.get("access", ""), s.get("kind", ""), s.get("what", ""),
                                              ", ".join(s.get("agents", [])), (" - " + s["landing"]) if s.get("landing") else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("setup-whisper", help="download the whisper.cpp model once")

    def run_args(p):
        p.add_argument("--run", required=True)
        p.add_argument("--author", required=True)
    p = sub.add_parser("open"); p.add_argument("source"); run_args(p)
    p = sub.add_parser("tri"); p.add_argument("--index", required=True); p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True); run_args(p)
    p = sub.add_parser("mospi"); p.add_argument("tool", choices=MOSPI_TOOLS); p.add_argument("--args", default="{}"); run_args(p)
    p = sub.add_parser("gdelt"); p.add_argument("--query", required=True); p.add_argument("--from", dest="start", required=True)
    p.add_argument("--to", dest="end", required=True); p.add_argument("--max", type=int, default=250); run_args(p)
    p = sub.add_parser("openfda"); p.add_argument("--endpoint", default="drug/enforcement"); p.add_argument("--search", required=True)
    p.add_argument("--limit", type=int, default=100); p.add_argument("--skip", type=int, default=0); run_args(p)
    p = sub.add_parser("kanoon"); p.add_argument("action", choices=("search", "doc", "meta", "fragment"))
    p.add_argument("--query", default=""); p.add_argument("--id", default=""); p.add_argument("--page", type=int, default=0)
    p.add_argument("--doctypes", default=""); p.add_argument("--fromdate", default=""); p.add_argument("--todate", default="")
    run_args(p)
    p = sub.add_parser("transcribe"); p.add_argument("audio"); p.add_argument("--language", default="en"); run_args(p)
    a = ap.parse_args(argv)
    if a.cmd == "list":
        print_list()
        return 0
    if a.cmd == "setup-whisper":
        print(setup_whisper())
        return 0
    run_dir = Path(a.run)
    if not (run_dir / rl.RUN_MANIFEST).exists():
        ap.error("%s is not a run directory" % run_dir)
    if a.author not in rl.AGENT_NAMES:
        ap.error("--author must be one of: %s" % ", ".join(sorted(rl.AGENT_NAMES)))
    try:
        if a.cmd == "open":
            path = open_source(run_dir, a.author, a.source)
        elif a.cmd == "tri":
            path = tri(run_dir, a.author, a.index, a.start, a.end)
        elif a.cmd == "mospi":
            path = mospi(run_dir, a.author, a.tool, json.loads(a.args))
        elif a.cmd == "gdelt":
            path = gdelt(run_dir, a.author, a.query, a.start, a.end, a.max)
        elif a.cmd == "openfda":
            path = openfda(run_dir, a.author, a.endpoint, a.search, a.limit, a.skip)
        elif a.cmd == "kanoon":
            path = kanoon(run_dir, a.author, a.action, a.query, a.id, a.page, a.doctypes, a.fromdate, a.todate)
        else:
            path = transcribe(run_dir, a.author, a.audio, a.language)
    except (ConnectorError, ValueError) as exc:
        print("FAILED: %s" % exc, file=sys.stderr)
        return 1
    print(path)
    print("cached and logged in source_retrievals.csv; cite this file. Read it with the Read tool (in ranges if large).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
