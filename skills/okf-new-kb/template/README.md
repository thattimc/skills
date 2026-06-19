# Knowledge base (Open Knowledge Format)

A personal wiki / knowledge base stored as plain Markdown, conforming to the
**[Open Knowledge Format (OKF) v0.1](OKF-SPEC.md)**. Designed to be authored by
coding agents (following [`CLAUDE.md`](CLAUDE.md)), read and edited in
[Obsidian](https://obsidian.md), and portable: the `wiki/` folder is a
self-contained OKF bundle.

## Layout

| Path | What it is |
|------|------------|
| `wiki/` | **The OKF bundle** — the knowledge itself. One `.md` file = one concept. |
| `wiki/index.md` | Root index (navigation). |
| `wiki/log.md` | Changelog. |
| `wiki/overview.md` | Narrative home / map of content. |
| `wiki/<domain>/` | A subject domain, each with its own `index.md`. |
| `wiki/assets/` | Images embedded in wiki pages (kept in-bundle so it stays portable). |
| `raw/` | Source material you ingest *from* (read-only provenance, not part of the bundle). |
| `templates/` | Obsidian template stamps for each doc type. |
| `tools/okf_lint.py` | Validator — checks OKF conformance + house rules. |
| `OKF-SPEC.md` | The pinned OKF v0.1 spec (verbatim). |
| `CLAUDE.md` / `AGENTS.md` | Operating manual for the agents that maintain this KB. |

## Use it

```bash
# Open in Obsidian:  "Open folder as vault" → select this repo.

# Validate after edits:
python3 tools/okf_lint.py

# Export just the portable knowledge bundle:
tar -czf wiki-bundle.tgz wiki/
```

Full conventions: [`CLAUDE.md`](CLAUDE.md). Scaffolded with the `okf-new-kb` skill.
