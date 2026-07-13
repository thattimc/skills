# iRate private config — schema & setup

The skill reads `~/.claude/irate.yaml` at runtime. This file holds the firm's
**confidential sell rates** and any calibration overrides. It must never be committed
to a repository or pasted into skill files — the skill only ever reads it and writes
figures into generated estimate documents.

If the file is missing, show the user the template below, ask them to create the file
with their real rates, and stop until it exists. Do not proceed with invented rates.

## Template (copy to `~/.claude/irate.yaml`)

```yaml
# iRate — confidential. Sell rates per man-day.
currency: HKD

rates:
  pm: 0          # Project Manager
  ba: 0          # Business Analyst
  sa: 0          # Solution Architect
  senior_dev: 0  # Senior Developer
  dev: 0         # Developer
  qa: 0          # QA / Tester
  uiux: 0        # UI/UX Designer

# Optional: default validity period for client letters (days)
validity_days: 30

# Optional: override any default in references/calibration.md.
# Only include keys you want to change; structure mirrors the tables.
calibration_overrides:
  tiers:            # build MD ranges [low, high]
    # S: [5, 10]
    # M: [12, 25]
    # L: [30, 55]
    # XL: [60, 100]
  overheads:        # fraction of build MD
    # design_pct: [0.20, 0.25]
    # qa_pct: [0.20, 0.25]
    # pm_pct: [0.12, 0.15]
    # uat_deploy_pct: [0.08, 0.12]
  adders:           # cross-cutting items, [low, high] MD
    # auth_standalone: [8, 15]
    # sso: [5, 10]
  integrations:
    # rest_oneway: [5, 10]
    # legacy: [12, 25]
  multipliers:
    # mobile_crossplatform: [1.3, 1.6]
    # compliance: [1.10, 1.15]
```

## Rules for the skill

- Validate on load: `currency` present; every role in `rates` a positive number.
  Zero or missing rates → treat as not set up; show the template.
- Extra custom roles in `rates` are allowed (e.g. `devops`, `data_engineer`); use them
  in the role mix only when the project clearly needs them, and say so in the
  internal sheet.
- Merge `calibration_overrides` shallowly per key on top of the defaults in
  [calibration.md](calibration.md); overrides always win.
- If `currency` is not HKD, use it consistently everywhere and drop HKD-specific
  rounding (round to a similar magnitude in that currency).
- Quote rates only inside the generated internal sheet. The client letter shows
  cost ranges, never the per-role day rates, unless the user explicitly asks to
  include a rate table.
