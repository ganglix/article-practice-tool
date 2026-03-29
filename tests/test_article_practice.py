import unittest

from article_practice import build_exercise, grade_exercise


class ArticlePracticeTests(unittest.TestCase):
    def test_build_exercise_blanks_articles_but_keeps_protected_phrases(self) -> None:
        exercise = build_exercise(
            "A teacher found a notebook in the classroom after a few minutes."
        )

        self.assertEqual([blank.answer for blank in exercise.blanks], ["a", "a", "the"])
        rendered = "".join(
            "___" if segment["type"] == "blank" else segment["content"]
            for segment in exercise.segments
        )
        self.assertIn("___ teacher", rendered)
        self.assertIn("a few", rendered)

    def test_grade_exercise_reports_mistakes(self) -> None:
        exercise = build_exercise("The artist opened a window and found an answer.")
        result = grade_exercise(exercise, ["the", "an", "a"])

        self.assertEqual(result["correct_count"], 1)
        self.assertEqual(len(result["mistakes"]), 2)
        self.assertEqual(result["mistakes"][0]["expected"], "a")

    def test_build_exercise_requires_articles(self) -> None:
        with self.assertRaises(ValueError):
            build_exercise("Writers practice carefully.")

    def test_build_exercise_collapses_line_wraps_into_paragraphs(self) -> None:
        exercise = build_exercise("The artist\nfound a notebook.\n\nThe room was quiet.")

        self.assertEqual(
            exercise.original_text,
            "The artist found a notebook.\n\nThe room was quiet.",
        )


if __name__ == "__main__":
    unittest.main()
