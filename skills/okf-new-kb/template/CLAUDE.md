# Operating manual for this knowledge base

This repository is a **personal wiki / knowledge base in the Open Knowledge
Format (OKF) v0.1**. It is authored and maintained primarily by coding agents
(Claude Code, Codex) and read/edited by a human in **Obsidian**.

Read this file before creating or editing anything. The pinned spec is
[`OKF-SPEC.md`](OKF-SPEC.md) (vendored verbatim — never edit it). Where this
manual and the spec disagree, the spec wins on *conformance*; this manual adds
house rules on top.

---

## 1. Repository map and the bundle boundary

```
wiki/              <- THE OKF BUNDLE. The only OKF-conformant part of the repo.
  index.md           root index (reserved; frontmatter = only `okf_version: 0.1`)
  log.md             changelog (reserved; no frontmatter)
  overview.md        narrative home concept (type: Overview)
  <domain>/          a domain folder (path = domain, not type)
    index.md         domain index (reserved; no frontmatter)
    <slug>.md        a concept (one file = one concept)
  assets/            images embedded in wiki pages (in-bundle, portable)
raw/               source material you ingest FROM (read-only provenance, NOT in the bundle)
  assets/            large/binary captures
templates/         Obsidian template stamps (NOT in the bundle)
tools/okf_lint.py  validator — run after every change
OKF-SPEC.md        pinned OKF v0.1 spec (verbatim; never edit)
AGENTS.md          pointer to this file for other agents
.obsidian/         Obsidian vault config (vault root = repo root)
```

**Bundle boundary — the most important rule:**
- The bundle is **`wiki/` only**. `tar -czf wiki.tgz wiki/` must be a complete,
  self-contained, OKF-conformant bundle.
- **Edit knowledge only under `wiki/`.**
- **Never** create cross-links from a concept to a file outside `wiki/`
  (e.g. `../../OKF-SPEC.md`) — it breaks bundle portability. Reference external
  things by their URL in `resource`/`# Citations`, or by plain prose path.
- Treat `raw/` as **read-only**: ingest from it, never rewrite it.
- Never edit `OKF-SPEC.md`.

---

## 2. Core OKF model (what you must internalize)

- **Concept = one markdown file.** Every non-reserved `.md` file under `wiki/`
  is exactly one concept.
- **Concept ID = file path within the bundle, minus `.md`.**
  `wiki/meta/open-knowledge-format.md` → concept id `meta/open-knowledge-format`.
- **Identity is the path.** Renaming/moving a file *renames the concept* — so
  when you move a file you MUST fix every inbound link and the affected indexes.
- **The graph is the links.** Directory nesting gives the parent/child tree;
  markdown cross-links give the richer graph. Links are **untyped** — the *kind*
  of relationship (cites, depends-on, part-of) lives in the surrounding prose,
  not the link.

---

## 3. Frontmatter standard (house rules)

Every **non-reserved** concept file MUST open with a YAML frontmatter block
delimited by `---`. Emit keys in **this order**:

```yaml
---
type:        # REQUIRED. See the type vocabulary (§5).
resource:    # optional. A URI for the underlying asset (required on Source).
title:       # REQUIRED. Human-readable display name.
description: # REQUIRED. One sentence. Shown in indexes and previews.
tags:        # optional. A YAML LIST. Never a comma-separated string.
timestamp:   # REQUIRED. ISO 8601 UTC, e.g. 2026-06-19T08:33:09Z. Refresh on every edit.
---
```

