# thattimc / skills

A small collection of agent skills, shareable two ways: as a **Claude Code plugin** (one-command install + updates) or as **plain skill folders** any other agent (Codex, Cursor, etc.) can copy and use.

## Skills

### Engineering

| Skill | What it does |
|-------|--------------|
| [`claude-code-review`](skills/claude-code-review) | Run Claude Code as an independent cross-model reviewer, then verify every reported finding locally before presenting it. |

### Discovery and research

| Skill | What it does |
|-------|--------------|
| [`domain-search`](skills/domain-search) | Check domain-name availability and brainstorm brandable names across TLDs (`.com`/`.ai`/`.io`/…). |
| [`ssr-market-research`](skills/ssr-market-research) | Run synthetic (LLM-simulated) market research using Semantic Similarity Rating (SSR), from Maier et al. 2025 ([arXiv:2510.08338](https://arxiv.org/abs/2510.08338)) — estimate adoption, purchase intent, and willingness-to-pay without surveying real users. |
| [`xquik-x-research`](skills/xquik-x-research) | Research public X data with Xquik REST or MCP while keeping source text isolated and bounded. |
| [`presales-with-docs`](skills/presales-with-docs) | Run live client discovery one question at a time, preserve a decision ledger, and produce an auditable ballpark/ROM covering services, timeline, infrastructure, cloud, and BAU. |

### Teaching

| Skill | What it does |
|-------|--------------|
| [`teach-enhance`](skills/teach-enhance) | Teach a topic over multiple sessions **and** ship it as a polished, self-hosted HTML course in one command. A superset of `/teach`: runs the full teaching methodology (mission-first, stateful lessons + glossary + reference cards, ZPD pacing) with the experience baked into every lesson — in-browser neural read-aloud (Kokoro-82M) with word-highlighting, ADHD-friendly reading aids, a light/dark inline-SVG diagram kit, and content patterns (TL;DR, mid/end quizzes, worked examples, recap). |

### Knowledge bases

| Skill | What it does |
|-------|--------------|
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
| `xquik-x-research` | `XQUIK_API_KEY` for live REST or MCP requests. No dependency for planning and source review. |
| `presales-with-docs` | `python3` for the zero-dependency ballpark calculator; an approved private rate card and dated infrastructure/cloud/BAU price sources for real estimates. |
| `claude-code-review` | An authenticated Claude Code CLI with the `ultrareview` command. |
| `teach-enhance` | `python3` to run `scripts/apply.py` (wires components into a lesson workspace; vendors the highlighter — needs network on first wire) and to serve lessons over `http` (`python3 -m http.server`). The read-aloud downloads an ~80 MB Kokoro model in-browser on first use (best on Chrome/WebGPU; falls back to the OS voice offline or over `file://`). |
| `okf-new-kb` / `okf-lint` | `python3` (the validator is zero-dependency; `pyyaml` optional for max fidelity). |
| `okf-ingest` | `curl` / web fetch to verify sources before writing (e.g. the arXiv API); `python3` for the lint step. |
| `okf-query` | none beyond a shell (`grep`); reads plain Markdown. |

## License

MIT
