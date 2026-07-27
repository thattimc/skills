---
name: domain-search
description: >
  Check domain-name availability and brainstorm brandable names to buy. Use when the user
  wants to know if a domain is available/taken, find an available name for a project, compare
  names across TLDs (.com/.ai/.io/...), or pick a product/company/brand name. Triggers:
  "is X.com available", "find a domain", "check these domains", "available domain names",
  "name this project/product/company", "brainstorm a brand name", "domain availability".
---

# Domain Search

Brainstorm brandable names and check which domains are actually available to register.

## How availability is checked: RDAP (not WHOIS, not a paid API)

Availability is determined with **RDAP** — the official IETF successor to WHOIS (RFC 9082/9083).
Query `https://rdap.org/domain/<fqdn>`, which routes to the responsible registry and returns:

- **HTTP 404 → AVAILABLE** (no registration record exists)
- **HTTP 200 → TAKEN** (a registration record exists)
- **anything else → UNKNOWN** (TLD has no RDAP server)

rdap.org throttles bursts, so the script retries `429`/`5xx`/network failures up to 3× with
backoff and pauses ~0.2s between domains (`RDAP_THROTTLE` env var). Without that, transient
rate-limiting shows up as `UNKNOWN` and quietly hides real answers in a large batch.

This is authoritative and free. It is more reliable than scraping Instant Domain Search /
GoDaddy, whose public endpoints change and rate-limit. RDAP tells you *registered or not*; it
does **not** price premium/reserved names — confirm the final price at a registrar.

### Caveats (state these when relevant)
- **Not all TLDs publish RDAP.** `.io` historically had no RDAP, and some ccTLDs still don't.
  `UNKNOWN` means "couldn't determine" — never report it as available.
- `.com`, `.ai`, `.net`, `.org`, `.app`, `.dev`, `.co` work well via RDAP.
- An RDAP-available name can still be a **premium** listing (high price). Verify at checkout.

## The script

`scripts/check-domains.sh` — batch checker. Always pass it as an explicit list (zsh does not
word-split unquoted variables, so loop over arrays or pass args directly).

```bash
# Names × TLDs (cartesian):
bash scripts/check-domains.sh --tlds com,ai,app myname otherword

# Explicit FQDNs:
bash scripts/check-domains.sh acme.com acme.ai foo.io

# Machine-readable (for further processing):
bash scripts/check-domains.sh --json --tlds com,ai myname
```

Output uses ✅ AVAILABLE / ❌ taken / ❓ unknown.

## Workflow

1. **Understand the product** before brainstorming. Check the repo, README, and (if present)
   the user's memory/notes so names fit the actual positioning, audience, and tone.
2. **Brainstorm in styles**, not at random — mix: real words, invented/portmanteau, foreign
   words, compounds, and `verb+suffix` (-ly, -ify, -ish). Short single words are almost always
   taken on `.com`; **compounds and coined words** are where `.com` wins are found.
3. **Batch-check** with the script across the TLDs the user cares about (default `.com,.ai`).
4. **Present results grouped by availability**, leading with names available on the user's
   preferred TLD. For each, give a one-line rationale (what it evokes) so the choice is informed.
5. **Remind** that RDAP-available ≠ final price; premium names cost more — verify at a registrar
   (Cloudflare Registrar is at-cost and a good default if the user already uses Cloudflare).

## Tips
- Default to checking `.com` and `.ai`; add `.app`/`.io`/`.dev` for developer-facing tools.
- If the user already owns domains (e.g. registered at Cloudflare), check whether one fits
  before suggesting new purchases — reusing an owned domain is free.
- Avoid names colliding with direct competitors or trademarks; flag near-misses you notice.
