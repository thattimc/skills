from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "calculate_ballpark.py"
SAMPLE = SKILL_DIR / "examples" / "sample-estimate.json"
SPEC = importlib.util.spec_from_file_location("calculate_ballpark", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BallparkCalculatorTests(unittest.TestCase):
    def sample(self):
        return MODULE.load_input(SAMPLE)

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
        self.assertNotIn("HKD 6,000", draft_client)
        self.assertIn("Synthetic FY2026 approved rate card", internal)
        self.assertIn("HKD 6,000", internal)

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


if __name__ == "__main__":
    unittest.main()
