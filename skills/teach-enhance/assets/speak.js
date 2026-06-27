/* Read the lesson aloud with a local NEURAL voice (Kokoro-82M TTS, in-browser).
   First click downloads the ~80MB model once (cached after); inference runs locally
   (WebGPU, or WASM fallback). Falls back to the OS speech voice if the model can't load.
   Highlights the current block AND word; voice + speed picker in the gear menu. */
(function () {
  var synthOK = 'speechSynthesis' in window;
  var chunks = [], state = 'idle', engine = null, tried = false, keep = null, raf = null, cur = null, curIdx = 0;
  var controls, primary, stopBtn, pctEl, tts = null, voice = 'af_heart', rate = 1, cache = [], audioEl = null;
  try { var sv = localStorage.getItem('aisdlc-voice'); if (sv) voice = sv; var sr = parseFloat(localStorage.getItem('aisdlc-rate')); if (sr) rate = sr; } catch (e) {}

  var VOICES = [
    ['American — female', [['af_heart', 'Heart'], ['af_bella', 'Bella'], ['af_nova', 'Nova']]],
    ['American — male', [['am_michael', 'Michael'], ['am_fenrir', 'Fenrir'], ['am_puck', 'Puck']]],
    ['British — female', [['bf_emma', 'Emma'], ['bf_isabella', 'Isabella']]],
    ['British — male', [['bm_george', 'George'], ['bm_fable', 'Fable']]]
  ];
  var SPEEDS = [0.75, 1, 1.25, 1.5, 2];

  var IC = {
    listen: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4z" fill="currentColor"/><path d="M16 9a4 4 0 0 1 0 6M19 6.5a7 7 0 0 1 0 11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    pause:  '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="7" y="5" width="3.4" height="14" rx="1.5"/><rect x="13.6" y="5" width="3.4" height="14" rx="1.5"/></svg>',
    play:   '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.2v13.6a1 1 0 0 0 1.52.86l10.5-6.8a1 1 0 0 0 0-1.72L9.52 4.34A1 1 0 0 0 8 5.2z"/></svg>',
    stop:   '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="3.2"/></svg>',
    spin:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true" class="speak-spin"><path d="M12 3a9 9 0 1 0 9 9"/></svg>',
    gear:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="20" y2="16"/><circle cx="9" cy="8" r="2.3" fill="var(--paper)"/><circle cx="15" cy="16" r="2.3" fill="var(--paper)"/></svg>'
  };
  function setUI(s) {
    controls.classList.toggle('is-active', s === 'playing' || s === 'paused');
    controls.classList.toggle('is-playing', s === 'playing');
    controls.classList.toggle('is-loading', s === 'loading');
    primary.innerHTML = IC[s === 'idle' ? 'listen' : s === 'loading' ? 'spin' : s === 'playing' ? 'pause' : 'play'];
    primary.setAttribute('aria-label', s === 'playing' ? 'Pause' : s === 'paused' ? 'Resume' : s === 'loading' ? 'Loading voice' : 'Listen to this lesson');
  }

  function collect() {
    var wrap = document.querySelector('.wrap'); if (!wrap) return [];
    var skip = '.masthead, pre, figure, .quiz, .lesson-footer, .note, table, script, style, svg';
    var out = [];
    wrap.querySelectorAll('h1, h2, h3, p, li, blockquote').forEach(function (el) {
      if (el.closest(skip)) return;
      if (!(el.textContent || '').trim()) return;
      out.push({ el: el });
    });
    return out;
  }

  /* ---- word wrapping (text nodes only -> keeps links/emphasis/citations intact) ---- */
  function wrapWords(el) {
    var spans = [], nodes = [], w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
    while ((n = w.nextNode())) nodes.push(n);
    nodes.forEach(function (tn) {
      if (!/\S/.test(tn.nodeValue)) return;
      var parts = tn.nodeValue.split(/(\s+)/), frag = document.createDocumentFragment();
      parts.forEach(function (p) {
        if (p === '') return;
        if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(' ')); return; }
        var s = document.createElement('span'); s.className = 'w'; s.textContent = p;
        frag.appendChild(s); spans.push({ span: s, text: p });
      });
      tn.parentNode.replaceChild(frag, tn);
    });
    return spans;
  }
  function prep(i) {
    var c = chunks[i]; if (c.words) return c;
    c.words = wrapWords(c.el); c.offsets = []; var off = 0;
    c.words.forEach(function (x, k) { c.offsets[k] = off; off += x.text.length + 1; });
    c.total = Math.max(1, off - 1);
    c.text = c.words.map(function (x) { return x.text; }).join(' ') || (c.el.textContent || '').trim();
    return c;
  }
  function wordAt(c, ch) { var k = 0; for (var j = 0; j < c.offsets.length; j++) { if (c.offsets[j] <= ch) k = j; else break; } return k; }
  function setWord(c, k) {
    if (!c || !c.words) return; if (c._cur === k) return;
    if (c._cur != null && c.words[c._cur]) c.words[c._cur].span.classList.remove('is-word');
    c._cur = k; if (c.words[k]) c.words[k].span.classList.add('is-word');
  }
  function clearWord(c) { if (c && c._cur != null && c.words[c._cur]) c.words[c._cur].span.classList.remove('is-word'); if (c) c._cur = null; }
  function clearBlocks() { chunks.forEach(function (c) { c.el.classList.remove('is-speaking'); clearWord(c); }); }
  function enterBlock(i) { clearBlocks(); cur = prep(i); curIdx = i; cur.el.classList.add('is-speaking'); cur.el.scrollIntoView({ behavior: 'smooth', block: 'center' }); return cur; }

  /* ---- Kokoro (neural) engine ---- */
  function pcmToWav(f32, r) {
    var len = f32.length, buf = new ArrayBuffer(44 + len * 2), dv = new DataView(buf), i, o;
    function ws(p, s) { for (var k = 0; k < s.length; k++) dv.setUint8(p + k, s.charCodeAt(k)); }
    ws(0, 'RIFF'); dv.setUint32(4, 36 + len * 2, true); ws(8, 'WAVE'); ws(12, 'fmt '); dv.setUint32(16, 16, true);
    dv.setUint16(20, 1, true); dv.setUint16(22, 1, true); dv.setUint32(24, r, true); dv.setUint32(28, r * 2, true);
    dv.setUint16(32, 2, true); dv.setUint16(34, 16, true); ws(36, 'data'); dv.setUint32(40, len * 2, true);
    o = 44; for (i = 0; i < len; i++) { var x = Math.max(-1, Math.min(1, f32[i])); dv.setInt16(o, x < 0 ? x * 0x8000 : x * 0x7fff, true); o += 2; }
    return new Blob([buf], { type: 'audio/wav' });
  }
  async function initKokoro() {
    setUI('loading'); pctEl.textContent = '';
    var mod = await import('https://esm.sh/kokoro-js@1.2.1');
    var device = (typeof navigator !== 'undefined' && navigator.gpu) ? 'webgpu' : 'wasm';
    var dtype = device === 'webgpu' ? 'fp32' : 'q8';
    tts = await mod.KokoroTTS.from_pretrained('onnx-community/Kokoro-82M-v1.0-ONNX', {
      dtype: dtype, device: device,
      progress_callback: function (p) { if (p && p.status === 'progress' && typeof p.progress === 'number') pctEl.textContent = Math.round(p.progress) + '%'; }
    });
    audioEl = new Audio();
  }
  async function genK(i) {
    if (i >= chunks.length) return null;
    if (cache[i]) return cache[i];
    var a = await tts.generate(prep(i).text, { voice: voice });
    cache[i] = (a && a.audio) ? pcmToWav(a.audio, a.sampling_rate || a.samplingRate || 24000) : a.toBlob();
    return cache[i];
  }
  function trackWords() {
    cancelAnimationFrame(raf);
    (function loop() {
      if (state !== 'playing' || !audioEl || !cur) return;
      if (audioEl.duration) setWord(cur, wordAt(cur, (audioEl.currentTime / audioEl.duration) * cur.total));
      raf = requestAnimationFrame(loop);
    })();
  }
  async function playK(i) {
    if (state !== 'playing') return;
    if (i >= chunks.length) { stop(); return; }
    var c = enterBlock(i), blob;
    try { blob = await genK(i); } catch (e) { stop(); return; }
    if (state !== 'playing' || !blob) return;
    audioEl.src = URL.createObjectURL(blob);
    audioEl.playbackRate = rate;
    audioEl.onended = function () { clearWord(c); if (state === 'playing') playK(i + 1); };
    audioEl.play(); trackWords();
    genK(i + 1);
  }

  /* ---- OS speech fallback (real word-boundary events) ---- */
  function playS(i) {
    if (state !== 'playing') return;
    if (i >= chunks.length) { stop(); return; }
    var c = enterBlock(i);
    var u = new SpeechSynthesisUtterance(c.text);
    u.lang = document.documentElement.lang || 'en'; u.rate = rate;
    u.onboundary = function (e) { if (e.charIndex != null) setWord(c, wordAt(c, e.charIndex)); };
    u.onend = function () { clearWord(c); if (state === 'playing') playS(i + 1); };
    window.speechSynthesis.speak(u);
  }

  async function start() {
    chunks = collect(); if (!chunks.length) return;
    state = 'playing';
    if (!tried) { tried = true; try { await initKokoro(); engine = 'kokoro'; } catch (e) { engine = synthOK ? 'speech' : null; } }
    if (state !== 'playing') return;
    setUI('playing');
    if (engine === 'kokoro') { cache = []; playK(0); }
    else if (engine === 'speech') {
      window.speechSynthesis.cancel(); playS(0);
      keep = setInterval(function () { if (state === 'playing' && !window.speechSynthesis.paused) window.speechSynthesis.resume(); }, 10000);
    } else { stop(); }
  }
  function stop() {
    state = 'idle'; cancelAnimationFrame(raf); clearBlocks(); cur = null; setUI('idle'); clearInterval(keep);
    if (audioEl) { try { audioEl.pause(); } catch (e) {} }
    if (synthOK) window.speechSynthesis.cancel();
  }
  function toggle() {
    if (state === 'idle') start();
    else if (state === 'loading') { /* ignore */ }
    else if (state === 'playing') {
      state = 'paused'; setUI('paused'); cancelAnimationFrame(raf);
      if (engine === 'kokoro' && audioEl) audioEl.pause(); else if (synthOK) window.speechSynthesis.pause();
    } else {
      state = 'playing'; setUI('playing');
      if (engine === 'kokoro' && audioEl) { audioEl.play(); trackWords(); } else if (synthOK) window.speechSynthesis.resume();
    }
  }

  function buildPanel() {
    var panel = document.createElement('div'); panel.className = 'speak-panel';
    panel.addEventListener('click', function (e) { e.stopPropagation(); });
    var vl = document.createElement('div'); vl.className = 'speak-lbl'; vl.textContent = 'Voice';
    var sel = document.createElement('select'); sel.className = 'speak-voice'; sel.setAttribute('aria-label', 'Voice');
    VOICES.forEach(function (g) {
      var og = document.createElement('optgroup'); og.label = g[0];
      g[1].forEach(function (o) { var op = document.createElement('option'); op.value = o[0]; op.textContent = o[1]; if (o[0] === voice) op.selected = true; og.appendChild(op); });
      sel.appendChild(og);
    });
    sel.addEventListener('change', function () {
      voice = sel.value; try { localStorage.setItem('aisdlc-voice', voice); } catch (e) {}
      cache = []; if (state === 'playing' && engine === 'kokoro') playK(curIdx);
    });
    var sll = document.createElement('div'); sll.className = 'speak-lbl'; sll.textContent = 'Speed';
    var sp = document.createElement('div'); sp.className = 'speak-speeds';
    SPEEDS.forEach(function (r) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = r + '×'; b.dataset.rate = r;
      if (r === rate) b.classList.add('on');
      b.addEventListener('click', function () {
        rate = r; try { localStorage.setItem('aisdlc-rate', String(r)); } catch (e) {}
        sp.querySelectorAll('button').forEach(function (x) { x.classList.toggle('on', parseFloat(x.dataset.rate) === rate); });
        if (engine === 'kokoro' && audioEl) audioEl.playbackRate = rate;
      });
      sp.appendChild(b);
    });
    panel.appendChild(vl); panel.appendChild(sel); panel.appendChild(sll); panel.appendChild(sp);
    return panel;
  }
  function boot() {
    controls = document.createElement('div'); controls.className = 'speak-controls';
    var gear = document.createElement('button'); gear.type = 'button'; gear.className = 'speak-btn speak-gear';
    gear.title = 'Voice & speed'; gear.setAttribute('aria-label', 'Voice and speed'); gear.innerHTML = IC.gear;
    gear.addEventListener('click', function (e) { e.stopPropagation(); controls.classList.toggle('is-open'); });
    primary = document.createElement('button'); primary.type = 'button'; primary.className = 'speak-btn speak-primary';
    primary.title = 'Read this lesson aloud (local neural voice)'; primary.addEventListener('click', toggle);
    pctEl = document.createElement('span'); pctEl.className = 'speak-pct';
    stopBtn = document.createElement('button'); stopBtn.type = 'button'; stopBtn.className = 'speak-btn speak-stop';
    stopBtn.title = 'Stop'; stopBtn.setAttribute('aria-label', 'Stop'); stopBtn.innerHTML = IC.stop; stopBtn.addEventListener('click', stop);
    controls.appendChild(gear); controls.appendChild(primary); controls.appendChild(pctEl); controls.appendChild(stopBtn);
    controls.appendChild(buildPanel());
    document.body.appendChild(controls); setUI('idle');
    document.addEventListener('click', function () { controls.classList.remove('is-open'); });
    window.addEventListener('beforeunload', stop);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
