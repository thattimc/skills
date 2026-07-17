---
name: presales-with-docs
description: >
  Run live presales discovery one question at a time, preserve a decision ledger, and
  produce an auditable ballpark/ROM for services, infrastructure, timeline, and BAU.
  Use when a presales operator is scoping a client project, qualifying requirements,
  estimating man-days, or preparing an indicative cost for client discussion.
---

# Presales with Docs

Guide a client conversation from desired outcome to a reviewable, non-binding ballpark.
The presales operator owns the meeting and every commercial approval.

## Start

1. Read [references/live-discovery.md](references/live-discovery.md). Ingest supplied
   requirements before asking anything. Ask the operator whether the conversation is
   client-visible or private, then create `<client-slug>-presales/discovery-record.md`
   from the reference template. State that this is discovery for an indicative ROM.
   **Complete when:** visibility is known and the record contains every fact already
   available from supplied material.

2. Ask: **“What outcome would make this project successful for you?”** Ask exactly one
   client-facing question, then wait. Honor operator controls: `park`, `skip`, `revisit`,
   `summarize`, `private checkpoint`, and `end discovery`.
   **Complete when:** the client has answered or the item is explicitly parked.

## Discovery loop

3. Update `discovery-record.md` after every answer: confirmed facts, client decisions,
   assumptions, exclusions, unresolved items, and conflicts remain distinct. Choose the
   next question by this order: conflict, readiness blocker, largest estimate swing,
   then output detail. Ask one question and wait. Offer a recommended answer only when
   the operator or client needs options; label it as a recommendation.
   **Complete when:** every readiness-gate field is confirmed, assumed with a stated
   basis, or recorded as non-blocking, and no blocking conflict remains.

4. Present one scope checkpoint: outcomes, scope in/out, work breakdown, assumptions,
   unresolved items, and proposed effort ranges. Ask the operator for one confirmation.
   Revise through the discovery loop when they reject it.
   **Complete when:** the operator explicitly approves the estimate basis.

## Ballpark

5. Read [references/estimate-input.md](references/estimate-input.md). Build the JSON input
   from the approved basis and controlled sources. Use approved day rates and dated vendor
   or cloud figures. Keep private rates and role math out of client-visible conversation.
   **Complete when:** every service line has role, day range, rate-card match, and basis;
   every external cost has source and as-of date; timeline has a stated basis.

6. Run the deterministic calculator in draft mode:

   ```bash
   python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json \
     --output-dir ./ballpark-output
   ```

   Validation errors return to the discovery loop. Review `internal-estimate.md` privately;
   the client artifact contains totals but no day rates.
   **Complete when:** every total traces to an input line and the operator accepts the
   range, confidence, assumptions, exclusions, contingency, and validity period.

7. Ask one approval question: **“Do you approve this ROM for client discussion?”** After
   explicit approval, record the human reviewer:

   ```bash
   python3 "<this skill dir>/scripts/calculate_ballpark.py" estimate.json \
     --output-dir ./ballpark-output --approved-by "Reviewer name"
   ```

   Present `client-ballpark.md`. If approval is withheld, present the discovery summary
   and missing decisions instead.
   **Complete when:** approved output names its reviewer, or the session ends without a
   commercially usable estimate.

## Hard gates

- A ballpark is a range. The client artifact states ROM status, confidence, basis,
  assumptions, exclusions, contingency, validity, unresolved items, and non-binding use.
- Critical unknowns stay in `blocking_unknowns`; the calculator refuses an estimate.
- Services, one-time infrastructure, and recurring cloud/BAU remain separate totals.
- Keep private rates, margins, discounts, and role-level math in internal artifacts.
- The calculator performs arithmetic; the model performs discovery and decomposition.

For a complete synthetic run, read [examples/sample-session.md](examples/sample-session.md)
and use [examples/sample-estimate.json](examples/sample-estimate.json).
