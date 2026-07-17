#!/usr/bin/env python3
"""Validate a presales estimate and emit internal and client-facing ROM artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


class EstimateError(ValueError):
    """Raised when estimate input cannot support an auditable calculation."""


def _mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EstimateError(f"{path} must be an object")
    return value


def _items(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise EstimateError(f"{path} must be a list")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EstimateError(f"{path} must be non-empty text")
    return value.strip()


def _text_list(value: Any, path: str, *, nonempty: bool = False) -> list[str]:
    rows = _items(value, path)
    if nonempty and not rows:
        raise EstimateError(f"{path} must contain at least one item")
    return [_text(item, f"{path}[{index}]") for index, item in enumerate(rows)]


def _decimal(value: Any, path: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool):
        raise EstimateError(f"{path} must be a number")
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EstimateError(f"{path} must be a number") from exc
    if not number.is_finite():
        raise EstimateError(f"{path} must be finite")
    if number < 0 or (positive and number <= 0):
        qualifier = "positive" if positive else "zero or greater"
        raise EstimateError(f"{path} must be {qualifier}")
    return number


def _whole_positive(value: Any, path: str) -> int:
    number = _decimal(value, path, positive=True)
    if number != number.to_integral_value():
        raise EstimateError(f"{path} must be a whole number")
    return int(number)


def _iso_date(value: Any, path: str) -> date:
    raw = _text(value, path)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise EstimateError(f"{path} must use YYYY-MM-DD") from exc


def _range(row: dict[str, Any], low_key: str, high_key: str, path: str) -> tuple[Decimal, Decimal]:
    low = _decimal(row.get(low_key), f"{path}.{low_key}")
    high = _decimal(row.get(high_key), f"{path}.{high_key}")
    if high < low:
        raise EstimateError(f"{path}.{high_key} must be greater than or equal to {low_key}")
    return low, high


def _percent(value: Any, path: str) -> Decimal:
    number = _decimal(value, path)
    if number > 100:
        raise EstimateError(f"{path} must be between 0 and 100")
    return number


def _round_to(value: Decimal, quantum: Decimal) -> Decimal:
    return (value / quantum).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * quantum


def _fmt(value: Decimal) -> str:
    rendered = f"{value:,.2f}"
    return rendered.rstrip("0").rstrip(".")


def _money(currency: str, value: Decimal) -> str:
    return f"{currency} {_fmt(value)}"


def _money_range(currency: str, low: Decimal, high: Decimal) -> str:
    return f"{_money(currency, low)}–{_money(currency, high)}"


def _range_text(low: Decimal, high: Decimal, unit: str) -> str:
    return f"{_fmt(low)}–{_fmt(high)} {unit}"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _bullets(values: list[str], empty: str = "None recorded.") -> str:
    return "\n".join(f"- {value}" for value in values) if values else empty


def load_input(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal, parse_int=Decimal)
    except OSError as exc:
        raise EstimateError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EstimateError(f"invalid JSON in {path}: {exc}") from exc


def calculate(data: dict[str, Any], approved_by: str | None = None) -> dict[str, Any]:
    root = _mapping(data, "input")

    project_raw = _mapping(root.get("project"), "project")
    estimate_date = _iso_date(project_raw.get("estimate_date"), "project.estimate_date")
    validity_days = _whole_positive(project_raw.get("validity_days"), "project.validity_days")
    project = {
        "client": _text(project_raw.get("client"), "project.client"),
        "name": _text(project_raw.get("name"), "project.name"),
        "estimate_date": estimate_date.isoformat(),
        "currency": _text(project_raw.get("currency"), "project.currency"),
        "validity_days": validity_days,
        "valid_until": (estimate_date + timedelta(days=validity_days)).isoformat(),
    }

    discovery_raw = _mapping(root.get("discovery"), "discovery")
    confidence_raw = _mapping(discovery_raw.get("confidence"), "discovery.confidence")
    confidence_level = _text(confidence_raw.get("level"), "discovery.confidence.level").lower()
    if confidence_level not in {"low", "medium", "high"}:
        raise EstimateError("discovery.confidence.level must be low, medium, or high")
    blockers = _text_list(discovery_raw.get("blocking_unknowns"), "discovery.blocking_unknowns")
    if blockers:
        raise EstimateError("ballpark blocked by: " + "; ".join(blockers))
    discovery = {
        "outcome": _text(discovery_raw.get("outcome"), "discovery.outcome"),
        "scope_in": _text_list(discovery_raw.get("scope_in"), "discovery.scope_in", nonempty=True),
        "scope_out": _text_list(discovery_raw.get("scope_out"), "discovery.scope_out"),
        "assumptions": _text_list(discovery_raw.get("assumptions"), "discovery.assumptions"),
        "unresolved": _text_list(discovery_raw.get("unresolved"), "discovery.unresolved"),
        "blocking_unknowns": blockers,
        "confidence": {
            "level": confidence_level,
            "rationale": _text(confidence_raw.get("rationale"), "discovery.confidence.rationale"),
        },
    }

    rate_raw = _mapping(root.get("rate_card"), "rate_card")
    roles_raw = _mapping(rate_raw.get("roles"), "rate_card.roles")
    if not roles_raw:
        raise EstimateError("rate_card.roles must contain at least one role")
    roles: dict[str, Decimal] = {}
    for role, raw_rate in roles_raw.items():
        role_key = _text(role, "rate_card.roles key")
        roles[role_key] = _decimal(raw_rate, f"rate_card.roles.{role_key}", positive=True)
    rate_effective_date = _iso_date(rate_raw.get("effective_date"), "rate_card.effective_date")
    if rate_effective_date > estimate_date:
        raise EstimateError("rate_card.effective_date cannot be after project.estimate_date")
    rate_card = {
        "source": _text(rate_raw.get("source"), "rate_card.source"),
        "effective_date": rate_effective_date.isoformat(),
        "roles": roles,
    }

    service_rows = _items(root.get("services"), "services")
    if not service_rows:
        raise EstimateError("services must contain at least one work item")
    services: list[dict[str, Any]] = []
    effort_low = Decimal("0")
    effort_high = Decimal("0")
    service_cost_low = Decimal("0")
    service_cost_high = Decimal("0")
    for index, raw in enumerate(service_rows):
        path = f"services[{index}]"
        row = _mapping(raw, path)
        role = _text(row.get("role"), f"{path}.role")
        if role not in roles:
            raise EstimateError(f"{path}.role '{role}' is absent from rate_card.roles")
        low_days, high_days = _range(row, "low_days", "high_days", path)
        low_cost = low_days * roles[role]
        high_cost = high_days * roles[role]
        services.append({
            "work_item": _text(row.get("work_item"), f"{path}.work_item"),
            "role": role,
            "low_days": low_days,
            "high_days": high_days,
            "basis": _text(row.get("basis"), f"{path}.basis"),
            "day_rate": roles[role],
            "low_cost": low_cost,
            "high_cost": high_cost,
        })
        effort_low += low_days
        effort_high += high_days
        service_cost_low += low_cost
        service_cost_high += high_cost

    one_time: list[dict[str, Any]] = []
    one_time_low = Decimal("0")
    one_time_high = Decimal("0")
    eligible_one_time_low = Decimal("0")
    eligible_one_time_high = Decimal("0")
    for index, raw in enumerate(_items(root.get("one_time", []), "one_time")):
        path = f"one_time[{index}]"
        row = _mapping(raw, path)
        low, high = _range(row, "low", "high", path)
        eligible = row.get("contingency_eligible")
        if not isinstance(eligible, bool):
            raise EstimateError(f"{path}.contingency_eligible must be true or false")
        as_of = _iso_date(row.get("as_of"), f"{path}.as_of")
        if as_of > estimate_date:
            raise EstimateError(f"{path}.as_of cannot be after project.estimate_date")
        normalized = {
            "category": _text(row.get("category"), f"{path}.category"),
            "label": _text(row.get("label"), f"{path}.label"),
            "low": low,
            "high": high,
            "contingency_eligible": eligible,
            "source": _text(row.get("source"), f"{path}.source"),
            "as_of": as_of.isoformat(),
        }
        one_time.append(normalized)
        one_time_low += low
        one_time_high += high
        if eligible:
            eligible_one_time_low += low
            eligible_one_time_high += high

    recurring: list[dict[str, Any]] = []
    recurring_by_period: dict[str, dict[str, Decimal]] = {}
    for index, raw in enumerate(_items(root.get("recurring", []), "recurring")):
        path = f"recurring[{index}]"
        row = _mapping(raw, path)
        low, high = _range(row, "low", "high", path)
        period = _text(row.get("period"), f"{path}.period").lower()
        as_of = _iso_date(row.get("as_of"), f"{path}.as_of")
        if as_of > estimate_date:
            raise EstimateError(f"{path}.as_of cannot be after project.estimate_date")
        normalized = {
            "category": _text(row.get("category"), f"{path}.category"),
            "label": _text(row.get("label"), f"{path}.label"),
            "period": period,
            "low": low,
            "high": high,
            "source": _text(row.get("source"), f"{path}.source"),
            "as_of": as_of.isoformat(),
        }
        recurring.append(normalized)
        totals = recurring_by_period.setdefault(period, {"low": Decimal("0"), "high": Decimal("0")})
        totals["low"] += low
        totals["high"] += high

    contingency_raw = _mapping(root.get("contingency"), "contingency")
    contingency = {
        "low_pct": _percent(contingency_raw.get("low_pct"), "contingency.low_pct"),
        "high_pct": _percent(contingency_raw.get("high_pct"), "contingency.high_pct"),
    }
    if contingency["high_pct"] < contingency["low_pct"]:
        raise EstimateError("contingency.high_pct must be greater than or equal to low_pct")

    commercial_raw = _mapping(root.get("commercial", {}), "commercial")
    commercial = {
        "discount_pct": _percent(commercial_raw.get("discount_pct", 0), "commercial.discount_pct"),
        "tax_pct": _percent(commercial_raw.get("tax_pct", 0), "commercial.tax_pct"),
    }

    timeline_raw = _mapping(root.get("timeline"), "timeline")
    timeline_low, timeline_high = _range(timeline_raw, "low_weeks", "high_weeks", "timeline")
    timeline = {
        "low_weeks": timeline_low,
        "high_weeks": timeline_high,
        "basis": _text(timeline_raw.get("basis"), "timeline.basis"),
        "milestones": _text_list(timeline_raw.get("milestones"), "timeline.milestones", nonempty=True),
    }

    presentation_raw = _mapping(root.get("presentation"), "presentation")
    presentation = {
        "effort_round_to": _decimal(
            presentation_raw.get("effort_round_to"), "presentation.effort_round_to", positive=True
        ),
        "money_round_to": _decimal(
            presentation_raw.get("money_round_to"), "presentation.money_round_to", positive=True
        ),
    }

    base_low = service_cost_low + one_time_low
    base_high = service_cost_high + one_time_high
    eligible_low = service_cost_low + eligible_one_time_low
    eligible_high = service_cost_high + eligible_one_time_high
    contingency_cost_low = eligible_low * contingency["low_pct"] / Decimal("100")
    contingency_cost_high = eligible_high * contingency["high_pct"] / Decimal("100")
    gross_low = base_low + contingency_cost_low
    gross_high = base_high + contingency_cost_high
    discount_low = gross_low * commercial["discount_pct"] / Decimal("100")
    discount_high = gross_high * commercial["discount_pct"] / Decimal("100")
    discounted_low = gross_low - discount_low
    discounted_high = gross_high - discount_high
    tax_low = discounted_low * commercial["tax_pct"] / Decimal("100")
    tax_high = discounted_high * commercial["tax_pct"] / Decimal("100")
    project_total_low = discounted_low + tax_low
    project_total_high = discounted_high + tax_high
    commercial_low_factor = (
        (Decimal("1") - commercial["discount_pct"] / Decimal("100"))
        * (Decimal("1") + commercial["tax_pct"] / Decimal("100"))
    )
    commercial_high_factor = commercial_low_factor
    service_initial_low = (
        service_cost_low * (Decimal("1") + contingency["low_pct"] / Decimal("100"))
        * commercial_low_factor
    )
    service_initial_high = (
        service_cost_high * (Decimal("1") + contingency["high_pct"] / Decimal("100"))
        * commercial_high_factor
    )
    one_time_initial_low = (
        one_time_low + eligible_one_time_low * contingency["low_pct"] / Decimal("100")
    ) * commercial_low_factor
    one_time_initial_high = (
        one_time_high + eligible_one_time_high * contingency["high_pct"] / Decimal("100")
    ) * commercial_high_factor

    reviewer = approved_by.strip() if approved_by else None
    if approved_by is not None and not reviewer:
        raise EstimateError("--approved-by must name the human reviewer")

    totals = {
        "effort_low": effort_low,
        "effort_high": effort_high,
        "service_cost_low": service_cost_low,
        "service_cost_high": service_cost_high,
        "one_time_low": one_time_low,
        "one_time_high": one_time_high,
        "eligible_low": eligible_low,
        "eligible_high": eligible_high,
        "contingency_low": contingency_cost_low,
        "contingency_high": contingency_cost_high,
        "gross_low": gross_low,
        "gross_high": gross_high,
        "discount_low": discount_low,
        "discount_high": discount_high,
        "tax_low": tax_low,
        "tax_high": tax_high,
        "project_total_low": project_total_low,
        "project_total_high": project_total_high,
        "service_initial_low": service_initial_low,
        "service_initial_high": service_initial_high,
        "one_time_initial_low": one_time_initial_low,
        "one_time_initial_high": one_time_initial_high,
        "presented_effort_low": _round_to(effort_low, presentation["effort_round_to"]),
        "presented_effort_high": _round_to(effort_high, presentation["effort_round_to"]),
        "presented_service_low": _round_to(service_initial_low, presentation["money_round_to"]),
        "presented_service_high": _round_to(service_initial_high, presentation["money_round_to"]),
        "presented_one_time_low": _round_to(one_time_initial_low, presentation["money_round_to"]),
        "presented_one_time_high": _round_to(one_time_initial_high, presentation["money_round_to"]),
        "presented_project_low": _round_to(project_total_low, presentation["money_round_to"]),
        "presented_project_high": _round_to(project_total_high, presentation["money_round_to"]),
        "recurring_by_period": recurring_by_period,
    }

    return {
        "status": "approved" if reviewer else "draft",
        "approved_by": reviewer,
        "project": project,
        "discovery": discovery,
        "rate_card": rate_card,
        "services": services,
        "one_time": one_time,
        "recurring": recurring,
        "contingency": contingency,
        "commercial": commercial,
        "timeline": timeline,
        "presentation": presentation,
        "totals": totals,
    }


def render_internal(result: dict[str, Any]) -> str:
    project = result["project"]
    discovery = result["discovery"]
    totals = result["totals"]
    currency = project["currency"]
    approval = (
        f"APPROVED FOR CLIENT DISCUSSION BY {result['approved_by']}"
        if result["approved_by"]
        else "DRAFT — HUMAN APPROVAL REQUIRED"
    )

    service_rows = [
        "| Work item | Role | Days | Day rate | Cost | Basis |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in result["services"]:
        service_rows.append(
            "| {work} | {role} | {days} | {rate} | {cost} | {basis} |".format(
                work=_cell(row["work_item"]),
                role=_cell(row["role"]),
                days=_range_text(row["low_days"], row["high_days"], "MD"),
                rate=_money(currency, row["day_rate"]),
                cost=_money_range(currency, row["low_cost"], row["high_cost"]),
                basis=_cell(row["basis"]),
            )
        )

    one_time_rows = [
        "| Category | Item | Cost | Contingency | Source | As of |",
        "|---|---|---:|---|---|---|",
    ]
    if result["one_time"]:
        for row in result["one_time"]:
            one_time_rows.append(
                f"| {_cell(row['category'])} | {_cell(row['label'])} | "
                f"{_money_range(currency, row['low'], row['high'])} | "
                f"{'eligible' if row['contingency_eligible'] else 'excluded'} | "
                f"{_cell(row['source'])} | {row['as_of']} |"
            )
    else:
        one_time_rows.append("| — | None | — | — | — | — |")

    recurring_rows = [
        "| Category | Item | Period | Cost | Source | As of |",
        "|---|---|---|---:|---|---|",
    ]
    if result["recurring"]:
        for row in result["recurring"]:
            recurring_rows.append(
                f"| {_cell(row['category'])} | {_cell(row['label'])} | {_cell(row['period'])} | "
                f"{_money_range(currency, row['low'], row['high'])} | "
                f"{_cell(row['source'])} | {row['as_of']} |"
            )
    else:
        recurring_rows.append("| — | None | — | — | — | — |")

    recurring_summary = (
        "\n".join(
            f"- {period}: {_money_range(currency, values['low'], values['high'])}"
            for period, values in sorted(totals["recurring_by_period"].items())
        )
        or "- None estimated"
    )

    return f"""# {project['name']} — internal ballpark

