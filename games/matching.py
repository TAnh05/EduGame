"""Phần 2: Nối từ - LOGIC thuần Python (không có giao diện). (Phụ trách: Thế Anh)

Giao diện nằm ở web/matching.html, nối với logic này qua server.py.
Dữ liệu đầu vào (items) lấy từ chapter.json:
    {"id": "p2-01", "term": "luggage", "definition": "hành lý"}
Kết quả chấm điểm theo hợp đồng chung: {"score": int, "total": int, "wrong": [id, ...]}
(kèm thêm "review" để giao diện hiển thị; summary.py có thể bỏ qua khóa này).
"""
from __future__ import annotations

import random
import threading
import unicodedata
import uuid
from copy import deepcopy


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", " ".join(text.split()).casefold())


def shuffle_definitions(items: list[dict]) -> list[str]:
    definitions = [item["definition"] for item in items]
    random.shuffle(definitions)
    return definitions


def score_pairs(items: list[dict], user_pairs: dict[str, str]) -> int:
    """user_pairs: {term: definition người dùng chọn}. Trả về số cặp đúng."""
    return sum(1 for item in items if user_pairs.get(item["term"]) == item["definition"])


def wrong_ids(items: list[dict], user_pairs: dict[str, str]) -> list[str]:
    """user_pairs: {id: definition người dùng chọn}. Trả về id các cặp ghép sai."""
    return [it["id"] for it in items if user_pairs.get(it["id"]) != it["definition"]]


def get_matching_items(data: dict) -> list[dict]:
    """Lấy items của phần nối từ từ chapter (hoặc file mẫu) đã load từ JSON."""
    for part in data.get("parts", []):
        if part.get("game") == "matching":
            return part["items"]
    raise ValueError("Không tìm thấy phần 'matching' trong dữ liệu JSON.")


def validate_items(items) -> list[str]:
    """Trả về danh sách lỗi (rỗng nếu dữ liệu hợp lệ)."""
    if not isinstance(items, list) or not items:
        return ["Không có cặp từ nào để chơi."]
    problems = []
    for n, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append(f"Cặp #{n} không đúng định dạng.")
            continue
        for field in ("id", "term", "definition"):
            value = it.get(field)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"Cặp #{n} thiếu trường '{field}' hợp lệ.")
    ids = [
        it["id"].strip() for it in items
        if isinstance(it, dict) and isinstance(it.get("id"), str) and it["id"].strip()
    ]
    if len(ids) != len(set(ids)):
        problems.append("Có id bị trùng nhau.")
    if not problems:
        if len({_norm(it["term"]) for it in items}) != len(items):
            problems.append("Có thuật ngữ bị trùng hoặc nhập nhằng.")
        if len({_norm(it["definition"]) for it in items}) != len(items):
            problems.append("Có định nghĩa bị trùng hoặc nhập nhằng.")
    return problems


def _new_order(items: list[dict]) -> list[str]:
    """Xáo định nghĩa, cố tránh trùng đúng thứ tự gốc."""
    original = [it["definition"] for it in items]
    order = shuffle_definitions(items)
    for _ in range(10):
        if len(items) < 2 or order != original:
            break
        order = shuffle_definitions(items)
    return order


class MatchingGame:
    """Một ván nối từ. Giữ đáp án ở phía server, giao diện chỉ nhận dữ liệu đã xáo."""

    def __init__(self, items: list[dict]):
        problems = validate_items(items)
        if problems:
            raise ValueError("Dữ liệu nối từ không hợp lệ: " + "; ".join(problems))
        self.items = items
        self.order = _new_order(items)      # định nghĩa đã xáo; giao diện chỉ biết chỉ số
        self.id = uuid.uuid4().hex
        self._check_lock = threading.Lock()
        self._result: dict | None = None

    def public_view(self) -> dict:
        """Dữ liệu gửi cho giao diện (KHÔNG chứa đáp án)."""
        return {
            "game_id": self.id,
            "terms": [{"id": it["id"], "term": it["term"]} for it in self.items],
            "definitions": [{"idx": j, "text": t} for j, t in enumerate(self.order)],
        }

    def check(self, pairs: dict) -> dict:
        """pairs: {term_id: chỉ số định nghĩa}. Trả về kết quả chấm điểm."""
        with self._check_lock:
            return self._check(pairs)

    def _check(self, pairs: dict) -> dict:
        if self._result is not None:
            return deepcopy(self._result)
        if not isinstance(pairs, dict) or set(pairs) != {it["id"] for it in self.items}:
            raise ValueError("Chưa ghép đủ các cặp.")
        idxs = list(pairs.values())
        if len(set(idxs)) != len(idxs) or any(
            not isinstance(j, int) or isinstance(j, bool) or not 0 <= j < len(self.order)
            for j in idxs
        ):
            raise ValueError("Lựa chọn không hợp lệ.")
        chosen = {tid: self.order[j] for tid, j in pairs.items()}
        wrong = wrong_ids(self.items, chosen)
        review = [
            {"id": it["id"], "term": it["term"], "chosen": chosen[it["id"]],
             "correct": it["definition"], "ok": it["id"] not in wrong}
            for it in self.items
        ]
        self._result = {
            "score": len(self.items) - len(wrong), "total": len(self.items),
            "wrong": wrong, "review": review,
        }
        return deepcopy(self._result)
