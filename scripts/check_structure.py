#!/usr/bin/env python3
"""Validate repository-level skill structure invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to validate (defaults to this repository).",
    )
    return parser.parse_args()


def frontmatter_value(path: Path, wanted_key: str) -> str | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:]:
        if line == "---":
            break
        if line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if separator and key.strip() == wanted_key:
            return value.strip()
    return None


def nested_yaml_value(path: Path, section: str, wanted_key: str) -> str | None:
    section_indentation: int | None = None
    child_indentation: int | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indentation = len(line) - len(line.lstrip())
        if section_indentation is None:
            if indentation == 0 and stripped == f"{section}:":
                section_indentation = indentation
            continue
        if indentation <= section_indentation:
            return None
        if child_indentation is None:
            child_indentation = indentation
        if indentation != child_indentation:
            continue
        key, separator, value = stripped.partition(":")
        if separator and key == wanted_key:
            return value.split("#", 1)[0].strip()
    return None


def yaml_boolean(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.split(" #", 1)[0].strip()
    if normalized in {"true", "True", "TRUE"}:
        return True
    if normalized in {"false", "False", "FALSE"}:
        return False
    return None


def load_json(path: Path, root: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"{path.relative_to(root)}: missing required file")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(
            f"{path.relative_to(root)}: invalid JSON at line {error.lineno}"
        )
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(root)}: expected a JSON object")
        return None
    return value


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return ["skills: missing required directory"]

    readme_path = root / "README.md"
    readme_text = (
        readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    )
    if not readme_path.is_file():
        errors.append("README.md: missing required file")

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        for relative_path in (Path("SKILL.md"), Path("agents/openai.yaml")):
            path = skill_dir / relative_path
            if not path.is_file():
                errors.append(
                    f"{path.relative_to(root)}: missing required file"
                )
        skill_md = skill_dir / "SKILL.md"
        if skill_md.is_file():
            raw_name = frontmatter_value(skill_md, "name")
            if raw_name is None:
                errors.append(
                    f"{skill_md.relative_to(root)}: missing frontmatter name"
                )
            else:
                name = raw_name.strip('"\'')
            if raw_name is not None and name != skill_dir.name:
                errors.append(
                    f"{skill_md.relative_to(root)}: frontmatter name '{name}' "
                    f"does not match directory '{skill_dir.name}'"
                )
        openai_yaml = skill_dir / "agents" / "openai.yaml"
        if skill_md.is_file() and openai_yaml.is_file():
            claude_control = frontmatter_value(
                skill_md,
                "disable-model-invocation",
            )
            codex_control = nested_yaml_value(
                openai_yaml,
                "policy",
                "allow_implicit_invocation",
            )
            claude_value = yaml_boolean(claude_control)
            codex_value = yaml_boolean(codex_control)
            if claude_control is not None and claude_value is None:
                errors.append(
                    f"{skill_md.relative_to(root)}: "
                    "disable-model-invocation must be a boolean"
                )
            if codex_control is not None and codex_value is None:
                errors.append(
                    f"{openai_yaml.relative_to(root)}: "
                    "allow_implicit_invocation must be a boolean"
                )
            claude_disabled = claude_value is True
            codex_disabled = codex_value is False
            if (
                (claude_control is None or claude_value is not None)
                and (codex_control is None or codex_value is not None)
                and claude_disabled != codex_disabled
            ):
                missing = (
                    "allow_implicit_invocation=false missing"
                    if claude_disabled
                    else "disable-model-invocation=true missing"
                )
                errors.append(
                    f"{skill_dir.relative_to(root)}: invocation controls disagree "
                    f"(disable-model-invocation={str(claude_disabled).lower()}, "
                    f"{missing})"
                )
        readme_target = f"](skills/{skill_dir.name})"
        link_count = readme_text.count(readme_target)
        if link_count != 1:
            errors.append(
                f"README.md: expected one link to skills/{skill_dir.name}, "
                f"found {link_count}"
            )

    plugin_path = root / ".claude-plugin" / "plugin.json"
    marketplace_path = root / ".claude-plugin" / "marketplace.json"
    plugin = load_json(plugin_path, root, errors)
    marketplace = load_json(marketplace_path, root, errors)
    if plugin is not None and marketplace is not None:
        plugin_version = plugin.get("version")
        marketplace_metadata = marketplace.get("metadata")
        if not isinstance(marketplace_metadata, dict):
            errors.append(
                ".claude-plugin/marketplace.json: metadata must be an object"
            )
        else:
            marketplace_version = marketplace_metadata.get("version")
            if plugin_version != marketplace_version:
                errors.append(
                    ".claude-plugin: version mismatch "
                    f"(plugin.json={plugin_version}, "
                    f"marketplace.json={marketplace_version})"
                )

    canonical_linter = root / "skills" / "okf-lint" / "scripts" / "okf_lint.py"
    embedded_linter = (
        root
        / "skills"
        / "okf-new-kb"
        / "template"
        / "tools"
        / "okf_lint.py"
    )
    if canonical_linter.exists() or embedded_linter.exists():
        if not canonical_linter.is_file():
            errors.append(
                f"{canonical_linter.relative_to(root)}: missing required file"
            )
        elif not embedded_linter.is_file():
            errors.append(
                f"{embedded_linter.relative_to(root)}: missing required file"
            )
        elif canonical_linter.read_bytes() != embedded_linter.read_bytes():
            errors.append("OKF linter copies differ")
    return errors


def main() -> int:
    args = parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("structure ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
