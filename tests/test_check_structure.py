import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_STRUCTURE = REPO_ROOT / "scripts" / "check_structure.py"


class CheckStructureCliTests(unittest.TestCase):
    def make_valid_repo(self, root: Path) -> None:
        skill = root / "skills" / "example-skill"
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: example-skill\ndescription: Example skill.\n---\n",
            encoding="utf-8",
        )
        (skill / "agents" / "openai.yaml").write_text(
            'interface:\n  display_name: "Example Skill"\n'
            '  short_description: "Example repository skill"\n',
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "[`example-skill`](skills/example-skill)\n",
            encoding="utf-8",
        )
        plugin_dir = root / ".claude-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "example", "version": "1.0.0"}),
            encoding="utf-8",
        )
        (plugin_dir / "marketplace.json").write_text(
            json.dumps({"metadata": {"version": "1.0.0"}}),
            encoding="utf-8",
        )

    def run_check(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CHECK_STRUCTURE), "--root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_valid_repository_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)

            result = self.run_check(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "structure ok\n")

    def test_missing_openai_metadata_fails_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "agents" / "openai.yaml").unlink()

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "skills/example-skill/agents/openai.yaml: missing required file",
            result.stderr,
        )

    def test_skill_name_must_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "SKILL.md").write_text(
                "---\nname: different-name\ndescription: Example skill.\n---\n",
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "skills/example-skill/SKILL.md: frontmatter name 'different-name' "
            "does not match directory 'example-skill'",
            result.stderr,
        )

    def test_invocation_controls_must_agree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example skill.\n"
                "disable-model-invocation: true\n---\n",
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "skills/example-skill: invocation controls disagree "
            "(disable-model-invocation=true, allow_implicit_invocation=false missing)",
            result.stderr,
        )

    def test_commented_codex_control_does_not_satisfy_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example skill.\n"
                "disable-model-invocation: true\n---\n",
                encoding="utf-8",
            )
            (root / "skills" / "example-skill" / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Example Skill"\n'
                '  short_description: "Example repository skill"\n'
                "# allow_implicit_invocation: false\n",
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("invocation controls disagree", result.stderr)

    def test_quoted_false_is_not_a_boolean_policy_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example skill.\n"
                "disable-model-invocation: true\n---\n",
                encoding="utf-8",
            )
            (root / "skills" / "example-skill" / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Example Skill"\n'
                '  short_description: "Example repository skill"\n'
                'policy:\n  allow_implicit_invocation: "false"\n',
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "agents/openai.yaml: allow_implicit_invocation must be a boolean",
            result.stderr,
        )

    def test_nested_policy_value_is_not_a_direct_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "skills" / "example-skill" / "SKILL.md").write_text(
                "---\nname: example-skill\ndescription: Example skill.\n"
                "disable-model-invocation: true\n---\n",
                encoding="utf-8",
            )
            (root / "skills" / "example-skill" / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Example Skill"\n'
                '  short_description: "Example repository skill"\n'
                "policy:\n  nested:\n    allow_implicit_invocation: false\n",
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("invocation controls disagree", result.stderr)

    def test_readme_must_link_each_skill_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / "README.md").write_text("# Skills\n", encoding="utf-8")

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "README.md: expected one link to skills/example-skill, found 0",
            result.stderr,
        )

    def test_plugin_versions_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"metadata": {"version": "2.0.0"}}),
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ".claude-plugin: version mismatch "
            "(plugin.json=1.0.0, marketplace.json=2.0.0)",
            result.stderr,
        )

    def test_okf_linter_copies_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            canonical = root / "skills" / "okf-lint" / "scripts" / "okf_lint.py"
            embedded = (
                root
                / "skills"
                / "okf-new-kb"
                / "template"
                / "tools"
                / "okf_lint.py"
            )
            canonical.parent.mkdir(parents=True)
            embedded.parent.mkdir(parents=True)
            canonical.write_text("canonical\n", encoding="utf-8")
            embedded.write_text("stale\n", encoding="utf-8")

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("OKF linter copies differ", result.stderr)

    def test_invalid_plugin_json_reports_file_and_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / ".claude-plugin" / "plugin.json").write_text(
                "{\ninvalid\n",
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ".claude-plugin/plugin.json: invalid JSON at line 2",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_marketplace_metadata_shape_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_valid_repo(root)
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"metadata": []}),
                encoding="utf-8",
            )

            result = self.run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ".claude-plugin/marketplace.json: metadata must be an object",
            result.stderr,
        )
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
