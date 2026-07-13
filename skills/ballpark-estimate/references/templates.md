# Output templates

Two documents per estimate, written to the working directory (or where the user says).
`<client-slug>` = lowercase-hyphenated client or project name.

---

## 1. Internal working sheet — `<client-slug>-estimate-internal.md`

For the firm only. Shows all math so the estimate can be defended and revised.

```markdown
# [Project name] — ballpark estimate (INTERNAL)

Prepared: [date] · Estimate class: ROM ±40–50% · Currency: [HKD]

## Input summary
[2–5 sentences: what the client asked for, what material we had, key unknowns.]

## Requirement gaps → assumptions
| # | Gap | Assumption taken |
|---|-----|------------------|

## Module decomposition
| Module | Tier | Rationale | Build MD (low–high) |
|--------|------|-----------|---------------------|
| … | | | |
| **Subtotal — modules** | | | **X–Y** |

## Cross-cutting & integrations
| Item | Basis (table row) | MD (low–high) |
|------|-------------------|---------------|
| **Subtotal — build** | | **X–Y** |

## Multipliers
| Condition | Factor | Running subtotal (low–high) |
|-----------|--------|------------------------------|

## Overheads
| Overhead | % used | MD (low–high) | Role(s) |
|----------|--------|---------------|---------|
| **Total effort** | | **X–Y MD** | |

## Cost build-up
| Role | Day rate | MD (low–high) | Cost (low–high) |
|------|----------|---------------|-----------------|
| **Total** | | | **HKD X–Y** |

## Presented figures (after rounding rules)
Effort: **X–Y man-days** · Cost: **HKD X–Y**
[Indicative timeline if computed.]

## Sensitivity / watch-outs
[Bullets: which assumptions swing the number most; what would push it out of range;
what to verify before any firm quote.]
```

---

## 2. Client-facing letter — `<client-slug>-estimate-letter.md`

Polished, English, no internal rate math. Tone: professional, plain, confident about
the range and honest about its class.

```markdown
# Ballpark estimate — [Project name]

**Prepared for:** [Client] · **Date:** [date] · **Valid for:** [validity_days] days

## Understanding of your requirements
[Short prose: the system as we understood it — purpose, main user groups, platforms.]

## Scope summary
| Area | What's included |
|------|-----------------|
[One row per module/area, plain-language description. No MD figures per row.]

## Indicative estimate
| | |
|---|---|
| Estimated effort | **X–Y man-days** |
| Estimated investment | **HKD X–Y** |
| Indicative duration | [only if requested] |

This is a **rough-order-of-magnitude (ROM) estimate with an accuracy of roughly
±40–50%**, based on the information available to date. It is provided for budgetary
planning and is not a fixed quotation. A detailed proposal with a firm price requires
a requirements-definition exercise.

## Assumptions
[Numbered list — every gap converted to an assumption, plus standard ones:
client provides timely input/UAT, content and data supplied in agreed format, etc.]

## Exclusions
[Numbered list — always consider: third-party licences and subscriptions, hosting and
cloud running costs, data migration (if not scoped), content entry, hardware,
ongoing support/maintenance beyond warranty, travel, taxes.]

## Next step
[One short paragraph: propose a requirements workshop / discovery phase to firm up
scope and produce a detailed quotation.]
```

---

## Writing rules

- Ranges only in client-facing figures; never a single number.
- Round per calibration.md presentation rules before writing either doc.
- The letter's scope table must cover everything counted in the internal sheet —
  a client comparing the two later should find no surprises.
- Exclusions are the cheapest insurance the firm has: when unsure whether something
  is in scope, exclude it explicitly rather than staying silent.
