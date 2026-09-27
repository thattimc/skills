"""Offline tests for check_domains.py. HTTP, WHOIS, sleep and the clock are all faked."""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "check_domains.py"
WRAPPER = SKILL_DIR / "scripts" / "check-domains.sh"
SPEC = importlib.util.spec_from_file_location("check_domains", SCRIPT)
assert SPEC and SPEC.loader
cd = importlib.util.module_from_spec(SPEC)
sys.modules["check_domains"] = cd
SPEC.loader.exec_module(cd)

VERISIGN = "https://rdap.verisign.com/com/v1/"
IDENTITY = "https://rdap.identitydigital.services/rdap/"
BOOTSTRAP = {
    "services": [
        [["com", "net"], [VERISIGN]],
        [["ai"], [IDENTITY]],
        [["zz"], ["http://rdap.zz.test/", "https://rdap.zz.test/"]],
    ]
}
# rdap.org's reply for a TLD it has no server for (captured 2026-09 for google.io).
NO_SERVICE_BODY = (
    b'{"rdapConformance":["rdap_level_0"],"lang":"en","errorCode":404,'
    b'"title":"No RDAP service is available for this resource"}'
)
IDENTITY_TERMS = (
    "Terms of Use: ... Queries to the Whois services are throttled. If too many queries are "
    "received from a single IP address within a specified time, the service will begin to "
    "reject further queries. Identity Digital reserves the right to modify these terms."
)
IDENTITY_NOT_FOUND = (
    "Domain not found.\n>>> Last update of WHOIS database: 2026-09-26T23:47:34Z <<<\n\n"
    + IDENTITY_TERMS
)
IDENTITY_TAKEN = (
    "Domain Name: google.io\nRegistry Domain ID: REDACTED\n"
    "Registrar WHOIS Server: whois.markmonitor.com\nCreation Date: 2002-10-01T00:00:00Z\n"
    + IDENTITY_TERMS
)


def response(status, body=b"", headers=None):
    return cd.HttpResponse(status, {k.lower(): v for k, v in (headers or {}).items()}, body)


def record(domain):
    return response(200, json.dumps({"objectClassName": "domain", "ldhName": domain.upper()}).encode())


class FakeClock:
    def __init__(self):
        self.t = 1_800_000_000.0
        self.sleeps = []
        self.lock = threading.Lock()

    def now(self):
        with self.lock:
            return self.t

    def sleep(self, seconds):
        with self.lock:
            self.sleeps.append(seconds)
            self.t += seconds


class FakeHttp:
    """Answers by URL. A route is a response, a list of responses (consumed), or a callable."""

    def __init__(self, routes=None, doh=None):
        self.routes = dict(routes or {})
        self.routes.setdefault(cd.IANA_RDAP_BOOTSTRAP, response(200, json.dumps(BOOTSTRAP).encode()))
        self.doh = doh or {}
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, url, headers, timeout=None):
        with self.lock:
            self.calls.append(url)
        if url.startswith(cd.DOH_URL):
            name = url.split("name=", 1)[1].split("&", 1)[0]
            data = self.doh.get(name, {"Status": 3, "Answer": []})
            return response(200, json.dumps(data).encode())
        route = self.routes.get(url)
        if route is None:
            return response(404)
        if callable(route):
            return route(url)
        if isinstance(route, list):
            with self.lock:
                return route.pop(0)
        return route

    def calls_to(self, prefix):
        return [url for url in self.calls if url.startswith(prefix)]


class FakeWhois:
    def __init__(self, replies=None):
        self.replies = dict(replies or {})
        self.calls = []

    def __call__(self, server, query, timeout=None):
        self.calls.append((server, query))
        reply = self.replies.get((server, query))
        if reply is None:
            raise OSError(f"no fake reply for {server} {query}")
        return reply


class CheckerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name)
        self.clock = FakeClock()
        self.warnings = []

    def tearDown(self):
        self.tmp.cleanup()

    def checker(self, http, whois=None, **options):
        options.setdefault("use_doh", False)
        return cd.Checker(
            cache_dir=self.cache_dir,
            fetch=http,
            whois=whois or FakeWhois(),
            sleep=self.clock.sleep,
            now=self.clock.now,
            warn=self.warnings.append,
            **options,
        )


