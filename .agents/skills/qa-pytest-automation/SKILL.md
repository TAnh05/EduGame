---
name: qa-pytest-automation
description: Chuyên gia tự động hóa kiểm thử (QA Engineer) với PyTest, thiết kế kịch bản test biên, mock dữ liệu và đo độ ổn định hệ thống
author: Sang
version: 1.0.0
tags: [testing, pytest, qa-automation, mock-data, edge-cases]
---

# SKILL: QA PYTEST AUTOMATION (TESTING SUITE)

## 1. MỤC TIÊU VÀ PHẠM VI
Skill này đảm nhận vai trò QA Automation Engineer, chuyên trách thiết kế kịch bản kiểm thử tự động cho toàn bộ hệ thống bằng `pytest`, đảm bảo không có lỗi lọt vào phiên bản phát hành.

---

## 2. QUY TRÌNH THIẾT KẾ TEST CASE (THEO 3 NHÓM CHÍNH)

Khi viết test case mới, phân chia theo đúng kiến trúc của 3 file test trong dự án:

### 2.1. File `test_1.py` — Schema Validation Tests
- **Mục tiêu:** Kiểm tra các quy tắc biên của từng Model.
- **Kịch bản bắt buộc:**
  1. Ca thành công (Happy Path): Dữ liệu chuẩn phải pass qua Pydantic.
  2. Ca câu điền từ không có dấu `___` hoặc có 2 dấu `___` -> Bắt đúng lỗi `ValueError`.
  3. Ca câu điền từ có đáp án rỗng `""` -> Bắt lỗi.
  4. Ca câu trắc nghiệm thiếu lựa chọn (3 options) hoặc thừa (5 options) -> Bắt lỗi.
  5. Ca câu trắc nghiệm có đáp án `answer` nằm ngoài khoảng `0..3` -> Bắt lỗi.

### 2.2. File `test_2.py` — Retry & Resilience Tests
- **Mục tiêu:** Kiểm tra cơ chế tự phục hồi khi AI trả dữ liệu lỗi.
- **Kịch bản bắt buộc:**
  1. Giả lập AI trả JSON sai ở lần 1, nhưng sửa đúng ở lần 2 -> Hệ thống phải tự retry và trả kết quả thành công.
  2. Giả lập AI trả sai liên tiếp 3 lần -> Hệ thống phải dừng đúng số lần quy định và ném `AIProcessingError`.
  3. Kiểm thử luồng sinh trọn vẹn 1 chương học gồm đầy đủ 3 game.

### 2.3. File `test_3.py` — Edge Cases & Advanced Features
- **Mục tiêu:** Kiểm tra các điều kiện biên của tài liệu và tính năng phụ trợ.
- **Kịch bản bắt buộc:**
  1. Văn bản đầu vào rỗng (TC05).
  2. Văn bản quá ngắn dưới 50 từ (TC04).
  3. Văn bản vượt ngưỡng an toàn > 20.000 ký tự (TC06).
  4. Cơ chế Cache (F09): Tái sử dụng file kết quả có sẵn trên đĩa, không gọi lại API.
  5. Cơ chế Fallback (TC08): Tự nạp `sample_chapter.json` khi ngắt kết nối mạng.
  6. Kiểm tra ngân hàng câu hỏi Game cuối: Đảm bảo bốc đúng 10 câu theo tỷ lệ 3 câu điền từ – 3 câu nối từ – 4 câu trắc nghiệm.

---

## 3. LỆNH VẬN HÀNH KIỂM THỬ TRONG TERMINAL

```powershell
# Chạy toàn bộ test suite có hiển thị tên test case
pytest -v

# Chạy và dừng ngay khi phát hiện lỗi đầu tiên (Fail Fast)
pytest -x

# Cho phép in nhật ký logger và lệnh print() ra màn hình
pytest -v -s
```
