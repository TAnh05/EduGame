"""
test_3.py
Kịch bản kiểm thử tự động cho các ca ngoại lệ, biên dữ liệu và cơ chế phụ trợ:
- Kiểm thử các ca biên đầu vào:
    + TC04: Văn bản quá ngắn / khó đọc
    + TC05: File rỗng / văn bản rỗng
    + TC06: Giới hạn độ dài văn bản an toàn
    + TC07: Bắt lỗi cú pháp AI và giới hạn số lần retry
    + TC08: Cơ chế fallback nạp dữ liệu mẫu khi ngắt kết nối
- Kiểm thử cơ chế Cache F09 (tái sử dụng JSON không gọi lại API)
- Kiểm thử bộ sinh câu hỏi Game cuối 10 câu theo tỷ lệ 3-3-4
"""

import os
import sys
import json
import pytest

# Thiết lập UTF-8 cho console Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

from ai_generate import (
    generate_chapter,
    generate_part_with_retry,
    validate_input_text,
    create_final_quiz_pool,
    load_chapter_from_file,
    AIProcessingError,
    ChapterModel,
)


MOCK_RAW_PART1_VALID = """```json
{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {"id": "p1-01", "sentence": "Vật chất là ___ khách quan.", "answer": "thực tại"},
    {"id": "p1-02", "sentence": "Ý thức là hình ảnh chủ quan của thế giới ___.", "answer": "khách quan"},
    {"id": "p1-03", "sentence": "Vận động là phương thức tồn tại của ___.", "answer": "vật chất"}
  ]
}
```"""

MOCK_RAW_PART2_VALID = """```json
{
  "part": 2,
  "game": "matching",
  "items": [
    {"id": "p2-01", "term": "Vật chất", "definition": "Thực tại khách quan tồn tại độc lập với ý thức."},
    {"id": "p2-02", "term": "Vận động", "definition": "Phương thức tồn tại của vật chất."},
    {"id": "p2-03", "term": "Ý thức", "definition": "Hình ảnh chủ quan của thế giới khách quan."}
  ]
}
```"""

MOCK_RAW_PART3_VALID = """```json
{
  "part": 3,
  "game": "quiz",
  "items": [
    {"id": "p3-01", "q": "Vận động là gì?", "options": ["Đứng im", "Phương thức tồn tại", "Ảo giác", "Tự nhiên"], "answer": 1},
    {"id": "p3-02", "q": "Nguồn gốc tự nhiên của ý thức?", "options": ["Bộ óc người", "Thần linh", "Tự nhiên vô tri", "Không có"], "answer": 0},
    {"id": "p3-03", "q": "Vật chất có trước hay ý thức có trước?", "options": ["Vật chất có trước", "Ý thức có trước", "Đồng thời", "Không biết"], "answer": 0},
    {"id": "p3-04", "q": "Ý thức có tính chất gì?", "options": ["Thụ động", "Năng động sáng tạo", "Cố định", "Vô thức"], "answer": 1}
  ]
}
```"""

VALID_LONG_TEXT = (
    "Vật chất là phạm trù triết học dùng để chỉ thực tại khách quan được đem lại cho con người trong cảm giác. "
    "Vận động là phương thức tồn tại của vật chất, là thuộc tính cố hữu của vật chất trong tự nhiên và xã hội. "
    "Ý thức là hình ảnh chủ quan của thế giới khách quan, là sự phản ánh tích cực, năng động, sáng tạo vào bộ óc con người."
)


def mock_working_caller(prompt):
    if "fill_blank" in prompt or "Điền vào chỗ trống" in prompt:
        return MOCK_RAW_PART1_VALID
    elif "matching" in prompt or "Nối từ" in prompt:
        return MOCK_RAW_PART2_VALID
    elif "quiz" in prompt or "Trắc nghiệm" in prompt:
        return MOCK_RAW_PART3_VALID
    return MOCK_RAW_PART1_VALID


# BÀI TEST 1: TC05 - XỬ LÝ VĂN BẢN RỖNG / FILE RỖNG

def test_tc05_empty_input():
    """TC05: File rỗng hoặc văn bản rỗng -> Không crash, báo lỗi tiếng Việt thân thiện"""
    with pytest.raises(AIProcessingError) as exc_info:
        generate_chapter(clean_text="   ", subject="philosophy")
    assert "TC05" in str(exc_info.value)
    print("\n[PASS - TC05] Bắt lỗi văn bản rỗng chuẩn xác, không crash ứng dụng!")


# BÀI TEST 2: TC04 - XỬ LÝ VĂN BẢN QUÁ NGẮN (< 50 KÝ TỰ)

def test_tc04_short_input():
    """TC04: Văn bản quá ngắn không đủ sinh 3 game -> Báo lỗi rõ ràng"""
    short_text = "Đoạn văn ngắn quá."
    with pytest.raises(AIProcessingError) as exc_info:
        generate_chapter(clean_text=short_text, subject="philosophy")
    assert "TC04" in str(exc_info.value)
    print("[PASS - TC04] Bắt lỗi văn bản quá ngắn (< 50 ký tự) thành công!")


# BÀI TEST 3: TC06 - GIỚI HẠN ĐỘ DÀI VĂN BẢN QUÁ LỚN

def test_tc06_long_input_truncation():
    """TC06: Văn bản quá lớn (> 15.000 ký tự) tự động cắt tỉa an toàn để tránh quá tải/hết quota"""
    giant_text = VALID_LONG_TEXT * 100  # > 25.000 ký tự
    clipped = validate_input_text(giant_text)
    assert len(clipped) <= 15000
    print("[PASS - TC06] Tự động cắt tỉa văn bản quá lớn an toàn thành công!")