class RdapInterpretationTests(unittest.TestCase):
    def test_router_no_service_404_is_never_available(self):
        verdict, _ = cd.interpret_rdap("https://rdap.org/domain/google.io", response(404, NO_SERVICE_BODY))
        self.assertEqual(verdict, "NO_SERVICE")
        # Even an empty 404 from a router says nothing about the domain.
        verdict, _ = cd.interpret_rdap("https://rdap.org/domain/google.io", response(404))
        self.assertEqual(verdict, "NO_SERVICE")
        # The same body relayed by any other host is not an availability answer either.
        verdict, _ = cd.interpret_rdap(IDENTITY + "domain/google.io", response(404, NO_SERVICE_BODY))
        self.assertEqual(verdict, "NO_SERVICE")

    def test_registry_404_is_available(self):
        verdict, _ = cd.interpret_rdap(VERISIGN + "domain/zqxv.com", response(404))
        self.assertEqual(verdict, cd.AVAILABLE)

    def test_registry_200_with_domain_record_is_taken(self):
        verdict, _ = cd.interpret_rdap(VERISIGN + "domain/google.com", record("google.com"))
        self.assertEqual(verdict, cd.TAKEN)

    def test_200_without_rdap_record_is_not_an_answer(self):
        verdict, _ = cd.interpret_rdap(VERISIGN + "domain/x.com", response(200, b"<html>portal</html>"))
        self.assertEqual(verdict, "NO_SERVICE")

    def test_rate_limits_and_server_errors_are_retried(self):
        for status in (429, 500, 503):
            verdict, _ = cd.interpret_rdap(VERISIGN + "domain/x.com", response(status))
            self.assertEqual(verdict, "RETRY")

    def test_parse_retry_after(self):
        self.assertEqual(cd.parse_retry_after("86361", 0), 86361.0)
        self.assertIsNone(cd.parse_retry_after(None, 0))
        self.assertIsNone(cd.parse_retry_after("soon", 0))
        now = 1_800_000_000.0
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now + 120))
        self.assertAlmostEqual(cd.parse_retry_after(date, now), 120.0, delta=1)


class ResolutionTests(unittest.TestCase):
    def test_overrides_cover_tlds_missing_from_the_bootstrap(self):
        self.assertEqual(cd.rdap_base_for("google.io", {}), IDENTITY)
        self.assertEqual(cd.rdap_base_for("google.me", {}), IDENTITY)
        self.assertEqual(cd.rdap_base_for("google.sh", {}), IDENTITY)
        self.assertEqual(cd.rdap_base_for("google.co", {}), "https://rdap.registry.co/co/")

    def test_override_wins_and_bootstrap_fills_the_rest(self):
        bootstrap = cd.bootstrap_map(BOOTSTRAP)
        bootstrap["co"] = "https://elsewhere.test/"
        self.assertEqual(cd.rdap_base_for("google.co", bootstrap), "https://rdap.registry.co/co/")
        self.assertEqual(cd.rdap_base_for("google.com", bootstrap), VERISIGN)
        self.assertIsNone(cd.rdap_base_for("google.gg", bootstrap))

    def test_bootstrap_prefers_https(self):
        self.assertEqual(cd.bootstrap_map(BOOTSTRAP)["zz"], "https://rdap.zz.test/")

    def test_routers_are_never_a_base(self):
        self.assertIsNone(cd.rdap_base_for("google.io", {"io": "https://rdap.org/"}, overrides={}))

    def test_longest_suffix_wins(self):
        table = {"uk": "https://uk.test/", "co.uk": "https://co-uk.test"}
        self.assertEqual(cd.rdap_base_for("acme.co.uk", table, overrides={}), "https://co-uk.test/")


class WhoisParsingTests(unittest.TestCase):
    def assertWhois(self, text, domain, expected):
        status, _ = cd.parse_whois(text, domain)
        self.assertEqual(status, expected, text[:80])

    def test_not_found_replies_are_available(self):
        self.assertWhois(IDENTITY_NOT_FOUND, "zqxv.io", cd.AVAILABLE)
        self.assertWhois('No match for "ZQXV.COM".\n>>> Last update <<<\n', "zqxv.com", cd.AVAILABLE)
        self.assertWhois(
            "The queried object does not exist: DOMAIN NOT FOUND\n\n>>> Last update <<<",
            "zqxv.co",
            cd.AVAILABLE,
        )
        self.assertWhois("NOT FOUND\n", "zqxv.gg", cd.AVAILABLE)
        self.assertWhois("Domain: zqxv.de\nStatus: free\n", "zqxv.de", cd.AVAILABLE)
        self.assertWhois("%% NOT FOUND\n", "zqxv.fr", cd.AVAILABLE)

    def test_registered_records_are_taken(self):
        self.assertWhois(IDENTITY_TAKEN, "google.io", cd.TAKEN)
        self.assertWhois(
            "Domain:\n     google.gg\n\nDomain Status:\n     Active\n", "google.gg", cd.TAKEN
        )
        self.assertWhois("Reserved Domain Name\n", "nic.zz", cd.TAKEN)

    def test_anything_else_is_unknown(self):
        self.assertWhois("", "x.io", cd.UNKNOWN)
        self.assertWhois("Query rate limit exceeded. Try again later.\n", "x.io", cd.UNKNOWN)
        self.assertWhois("Copyright 2026. All rights reserved.\n", "x.io", cd.UNKNOWN)


