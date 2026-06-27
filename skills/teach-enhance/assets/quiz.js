/* ============================================================
   quiz.js — reusable retrieval-practice widget for lessons
   ------------------------------------------------------------
   Markup contract (author writes this in the lesson HTML):

   <div class="quiz" data-answer="2">
     <p class="quiz__kicker">Retrieval check</p>
     <p class="quiz__stem">Your question goes here?</p>
     <ul class="quiz__opts">
       <li class="quiz__opt">First option</li>
       <li class="quiz__opt">Second option</li>
       <li class="quiz__opt">Third option</li>   <!-- index 2 = correct -->
     </ul>
     <p class="quiz__feedback">Explanation shown after any answer.</p>
   </div>

   - data-answer is the 0-based index of the correct <li>.
   - One choice per question; the widget locks after the first click.
   - Feedback is always revealed (right or wrong) to close the loop.
   - Pedagogy note: keep every option the same length / word count so
     formatting never leaks the answer. See NOTES.md.
   ============================================================ */
(function () {
  function initQuiz(quiz) {
    var answer = parseInt(quiz.getAttribute("data-answer"), 10);
    var opts = Array.prototype.slice.call(quiz.querySelectorAll(".quiz__opt"));
    opts.forEach(function (opt, i) {
      opt.setAttribute("role", "button");
      opt.setAttribute("tabindex", "0");
      function choose() {
        if (quiz.classList.contains("is-answered")) return;
        quiz.classList.add("is-answered");
        if (i === answer) {
          opt.classList.add("is-correct");
        } else {
          opt.classList.add("is-wrong");
          if (opts[answer]) opts[answer].classList.add("is-correct");
        }
      }
      opt.addEventListener("click", choose);
      opt.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(); }
      });
    });
  }
  function boot() {
    document.querySelectorAll(".quiz[data-answer]").forEach(initQuiz);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
