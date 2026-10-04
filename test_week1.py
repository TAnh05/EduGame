"""
test_week1.py
Kịch bản kiểm thử tự động (Unit Test) cho module kiểm tra Schema dữ liệu:
1. Kiểm tra tính hợp lệ của file sample_chapter.json (Hợp đồng JSON).
2. Kiểm tra khung Pydantic bắt lỗi chính xác theo Mục 6.2 của báo cáo.
3. Kiểm tra hàm loại bỏ Markdown code fence.
4. Kiểm tra hàm chia văn bản làm 3 phần.
5. Kiểm tra hàm lấy prompt cho 3 game và 2 môn học.
"""

import os
import sys
import json
import pytest

# Thiết lập UTF-8 cho terminal Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
from pydantic import ValidationError
from ai_generate import (
    ChapterModel,
    load_chapter_from_file,
    validate_chapter_data,
    strip_markdown_fence,
    split_text_into_three_parts,
)
from prompts import get_game_prompt


def test_sample_chapter_json_valid():
    """Kiểm tra file dữ liệu mẫu dùng cho cả nhóm đạt chuẩn 100%"""
    file_path = os.path.join("data", "sample_chapter.json")
    assert os.path.exists(file_path), "Không tìm thấy file data/sample_chapter.json"
    chapter = load_chapter_from_file(file_path)
    assert chapter.subject in ["english", "philosophy"]
    assert len(chapter.parts) == 3
    assert [p.part for p in chapter.parts] == [1, 2, 3]
    print("\n[PASS] sample_chapter.json hợp lệ với Pydantic schema!")


def test_markdown_fence_stripping():
    """Quy tắc 6.2: Loại bỏ markdown code fence trước khi parse"""
    raw_markdown = """```json
    {
      "subject": "english",
      "chapter_title": "Vocabulary Unit 1",
      "parts": [
        {"part": 1, "game": "fill_blank", "items": [{"id": "1", "sentence": "He is ___ boy.", "answer": "a"}]},
        {"part": 2, "game": "matching", "items": [{"id": "2", "term": "Apple", "definition": "A fruit"}]},
        {"part": 3, "game": "quiz", "items": [{"id": "3", "q": "Color?", "options": ["Red", "Blue", "Green", "Pink"], "answer": 0}]}
      ]
    }
    ```"""
    chapter = validate_chapter_data(raw_markdown)
    assert chapter.subject == "english"
    print("[PASS] Đã loại bỏ code fence và parse JSON thành công!")


def test_split_text_into_three_parts():
    """Quy tắc 7.2: Chia văn bản thành 3 phần"""
    text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3.\nĐoạn 4.\nĐoạn 5.\nĐoạn 6."
    parts = split_text_into_three_parts(text)
    assert len(parts) == 3
    assert all(len(p) > 0 for p in parts)
    print("[PASS] Chia văn bản thành 3 phần hoạt động chuẩn xác!")


def test_prompts_generation():
    """Kiểm tra gọi prompt cho 3 phần và 2 môn"""
    dummy_text = "Nội dung bài học mẫu..."
    for subject in ["english", "philosophy"]:
        for part_num in [1, 2, 3]:
            prompt = get_game_prompt(part_num, subject, dummy_text)
            assert dummy_text in prompt
            assert "JSON" in prompt
    print("[PASS] Tất cả Prompt cho 3 game và 2 môn đều được tạo đúng!")


def test_pydantic_validation_rules():
    """Kiểm tra khung Pydantic bắt đúng các lỗi theo đặc tả Mục 6.2"""
    # 1. Sai môn học (không phải english hoặc philosophy)
    bad_data = {
        "subject": "math",
        "chapter_title": "Toán",
        "parts": [
            {"part": 1, "game": "fill_blank", "items": [{"sentence": "1 + 1 = ___", "answer": "2"}]},
            {"part": 2, "game": "matching", "items": [{"term": "T", "definition": "D"}]},
            {"part": 3, "game": "quiz", "items": [{"q": "Q", "options": ["1", "2", "3", "4"], "answer": 0}]}
        ]
    }
    with pytest.raises(ValidationError):
        validate_chapter_data(bad_data)

    # 2. Sai game 1: không chứa ký hiệu '___'
    bad_fill = bad_data.copy()
    bad_fill["subject"] = "philosophy"
    bad_fill["parts"][0]["items"][0]["sentence"] = "Câu này không có chỗ đục lỗ"
    with pytest.raises(ValidationError):
        validate_chapter_data(bad_fill)

    # 3. Sai game 3: options không đủ 4 phần tử
    bad_quiz = bad_data.copy()
    bad_quiz["subject"] = "philosophy"
    bad_quiz["parts"][0]["items"][0]["sentence"] = "Câu có ___ đục lỗ"
    bad_quiz["parts"][2]["items"][0]["options"] = ["A", "B"]  # chỉ có 2 options
    with pytest.raises(ValidationError):
        validate_chapter_data(bad_quiz)

    # 4. Sai game 3: answer vượt ngoài khoảng 0..3 (Mục 6.2)
    bad_answer = bad_data.copy()
    bad_answer["subject"] = "philosophy"
    bad_answer["parts"][0]["items"][0]["sentence"] = "Câu có ___ đục lỗ"
    bad_answer["parts"][2]["items"][0]["options"] = ["A", "B", "C", "D"]
    bad_answer["parts"][2]["items"][0]["answer"] = 5  # ngoài 0..3
    with pytest.raises(ValidationError):
        validate_chapter_data(bad_answer)

    print("[PASS] Pydantic bắt lỗi vi phạm quy tắc cực kỳ chính xác!")


if __name__ == "__main__":
    test_sample_chapter_json_valid()
    test_markdown_fence_stripping()
    test_split_text_into_three_parts()
    test_prompts_generation()
    test_pydantic_validation_rules()
    print("\n==========================================")
    print("TẤT CẢ CÁC BÀI TEST TUẦN 1 CỦA SANG ĐÃ PASS 100%!")
    print("==========================================")
