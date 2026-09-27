#!/usr/bin/env python3
"""Check whether domains are registered, asking the registries themselves.

For each domain, in order:
  1. Result cache: answers younger than 6 hours are reused (--no-cache skips it).
  2. DNS-over-HTTPS NS lookup (Cloudflare): a delegated name is TAKEN (--no-doh skips it).
     An undelegated name is not proof of anything: registered names can lack NS records.
  3. Registry RDAP. The server comes from the IANA bootstrap (cached for a day) plus
     RDAP_OVERRIDES for registries missing from it. 200 = TAKEN, 404 = AVAILABLE.
     Routers such as rdap.org are never used: their "no service" 404 says nothing.
  4. WHOIS over port 43 when the TLD has no RDAP server or its server refuses us
     (Retry-After above 30 s, repeated errors).
  5. Otherwise UNKNOWN. UNKNOWN is never a guess at AVAILABLE.

Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import email.utils
import http.client
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

AVAILABLE = "AVAILABLE"
TAKEN = "TAKEN"
UNKNOWN = "UNKNOWN"

IANA_RDAP_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
IANA_WHOIS = "whois.iana.org"
DOH_URL = "https://cloudflare-dns.com/dns-query"
USER_AGENT = "domain-search-skill (+https://github.com/thattimc/skills)"

# Registries that run RDAP but are missing from the IANA bootstrap. Verified 2026-09:
# rdap.registry.co/co/ answers google.co with 200 and an unregistered .co with 404 (the bare
# host answers 404 for everything). .io/.me/.sh share Identity Digital's server with .ai.
RDAP_OVERRIDES = {
    "co": "https://rdap.registry.co/co/",
    "io": "https://rdap.identitydigital.services/rdap/",
    "me": "https://rdap.identitydigital.services/rdap/",
    "sh": "https://rdap.identitydigital.services/rdap/",
}

# Routers answer a 404 of their own for TLDs they have no server for, so a 404 from them
# says nothing about the domain.
RDAP_ROUTERS = frozenset({"rdap.org", "www.rdap.org"})

# Known registry WHOIS servers. Other TLDs are looked up once at whois.iana.org.
WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.publicinterestregistry.org",
    "ai": "whois.nic.ai",
    "io": "whois.nic.io",
    "me": "whois.nic.me",
    "sh": "whois.nic.sh",
    "co": "whois.registry.co",
    "app": "whois.nic.google",
    "dev": "whois.nic.google",
    "gg": "whois.gg",
}

# Parallel RDAP requests per registry host. Verisign answered 8 in parallel without errors;
# every other value is a conservative guess, not a published limit.
HOST_CONCURRENCY = {
    "rdap.verisign.com": 8,
    "pubapi.registry.google": 4,  # guess
    "rdap.identitydigital.services": 1,  # guess; it locks an IP out for ~24 h when pushed
}
DEFAULT_CONCURRENCY = 2  # guess
# Minimum seconds between requests to one host (guess).
HOST_MIN_INTERVAL = {"rdap.identitydigital.services": 1.0}
WHOIS_CONCURRENCY = 1
DOH_CONCURRENCY = 8
MAX_WORKERS = 16

MAX_RETRY_AFTER = 30.0  # a longer Retry-After switches the host to WHOIS instead of sleeping
RDAP_ATTEMPTS = 3
HTTP_TIMEOUT = 12.0
DOH_TIMEOUT = 5.0
WHOIS_TIMEOUT = 10.0

RESULT_TTL = 6 * 3600
BOOTSTRAP_TTL = 24 * 3600
WHOIS_REFERRAL_TTL = 30 * 24 * 3600

LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")

WHOIS_NOT_FOUND = re.compile(
    r"""^[\s%#>*]*(?:
        no\ match\b
      | not\ found\b
      | domain\ not\ found\b
      | no\ entries\ found\b
      | no\ data\ found\b
      | no\ object\ found\b
      | nothing\ found\b
      | object\ does\ not\ exist\b
      | the\ queried\ object\ does\ not\ exist\b
      | no\ matching\ record\b
      | (?:domain\ )?status:\s*(?:free|available|no\ object\ found)\s*$
      | this\ domain\ name\ has\ not\ been\ registered\b
      | the\ domain\ has\ not\ been\ registered\b
    )""",
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)
WHOIS_REGISTERED = re.compile(
    r"^\s*(?:domain(?:\s+name)?|registry\s+domain\s+id|registrar|creation\s+date|created"
    r"|registered(?:\s+on)?|nserver|name\s+servers?)\s*:\s*\S",
    re.IGNORECASE | re.MULTILINE,
)
WHOIS_RESERVED = re.compile(
    r"^\W*(?:reserved\b|.*\bis\s+reserved\b|(?:domain\s+)?status:\s*reserved\b)",
    re.IGNORECASE | re.MULTILINE,
)
WHOIS_RATE_LIMITED = re.compile(
    r"limit\s+exceeded|exceeded\s+(?:the\s+)?(?:query|request)|too\s+many\s+(?:queries|requests)"
    r"|try\s+again\s+later|quota",
    re.IGNORECASE,
)


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    body: bytes


@dataclass
class Result:
    domain: str
    status: str
    source: Optional[str] = None  # "rdap", "whois" or "doh"; None when UNKNOWN
    detail: str = ""
    cached: bool = False

    def to_json(self) -> dict:
        return {
            "domain": self.domain,
            "status": self.status,
            "source": self.source,
            "detail": self.detail,
            "cached": self.cached,
        }


Fetch = Callable[..., HttpResponse]
WhoisQuery = Callable[..., str]


def http_get(url: str, headers: Dict[str, str], timeout: float = HTTP_TIMEOUT) -> HttpResponse:
    """GET a URL. HTTP errors come back as responses; network failures raise OSError."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResponse(
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )
    except urllib.error.HTTPError as error:
        headers_out = {key.lower(): value for key, value in (error.headers or {}).items()}
        return HttpResponse(error.code, headers_out, error.read() if error.fp else b"")


