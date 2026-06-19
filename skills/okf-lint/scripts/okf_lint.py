#!/usr/bin/env python3
"""okf_lint — validate this knowledge base against OKF v0.1 + the house rules.

Usage:
    python3 tools/okf_lint.py [--bundle wiki] [--strict] [--quiet]

Exit code is non-zero if any ERROR is found (or any WARNING when --strict).

ERRORs are OKF non-conformance or house-standard violations.
WARNINGs are things OKF tolerates but we'd rather fix, such as broken links,
orphans, non-ISO timestamps, wikilinks, leading-slash links, non-canonical key
order, odd or non-lowercase slugs, a Source missing its resource, or an
unexpected okf_version.

PyYAML is used when available; otherwise a small built-in parser handles the
constrained frontmatter this KB uses. Install PyYAML (`pip install pyyaml`) for
maximum fidelity.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime

try:
    import yaml  # type: ignore
    _HAVE_YAML = True
except Exception:  # pragma: no cover
    yaml = None
    _HAVE_YAML = False

RESERVED = {"index.md", "log.md"}
CANONICAL_ORDER = ["type", "resource", "title", "description", "tags", "timestamp"]
REQUIRED_KEYS = ["type", "title", "description", "timestamp"]
SEGMENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
MD_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
IMG_LINK_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
SKIP_DIRS = {"assets", ".obsidian", ".git", "__pycache__"}


class Finding:
    __slots__ = ("level", "path", "msg")

    def __init__(self, level: str, path: str, msg: str):
        self.level = level
        self.path = path
        self.msg = msg


# ---------------------------------------------------------------------------
# Frontmatter handling
# ---------------------------------------------------------------------------

def split_frontmatter(text: str):
    """Return (frontmatter_str | None | 'UNTERMINATED', body_str)."""
    if not text.startswith("---"):
        return None, text
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "UNTERMINATED", text


def _fallback_parse(fm: str):
    """Minimal YAML for the constrained frontmatter this KB uses."""
    data: dict = {}
    key = None
    for raw in fm.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m_item = re.match(r"^\s*-\s+(.*)$", raw)
        if m_item and key is not None:
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(_scalar(m_item.group(1)))
            continue
        m_kv = re.match(r"^([A-Za-z0-9_][\w.\-]*):\s*(.*)$", raw)
        if m_kv:
            key = m_kv.group(1)
            rest = m_kv.group(2).strip()
            if rest == "":
                data[key] = None  # may become a block list
            elif rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1].strip()
                data[key] = [_scalar(x) for x in inner.split(",")] if inner else []
            else:
                data[key] = _scalar(rest)
    return data


def ts_to_str(ts):
    """Canonicalize a timestamp value to an ISO-8601 string.

    PyYAML auto-coerces an unquoted `2026-06-19T08:33:09Z` to a datetime, whose
    str() is `2026-06-19 08:33:09+00:00` (space separator, +00:00). Normalize it
    back to `...Z` so the same file lints identically with or without PyYAML.
    """
    if isinstance(ts, datetime):
        s = ts.isoformat()
        return s[:-6] + "Z" if s.endswith("+00:00") else s
    if isinstance(ts, date):
        return ts.isoformat()  # date-only: intentionally lacks a time -> will warn
    return str(ts).strip()


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def parse_frontmatter(fm: str):
    if _HAVE_YAML:
        return yaml.safe_load(fm)
    return _fallback_parse(fm)


# ---------------------------------------------------------------------------
# Link handling
# ---------------------------------------------------------------------------

def _is_external(target: str) -> bool:
    return ("://" in target) or target.startswith("mailto:") or target.startswith("#")


def strip_code(text: str) -> str:
    """Remove fenced blocks and inline code spans so example links inside code
    are not validated as real cross-links."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def extract_links(text: str):
    """Yield (target, is_image) for every markdown/image link."""
    for m in IMG_LINK_RE.finditer(text):
        yield m.group(1).strip(), True
    for m in MD_LINK_RE.finditer(text):
        yield m.group(1).strip(), False


