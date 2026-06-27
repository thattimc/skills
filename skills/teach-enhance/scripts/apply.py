#!/usr/bin/env python3
"""
apply.py — wire the teach-enhance bundle into a /teach workspace.

Usage:
    python3 apply.py [WORKSPACE_DIR]     # defaults to the current directory

It is idempotent. It:
  1. copies the JS components into  <workspace>/assets/  (overwrites — they are the canonical versions),
  2. copies  course.css  only if the workspace has none (otherwise leaves yours; see SKILL.md to merge),
  3. vendors  highlight.min.js  (downloaded once) for offline syntax highlighting,
  4. adds the <script> includes before </body> in every  lessons/*.html
     (quiz.js + speak.js + reading.js + content.js everywhere; highlight only where there's a <pre>).

After running, use references/content-patterns.md and references/diagram-kit.md to add the
TL;DR / recap / worked-example / mid-lesson-quiz / unified-diagram patterns to each lesson.
"""
import os, sys, shutil, urllib.request

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL, "assets")
HLJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"
JS = ["quiz.js", "speak.js", "reading.js", "content.js", "code-highlight.js"]
# include order before </body>; highlight pair is conditional on a <pre> in the lesson
ALWAYS = ["quiz.js", "speak.js", "reading.js", "content.js"]
CODE = ["highlight.min.js", "code-highlight.js"]


def main():
    ws = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    lessons = os.path.join(ws, "lessons")
    if not os.path.isdir(lessons):
        sys.exit(f"No lessons/ dir in {ws} — point me at a /teach workspace root.")
    wassets = os.path.join(ws, "assets")
    os.makedirs(wassets, exist_ok=True)

    for f in JS:
        shutil.copy2(os.path.join(ASSETS, f), os.path.join(wassets, f))
    print(f"copied components: {', '.join(JS)}")

    css_dst = os.path.join(wassets, "course.css")
    if not os.path.exists(css_dst):
        shutil.copy2(os.path.join(ASSETS, "course.css"), css_dst)
        print("copied course.css (none existed)")
    else:
        print("course.css already present — left as-is; merge the enhance layers from this skill's assets/course.css if missing")

    hljs = os.path.join(wassets, "highlight.min.js")
    if not os.path.exists(hljs):
        try:
            urllib.request.urlretrieve(HLJS_URL, hljs)
            print(f"vendored highlight.min.js ({os.path.getsize(hljs)//1024} KB)")
        except Exception as e:
            print(f"!! could not fetch highlight.min.js ({e}); add it manually from {HLJS_URL}")

    import glob, re
    n = 0
    for f in sorted(glob.glob(os.path.join(lessons, "*.html"))):
        s = open(f, encoding="utf-8").read()
        tags = list(ALWAYS)
        if "<pre" in s:
            tags = CODE[:1] + tags + CODE[1:]  # highlight.min.js + always + code-highlight.js
        add = [t for t in tags if f'assets/{t}"' not in s]
        if not add:
            continue
        block = "".join(f'<script src="../assets/{t}"></script>\n' for t in add)
        s = s.replace("</body>", block + "</body>", 1)
        open(f, "w", encoding="utf-8").write(s)
        n += 1
    print(f"script includes ensured on {n} lesson(s)")
    print("done — now apply the content patterns (references/) per lesson.")


if __name__ == "__main__":
    main()
