# Notion-backed rate cards

Use this reference only at a private presales checkpoint. The loader calls Notion directly;
do not paste the token, database rows, snapshot, or rate values into model context.

## Registry schema

Create one original Notion data source named `Approved Rate Card Registry`. Do not point the connection
at a linked database. Use these exact property names and types:

| Property | Notion type | Rule |
|---|---|---|
| `Name` | Title | Human label; required |
| `Rate Card ID` | Rich text | Stable approved card identifier such as `EXAMPLE-SERVICES-USD` |
| `Rate Card Version` | Select | Version label such as `2026.1` |
| `Rate Family` | Select | Business scope such as `Services` or `Support` |
| `Band or Category` | Rich text | `Level 2` or another approved code |
| `Service Stream` | Select | Stream such as `Engineering`; may be empty for category-only cards |
| `Delivery Location` | Select | Stable label such as `Remote` or `Onsite` |
| `Currency` | Select | ISO currency code |
| `Day Rate` | Number | Positive per-person day rate |
| `Effective From` | Date | First valid day |
| `Effective Until` | Date | Last valid day; may be empty for open-ended cards |
| `Status` | Status | `Draft`, `Approved`, or `Retired` |
| `Approved By` | People | At least one human approver |
| `Approval Date` | Date | Approval date |

One active row is identified by this composite key:

`card-id|version|family|band-or-category|service-stream-or--|delivery-location|currency`

Never treat a dash from a source export as zero. Omit that rate from the registry or keep
it in Draft with no positive `Day Rate`; the loader selects only Approved positive rows.
Preserve decimal precision. Resolve misspelled currencies, ambiguous locations, and unusual
category codes before approval.

## Connection

1. Create a Notion internal connection with read-content capability only.
2. Share the original registry database with that connection.
3. Store its secret outside the repository, normally in `NOTION_TOKEN`.
4. Record the data source ID, not only the parent database ID.

Notion API references:

- `https://developers.notion.com/reference/query-a-data-source`
- `https://developers.notion.com/reference/request-limits`
- `https://developers.notion.com/reference/retrieve-a-data-source`

## Load a private snapshot

Run outside any client-visible terminal:

```bash
export NOTION_TOKEN='<secret>'
python3 "<this skill dir>/scripts/load_notion_rate_card.py" \
  --data-source-id '<data-source-id>' \
  --rate-card-id 'EXAMPLE-SERVICES-USD' \
  --rate-card-version '2026.1' \
  --rate-family 'Services' \
  --currency 'USD' \
  --as-of '2026-07-18' \
  --output './private/rate-card-snapshot.json'
```

Omit `--rate-card-version` only when exactly one approved version is active. The loader:

- validates the data-source schema before reading rows;
- filters Approved rows effective on `--as-of`;
- follows pagination and retries transient network errors plus HTTP 429, 500, 502, 503,
  504, and 529 responses;
- rejects multiple active versions, duplicates/overlaps, mixed currency, invalid rates, and
  malformed properties;
- writes a new snapshot with mode `0600`, refuses to overwrite an existing path, and binds
  page IDs, last edit time, API version, retrieval time, and card contents into its checksum;
- prints no rate values or token.

Use [../examples/notion-rate-card-template.csv](../examples/notion-rate-card-template.csv) as a
synthetic import shape. After CSV import, change the Notion property types to match the table
above and complete approval fields in Notion. Never commit a live export or snapshot.

## Map rates into an estimate

Copy only composite keys—not rates—into private `estimate.json`:

```json
{
  "rate_mapping": {
    "developer": "EXAMPLE-SERVICES-USD|2026.1|Services|Level 2|Engineering|Remote|USD"
  }
}
```

Then calculate:

```bash
python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json \
  --rate-card-snapshot './private/rate-card-snapshot.json' \
  --output-dir './ballpark-output'
```

The estimate currency must match the snapshot currency. Use a separately approved conversion
process before calculation; this implementation intentionally does not invent foreign-exchange
rates or mix currencies.

## Operations and fallback

- Refresh to a new uniquely named snapshot for each estimate date or whenever an approved
  Notion row changes. Never overwrite a frozen snapshot.
- Retain the checksum with the private calculation record.
- If Notion is unavailable, use a previously frozen snapshot only while its effective period
  and approval remain valid.
- Use inline `rate_card` mode only as an explicit, reviewed fallback.
- A 404 usually means the original database was not shared with the connection or the wrong
  data source ID was used.
- A live smoke test is complete when the loader reads the shared source, writes a private
  snapshot, and the calculator generates all three artifacts without exposing rates in the
  client file.
- Assign a named commercial owner for card approval and a named presales tooling owner for
  schema/access maintenance. Record both owners outside the client artifact.
