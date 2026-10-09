"""
demo.py
Kịch bản demo mô phỏng quy trình hoạt động của pipeline:
1. Tiếp nhận văn bản học tập mẫu (Triết học / Tiếng Anh).
2. Tự động phân đoạn nội dung thành 3 phần cho 3 dạng bài tập.
3. Sinh câu hỏi và kiểm định Schema qua Pydantic.
4. Xuất file JSON hoàn chỉnh để các module trò chơi sử dụng.
"""

import os
import sys
import json
import time

# Thiết lập UTF-8 hiển thị tiếng Việt trên Windows terminal
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")

from ai_generate import (
    split_text_into_three_parts,
    validate_chapter_data,
    save_chapter_to_file,
    ChapterModel,
    Part1FillBlank,
    Part2Matching,
    Part3Quiz,
    FillBlankItem,
    MatchingItem,
    QuizItem,
)

SAMPLE_TEXT_DEMO = """
Vật chất là phạm trù triết học dùng để chỉ thực tại khách quan được đem lại cho con người trong cảm giác, được cảm giác của chúng ta chép lại, chụp lại, phản ánh, và tồn tại không lệ thuộc vào cảm giác.

Vận động là phương thức tồn tại của vật chất, là thuộc tính cố hữu của vật chất, bao gồm tất cả mọi sự thay đổi và mọi quá trình diễn ra trong vũ trụ, kể từ sự thay đổi vị trí đơn giản cho đến tư duy.

Ý thức là hình ảnh chủ quan của thế giới khách quan, là sự phản ánh tích cực, năng động, sáng tạo thế giới hiện thực vào trong bộ óc con người. Nguồn gốc tự nhiên của ý thức là bộ óc người và thế giới khách quan tác động lên bộ óc.
"""

def print_separator(title=""):
    print("\n" + "=" * 60)
    if title:
        print(f" {title.upper()} ")
        print("=" * 60)

def run_demo():
    print_separator("DEMO PIPELINE SINH DỮ LIỆU CÂU HỎI & KIỂM ĐỊNH SCHEMA")
    print("▶ BƯỚC 1: TIẾP NHẬN VĂN BẢN ĐẦU VÀO & MÔN HỌC")
    print(f"  • Môn học: 'philosophy' (Triết học)")
    print(f"  • Độ dài văn bản: {len(SAMPLE_TEXT_DEMO.strip())} ký tự")
    time.sleep(1)

    print_separator("▶ BƯỚC 2: PHÂN ĐOẠN VĂN BẢN CHO 3 TRÒ CHƠI")
    parts = split_text_into_three_parts(SAMPLE_TEXT_DEMO)
    for i, p in enumerate(parts, 1):
        print(f"  [Phần {i}]: {p[:65]}...")
    time.sleep(1)

    print_separator("▶ BƯỚC 3: AI SINH CÂU HỎI & PYDANTIC SCHEMA VALIDATION")
    
    # Kiểm tra xem có API Key thật hay chạy demo mô phỏng
    api_key = os.getenv("GEMINI_API_KEY", "")
    has_real_key = bool(api_key and "your_gemini_api_key_here" not in api_key)
    
    if has_real_key:
        print("  ✓ Phát hiện GEMINI_API_KEY thật trong .env -> Đang gọi trực tiếp Gemini API...")
        # Gọi trực tiếp qua pipeline
        from ai_generate import generate_chapter
        chapter = generate_chapter(
            clean_text=SAMPLE_TEXT_DEMO,
            subject="philosophy",
            chapter_title="Chương 1: Triết học Mác - Lênin",
            output_path="data/demo_output.json"
        )
    else:
        print("  ℹ Chế độ Demo mô phỏng (Pydantic Schema Contract):")
        print("  ✓ Đang sinh Phần 1: Điền vào chỗ trống (fill_blank)...")
        p1 = Part1FillBlank(items=[
            FillBlankItem(id="p1-01", sentence="Vật chất là phạm trù triết học chỉ ___ khách quan.", answer="thực tại"),
            FillBlankItem(id="p1-02", sentence="Ý thức là hình ảnh chủ quan của thế giới ___.", answer="khách quan")
        ])
        time.sleep(0.5)

        print("  ✓ Đang sinh Phần 2: Nối từ / định nghĩa (matching)...")
        p2 = Part2Matching(items=[
            MatchingItem(id="p2-01", term="Vật chất", definition="Thực tại khách quan độc lập với ý thức"),
            MatchingItem(id="p2-02", term="Vận động", definition="Phương thức tồn tại của vật chất")
        ])
        time.sleep(0.5)

        print("  ✓ Đang sinh Phần 3: Trắc nghiệm (quiz)...")
        p3 = Part3Quiz(items=[
            QuizItem(id="p3-01", q="Phương thức tồn tại của vật chất là gì?", options=["Đứng im", "Cảm giác", "Ý chí", "Vận động"], answer=3)
        ])
        time.sleep(0.5)

        chapter = ChapterModel(
            subject="philosophy",
            chapter_title="Chương 1: Triết học Mác - Lênin",
            parts=[p1, p2, p3]
        )
        save_chapter_to_file(chapter, "data/demo_output.json")

    print_separator("▶ BƯỚC 4: KẾT QUẢ ĐÃ ĐƯỢC THẨM ĐỊNH BỞI PYDANTIC (CHI TIẾT CÂU HỎI)")
    print(f"  • Môn: {chapter.subject.upper()} | Tiêu đề: {chapter.chapter_title}")
    print("  • Pydantic Verification: [HỢP LỆ THEO SCHEMA]\n")

    # In chi tiết Game 1
    print("  --- [GAME 1: ĐIỀN VÀO CHỖ TRỐNG (fill_blank)] ---")
    for item in chapter.parts[0].items:
        print(f"  [Câu hỏi]: {item.sentence}")
        print(f"  [Đáp án đúng]: >> {item.answer} <<\n")

    # In chi tiết Game 2
    print("  --- [GAME 2: NỐI TỪ / ĐỊNH NGHĨA (matching)] ---")
    for item in chapter.parts[1].items:
        print(f"  [Thuật ngữ]: {item.term} <---> [Định nghĩa]: {item.definition}")
    print()

    # In chi tiết Game 3
    print("  --- [GAME 3: TRẮC NGHIỆM 4 PHƯƠNG ÁN (quiz)] ---")
    for item in chapter.parts[2].items:
        print(f"  [Câu hỏi]: {item.q}")
        opt_labels = ["A", "B", "C", "D"]
        for idx, opt in enumerate(item.options):
            marker = " (✓ ĐÁP ÁN ĐÚNG)" if idx == item.answer else ""
            print(f"    {opt_labels[idx]}. {opt}{marker}")
        print()

    time.sleep(1)

    print_separator("▶ BƯỚC 5: XUẤT FILE HOÀN CHỈNH CHO CÁC MODULE TRÒ CHƠI")
    print("  ✓ Đã ghi dữ liệu thành công ra: data/demo_output.json")
    print("  ✓ Dữ liệu sẵn sàng nạp trực tiếp vào các module trò chơi (Điền từ, Nối từ, Trắc nghiệm)!")
    print("=" * 60)
    print("DEMO HOÀN TẤT THÀNH CÔNG!\n")

if __name__ == "__main__":
    run_demo()
