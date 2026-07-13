# Requirements capture checklist

Extract these from the client's material first; interview only for the gaps.
Every item left unknown after the interview becomes a written assumption in both
output documents.

## 1. Business context

- [ ] What business problem does the system solve? Who sponsors it?
- [ ] Industry / regulatory context (finance, healthcare, government tender, …)
- [ ] Replace an existing system, or greenfield? If replacing: what, and why now?
- [ ] Hard deadline or external driver (compliance date, contract, event)?

## 2. Users and access

- [ ] User types / roles and rough headcount per type
- [ ] Internal staff only, external customers/public, or both?
- [ ] Concurrency expectations (tens / hundreds / thousands)
- [ ] Authentication: standalone accounts, corporate SSO/AD, social login, 2FA?

## 3. Functional scope (drives the module decomposition)

- [ ] Core entities and what users do with them (the CRUD backbone)
- [ ] Workflow/approval chains — how many steps, how many variants?
- [ ] Documents/files: upload, generation (PDF), templates?
- [ ] Search complexity: simple filters vs full-text/faceted
- [ ] Reporting: standard lists/exports vs dashboards vs analytics
- [ ] Notifications: email, SMS, in-app, push?
- [ ] Payment/e-commerce functionality?
- [ ] Admin/back-office console needs

## 4. Platforms

- [ ] Web app: desktop-first, responsive, or both?
- [ ] Native/hybrid mobile app needed? iOS, Android, both?
- [ ] Multi-language UI? (In HK: EN / 繁中 / 简中 — count the set)

## 5. Integrations

For each external system: name, direction (in/out/both), interface style
(REST, SOAP, file/batch, database link, middleware), and whether the counterparty
API is documented and modern or legacy/undocumented.

- [ ] ERP / finance system
- [ ] HR system
- [ ] Payment gateway
- [ ] Identity provider (AD/AAD, Okta, …)
- [ ] Email/SMS providers
- [ ] Anything government-facing (e.g. HK government gateways) — usually legacy-grade

## 6. Data

- [ ] Data migration from existing system(s)? Volume, quality, number of sources
- [ ] Retention or archival requirements
- [ ] Personal data involved → PDPO obligations (HK Personal Data (Privacy) Ordinance)

## 7. Non-functional

- [ ] Hosting: client's cloud, our cloud, on-prem, government cloud?
- [ ] Security/compliance: pen test required, audit trail, ISO/PCI constraints
- [ ] Availability expectations (business hours vs 24×7)
- [ ] Accessibility requirements (WCAG — common in HK government/public work)

## 8. Delivery context

- [ ] Who does UAT and how formal is it?
- [ ] Training / documentation expectations
- [ ] Warranty / support period expectations (affects exclusions, not build effort)
- [ ] Client-side PM/IT maturity (affects PM overhead choice: low vs high end)

## Interviewing rules

- Batch questions; one or two rounds maximum. This is a ballpark, not discovery.
- Prefer enumerable options over open questions where possible.
- When the client material and the user's answers conflict, flag it and ask once.
- Anything still unknown: choose the mid-conservative interpretation, write it as an
  assumption, and move on.
