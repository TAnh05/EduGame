"""Phần 1: Điền vào chỗ trống. (Phụ trách: Thế Anh)"""
import streamlit as st


def normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_correct(user_answer: str, answer: str) -> bool:
    return normalize(user_answer) == normalize(answer)


def run(items: list[dict]) -> dict:
    """Hiển thị game, trả về kết quả: {'score': int, 'total': int, 'wrong': [id, ...]}."""
    # TODO: hiển thị từng câu, nhận đáp án, chấm điểm, lưu vào st.session_state.
    raise NotImplementedError
