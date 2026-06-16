---
name: ssr-market-research
description: >
  Run synthetic (LLM-simulated) market research using Semantic Similarity Rating (SSR),
  the method from Maier et al. 2025 (arXiv:2510.08338). Use when estimating customer
  adoption, purchase intent, or willingness-to-pay for product concepts/features WITHOUT
  surveying real users: define target-segment personas, elicit free-text reactions, and
  map them to Likert intent distributions via embedding similarity. Triggers: "synthetic
  research", "SSR", "test these feature/product ideas", "willingness to pay", "which
  concept resonates", "simulated survey", "concept testing", "productized marketing research".
---

# SSR Market Research

Estimate how a target market will react to product concepts by simulating consumers with an
LLM and scoring their reactions with **Semantic Similarity Rating (SSR)**. SSR avoids the
"everything is a 3" failure mode of asking an LLM for numeric ratings directly.

## Why direct numeric ratings fail (and what SSR does instead)

If you ask an LLM "rate your purchase intent 1–5," it **regresses to the center** — low
variance, unrealistic, ~50% accuracy. SSR fixes this with four design choices, all of which
matter (dropping persona detail alone cut accuracy 92% → 50% in the paper):

1. **Rich persona conditioning.** Each synthetic respondent impersonates a *specific* person
   with demographics + backstory + context, not a generic "user."
2. **Free-text elicitation first.** NEVER ask for a number. Ask an open question
   ("How likely would you be to adopt/pay for this, and why?") and capture the natural-language
   answer. The variance lives in the words.
3. **Embedding → Likert mapping.** Embed the free-text reply and 5 anchor statements (one per
   Likert point). Cosine-similarity, subtract the minimum, normalize → a probability
   distribution over 1–5.
4. **Average over multiple anchor sets + many respondents.** 6 stylistic anchor sets capture
   different ways people express intent; many respondents give a survey-level distribution.

The paper hit ~90% of human test–retest reliability this way, beating supervised models.

## The pipeline

```
segments + personas  →  concepts to test  →  free-text reactions  →  ssr.py  →  intent distributions
   (who)                  (what)               (LLM impersonation)    (scoring)   (per concept × segment)
```

### Step 1 — Design the study
- **Segments & personas.** Write ≥1 persona per target segment with real demographic +
  psychographic + situational detail (role, tools, pains, context). More personas per
  segment = tighter estimates. Store in `personas.json`.
- **Concepts.** One short, concrete description per feature/product idea you want to test.
  Store in `concepts.json`. Keep each concept self-contained — a respondent reads it cold.

### Step 2 — Elicit free-text reactions (the impersonation step)
For every (persona × concept) pair, produce a 2–4 sentence first-person reaction answering
"How likely would you be to adopt and pay for this, and why?" — in that persona's voice,
with their specific concerns. **Two ways to generate them:**
- **Inline:** author them yourself, varying voice/skepticism/enthusiasm per persona. Fast,
  fine for a directional v1. Risk: responses homogenize within one context.
- **Workflow (preferred for rigor):** spawn one subagent *per persona* so each reacts in an
  independent context (true respondent independence). Use this when the user opts into
  multi-agent orchestration / a larger N. See `references/workflow-example.md`.

Store as `responses.json`: a list of `{persona_id, segment, concept, response_text}`.

### Step 3 — Score with SSR
```bash
python3 scripts/ssr.py \
  --responses responses.json \
  --anchors scripts/anchors.json \
  --out results.json
```
Outputs per-concept and per-(concept × segment): the Likert PMF, **mean intent**,
**top-2-box %** (mass on the top two points = strong intent), **bottom-box %**, and n.
Prints a ranked table to stdout. Requires the venv from "Setup" below.

### Step 4 — Interpret
- Rank concepts by **top-2-box** (share of strong adopters) and by **mean**.
- Read the **segment split** — a concept can score mid overall but dominate one segment
  (your wedge). Variance/polarization is signal, not noise.
- Treat absolute numbers as **directional**, not validated, unless N is large and personas
  are grounded in real data. Report it that way.

## Setup (one-time, per machine)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install numpy model2vec openai
```
`ssr.py` **defaults to OpenAI `text-embedding-3-small`** (closest to the paper; sharpest
distribution spread). It reads `OPENAI_API_KEY` from the environment or a local `.env` file
(auto-loaded). If no key is found it **falls back to local** static embeddings
(`minishlab/potion-base-8M`, no torch, no key, free) with a printed notice — good enough for
ranking, just lower discrimination. Force local explicitly with `--backend local`.

## Files
- `scripts/ssr.py` — the SSR scoring engine (embeddings → Likert PMFs → ranked report).
- `scripts/anchors.json` — 6 generic, domain-independent adoption/WTP anchor sets (1–5).
- `references/methodology.md` — the paper's method, math, and fidelity caveats in depth.
- `references/workflow-example.md` — how to generate reactions with parallel persona agents.

## Caveats
- SSR validates at the **aggregate** level. A single response's Likert is noisy; trust
  distributions over individuals.
- Fidelity depends on persona realism. Garbage personas → confident garbage.
- The impersonating model carries its own biases; results lean toward "what an LLM thinks
  segment X would say," which is a prior, not ground truth. Use to **prioritize and falsify
  hypotheses**, then validate winners with real users.
