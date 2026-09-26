---
name: domain-search
description: >
  Check domain-name availability and brainstorm brandable names to buy. Use when the user
  wants to know if a domain is available/taken, find an available name for a project, compare
  names across TLDs (.com/.ai/.io/...), check whether a domain is premium or for sale, or pick a
  product/company/brand name. Triggers: "is X.com available", "find a domain", "check these
  domains", "available domain names", "name this project/product/company", "brainstorm a brand
  name", "domain availability".
---

# Domain Search

Brainstorm brandable names, find which domains can really be registered, and screen the
shortlist before the user buys.

## What the statuses mean

- **AVAILABLE**: the registry itself has no registration (registry RDAP 404, or its WHOIS
  says "not found"). It can still be premium-priced or reserved; confirm at a registrar.
- **TAKEN**: the registry has a record, or the name is delegated in DNS.
- **UNKNOWN**: no registry answered (no RDAP server and no usable WHOIS, or rate-limited).
  Never present UNKNOWN as available. Say which names need a manual check.

## Recommended flow

1. **Bulk screen with Instant Domain Search** when its MCP tools are in the session
   (free, no key; server `https://mcp.instantdomainsearch.com/mcp`). Use
   `check_domain_availability` (up to 50 full domains per call), `search_domains` (one name
   across TLDs) and `generate_domain_variations` (.com alternatives). Results add what the
   script cannot: registry premium prices, aftermarket listings with prices (Atom, Afternic,
   Sedo) and `etldCount` (how many TLDs already hold the name; high means contested).
   Its status comes from a daily index, so treat it as a filter, not a verdict.
2. **Confirm the shortlist live** with `scripts/check-domains.sh` (below). Its answer is
   the one to report.
3. **Confirm the price at a registrar** right before buying: Cloudflare Registrar sells at
   cost; Porkbun is a good second quote. Run the script with `--no-cache` first.

Without the MCP tools, run step 2 on every candidate and warn that premium and for-sale
status is unchecked.

## The script

```bash
bash scripts/check-domains.sh --tlds com,ai,io acme otherword   # names x TLDs
bash scripts/check-domains.sh acme.com acme.ai foo.co            # explicit domains
bash scripts/check-domains.sh --json --tlds com,ai acme          # adds "source"
```

Output: ✅ AVAILABLE / ❌ taken / ❓ unknown (with the reason). `--json` returns `domain`,
`status`, `source` (`rdap`, `whois` or `doh`), `detail` and `cached`. Bare names without
`--tlds` are checked as `.com`. In zsh, pass names as separate arguments or an array: an
unquoted `$NAMES` is not word-split.

How it decides, per domain, in parallel (Python 3 standard library, no key):

1. **DNS-over-HTTPS** (Cloudflare) NS lookup: a delegated name is TAKEN. A missing
   delegation proves nothing, so those names go on to the registry. Local `dig` is not
   used; networks that intercept DNS make it wrong.
2. **Registry RDAP**, found through the IANA bootstrap (cached daily) plus overrides for
   registries missing from it (`.co`, `.io`, `.me`, `.sh`). rdap.org is never used: for
   TLDs it has no server for it answers 404, which the old script reported as AVAILABLE
   (google.io, google.co and google.me all showed as available).
3. **Registry WHOIS** (port 43) when a TLD has no RDAP or its server refuses us.
4. Otherwise **UNKNOWN**.

Rate limits: parallel requests are capped per registry (Verisign 8, Google 4, Identity
Digital 1, others 2). A `Retry-After` up to 30 s is honored; a longer one switches that
registry to WHOIS and is remembered across runs so the lockout is not extended. Results
are cached for 6 hours in `${XDG_CACHE_HOME:-~/.cache}/domain-search/`; `--no-cache`
forces fresh checks and `--no-doh` skips the DNS step.

## Naming workflow

1. **Understand the product** first: repo, README, the user's notes. Names must fit the
   positioning, audience and tone.
2. **Brainstorm in styles**: real words, coined or portmanteau words, foreign words,
   compounds, verb + suffix (-ly, -ify). Short dictionary words are almost always taken on
   `.com`; compounds and coined words are where `.com` wins are.
3. **Screen, confirm, then gate** the shortlist (flow above, quality gate below).
4. **Present by availability**, leading with the user's preferred TLD, one line each on
   what the name evokes, plus price or listing when known.

Default TLDs: `.com` and `.ai`; add `.io`/`.dev`/`.app` for developer tools. If the user
already owns domains, check whether one fits before suggesting purchases.

## Multi-agent pipeline

For a large brainstorm with several agents:

1. **Naming lanes in parallel**, each with a different style constraint (coined,
   compound, real word, foreign word, verb + suffix). Lanes make no network calls; each
   returns a plain list.
2. **One checking stage**: the lead merges and de-duplicates every list, then runs one
   Instant Domain Search pass and one script run. Never let each agent run the checker:
   they share one IP and its rate limits, and parallel runs trip registry lockouts.
3. **Scoring in parallel** on a shortlist of 10-15 available names: each scorer runs the
   quality gate below on its share.
4. **The lead ranks** and presents the result.

## Name-quality gate (search and answer engines)

What the evidence says:

- Keywords in the domain give no ranking boost. Google: "the keywords in the name of the
  domain (or URL path) alone have hardly any effect beyond appearing in breadcrumbs"
  ([SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)).
  Pick the name for the brand.
- Google treats `.ai`, `.io`, `.co` and `.me` as generic, like `.com`, not as country
  targeting ([managing multi-regional sites](https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites)).
  `.sh` is not on that list.
- `.io` has a sovereignty risk: the UK's agreement to transfer the Chagos Islands to
  Mauritius could retire the `IO` country code, and IANA retires ccTLDs whose code is
  removed. Retirement comes with years of notice, but prefer another TLD for a brand
  meant to last.
- Answer engines resolve a distinctive coined name to one entity more reliably than a
  dictionary word, which competes with the word's meaning and every other user of it.

Check each shortlisted name:

- Search the exact name: who already ranks for it?
- Search [Wikidata](https://www.wikidata.org/) for existing entities with that name.
- Ask ChatGPT, Perplexity and Claude "What is <name>?" and note any existing entity.
- Trademarks: USPTO (Instant Domain Search `search_trademarks`, or USPTO search) and EUIPO
  [TMview](https://www.tmdn.org/tmview/) in the classes the product uses.
- Handles: X, GitHub, npm, Instagram, LinkedIn. Also app-store names.
- Radio test: at most 3 syllables, one obvious spelling when heard, no digits or hyphens.

At launch, publish `Organization` schema with `sameAs` links to every profile, and use one
consistent category sentence ("<Name> is a <category> for <audience>") everywhere.

## Pitfalls

- **Shared IP rate limits.** Identity Digital (`.ai`, `.io`, `.me`, `.sh` and many new
  gTLDs) locked an IP out of RDAP for about 24 hours after a few quick requests. The script
  then uses WHOIS, which still answers, but keep batches small and never run checkers in
  parallel.
- **Instant Domain Search is a daily index.** `search_domains` reports `false` for TLDs it
  does not cover; `check_domain_availability` reports `null` there. Confirm with the script.
- **AVAILABLE is not a price.** Registry premium and reserved names can pass the check;
  the registrar's checkout is the final word.
- **Cached answers are up to 6 hours old.** Use `--no-cache` right before buying.
