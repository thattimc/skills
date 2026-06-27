# Content-design patterns

The per-lesson structure the enhancement layer assumes. The runtime JS (`reading.js`,
`content.js`, `speak.js`) is markup-driven, so following these classes is what makes the
features work. All styling lives in `assets/course.css`.

## Lesson skeleton (top → bottom)
```html
<nav class="masthead"> … breadcrumb + "Lesson NN" </nav>
<p class="eyebrow">Section · subhook <span class="phase phase--build">Build</span></p>   <!-- phase chip optional -->
<h1>Title</h1>
<p class="subtitle">one punchy hook sentence</p>
<p class="lead">opening paragraph</p>

<!-- TL;DR box, right after the lead -->
<div class="tldr"><span class="tldr__icon"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 2 4 14h6l-1 8 9-12h-6z"/></svg></span>
  <div class="tldr__body"><b>In 20 seconds</b> 1–2 sentence summary: the core point + the action.</div></div>

<h2>Section</h2> … prose, callouts, one <figure> diagram, a <pre><code> or <table> worked example …

<!-- Worked-example label immediately before the lesson's primary artifact -->
<p class="worked-label">Worked example</p>
<pre><code>…</code></pre>

<!-- Mid-lesson "Quick check" quiz, right after the section it tests -->
<div class="quiz" data-answer="K"><p class="quiz__kicker">Quick check</p> … </div>

… more sections …

<!-- End "Retrieval check" quiz -->
<div class="quiz" data-answer="K"><p class="quiz__kicker">Retrieval check</p> … </div>

<!-- Recap, immediately before the footer -->
<div class="recap"><b>Recap</b><ul><li>…</li><li>…</li></ul></div>

<div class="lesson-footer"> source callout · .ask "Ask your teacher" · <ol class="ref-list"> · .pager </div>
```

## Retrieval (quizzes)
- Two `.quiz` widgets per lesson: ONE **mid-lesson** ("Quick check", placed right after the
  section it tests) and ONE at the **end** ("Retrieval check"). Retrieval at the point of
  learning + a recap pass.
- Markup: `<div class="quiz" data-answer="K">` (K = 0-based index of the correct `<li class="quiz__opt">`),
  a `.quiz__kicker`, a `.quiz__stem`, exactly three `.quiz__opt`, a `.quiz__feedback`.
- **Rule:** the three options must be ~equal in word AND character count — no length tell.

## Read-aloud (speak.js)
- Local **neural voice (Kokoro-82M)** in-browser; floating 🔊 control bottom-right with a
  voice + speed gear menu. Highlights the current block (`.is-speaking`) and word (`.is-word`).
- Reads prose; skips `.masthead, pre, figure, .quiz, .lesson-footer, .note, table`.
- First click downloads ~80 MB once (cached); inference is local (WebGPU / WASM). Falls back
  to the OS speech voice if the model can't load (offline / `file://`). Needs http(s), not `file://`.

## Reading aids
- `reading.js`: top **progress bar**, a `~N min` **read-time** appended to the masthead, and a
  **focus mode** toggle (bottom-left) that dims everything but the line nearest centre
  (`body.focus-mode .focusable` / `.in-focus`).
- `content.js`: wraps `<table>` in `.table-wrap` (mobile scroll); adds **glossary tooltips**
  (first use of a curated term → dotted underline + hover definition, `.gloss`); builds an
  "On this page" `<details class="toc">` for lessons with ≥4 `<h2>`. The term→definition map is
  the `DEFS` object at the top of `content.js` — edit it to match the course's glossary.

## Syntax highlighting
- Any lesson with a `<pre>` loads `highlight.min.js` + `code-highlight.js` (auto-detect).
  The token theme is palette-matched in `course.css` (`.hljs-*`).

## Required CSS variables
The components assume the base palette variables from `course.css`:
`--paper --ink --ink-soft --ink-faint --rule --rule-soft --accent --accent-dim`,
the phase colours `--plan --build --verify --ship`, and `--serif --sans --mono`.
If you bring your own stylesheet, define these (and the dark `prefers-color-scheme` overrides).

## Callouts available
`.callout--idea` (key idea) · `.callout--warn` (trap/pitfall) · `.callout--try` (do this) ·
`.callout--source` (watch/read this). Plus `.phase--{plan,build,verify,ship}` chips and margin
`.note` (Tufte sidenotes that sit in the right gutter on wide screens, inline below).
