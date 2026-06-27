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

Teach someone a topic over multiple sessions by building them a beautiful, self-hosted HTML
course. Knowledge, skill, and experience are one thing here: each lesson is at once a grounded
pedagogical unit *and* a finished, polished artifact. The pedagogy is the `/teach` method (by
Matt Pocock, MIT — read `references/teach-method/teach-method.md` and its format files first);
this skill *is* that method, realized in a fixed house style so nothing has to be polished after
the fact.

## The teaching workspace
Treat the current directory as a **stateful workspace** that holds the learner's progress:

- `MISSION.md` — the real reason the user is learning; ground every decision in it. Interview
  first if it's unclear (a bad mission is worse than none).
- `RESOURCES.md` — high-trust sources. Draw all knowledge from here; never teach from parametric
  guesses, and cite liberally.
- `lessons/NNNN-slug.html` — the lessons (see below).
- `GLOSSARY.md` — the course's controlled vocabulary · `reference/*.html` — printable cards ·
  `learning-records/*.md` — ADRs for what the learner has learned (drives the next session's
  zone of proximal development).
- `assets/` — the shared design system + components every lesson links, so the course looks like
  one thing, not a pile of one-offs.

Pace each lesson to the learner's **zone of proximal development** from the learning records:
challenged just enough, one tangible win, tied to the mission.

## What a lesson is
One short, self-contained HTML file that teaches **one tightly-scoped thing** in the learner's
ZPD, grounded in `RESOURCES.md` — and is built to a fixed skeleton that carries the experience,
so the teaching and the polish are the same act. Every lesson has, in order:

> masthead · eyebrow (+ phase chip) · **h1** · subtitle · lead · **TL;DR box** · 2–4 sections
> (with callouts, a kit **diagram**, and a labeled **Worked example**) · a **mid-lesson Quick
> check** quiz + an **end Retrieval check** quiz · a **Recap box** · footer (recommended source ·
> "Ask your teacher" · cited references · prev/next pager).

By linking the shared `assets/`, every lesson also inherits — for free, at runtime — a **local
neural read-aloud** (Kokoro-82M in-browser, with word-highlighting and a voice/speed picker), a
scroll **progress bar**, a **focus mode** that dims all but the current line, a `~N min`
read-time, **glossary tooltips** on first term use, mobile-safe table scrolling, an "On this
page" contents on longer lessons, and palette-matched **syntax highlighting**. The two specs
that define the skeleton and the visuals are `references/content-patterns.md` (every class the
markup and JS expect) and `references/diagram-kit.md` (the one inline-SVG kit — gradient tints,
52px boxes, curved connectors, one arrowhead — that themes light/dark automatically).

## Workflow
1. **Mission.** Establish/confirm `MISSION.md` (interview if needed) and set up the workspace.
2. **Sources.** Populate `RESOURCES.md` with high-trust references; ground every claim there.
3. **Lessons.** Build each lesson to the skeleton above — in the learner's ZPD, with the two
   quizzes, a worked example, a kit diagram, a TL;DR, and a recap — keeping the glossary,
   reference cards, and learning records current as understanding deepens.
4. **Wire it in.** Run `python3 scripts/apply.py <workspace>` to copy the components into
   `assets/`, add the `<script>` includes to every `lessons/*.html`, and vendor the highlighter.
   (If the workspace already had a `course.css`, merge in this skill's `assets/course.css`.) Then
   tune the glossary tooltips via the `DEFS` map at the top of `assets/content.js`.
5. **Serve over http** (not `file://`) so the neural voice can fetch its model, e.g.
   `python3 -m http.server 8137 --directory <workspace>`, and open a lesson.

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
