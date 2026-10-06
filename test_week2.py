"""
test_week2.py
Kịch bản kiểm thử toàn diện cho các nhiệm vụ Tuần 2 của Sang:
1. Kiểm tra cơ chế Retry tối đa 2 lần khi AI trả dữ liệu sai format (Mục 7.2 & 6.2).
2. Kiểm tra việc bóc tách markdown code fence từ output AI.
3. Kiểm tra kiểm định Pydantic schema cho từng game và toàn bộ chapter.
4. Kiểm tra pipeline sinh chapter hoàn chỉnh từ văn bản và lưu ra file.
5. Kiểm tra cơ chế Fallback mẫu dự phòng khi gặp sự cố API (Mục 11 & TC08).
"""

import os
import sys
import json
import pytest

# Thiết lập UTF-8 cho console
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

from pydantic import ValidationError
from ai_generate import (
    FillBlankItem,
    MatchingItem,
    QuizItem,
    Part1FillBlank,
    Part2Matching,
    Part3Quiz,
    ChapterModel,
    generate_part_with_retry,
    generate_chapter,
    load_chapter_from_file,
    save_chapter_to_file,
)


# =====================================================================
# DỮ LIỆU MOCK PHỤC VỤ TEST TỰ ĐỘNG
# =====================================================================

MOCK_RAW_PART1_VALID = """```json
{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {"id": "p1-01", "sentence": "Vật chất là ___ khách quan.", "answer": "thực tại"}
  ]
}
```"""

MOCK_RAW_PART2_VALID = """```json
{
  "part": 2,
  "game": "matching",
  "items": [
    {"id": "p2-01", "term": "Vật chất", "definition": "Thực tại khách quan tồn tại độc lập với ý thức."}
  ]
}
```"""

MOCK_RAW_PART3_VALID = """```json
{
  "part": 3,
  "game": "quiz",
  "items": [
    {
      "id": "p3-01",
      "q": "Vận động là gì?",
      "options": ["Đứng im", "Phương thức tồn tại của vật chất", "Ảo giác", "Tự nhiên"],
      "answer": 1
    }
  ]
}
```"""

MOCK_RAW_INVALID_SYNTAX = "Đây là văn bản lỗi, không phải JSON!"

MOCK_RAW_INVALID_SCHEMA = """```json
{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {"id": "p1-01", "sentence": "Câu này không có ba dấu gạch dưới", "answer": "sai"}
  ]
}
```"""


# =====================================================================
# TEST CASES
# =====================================================================