# BÀI TEST 4: TC07 - AI TRẢ SAI JSON HOẶC QUÁ SỐ LẦN RETRY

def test_tc07_ai_invalid_json_exhaustion():
    """TC07: AI trả dữ liệu không phải JSON -> Bắt lỗi và retry, vượt 2 lần thì dừng"""
    call_count = 0
    def broken_json_caller(prompt):
        nonlocal call_count
        call_count += 1
        return "Lỗi cú pháp không parse được"

    with pytest.raises(AIProcessingError) as exc_info:
        generate_part_with_retry(
            part_num=1,
            subject="philosophy",
            text_part=VALID_LONG_TEXT,
            max_retries=2,
            custom_caller=broken_json_caller
        )
    assert call_count == 3  # 1 lần đầu + 2 lần retry
    assert "TC07" in str(exc_info.value)
    print("[PASS - TC07] Pydantic & Retry xử lý AI trả sai JSON đạt chuẩn!")


# BÀI TEST 5: TC08 - API LỖI KHI DEMO -> TỰ ĐỘNG FALLBACK DỰ PHÒNG

def test_tc08_api_failure_fallback():
    """TC08: API bị ngắt hoặc hết quota lúc demo -> Tự động kích hoạt sample_chapter.json"""
    def disconnected_caller(prompt):
        raise ConnectionResetError("Mất mạng khi đang demo!")

    test_out = os.path.join("data", "test_fallback_temp.json")
    chapter = generate_chapter(
        clean_text=VALID_LONG_TEXT,
        subject="philosophy",
        output_path=test_out,
        custom_caller=disconnected_caller,
        use_fallback_on_failure=True,
        use_cache=False
    )
    assert chapter is not None
    assert len(chapter.parts) == 3
    assert os.path.exists(test_out)

    if os.path.exists(test_out):
        os.remove(test_out)
    print("[PASS - TC08] Cơ chế Fallback mẫu dự phòng kích hoạt mượt mà khi API lỗi!")


# BÀI TEST 6: F09 - CƠ CHẾ CACHE (KHÔNG GỌI LẠI AI KHI CHƠI LẠI)

def test_f09_cache_mechanism():
    """F09: File JSON đã tồn tại -> Nạp lại từ đĩa, không gọi AI tốn chi phí"""
    test_out = os.path.join("data", "test_cache_temp.json")
    ai_called = False

    def spy_caller(prompt):
        nonlocal ai_called
        ai_called = True
        return mock_working_caller(prompt)

    # Lần 1: Chưa có file -> Phải gọi AI sinh và lưu
    ch1 = generate_chapter(
        clean_text=VALID_LONG_TEXT,
        subject="philosophy",
        output_path=test_out,
        custom_caller=spy_caller,
        use_cache=True
    )
    assert ai_called is True

    # Lần 2: Đã có file cache -> KHÔNG được gọi AI
    ai_called = False
    ch2 = generate_chapter(
        clean_text=VALID_LONG_TEXT,
        subject="philosophy",
        output_path=test_out,
        custom_caller=spy_caller,
        use_cache=True
    )
    assert ai_called is False
    assert ch2.subject == ch1.subject

    if os.path.exists(test_out):
        os.remove(test_out)
    print("[PASS - F09] Cơ chế Cache hoạt động hoàn hảo, tiết kiệm 100% quota API khi chơi lại!")


# BÀI TEST 7: TẠO GAME CUỐI TỶ LỆ 3-3-4

def test_create_final_quiz_pool_3_3_4():
    """Game cuối lấy tỷ lệ 3-3-4 từ 3 game thành quiz, lưu source_part và source_id"""
    test_out = os.path.join("data", "test_pool_temp.json")
    chapter = generate_chapter(
        clean_text=VALID_LONG_TEXT,
        subject="philosophy",
        output_path=test_out,
        custom_caller=mock_working_caller,
        use_cache=False
    )

    final_pool = create_final_quiz_pool(chapter, num_part1=3, num_part2=3, num_part3=4)

    assert len(final_pool) == 10
    part1_count = sum(1 for q in final_pool if q["source_part"] == 1)
    part2_count = sum(1 for q in final_pool if q["source_part"] == 2)
    part3_count = sum(1 for q in final_pool if q["source_part"] == 3)

    assert part1_count == 3
    assert part2_count == 3
    assert part3_count == 4

    # Kiểm tra mỗi câu quiz đều có đủ 4 lựa chọn và đáp án hợp lệ 0..3
    for q in final_pool:
        assert len(q["options"]) == 4
        assert 0 <= q["answer"] <= 3
        assert q["source_id"] != ""

    if os.path.exists(test_out):
        os.remove(test_out)
    print("[PASS] Tạo Game cuối 10 câu tỷ lệ 3-3-4 và lưu truy vết câu sai thành công 100%!")


if __name__ == "__main__":
    test_tc05_empty_input()
    test_tc04_short_input()
    test_tc06_long_input_truncation()
    test_tc07_ai_invalid_json_exhaustion()
    test_tc08_api_failure_fallback()
    test_f09_cache_mechanism()
    test_create_final_quiz_pool_3_3_4()
    print("\n========================================================")
    print("TẤT CẢ BÀI TEST TRONG TEST_3 ĐÃ PASS!")
    print("========================================================")
