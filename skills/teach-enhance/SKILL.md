---
name: teach-enhance
description: >
  Layer the polished reading + media experience onto a course built with the /teach skill:
  a local neural read-aloud button (Kokoro-82M, in-browser) with word-highlighting and a
  voice/speed picker, ADHD-friendly reading aids (scroll progress bar, focus mode, read-time,
  glossary tooltips, mobile-safe tables, on-this-page TOC), offline syntax highlighting, a
  unified inline-SVG diagram kit with light/dark theming, and content-design patterns (TL;DR
  box, mid-lesson "Quick check" + end "Retrieval check", labeled Worked examples, Recap box).
  Use AFTER /teach has produced lessons/*.html + assets/course.css. Triggers: "enhance my teach
  course", "add the speak/read-aloud button", "polish the lessons", "make the diagrams a set",
  "add focus mode / progress bar / TL;DR / recap", "apply the course design system".
---

# Teach Enhance

A reusable polish layer for `/teach` courses. `/teach` produces the pedagogy (lessons, glossary,
references); this skill adds the **experience** — read-aloud, reading aids, syntax highlighting,
a unified diagram system, and the per-lesson content patterns — so any course gets the same
fine-tuned feel. Everything is vanilla CSS + dependency-free JS that works offline.

## When to use
- A `/teach` workspace already exists (`lessons/*.html`, `assets/course.css`).
- You want the read-aloud button, focus mode, progress bar, glossary tooltips, consistent
  diagrams, TL;DR/recap/worked-example structure, or the whole package.

Do **not** use it to author lesson *content* — that's `/teach`. This is the presentation layer.

## What it adds
- **Read-aloud (`speak.js`)** — local neural voice (Kokoro-82M) in the browser; floating 🔊
  control with a voice + speed gear menu; highlights the current block and word as it reads;
  falls back to the OS voice offline.
- **Reading aids (`reading.js`, `content.js`)** — top progress bar, `~N min` read-time, a
  focus mode that dims all but the current line, glossary tooltips on first term use,
  mobile-safe table scroll, and an "On this page" contents on longer lessons.
- **Syntax highlighting (`highlight.min.js` + `code-highlight.js`)** — palette-matched, offline.
- **Unified diagrams** — one inline-SVG kit (gradient tints, 52px boxes, curved connectors,
  one arrowhead) that theme to light/dark. See `references/diagram-kit.md`.
- **Content patterns** — TL;DR box, mid-lesson Quick check + end Retrieval check, labeled
  Worked examples, Recap box. See `references/content-patterns.md`.

## How to apply
1. **Wire in the components** (idempotent):
   ```bash
   python3 scripts/apply.py /path/to/teach-workspace      # defaults to cwd
   ```
   This copies the JS components into `assets/`, copies `course.css` if you have none (else
   leave yours and merge the enhance layers), vendors `highlight.min.js`, and adds the
   `<script>` includes before `</body>` in every `lessons/*.html`.
2. **Adopt the design system** — if the workspace already had a `course.css`, merge in the
   enhance layers from this skill's `assets/course.css` (read-aloud, reading aids, code theme,
   diagram polish + dark recolor, `.tldr` / `.recap` / `.worked-label` / `.gloss` / `.table-wrap`
   / `.toc`). It assumes the base palette variables — see `references/content-patterns.md`.
3. **Tune the glossary tooltips** — edit the `DEFS` map at the top of `assets/content.js` to the
   course's actual terms + one-line definitions.
4. **Apply the content patterns per lesson** — add the TL;DR box, move one quiz mid-lesson,
   label the worked example, add the Recap, and (re)draw diagrams with the kit. For a whole
   course this is best done as a small per-lesson workflow; the two `references/` files are the
   exact specs to give each agent.
5. **Serve over http** (not `file://`) so the neural voice can fetch its model:
   `python3 -m http.server 8137 --directory /path/to/teach-workspace`.

## Files
- `assets/` — `course.css` (full design system), `quiz.js`, `speak.js`, `reading.js`,
  `content.js`, `code-highlight.js`. (`highlight.min.js` is vendored by `apply.py`.)
- `scripts/apply.py` — wires the bundle into a workspace.
- `references/diagram-kit.md` — the unified inline-SVG kit (colours/ids the dark mode keys off).
- `references/content-patterns.md` — the per-lesson skeleton + every class the JS expects.

## Caveats
- **Kokoro download:** the neural voice fetches an ~80 MB model on first use (cached after);
  best on Chrome/WebGPU, slower on Safari/WASM. Offline or `file://` → it falls back to the OS
  voice automatically.
- **Dark-mode diagrams** recolor via CSS attribute selectors keyed to the kit's exact hexes and
  `url(#g…)` gradient ids — diagrams that stray from the kit won't adapt. Keep to `diagram-kit.md`.
- The components are markup-driven; if you change the lesson class names, update the selectors
  in the JS to match.
