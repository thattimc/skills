---
name: teach-enhance
description: >
  Teach a topic over multiple sessions AND ship it as a polished, self-hosted HTML course in
  one command — no separate /teach call. Runs the full teaching methodology (mission-first
  grounding, a stateful workspace of lessons + glossary + reference cards + learning records,
  zone-of-proximal-development pacing) and produces every lesson with the enhanced experience
  baked in: a local neural read-aloud button (Kokoro-82M, in-browser) with word-highlighting
  and a voice/speed picker, ADHD-friendly reading aids (progress bar, focus mode, read-time,
  glossary tooltips, mobile-safe tables, on-this-page TOC), offline syntax highlighting, a
  unified light/dark inline-SVG diagram kit, and content-design patterns (TL;DR box, mid-lesson
  Quick check + end Retrieval check, labeled Worked examples, Recap box). Triggers: "teach me
  X", "build a course on X", "I want to learn X over time", "make me lessons on …", plus
  "enhance / polish my course", "add the read-aloud button / focus mode / TL;DR".
disable-model-invocation: true
argument-hint: "What would you like to learn or build a course on?"
---

# Teach Enhance

The teaching skill **with the polished experience built in**. `/teach-enhance` is a superset of
`/teach`: it runs the same multi-session teaching methodology, but every lesson it produces
already ships with the read-aloud voice, reading aids, unified diagrams, and content patterns —
so you only ever call this one command.

It has two halves, applied together:

## 1 — Teach (the methodology)
The pedagogy is the bundled `/teach` method (by Matt Pocock, MIT — see
`references/teach-method/NOTICE.md`). **Read `references/teach-method/teach-method.md` first**,
plus the format files it points to (`MISSION-FORMAT.md`, `RESOURCES-FORMAT.md`,
`LEARNING-RECORD-FORMAT.md`, `GLOSSARY-FORMAT.md`). In short:

- Treat the current directory as a **stateful teaching workspace**. Ground everything in
  `MISSION.md` (the real reason the user is learning) — interview first if it's unclear.
- Gather knowledge from **trusted sources** into `RESOURCES.md`; never teach from parametric
  guesses. Cite liberally.
- Produce short, self-contained **lessons** in `lessons/NNNN-slug.html`, each a single tangible
  win in the user's zone of proximal development. Maintain `GLOSSARY.md` (controlled vocabulary),
  printable reference cards in `reference/`, and `learning-records/` (ADRs for what was learned).
- Reuse components from `assets/`; lessons should look like one course, not a pile of one-offs.

## 2 — Enhance (baked into every lesson)
Don't bolt the experience on at the end — build lessons in the enhanced house style from the
start, using this skill's assets and specs:

- **Design system & components.** Link `assets/course.css` (the full design system) and include
  the JS components (`quiz.js`, `speak.js`, `reading.js`, `content.js`, `code-highlight.js`).
  Wire them with `scripts/apply.py` (idempotent — also vendors `highlight.min.js`).
- **Lesson skeleton & content patterns** — `references/content-patterns.md`: masthead · eyebrow
  (+phase chip) · h1 · subtitle · lead · **TL;DR box** · sections with callouts · a **diagram** ·
  a labeled **Worked example** · a **mid-lesson Quick check** + an **end Retrieval check** ·
  a **Recap box** · footer (source callout · "Ask your teacher" · ref-list · pager).
- **Diagrams** — `references/diagram-kit.md`: one inline-SVG kit (gradient tints, 52px boxes,
  curved connectors, one arrowhead) that themes to light/dark automatically.
- **For free at runtime:** the 🔊 local neural read-aloud (with word highlighting + voice/speed
  picker), the scroll progress bar, focus mode, read-time, glossary tooltips, mobile table
  scroll, on-this-page TOC, and palette-matched syntax highlighting.

## Workflow
1. **Mission.** Establish/confirm `MISSION.md` (interview if needed). Set up the workspace.
2. **Sources.** Populate `RESOURCES.md` with high-trust references; ground all claims there.
3. **Lessons.** Build each lesson in the enhanced skeleton (patterns above), in the user's ZPD,
   with two quizzes (mid + end), a worked example, a kit diagram, a TL;DR, and a recap. Keep the
   glossary, reference cards, and learning records current.
4. **Wire the experience.** Run `python3 scripts/apply.py <workspace>` to copy components, add the
   script includes to every `lessons/*.html`, and vendor the highlighter. (If the workspace
   already has a `course.css`, merge in the enhance layers from this skill's `assets/course.css`.)
5. **Serve over http** (not `file://`) so the neural voice can fetch its model:
   `python3 -m http.server 8137 --directory <workspace>` and open a lesson.
6. **Tune** the glossary tooltips: edit the `DEFS` map at the top of `assets/content.js`.

## Files
- `assets/` — `course.css` (full design system) + `quiz.js`, `speak.js`, `reading.js`,
  `content.js`, `code-highlight.js`. (`highlight.min.js` is vendored by `apply.py`.)
- `scripts/apply.py` — wires the components into a workspace.
- `references/teach-method/` — the bundled `/teach` methodology + format files (MIT; see NOTICE).
- `references/content-patterns.md` — the per-lesson skeleton + every class the JS expects.
- `references/diagram-kit.md` — the unified inline-SVG kit (colours/ids the dark mode keys off).

## Caveats
- **Kokoro read-aloud** downloads an ~80 MB model on first use (cached after); best on
  Chrome/WebGPU, slower on Safari/WASM; offline or `file://` → it falls back to the OS voice.
- **Dark-mode diagrams** recolor via CSS attribute selectors keyed to the kit's exact colours/ids
  — keep diagrams to `diagram-kit.md` or they won't adapt.
- The components are markup-driven; if you rename lesson classes, update the JS selectors.
- This skill is **user-invoked** (`/teach-enhance`); it does not auto-trigger.