**PRIVATE — INTERNAL RATE AND COST DATA**  
**Status:** {approval}  
**Client:** {project['client']}  
**Prepared:** {project['estimate_date']} · **Valid until:** {project['valid_until']}  
**Confidence:** {discovery['confidence']['level'].upper()} — {discovery['confidence']['rationale']}

## Outcome

{discovery['outcome']}

## Scope in

{_bullets(discovery['scope_in'])}

## Scope out

{_bullets(discovery['scope_out'])}

## Services

{chr(10).join(service_rows)}

Rate-card source: **{result['rate_card']['source']}**, effective {result['rate_card']['effective_date']}.

## One-time non-service costs

{chr(10).join(one_time_rows)}

## Recurring cloud, license, support, and BAU

{chr(10).join(recurring_rows)}

Recurring totals:

{recurring_summary}

## Exact calculation

| Component | Low | High |
|---|---:|---:|
| Service effort | {_fmt(totals['effort_low'])} MD | {_fmt(totals['effort_high'])} MD |
| Service cost | {_money(currency, totals['service_cost_low'])} | {_money(currency, totals['service_cost_high'])} |
| One-time cost | {_money(currency, totals['one_time_low'])} | {_money(currency, totals['one_time_high'])} |
| Contingency ({_fmt(result['contingency']['low_pct'])}%–{_fmt(result['contingency']['high_pct'])}%) | {_money(currency, totals['contingency_low'])} | {_money(currency, totals['contingency_high'])} |
| Gross initial investment | {_money(currency, totals['gross_low'])} | {_money(currency, totals['gross_high'])} |
| Discount ({_fmt(result['commercial']['discount_pct'])}%) | −{_money(currency, totals['discount_low'])} | −{_money(currency, totals['discount_high'])} |
| Tax ({_fmt(result['commercial']['tax_pct'])}%) | {_money(currency, totals['tax_low'])} | {_money(currency, totals['tax_high'])} |
| **Initial investment** | **{_money(currency, totals['project_total_low'])}** | **{_money(currency, totals['project_total_high'])}** |