class DohTests(unittest.TestCase):
    def test_ns_answer_for_the_domain_means_delegated(self):
        data = {"Status": 0, "Answer": [{"name": "google.com.", "type": 2, "data": "ns1.google.com."}]}
        self.assertTrue(cd.interpret_doh(data, "google.com"))

    def test_nxdomain_and_other_names_prove_nothing(self):
        self.assertFalse(cd.interpret_doh({"Status": 3}, "zqxv.com"))
        wildcard = {"Status": 0, "Answer": [{"name": "zqxv.zz", "type": 1, "data": "192.0.2.1"}]}
        self.assertFalse(cd.interpret_doh(wildcard, "zqxv.zz"))
        parent = {"Status": 0, "Answer": [{"name": "zz", "type": 2, "data": "a.nic.zz."}]}
        self.assertFalse(cd.interpret_doh(parent, "zqxv.zz"))


class CheckerTests(CheckerTestCase):
    def test_registry_404_is_available_via_rdap(self):
        result = self.checker(FakeHttp()).check_one("zqxv.com")
        self.assertEqual((result.status, result.source), (cd.AVAILABLE, "rdap"))

    def test_registry_200_is_taken_via_rdap(self):
        http = FakeHttp({VERISIGN + "domain/google.com": record("google.com")})
        result = self.checker(http).check_one("google.com")
        self.assertEqual((result.status, result.source), (cd.TAKEN, "rdap"))

    def test_no_service_404_falls_back_to_whois_and_never_reports_available(self):
        http = FakeHttp({"https://rdap.zz.test/domain/google.zz": response(404, NO_SERVICE_BODY)})
        whois = FakeWhois(
            {
                ("whois.iana.org", "zz"): "refer: whois.nic.zz\n",
                ("whois.nic.zz", "google.zz"): "Domain Name: google.zz\nRegistrar: X\n",
            }
        )
        result = self.checker(http, whois).check_one("google.zz")
        self.assertEqual((result.status, result.source), (cd.TAKEN, "whois"))

        whois.replies[("whois.nic.zz", "google.zz")] = "?? unexpected\n"
        result = self.checker(http, whois, use_cache=False).check_one("google.zz")
        self.assertEqual(result.status, cd.UNKNOWN)
        self.assertIsNone(result.source)

    def test_tld_without_rdap_or_whois_is_unknown(self):
        whois = FakeWhois({("whois.iana.org", "qq"): "domain: QQ\nstatus: ACTIVE\n"})
        result = self.checker(FakeHttp(), whois).check_one("acme.qq")
        self.assertEqual(result.status, cd.UNKNOWN)

    def test_long_retry_after_switches_the_host_to_whois(self):
        limited = response(429, b"error code: 1015", {"Retry-After": "86361"})
        http = FakeHttp({IDENTITY + "domain/zqxv.ai": limited, IDENTITY + "domain/google.ai": limited})
        whois = FakeWhois(
            {
                ("whois.nic.ai", "zqxv.ai"): IDENTITY_NOT_FOUND,
                ("whois.nic.ai", "google.ai"): IDENTITY_TAKEN.replace("google.io", "google.ai"),
            }
        )
        checker = self.checker(http, whois)
        first = checker.check_one("zqxv.ai")
        second = checker.check_one("google.ai")
        self.assertEqual((first.status, first.source), (cd.AVAILABLE, "whois"))
        self.assertEqual((second.status, second.source), (cd.TAKEN, "whois"))
        self.assertEqual(len(http.calls_to(IDENTITY)), 1, "a blocked host must not be queried again")
        self.assertFalse([s for s in self.clock.sleeps if s > cd.MAX_RETRY_AFTER])
        self.assertTrue(any("rate-limited" in warning for warning in self.warnings))

        # The lockout is remembered across runs.
        later = self.checker(http, whois, use_cache=False)
        self.assertEqual(later.check_one("zqxv.ai").source, "whois")
        self.assertEqual(len(http.calls_to(IDENTITY)), 1)

    def test_short_retry_after_is_honored_then_retried(self):
        http = FakeHttp(
            {
                VERISIGN + "domain/google.com": [
                    response(429, headers={"Retry-After": "2"}),
                    record("google.com"),
                ]
            }
        )
        result = self.checker(http).check_one("google.com")
        self.assertEqual((result.status, result.source), (cd.TAKEN, "rdap"))
        self.assertIn(2.0, self.clock.sleeps)

    def test_persistent_server_errors_fall_back_to_whois(self):
        http = FakeHttp({VERISIGN + "domain/zqxv.com": response(503)})
        whois = FakeWhois({("whois.verisign-grs.com", "zqxv.com"): 'No match for "ZQXV.COM".\n'})
        result = self.checker(http, whois).check_one("zqxv.com")
        self.assertEqual((result.status, result.source), (cd.AVAILABLE, "whois"))
        self.assertEqual(len(http.calls_to(VERISIGN)), cd.RDAP_ATTEMPTS)

    def test_doh_delegation_answers_taken_without_rdap(self):
        http = FakeHttp(doh={"google.com": {"Status": 0, "Answer": [{"name": "google.com", "type": 2}]}})
        result = self.checker(http, use_doh=True).check_one("google.com")
        self.assertEqual((result.status, result.source), (cd.TAKEN, "doh"))
        self.assertFalse(http.calls_to(VERISIGN))

    def test_doh_nxdomain_is_confirmed_by_rdap(self):
        http = FakeHttp({VERISIGN + "domain/parked.com": record("parked.com")})
        result = self.checker(http, use_doh=True).check_one("parked.com")
        self.assertEqual((result.status, result.source), (cd.TAKEN, "rdap"))

    def test_results_are_cached_for_six_hours(self):
        http = FakeHttp()
        self.checker(http).check_many(["zqxv.com"])
        cached = self.checker(http).check_many(["zqxv.com"])[0]
        self.assertTrue(cached.cached)
        self.assertEqual((cached.status, cached.source), (cd.AVAILABLE, "rdap"))
        self.assertEqual(len(http.calls_to(VERISIGN)), 1)

        self.assertFalse(self.checker(http, use_cache=False).check_many(["zqxv.com"])[0].cached)
        self.clock.t += cd.RESULT_TTL + 1
        self.assertFalse(self.checker(http).check_many(["zqxv.com"])[0].cached)

    def test_unknown_results_are_not_cached(self):
        whois = FakeWhois({("whois.iana.org", "qq"): "domain: QQ\n"})
        self.checker(FakeHttp(), whois).check_many(["acme.qq"])
        results = json.loads((self.cache_dir / "results.json").read_text()) if (
            self.cache_dir / "results.json"
        ).exists() else {}
        self.assertNotIn("acme.qq", results)

    def test_stale_bootstrap_is_used_when_iana_is_unreachable(self):
        (self.cache_dir / "rdap-dns.json").write_text(
            json.dumps({"fetched_at": self.clock.t - 10 * cd.BOOTSTRAP_TTL, "data": BOOTSTRAP})
        )
        http = FakeHttp({cd.IANA_RDAP_BOOTSTRAP: response(503)})
        result = self.checker(http).check_one("zqxv.com")
        self.assertEqual((result.status, result.source), (cd.AVAILABLE, "rdap"))

    def test_whois_referral_is_cached(self):
        whois = FakeWhois(
            {
                ("whois.iana.org", "zz"): "whois:        whois.nic.zz\n",
                ("whois.nic.zz", "a.zz"): "No match for a.zz\n",
            }
        )
        http = FakeHttp({"https://rdap.zz.test/domain/a.zz": response(400)})
        self.assertEqual(self.checker(http, whois).check_one("a.zz").source, "whois")
        self.checker(http, whois, use_cache=False).check_one("a.zz")
        self.assertEqual(whois.calls.count(("whois.iana.org", "zz")), 1)

    def test_batch_keeps_input_order_and_caps_parallelism_per_host(self):
        in_flight = {}
        peak = {}
        lock = threading.Lock()

        def slow(url):
            host = url.split("/")[2]
            with lock:
                in_flight[host] = in_flight.get(host, 0) + 1
                peak[host] = max(peak.get(host, 0), in_flight[host])
            time.sleep(0.02)
            with lock:
                in_flight[host] -= 1
            return response(404)

        names = [f"n{i}.com" for i in range(12)] + [f"n{i}.ai" for i in range(4)]
        routes = {VERISIGN + f"domain/{name}": slow for name in names if name.endswith(".com")}
        routes.update({IDENTITY + f"domain/{name}": slow for name in names if name.endswith(".ai")})
        results = self.checker(FakeHttp(routes)).check_many(names)
        self.assertEqual([result.domain for result in results], names)
        self.assertTrue(all(result.status == cd.AVAILABLE for result in results))
        self.assertLessEqual(peak["rdap.verisign.com"], 8)
        self.assertGreaterEqual(peak["rdap.verisign.com"], 2)
        self.assertEqual(peak["rdap.identitydigital.services"], 1)

    def test_invalid_names_are_unknown(self):
        result = self.checker(FakeHttp()).check_one("bad_name!.com")
        self.assertEqual(result.status, cd.UNKNOWN)


