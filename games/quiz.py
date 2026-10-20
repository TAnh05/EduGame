"""Phần trắc nghiệm - logic thuần Python, không phụ thuộc giao diện."""
from __future__ import annotations

import random
import uuid

BLANK = "___"

def get_quiz_items(data: dict) -> list[dict]:
    for part in data.get("parts", []):
        if part.get("game") == "quiz":
            return part["items"]
    raise ValueError("Không tìm thấy phần 'quiz' trong dữ liệu JSON.")

def validate_items(items: list[dict]) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["Không có câu nào để chơi."]
    problems = []
    ids = []
    for n, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append(f"Câu #{n} không đúng định dạng.")
            continue
        qid = it.get("id")
        if not isinstance(qid, str) or not qid.strip():
            problems.append(f"Câu #{n} thiếu trường 'id'.")
        else:
            ids.append(qid)
        question_text = it.get("q", it.get("sentence", ""))
        if not isinstance(question_text, str) or not question_text.strip():
            problems.append(f"Câu #{n} thiếu nội dung câu hỏi.")
        options = it.get("options")
        if (
            not isinstance(options, list)
            or len(options) != 4
            or any(not isinstance(option, str) or not option.strip() for option in options)
        ):
            problems.append(f"Câu #{n} phải có đúng 4 phương án không rỗng.")
        answer = it.get("answer")
        if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer < 4:
            problems.append(f"Câu #{n} phải có đáp án là chỉ số từ 0 đến 3.")
    if len(ids) != len(set(ids)):
        problems.append("Có id bị trùng nhau.")
    return problems

class EnglishQuizGame:
    def __init__(self, items: list[dict]):
        problems = validate_items(items)
        if problems:
            raise ValueError("Dữ liệu câu hỏi không hợp lệ: " + "; ".join(problems))
        self.items = items
        self.id = uuid.uuid4().hex
        self.chosen: dict[str, int] = {}
        self.questions = self._build()

    def _build(self) -> list[dict]:
        qs = []
        for it in self.items:
            q_text = it.get("sentence", it.get("q", ""))
            options = list(it["options"])
            correct_idx = it["answer"]
            is_blank = BLANK in q_text or "___" in q_text
            if is_blank:
                if BLANK not in q_text:
                    q_text = q_text.replace("___", BLANK)
                before, _, after = q_text.partition(BLANK)
            else:
                before, after = q_text, ""

            qs.append({
                "id": it["id"],
                "before": before,
                "after": after,
                "is_blank": is_blank,
                "question_text": q_text,
                "options": options,
                "correct": correct_idx
            })
        random.shuffle(qs)
        return qs

    def public_view(self) -> dict:
        return {
            "game_id": self.id,
            "questions": [
                {
                    "id": q["id"],
                    "before": q["before"],
                    "after": q["after"],
                    "is_blank": q["is_blank"],
                    "options": [{"idx": j, "text": t} for j, t in enumerate(q["options"])]
                }
                for q in self.questions
            ]
        }

    def check_one(self, qid: str, idx) -> dict:
        q = next((q for q in self.questions if q["id"] == qid), None)
        if q is None:
            raise ValueError("Câu hỏi không tồn tại.")
        if qid not in self.chosen:
            if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(q["options"]):
                raise ValueError("Lựa chọn không hợp lệ.")
            self.chosen[qid] = idx
        return {
            "ok": self.chosen[qid] == q["correct"],
            "correct_idx": q["correct"],
            "correct_text": q["options"][q["correct"]]
        }

    def result(self) -> dict:
        if len(self.chosen) != len(self.questions):
            raise ValueError("Chưa trả lời hết các câu.")
        wrong, review = [], []
        for q in self.questions:
            ok = self.chosen[q["id"]] == q["correct"]
            if not ok:
                wrong.append(q["id"])
            review.append({
                "id": q["id"],
                "sentence": q["question_text"],
                "chosen": q["options"][self.chosen[q["id"]]],
                "correct": q["options"][q["correct"]],
                "ok": ok
            })
        return {
            "score": len(self.questions) - len(wrong),
            "total": len(self.questions),
            "wrong": wrong,
            "review": review
        }