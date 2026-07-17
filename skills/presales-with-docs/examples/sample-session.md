# Synthetic live presales session

This abbreviated session corresponds to `sample-estimate.json`. Every assistant turn has
one client-facing question. The agent updates `discovery-record.md` after every answer.

## Preparation

**Operator:** This will be client-visible. Use our synthetic rate card privately.

**Assistant:** Starting discovery for an indicative, non-binding ROM. I will ask one
question at a time and keep private commercial details in internal artifacts.

## Outcome

**Assistant:** What outcome would make this project successful for you?

**Client:** Cut manual service-request handling and let staff see request status online.

_Ledger: outcome confirmed; measurable target remains open._

## Users and scale

**Assistant:** Who will submit, approve, and operate these requests?

**Client:** About 300 employees submit them, 20 managers approve them, and 8 operations
staff administer the process.

_Ledger: three roles and order-of-magnitude user counts confirmed._

## Workflow

**Assistant:** What happens from submission until a request is completed?

**Client:** Employee submits, manager approves, then operations fulfils and closes it.

_Ledger: two-step approval and fulfilment workflow confirmed._

## Integration

**Assistant:** Which external system must the first release integrate with?

**Client:** Corporate SSO only. We can provide documentation and a test tenant.

_Ledger: one integration confirmed; client dependency recorded._

## Data

**Assistant:** What historical data must be available at launch?

**Client:** Open requests from one CSV export. We do not need old closed requests.

_Ledger: bounded migration assumption and exclusion recorded._

## Reporting

**Assistant:** Which reporting capability is essential for the ballpark scope?

**Client:** An operations dashboard, but we have not finalized the KPIs.

_Ledger: dashboard in scope; KPI definitions unresolved and non-blocking._

## Hosting and security

**Assistant:** Which hosting and availability basis should we use for this estimate?

**Client:** Managed public cloud, business-hours support, normal office usage.

_Ledger: managed-cloud basis confirmed; 24x7 support excluded._

## Timeline

**Assistant:** Is there a deadline or event that constrains delivery?

**Client:** We want production within four months, but there is no regulatory deadline.

_Ledger: four-month target confirmed; no immovable deadline._

## BAU

**Assistant:** After launch, which operational services should the recurring ballpark cover?

**Client:** Monitoring, backups, patching, and business-hours incident support.

_Ledger: BAU boundary confirmed._

## Scope checkpoint

The assistant presents outcomes, scope, work packages, 39–60 man-days, assumptions,
exclusions, 10–14 weeks, and remaining KPI detail.

**Assistant:** Do you approve this scope and effort basis for the draft ROM?

**Operator:** Approved as the draft basis.

The calculator writes private internal math and a draft client artifact.

## Commercial gate

**Assistant:** Do you approve this ROM for client discussion?

**Operator:** Approved by Alex Reviewer.

## Result

- Professional-services effort: **39–60 man-days**
- Professional services: **HKD 250,000–418,000**
- One-time infrastructure/hardware: **HKD 31,000–43,000**
- Initial investment: **HKD 281,000–461,000**
- Recurring cloud and BAU: **HKD 12,000–19,000 monthly**
- Indicative delivery: **10–14 weeks**
- Confidence: **Medium**
- Validity: **30 days**

The result remains a ROM, not a fixed quote. The client artifact lists assumptions,
exclusions, unresolved KPI detail, and the named human approver.
