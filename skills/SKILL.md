---
name: edu-game
description: Phát triển và sửa phần game của dự án Edu_game (web ôn bài bằng trò chơi). Dùng khi làm việc với server.py, games/*.py, web/*.html, chapter.json, GameFlow, fill_blank, matching, quiz, hoặc khi người dùng nhắc đến hợp đồng dữ liệu game, thứ tự game, public_view, kết quả score/total/wrong.
---

# Edu_game – Skill phát triển phần Game

Bạn đang làm việc trên phần **game** của dự án Edu_game (Web ôn bài bằng các trò chơi).

Người học tải tài liệu → AI sinh `chapter.json` → chơi 3 game theo thứ tự cố định → bài kiểm tra cuối → xem điểm + ôn lại câu sai.

## Phạm vi trách nhiệm

Chỉ sửa các file thuộc phần game:
- `games/fill_blank.py`, `games/matching.py`, `games/quiz.py`
- `server.py`
- `web/*.html` (fill_blank.html, matching.html, quiz.html)
- `tests/`

**Không** sửa (trừ khi được yêu cầu rõ ràng):
- `preprocess.py`, `ai_generate.py`, `prompts.py`
- `games/final_test.py`
- `app.py`, `summary.py`

## Nguyên tắc kiến trúc (bắt buộc)

1. Game **chỉ** đọc dữ liệu theo hợp đồng `chapter.json`. Không đọc văn bản thô, không gọi AI/OCR.
2. Logic game nằm trong `games/`, không import Streamlit hay `http.server`. Giao diện và server chỉ gọi logic.
3. Đáp án đúng giữ ở phía logic. `public_view()` **tuyệt đối không** chứa đáp án.
4. Mọi game theo cùng khuôn class (xem `references/architecture.md`).
5. Kết quả mỗi game: `{"score": int, "total": int, "wrong": [id, ...]}` (có thể kèm `"review"`).
   - `score` = **số câu đúng** (không phải điểm). Điểm hiển thị tính ở lớp UI.
6. Mỗi item có `id` ổn định (vd `p1-01`, `p2-01`, `p3-01`).
7. Người học chơi theo thứ tự cố định: `fill_blank` → `matching` → `quiz` → bài kiểm tra cuối.
   - Không có màn hình chọn game.
   - Thứ tự là danh sách cấu hình (`GAME_ORDER`); mở khóa theo vị trí trong danh sách.

Chi tiết hợp đồng dữ liệu xem `references/data-contract.md`.

## Hành vi từng game (đã chốt)

- **fill_blank (Phần 1):** người học GÕ đáp án. So khớp không phân biệt hoa/thường và bỏ khoảng trắng thừa (dùng `_norm`).
- **matching (Phần 2):** nối thuật ngữ với định nghĩa; chấm theo `id`.
- **quiz (Phần 3):** chọn 1 trong 4 phương án, `answer` là chỉ số 0..3.

## Quy ước code

- Hàm/biến: `snake_case`; class: `PascalCase`; hằng: `UPPER_CASE`.
- Docstring và thông báo cho người dùng viết bằng **tiếng Việt**.
- Không đổi tên class/hàm đã có trong `docs/` hoặc dùng bởi module khác nếu chưa hỏi.
- Commit nhỏ, mỗi việc một commit, message rõ nghĩa.
- Không thêm thư viện mới khi chưa hỏi.
- Không đưa API key vào code; chỉ dùng `.env` (đã nằm trong `.gitignore`).

## Điều cấm

- Không sửa file của module người khác khi chưa được yêu cầu.
- Không đổi cấu trúc `chapter.json` hoặc hợp đồng kết quả `{score, total, wrong}`.
- Không đưa đáp án vào `public_view()`.
- Không xóa hay sửa test cho pass; test sai thì báo lại.
- Không commit `.env`, `__pycache__/`, tài liệu hay ảnh riêng tư.
- Không "tiện tay" sửa chỗ không liên quan.
- Không tự suy diễn các quyết định còn mở (ghi **[Cần chốt]** trong docs).

## Cách làm việc với Agent

1. Trước khi sửa, liệt kê các file định thay đổi và chờ duyệt.
2. Mỗi lần chỉ một việc nhỏ, có tiêu chí hoàn thành rõ (xem `references/current-tasks.md` hoặc `docs/viec-can-lam.md`).
3. Mỗi hàm mới kèm test trong `tests/` (cả trường hợp đúng, sai, rỗng, biên).
4. Sau khi sửa: chạy test, chạy thử bằng tay, rồi trình bày `git diff` để người dùng đọc trước khi commit.
5. Không chắc về API/thư viện thì nói rõ là không chắc, không tự bịa.

## Lệnh thường dùng

```bash
py server.py                          # mở http://127.0.0.1:8000
py -m unittest tests.test_game_flow -v
# hoặc
pytest
pip install -r requirements.txt