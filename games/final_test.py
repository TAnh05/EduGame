"""Build and score a final multiple-choice quiz from one chapter."""
from __future__ import annotations

import random

GAME_NAMES = ("fill_blank", "matching", "quiz")
MAX_QUESTIONS = 30
MAX_OPTIONS = 4
MIN_OPTIONS = 2


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _validate_chapter(chapter: dict) -> dict[str, list[dict]]:
    if not isinstance(chapter, dict):
        raise ValueError("Dữ liệu chương phải là object.")
    subject = chapter.get("subject")
    title = chapter.get("chapter_title")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Chương thiếu subject hợp lệ.")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Chương thiếu chapter_title hợp lệ.")
    parts = chapter.get("parts")
    if not isinstance(parts, list):
        raise ValueError("Chương phải có danh sách parts.")

    by_game: dict[str, list[dict]] = {}
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("Phần trong chương không đúng định dạng.")
        game = part.get("game")
        if game not in GAME_NAMES or game in by_game:
            raise ValueError("Chương phải có đúng một phần cho mỗi game.")
        items = part.get("items")
        if not isinstance(items, list):
            raise ValueError(f"Phần {game} thiếu danh sách items.")
        ids = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"Dữ liệu câu hỏi của {game} không đúng định dạng.")
            qid = item.get("id")
            if not isinstance(qid, str) or not qid.strip():
                raise ValueError(f"Câu hỏi của {game} thiếu id hợp lệ.")
            ids.append(qid)
        if len(ids) != len(set(ids)):
            raise ValueError(f"Phần {game} có id bị trùng.")
        by_game[game] = items

    if set(by_game) != set(GAME_NAMES):
        raise ValueError("Chương phải có đủ fill_blank, matching và quiz.")
    if not any(by_game.values()):
        raise ValueError("Chương không có câu hỏi.")
    return by_game


def _build_options(answer: str, pool: list[str]) -> tuple[list[str], int]:
    unique = {}
    for option in [answer, *pool]:
        normalized = _normalize(option)
        if normalized:
            unique.setdefault(normalized, option)
    options = list(unique.values())
    if len(options) < MIN_OPTIONS:
        raise ValueError("Không đủ ít nhất 2 phương án khác nhau cho câu Final Test.")
    options = options[:MAX_OPTIONS]
    random.shuffle(options)
    return options, next(i for i, option in enumerate(options) if _normalize(option) == _normalize(answer))


def build_final_quiz(chapter: dict) -> list[dict]:
    """Convert the three game parts into at most 30 traceable quiz items."""
    parts = _validate_chapter(chapter)
    fill_answers = [
        item.get("answer") for item in parts["fill_blank"]
        if isinstance(item.get("answer"), str) and item["answer"].strip()
    ]
    matching_definitions = [
        item.get("definition") for item in parts["matching"]
        if isinstance(item.get("definition"), str) and item["definition"].strip()
    ]
    questions = []

    for item in parts["fill_blank"]:
        sentence = item.get("sentence")
        answer = item.get("answer")
        if not isinstance(sentence, str) or sentence.count("___") != 1:
            raise ValueError("Mỗi câu Fill Blank phải có đúng một chỗ trống '___'.")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Câu Fill Blank thiếu đáp án.")
        options, correct = _build_options(
            answer, [value for value in fill_answers if _normalize(value) != _normalize(answer)]
        )
        questions.append({
            "id": f"final:fill_blank:{item['id']}",
            "q": sentence,
            "options": options,
            "answer": correct,
            "source_game": "fill_blank",
            "source_id": item["id"],
        })

    for item in parts["matching"]:
        term, answer = item.get("term"), item.get("definition")
        if not isinstance(term, str) or not term.strip() or not isinstance(answer, str) or not answer.strip():
            raise ValueError("Câu Matching cần term và definition không rỗng.")
        options, correct = _build_options(
            answer,
            [value for value in matching_definitions if _normalize(value) != _normalize(answer)],
        )
        questions.append({
            "id": f"final:matching:{item['id']}",
            "q": f"Thuật ngữ “{term}” có nghĩa là gì?",
            "options": options,
            "answer": correct,
            "source_game": "matching",
            "source_id": item["id"],
        })

    for item in parts["quiz"]:
        question = item.get("q")
        options = item.get("options")
        answer = item.get("answer")
        if (
            not isinstance(question, str) or not question.strip()
            or not isinstance(options, list) or len(options) != 4
            or any(not isinstance(option, str) or not option.strip() for option in options)
            or not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < 4
        ):
            raise ValueError("Câu Quiz phải có nội dung, 4 phương án và đáp án từ 0 đến 3.")
        questions.append({
            "id": f"final:quiz:{item['id']}",
            "q": question,
            "options": list(options),
            "answer": answer,
            "source_game": "quiz",
            "source_id": item["id"],
        })

    if len(questions) > MAX_QUESTIONS:
        questions = random.sample(questions, MAX_QUESTIONS)
    return questions


def calculate_grade_10(score: int, total: int) -> float:
    """Return the unrounded grade on a 10-point scale."""
    if (
        not isinstance(score, int) or isinstance(score, bool)
        or not isinstance(total, int) or isinstance(total, bool)
        or total <= 0 or score < 0 or score > total
    ):
        raise ValueError("Số câu đúng và tổng số câu không hợp lệ.")
    return 10 * score / total


def run(chapter: dict) -> dict:
    """Return a validated final-test quiz and its scoring helper."""
    return {"items": build_final_quiz(chapter)}
