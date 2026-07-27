#!/usr/bin/env python3
"""Load approved rate-card rows from Notion into a private frozen snapshot."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from calculate_ballpark import SNAPSHOT_VERSION, rate_card_snapshot_checksum

API_VERSION = "2026-03-11"


class RateCardError(ValueError):
    """Raised when Notion cannot provide an auditable rate-card snapshot."""


REQUIRED_PROPERTIES: dict[str, tuple[str, ...]] = {
    "Name": ("title",),
    "Rate Card ID": ("rich_text",),
    "Rate Card Version": ("select",),
    "Rate Family": ("select",),
    "Band or Category": ("rich_text",),
    "Service Stream": ("select",),
    "Delivery Location": ("select",),
    "Currency": ("select",),
    "Day Rate": ("number",),
    "Effective From": ("date",),
    "Effective Until": ("date",),
    "Status": ("status",),
    "Approved By": ("people",),
    "Approval Date": ("date",),
}


def _json_request(
    url: str,
    token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> Any:
    encoded = None if body is None else json.dumps(body).encode("utf-8")
    for attempt in range(4):
        request = Request(
            url,
            data=encoded,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": API_VERSION,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                message = payload.get("message") or payload.get("code") or str(exc.reason)
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = str(exc.reason)
            if exc.code in {429, 500, 502, 503, 504, 529} and attempt < 3:
                retry_after = exc.headers.get("Retry-After")
                try:
                    delay = (
                        max(0.0, float(retry_after))
                        if retry_after is not None
                        else 2**attempt
                    )
                except ValueError:
                    delay = 2**attempt
                time.sleep(delay)
                continue
            raise RateCardError(f"Notion API returned HTTP {exc.code}: {message}") from exc
        except URLError as exc:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            raise RateCardError(f"cannot reach Notion API: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RateCardError("Notion API returned invalid JSON") from exc
    raise RateCardError("Notion API retry limit exhausted")


def _validate_schema(payload: Any) -> None:
    if not isinstance(payload, dict) or not isinstance(payload.get("properties"), dict):
        raise RateCardError("Notion data source response has no properties schema")
    properties = payload["properties"]
    for name, allowed_types in REQUIRED_PROPERTIES.items():
        prop = properties.get(name)
        if not isinstance(prop, dict):
            raise RateCardError(f"Notion data source is missing required property '{name}'")
        actual = prop.get("type")
        if actual not in allowed_types:
            expected = " or ".join(allowed_types)
            raise RateCardError(f"Notion property '{name}' must be {expected}, got {actual!r}")


def _property(page: dict[str, Any], name: str, kind: str) -> Any:
    properties = page.get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get(name), dict):
        raise RateCardError(f"Notion page {page.get('id', '<unknown>')} is missing property '{name}'")
    prop = properties[name]
    if prop.get("type") != kind:
        raise RateCardError(
            f"Notion page {page.get('id', '<unknown>')} property '{name}' "
            f"must be {kind}, got {prop.get('type')!r}"
        )
    return prop.get(kind)


def _plain_text(page: dict[str, Any], name: str, kind: str, *, optional: bool = False) -> str:
    items = _property(page, name, kind)
    if not isinstance(items, list):
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must be text")
    value = "".join(
        str(item.get("plain_text", "")) for item in items if isinstance(item, dict)
    ).strip()
    if not value and not optional:
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must not be empty")
    return value


def _select(page: dict[str, Any], name: str, *, optional: bool = False) -> str:
    value = _property(page, name, "select")
    selected = value.get("name", "").strip() if isinstance(value, dict) else ""
    if not selected and not optional:
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must be selected")
    return selected


def _status(page: dict[str, Any], name: str) -> str:
    value = _property(page, name, "status")
    selected = value.get("name", "").strip() if isinstance(value, dict) else ""
    if not selected:
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must be selected")
    return selected


def _date(page: dict[str, Any], name: str, *, optional: bool = False) -> date | None:
    value = _property(page, name, "date")
    raw = value.get("start") if isinstance(value, dict) else None
    if raw is None and optional:
        return None
    if not isinstance(raw, str):
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must contain a date")
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise RateCardError(
            f"Notion page {page.get('id')} property '{name}' must contain an ISO date"
        ) from exc


def _positive_decimal(page: dict[str, Any], name: str) -> Decimal:
    raw = _property(page, name, "number")
    if isinstance(raw, bool):
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must be positive")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RateCardError(
            f"Notion page {page.get('id')} property '{name}' must be positive"
        ) from exc
    if not value.is_finite() or value <= 0:
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must be positive")
    return value


def _people(page: dict[str, Any], name: str) -> list[dict[str, str]]:
    values = _property(page, name, "people")
    if not isinstance(values, list) or not values:
        raise RateCardError(f"Notion page {page.get('id')} property '{name}' must name an approver")
    approvers = [
        {"id": str(person.get("id", "")), "name": str(person.get("name", ""))}
        for person in values
        if isinstance(person, dict) and person.get("id")
    ]
    if not approvers:
        raise RateCardError(
            f"Notion page {page.get('id')} property '{name}' must name an approver"
        )
    return approvers


def _decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _key_component(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.translate(
        str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-"})
    )
    return " ".join(normalized.split())


def _rate_key(
    card_id: str,
    version: str,
    family: str,
    band: str,
    stream: str,
    location: str,
    currency: str,
) -> str:
    parts = [card_id, version, family, band, stream or "-", location, currency]
    parts = [_key_component(part) for part in parts]
    if any("|" in part for part in parts):
        raise RateCardError("rate-card key components must not contain '|'")
    return "|".join(parts)


def _identity_key(
    card_id: str,
    family: str,
    band: str,
    stream: str,
    location: str,
    currency: str,
) -> str:
    parts = [card_id, family, band, stream or "-", location, currency]
    return "|".join(_key_component(part) for part in parts)


def _normalize_page(
    page: Any,
    *,
    requested_card_id: str,
    requested_family: str,
    requested_currency: str,
) -> dict[str, Any]:
    if not isinstance(page, dict) or page.get("object") != "page" or not page.get("id"):
        raise RateCardError("Notion query returned a non-page result")
    _plain_text(page, "Name", "title")
    card_id = _plain_text(page, "Rate Card ID", "rich_text")
    version = _select(page, "Rate Card Version")
    family = _select(page, "Rate Family")
    currency = _select(page, "Currency")
    status = _status(page, "Status")
    if card_id != requested_card_id:
        raise RateCardError(f"Notion returned unexpected rate-card ID '{card_id}'")
    if family != requested_family:
        raise RateCardError(f"Notion returned unexpected rate family '{family}'")
    if currency != requested_currency:
        raise RateCardError(f"Notion returned mixed currency '{currency}'")
    if status.casefold() != "approved":
        raise RateCardError(f"Notion returned non-approved rate with status '{status}'")
    effective_from = _date(page, "Effective From")
    effective_until = _date(page, "Effective Until", optional=True)
    assert effective_from is not None
    band = _plain_text(page, "Band or Category", "rich_text")
    stream = _select(page, "Service Stream", optional=True)
    location = _select(page, "Delivery Location")
    rate = _positive_decimal(page, "Day Rate")
    approval_date = _date(page, "Approval Date")
    approvers = _people(page, "Approved By")
    return {
        "version": version,
        "rate_key": _rate_key(
            card_id, version, family, band, stream, location, currency
        ),
        "identity_key": _identity_key(
            card_id, family, band, stream, location, currency
        ),
        "band_or_category": band,
        "service_stream": stream,
        "delivery_location": location,
        "day_rate": _decimal_text(rate),
        "source_page_id": str(page["id"]),
        "last_edited_time": str(page.get("last_edited_time", "")),
        "effective_from": effective_from.isoformat(),
        "effective_until": effective_until.isoformat() if effective_until else None,
        "approval_date": approval_date.isoformat() if approval_date else None,
        "approved_by": approvers,
    }


def _query_filter(card_id: str, family: str, currency: str) -> dict[str, Any]:
    filters: list[dict[str, Any]] = [
        {"property": "Rate Card ID", "rich_text": {"equals": card_id}},
        {"property": "Rate Family", "select": {"equals": family}},
        {"property": "Currency", "select": {"equals": currency}},
        {"property": "Status", "status": {"equals": "Approved"}},
    ]
    return {"and": filters}


def _validate_no_overlaps(rows: list[dict[str, Any]]) -> None:
    by_identity: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_identity.setdefault(row["identity_key"], []).append(row)
    for identity, candidates in by_identity.items():
        ordered = sorted(candidates, key=lambda row: row["effective_from"])
        previous_end: date | None = None
        for row in ordered:
            start = date.fromisoformat(row["effective_from"])
            end = (
                date.fromisoformat(row["effective_until"])
                if row["effective_until"]
                else date.max
            )
            if end < start:
                raise RateCardError(
                    f"rate interval ends before it starts for {row['source_page_id']}"
                )
            if previous_end is not None and start <= previous_end:
                raise RateCardError(
                    f"overlapping approved rate intervals found for {identity}"
                )
            previous_end = end


def load_snapshot(
    *,
    api_base: str,
    token: str,
    data_source_id: str,
    card_id: str,
    version: str | None,
    family: str,
    currency: str,
    as_of: date,
) -> dict[str, Any]:
    base = api_base.rstrip("/")
    source_url = f"{base}/data_sources/{data_source_id}"
    _validate_schema(_json_request(source_url, token))
    pages: list[Any] = []
    cursor: str | None = None
    seen_cursors: set[str] = set()
    while True:
        body: dict[str, Any] = {
            "filter": _query_filter(card_id, family, currency),
            "page_size": 100,
        }
        if cursor is not None:
            body["start_cursor"] = cursor
        response = _json_request(f"{source_url}/query", token, "POST", body)
        if not isinstance(response, dict) or not isinstance(response.get("results"), list):
            raise RateCardError("Notion query returned an invalid list response")
        pages.extend(response["results"])
        if not response.get("has_more"):
            break
        next_cursor = response.get("next_cursor")
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            raise RateCardError("Notion query returned an invalid pagination cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    rows = [
        _normalize_page(
            page,
            requested_card_id=card_id,
            requested_family=family,
            requested_currency=currency,
        )
        for page in pages
    ]
    _validate_no_overlaps(rows)
    active_rows: list[dict[str, Any]] = []
    for row in rows:
        effective_from = date.fromisoformat(row["effective_from"])
        effective_until = (
            date.fromisoformat(row["effective_until"])
            if row["effective_until"]
            else None
        )
        if effective_from <= as_of and (
            effective_until is None or effective_until >= as_of
        ):
            approval_date = date.fromisoformat(row["approval_date"])
            if approval_date > as_of:
                raise RateCardError(
                    f"rate {row['source_page_id']} was approved after {as_of.isoformat()}"
                )
            active_rows.append(row)
    rows = active_rows
    if not rows:
        raise RateCardError("no approved rates are effective for the requested selection")
    active_versions = sorted({row["version"] for row in rows})
    if len(active_versions) > 1:
        raise RateCardError(
            "multiple approved rate-card versions are active for this rate-card ID: "
            + ", ".join(active_versions)
        )
    selected_version = active_versions[0]
    if version is not None and selected_version != version:
        raise RateCardError(
            f"active rate-card version is '{selected_version}', not requested '{version}'"
        )
    rows.sort(key=lambda row: row["rate_key"])
    keys = [row["rate_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise RateCardError("duplicate or overlapping active rates found for one composite rate key")

    effective_from = max(row["effective_from"] for row in rows)
    until_values = [row["effective_until"] for row in rows if row["effective_until"]]
    effective_until = min(until_values) if until_values else None
    approval_date = max(row["approval_date"] for row in rows if row["approval_date"])
    approvers = sorted(
        {person["id"]: person for row in rows for person in row["approved_by"]}.values(),
        key=lambda person: person["id"],
    )
    rates = [
        {
            key: value
            for key, value in row.items()
            if key
            not in {
                "version",
                "identity_key",
                "effective_from",
                "effective_until",
                "approval_date",
                "approved_by",
            }
        }
        for row in rows
    ]
    source = {
        "provider": "notion",
        "data_source_id": data_source_id,
        "api_version": API_VERSION,
        "as_of": as_of.isoformat(),
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "page_ids": [row["source_page_id"] for row in rows],
        "last_edited_time": max(row["last_edited_time"] for row in rows),
    }
    rate_card = {
        "card_id": card_id,
        "version": selected_version,
        "family": family,
        "currency": currency,
        "effective_from": effective_from,
        "effective_until": effective_until,
        "status": "Approved",
        "approval_date": approval_date,
        "approved_by": approvers,
        "rates": rates,
    }
    return {
        "schema_version": SNAPSHOT_VERSION,
        "source": source,
        "rate_card": rate_card,
        "checksum": rate_card_snapshot_checksum(source, rate_card),
    }


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise RateCardError(
            f"snapshot output already exists: {path}; choose a new immutable path"
        ) from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.chmod(path, 0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--rate-card-id", required=True)
    parser.add_argument(
        "--rate-card-version",
        help="approved version to load; required when more than one version is active",
    )
    parser.add_argument("--rate-family", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--as-of", required=True, help="ISO date used for effective-rate selection")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--token-env", default="NOTION_TOKEN")
    parser.add_argument("--api-base", default="https://api.notion.com/v1")
    args = parser.parse_args(argv)

    token = os.environ.get(args.token_env, "").strip()
    if not token:
        print(f"ERROR: environment variable {args.token_env} is empty", file=sys.stderr)
        return 2
    try:
        as_of = date.fromisoformat(args.as_of)
        snapshot = load_snapshot(
            api_base=args.api_base,
            token=token,
            data_source_id=args.data_source_id,
            card_id=args.rate_card_id,
            version=args.rate_card_version,
            family=args.rate_family,
            currency=args.currency,
            as_of=as_of,
        )
        _write_private_json(args.output, snapshot)
    except (RateCardError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote private rate-card snapshot: {args.output}")
    print(f"Selected {len(snapshot['rate_card']['rates'])} approved rates; {snapshot['checksum']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
