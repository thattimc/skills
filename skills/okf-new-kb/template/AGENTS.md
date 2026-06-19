# AGENTS.md

This repository is a personal knowledge base in the **Open Knowledge Format
(OKF) v0.1**, managed by coding agents and read in Obsidian.

**All operating rules live in [`CLAUDE.md`](CLAUDE.md).** Read it before
creating or editing anything — it defines the bundle boundary (edit knowledge
only under `wiki/`), the frontmatter standard, filename/link rules, the type
vocabulary, and the ingest/lint procedures.

After any change, run the validator:

```bash
python3 tools/okf_lint.py
```

The pinned spec is [`OKF-SPEC.md`](OKF-SPEC.md) (verbatim — never edit it).
