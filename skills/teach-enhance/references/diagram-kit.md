# Unified inline-SVG diagram kit

Every lesson diagram is a hand-built inline SVG that follows ONE kit, so the whole course
reads as one visual family. The dark-mode recolor in `course.css` keys off these exact
colours and gradient-id prefixes — **stick to them** or dark mode won't adapt that diagram.

## Frame
- One `<figure>` containing one `<svg>` and a `<figcaption>` (≤ ~18 words, no citation marker).
- `course.css` frames every `figure:has(> svg)` as a theme-coloured plate (warm paper in light
  mode, dark in dark mode) — do **not** set a background inside the SVG.

## Root
```html
<svg viewBox="0 0 680 H" width="100%" role="img" aria-label="…">  <!-- H 140–240; ~18px outer margin -->
```
`viewBox` width is always **680**. Pick H to fit.

## Defs (paste at the top; replace {N} with the lesson number so ids are unique on the page)
```html
<defs>
  <linearGradient id="gPlan{N}"    x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fdf4d9"/><stop offset="1" stop-color="#f6e6af"/></linearGradient>
  <linearGradient id="gBuild{N}"   x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eef4fc"/><stop offset="1" stop-color="#d8e6f7"/></linearGradient>
  <linearGradient id="gVerify{N}"  x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3ecfa"/><stop offset="1" stop-color="#e5d8f2"/></linearGradient>
  <linearGradient id="gShip{N}"    x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e6f5ec"/><stop offset="1" stop-color="#cfead9"/></linearGradient>
  <linearGradient id="gNeutral{N}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#f0ede4"/></linearGradient>
  <filter id="sh{N}" x="-20%" y="-25%" width="140%" height="150%"><feDropShadow dx="0" dy="1.5" stdDeviation="1.6" flood-color="#1b1b2e" flood-opacity="0.12"/></filter>
  <marker id="arw{N}" markerWidth="10" markerHeight="10" refX="6.5" refY="3" orient="auto"><path d="M0.6,0.6 L6.6,3 L0.6,5.4" fill="none" stroke="#7d8aa6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></marker>
</defs>
```

## Box (height 52, rx 11). Pick the gradient that matches the lifecycle phase; `gNeutral` otherwise.
```html
<rect x="" y="" width="" height="52" rx="11" fill="url(#gBuild{N})" stroke="#2f6db0" stroke-width="1.3" filter="url(#sh{N})"/>
<text x="cx" y="" text-anchor="middle" font-size="13"   font-weight="600" fill="#1b1b1a">Title</text>
<text x="cx" y="" text-anchor="middle" font-size="10.5"                   fill="#4a4a46">subtitle</text>
```
Stroke colour by phase — **use these exact hexes**:
`plan #b07d18 · build #2f6db0 · verify #7a4ea8 · ship #2f8a5b · neutral #b8b2a4`.

## Connector (prefer gentle curves; always end with the arrowhead)
```html
<path d="M x1 y1 C cx1 cy1 cx2 cy2 x2 y2" fill="none" stroke="#7d8aa6" stroke-width="1.6" marker-end="url(#arw{N})"/>
```

## Labels
Section/axis labels: `<text font-size="10" fill="#807d75">…</text>` (uppercase headers in the phase
colour). Micro text 9px. Title text fill is `#1b1b1a`; subtitle/secondary is `#4a4a46`.

## Rules
- Only the palette tints/strokes above. No external refs/images/scripts/`<style>`.
- Keep it legible and uncrowded; consistent 52px box height and ~16px gaps.
- Dark mode is handled entirely by `course.css` attribute selectors (`[fill^="url(#gBuild"]`,
  `text[fill="#1b1b1a"]`, `[stroke="#2f6db0"]`, …). If you invent new colours, add a matching
  dark-mode rule or the diagram will look light-on-dark.