Presented range after rounding: **{_money_range(currency, totals['presented_project_low'], totals['presented_project_high'])}** and **{_range_text(totals['presented_effort_low'], totals['presented_effort_high'], 'man-days')}**.

## Indicative timeline

**{_range_text(result['timeline']['low_weeks'], result['timeline']['high_weeks'], 'weeks')}** — {result['timeline']['basis']}

{_bullets(result['timeline']['milestones'])}

## Assumptions

{_bullets(discovery['assumptions'])}

## Unresolved, non-blocking items

{_bullets(discovery['unresolved'])}
"""


def render_client(result: dict[str, Any]) -> str:
    project = result["project"]
    discovery = result["discovery"]
    totals = result["totals"]
    currency = project["currency"]
    approval = (
        f"Approved for client discussion by {result['approved_by']}"
        if result["approved_by"]
        else "DRAFT — human approval required before client use"
    )
    recurring_summary = (
        "\n".join(
            f"| Recurring ({_cell(period)}) | **{_money_range(currency, values['low'], values['high'])}** |"
            for period, values in sorted(totals["recurring_by_period"].items())
        )
        or "| Recurring cloud/BAU | Not included in this ROM |"
    )

    return f"""# Ballpark estimate — {project['name']}

**Status:** {approval}  
**Prepared for:** {project['client']}  
**Prepared:** {project['estimate_date']} · **Valid until:** {project['valid_until']}

