# Edu_game: Web ôn bài bằng các trò chơi

Người học tải tài liệu một chương -> hệ thống trích văn bản -> AI sinh câu hỏi (`chapter.json`) -> chơi 3 game theo thứ tự -> bài kiểm tra cuối -> tổng kết.
Thiết kế nằm trong `docs/`. Đọc trước khi code: `docs/01-kich-ban.md` (kế hoạch), `docs/01-UML-phan-game.md` (sơ đồ), `docs/02-viec-can-lam.md` (việc đang làm).

## Vai trò của người dùng file này
Phụ trách phần game: `games/fill_blank.py`, `games/matching.py`, `games/quiz.py`, `server.py`, `web/*.html`.
Các module khác do người khác phụ trách, KHÔNG tự ý sửa:
- `preprocess.py` (Toàn), `ai_generate.py` + `prompts.py` (Sang)
- `games/final_test.py` (Sơn Nguyễn), `app.py` + `summary.py` (Sơn Phạm)

Lưu ý phân công: báo cáo ghi `games/quiz.py` là của Sơn Nguyễn, nhưng kế hoạch hiện tại giao việc viết lại `quiz.py` cho phần game này.
Cần báo Sơn Nguyễn để tránh viết trùng. Khi chưa xác nhận, chỉ tạo `quiz.py` theo khuôn bên dưới và không đụng tới `final_test.py`.

## Tech stack
- Python 3.10+, `server.py` chỉ dùng thư viện chuẩn `http.server`
- Giao diện: HTML/CSS/JavaScript thuần trong `web/`
- Pydantic (kiểm tra JSON do AI sinh), pytest (test)
- Streamlit: báo cáo ghi Streamlit + Streamlit Community Cloud, nhưng phần game đang đi theo `server.py` + `web/`.
  Việc thống nhất hướng này với cả nhóm và sửa báo cáo còn mở (xem "Quyết định đang chờ"). Không phát triển thêm `app.py` khi chưa chốt.

## Cấu trúc thư mục
```
server.py           Server dẫn người học qua các game theo thứ tự (127.0.0.1:8000)
web/                index.html, matching.html, fill_blank.html (đã có); quiz.html (cần thêm)
games/              Logic game, Python thuần, KHÔNG phụ thuộc giao diện
  matching.py       đã chạy được
  fill_blank.py     đang là bản CŨ (chọn phương án), sẽ viết lại thành GÕ đáp án
  quiz.py           mới là khung Streamlit, sẽ viết lại theo khuôn class
  final_test.py     khung (không thuộc việc hiện tại)
data/               6 file JSON mẫu (2 môn x 3 game)
preprocess.py, ai_generate.py, prompts.py, summary.py, app.py   module của người khác
tests/              cần tạo
docs/               kế hoạch, sơ đồ, việc cần làm
```

## Nguyên tắc kiến trúc (quan trọng)
1. Game CHỈ đọc dữ liệu theo hợp đồng chapter.json. Game không đọc văn bản thô, không gọi API AI/OCR.
2. Logic game nằm trong `games/`, không import Streamlit hay http.server. Giao diện và server chỉ gọi logic.
3. Đáp án đúng giữ ở phía logic. `public_view()` KHÔNG chứa đáp án.
4. Mọi game theo cùng khuôn class:
   - `__init__(items)`: gọi `validate_items`, lỗi thì `raise ValueError` kèm thông báo tiếng Việt
   - `public_view() -> dict`: dữ liệu gửi giao diện
   - hàm chấm (`check` / `check_one`) và `result() -> dict`
5. Kết quả mỗi game: `{"score": int, "total": int, "wrong": [id, ...]}`, có thể kèm `"review"`.
   Hiện `score` = SỐ CÂU ĐÚNG (không phải điểm). Điểm hiển thị tính ở lớp hiển thị (xem "Chấm điểm").
6. Mỗi item có `id` ổn định (vd `p1-01`, `p2-01`, `p3-01`).
7. Người học chơi theo thứ tự cố định: fill_blank -> matching -> quiz -> bài kiểm tra cuối. Không có màn hình chọn game.
   Thứ tự là một danh sách cấu hình (`GAME_ORDER`); việc mở khóa kiểm tra theo VỊ TRÍ trong danh sách, không theo số `part`.

