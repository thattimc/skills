/* runs highlight.js over every <pre><code> once the page loads (auto-detects language) */
(function () {
  function run() { if (window.hljs) { try { hljs.highlightAll(); } catch (e) {} } }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();