## Our understanding

{discovery['outcome']}

## Scope included

{_bullets(discovery['scope_in'])}

## Indicative ballpark

| | Range |
|---|---:|
| Professional-services effort | **{_range_text(totals['presented_effort_low'], totals['presented_effort_high'], 'man-days')}** |
| Professional services | **{_money_range(currency, totals['presented_service_low'], totals['presented_service_high'])}** |
| One-time infrastructure, hardware, and licenses | **{_money_range(currency, totals['presented_one_time_low'], totals['presented_one_time_high'])}** |
| Initial investment | **{_money_range(currency, totals['presented_project_low'], totals['presented_project_high'])}** |
{recurring_summary}
| Indicative delivery | **{_range_text(result['timeline']['low_weeks'], result['timeline']['high_weeks'], 'weeks')}** |

**Confidence:** {discovery['confidence']['level'].upper()} — {discovery['confidence']['rationale']}

Timeline basis: {result['timeline']['basis']}

Service and one-time ranges include their allocated contingency and configured commercial
and tax treatment. Recurring figures remain as supplied by their dated sources.

## Assumptions

{_bullets(discovery['assumptions'])}

## Exclusions

{_bullets(discovery['scope_out'])}

## Items to confirm during detailed discovery

{_bullets(discovery['unresolved'])}

## Estimate status

This is a rough-order-of-magnitude (ROM) range for budgetary discussion. It is based on
the scope, assumptions, sources, and confidence stated above; it is not a fixed quotation
or commitment. A detailed proposal requires confirmation of requirements, dependencies,
commercial terms, and delivery responsibilities. Figures remain valid through
{project['valid_until']}.
"""


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        output_dir / "calculation.json",
        output_dir / "internal-estimate.md",
        output_dir / "client-ballpark.md",
    ]
    paths[0].write_text(json.dumps(_json_safe(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths[1].write_text(render_internal(result), encoding="utf-8")
    paths[2].write_text(render_client(result), encoding="utf-8")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="estimate JSON input")
    parser.add_argument("--output-dir", type=Path, help="artifact directory; defaults beside input")
    parser.add_argument("--approved-by", help="human reviewer who approved client discussion")
    args = parser.parse_args(argv)

    try:
        result = calculate(load_input(args.input), args.approved_by)
        output_dir = args.output_dir or args.input.with_name(f"{args.input.stem}-output")
        paths = write_outputs(result, output_dir)
    except EstimateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    status = "approved" if result["approved_by"] else "draft"
    print(f"Wrote {status} ballpark artifacts:")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
