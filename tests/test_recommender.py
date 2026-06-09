import csv
import tempfile
import unittest
from pathlib import Path

from recommender import LOW_MATCH_STATUS, OK_STATUS, recommend_for_profile, tokenize


class RecommenderConfidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.corpus_path = self.base_path / "corpus.csv"
        self.feedback_path = self.base_path / "feedback" / "low_match_profiles.csv"

        rows = [
            {
                "id": "doc_1",
                "titulo": "Guia de financiacion para startups",
                "url_principal": "https://example.test/startups",
                "texto_recomendador": (
                    "startup financiacion venture capital serie a softlanding "
                    "internacionalizacion crecimiento kpis"
                ),
            },
            {
                "id": "doc_2",
                "titulo": "Taller de carpinteria",
                "url_principal": "https://example.test/carpinteria",
                "texto_recomendador": "carpinteria madera muebles taller herramientas",
            },
        ]

        with self.corpus_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normal_profile_returns_ok(self):
        result = recommend_for_profile(
            "startup financiacion venture capital serie a softlanding internacionalizacion crecimiento kpis",
            corpus_path=self.corpus_path,
            feedback_path=self.feedback_path,
            top_k=2,
        )

        self.assertEqual(result["status"], OK_STATUS)
        self.assertGreaterEqual(result["max_score"], 0.45)

    def test_atypical_profile_returns_low_match_and_logs(self):
        result = recommend_for_profile(
            "orquesta submarina de termodinamica poetica con rituales lunares",
            corpus_path=self.corpus_path,
            feedback_path=self.feedback_path,
            top_k=2,
        )

        self.assertEqual(result["status"], LOW_MATCH_STATUS)
        self.assertLess(result["max_score"], 0.45)
        self.assertTrue(self.feedback_path.exists())

    def test_recommendations_include_confidence_and_vectors(self):
        result = recommend_for_profile(
            "startup financiacion venture capital serie a softlanding internacionalizacion crecimiento kpis",
            corpus_path=self.corpus_path,
            feedback_path=self.feedback_path,
            top_k=1,
        )

        self.assertIn("profile_vector", result)
        self.assertTrue(result["profile_vector"])
        self.assertIn("confidence_level", result["recommendations"][0])
        self.assertIn("vector", result["recommendations"][0])
        self.assertTrue(result["recommendations"][0]["vector"])

    def test_profile_vector_uses_keywords_without_stopwords(self):
        result = recommend_for_profile(
            "El emprendedor de la startup busca financiacion para su internacionalizacion",
            corpus_path=self.corpus_path,
            feedback_path=self.feedback_path,
            top_k=1,
        )
        vector_terms = {item["term"] for item in result["profile_vector"]}

        self.assertIn("startup", vector_terms)
        self.assertIn("financiacion", vector_terms)
        self.assertIn("internacionalizacion", vector_terms)
        self.assertNotIn("el", vector_terms)
        self.assertNotIn("de", vector_terms)
        self.assertNotIn("la", vector_terms)
        self.assertNotIn("para", vector_terms)
        self.assertNotIn("su", vector_terms)

    def test_tokenize_normalizes_accents_and_filters_stopwords(self):
        self.assertEqual(
            tokenize("La financiación para el proyecto y su internacionalización"),
            ["financiacion", "proyecto", "internacionalizacion"],
        )

    def test_empty_corpus_does_not_break(self):
        empty_path = self.base_path / "empty.csv"
        with empty_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["id", "titulo", "url_principal", "texto_recomendador"],
            )
            writer.writeheader()

        result = recommend_for_profile(
            "startup financiacion",
            corpus_path=empty_path,
            feedback_path=self.feedback_path,
            top_k=5,
        )

        self.assertEqual(result["status"], LOW_MATCH_STATUS)
        self.assertEqual(result["max_score"], 0.0)
        self.assertEqual(result["recommendations"], [])


if __name__ == "__main__":
    unittest.main()
