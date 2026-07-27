# Live discovery

Use this reference before the first client question and throughout the discovery loop.

## Discovery ledger

Maintain one private working ledger. Each statement gets one status and a source.

| Status | Meaning |
|---|---|
| Confirmed | Client or supplied evidence states it clearly |
| Decision | Client selected among alternatives |
| Assumed | Working basis accepted for ROM; includes rationale and owner |
| Excluded | Explicitly outside the estimate boundary |
| Unknown | Open but not currently blocking |
| Conflict | Two sources disagree; resolve before dependent questions |

Use these sections:

1. Outcome and measurable success
2. Sponsor, stakeholders, users, roles, and scale
3. Current state and pain points
4. Scope in, scope out, workflows, and acceptance signals
5. Channels, platforms, accessibility, and languages
6. Integrations and third-party dependencies
7. Data, migration, retention, and reporting
8. Security, privacy, compliance, availability, and performance
9. Delivery deadline, milestones, client duties, and constraints
10. Hosting, environments, hardware, licenses, and cloud boundary
11. BAU ownership, support hours, SLA, monitoring, backup, and maintenance
12. Assumptions, exclusions, risks, dependencies, and unresolved items

Record source as `client`, `operator`, a supplied document name, or a dated pricing source.
Never silently promote an inference to a confirmed fact.

## Question selection

Ask exactly one client-facing question per turn. Select it using this queue:

1. Resolve the earliest conflict that changes downstream scope.
2. Fill a readiness blocker.
3. Reduce the unknown with the largest likely effect on effort or recurring cost.
4. Complete the next missing output field.

Prefer a plain open question when the client knows their domain. Offer 2–3 options and a
recommended default when they need help choosing. State the consequence of each option.
When an answer creates a new dependency, resolve that branch before returning to the queue.

## Operator controls

- `park`: record the item as unknown and continue if it is non-blocking.
- `skip`: mark it declined; state whether that lowers confidence or blocks the ROM.
- `revisit`: return to a named ledger item.
- `summarize`: show confirmed facts, assumptions, exclusions, conflicts, and remaining gate.
- `private checkpoint`: prepare internal decomposition without exposing rates in chat.
- `end discovery`: run the readiness gate and either proceed or list blockers.

## Readiness gate

The estimate basis needs all rows below. A row can be confirmed or an explicit assumption,
except the three hard blockers.

| Field | Minimum basis |
|---|---|
| Outcome | Intended business result and one success signal |
| Users and scale | User groups plus an order-of-magnitude usage/concurrency assumption |
| Scope boundary | Core capabilities/workflows and explicit exclusions |
| Integrations | Named systems or explicit “none”; direction and interface maturity assumed |
| Data | Migration sources/volume/quality or explicit “no migration” |
| Non-functional | Hosting, security/compliance, availability, performance tier |
| Delivery | Deadline constraint, client responsibilities, UAT, training, and handover |
| Infrastructure | Environments and hardware/cloud/license inclusion boundary |
| BAU | Support ownership, hours/SLA, monitoring, maintenance, backup, recurring licenses |
| Estimate basis | Work packages, role day ranges, approved rate card, contingency rule |
| Timeline | Staffing/dependency basis for low–high weeks |
| Commercial | Currency, estimate date, validity, tax/discount treatment |

Hard blockers:

- Intended outcome or system boundary is unknown.
- Core scope is too unclear to form work packages.
- Approved rate card is absent or a used role has no positive day rate.

An unresolved integration, migration, compliance, or hosting decision is also blocking when
no bounded assumption can contain its cost. Put all blockers in `blocking_unknowns`; the
calculator will refuse to generate artifacts.

## Scope checkpoint

Before calculation, show the operator:

- outcome and success signal;
- scope in and out;
- work packages with role, low–high man-days, and one-line basis;
- infrastructure and BAU inclusions;
- timeline range and dependency basis;
- assumptions, exclusions, unresolved items, and confidence rationale.

Ask one approval question. Approval covers the estimate basis, not commercial release.

## Discovery record template

Create this file before the first client question. Update it immediately after every answer.
Keep status and source visible so later reviewers can distinguish evidence from inference.

```markdown
# [Client] — [Project] presales discovery

Status: Live discovery
Visibility: Client-visible | Private preparation
Started: [ISO date]
Presales operator: [name]

## Outcome and success

| Status | Statement | Source |
|---|---|---|

## Users, current state, and pain points

| Status | Statement | Source |
|---|---|---|

## Scope in

| Status | Capability or workflow | Source |
|---|---|---|

## Scope out

| Status | Exclusion | Source |
|---|---|---|

## Integrations and data

| Status | Statement | Source |
|---|---|---|

## Non-functional requirements

| Status | Statement | Source |
|---|---|---|

## Delivery and timeline

| Status | Statement | Source |
|---|---|---|

## Infrastructure, cloud, and BAU

| Status | Statement | Source or as-of date |
|---|---|---|

## Assumptions and decisions

| Status | Statement | Owner | Source |
|---|---|---|---|

## Risks, dependencies, and unresolved items

| Status | Statement | Estimate impact | Owner |
|---|---|---|---|

## Readiness gate

| Field | Ready? | Basis or blocker |
|---|---|---|

## Work breakdown checkpoint

| Work item | Role | Low MD | High MD | Basis | Approved? |
|---|---|---:|---:|---|---|

## Session log

| Time | Question | Answer summary | Ledger change |
|---|---|---|---|
```
