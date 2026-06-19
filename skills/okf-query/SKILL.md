---
name: okf-query
description: >
  Answer a question using ONLY an Open Knowledge Format (OKF) knowledge base (a wiki/ bundle of
  Markdown + YAML frontmatter), with citations and honest gaps. Use when the user asks something
  their wiki / knowledge base / notes should answer, or says "according to my notes/KB", "what
  does my wiki say about X", "search my knowledge base", "what do I have on X". Navigates the
  indexes, cites concept ids, and flags what's missing instead of guessing.
---

# Query an OKF knowledge base

Answer from the wiki, grounded and cited. If the repo has a `CLAUDE.md`, follow its query
guidance; this skill states the same discipline so it works standalone.

## How to navigate (progressive disclosure)

1. Start at `wiki/index.md` → the relevant domain `index.md` → the concept page. Follow the
   `description` fields and relative links rather than loading the whole tree.
2. Useful shortcuts:
   - `grep -ril "<term>" wiki` — find pages mentioning a term.
   - `grep -rl "^type: Source" wiki` — list pages of a type.
   - `grep -rl "<tag>" wiki` — find by tag. Frontmatter is plain text, so grep works.
   - Follow `# Related` / cross-links and backlinks for neighboring concepts.

## Rules

- **Answer only from KB content.** Do not fill gaps from training data.
- **Cite the concept id / path** for each claim, e.g. `papers/routenlp-...` or a relative link.
- **If the answer isn't in the KB, say so plainly** and offer to add it with the `okf-ingest`
  skill — don't guess.
- Distinguish what the KB asserts from your own inference; keep them clearly separated.
- For "what's related to X", report the actual cross-links/backlinks, not associations you
  imagine.

## In Obsidian (for the user)

Mention that they can also use Obsidian's Search (`Cmd-Shift-F`, including property filters like
`tag:#…` or `[year:2026]`), the graph view, and the backlinks panel — all of which read the same
relative-markdown links the KB uses.
