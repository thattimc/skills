# Calibration table & math procedure

Default effort figures for custom-built business applications. All figures are
**man-days (MD) of build effort** (developers only) unless marked otherwise; overheads
add the other roles. Every entry here can be overridden by `calibration_overrides`
in the user's private `~/.claude/irate.yaml` — overrides always win.

These defaults are generic industry-shaped numbers, not the firm's actuals. Encourage
the user to tighten them in their private file as real project data accumulates.

## Module tiers

Size each functional module independently. When a module straddles two tiers, use the
higher tier's low bound to the lower tier's high bound — don't average away uncertainty.

| Tier | Definition | Build MD |
|------|------------|----------|
| S | Simple CRUD over one entity; static/informational screens; basic admin list | 5–10 |
| M | Standard module: multi-screen forms, validation, business rules, list/detail/search | 12–25 |
| L | Complex module: multi-step workflow, approval chains, role-dependent behaviour, complex domain logic | 30–55 |
| XL | Core engine: calculation/rules engine, scheduling/optimisation, real-time features, heavy concurrency | 60–100 |

Tier test questions: How many screens? How many business rules? How many roles behave
differently in it? Does it hold state across steps? Anything real-time or computed?

## Cross-cutting adders (build MD)

| Item | MD |
|------|----|
| Authentication + user/role management, standalone | 8–15 |
| SSO / AD / AAD integration | +5–10 |
| 2FA (SMS/TOTP) | +3–6 |
| Notifications (email templates + triggers) | 5–12 |
| SMS or push channel, each additional | +3–6 |
| File upload/storage with preview | 4–8 |
| PDF/document generation, per template family | 3–6 |
| Standard reports/exports (CSV/Excel), per batch of ~5 | 5–10 |
| Dashboard with charts | 8–18 |
| Full-text / faceted search | 6–15 |
| Payment gateway integration (one provider) | 8–15 |
| Admin console beyond basic CRUD (config, audit views) | 10–20 |

## Integrations (per external system, build MD)

| Kind | MD |
|------|----|
| Modern documented REST API, one-way | 5–10 |
| Modern API, bidirectional / multiple entities | 10–18 |
| Legacy interface (SOAP, file/batch, DB link, undocumented) | 12–25 |
| Middleware/ESB involvement or government gateway | 20–40 |

## Data migration (total MD, all roles)

| Kind | MD |
|------|----|
| Single clean source, scripted load | 10–20 |
| Multiple sources or dirty data, mapping + cleansing + trial runs | 30–60 |

## Project-level multipliers (apply to build subtotal)

Apply multiplicatively, in this order, only where they genuinely apply:

| Condition | Factor |
|-----------|--------|
| Mobile app mirrors web scope (cross-platform, iOS+Android) | ×1.3–1.6 on mirrored scope only |
| Fully native iOS + Android (two codebases) | ×1.6–2.0 on mirrored scope only |
| Multi-language UI (per language beyond first) | ×1.05 each |
| Compliance-heavy (PDPO handling, audit trail everywhere, pen-test remediation cycle) | ×1.10–1.15 |
| Client is government / tender-grade documentation expected | ×1.10 |

## Overheads (percent of post-multiplier build MD → other roles)

| Overhead | % | Role(s) |
|----------|---|---------|
| Requirements & design | 20–25% | BA, SA, UI/UX |
| QA / testing | 20–25% | QA |
| Project management | 12–15% | PM |
| UAT support, deployment, handover | 8–12% | Sr Dev, BA |

Pick the low end for a mature client with clear requirements, high end for vague scope,
committee-driven clients, or first-time-outsourcing clients (see checklist §8).

## Role-mix for build effort

Split build MD (post-multiplier, before overheads): **Senior Dev 30–40%, Dev 55–65%,
SA 5%** (technical design embedded in build). Overheads map to roles per the table above;
split "Requirements & design" roughly BA 50% / SA 25% / UI-UX 25% unless the project is
UI-heavy (portal, consumer mobile) — then BA 35% / SA 15% / UI-UX 50%.

## Math procedure

1. Sum module tier ranges → low/high build MD.
2. Add cross-cutting adders and integrations (their own low/high).
3. Apply project-level multipliers to the running low/high.
4. Compute overhead MD from the build subtotal; add. Now you have total low/high MD.
5. Allocate MD to roles per role-mix. Multiply each role's MD by its iRate day rate.
6. Sum → low/high HKD. **Do the arithmetic stepwise and verify the total twice** —
   a slipped decimal in a client quote is fatal.

## Presentation rules

- Round MD to the nearest 5; round HKD to the nearest 10,000 (nearest 50,000 above ~3M).
- If the computed high < 1.4 × low, widen the high to 1.4 × low — a narrower range
  overstates ROM precision.
- Label everything ±40–50% ROM. Never present a midpoint as "the price".

## Indicative timeline (only if asked)

Elapsed months ≈ total MD ÷ (20 × feasible team size). Feasible team: 3–4 for
< 300 MD, 5–7 for 300–800 MD, 8+ above. Add ~1 month for UAT + deployment. Label
indicative; sequencing and client availability dominate real timelines.
