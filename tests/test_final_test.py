"""Kiểm thử hướng phát triển (TDD) cho bài kiểm tra cuối Edu_game.

Quy ước đang thử nghiệm:
- Trắc nghiệm một đáp án, bốn phương án/câu.
- Lấy hết câu từ fill_blank, matching, quiz trong cùng chương, tối đa 30.
- `score` là số câu đúng, `total` là số câu, điểm thang 10 = 10 * score / total.
- Mỗi câu phải truy vết ngược về source_game/source_id.

Trong snapshot hiện tại games/final_test.py chưa triển khai. Các acceptance test
phụ thuộc vào module này được tự động SKIP, không giả vờ đã kiểm chứng.
Khi build_final_quiz / calculate_grade_10 có bản triển khai, test tự kích hoạt.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
import json
import unittest

from games import final_test
from games.quiz import EnglishQuizGame, validate_items as validate_quiz_items

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCES = ("fill_blank", "matching", "quiz")


def sample_chapter(subject: str = "english") -> dict:
    """Ghép các file mẫu một-part thành chapter có đủ ba phần."""
    files = [DATA / f"sample_{subject}_{game}.json" for game in SOURCES]
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    subjects = {payload["subject"] for payload in payloads}
    titles = {payload["chapter_title"] for payload in payloads}
    if subjects != {subject} or len(titles) != 1:
        raise ValueError("Các file mẫu không thuộc cùng môn/chương")
    return {
        "subject": subject,
        "chapter_title": payloads[0]["chapter_title"],
        "parts": [payload["parts"][0] for payload in payloads],
    }


def synthetic_chapter(per_game: int) -> dict:
    """Tạo 3*per_game câu đúng schema, có ít nhất 4 nhiễu mỗi loại."""
    return {
        "subject": "english",
        "chapter_title": "Synthetic final-test fixture",
        "parts": [
            {"part": 1, "game": "fill_blank", "items": [
                {"id": f"f-{i}", "sentence": f"Sentence {i}: ___", "answer": f"word-{i}"}
                for i in range(per_game)
            ]},
            {"part": 2, "game": "matching", "items": [
                {"id": f"m-{i}", "term": f"term-{i}", "definition": f"definition-{i}"}
                for i in range(per_game)
            ]},
            {"part": 3, "game": "quiz", "items": [
                {"id": f"q-{i}", "q": f"Question {i}?",
                 "options": [f"right-{i}", f"wrong-a-{i}", f"wrong-b-{i}", f"wrong-c-{i}"],
                 "answer": 0}
                for i in range(per_game)
            ]},
        ],
    }


def _builder_is_ready() -> bool:
    """Phát hiện khung TODO, để dự án vẫn có thể chạy test hiện hành."""
    try:
        final_test.build_final_quiz(sample_chapter())
    except NotImplementedError:
        return False
    except Exception:
        # Có triển khai nhưng đang lỗi: bật acceptance tests để hiện lỗi rõ.
        return True
    return True


BUILDER_READY = _builder_is_ready()
GRADE_READY = callable(getattr(final_test, "calculate_grade_10", None))


class ExistingQuizContractTests(unittest.TestCase):
    """Các test CHẠY NGAY với game Quiz đang có."""

    def test_existing_samples_have_16_questions_per_subject(self):
        for subject in ("english", "philosophy"):
            with self.subTest(subject=subject):
                chapter = sample_chapter(subject)
                counts = {part["game"]: len(part["items"]) for part in chapter["parts"]}
                self.assertEqual(counts, {"fill_blank": 5, "matching": 6, "quiz": 5})
                self.assertEqual(sum(counts.values()), 16)

    def test_existing_quiz_engine_never_exposes_answer_index_in_public_view(self):
        items = sample_chapter()["parts"][2]["items"]
        game = EnglishQuizGame(items)
        public = game.public_view()
        for question in public["questions"]:
            self.assertNotIn("answer", question)
            self.assertNotIn("correct", question)
            self.assertNotIn("correct_idx", question)
            self.assertEqual(len(question["options"]), 4)

    def test_existing_quiz_keeps_raw_score_as_number_correct(self):
        items = sample_chapter()["parts"][2]["items"]
        game = EnglishQuizGame(items)
        for question in game.questions:
            game.check_one(question["id"], question["correct"])
        result = game.result()
        self.assertEqual(result["score"], 5)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["wrong"], [])
        self.assertIsInstance(result["score"], int)


@unittest.skipUnless(BUILDER_READY, "TDD chờ triển khai games.final_test.build_final_quiz()")
class FinalQuizBuilderAcceptanceTests(unittest.TestCase):
    """Tiêu chí nghiệm thu cho hàm đã có tên nhưng còn NotImplementedError."""

    def test_takes_all_16_questions_when_below_cap(self):
        for subject in ("english", "philosophy"):
            with self.subTest(subject=subject):
                actual = final_test.build_final_quiz(sample_chapter(subject))
                self.assertEqual(len(actual), 16)
                self.assertEqual(Counter(q["source_game"] for q in actual),
                                 {"fill_blank": 5, "matching": 6, "quiz": 5})

    def test_capped_to_30_without_duplicate_source_questions(self):
        actual = final_test.build_final_quiz(synthetic_chapter(15))
        self.assertEqual(len(actual), 30)
        self.assertEqual(len({(q["source_game"], q["source_id"]) for q in actual}), 30)

    def test_exactly_30_questions_does_not_drop_any(self):
        actual = final_test.build_final_quiz(synthetic_chapter(10))
        self.assertEqual(len(actual), 30)
        self.assertEqual(Counter(q["source_game"] for q in actual),
                         {"fill_blank": 10, "matching": 10, "quiz": 10})

    def test_all_questions_fit_existing_quiz_engine_four_options(self):
        items = final_test.build_final_quiz(sample_chapter())
        self.assertEqual(validate_quiz_items(items), [])
        self.assertTrue(all(len(item["options"]) == 4 for item in items))
        self.assertTrue(all(0 <= item["answer"] < 4 for item in items))

    def test_final_test_accepts_two_to_four_options_without_changing_regular_quiz_contract(self):
        chapter = {
            "subject": "english",
            "chapter_title": "Small source set",
            "parts": [
                {"game": "fill_blank", "items": [
                    {"id": "f1", "sentence": "A ___", "answer": "one"},
                    {"id": "f2", "sentence": "B ___", "answer": "two"},
                ]},
                {"game": "matching", "items": [
                    {"id": "m1", "term": "one", "definition": "first"},
                    {"id": "m2", "term": "two", "definition": "second"},
                ]},
                {"game": "quiz", "items": [{
                    "id": "q1", "q": "Pick one", "options": ["A", "B", "C", "D"], "answer": 0,
                }]},
            ],
        }
        items = final_test.build_final_quiz(chapter)
        self.assertEqual([len(item["options"]) for item in items], [2, 2, 2, 2, 4])
        self.assertNotEqual(validate_quiz_items(items), [])
        self.assertEqual(validate_quiz_items(items, allow_variable_options=True), [])
        game = EnglishQuizGame(items, allow_variable_options=True)
        self.assertEqual(len(game.questions), 5)

    def test_final_test_rejects_question_with_only_one_possible_option(self):
        chapter = {
            "subject": "english",
            "chapter_title": "Insufficient answers",
            "parts": [
                {"game": "fill_blank", "items": [
                    {"id": "f1", "sentence": "A ___", "answer": "same"},
                    {"id": "f2", "sentence": "B ___", "answer": "same"},
                ]},
                {"game": "matching", "items": [
                    {"id": "m1", "term": "one", "definition": "first"},
                    {"id": "m2", "term": "two", "definition": "second"},
                ]},
                {"game": "quiz", "items": [{
                    "id": "q1", "q": "Pick one", "options": ["A", "B", "C", "D"], "answer": 0,
                }]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "ít nhất 2 phương án"):
            final_test.build_final_quiz(chapter)

    def test_correct_answer_preserved_for_each_original_game(self):
        chapter = sample_chapter()
        expected = {
            (part["game"], item["id"]): item
            for part in chapter["parts"] for item in part["items"]
        }
        actual = final_test.build_final_quiz(chapter)
        for item in actual:
            with self.subTest(source_game=item["source_game"], source_id=item["source_id"]):
                source = expected[item["source_game"], item["source_id"]]
                if item["source_game"] == "fill_blank":
                    answer_text = source["answer"]
                elif item["source_game"] == "matching":
                    answer_text = source["definition"]
                else:
                    answer_text = source["options"][source["answer"]]
                self.assertEqual(item["options"][item["answer"]], answer_text)

    def test_source_identity_is_unique_and_traceable(self):
        items = final_test.build_final_quiz(sample_chapter())
        self.assertEqual(len(items), len({item["id"] for item in items}))
        for item in items:
            self.assertIn(item["source_game"], SOURCES)
            self.assertIsInstance(item["source_id"], str)
            self.assertTrue(item["source_id"])
        original = {(p["game"], q["id"]) for p in sample_chapter()["parts"] for q in p["items"]}
        self.assertEqual({(q["source_game"], q["source_id"]) for q in items}, original)

    def test_converted_quiz_public_view_hides_correct_answer(self):
        game = EnglishQuizGame(final_test.build_final_quiz(sample_chapter()))
        for question in game.public_view()["questions"]:
            self.assertNotIn("answer", question)
            self.assertNotIn("correct", question)
            self.assertNotIn("correct_idx", question)

    def test_converted_quiz_marks_wrong_source_question(self):
        game = EnglishQuizGame(final_test.build_final_quiz(sample_chapter()))
        wrong_question_id = game.questions[0]["id"]
        for q in game.questions:
            choice = (q["correct"] + 1) % 4 if q["id"] == wrong_question_id else q["correct"]
            game.check_one(q["id"], choice)
        result = game.result()
        self.assertEqual(result["total"], 16)
        self.assertEqual(result["score"], 15)
        self.assertEqual(result["wrong"], [wrong_question_id])
        self.assertEqual(sum(1 for r in result["review"] if not r["ok"]), 1)

    def test_building_exam_does_not_mutate_original_chapter(self):
        chapter = sample_chapter()
        untouched = deepcopy(chapter)
        final_test.build_final_quiz(chapter)
        self.assertEqual(chapter, untouched)

    def test_invalid_or_missing_part_is_rejected(self):
        chapter = sample_chapter()
        chapter["parts"] = chapter["parts"][:2]
        with self.assertRaises(ValueError):
            final_test.build_final_quiz(chapter)

    def test_duplicate_id_in_one_part_is_rejected(self):
        chapter = sample_chapter()
        chapter["parts"][0]["items"][1]["id"] = chapter["parts"][0]["items"][0]["id"]
        with self.assertRaises(ValueError):
            final_test.build_final_quiz(chapter)

    def test_empty_chapter_is_rejected(self):
        with self.assertRaises(ValueError):
            final_test.build_final_quiz({"subject": "english", "chapter_title": "Empty", "parts": []})


@unittest.skipUnless(GRADE_READY, "TDD chờ hàm calculate_grade_10(score, total)")
class FinalExamGradeAcceptanceTests(unittest.TestCase):
    """Đánh giá trên thang 10; không làm thay đổi `score`/`total`."""

    def test_full_correct_is_ten_for_any_number_of_questions(self):
        for n in (1, 3, 10, 16, 30):
            with self.subTest(total=n):
                self.assertAlmostEqual(final_test.calculate_grade_10(n, n), 10.0, places=2)

    def test_half_correct_is_five_points(self):
        for n in (10, 16, 30):
            with self.subTest(total=n):
                self.assertAlmostEqual(final_test.calculate_grade_10(n // 2, n), 5.0, places=2)

    def test_zero_correct_gets_zero(self):
        self.assertEqual(final_test.calculate_grade_10(0, 16), 0)

    def test_three_questions_uses_ten_divided_by_three(self):
        self.assertAlmostEqual(final_test.calculate_grade_10(2, 3), 20 / 3, places=2)

    def test_invalid_counts_do_not_produce_grade(self):
        for correct, total in ((0, 0), (-1, 10), (11, 10), (1, -2)):
            with self.subTest(correct=correct, total=total):
                with self.assertRaises(ValueError):
                    final_test.calculate_grade_10(correct, total)


if __name__ == "__main__":
    unittest.main()
