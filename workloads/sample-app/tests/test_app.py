import unittest

from src.app import deterministic_score, normalize_text


class AppTestCase(unittest.TestCase):
    def test_normalize_text(self) -> None:
        self.assertEqual(normalize_text("  PipelineBench   SAMPLE app "), "pipelinebench sample app")

    def test_deterministic_score(self) -> None:
        self.assertEqual(deterministic_score([3, 1, 4, 1, 5]), 46)


if __name__ == "__main__":
    unittest.main()
