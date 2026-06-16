# thattimc / skills

A small collection of agent skills, shareable two ways: as a **Claude Code plugin** (one-command install + updates) or as **plain skill folders** any other agent (Codex, Cursor, etc.) can copy and use.

## Skills

| Skill | What it does |
|-------|--------------|
| [`domain-search`](skills/domain-search) | Check domain-name availability and brainstorm brandable names across TLDs (`.com`/`.ai`/`.io`/…). |
| [`ssr-market-research`](skills/ssr-market-research) | Run synthetic (LLM-simulated) market research using Semantic Similarity Rating (SSR), from Maier et al. 2025 ([arXiv:2510.08338](https://arxiv.org/abs/2510.08338)) — estimate adoption, purchase intent, and willingness-to-pay without surveying real users. |

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

## License

MIT
