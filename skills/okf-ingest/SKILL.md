---
name: okf-ingest
description: >
  Ingest a source or new concept into an Open Knowledge Format (OKF) knowledge base (a wiki/
  bundle of Markdown + YAML frontmatter). Use when the user wants to add a paper, article, URL,
  video, repo, dataset, person, project, or note to their wiki / knowledge base / second brain.
  Triggers: "ingest this", "add this paper/article to the wiki", "capture this source", "save
  this to my KB", "add a note about X". Fetches and VERIFIES the source, writes a conformant
  page, cross-links it, updates the index + changelog, and lints.
---

# Ingest into an OKF knowledge base

Add a source or concept to an OKF wiki as one Markdown file (a "concept"). If the repo has a
`CLAUDE.md`, **that is authoritative — follow it** (this skill summarizes the same rules so it
works standalone).

## 0. Orient

- The bundle is the `wiki/` directory. Edit knowledge only there. A concept's id is its path
  minus `.md` (`wiki/papers/foo.md` → `papers/foo`).
- If `tools/okf_lint.py` exists, you'll run it at the end.

## 1. Verify — never fabricate

Fetch the real source and confirm its facts from the source itself, not memory (your training
cutoff may predate it):

- **arXiv**: `curl -sL "http://export.arxiv.org/api/query?id_list=<id>"` — read the canonical
  `<title>`, `<author>` list, and `<published>` date. If the id is unknown, search:
  `...query?search_query=ti:%22<title words>%22&max_results=5`.
- **Web**: use WebFetch on the URL; capture title, author/site, date.
- If you cannot confirm it exists, **stop and tell the user** — do not invent metadata.
- Optionally save the raw capture under `raw/` (read-only provenance, outside the bundle).

## 2. Place it

- Choose a **domain folder** by subject (`wiki/papers/`, `wiki/people/`, …) — folder = subject,
  `type` = kind. Create the folder + an `index.md` if it's new.
- Choose a lowercase, hyphenated **slug** (matches `[A-Za-z0-9_][A-Za-z0-9_.-]*`, no spaces).

## 3. Write `wiki/<domain>/<slug>.md`

Frontmatter (keys in this order; use `templates/<type>.md` as a stamp if present):

```yaml
---
type: Source            # Source | Entity | Concept | Note | Overview | Reference
resource: <URI>         # required for Source
title: <human title>
description: <one sentence>
tags: [a, b]            # a YAML LIST, never a comma string
timestamp: 2026-01-01T00:00:00Z   # UTC ISO 8601; refresh on every edit
# extensions allowed after the standard keys (authors, year, venue, doi, …)
---
```

Body: grounded summary prose, then optional `# Key contributions` / `# Schema` / `# Examples`
(fenced code is fine), then `# Citations` (the source's own `resource` URI first). Ground every
claim in the source.

## 4. Link, index, log

- Add genuine **relative markdown** cross-links to/from related concepts —
  `[title](../other/x.md)`. **No `[[wikilinks]]`, no leading `/`.**
- Update the domain `index.md` (`* [Title](slug.md) - description`) and the root `wiki/index.md`
  if you added a new domain.
- Prepend a `wiki/log.md` entry under today's date (`* **Creation**: Added [Title](path).`).

## 5. Lint

```bash
python3 tools/okf_lint.py     # fix any errors; review warnings
```

## Scaling up

For many sources, or anything post-dating your knowledge cutoff, fan out with a workflow:
**discover → verify each against arXiv/web → author**. Verification-before-authoring is what
keeps the KB free of hallucinated sources.
