# Edu_game: Web ôn tập bằng trò chơi

Sinh viên tải tài liệu một chương -> hệ thống trích văn bản -> AI sinh câu hỏi -> chơi 3 game tuần tự + game cuối -> tổng kết.
Thiết kế chi tiết nằm trong báo cáo của nhóm và thư mục `docs/` (đọc trước khi code).

## Vai trò của người dùng file này
Phụ trách module game Phần 1–2: `games/fill_blank.py`, `games/matching.py` (và giao diện tương ứng).
Các module khác do người khác phụ trách, KHÔNG tự ý sửa:
- `preprocess.py` (Toàn), `ai_generate.py` + `prompts.py` (Sang)
- `games/quiz.py` + `games/final_test.py` (Sơn Nguyễn)
- `app.py` + `summary.py` (Sơn Phạm)

## Tech stack
- Python 3.10+ (dùng cú pháp `list[dict]`, `from __future__ import annotations`)
- Streamlit (`app.py`), Pydantic (kiểm tra JSON do AI sinh), pytest (test)
- Prototype cục bộ: `server.py` (chỉ dùng thư viện chuẩn `http.server`) + `web/*.html`

## Cấu trúc thư mục
```
app.py              Trang Streamlit, điều hướng các bước
server.py           Server prototype cho game Matching + Fill Blank (127.0.0.1:8000)
preprocess.py       PDF/Word/ảnh -> văn bản sạch (chưa làm)
ai_generate.py      Văn bản -> chapter.json, Pydantic, retry tối đa 2 lần (chưa làm)
prompts.py          Prompt từng môn/phần
summary.py          Màn hình tổng kết (chưa làm)
games/              Logic game, Python thuần, KHÔNG phụ thuộc giao diện
  fill_blank.py, matching.py   đã chạy được
  quiz.py, final_test.py       mới là khung
web/                Giao diện HTML của prototype
data/               File JSON mẫu (6 file: 2 môn x 3 game)
tests/              Test (cần tạo)
docs/               Use case, sơ đồ Mermaid, kịch bản (cần tạo)
```

## Nguyên tắc kiến trúc (quan trọng)
1. Game CHỈ đọc dữ liệu theo hợp đồng chapter.json. Game không đọc văn bản thô, không gọi API AI/OCR.
2. Logic game nằm trong `games/` và không import Streamlit hay http.server. Giao diện chỉ gọi logic.
3. Đáp án đúng giữ ở phía logic. Hàm `public_view()` trả dữ liệu cho giao diện và KHÔNG chứa đáp án.
4. Mọi game theo cùng một khuôn class:
   - `__init__(items)`: gọi `validate_items`, lỗi thì `raise ValueError` kèm thông báo tiếng Việt
   - `public_view() -> dict`: dữ liệu gửi giao diện
   - hàm chấm (`check` / `check_one`) và `result() -> dict`
5. Kết quả mỗi game theo hợp đồng chung: `{"score": int, "total": int, "wrong": [id, ...]}`, có thể kèm `"review"` cho giao diện.
6. Mỗi item có `id` ổn định (vd `p1-01`, `p2-01`, `p3-01`) để truy câu sai và để game cuối lưu nguồn câu.

## Hợp đồng dữ liệu chapter.json
```
{"subject": "english|philosophy", "chapter_title": "...",
 "parts": [
  {"part": 1, "game": "fill_blank", "items": [{"id": "p1-01", "sentence": "... ___ ...", "answer": "..."}]},
  {"part": 2, "game": "matching",   "items": [{"id": "p2-01", "term": "...", "definition": "..."}]},
  {"part": 3, "game": "quiz",       "items": [{"id": "p3-01", "q": "...", "options": ["","","",""], "answer": 0}]}
 ]}
```
Ràng buộc: `subject` chỉ `english` hoặc `philosophy`; đúng 3 phần theo thứ tự 1,2,3; fill_blank có đúng MỘT `___`;
quiz có đúng 4 options và `answer` là số nguyên 0..3; `id` không rỗng và không trùng trong cùng phần.

## Quyết định đang chờ nhóm chốt (không tự suy diễn)
- Giao diện chính: Streamlit hay server.py + web/. Báo cáo ghi Streamlit Community Cloud, và server.py không chạy được ở đó.
- `id` của item: code bắt buộc có `id`, còn báo cáo/prompt chưa có. Đề xuất: `ai_generate.py` tự gán id sau khi Pydantic kiểm tra.
- Fill Blank: đang là chọn phương án (có đáp án nhiễu), báo cáo ghi là gõ đáp án.
Khi chưa chốt, đừng đổi hành vi hiện có và hãy hỏi lại.

## Quy ước code
- Hàm/biến: `snake_case`; class: `PascalCase`; hằng: `UPPER_CASE`
- Docstring và thông báo cho người dùng viết bằng tiếng Việt
- Không đổi tên class/hàm đã có trong `docs/` và trong các module khác nếu chưa hỏi
- Commit nhỏ, mỗi tính năng một commit, message rõ nghĩa, làm trên branch riêng rồi gộp qua pull request

## Lệnh thường dùng
- Cài thư viện: `pip install -r requirements.txt` (thêm `pytest` khi bắt đầu viết test)
- Chạy prototype: `python server.py`, mở http://127.0.0.1:8000
- Chạy Streamlit: `streamlit run app.py`
- Chạy test: `pytest`

## Điều cấm
- Không sửa file của module người khác (xem danh sách ở trên) khi chưa được yêu cầu
- Không đổi cấu trúc chapter.json hoặc hợp đồng kết quả `{score, total, wrong}`
- Không đưa đáp án vào `public_view()`
- Không thêm thư viện mới khi chưa hỏi
- Không xóa hay sửa test cho pass; test sai thì báo lại
- Không đưa API key vào code; chỉ dùng `.env` (đã nằm trong `.gitignore`)
- Không commit `.env`, `__pycache__/`, tài liệu hay ảnh riêng tư của người dùng
- Không "tiện tay" sửa chỗ không liên quan

## Cách làm việc với Agent
1. Trước khi sửa, liệt kê các file định thay đổi và chờ duyệt.
2. Mỗi lần chỉ một việc nhỏ, có tiêu chí hoàn thành rõ.
3. Mỗi hàm mới kèm test trong `tests/` (cả trường hợp đúng, sai, rỗng, biên).
4. Sau khi sửa: chạy `pytest`, chạy thử bằng tay, rồi trình bày `git diff` để người dùng đọc trước khi commit.
5. Không chắc về API/thư viện thì nói rõ là không chắc, không tự bịa.
