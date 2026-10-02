"""Phần 2: Nối từ (thuật ngữ <-> định nghĩa). (Phụ trách: Thế Anh)"""
import random

import streamlit as st


def shuffle_definitions(items: list[dict]) -> list[str]:
    definitions = [item["definition"] for item in items]
    random.shuffle(definitions)
    return definitions


def score_pairs(items: list[dict], user_pairs: dict[str, str]) -> int:
    """user_pairs: {term: definition người dùng chọn}. Trả về số cặp đúng."""
    return sum(1 for item in items if user_pairs.get(item["term"]) == item["definition"])


def run(items: list[dict]) -> dict:
    """Hiển thị game, trả về kết quả: {'score': int, 'total': int, 'wrong': [id, ...]}."""
    # TODO: hiển thị term + danh sách definition đã xáo trộn, nhận cặp ghép, chấm điểm.
    raise NotImplementedError
