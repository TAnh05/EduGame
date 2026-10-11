# 02. Việc cần làm (phần game)

> Danh sách việc đang thực hiện, theo thứ tự. Làm xong việc nào thì đánh dấu và commit trước khi sang việc sau.
> Thứ tự 1 -> 2 -> 3 -> 4: mỗi game phải chạy được riêng trước khi nối thành luồng.

## Bảng việc

| # | Việc | File chính | Xong khi | Test cần có | Trạng thái |
|---|---|---|---|---|---|
| 1 | Viết `quiz.py` (4 lựa chọn, `answer` 0..3) | `games/quiz.py` | Class chạy được với `data/sample_*_quiz.json`; `public_view()` không có đáp án | chọn đúng, chọn sai, thiếu `options`, `answer` ngoài 0..3 | [ ] |
| 2 | Viết lại `fill_blank.py` (gõ đáp án) | `games/fill_blank.py` | So khớp không phân biệt hoa/thường, bỏ khoảng trắng thừa | `"Goes"` và `" goes "` đúng, `"go"` sai, chuỗi rỗng sai | [ ] |
| 3 | Thêm HTML cho fill_blank và quiz | `web/fill_blank.html`, `web/quiz.html` | Chơi được hết một ván trong trình duyệt | chạy tay, chụp ảnh | [ ] |
| 4 | Sửa `server.py` cho chơi theo thứ tự | `server.py`, `web/index.html` | Không vào được game 2 khi chưa xong game 1; xong game 3 có kết quả; bỏ màn hình chọn game | chạy tay, test hàm kiểm tra mở khóa | [ ] |

## Chi tiết từng việc

### Việc 1: `quiz.py`
- Bỏ khung Streamlit hiện tại (`run(items)`), viết class `QuizGame` theo khuôn chung: `validate_items`, `public_view()`, `check_one(qid, idx)`, `result()`.
- Quy tắc kiểm tra: đúng 4 `options`, `answer` là số nguyên 0..3, `q` không rỗng, `id` không trùng.
- Đây là class mới, đơn giản hơn logic cũ trong `fill_blank.py` (không cần tự sinh đáp án nhiễu, vì `options` có sẵn trong dữ liệu).
- Báo Sơn Nguyễn trước khi bắt đầu (file này ghi tên bạn ấy trong báo cáo).

### Việc 2: `fill_blank.py` (gõ đáp án)
- `check_one` đổi từ nhận chỉ số lựa chọn sang nhận **chuỗi** người học gõ; so khớp bằng `_norm`.
- Bỏ phần sinh đáp án nhiễu và `options` trong `public_view()`; ràng buộc "đúng một `___`" và `answer` không rỗng vẫn giữ.
- **Chú ý ảnh hưởng:** hàm `fill_api_check` trong `server.py` và `web/fill_blank.html` đang giả định lựa chọn theo chỉ số, phải sửa cho khớp (việc 3).
- Kết quả giữ nguyên hợp đồng `{score, total, wrong}` (+ `review`).

### Việc 3: HTML
- `web/fill_blank.html`: ô nhập chữ thay cho các nút chọn.
- `web/quiz.html`: 4 nút lựa chọn (có thể tham khảo giao diện chọn cũ của fill_blank).
- Thêm các route `/api/quiz/new`, `/api/quiz/check`, `/api/quiz/result` trong `server.py` (theo mẫu của `fill_blank`).

### Việc 4: chơi theo thứ tự
- Khai báo thứ tự là một danh sách cấu hình (ví dụ `GAME_ORDER = ["fill_blank", "matching", "quiz"]`).
- Mở khóa kiểm tra theo **vị trí trong danh sách**, không theo số `part` trong JSON (để sau này đổi sang random chỉ cần xáo danh sách).
- Bỏ lựa chọn game ở `index.html`; sau khi xong một game thì server chuyển sang game kế tiếp.

## Prompt mẫu (công thức: Bối cảnh + Mục tiêu + Ràng buộc + Cách kiểm chứng)

**Việc 1:**
> Bối cảnh: dự án Edu_game, đọc `CLAUDE.md`, `docs/01-kich-ban.md` và `games/matching.py` (mẫu khuôn class). Mục tiêu: viết class `QuizGame` trong `games/quiz.py`: `validate_items`, `public_view()` (không chứa đáp án), `check_one(qid, idx)`, `result()` trả `{score, total, wrong}`. Ràng buộc: chỉ tạo/sửa `games/quiz.py` và `tests/test_quiz.py`; không import Streamlit; đúng 4 options, answer 0..3. Kiểm chứng: test chọn đúng, chọn sai, thiếu options, answer ngoài 0..3. Hãy liệt kê kế hoạch và file định sửa trước, chưa viết code.

**Việc 2:**
> Bối cảnh: đọc `CLAUDE.md` và `games/fill_blank.py` hiện tại (bản chọn phương án). Mục tiêu: viết lại thành bản người học gõ đáp án, so khớp bằng `_norm`. Ràng buộc: chỉ sửa `games/fill_blank.py` và `tests/test_fill_blank.py`; giữ hợp đồng kết quả; giữ ràng buộc đúng một `___`. Kiểm chứng: `"Goes"` và `" goes "` đúng, `"go"` sai, chuỗi rỗng sai. Liệt kê chỗ khác trong repo bị ảnh hưởng (server, HTML) trước khi sửa, chưa sửa những chỗ đó.

## Quy tắc làm việc
- Mỗi việc một branch hoặc ít nhất một commit riêng, message rõ nghĩa, đặt đúng tên/email.
- Trước khi commit: chạy `pytest`, chạy thử bằng tay, đọc `git diff`.
- Ghi lại một lần Agent làm sai (nếu có) và cách phát hiện, để dùng làm bằng chứng khi vấn đáp.
- Khi chốt xong các điểm còn mở ở `01-kich-ban.md` mục 8, cập nhật cả `CLAUDE.md`.
