# thattimc / skills

A small collection of agent skills, shareable two ways: as a **Claude Code plugin** (one-command install + updates) or as **plain skill folders** any other agent (Codex, Cursor, etc.) can copy and use.

## Skills

| Skill | What it does |
|-------|--------------|
| [`domain-search`](skills/domain-search) | Check domain-name availability and brainstorm brandable names across TLDs (`.com`/`.ai`/`.io`/…). |
| [`ssr-market-research`](skills/ssr-market-research) | Run synthetic (LLM-simulated) market research using Semantic Similarity Rating (SSR), from Maier et al. 2025 ([arXiv:2510.08338](https://arxiv.org/abs/2510.08338)) — estimate adoption, purchase intent, and willingness-to-pay without surveying real users. |
| [`okf-new-kb`](skills/okf-new-kb) | Scaffold a new **Open Knowledge Format** personal wiki / knowledge base — Markdown + YAML frontmatter, Obsidian-ready, with operating manual, templates, and a validator. |
| [`okf-ingest`](skills/okf-ingest) | Ingest a source/concept into an OKF knowledge base: verify the source, write a conformant page, cross-link it, update the index + changelog, and lint. |
| [`okf-query`](skills/okf-query) | Answer a question using **only** an OKF knowledge base, with citations and honest gaps. |
| [`okf-lint`](skills/okf-lint) | Validate an OKF knowledge base (spec conformance + house rules). |

The four `okf-*` skills form a family for an OKF / agent-managed / Obsidian wiki: scaffold one with `okf-new-kb`, fill it with `okf-ingest`, read it with `okf-query`, and keep it conformant with `okf-lint`.

## Install — Claude Code (recommended)

```
/plugin marketplace add thattimc/skills
/plugin install tim-skills@thattimc
```

`/plugin update tim-skills` pulls the latest version later.

## Install — other agents (Codex, Cursor, manual)

The skills are plain folders — no Claude-specific runtime needed. Either:

- **Copy into your skills dir:** `cp -R skills/domain-search ~/.claude/skills/` (or wherever your tool reads skills from), or
- **Reference directly:** point your `AGENTS.md` / system prompt at the relevant `skills/<name>/SKILL.md`, which contains the full instructions.

### Script dependencies

| Skill | Needs |
|-------|-------|
| `domain-search` | `bash` + `curl` (queries RDAP via `rdap.org` — no API key) |
| `ssr-market-research` | `python3` + `numpy`. Embeddings backend is either **local** (`model2vec`, no key) or **openai** (`openai` package + `OPENAI_API_KEY`). Defaults to openai, falls back to local. |
| `okf-new-kb` / `okf-lint` | `python3` (the validator is zero-dependency; `pyyaml` optional for max fidelity). |
| `okf-ingest` | `curl` / web fetch to verify sources before writing (e.g. the arXiv API); `python3` for the lint step. |
| `okf-query` | none beyond a shell (`grep`); reads plain Markdown. |

## License

MIT
