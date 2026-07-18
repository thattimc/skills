from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "calculate_ballpark.py"
SAMPLE = SKILL_DIR / "examples" / "sample-estimate.json"
SNAPSHOT = SKILL_DIR / "examples" / "sample-rate-card-snapshot.json"
SPEC = importlib.util.spec_from_file_location("calculate_ballpark", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BallparkCalculatorTests(unittest.TestCase):
    def sample(self):
        return MODULE.load_input(SAMPLE)

    def rate_mapping(self):
        prefix = "EXAMPLE-SERVICES-USD|2026.1|Services"
        return {
            "ba": f"{prefix}|Level 3|Business Analysis|Remote|USD",
            "solution_architect": f"{prefix}|Level 4|Architecture|Remote|USD",
            "developer": f"{prefix}|Level 2|Engineering|Remote|USD",
            "qa": f"{prefix}|Level 1|Quality Assurance|Remote|USD",
            "pm": f"{prefix}|Level 4|Delivery Management|Remote|USD",
        }

    def test_calculates_expected_range(self):
        result = MODULE.calculate(self.sample())
        totals = result["totals"]

        self.assertEqual(totals["effort_low"], Decimal("39"))
        self.assertEqual(totals["effort_high"], Decimal("60"))
        self.assertEqual(totals["service_cost_low"], Decimal("227000"))
        self.assertEqual(totals["service_cost_high"], Decimal("348000"))
        self.assertEqual(totals["project_total_low"], Decimal("280700"))
        self.assertEqual(totals["project_total_high"], Decimal("460600"))
        self.assertEqual(totals["service_initial_low"], Decimal("249700"))
        self.assertEqual(totals["service_initial_high"], Decimal("417600"))
        self.assertEqual(totals["one_time_initial_low"], Decimal("31000"))
        self.assertEqual(totals["one_time_initial_high"], Decimal("43000"))
        self.assertEqual(totals["presented_project_low"], Decimal("281000"))
        self.assertEqual(totals["presented_project_high"], Decimal("461000"))
        self.assertEqual(
            totals["recurring_by_period"]["monthly"],
            {"low": Decimal("12000"), "high": Decimal("19000")},
        )

    def test_draft_and_approved_outputs_keep_rates_internal(self):
        draft = MODULE.calculate(self.sample())
        approved = MODULE.calculate(self.sample(), "Alex Reviewer")

        draft_client = MODULE.render_client(draft)
        approved_client = MODULE.render_client(approved)
        internal = MODULE.render_internal(draft)

        self.assertIn("DRAFT — human approval required", draft_client)
        self.assertIn("Approved for client discussion by Alex Reviewer", approved_client)
        self.assertNotIn("Synthetic FY2026 approved rate card", draft_client)
        self.assertNotIn("USD 6,000", draft_client)
        self.assertIn("Synthetic FY2026 approved rate card", internal)
        self.assertIn("USD 6,000", internal)

    def test_blocking_unknown_refuses_estimate(self):
        data = self.sample()
        data["discovery"]["blocking_unknowns"] = ["Core workflow is undefined"]

        with self.assertRaisesRegex(MODULE.EstimateError, "ballpark blocked"):
            MODULE.calculate(data)

    def test_invalid_range_refuses_estimate(self):
        data = copy.deepcopy(self.sample())
        data["services"][0]["low_days"] = Decimal("9")
        data["services"][0]["high_days"] = Decimal("8")

        with self.assertRaisesRegex(MODULE.EstimateError, "high_days"):
            MODULE.calculate(data)

    def test_optional_cost_lists_and_commercial_can_be_omitted(self):
        data = self.sample()
        del data["one_time"]
        del data["recurring"]
        del data["commercial"]

        result = MODULE.calculate(data)

        self.assertEqual(result["one_time"], [])
        self.assertEqual(result["recurring"], [])
        self.assertEqual(result["commercial"]["discount_pct"], Decimal("0"))
        self.assertEqual(result["commercial"]["tax_pct"], Decimal("0"))

    def test_future_price_source_refuses_estimate(self):
        data = self.sample()
        data["recurring"][0]["as_of"] = "2026-07-18"

        with self.assertRaisesRegex(MODULE.EstimateError, "cannot be after"):
            MODULE.calculate(data)

    def test_writes_three_artifacts(self):
        result = MODULE.calculate(self.sample())
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = MODULE.write_outputs(result, Path(temp_dir))
            self.assertEqual(len(paths), 3)
            self.assertTrue(all(path.is_file() for path in paths))

    def test_cli_uses_frozen_rate_card_snapshot(self):
        data = self.sample()
        del data["rate_card"]
        data["rate_mapping"] = self.rate_mapping()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "estimate.json"
            output_dir = root / "output"
            input_path.write_text(
                json.dumps(MODULE._json_safe(data), indent=2) + "\n", encoding="utf-8"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(input_path),
                    "--rate-card-snapshot",
                    str(SNAPSHOT),
                    "--output-dir",
                    str(output_dir),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            calculation = json.loads((output_dir / "calculation.json").read_text())
            client = (output_dir / "client-ballpark.md").read_text()
            internal = (output_dir / "internal-estimate.md").read_text()
            self.assertEqual(calculation["totals"]["service_cost_low"], "227000")
            self.assertEqual(
                calculation["rate_card"]["snapshot_checksum"],
                "sha256:3138132961f7c3072ba33b89cae8df0bee4a9547364bc04ae52786e17b8d7095",
            )
            self.assertIn("Notion rate card", internal)
            self.assertIn("snapshot checksum", internal)
            self.assertNotIn("Notion rate card", client)
            self.assertNotIn("sha256:", client)

    def test_cli_rejects_tampered_rate_card_snapshot(self):
        data = self.sample()
        del data["rate_card"]
        data["rate_mapping"] = self.rate_mapping()
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        snapshot["rate_card"]["rates"][0]["day_rate"] = "999999"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "estimate.json"
            snapshot_path = root / "tampered-snapshot.json"
            input_path.write_text(
                json.dumps(MODULE._json_safe(data), indent=2) + "\n", encoding="utf-8"
            )
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(input_path),
                    "--rate-card-snapshot",
                    str(snapshot_path),
                    "--output-dir",
                    str(root / "output"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("snapshot checksum does not match", result.stderr)

    def test_cli_rejects_changed_snapshot_retrieval_time(self):
        data = self.sample()
        del data["rate_card"]
        data["rate_mapping"] = self.rate_mapping()
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        snapshot["source"]["retrieved_at"] = "2030-01-01T00:00:00Z"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "estimate.json"
            snapshot_path = root / "changed-retrieval-time.json"
            input_path.write_text(
                json.dumps(MODULE._json_safe(data), indent=2) + "\n", encoding="utf-8"
            )
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(input_path),
                    "--rate-card-snapshot",
                    str(snapshot_path),
                    "--output-dir",
                    str(root / "output"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("snapshot checksum does not match", result.stderr)

    def test_snapshot_requires_mapping_for_every_service_role(self):
        data = self.sample()
        del data["rate_card"]
        data["rate_mapping"] = self.rate_mapping()
        del data["rate_mapping"]["qa"]
        snapshot = MODULE.load_input(SNAPSHOT)

        with self.assertRaisesRegex(MODULE.EstimateError, "role 'qa' is absent"):
            MODULE.calculate(data, rate_card_snapshot=snapshot)


if __name__ == "__main__":
    unittest.main()
