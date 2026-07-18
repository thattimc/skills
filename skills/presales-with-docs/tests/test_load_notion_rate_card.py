from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "load_notion_rate_card.py"


def notion_property(kind, value):
    return {"id": kind, "type": kind, kind: value}


def rich_text(value):
    return [{"type": "text", "plain_text": value, "text": {"content": value}}]


def schema_response():
    kinds = {
        "Name": "title",
        "Rate Card ID": "rich_text",
        "Rate Card Version": "select",
        "Rate Family": "select",
        "Band or Category": "rich_text",
        "Service Stream": "select",
        "Delivery Location": "select",
        "Currency": "select",
        "Day Rate": "number",
        "Effective From": "date",
        "Effective Until": "date",
        "Status": "status",
        "Approved By": "people",
        "Approval Date": "date",
    }
    return {
        "object": "data_source",
        "id": "source-123",
        "properties": {
            name: {"id": f"p-{index}", "name": name, "type": kind, kind: {}}
            for index, (name, kind) in enumerate(kinds.items())
        },
    }


def rate_page(
    page_id="page-1",
    *,
    day_rate=2790,
    card_id="EXAMPLE-SERVICES-USD",
    version="2026.1",
    family="Services",
    band="Level 3",
    stream="Engineering",
    location="Remote",
    currency="USD",
    status="Approved",
    effective_from="2026-04-01",
    effective_until="2027-03-31",
    approval_date="2026-03-28",
):
    return {
        "object": "page",
        "id": page_id,
        "last_edited_time": "2026-07-17T10:00:00.000Z",
        "properties": {
            "Name": notion_property("title", rich_text("Level 3 Engineering Remote")),
            "Rate Card ID": notion_property("rich_text", rich_text(card_id)),
            "Rate Card Version": notion_property("select", {"name": version}),
            "Rate Family": notion_property("select", {"name": family}),
            "Band or Category": notion_property("rich_text", rich_text(band)),
            "Service Stream": notion_property("select", {"name": stream} if stream else None),
            "Delivery Location": notion_property("select", {"name": location}),
            "Currency": notion_property("select", {"name": currency}),
            "Day Rate": notion_property("number", day_rate),
            "Effective From": notion_property(
                "date", {"start": effective_from, "end": None, "time_zone": None}
            ),
            "Effective Until": notion_property(
                "date",
                (
                    {"start": effective_until, "end": None, "time_zone": None}
                    if effective_until
                    else None
                ),
            ),
            "Status": notion_property("status", {"name": status}),
            "Approved By": notion_property(
                "people", [{"object": "user", "id": "reviewer-1", "name": "Reviewer"}]
            ),
            "Approval Date": notion_property(
                "date", {"start": approval_date, "end": None, "time_zone": None}
            ),
        },
    }