Rules:
- **OKF requires only a non-empty `type`.** As a house rule we additionally
  require `title`, `description`, and `timestamp` — they make indexes and search
  useful (and they happen to match the four keys the OKF reference
  implementation's validator checks). OKF itself treats these as optional, so
  when *reading* foreign bundles, tolerate their absence (see §10).
- `tags` is always a **YAML list** (`- foo`), never `tags: a, b, c`. The lint
  rejects the comma-string form even though OKF consumers tolerate it.
- `resource` is a URI identifying the asset a concept describes. Put it on every
  **Source**; omit it for abstract concepts.
- `timestamp` is **UTC, ISO 8601** (`...Z`). **Refresh it on every meaningful
  edit.**
- **Extensions are allowed.** You may add domain keys (`doi`, `venue`, `aliases`,
  `ticker`, …). Put them *after* the standard keys. `aliases` is Obsidian-native
  (alternate page names). Never *remove* unknown keys another author added —
  preserve them when round-tripping.

**Reserved files are the exception** (see §6): `index.md` and `log.md` carry no
frontmatter, except the bundle-root `wiki/index.md`, which carries only
`okf_version: 0.1`.

---

## 4. Filenames, slugs, and domain folders

- Filenames: **lowercase**, words joined by `-` (hyphen). Each path segment must
  match the OKF reference regex `[A-Za-z0-9_][A-Za-z0-9_.-]*` (start with a
  letter/digit/underscore; then letters, digits, `_`, `.`, `-`). **No spaces.**
- The slug should be a stable, human-readable name for the concept, not a date
  or an opaque id.
- **Domain folders organize by subject, not by type.** Use `wiki/papers/`,
  `wiki/people/`, `wiki/projects/` — *not* `wiki/sources/` or `wiki/notes/`.
  The folder says *what it's about*; the `type` field says *what kind of doc it
  is*. Create a domain folder the first time you have something to file there,
  and give it an `index.md`.

---

## 5. Type vocabulary (starter set — extensible)

`type` values are free-form and uncontrolled; consumers tolerate unknown types.
Default to this starter set; add new types when a real new kind appears (and
note it here).

| type       | use for                                                        | `resource`? |
|------------|----------------------------------------------------------------|-------------|
| `Source`   | external material you ingested or cite (article, paper, video, repo, dataset) | **required** |
| `Entity`   | a concrete named thing (person, org, project, tool, product, place) | if it has one |
| `Concept`  | an idea, topic, theory, definition, pattern                    | optional |
| `Note`     | your own atomic observation, idea, or working note             | rarely |
| `Overview` | a hub / map-of-content narrative that orients a domain         | no |
| `Reference`| a small reusable definition other concepts link to (a formula, an enum, a snippet) | optional |

Reserved files (`index.md`, `log.md`) have **no** `type`.

---

## 6. Indexes (reserved `index.md`)

`index.md` provides progressive-disclosure navigation. **Hand-maintain one in
the bundle root and in every domain folder.** Keep them current after any
create / move / rename / delete.

- **No frontmatter** — except the bundle-root `wiki/index.md`, which has exactly
  `okf_version: 0.1` and nothing else.
- Body format: a `#` heading per group, then bullets
  `* [Title](relative-link.md) - description`, where the description is pulled
  from the child's frontmatter `description`.
- Link a **subdirectory via its `index.md`**, not the bare folder:
  `* [Papers](papers/index.md) - ...`.

Example domain index:

```markdown
# Concept

* [Open Knowledge Format](open-knowledge-format.md) - A vendor-neutral file format for portable knowledge.

# Source

* [OKF v0.1 specification](okf-spec.md) - The upstream draft spec this wiki conforms to.
```

---

## 7. The changelog (reserved `log.md`)

`wiki/log.md` is an append-only, newest-first changelog. No frontmatter. After
each ingest or structural change, prepend an entry under today's ISO date:

```markdown
# Update Log

## 2026-06-19

* **Creation**: Added [Memex](concepts/memex.md).
* **Update**: Expanded `# Schema` on [Events table](tables/events.md).
```

Verbs: **Creation**, **Update**, **Initialization**, **Removal**.

---

## 8. Linking (Obsidian + OKF reconciliation)

- **Use relative markdown links only:** `[customers](../tables/customers.md)`.
- **Do NOT use `[[wikilinks]]`.** They are not valid OKF/markdown links and OKF
  consumers (and the reference graph viewer) ignore them. Obsidian is configured
  in `.obsidian/app.json` to author relative markdown links instead — you still
  get autocomplete, backlinks, and graph view.
- **Do NOT start links with `/`.** OKF *recommends* bundle-absolute `/path.md`,
  but the Obsidian vault root is the repo root (not the bundle root), so a
  leading slash breaks in Obsidian. Relative links work in both. (This is our
  one deliberate inversion of OKF §5.1.)
- Keep the `.md` suffix on link targets.
- `# Citations` is a numbered list at the bottom for external sources; a
  `Source` lists its own `resource` URI first.

---

## 9. Procedures

### 9a. Ingest a source
1. If you captured raw material, drop it under `raw/` (read-only provenance).
2. Decide the **domain folder** and a **slug**.
3. Create `wiki/<domain>/<slug>.md` with full frontmatter (`type: Source`,
   `resource:` the URL).
4. Body: summary prose, then any `# Schema` / `# Examples` (fenced code is fine),
   then `# Citations`.
5. Cross-link it from related concepts and vice versa.
6. Update the domain `index.md` and the root `index.md` if a new domain.
7. Prepend a `log.md` entry. Run the lint (§9d).

### 9b. Create a concept
Same as ingest, minus `raw/`. Pick the right `type`. Prefer linking to existing
concepts over duplicating their content (e.g. link to a `Reference` that owns a
formula rather than restating it).

### 9c. Move / rename a concept
The concept id changes. Update **every inbound link** (`grep` for the old path),
the domain indexes, and add a `log.md` entry. Let Obsidian update links on
rename when editing interactively, but verify with the lint.

### 9d. Lint (run after every change)
```bash
python3 tools/okf_lint.py          # lints ./wiki
```
Errors = OKF non-conformance or house-standard violations; fix them. Warnings
(such as broken links, orphans, non-ISO timestamps, wikilinks, leading-slash
links, non-canonical key order, non-lowercase slugs, a Source missing its
`resource`) = review and usually fix. Broken links are *tolerated* by OKF (a
target may be not-yet-written), so they warn rather than fail the build.

### 9e. Query / answer from the KB
Start at `wiki/index.md` → domain `index.md` → concept, following links. Use the
`description` fields and indexes for progressive disclosure; don't load the whole
tree when a path through the indexes suffices.

---

## 10. Be tolerant when reading, strict when writing
- **Reading:** never reject a doc for an unknown `type`, extra frontmatter keys,
  a missing optional field, or a broken link. Preserve unknown keys.
- **Writing your own docs:** follow the full house standard above.

## 11. When you change conventions
If you introduce a new `type`, a new domain key, or a new rule: record it in this
file (§5/§3), mirror it in `templates/`, and add a `log.md` entry. Keep
`templates/` and this manual in sync.
