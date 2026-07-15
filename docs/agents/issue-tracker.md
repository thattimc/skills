# Issue tracker: Linear

Issues, specifications, and implementation work for this repository live in Linear.

- Team: `thattimc`
- Project: `skills`

Use the configured Linear integration for all operations.

## Conventions

- Create issues in team `thattimc` and project `skills`.
- Read the full issue description, comments, labels, state, and relationships before acting.
- Refer to issues using their Linear identifier or URL.
- Apply triage labels using `docs/agents/triage-labels.md`.
- Use Linear’s native parent, child, and blocking relationships.
- Do not modify issues outside this team and project unless explicitly requested.

## Publishing

When a skill says “publish to the issue tracker,” create a Linear issue in team `thattimc`, project `skills`.

When a skill says “fetch the relevant issue,” read the referenced Linear issue, including comments and relationships.

## Wayfinding operations

- Map: one Linear issue labelled `wayfinder:map`.
- Child ticket: a child issue of the map, labelled with its `wayfinder:<type>`.
- Blocking: use Linear’s native blocked-by relationship.
- Frontier: open, unblocked, unassigned child issues.
- Claim: assign the issue before starting work.
- Resolve: post the answer, complete the issue, then add a linked summary to the map.
