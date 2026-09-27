"""Run the domain-search skill's offline tests from the repository test command."""

import unittest
from pathlib import Path


SKILL_TESTS = Path(__file__).resolve().parents[1] / "skills" / "domain-search" / "tests"


def load_tests(loader, standard_tests, pattern):
    # A separate loader keeps the outer discovery's top-level directory intact.
    standard_tests.addTests(
        unittest.TestLoader().discover(
            start_dir=str(SKILL_TESTS),
            pattern="test_*.py",
            top_level_dir=str(SKILL_TESTS),
        )
    )
    return standard_tests
