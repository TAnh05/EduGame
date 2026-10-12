# BÁO CÁO CÁC FILE, CHỨC NĂNG VÀ LỆNH CHẠY DỰ ÁN

---

## 1. DANH SÁCH FILE VÀ CHỨC NĂNG

### 1.1. Mã nguồn chính
* **`ai_generate.py`**: File trung tâm của dự án.
  * Định nghĩa cấu trúc dữ liệu và luật kiểm tra cho 3 mini-game bằng Pydantic (`FillBlankItem`, `MatchingItem`, `QuizItem`).
  * Kết nối Google Gemini API để sinh câu hỏi từ văn bản giáo trình.
  * Phân tích cú pháp JSON, kiểm tra tính hợp lệ dữ liệu.
  * Xử lý cơ chế tự động thử lại (Retry tối đa 2 lần) khi AI trả về sai format hoặc vi phạm luật.
  * Cung cấp cơ chế dự phòng (Fallback) tự nạp dữ liệu mẫu khi mất kết nối mạng.
  * Tạo ngân hàng câu hỏi Game cuối theo tỷ lệ 3–3–4.

* **`prompts.py`**: Chứa toàn bộ câu lệnh chỉ dẫn (prompt) gửi cho AI.
  * Định nghĩa `SYSTEM_PROMPT` quy định vai trò chuyên gia sư phạm của AI và bắt buộc chỉ trả về định dạng JSON thuần.
  * Cung cấp các mẫu ví dụ (few-shot examples) cho từng game: Phần 1 (Điền từ), Phần 2 (Nối từ), Phần 3 (Trắc nghiệm).
  * Hàm `get_game_prompt()` ghép nội dung bài học vào prompt theo từng môn học (`english` hoặc `philosophy`).

* **`demo.py`**: Kịch bản mô phỏng chạy thử toàn bộ luồng hoạt động.
  * Nạp đoạn văn bản mẫu (Triết học Mác - Lênin).
  * Tự động nhận diện có `GEMINI_API_KEY` hay không để chạy chế độ gọi Gemini thật hoặc chế độ mô phỏng Pydantic schema.
  * Thực hiện tiền xử lý văn bản, sinh câu hỏi cho cả 3 phần và lưu file kết quả ra `data/demo_output.json`.

---

### 1.2. Bộ kiểm thử tự động
* **`test_1.py`**: Kiểm thử các quy tắc ràng buộc dữ liệu (Schema Validation).
  * Kiểm tra dữ liệu hợp lệ phải pass.
  * Bắt lỗi khi câu điền từ không có hoặc có nhiều hơn 1 dấu `___`.
  * Bắt lỗi khi câu hỏi hoặc đáp án bị để khoảng trắng rỗng.
  * Bắt lỗi khi câu trắc nghiệm không đủ 4 đáp án hoặc đáp án đúng nằm ngoài khoảng 0–3.

* **`test_2.py`**: Kiểm thử cơ chế chịu lỗi và thử lại (Retry Mechanism).
  * Giả lập tình huống AI trả về lỗi JSON hoặc sai cấu trúc ở lần đầu, nhưng đúng ở lần thứ 2.
  * Kiểm tra hệ thống dừng và báo lỗi `AIProcessingError` khi thử lại quá số lần quy định mà vẫn sai.
  * Kiểm tra quy trình sinh trọn vẹn 1 chương gồm đủ cả 3 game.

* **`test_3.py`**: Kiểm thử các ca biên ngoại lệ và tính năng mở rộng.
  * Kiểm tra bắt lỗi khi văn bản đầu vào rỗng, quá ngắn (dưới 50 từ) hoặc quá dài (vượt 20.000 ký tự).
  * Kiểm tra cơ chế Cache: Tái sử dụng file kết quả có sẵn trên đĩa, không gọi lại API.
  * Kiểm tra cơ chế Fallback: Tự nạp dữ liệu mẫu có sẵn khi mất kết nối API.
  * Kiểm tra thuật toán bốc ngẫu nhiên câu hỏi cho Game cuối theo đúng tỷ lệ 3–3–4.

---

### 1.3. Thư mục dữ liệu (`data/`)
* **`data/sample_chapter.json`**: File JSON chuẩn mẫu ban đầu, dùng làm dữ liệu dự phòng (Fallback) khi API gặp sự cố.
* **`data/sample_chapter_philosophy.json`**: File dữ liệu mẫu về chủ đề Triết học, dùng làm mock data trong các kịch bản kiểm thử của `test_3.py`.
* **`data/demo_output.json`**: File chứa kết quả đầu ra thực tế do `demo.py` sinh ra và lưu trên đĩa sau khi hoàn thành quy trình chạy thử.

---

### 1.4. File cấu hình & môi trường
* **`requirements.txt`**: Danh sách thư viện cần thiết (`pydantic`, `google-generativeai`, `python-dotenv`, `pytest`).
* **`.env.example`**: File mẫu hướng dẫn khai báo biến môi trường `GEMINI_API_KEY`.
* **`.gitignore`**: Khai báo các file loại trừ khỏi Git (`.env`, `__pycache__/`, cache test).

---

## 2. LỆNH CHẠY DEMO VÀ KIỂM THỬ

### 2.1. Lệnh chạy Demo mô phỏng
```powershell
# Chạy pipeline hoàn chỉnh từ văn bản đầu vào đến xuất file JSON
python demo.py
```

---

### 2.2. Lệnh chạy Kiểm thử (pytest)

#### Chạy toàn bộ các bài test:
```powershell
# Chạy tất cả test case
pytest

# Chạy có thông tin chi tiết từng test case (PASS / FAIL)
pytest -v
```

#### Chạy từng file test riêng biệt:
```powershell
# Kiểm tra các luật ràng buộc Pydantic
pytest test_1.py -v

# Kiểm tra cơ chế Retry khi AI gặp lỗi
pytest test_2.py -v

# Kiểm tra ca biên đầu vào, Cache và Fallback
pytest test_3.py -v
```

#### Tùy chọn mở rộng:
```powershell
# Dừng ngay khi gặp test case đầu tiên bị lỗi (Fail Fast)
pytest -x

# Hiển thị toàn bộ log và lệnh print() ra màn hình trong khi test
pytest -v -s
```
