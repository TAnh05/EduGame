"""Phần 1: Điền vào chỗ trống - LOGIC thuần Python (không có giao diện).

Giao diện nằm ở web/fill_blank.html, nối với logic này qua server_fill_blank.py.
Dữ liệu đầu vào (items) lấy từ chapter.json:
    {"id": "p1-01", "sentence": "Vận động là ___ của vật chất.", "answer": "phương thức tồn tại"}
Kết quả theo hợp đồng chung: {"score": int, "total": int, "wrong": [id, ...]}
(kèm "review" để giao diện hiển thị). Đáp án đúng chỉ lộ ra sau khi người chơi bấm Check.
"""
from __future__ import annotations

import random
import uuid

BLANK = "___"


def _norm(text: str) -> str:
    return " ".join(str(text).split()).casefold()


def get_fill_items(data: dict) -> list[dict]:
    """Lấy items của phần điền chỗ trống từ chapter (hoặc file mẫu) đã load từ JSON."""
    for part in data.get("parts", []):
        if part.get("game") == "fill_blank":
            return part["items"]
    raise ValueError("Không tìm thấy phần 'fill_blank' trong dữ liệu JSON.")


def validate_items(items) -> list[str]:
    """Trả về danh sách lỗi (rỗng nếu dữ liệu hợp lệ)."""
    if not isinstance(items, list) or not items:
        return ["Không có câu nào để chơi."]
    problems = []
    for n, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append(f"Câu #{n} không đúng định dạng.")
            continue
        for field in ("id", "sentence", "answer"):
            if not str(it.get(field, "")).strip():
                problems.append(f"Câu #{n} thiếu trường '{field}'.")
        if str(it.get("sentence", "")).count(BLANK) != 1:
            problems.append(f"Câu #{n} phải có đúng một chỗ trống '{BLANK}'.")
    ids = [it["id"] for it in items if isinstance(it, dict) and "id" in it]
    if len(ids) != len(set(ids)):
        problems.append("Có id bị trùng nhau.")
    if not problems and len({_norm(it["answer"]) for it in items}) < 2:
        problems.append("Cần ít nhất 2 đáp án khác nhau để tạo lựa chọn.")
    return problems


class FillBlankGame:
    """Một ván điền chỗ trống. Giữ đáp án ở phía server, giao diện chỉ nhận câu đã xáo."""

    def __init__(self, items: list[dict]):
        problems = validate_items(items)
        if problems:
            raise ValueError("Dữ liệu điền chỗ trống không hợp lệ: " + "; ".join(problems))
        self.items = items
        self.id = uuid.uuid4().hex
        self.chosen: dict[str, int] = {}      # id câu -> chỉ số lựa chọn đã chốt
        self.questions = self._build()

    def _build(self) -> list[dict]:
        """Mỗi câu: đáp án đúng + tối đa 3 đáp án nhiễu lấy từ các câu khác trong chương."""
        qs = []
        for it in self.items:
            pool = {}
            for other in self.items:
                if _norm(other["answer"]) != _norm(it["answer"]):
                    pool.setdefault(_norm(other["answer"]), other["answer"])
            distractors = list(pool.values())
            random.shuffle(distractors)
            options = [it["answer"]] + distractors[:3]
            random.shuffle(options)
            before, _, after = it["sentence"].partition(BLANK)
            qs.append({"id": it["id"], "before": before, "after": after,
                       "options": options, "correct": options.index(it["answer"])})
        random.shuffle(qs)
        return qs

    def public_view(self) -> dict:
        """Dữ liệu gửi cho giao diện (KHÔNG chứa đáp án)."""
        return {"game_id": self.id, "questions": [
            {"id": q["id"], "before": q["before"], "after": q["after"],
             "options": [{"idx": j, "text": t} for j, t in enumerate(q["options"])]}
            for q in self.questions]}

    def check_one(self, qid: str, idx) -> dict:
        """Chấm một câu khi người chơi bấm Check. Đã chốt rồi thì giữ lựa chọn cũ."""
        q = next((q for q in self.questions if q["id"] == qid), None)
        if q is None:
            raise ValueError("Câu hỏi không tồn tại.")
        if qid not in self.chosen:
            if not isinstance(idx, int) or isinstance(idx, bool) or not 0 <= idx < len(q["options"]):
                raise ValueError("Lựa chọn không hợp lệ.")
            self.chosen[qid] = idx
        return {"ok": self.chosen[qid] == q["correct"], "correct_idx": q["correct"],
                "correct_text": q["options"][q["correct"]]}

    def result(self) -> dict:
        """Kết quả cả ván, theo hợp đồng chung: score, total, wrong (+ review)."""
        if len(self.chosen) != len(self.questions):
            raise ValueError("Chưa trả lời hết các câu.")
        wrong, review = [], []
        for q in self.questions:
            ok = self.chosen[q["id"]] == q["correct"]
            if not ok:
                wrong.append(q["id"])
            review.append({"id": q["id"], "sentence": q["before"] + "___" + q["after"],
                           "chosen": q["options"][self.chosen[q["id"]]],
                           "correct": q["options"][q["correct"]], "ok": ok})
        return {"score": len(self.questions) - len(wrong), "total": len(self.questions),
                "wrong": wrong, "review": review}
