import unittest

from games.fill_blank import FillBlankGame
from games.matching import MatchingGame
from games.quiz import EnglishQuizGame


class GameInputValidationTests(unittest.TestCase):
    def test_fill_blank_rejects_non_string_answer(self):
        with self.assertRaises(ValueError):
            FillBlankGame([
                {"id": "f1", "sentence": "A ___", "answer": 7},
                {"id": "f2", "sentence": "B ___", "answer": "word"},
            ])

    def test_fill_blank_rejects_non_string_id(self):
        with self.assertRaises(ValueError):
            FillBlankGame([
                {"id": 1, "sentence": "A ___", "answer": "one"},
                {"id": "f2", "sentence": "B ___", "answer": "two"},
            ])

    def test_fill_blank_single_question_review_uses_original_answer_pool(self):
        source_items = [
            {"id": "f1", "sentence": "A ___", "answer": "one"},
            {"id": "f2", "sentence": "B ___", "answer": "two"},
        ]
        game = FillBlankGame([source_items[0]], option_items=source_items)

        self.assertEqual(len(game.questions), 1)
        self.assertGreaterEqual(len(game.questions[0]["options"]), 2)
        self.assertEqual(
            game.questions[0]["options"][game.questions[0]["correct"]], "one")

    def test_fill_blank_keeps_first_answer_for_each_question(self):
        game = FillBlankGame([
            {"id": "f1", "sentence": "A ___", "answer": "one"},
            {"id": "f2", "sentence": "B ___", "answer": "two"},
        ])
        question = game.questions[0]
        wrong_idx = (question["correct"] + 1) % len(question["options"])

        first_response = game.check_one(question["id"], wrong_idx)
        repeated_response = game.check_one(question["id"], question["correct"])
        for remaining in game.questions[1:]:
            game.check_one(remaining["id"], remaining["correct"])

        self.assertEqual(repeated_response, first_response)
        self.assertFalse(repeated_response["ok"])
        self.assertEqual(game.result()["score"], 1)

    def test_matching_rejects_duplicate_normalized_terms(self):
        with self.assertRaises(ValueError):
            MatchingGame([
                {"id": "m1", "term": "same term", "definition": "first"},
                {"id": "m2", "term": " SAME   TERM ", "definition": "second"},
            ])

    def test_matching_rejects_duplicate_normalized_definitions(self):
        with self.assertRaises(ValueError):
            MatchingGame([
                {"id": "m1", "term": "first", "definition": "same meaning"},
                {"id": "m2", "term": "second", "definition": " SAME   MEANING "},
            ])

    def test_matching_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            MatchingGame([
                {"id": "same", "term": "first", "definition": "one"},
                {"id": "same", "term": "second", "definition": "two"},
            ])

    def test_matching_rejects_non_string_content(self):
        with self.assertRaises(ValueError):
            MatchingGame([
                {"id": "m1", "term": "first", "definition": "one"},
                {"id": "m2", "term": "second", "definition": 2},
            ])

    def test_matching_keeps_first_submission_result(self):
        game = MatchingGame([
            {"id": "m1", "term": "one", "definition": "first"},
            {"id": "m2", "term": "two", "definition": "second"},
        ])
        correct_pairs = {
            item["id"]: game.order.index(item["definition"]) for item in game.items
        }
        wrong_pairs = {
            item["id"]: game.order.index(game.items[1 - index]["definition"])
            for index, item in enumerate(game.items)
        }

        first_result = game.check(correct_pairs)
        second_result = game.check(wrong_pairs)

        self.assertEqual(first_result["score"], 2)
        self.assertEqual(second_result, first_result)

    def test_quiz_rejects_duplicate_options_after_normalization(self):
        with self.assertRaises(ValueError):
            EnglishQuizGame([{
                "id": "q1",
                "q": "Choose one",
                "options": ["Answer", " answer ", "Other", "Last"],
                "answer": 0,
            }])

    def test_quiz_rejects_non_string_option(self):
        with self.assertRaises(ValueError):
            EnglishQuizGame([{
                "id": "q1",
                "q": "Choose one",
                "options": ["Answer", 2, "Other", "Last"],
                "answer": 0,
            }])

    def test_quiz_rejects_duplicate_ids(self):
        with self.assertRaises(ValueError):
            EnglishQuizGame([
                {"id": "same", "q": "First?", "options": ["A", "B", "C", "D"], "answer": 0},
                {"id": "same", "q": "Second?", "options": ["E", "F", "G", "H"], "answer": 0},
            ])

    def test_quiz_keeps_first_answer_for_each_question(self):
        game = EnglishQuizGame([{
            "id": "q1",
            "q": "Choose one",
            "options": ["A", "B", "C", "D"],
            "answer": 0,
        }])
        question = game.questions[0]

        first_response = game.check_one(question["id"], 1)
        repeated_response = game.check_one(question["id"], question["correct"])

        self.assertEqual(repeated_response, first_response)
        self.assertFalse(repeated_response["ok"])
        self.assertEqual(game.result()["score"], 0)


if __name__ == "__main__":
    unittest.main()
