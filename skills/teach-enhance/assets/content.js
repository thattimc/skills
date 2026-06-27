/* Content-design enhancements applied at runtime (no per-lesson markup needed):
   1) wrap tables so they scroll on narrow screens,
   2) glossary tooltips on the first use of key terms (dotted underline + definition on hover),
   3) a quiet "On this page" contents for longer lessons. */
(function () {
  var wrap = document.querySelector('.wrap'); if (!wrap) return;

  /* 1 — mobile-safe tables */
  wrap.querySelectorAll('table').forEach(function (t) {
    if (t.parentNode && t.parentNode.classList && t.parentNode.classList.contains('table-wrap')) return;
    if (t.closest('.tldr, .recap')) return;
    var d = document.createElement('div'); d.className = 'table-wrap';
    t.parentNode.insertBefore(d, t); d.appendChild(t);
  });

  /* 2 — glossary tooltips (first occurrence of each term) */
  var DEFS = {
    "human–agent responsibility model": "An explicit map of which decisions an agent may make autonomously and which require a human.",
    "productivity paradox": "AI speeds up coding but not delivery — the saved time is reabsorbed by the lifecycle's other phases.",
    "spec-driven development": "Turning intent into an explicit spec an agent follows, scoped to small, well-defined tasks.",
    "ground-truth dataset": "A curated set of inputs with expected outputs, used to benchmark accuracy, hallucination rate, and cost.",
    "continuous evaluation": "Ongoing measurement of an agent's reasoning, safety, and tool use against a ground-truth dataset — replacing one-time pass/fail tests.",
    "ubiquitous language": "One shared vocabulary used in conversation, code, and prompts, derived from a single domain model.",
    "over-delegation": "Handing AI a big, ambiguous goal so unstated decisions and unread code pile up and review becomes the bottleneck.",
    "under-delegation": "Keeping all planning and design with the human and using AI only for small slices, so the heavy lifting stays manual.",
    "outcome metrics": "Delivery-health measures (lead time, change-failure rate, maintainability, complexity) instead of activity like lines of code.",
    "non-determinism": "An agent's output depends on prompt, context, model, and tools, so identical inputs need not produce identical outputs.",
    "shallow module": "A unit with a complex interface but little hidden — the opposite of a deep module.",
    "design concept": "The shared, not-yet-written idea of what is being built, held in common before any plan or code (Brooks).",
    "feedback loop": "A mechanism (types, tests, browser, logs) that tells you quickly whether the code is right; the rate of feedback is your speed limit.",
    "agent harness": "The system around the model — sub-agents, tools, MCP, skills, memory — that makes a raw model dependable.",
    "deep module": "A unit with a simple interface hiding a powerful implementation (Ousterhout).",
    "context rot": "Output degrades as the context window fills with irrelevant information, spreading the model's attention thin.",
    "vibe coding": "Generating code from loose prompts without reviewing or owning the result — fine for throwaway, risky at scale.",
    "gray box": "A deep module you design and test from the outside while delegating its implementation to AI — for non-critical modules.",
    "ADLC": "Agentic Development Life Cycle — a lifecycle for building non-deterministic agentic products.",
    "TDD": "Test-Driven Development: write a failing test, make it pass, then refactor; forces small, verifiable steps."
  };
  var terms = Object.keys(DEFS).sort(function (a, b) { return b.length - a.length; });
  var SKIP = 'a, h1, h2, h3, pre, code, .tldr, .recap, .quiz, .masthead, .lesson-footer, .gloss, figure, .callout__label, .toc, .worked-label';
  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  terms.forEach(function (term) {
    var re = new RegExp('(^|[^\\w-])(' + esc(term) + ')(?![\\w-])', 'i');
    var w = document.createTreeWalker(wrap, NodeFilter.SHOW_TEXT, null), node;
    while ((node = w.nextNode())) {
      if (node.parentNode.closest(SKIP)) continue;
      var m = re.exec(node.nodeValue); if (!m) continue;
      var i = m.index + m[1].length, val = node.nodeValue;
      var a = document.createElement('span'); a.className = 'gloss'; a.title = DEFS[term]; a.textContent = val.slice(i, i + term.length);
      var frag = document.createDocumentFragment();
      if (val.slice(0, i)) frag.appendChild(document.createTextNode(val.slice(0, i)));
      frag.appendChild(a);
      if (val.slice(i + term.length)) frag.appendChild(document.createTextNode(val.slice(i + term.length)));
      node.parentNode.replaceChild(frag, node);
      break;
    }
  });

  /* 3 — "On this page" for longer lessons */
  var h2s = Array.prototype.filter.call(wrap.querySelectorAll('h2'), function (h) { return !h.closest('.lesson-footer'); });
  h2s.forEach(function (h, i) { if (!h.id) h.id = 'sec-' + (i + 1); });
  if (h2s.length >= 4) {
    var anchor = wrap.querySelector('.tldr') || wrap.querySelector('.lead');
    if (anchor) {
      var det = document.createElement('details'); det.className = 'toc';
      var sum = document.createElement('summary'); sum.textContent = 'On this page'; det.appendChild(sum);
      var ul = document.createElement('ul');
      h2s.forEach(function (h) { var li = document.createElement('li'); var a = document.createElement('a'); a.href = '#' + h.id; a.textContent = h.textContent.replace(/\s+/g, ' ').trim(); li.appendChild(a); ul.appendChild(li); });
      det.appendChild(ul); anchor.parentNode.insertBefore(det, anchor.nextSibling);
    }
  }
})();
