---
name: okf-lint
description: >
  Validate an Open Knowledge Format (OKF) knowledge base (a wiki/ bundle of Markdown + YAML
  frontmatter) for spec conformance and house rules. Use when the user wants to check, validate,
  or lint their wiki / knowledge base, or after editing KB pages. Triggers: "lint my wiki",
  "validate the knowledge base", "check the OKF bundle", "is my wiki conformant", "run the okf
  linter". Reports errors (must fix) and warnings (review), with a non-zero exit on failure.
---

# Lint an OKF knowledge base

Validate a `wiki/` OKF bundle. A copy of the validator ships with this skill at
`scripts/okf_lint.py`; if the target repo already has `tools/okf_lint.py`, prefer that one
(it's the repo's pinned copy).

## Run it

```bash
# In the KB repo (bundle defaults to ./wiki):
python3 tools/okf_lint.py                 # repo's copy, if present
# or, standalone, using this skill's bundled copy:
python3 "<this skill dir>/scripts/okf_lint.py" --bundle <path-to>/wiki
```

Flags: `--bundle <dir>` (default `wiki`), `--quiet` (summary only), `--strict` (warnings fail
too — good for CI). Exit code is non-zero on failure, so it can gate commits/CI.

`pip install pyyaml` gives maximum parsing fidelity; without it a built-in fallback parser is
used (results are kept identical between the two).

## Interpreting output

- **`RESULT: PASS`, 0 errors** → OKF-conformant and house-rule-clean.
- **Errors (must fix)**: missing/empty `type` (the one OKF-required field), missing
  `title`/`description`/`timestamp` (house rule), `tags` as a comma-string instead of a list,
  a reserved file (`index.md`/`log.md`) carrying frontmatter (root `index.md` may carry only
  `okf_version`).
- **Warnings (review, usually fix)**: broken links, orphan pages, non-ISO timestamps,
  `[[wikilinks]]`, leading-slash links, non-canonical frontmatter key order, odd or
  non-lowercase slugs, a `Source` missing its `resource`. Broken links only warn because OKF
  tolerates not-yet-written targets.

## Make it automatic (suggest to the user)

Wire it into a git pre-commit hook so bad edits never land:

```sh
# .git/hooks/pre-commit
#!/bin/sh
python3 tools/okf_lint.py --quiet || { echo "okf_lint failed"; exit 1; }
```

Or run `--strict` in CI.