## Hợp đồng dữ liệu chapter.json
```
{"subject": "english|philosophy", "chapter_title": "...",
 "parts": [
  {"part": 1, "game": "fill_blank", "items": [{"id": "p1-01", "sentence": "... ___ ...", "answer": "..."}]},
  {"part": 2, "game": "matching",   "items": [{"id": "p2-01", "term": "...", "definition": "..."}]},
  {"part": 3, "game": "quiz",       "items": [{"id": "p3-01", "q": "...", "options": ["","","",""], "answer": 0}]}
 ]}
```
Ràng buộc: `subject` chỉ `english` hoặc `philosophy`; đúng 3 phần theo thứ tự 1,2,3;
fill_blank có đúng MỘT `___` và `answer` không rỗng; matching có `term`, `definition` không rỗng;
quiz có đúng 4 options và `answer` là số nguyên 0..3; `id` không rỗng và không trùng trong cùng phần.

## Hành vi từng game (đã chốt)
- **fill_blank (Phần 1):** người học GÕ đáp án. So khớp không phân biệt hoa/thường và bỏ khoảng trắng thừa. Dùng lại `_norm`.
- **matching (Phần 2):** nối thuật ngữ với định nghĩa; chấm theo `id`.
- **quiz (Phần 3):** chọn 1 trong 4 phương án, `answer` là chỉ số 0..3.

## Chấm điểm (kế hoạch của nhóm)
- Mỗi câu đúng 5 điểm, sai không trừ; mỗi game 100 điểm, nghĩa là cần đúng 20 câu mỗi game.
- Bài kiểm tra cuối: 50 câu lấy từ các câu đã ôn.
- Giữ nguyên hợp đồng `score` = số câu đúng; điểm = `score x 5` hoặc theo tỷ lệ `score / total x 100` do lớp hiển thị tính.
  Chọn cách nào còn đang chờ nhóm (xem bên dưới). Không tự đổi ý nghĩa của `score`.

## Quyết định đang chờ nhóm chốt (không tự suy diễn)
- Bài kiểm tra cuối: 50 câu (kế hoạch) hay 10 câu (báo cáo), cách chấm và cách chia câu từ 3 game.
- Chấm "5 điểm cố định" (cần đủ 20 câu) hay theo tỷ lệ.
- Hướng giao diện: phần game dùng `server.py` + `web/`, báo cáo ghi Streamlit; cần thống nhất và sửa báo cáo/nơi triển khai.
- `id` của câu hỏi do hệ thống tự gán (đề xuất cho Sang, `ai_generate.py`), vì code bắt buộc có `id`.
Khi chưa chốt, đừng đổi hành vi hiện có và hãy hỏi lại.

## Quy ước code
- Hàm/biến: `snake_case`; class: `PascalCase`; hằng: `UPPER_CASE`
- Docstring và thông báo cho người dùng viết bằng tiếng Việt
- Không đổi tên class/hàm đã có trong `docs/` hoặc dùng bởi module khác nếu chưa hỏi
- Commit nhỏ, mỗi việc một commit, message rõ nghĩa, làm trên branch riêng rồi gộp qua pull request

## Lệnh thường dùng
- Chạy server: `python server.py`, mở http://127.0.0.1:8000
- Cài thư viện: `pip install -r requirements.txt` (thêm `pytest` khi bắt đầu viết test)
- Chạy test: `pytest`

## Điều cấm
- Không sửa file của module người khác (danh sách ở trên) khi chưa được yêu cầu
- Không đổi cấu trúc chapter.json hoặc hợp đồng kết quả `{score, total, wrong}`
- Không đưa đáp án vào `public_view()`
- Không thêm thư viện mới khi chưa hỏi
- Không xóa hay sửa test cho pass; test sai thì báo lại
- Không đưa API key vào code; chỉ dùng `.env` (đã nằm trong `.gitignore`)
- Không commit `.env`, `__pycache__/`, tài liệu hay ảnh riêng tư của người dùng
- Không "tiện tay" sửa chỗ không liên quan

## Cách làm việc với Agent
1. Trước khi sửa, liệt kê các file định thay đổi và chờ duyệt.
2. Mỗi lần chỉ một việc nhỏ, có tiêu chí hoàn thành rõ (xem `docs/02-viec-can-lam.md`).
3. Mỗi hàm mới kèm test trong `tests/` (cả trường hợp đúng, sai, rỗng, biên).
4. Sau khi sửa: chạy `pytest`, chạy thử bằng tay, rồi trình bày `git diff` để người dùng đọc trước khi commit.
5. Không chắc về API/thư viện thì nói rõ là không chắc, không tự bịa.
