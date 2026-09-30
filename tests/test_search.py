from pathlib import Path
import unittest

from src.data_loader import load_resources
from src.search import needs_ai_expansion, search_resources

ROOT = Path(__file__).resolve().parents[1]

class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resources = load_resources(ROOT / "data" / "resources.json")

    def test_money_query_finds_financial_aid(self):
        results = search_resources("I'm stressed about money", self.resources)
        ids = [r["resource"]["id"] for r in results]
        self.assertIn("financial-aid", ids)
        self.assertEqual(ids[0], "financial-aid")

    def test_math_query_finds_q_center(self):
        results = search_resources("I need math tutoring", self.resources)
        ids = [r["resource"]["id"] for r in results]
        self.assertIn("q-center", ids)

    def test_food_query_finds_food_support(self):
        results = search_resources("Where can I get free food?", self.resources)
        ids = {r["resource"]["id"] for r in results}
        self.assertIn("food-and-meal-assistance", ids)
        self.assertIn("211-connecticut", ids)

    def test_blank_search_returns_every_resource(self):
        self.assertEqual(len(search_resources("", self.resources)), len(self.resources))

    def test_unknown_query_has_no_results(self):
        self.assertEqual(search_resources("xyzzy quux", self.resources), [])

    def test_tfidf_score_is_returned(self):
        results = search_resources("math tutoring", self.resources)
        self.assertGreater(results[0]["tfidf_score"], 0)

    def test_ai_expansion_is_only_recommended_for_weak_local_matches(self):
        self.assertFalse(needs_ai_expansion(search_resources("math tutoring", self.resources)))
        self.assertTrue(needs_ai_expansion(search_resources("xyzzy quux", self.resources)))

if __name__ == "__main__":
    unittest.main()