def test_retry_success_after_first_failure():
    """Kiểm tra: Lần 1 trả JSON lỗi -> Lần 2 trả JSON chuẩn -> Thành công (1 lần retry)"""
    call_count = 0

    def mock_caller(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MOCK_RAW_INVALID_SYNTAX  # Lần 1 lỗi cú pháp
        return MOCK_RAW_PART1_VALID         # Lần 2 thành công

    part = generate_part_with_retry(
        part_num=1,
        subject="philosophy",
        text_part="Đoạn văn bản mẫu...",
        max_retries=2,
        custom_caller=mock_caller
    )

    assert call_count == 2
    assert part.game == "fill_blank"
    assert len(part.items) == 1
    assert part.items[0].answer == "thực tại"
    print("\n[PASS] Cơ chế Retry lần 1 thành công!")


def test_retry_success_after_schema_failure():
    """Kiểm tra: Lần 1 sai schema Pydantic -> Lần 2 thử lại chuẩn -> Thành công"""
    call_count = 0

    def mock_caller(prompt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MOCK_RAW_INVALID_SCHEMA  # Thiếu '___'
        return MOCK_RAW_PART1_VALID

    part = generate_part_with_retry(
        part_num=1,
        subject="philosophy",
        text_part="Đoạn văn bản...",
        max_retries=2,
        custom_caller=mock_caller
    )

    assert call_count == 2
    assert part.items[0].sentence.count("___") == 1
    print("[PASS] Pydantic bắt lỗi và retry thành công!")


def test_retry_exhaustion_raises_runtime_error():
    """Kiểm tra: Thử quá 2 lần retry (tổng 3 lần) mà vẫn lỗi -> Ném RuntimeError chuẩn xác"""
    call_count = 0

    def always_fail_caller(prompt):
        nonlocal call_count
        call_count += 1
        return MOCK_RAW_INVALID_SYNTAX

    with pytest.raises(RuntimeError) as exc_info:
        generate_part_with_retry(
            part_num=2,
            subject="philosophy",
            text_part="Đoạn văn...",
            max_retries=2,
            custom_caller=always_fail_caller,
        )

    # 1 lần gọi ban đầu + 2 lần retry = 3 lần gọi
    assert call_count == 3
    assert "sau 2 lần thử lại" in str(exc_info.value)
    print("[PASS] Đã thử đúng tối đa 2 lần retry trước khi dừng!")


def test_generate_chapter_end_to_end_and_save():
    """Kiểm tra pipeline sinh đầy đủ 3 phần và lưu file chapter.json"""
    def mock_caller(prompt):
        if "fill_blank" in prompt or "Điền vào chỗ trống" in prompt:
            return MOCK_RAW_PART1_VALID
        elif "matching" in prompt or "Nối từ" in prompt:
            return MOCK_RAW_PART2_VALID
        elif "quiz" in prompt or "Trắc nghiệm" in prompt:
            return MOCK_RAW_PART3_VALID
        return MOCK_RAW_PART1_VALID

    clean_text = "Đoạn 1 về triết học.\n\nĐoạn 2 về các phạm trù.\n\nĐoạn 3 về quy luật."
    test_out = os.path.join("data", "test_generated_chapter.json")

    chapter = generate_chapter(
        clean_text=clean_text,
        subject="philosophy",
        chapter_title="Chương 1: Triết học Mác - Lênin",
        output_path=test_out,
        max_retries=2,
        custom_caller=mock_caller,
    )

    # Kiểm tra object
    assert chapter.subject == "philosophy"
    assert chapter.chapter_title == "Chương 1: Triết học Mác - Lênin"
    assert len(chapter.parts) == 3
    assert [p.part for p in chapter.parts] == [1, 2, 3]
    assert [p.game for p in chapter.parts] == ["fill_blank", "matching", "quiz"]

    # Kiểm tra file được lưu trên đĩa
    assert os.path.exists(test_out)
    loaded = load_chapter_from_file(test_out)
    assert loaded.subject == "philosophy"
    assert len(loaded.parts) == 3

    # Dọn dẹp file test
    if os.path.exists(test_out):
        os.remove(test_out)

    print("[PASS] Pipeline sinh Chapter đầy đủ 3 phần & lưu JSON chuẩn hợp đồng 100%!")


def test_fallback_mechanism_when_api_disconnected():
    """Kiểm tra Mục 11 & TC08: Khi API lỗi hoàn toàn, fallback tự động nạp sample_chapter.json"""
    def broken_caller(prompt):
        raise ConnectionError("Mất mạng hoặc API timeout!")

    test_out = os.path.join("data", "test_fallback_chapter.json")

    chapter = generate_chapter(
        clean_text="Đoạn văn bản...",
        subject="philosophy",
        chapter_title="Chương Test",
        output_path=test_out,
        max_retries=2,
        custom_caller=broken_caller,
        use_fallback_on_failure=True
    )

    assert chapter is not None
    assert len(chapter.parts) == 3
    assert os.path.exists(test_out)

    # Dọn dẹp
    if os.path.exists(test_out):
        os.remove(test_out)

    print("[PASS] Cơ chế fallback dữ liệu dự phòng (Mục 11, TC08) hoạt động chính xác!")


if __name__ == "__main__":
    test_retry_success_after_first_failure()
    test_retry_success_after_schema_failure()
    test_retry_exhaustion_raises_runtime_error()
    test_generate_chapter_end_to_end_and_save()
    test_fallback_mechanism_when_api_disconnected()
    print("\n========================================================")
    print("TẤT CẢ CÁC BÀI TEST TUẦN 2 CỦA SANG ĐÃ PASS HOÀN TOÀN 100%!")
    print("========================================================")