def whois_query(server: str, query: str, timeout: float = WHOIS_TIMEOUT) -> str:
    """Send one WHOIS query over TCP port 43 and return the reply text."""
    chunks: List[bytes] = []
    size = 0
    with socket.create_connection((server, 43), timeout=timeout) as sock:
        sock.sendall((query + "\r\n").encode("ascii"))
        while size < 1_000_000:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
    return b"".join(chunks).decode("utf-8", "replace")


def normalize_domain(raw: str) -> Optional[str]:
    """Lower-case, strip scheme/path/trailing dot, punycode. None when it is not a domain."""
    value = raw.strip().lower()
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = value.split("/", 1)[0].rstrip(".")
    if not value:
        return None
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = value.split(".")
    if len(labels) < 2 or not all(LABEL_RE.fullmatch(label) for label in labels):
        return None
    return value


def build_domain_list(args: Iterable[str], tlds: Optional[str]) -> List[str]:
    """Expand bare names across TLDs (default .com), keep FQDNs, drop duplicates in order."""
    tld_list = [
        part.strip().strip(".").lower()
        for part in (tlds or "").split(",")
        if part.strip().strip(".")
    ] or ["com"]
    candidates: List[str] = []
    for arg in args:
        arg = arg.strip()
        if not arg:
            continue
        bare = arg.strip(".")
        if "." in bare:
            candidates.append(arg)
        else:
            candidates.extend(f"{bare}.{tld}" for tld in tld_list)
    seen = set()
    domains: List[str] = []
    for candidate in candidates:
        key = normalize_domain(candidate) or candidate.lower()
        if key not in seen:
            seen.add(key)
            domains.append(key)
    return domains