class NotionServer:
    def __init__(self, query_responses, *, schema=None):
        self.query_responses = list(query_responses)
        self.schema = schema or schema_response()
        self.requests = []

    def __enter__(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_GET(self):
                owner.requests.append(("GET", self.path, None, dict(self.headers)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(owner.schema).encode())

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                owner.requests.append(("POST", self.path, body, dict(self.headers)))
                status, headers, payload = owner.query_responses.pop(0)
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    @property
    def api_base(self):
        host, port = self.server.server_address
        return f"http://{host}:{port}/v1"


class LoadNotionRateCardCliTests(unittest.TestCase):
    def run_loader(self, server, output, *extra, version="2026.1"):
        env = os.environ.copy()
        env["TEST_NOTION_TOKEN"] = "secret-token-must-not-leak"
        arguments = [
            sys.executable,
            str(SCRIPT),
            "--data-source-id",
            "source-123",
            "--rate-card-id",
            "EXAMPLE-SERVICES-USD",
            "--rate-family",
            "Services",
            "--currency",
            "USD",
            "--as-of",
            "2026-07-18",
            "--output",
            str(output),
            "--token-env",
            "TEST_NOTION_TOKEN",
            "--api-base",
            server.api_base,
        ]
        if version is not None:
            arguments.extend(["--rate-card-version", version])
        arguments.extend(extra)
        return subprocess.run(
            arguments,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_writes_validated_private_snapshot(self):
        response = {
            "object": "list",
            "results": [rate_page()],
            "has_more": False,
            "next_cursor": None,
            "type": "page_or_data_source",
            "page_or_data_source": {},
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "rate-card-snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["schema_version"], "presales-rate-card-snapshot/v1")
            self.assertEqual(snapshot["rate_card"]["card_id"], "EXAMPLE-SERVICES-USD")
            self.assertEqual(snapshot["rate_card"]["version"], "2026.1")
            self.assertEqual(snapshot["rate_card"]["currency"], "USD")
            self.assertEqual(
                snapshot["rate_card"]["rates"],
                [
                    {
                        "rate_key": "EXAMPLE-SERVICES-USD|2026.1|Services|Level 3|Engineering|Remote|USD",
                        "band_or_category": "Level 3",
                        "service_stream": "Engineering",
                        "delivery_location": "Remote",
                        "day_rate": "2790",
                        "source_page_id": "page-1",
                        "last_edited_time": "2026-07-17T10:00:00.000Z",
                    }
                ],
            )
            self.assertTrue(snapshot["checksum"].startswith("sha256:"))
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("secret-token-must-not-leak", output.read_text())
            self.assertNotIn("secret-token-must-not-leak", result.stdout + result.stderr)
            self.assertEqual(server.requests[0][0], "GET")
            self.assertEqual(server.requests[1][0], "POST")
            query_filter = server.requests[1][2]["filter"]["and"]
            self.assertIn(
                {"property": "Status", "status": {"equals": "Approved"}}, query_filter
            )
            self.assertIn(
                {
                    "property": "Rate Card ID",
                    "rich_text": {"equals": "EXAMPLE-SERVICES-USD"},
                },
                query_filter,
            )

    def test_follows_notion_pagination(self):
        first = {
            "object": "list",
            "results": [rate_page()],
            "has_more": True,
            "next_cursor": "cursor-2",
            "type": "page_or_data_source",
            "page_or_data_source": {},
        }
        second = {
            "object": "list",
            "results": [rate_page("page-2", stream="Data", day_rate=2800)],
            "has_more": False,
            "next_cursor": None,
            "type": "page_or_data_source",
            "page_or_data_source": {},
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, first), (200, {}, second)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(snapshot["rate_card"]["rates"]), 2)
            self.assertEqual(server.requests[2][2]["start_cursor"], "cursor-2")

    def test_retries_rate_limit_using_retry_after(self):
        success = {
            "object": "list",
            "results": [rate_page()],
            "has_more": False,
            "next_cursor": None,
            "type": "page_or_data_source",
            "page_or_data_source": {},
        }
        rate_limited = {
            "object": "error",
            "status": 429,
            "code": "rate_limited",
            "message": "slow down",
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(429, {"Retry-After": "0"}, rate_limited), (200, {}, success)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([request[0] for request in server.requests], ["GET", "POST", "POST"])

    def test_rejects_multiple_active_versions_even_when_one_is_requested(self):
        response = {
            "object": "list",
            "results": [
                rate_page(),
                rate_page("page-2", version="2027.1", stream="Data"),
            ],
            "has_more": False,
            "next_cursor": None,
            "type": "page_or_data_source",
            "page_or_data_source": {},
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("multiple approved rate-card versions are active", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_rate_approved_after_as_of(self):
        response = {
            "object": "list",
            "results": [rate_page(approval_date="2026-07-19")],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("approved after 2026-07-18", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_historical_overlap_outside_selected_date(self):
        response = {
            "object": "list",
            "results": [
                rate_page(
                    "old-1",
                    version="2024.1",
                    effective_from="2024-04-01",
                    effective_until="2025-06-30",
                ),
                rate_page(
                    "old-2",
                    version="2025.1",
                    effective_from="2025-06-01",
                    effective_until="2026-03-31",
                ),
                rate_page("current", stream="Data"),
            ],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("overlapping approved rate intervals", result.stderr)
            self.assertFalse(output.exists())

    def test_normalizes_unicode_and_whitespace_before_duplicate_check(self):
        response = {
            "object": "list",
            "results": [
                rate_page(stream="Architecture-Review"),
                rate_page("page-2", band="Level\u00a03", stream="Architecture–Review"),
            ],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("overlapping approved rate intervals", result.stderr)
            self.assertFalse(output.exists())

    def test_does_not_overwrite_existing_frozen_snapshot(self):
        response = {
            "object": "list",
            "results": [rate_page()],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"
            output.write_text("sentinel", encoding="utf-8")

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

    def test_retries_transient_gateway_error(self):
        failure = {
            "object": "error",
            "status": 502,
            "code": "bad_gateway",
            "message": "temporary gateway failure",
        }
        success = {
            "object": "list",
            "results": [rate_page()],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(502, {"Retry-After": "0"}, failure), (200, {}, success)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                [request[0] for request in server.requests], ["GET", "POST", "POST"]
            )

    def test_rejects_invalid_notion_schema(self):
        invalid_schema = schema_response()
        del invalid_schema["properties"]["Day Rate"]
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [], schema=invalid_schema
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("missing required property 'Day Rate'", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_expired_rate_card(self):
        response = {
            "object": "list",
            "results": [rate_page(effective_until="2026-06-30")],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("no approved rates are effective", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_duplicate_active_composite_key(self):
        response = {
            "object": "list",
            "results": [rate_page(), rate_page("page-2")],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("overlapping approved rate intervals", result.stderr)
            self.assertFalse(output.exists())

    def test_rejects_mixed_currency_even_if_api_filter_is_ignored(self):
        response = {
            "object": "list",
            "results": [rate_page(currency="EUR")],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("mixed currency 'EUR'", result.stderr)
            self.assertFalse(output.exists())

    def test_reports_api_error_without_writing_snapshot(self):
        response = {
            "object": "error",
            "status": 401,
            "code": "unauthorized",
            "message": "invalid token",
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(401, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("HTTP 401: invalid token", result.stderr)
            self.assertNotIn("secret-token-must-not-leak", result.stderr)
            self.assertFalse(output.exists())

    def test_reports_transient_api_failure_after_retry_limit(self):
        response = {
            "object": "error",
            "status": 503,
            "code": "service_unavailable",
            "message": "try later",
        }
        failures = [(503, {"Retry-After": "0"}, response) for _ in range(4)]
        with tempfile.TemporaryDirectory() as directory, NotionServer(failures) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("HTTP 503: try later", result.stderr)
            self.assertEqual(len(server.requests), 5)
            self.assertFalse(output.exists())

    def test_rejects_non_positive_rate(self):
        response = {
            "object": "list",
            "results": [rate_page(day_rate=0)],
            "has_more": False,
            "next_cursor": None,
        }
        with tempfile.TemporaryDirectory() as directory, NotionServer(
            [(200, {}, response)]
        ) as server:
            output = Path(directory) / "snapshot.json"

            result = self.run_loader(server, output)

            self.assertEqual(result.returncode, 2)
            self.assertIn("property 'Day Rate' must be positive", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
