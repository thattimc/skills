# Estimate input and calculator

Use this reference only after the scope checkpoint is approved or when resolving calculator
validation. The calculator uses Python's decimal arithmetic and has no third-party dependency.

## Run

```bash
python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json --output-dir ./ballpark-output
python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json --output-dir ./ballpark-output \
  --approved-by "Reviewer name"
python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json --output-dir ./ballpark-output \
  --rate-card-snapshot ./private/rate-card-snapshot.json
```

Default output is a draft. `--approved-by` records explicit human approval and removes the
draft banner. Both modes write:

- `calculation.json`: machine-readable exact totals; internal/confidential.
- `internal-estimate.md`: rates, role math, sources, and full trace; internal/confidential.
- `client-ballpark.md`: rounded ranges and scope; no day rates or role-level cost math.

The command prints only status and file paths, so a client-visible terminal does not expose
rates. Review internal files privately.

## Required JSON shape

See [`../examples/sample-estimate.json`](../examples/sample-estimate.json) for a complete
synthetic input.

### `project`

| Field | Rule |
|---|---|
| `client`, `name` | Non-empty text |
| `estimate_date` | ISO `YYYY-MM-DD` |
| `currency` | Non-empty currency label, normally ISO code |
| `validity_days` | Positive whole number |

### `discovery`

| Field | Rule |
|---|---|
| `outcome` | Non-empty text |
| `scope_in` | Non-empty list of text |
| `scope_out` | List of explicit exclusions |
| `assumptions` | List; every inferred estimate input appears here |
| `unresolved` | Non-blocking open items |
| `blocking_unknowns` | Must be empty before calculation |
| `confidence.level` | `low`, `medium`, or `high` |
| `confidence.rationale` | Plain-language basis for that level |

### `rate_card`

Use one rate-card mode. Supplying both fails closed.

#### Inline fallback

`source` and `effective_date` identify the approved rate card. `roles` maps stable role keys
to positive day rates. Only `internal-estimate.md` shows them. Keep this mode for controlled
offline use and backward compatibility.

```json
{
  "source": "FY2026 approved sell-rate card",
  "effective_date": "2026-01-01",
  "roles": { "ba": 6000, "sa": 8000, "developer": 5500 }
}
```

#### Notion rate-card snapshot

Omit `rate_card`, add `rate_mapping`, and pass `--rate-card-snapshot`. Map each role used by
`services` to the exact composite key printed by `load_notion_rate_card.py` in its private JSON:

```json
{
  "rate_mapping": {
    "developer": "EXAMPLE-SERVICES-USD|2026.1|Services|Level 2|Engineering|Remote|USD",
    "pm": "EXAMPLE-SERVICES-USD|2026.1|Services|Level 4|Delivery Management|Remote|USD"
  }
}
```

The calculator verifies the snapshot checksum, approval status, effective dates, currency,
unique rate keys, positive rates, and every referenced mapping. It records rates and Notion
provenance only in private artifacts. Read [notion-rate-card.md](notion-rate-card.md) for setup and
loader commands.

### `services`

At least one service line is required. Each line has `work_item`, `role`, `low_days`,
`high_days`, and `basis`. The role must exist in the rate card; `high_days >= low_days`.

### `one_time`

Optional project costs such as hardware, licenses, or cloud setup. Omit the field or use an
empty list when none apply. Each line has `category`,
`label`, `low`, `high`, `contingency_eligible`, `source`, and ISO `as_of`. Rates and catalog
figures without a dated source fail validation.

### `recurring`

Optional cloud, license, support, or BAU costs. Omit the field or use an empty list when none
apply. Each line has `category`, `label`, `period`
(`monthly`, `annual`, or another explicit period), `low`, `high`, `source`, and ISO `as_of`.
Totals remain grouped by period; the calculator never mixes monthly and annual values.

### `contingency` and `commercial`

`contingency.low_pct` applies to low eligible cost and `high_pct` to high eligible cost.
Services are eligible; one-time lines opt in with `contingency_eligible`. Recurring lines are
outside contingency. `commercial.discount_pct` is applied after contingency, then
`tax_pct` is applied to the discounted initial investment. Recurring lines are supplied
already adjusted. `commercial` may be omitted; discount and tax then default to zero.

### `timeline`

Requires `low_weeks`, `high_weeks`, `basis`, and `milestones`. Timeline is an explicit
planning range; the calculator displays it but does not derive schedule from raw man-days.

### `presentation`

`effort_round_to` and `money_round_to` set client-facing rounding quanta. Exact amounts stay
in internal output and `calculation.json`.

## Formula

For each bound independently:

1. `service cost = Σ(role day rate × service days)`
2. `base initial = service cost + Σ(one-time cost)`
3. `contingency = (service cost + eligible one-time cost) × contingency %`
4. `gross = base initial + contingency`
5. `discounted = gross × (1 − discount %)`
6. `initial investment = discounted × (1 + tax %)`
7. Recurring totals are summed by their exact period and kept separate.

Every input range must have `high >= low`; negative figures and missing sources fail.