def bootstrap_map(data: dict) -> Dict[str, str]:
    """Map each TLD in an IANA RDAP bootstrap file to its first (https-preferred) base URL."""
    mapping: Dict[str, str] = {}
    for service in data.get("services") or []:
        if not isinstance(service, list) or len(service) != 2:
            continue
        tlds, urls = service
        urls = sorted(
            (url for url in urls if isinstance(url, str)),
            key=lambda url: not url.startswith("https:"),
        )
        if not urls:
            continue
        for tld in tlds:
            if isinstance(tld, str):
                mapping[tld.lower()] = urls[0]
    return mapping


def is_router(url: str) -> bool:
    return (urllib.parse.urlparse(url).hostname or "") in RDAP_ROUTERS


def rdap_base_for(
    domain: str,
    bootstrap: Dict[str, str],
    overrides: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """The registry RDAP base URL for a domain (longest suffix wins, overrides first)."""
    overrides = RDAP_OVERRIDES if overrides is None else overrides
    labels = domain.split(".")
    for index in range(1, len(labels)):
        suffix = ".".join(labels[index:])
        for table in (overrides, bootstrap):
            base = table.get(suffix)
            if base and not is_router(base):
                return base if base.endswith("/") else base + "/"
    return None


def interpret_rdap(url: str, response: HttpResponse) -> Tuple[str, str]:
    """Classify an RDAP reply: AVAILABLE, TAKEN, RETRY, or NO_SERVICE (fall back)."""
    text = response.body[:4096].decode("utf-8", "replace")
    if is_router(url) or "no rdap service" in text.lower():
        return "NO_SERVICE", "no registry RDAP server for this TLD"
    if response.status == 200:
        try:
            data = json.loads(response.body)
        except ValueError:
            return "NO_SERVICE", "RDAP 200 without an RDAP record"
        is_domain = isinstance(data, dict) and (
            data.get("objectClassName") == "domain" or "ldhName" in data
        )
        if is_domain:
            return TAKEN, "registry RDAP record exists"
        return "NO_SERVICE", "RDAP 200 without a domain record"
    if response.status == 404:
        return AVAILABLE, "registry RDAP 404 (no registration)"
    if response.status == 429 or 500 <= response.status < 600:
        return "RETRY", f"RDAP HTTP {response.status}"
    return "NO_SERVICE", f"RDAP HTTP {response.status}"


def parse_retry_after(value: Optional[str], now: float) -> Optional[float]:
    """Seconds to wait from a Retry-After header (delta-seconds or HTTP-date)."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    return max(0.0, when.timestamp() - now)


def interpret_doh(data: dict, domain: str) -> bool:
    """True when a DNS JSON reply shows NS records for exactly this domain."""
    if data.get("Status") != 0:
        return False
    for record in data.get("Answer") or []:
        name = str(record.get("name", "")).rstrip(".").lower()
        if record.get("type") == 2 and name == domain:
            return True
    return False


def parse_whois(text: str, domain: str) -> Tuple[str, str]:
    """Classify a registry WHOIS reply as AVAILABLE, TAKEN, or UNKNOWN."""
    lowered = text.lower()
    if not text.strip():
        return UNKNOWN, "empty WHOIS reply"
    if WHOIS_NOT_FOUND.search(text) or re.search(
        rf"^\s*{re.escape(domain)}\s+is\s+free\b", text, re.IGNORECASE | re.MULTILINE
    ):
        return AVAILABLE, "registry WHOIS has no record"
    if domain in lowered and WHOIS_REGISTERED.search(text):
        return TAKEN, "registry WHOIS record exists"
    if WHOIS_RESERVED.search(text):
        return TAKEN, "reserved by the registry"
    if WHOIS_RATE_LIMITED.search(text):
        return UNKNOWN, "WHOIS rate-limited"
    return UNKNOWN, "unrecognized WHOIS reply"


def duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}h{seconds % 3600 // 60:02d}m"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def stamp(entry: object, key: str) -> float:
    """A cached entry's timestamp; 0 (expired) when missing or malformed."""
    try:
        return float(entry.get(key, 0))  # type: ignore[union-attr]
    except (AttributeError, TypeError, ValueError):
        return 0.0


def default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "domain-search"


class Cache:
    """Small JSON files under the cache directory. Failures to write are ignored."""

    def __init__(self, directory: Path, now: Callable[[], float]):
        self.directory = directory
        self.now = now
        self._lock = threading.Lock()

    def read(self, name: str) -> Optional[dict]:
        try:
            data = json.loads((self.directory / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def write(self, name: str, data: dict) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary = self.directory / f".{name}.{os.getpid()}.{threading.get_ident()}"
            temporary.write_text(json.dumps(data), encoding="utf-8")
            os.replace(temporary, self.directory / name)
        except OSError:
            pass

    def update(self, name: str, entries: dict, ttl: float, stamp_key: str) -> None:
        """Merge entries into a file, dropping ones older than ttl."""
        with self._lock:
            current = self.read(name) or {}
            current.update(entries)
            now = self.now()
            fresh = {
                key: value
                for key, value in current.items()
                if isinstance(value, dict) and now - stamp(value, stamp_key) < ttl
            }
            self.write(name, fresh)


class Checker:
    def __init__(
        self,
        *,
        cache_dir: Optional[Path] = None,
        use_cache: bool = True,
        use_doh: bool = True,
        fetch: Fetch = http_get,
        whois: WhoisQuery = whois_query,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], float] = time.time,
        warn: Optional[Callable[[str], None]] = None,
    ):
        self.cache = Cache(cache_dir or default_cache_dir(), now)
        self.use_cache = use_cache
        self.use_doh = use_doh
        self.fetch = fetch
        self.whois = whois
        self.sleep = sleep
        self.now = now
        self.warn = warn or (lambda message: print(f"warning: {message}", file=sys.stderr))
        self._lock = threading.Lock()
        self._bootstrap_lock = threading.Lock()
        self._semaphores: Dict[str, threading.BoundedSemaphore] = {}
        self._next_request_at: Dict[str, float] = {}
        self._bootstrap: Optional[Dict[str, str]] = None
        self._whois_servers: Optional[dict] = None
        self._warned = set()
        blocks = self.cache.read("rdap-blocks.json") or {}
        self._blocked_until: Dict[str, float] = {
            host: float(until)
            for host, until in blocks.items()
            if isinstance(until, (int, float)) and until > now()
        }
        self._results = (self.cache.read("results.json") or {}) if use_cache else {}

    # -- public -------------------------------------------------------------------------

    def check_many(self, domains: List[str]) -> List[Result]:
        results: List[Optional[Result]] = [None] * len(domains)
        workers = max(1, min(MAX_WORKERS, len(domains)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self.check_one, domain): index for index, domain in enumerate(domains)
            }
            for future in concurrent.futures.as_completed(futures):
                index = futures[future]
                try:
                    results[index] = future.result()
                except Exception as error:  # one bad domain must not sink the batch
                    results[index] = Result(
                        domains[index], UNKNOWN, None, f"internal error: {error}"
                    )
        final = [result for result in results if result is not None]
        stamp = self.now()
        fresh = {
            result.domain: {
                "status": result.status,
                "source": result.source,
                "detail": result.detail,
                "checked_at": stamp,
            }
            for result in final
            if result.status != UNKNOWN and not result.cached
        }
        if fresh:
            self.cache.update("results.json", fresh, RESULT_TTL, "checked_at")
        return final

    def check_one(self, raw: str) -> Result:
        domain = normalize_domain(raw)
        if domain is None:
            return Result(raw, UNKNOWN, None, "not a valid domain name")
        cached = self._cached(domain)
        if cached:
            return cached
        if self.use_doh and self._delegated(domain):
            return Result(domain, TAKEN, "doh", "delegated in DNS (has NS records)")
        result, reason = self._rdap(domain)
        if result:
            return result
        return self._whois(domain, reason)

    # -- cache --------------------------------------------------------------------------

    def _cached(self, domain: str) -> Optional[Result]:
        if not self.use_cache:
            return None
        entry = self._results.get(domain)
        if not isinstance(entry, dict) or entry.get("status") not in (AVAILABLE, TAKEN):
            return None
        if self.now() - stamp(entry, "checked_at") >= RESULT_TTL:
            return None
        return Result(domain, entry["status"], entry.get("source"), entry.get("detail", ""), cached=True)

    # -- DNS over HTTPS -----------------------------------------------------------------

    def _delegated(self, domain: str) -> bool:
        url = DOH_URL + "?" + urllib.parse.urlencode({"name": domain, "type": "NS"})
        with self._semaphore("doh", DOH_CONCURRENCY):
            try:
                response = self.fetch(url, {"Accept": "application/dns-json"}, timeout=DOH_TIMEOUT)
            except (OSError, http.client.HTTPException, ValueError) as error:
                self._note_network_error(error)
                return False
        if response.status != 200:
            return False
        try:
            return interpret_doh(json.loads(response.body), domain)
        except (ValueError, AttributeError):
            return False

    # -- RDAP ---------------------------------------------------------------------------

    def bootstrap(self) -> Dict[str, str]:
        with self._bootstrap_lock:
            if self._bootstrap is None:
                self._bootstrap = self._load_bootstrap()
            return self._bootstrap

    def _load_bootstrap(self) -> Dict[str, str]:
        cached = self.cache.read("rdap-dns.json")
        if cached and self.now() - stamp(cached, "fetched_at") < BOOTSTRAP_TTL:
            return bootstrap_map(cached.get("data") or {})
        try:
            response = self.fetch(IANA_RDAP_BOOTSTRAP, {"Accept": "application/json"})
            if response.status == 200:
                data = json.loads(response.body)
                if isinstance(data, dict) and data.get("services"):
                    self.cache.write("rdap-dns.json", {"fetched_at": self.now(), "data": data})
                    return bootstrap_map(data)
        except (OSError, http.client.HTTPException, ValueError) as error:
            self._note_network_error(error)
        if cached:
            return bootstrap_map(cached.get("data") or {})  # stale beats nothing
        self._warn_once("bootstrap", "could not load the IANA RDAP bootstrap; using overrides and WHOIS")
        return {}

    def _rdap(self, domain: str) -> Tuple[Optional[Result], str]:
        base = rdap_base_for(domain, self.bootstrap())
        if base is None:
            return None, "no registry RDAP server for this TLD"
        url = base + "domain/" + domain
        host = urllib.parse.urlparse(url).hostname or base
        reason = "RDAP gave no answer"
        for attempt in range(RDAP_ATTEMPTS):
            blocked = self._wait_for(host)
            if blocked:
                return None, blocked
            response: Optional[HttpResponse] = None
            failure: BaseException = OSError("no response")
            with self._semaphore(host, HOST_CONCURRENCY.get(host, DEFAULT_CONCURRENCY)):
                self._pace(host)
                try:
                    response = self.fetch(url, {"Accept": "application/rdap+json"})
                except (OSError, http.client.HTTPException, ValueError) as error:
                    failure = error
            if response is None:
                reason = f"RDAP network error ({failure.__class__.__name__})"
                if self._note_network_error(failure):
                    break  # retrying cannot fix certificate verification
                if attempt < RDAP_ATTEMPTS - 1:
                    self.sleep(2**attempt)
                continue
            verdict, detail = interpret_rdap(url, response)
            if verdict in (AVAILABLE, TAKEN):
                return Result(domain, verdict, "rdap", detail), ""
            if verdict != "RETRY":
                return None, detail
            reason = detail
            retry_after = parse_retry_after(response.headers.get("retry-after"), self.now())
            if retry_after is not None and retry_after > MAX_RETRY_AFTER:
                self._block(host, self.now() + retry_after)
                return None, f"{host} asked us to wait {duration(retry_after)}"
            self._defer(host, self.now() + (retry_after if retry_after is not None else 2**attempt))
        return None, reason

    def _wait_for(self, host: str) -> Optional[str]:
        """Sleep through a short cooldown; return a reason when the host is blocked."""
        with self._lock:
            until = self._blocked_until.get(host, 0.0)
            next_at = self._next_request_at.get(host, 0.0)
        now = self.now()
        if until > now:
            return f"{host} asked us to wait {duration(until - now)}"
        if next_at - now > MAX_RETRY_AFTER:
            return f"{host} asked us to wait {duration(next_at - now)}"
        if next_at > now:
            self.sleep(next_at - now)
        return None

    def _pace(self, host: str) -> None:
        interval = HOST_MIN_INTERVAL.get(host)
        if not interval:
            return
        with self._lock:
            now = self.now()
            start = max(now, self._next_request_at.get(host, 0.0))
            self._next_request_at[host] = start + interval
        if start > now:
            self.sleep(start - now)

    def _defer(self, host: str, until: float) -> None:
        with self._lock:
            self._next_request_at[host] = max(self._next_request_at.get(host, 0.0), until)

    def _block(self, host: str, until: float) -> None:
        with self._lock:
            self._blocked_until[host] = max(self._blocked_until.get(host, 0.0), until)
            blocks = dict(self._blocked_until)
        # Remember across runs: querying a locked-out host again only extends the lockout.
        self.cache.write("rdap-blocks.json", blocks)
        self._warn_once(
            f"block:{host}",
            f"{host} rate-limited this IP for {duration(until - self.now())}; using WHOIS instead",
        )

    # -- WHOIS --------------------------------------------------------------------------

    def whois_server_for(self, tld: str) -> Optional[str]:
        if tld in WHOIS_SERVERS:
            return WHOIS_SERVERS[tld]
        with self._lock:
            if self._whois_servers is None:
                self._whois_servers = self.cache.read("whois-servers.json") or {}
            entry = self._whois_servers.get(tld)
            if isinstance(entry, dict) and self.now() - stamp(entry, "fetched_at") < WHOIS_REFERRAL_TTL:
                return entry.get("server") or None
        try:
            reply = self.whois(IANA_WHOIS, tld)
        except OSError:
            return None
        match = re.search(r"^(?:whois|refer):\s*(\S+)", reply, re.IGNORECASE | re.MULTILINE)
        server = match.group(1).lower() if match else ""
        with self._lock:
            self._whois_servers[tld] = {"server": server, "fetched_at": self.now()}
        self.cache.update(
            "whois-servers.json",
            {tld: {"server": server, "fetched_at": self.now()}},
            WHOIS_REFERRAL_TTL,
            "fetched_at",
        )
        return server or None

    def _whois(self, domain: str, reason: str) -> Result:
        server = self.whois_server_for(domain.rsplit(".", 1)[-1])
        if not server:
            return Result(domain, UNKNOWN, None, f"{reason}; no WHOIS server")
        text = None
        with self._semaphore(f"whois:{server}", WHOIS_CONCURRENCY):
            for attempt in range(2):
                try:
                    text = self.whois(server, domain)
                    break
                except OSError:
                    self.sleep(1 + attempt)
        if text is None:
            return Result(domain, UNKNOWN, None, f"{reason}; WHOIS {server} unreachable")
        status, detail = parse_whois(text, domain)
        if status == UNKNOWN:
            return Result(domain, UNKNOWN, None, f"{reason}; {detail}")
        return Result(domain, status, "whois", detail)

    # -- helpers ------------------------------------------------------------------------

    def _semaphore(self, key: str, limit: int) -> threading.BoundedSemaphore:
        with self._lock:
            if key not in self._semaphores:
                self._semaphores[key] = threading.BoundedSemaphore(limit)
            return self._semaphores[key]

    def _warn_once(self, key: str, message: str) -> None:
        with self._lock:
            if key in self._warned:
                return
            self._warned.add(key)
        self.warn(message)

    def _note_network_error(self, error: BaseException) -> bool:
        """Warn once about certificate failures; True when the error is one."""
        reason = getattr(error, "reason", error)
        if not isinstance(reason, ssl.SSLCertVerificationError):
            return False
        self._warn_once(
            "tls",
            "TLS certificate verification failed; HTTPS checks fall back to WHOIS "
            "(python.org macOS builds: run 'Install Certificates.command')",
        )
        return True


ICONS = {AVAILABLE: "✅", TAKEN: "❌", UNKNOWN: "❓"}


def format_line(result: Result) -> str:
    if result.status == AVAILABLE:
        return f"  {ICONS[AVAILABLE]} {result.domain:<28} AVAILABLE"
    if result.status == TAKEN:
        return f"  {ICONS[TAKEN]} {result.domain:<28} taken"
    return f"  {ICONS[UNKNOWN]} {result.domain:<28} unknown ({result.detail or 'no answer'}; verify manually)"


def format_text(results: List[Result]) -> str:
    return "".join(format_line(result) + "\n" for result in results)


def format_json(results: List[Result]) -> str:
    return json.dumps([result.to_json() for result in results], ensure_ascii=False, separators=(",", ":"))


def summary(results: List[Result], seconds: float) -> str:
    counts: Dict[str, int] = {}
    for result in results:
        key = "cache" if result.cached else (result.source or "unknown")
        counts[key] = counts.get(key, 0) + 1
    parts = ", ".join(f"{key} {counts[key]}" for key in sorted(counts))
    return f"checked {len(results)} domain(s) in {seconds:.1f}s ({parts})"


EPILOG = """\
examples:
  check-domains.sh acme.com acme.ai foo.io          explicit domains
  check-domains.sh --tlds com,ai,io acme foo bar     names x TLDs (bare names default to .com)
  check-domains.sh --json --tlds com,ai acme foo     JSON with status and source (rdap/whois/doh)

Output: ✅ AVAILABLE / ❌ taken / ❓ unknown. UNKNOWN means "could not tell", never "available".
AVAILABLE means unregistered at the registry; premium and reserved prices are not shown.
Cache: ${XDG_CACHE_HOME:-~/.cache}/domain-search (results 6 h, IANA bootstrap 1 day).
"""


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check-domains.sh",
        description="Check domain registration at the registries (RDAP, WHOIS fallback).",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("names", nargs="*", help="domains (acme.com) or bare names (acme)")
    parser.add_argument("--json", action="store_true", help="print a JSON array")
    parser.add_argument("--tlds", default="", help="comma-separated TLDs for bare names (default: com)")
    parser.add_argument("--no-cache", action="store_true", help="ignore cached results (still saves new ones)")
    parser.add_argument("--no-doh", action="store_true", help="skip the DNS-over-HTTPS pre-check")
    return parser.parse_intermixed_args(argv)


def main(
    argv: Optional[List[str]] = None,
    make_checker: Callable[..., Checker] = Checker,
    stdout=None,
    stderr=None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = parse_args(argv)
    domains = build_domain_list(args.names, args.tlds)
    if not domains:
        print("error: no names/domains given. See --help.", file=stderr)
        return 1
    if stdout is sys.stdout and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8")
    checker = make_checker(use_cache=not args.no_cache, use_doh=not args.no_doh)
    started = time.monotonic()
    results = checker.check_many(domains)
    elapsed = time.monotonic() - started
    stdout.write(format_json(results) + "\n" if args.json else format_text(results))
    stdout.flush()
    print(summary(results, elapsed), file=stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
