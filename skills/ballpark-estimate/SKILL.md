---
name: ballpark-estimate
description: >
  Produce a ROM-class (±40–50%) ballpark effort + cost estimate for a custom-built
  enterprise application (web, mobile, portal, workflow, integration), for an IT
  services provider quoting a client. Captures requirements from documents plus a gap
  interview, decomposes the system into modules sized against a calibration table, and
  prices the effort with the firm's private rate card (iRate). Emits an internal
  working sheet (full math) and a client-facing estimate letter. Use when a client
  asks "how much would this system cost", when preparing a ballpark/ROM/indicative
  quote from an RFP or meeting notes, or on triggers like "ballpark estimate",
  "rough quote", "iRate", "estimate this project".
---

# Ballpark Estimate

Turn a client's raw requirements into a defensible ROM (rough-order-of-magnitude) estimate:
effort range in man-days, cost range in HKD, assumptions, and exclusions. Scope is
**custom-built applications only** — web apps, portals, mobile apps, workflow systems,
API/integration layers. Do not use it for packaged ERP/CRM implementations (SAP, Dynamics,
Salesforce configuration); tell the user that is out of scope if asked.

## Prerequisite: the private iRate file

All rates live **outside** this skill in `~/.claude/irate.yaml` (role-based HKD day rates,
plus optional calibration overrides). Read it first, before any analysis.

- **File missing or unreadable** → stop. Print the setup template from
  [references/irate-schema.md](references/irate-schema.md) and ask the user to fill it in.
  Never invent rates, and never ask the user to paste rates into the conversation of a
  shared/public machine transcript if they'd rather edit the file directly.
- **File present** → load rates and merge any `calibration_overrides` on top of the
  defaults in [references/calibration.md](references/calibration.md). Overrides always win.

Never copy rate figures from `irate.yaml` into any file inside this repo or skill —
they appear only in the generated estimate documents.

## Workflow

1. **Ingest what exists.** Ask the user for anything the client provided — RFP, tender
   doc, email thread, meeting notes, sketches. Read it all and extract requirements
   against the checklist in [references/checklist.md](references/checklist.md).

2. **Gap interview.** Compare extracted facts to the checklist. Ask **only about the
   gaps**, batched into one or two rounds of concise questions (use AskUserQuestion where
   options are enumerable). Unresolved gaps don't block the estimate — convert each one
   into an explicit assumption instead, and pick the mid-conservative reading.

3. **Decompose and size.** Break the system into modules. For each module assign a
   complexity tier (S/M/L/XL) per the definitions in
   [references/calibration.md](references/calibration.md), and list cross-cutting items
   (auth, integrations, data migration, reporting, notifications) separately.
   **Present the decomposition table to the user for confirmation before doing any math**
   — module list, tier, one-line rationale each. Adjust per feedback.

4. **Compute.** Follow the math procedure in
   [references/calibration.md](references/calibration.md): sum module tier ranges → add
   cross-cutting adders → apply project-level multipliers → add overhead percentages
   (design, QA, PM, UAT/deployment) → split effort across roles via the role-mix table →
   multiply by iRate day rates → round per the presentation rules. Show every step in the
   internal sheet; do the arithmetic carefully and double-check the totals.

5. **Emit two documents** using the templates in
   [references/templates.md](references/templates.md), written to the current working
   directory (or a directory the user names):
   - `<client-slug>-estimate-internal.md` — full decomposition, tier maths, role mix,
     rate table, sensitivity notes. For the firm's eyes only.
   - `<client-slug>-estimate-letter.md` — client-facing: headline effort + cost range,
     module summary (no internal rate math), assumptions, exclusions, validity period
     (default 30 days), and the ROM disclaimer. English.

6. **Sanity pass.** Before finishing, re-read the letter as a skeptical client: is the
   range wide enough for the unknowns logged as assumptions? Does every exclusion that
   could bite (data migration, third-party licences, hosting fees, content entry) appear
   explicitly? State the estimate class plainly: ±40–50%, not a fixed quote.

## Style rules

- Ranges everywhere — never a single point number in client-facing text.
- Every unknown becomes a written assumption; every "not included" becomes an exclusion.
- Timeline, if requested, is derived loosely from effort (see calibration reference) and
  labelled indicative.
- Currency is HKD unless `irate.yaml` says otherwise.
