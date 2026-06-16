# Generating reactions with parallel persona agents (rigorous mode)

For respondent **independence** (the methodologically correct way), generate each persona's
free-text reactions in its own agent context instead of authoring them all in one chat. This
requires the user to opt into multi-agent orchestration (a Workflow). Sketch:

```js
export const meta = {
  name: 'ssr-elicit',
  description: 'Elicit independent free-text concept reactions, one agent per persona',
  phases: [{ title: 'Elicit' }],
}

// args: { personas: [...], concepts: [...] }
const { personas, concepts } = args

const REACTION_SCHEMA = {
  type: 'object',
  properties: {
    reactions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          concept: { type: 'string' },
          response_text: { type: 'string' },
        },
        required: ['concept', 'response_text'],
      },
    },
  },
  required: ['reactions'],
}

phase('Elicit')
const all = await parallel(personas.map(p => () =>
  agent(
    `You ARE this person — react in the first person, in your own voice:\n` +
    `${JSON.stringify(p, null, 2)}\n\n` +
    `For EACH concept below, answer in 2–4 sentences: "How likely would you be to ` +
    `adopt this and pay for it, and why?" Be honest, specific to your situation, and ` +
    `let your skepticism or enthusiasm show. Do NOT give a number or rating — words only.\n\n` +
    `Concepts:\n${concepts.map((c, i) => `${i + 1}. ${c.id}: ${c.description}`).join('\n')}`,
    { label: `persona:${p.persona_id}`, schema: REACTION_SCHEMA }
  ).then(r => (r?.reactions || []).map(x => ({
    persona_id: p.persona_id, segment: p.segment,
    concept: x.concept, response_text: x.response_text,
  })))
))

return all.filter(Boolean).flat()  // -> write to responses.json, then run ssr.py
```

Scale N by repeating personas with varied seeds (vary the prompt/label per replica). Then feed
`responses.json` to `scripts/ssr.py` exactly as in the inline path.

**Important:** only run a Workflow when the user has explicitly opted into multi-agent
orchestration. Otherwise author reactions inline.