def resolve_target(bundle: str, file_rel: str, target: str):
    """Resolve a local link target to a bundle-relative path, or None if N/A."""
    t = target.split("#", 1)[0].strip()
    if not t or _is_external(t) or t.startswith("/"):
        return None
    base = os.path.dirname(file_rel)
    return os.path.normpath(os.path.join(base, t))


# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

def lint(bundle: str):
    findings: list[Finding] = []
    md_files: list[str] = []  # bundle-relative paths

    if not os.path.isdir(bundle):
        findings.append(Finding("ERROR", bundle, "bundle directory does not exist"))
        return findings, md_files, {}

    for root, dirs, files in os.walk(bundle):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            abs_p = os.path.join(root, fn)
            rel = os.path.relpath(abs_p, bundle)
            md_files.append(rel)

    concept_files: set[str] = set()
    inbound: dict[str, int] = {}

    for rel in sorted(md_files):
        abs_p = os.path.join(bundle, rel)
        try:
            with open(abs_p, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            findings.append(Finding("ERROR", rel, f"cannot read file: {e}"))
            continue

        basename = os.path.basename(rel)
        is_root_index = (rel == "index.md")
        is_reserved = basename in RESERVED

        # --- slug / path segment check (concepts only) ---
        if not is_reserved:
            segments = rel[:-3].split("/")  # drop .md
            for seg in segments:
                if not SEGMENT_RE.match(seg):
                    findings.append(Finding(
                        "WARN", rel,
                        f"path segment '{seg}' violates [A-Za-z0-9_][A-Za-z0-9_.-]* (letters/digits/_/-/., no spaces)"))
                    break
                if seg != seg.lower():
                    findings.append(Finding(
                        "WARN", rel,
                        f"path segment '{seg}' is not lowercase (house rule: lowercase filenames)"))
                    break

        fm_raw, body = split_frontmatter(text)

        # --- reserved files ---
        if is_reserved:
            if fm_raw == "UNTERMINATED":
                findings.append(Finding("ERROR", rel, "unterminated frontmatter block"))
            elif fm_raw is not None:
                if is_root_index:
                    try:
                        data = parse_frontmatter(fm_raw) or {}
                    except Exception as e:
                        findings.append(Finding("ERROR", rel, f"invalid YAML frontmatter: {e}"))
                        data = {}
                    extra = [k for k in data.keys() if k != "okf_version"]
                    if extra:
                        findings.append(Finding(
                            "ERROR", rel,
                            f"root index.md may only carry 'okf_version'; found extra key(s): {', '.join(extra)}"))
                    if "okf_version" in data and str(data["okf_version"]) not in ("0.1",):
                        findings.append(Finding("WARN", rel, f"okf_version is '{data['okf_version']}', expected 0.1"))
                else:
                    findings.append(Finding(
                        "ERROR", rel,
                        f"reserved file '{basename}' must not have frontmatter"))
            _check_links(bundle, rel, text, findings, inbound)
            continue

        # --- concept files ---
        concept_files.add(rel)

        if fm_raw is None:
            findings.append(Finding("ERROR", rel, "missing YAML frontmatter (every concept needs a non-empty 'type')"))
            _check_links(bundle, rel, text, findings, inbound)
            continue
        if fm_raw == "UNTERMINATED":
            findings.append(Finding("ERROR", rel, "unterminated frontmatter block"))
            _check_links(bundle, rel, text, findings, inbound)
            continue

        try:
            data = parse_frontmatter(fm_raw)
        except Exception as e:
            findings.append(Finding("ERROR", rel, f"invalid YAML frontmatter: {e}"))
            _check_links(bundle, rel, text, findings, inbound)
            continue

        if not isinstance(data, dict):
            findings.append(Finding("ERROR", rel, "frontmatter is not a YAML mapping"))
            _check_links(bundle, rel, text, findings, inbound)
            continue

        # type (OKF-required)
        t = data.get("type")
        if t is None or str(t).strip() == "":
            findings.append(Finding("ERROR", rel, "frontmatter 'type' is required and must be non-empty (OKF conformance)"))

        # house-required keys
        for k in ("title", "description", "timestamp"):
            v = data.get(k)
            if v is None or str(v).strip() == "":
                findings.append(Finding("ERROR", rel, f"frontmatter '{k}' is required by the house standard"))

        # tags must be a list, never a comma-string
        if "tags" in data and data["tags"] is not None:
            if not isinstance(data["tags"], list):
                findings.append(Finding(
                    "ERROR", rel,
                    "frontmatter 'tags' must be a YAML list (- item), not a comma-separated string"))

        # timestamp format (normalize datetime/date so PyYAML and the fallback agree)
        ts = data.get("timestamp")
        if ts is not None and str(ts).strip():
            ts_str = ts_to_str(ts)
            if not TIMESTAMP_RE.match(ts_str):
                findings.append(Finding("WARN", rel, f"timestamp '{ts_str}' is not ISO 8601 (e.g. 2026-06-19T08:33:09Z)"))

        # resource recommended on Source
        if str(t).strip() == "Source" and not str(data.get("resource") or "").strip():
            findings.append(Finding("WARN", rel, "type is Source but 'resource' (asset URI) is missing"))

        # key order
        present = [k for k in data.keys() if k in CANONICAL_ORDER]
        ordered = sorted(present, key=lambda k: CANONICAL_ORDER.index(k))
        if present != ordered:
            findings.append(Finding(
                "WARN", rel,
                f"frontmatter key order is {present}; canonical order is {ordered} (extensions go last)"))

        _check_links(bundle, rel, text, findings, inbound)

    # --- orphans: concepts with no inbound links from anywhere ---
    for rel in sorted(concept_files):
        if inbound.get(rel, 0) == 0:
            findings.append(Finding("WARN", rel, "orphan: no other page links to this concept (add it to an index or link it)"))

    return findings, md_files, inbound


def _check_links(bundle, rel, text, findings, inbound):
    text = strip_code(text)
    for m in WIKILINK_RE.finditer(text):
        findings.append(Finding("WARN", rel, f"wikilink [[{m.group(1)}]] is not OKF-valid; use a relative markdown link"))
    for target, is_image in extract_links(text):
        if _is_external(target):
            continue
        if target.startswith("/"):
            findings.append(Finding("WARN", rel, f"link '{target}' starts with '/'; use a relative path (breaks in Obsidian)"))
            continue
        resolved = resolve_target(bundle, rel, target)
        if resolved is None:
            continue
        abs_target = os.path.join(bundle, resolved)
        if not os.path.exists(abs_target):
            kind = "image" if is_image else "link"
            findings.append(Finding("WARN", rel, f"broken {kind}: '{target}' -> {resolved} (target not found)"))
        elif not is_image and resolved.endswith(".md"):
            inbound[resolved] = inbound.get(resolved, 0) + 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate the OKF knowledge base.")
    ap.add_argument("--bundle", default="wiki", help="bundle directory (default: wiki)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args(argv)

    findings, md_files, _ = lint(args.bundle)

    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]

    if not args.quiet:
        by_file: dict[str, list[Finding]] = {}
        for f in findings:
            by_file.setdefault(f.path, []).append(f)
        for path in sorted(by_file):
            print(f"\n{path}")
            for f in by_file[path]:
                marker = "✗" if f.level == "ERROR" else "›"
                print(f"  {marker} {f.level}: {f.msg}")

    yaml_note = "" if _HAVE_YAML else "  (PyYAML not installed — used built-in parser)"
    print(f"\nokf_lint: {len(md_files)} markdown file(s), "
          f"{len(errors)} error(s), {len(warns)} warning(s).{yaml_note}")

    failed = bool(errors) or (args.strict and bool(warns))
    if failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
