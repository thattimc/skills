---
name: okf-new-kb
description: >
  Scaffold a brand-new personal wiki / knowledge base in the Open Knowledge Format (OKF).
  Use when the user wants to start a new knowledge base, personal wiki, "second brain", or
  notes repo from scratch — especially an OKF / agent-managed / Obsidian-friendly one.
  Triggers: "new knowledge base", "start a wiki", "scaffold an OKF kb", "set up a personal
  wiki", "create a notes vault", "bootstrap a knowledge base". Stamps a complete, lint-clean
  OKF bundle plus the agent operating manual, templates, validator, and Obsidian config.
---

# New OKF knowledge base

Scaffold an empty but complete **Open Knowledge Format (OKF) v0.1** knowledge base. The
result is a self-contained repo that:

- stores knowledge as plain Markdown with YAML frontmatter (one file = one concept),
- is authored by coding agents (Claude Code / Codex) following a bundled `CLAUDE.md`,
- opens directly as an **Obsidian** vault, and
- ships a zero-dependency validator so every change can be checked.

Everything is in this skill's `template/` directory — a clean, lint-passing bundle.

## Steps

1. **Pick the target directory** (should be empty or a fresh git repo). Confirm with the user.

2. **Copy the template in** (note the trailing `/.` so dotfiles like `.gitignore` and
   `.obsidian/` come along):
   ```bash
   cp -R "<this skill dir>/template/." "<target dir>/"
   ```

3. **Personalize**:
   - Set the KB name in `README.md` (title) and in `wiki/index.md` (the `# ...` heading).
   - Refresh the timestamp in `wiki/overview.md` to now (UTC, `YYYY-MM-DDTHH:MM:SSZ`,
     e.g. `date -u +%Y-%m-%dT%H:%M:%SZ`) and set today's date heading in `wiki/log.md`.

4. **Validate**:
   ```bash
   cd "<target dir>" && python3 tools/okf_lint.py
   ```
   Expect `RESULT: PASS`, 0 errors / 0 warnings.

5. **Initialize git** (if not already a repo) and make the first commit:
   ```bash
   git init -q && git add -A && git commit -qm "feat: scaffold OKF knowledge base"
   ```

6. **Tell the user** they can open the folder as an Obsidian vault ("Open folder as vault"),
   and that future content is best added with the `okf-ingest` skill.

## What gets created

```
wiki/            the OKF bundle (index.md, overview.md, log.md, assets/) — the only conformant part
CLAUDE.md        operating manual: frontmatter standard, link rules, type vocabulary, procedures
AGENTS.md        pointer to CLAUDE.md for Codex / other agents
OKF-SPEC.md      OKF v0.1 spec, vendored verbatim
templates/       Obsidian stamps per concept type
tools/okf_lint.py  validator (OKF conformance + house rules)
raw/             out-of-bundle source/provenance area
.obsidian/       vault config (relative markdown links, attachments -> wiki/assets)
.gitignore
```

## Notes

- The bundle is `wiki/` only — `tar -czf wiki.tgz wiki/` is a portable OKF bundle.
- Conventions (frontmatter, relative-markdown links not `[[wikilinks]]`, indexes, log) live in
  the copied `CLAUDE.md` — that is the single source of truth for the new KB.
- Do **not** edit `OKF-SPEC.md` (it is the pinned spec).
