/* Reading aids for focus (ADHD-friendly): a scroll progress bar, an estimated
   read time, and a "focus mode" that dims everything except the line you're on. */
(function () {
  var focusBtn, fill, focusables = [], rafP = null, rafF = null, focusOn = false;
  var SEL = 'h1, h2, h3, p, li, blockquote, figure, table';
  var ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="2.4" fill="currentColor" stroke="none"/></svg>';

  function readable() {
    var wrap = document.querySelector('.wrap'); if (!wrap) return [];
    return Array.prototype.filter.call(wrap.querySelectorAll(SEL), function (el) {
      return !el.closest('.lesson-footer') && !el.closest('.masthead') && (el.textContent || '').trim();
    });
  }
  function updProgress() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var p = max > 0 ? window.scrollY / max : 0;
    fill.style.width = (Math.max(0, Math.min(1, p)) * 100) + '%'; rafP = null;
  }
  function updFocus() {
    rafF = null; if (!focusOn) return;
    var mid = window.innerHeight / 2, best = null, bestD = Infinity;
    focusables.forEach(function (el) {
      var r = el.getBoundingClientRect();
      if (r.bottom < 0 || r.top > window.innerHeight) return;
      var d = Math.abs((r.top + r.bottom) / 2 - mid);
      if (d < bestD) { bestD = d; best = el; }
    });
    focusables.forEach(function (el) { el.classList.toggle('in-focus', el === best); });
  }
  function onScroll() {
    if (!rafP) rafP = requestAnimationFrame(updProgress);
    if (focusOn && !rafF) rafF = requestAnimationFrame(updFocus);
  }
  function setFocus(on) {
    focusOn = on; document.body.classList.toggle('focus-mode', on); focusBtn.classList.toggle('on', on);
    focusBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on) { focusables = readable(); focusables.forEach(function (el) { el.classList.add('focusable'); }); updFocus(); }
    else { focusables.forEach(function (el) { el.classList.remove('focusable', 'in-focus'); }); }
    try { localStorage.setItem('aisdlc-focus', on ? '1' : '0'); } catch (e) {}
  }
  function readTime() {
    var words = 0; readable().forEach(function (el) { words += (el.textContent || '').trim().split(/\s+/).length; });
    return Math.max(1, Math.round(words / 200));
  }
  function boot() {
    var bar = document.createElement('div'); bar.className = 'read-progress';
    fill = document.createElement('div'); fill.className = 'read-progress__fill'; bar.appendChild(fill);
    document.body.appendChild(bar);

    var mh = document.querySelector('.masthead');
    if (mh) { var rt = document.createElement('span'); rt.className = 'read-time'; rt.textContent = '~' + readTime() + ' min'; mh.appendChild(rt); }

    focusBtn = document.createElement('button'); focusBtn.type = 'button'; focusBtn.className = 'focus-toggle';
    focusBtn.title = 'Focus mode — dim everything but the current line'; focusBtn.setAttribute('aria-label', 'Toggle focus mode');
    focusBtn.innerHTML = ICON; focusBtn.addEventListener('click', function () { setFocus(!focusOn); });
    document.body.appendChild(focusBtn);

    updProgress();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', function () { updProgress(); if (focusOn) updFocus(); });
    var saved = false; try { saved = localStorage.getItem('aisdlc-focus') === '1'; } catch (e) {}
    if (saved) setFocus(true);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