class CliTests(unittest.TestCase):
    def test_names_cross_tlds_in_order(self):
        self.assertEqual(
            cd.build_domain_list(["acme", "foo"], "com,.ai"),
            ["acme.com", "acme.ai", "foo.com", "foo.ai"],
        )

    def test_fqdns_are_kept_and_duplicates_dropped(self):
        self.assertEqual(
            cd.build_domain_list(["Acme.COM", "acme.com.", "acme", "foo.io"], ""),
            ["acme.com", "foo.io"],
        )
        self.assertEqual(cd.build_domain_list(["acme.io", "foo"], "com"), ["acme.io", "foo.com"])

    def test_options_can_be_mixed_with_names(self):
        args = cd.parse_args(["acme", "--json", "--tlds=com,ai", "foo", "--no-cache", "--no-doh"])
        self.assertEqual(args.names, ["acme", "foo"])
        self.assertEqual(args.tlds, "com,ai")
        self.assertTrue(args.json and args.no_cache and args.no_doh)

    def run_main(self, argv, results):
        seen = {}

        class Stub:
            def __init__(self, **options):
                seen.update(options)

            def check_many(self, domains):
                seen["domains"] = domains
                return results

        stdout, stderr = io.StringIO(), io.StringIO()
        code = cd.main(argv, make_checker=Stub, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue(), seen

    RESULTS = [
        cd.Result("acme.com", cd.AVAILABLE, "rdap", "registry RDAP 404"),
        cd.Result("acme.ai", cd.TAKEN, "whois", "registry WHOIS record exists"),
        cd.Result("acme.zz", cd.UNKNOWN, None, "no WHOIS server"),
    ]

    def test_text_output_format(self):
        code, out, err, seen = self.run_main(["--tlds", "com,ai,zz", "acme"], self.RESULTS)
        self.assertEqual(code, 0)
        self.assertEqual(seen["domains"], ["acme.com", "acme.ai", "acme.zz"])
        self.assertEqual(
            out.splitlines(),
            [
                f"  ✅ {'acme.com':<28} AVAILABLE",
                f"  ❌ {'acme.ai':<28} taken",
                f"  ❓ {'acme.zz':<28} unknown (no WHOIS server; verify manually)",
            ],
        )
        self.assertIn("checked 3 domain(s)", err)

    def test_json_output_has_status_and_source(self):
        code, out, _, _ = self.run_main(["--json", "acme.com", "acme.ai", "acme.zz"], self.RESULTS)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(
            [(item["domain"], item["status"], item["source"]) for item in data],
            [("acme.com", "AVAILABLE", "rdap"), ("acme.ai", "TAKEN", "whois"), ("acme.zz", "UNKNOWN", None)],
        )

    def test_flags_reach_the_checker(self):
        _, _, _, seen = self.run_main(["--no-cache", "--no-doh", "acme.com"], self.RESULTS[:1])
        self.assertEqual((seen["use_cache"], seen["use_doh"]), (False, False))

    def test_no_names_is_an_error(self):
        code, _, err, _ = self.run_main([], [])
        self.assertEqual(code, 1)
        self.assertIn("error: no names/domains given", err)

    def test_shell_wrapper_runs_the_python_script(self):
        help_run = subprocess.run(["bash", str(WRAPPER), "--help"], capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("usage: check-domains.sh", help_run.stdout)
        empty_run = subprocess.run(["bash", str(WRAPPER)], capture_output=True, text=True)
        self.assertEqual(empty_run.returncode, 1)
        self.assertIn("error: no names/domains given", empty_run.stderr)


if __name__ == "__main__":
    unittest.main()
