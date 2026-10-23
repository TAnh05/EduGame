# Edu_game — Hướng dẫn chung cho AI Agent

> **Nguồn quy tắc khi thao tác dự án.** Đọc thêm `docs/01-kich-ban.md` (yêu cầu và quyết định của nhóm), `docs/01-UML-phan-game.md` (thiết kế), `docs/viec-can-lam.md` (lịch sử công việc). Luôn đối chiếu tài liệu với code hiện tại; không coi thiết kế dự kiến là đã triển khai.

## 1. Mục tiêu và tình trạng hiện tại

- **Mục tiêu tổng thể (chưa hoàn thiện hết):** người học tải Word/PDF → trích văn bản → AI sinh `chapter.json` → ba game → bài kiểm tra cuối → tổng kết/ôn câu sai.
- **Đã có trong bản hiện tại:** `server.py` + HTML/JS trong `web/` phục vụ **Fill Blank → Matching → Quiz → Final Test → Tổng kết**. Các game dùng JSON mẫu trong `data/` hoặc JSON cung cấp qua API; Final Test tổng hợp ba phần thuộc cùng môn/chương.
- **Fill Blank đã được xác nhận giữ nguyên dạng chọn đáp án.** Đây là quyết định hiện hành, không phải lỗi cần chuyển về nhập/gõ tự do.

## 2. Ranh giới công việc

Phần game gồm: `games/fill_blank.py`, `games/matching.py`, `games/quiz.py`, `server.py`, `web/*.html`, test cho những thành phần này.

Các module nhóm khác quản lý: `preprocess.py` (Toàn), `ai_generate.py` và `prompts.py` (Sang), `games/final_test.py` (Sơn Nguyễn), `app.py` và `summary.py` (Sơn Phạm). **Không tự ý chỉnh sửa module khác khi chưa được giao và thống nhất với người phụ trách.**

**Lưu ý phân công:** báo cáo từng ghi `games/quiz.py` thuộc Sơn Nguyễn; code Quiz hiện đã có trong phần game. Nếu cần thay đổi phạm vi sở hữu, xác nhận với hai bên; không tự mở rộng sang `games/final_test.py`.

## 3. Công nghệ và cách chạy hiện tại

- Python 3.10+; phần game dùng `http.server` từ thư viện chuẩn; frontend là HTML/CSS/JavaScript thuần trong `web/`.
- `requirements.txt` dành cho các module dự án khác: Streamlit, PyMuPDF, python-docx, Anthropic, Pydantic, python-dotenv. **Phần game hiện dùng server HTML độc lập, không phải Streamlit.** Cách tích hợp/triển khai toàn dự án vẫn **[Cần chốt]**.
- Chạy phần game: `python server.py`, mở `http://127.0.0.1:8000/`.
- Chạy test: `python -m unittest discover -s tests -v` (34 test đã xác minh trong snapshot hiện tại). `pytest` chưa được khai báo trong `requirements.txt`; chỉ dùng khi có sẵn hoặc đã được duyệt cài thêm.

## 4. Bản đồ mã nguồn thực tế

```text
server.py                  Handler HTTP, API, FLOW_STATE và khóa mở các game
web/fill_blank.html        Fill Blank: chọn phương án (đã có)
web/matching.html          Matching: nối thuật ngữ/định nghĩa (đã có)
web/quiz.html              Quiz: chọn 1 trong 4 phương án (đã có)
web/final_test.html        Bài kiểm tra cuối (đã có)
games/fill_blank.py        FillBlankGame (đã có)
games/matching.py          MatchingGame (đã có)
games/quiz.py              EnglishQuizGame (đã có)
games/final_test.py        Dựng câu hỏi Final Test và tính điểm thang 10 (đã có)
data/sample_*.json         6 file mẫu: 2 môn × 3 game; mỗi file chứa 1 part
tests/test_game_flow.py    Test luồng, mở khóa và API
tests/test_final_test.py   Test dựng đề, giới hạn câu, đáp án, điểm và truy vết nguồn
preprocess.py, ai_generate.py, prompts.py, summary.py, app.py
                           Các module khác của nhóm; nhiều chức năng còn khung/TODO
.claude/skills/            3 skill: coding, testing, documentation
```

## 5. Quy tắc kiến trúc và hợp đồng

1. Logic game ở `games/`; không phụ thuộc Streamlit hay `http.server`, không trực tiếp đọc PDF/Word hay gọi dịch vụ AI.
2. Game nhận các `items` đã lấy từ phần tương ứng trong JSON. `public_view()` chỉ trả thông tin câu hỏi/phương án **không đánh dấu phương án đúng**. Việc chấm và công bố đáp án nằm ở phía server sau khi người chơi kiểm tra bài.
3. Từng game có `__init__(items)` kiểm tra dữ liệu (báo lỗi `ValueError`), `public_view()`, hàm chấm `check()`/`check_one()` và `result()` khi phù hợp. `MatchingGame.check(pairs)` trả kết quả trực tiếp, không có `result()` riêng trong bản hiện tại.
4. Kết quả giữ hợp đồng `{"score": int, "total": int, "wrong": [id, ...]}` và có thể kèm `review`. **`score` = số câu/cặp đúng, không phải điểm trên thang 100.** Giao diện hiện hiển thị `score/total`.
5. Mỗi item có `id` ổn định, không trùng trong phần. Không tự thay JSON schema/chữ ký API khi chưa có yêu cầu.
6. **Luồng hiện tại:** Fill Blank → Matching → Quiz → Final Test → Tổng kết. Server kiểm soát bằng các cờ `FLOW_STATE` cùng `ACTIVE_*_GAME_ID`; **chưa có biến `GAME_ORDER` và chưa có class `GameFlow`**. `GAME_ORDER`/thứ tự ngẫu nhiên chỉ là **thiết kế giai đoạn sau**.
7. `FLOW_STATE` là biến toàn cục và server chưa phân lập phiên người dùng; hiện phù hợp nhất cho demo một người. Server yêu cầu ba game dùng cùng `subject` và `chapter_title` để dựng Final Test; chưa phải thiết kế đa người dùng.

### Dữ liệu đầu vào thiết kế: `chapter.json`

```json
{
  "subject": "english",
  "chapter_title": "Tên chương",
  "parts": [
    {"part": 1, "game": "fill_blank", "items": [{"id": "p1-01", "sentence": "She ___ to school.", "answer": "goes"}]},
    {"part": 2, "game": "matching", "items": [{"id": "p2-01", "term": "...", "definition": "..."}]},
    {"part": 3, "game": "quiz", "items": [{"id": "p3-01", "q": "...", "options": ["A", "B", "C", "D"], "answer": 0}]}
  ]
}
```

Theo **hợp đồng thiết kế**, `subject` là `english` hoặc `philosophy`, ba phần có thứ tự 1–3. **Hiện tại** các file `data/sample_*.json` chỉ chứa một `part` tương ứng; các game truy xuất theo tên `game` và chưa có lớp kiểm chứng đầy đủ toàn bộ hợp đồng `chapter.json` chung. Không khẳng định dữ liệu đầu vào toàn hệ thống đã được kiểm chứng toàn diện.

### Hành vi đã chốt của ba game

- **Fill Blank (giữ dạng chọn đáp án):** `sentence` chứa đúng một `___`, `answer` là chuỗi không rỗng. `FillBlankGame` sử dụng đáp án của câu hiện tại và tối đa 3 đáp án khác làm lựa chọn nhiễu, xáo thứ tự, hiện **từ 2 đến 4 phương án** tùy nguồn. Bộ items phải có **ít nhất 2 đáp án khác nhau sau chuẩn hóa** để tạo phương án. Giao diện chọn một phương án, gửi `{game_id, qid, idx}` đến `POST /api/fill_blank/check`; `check_one(qid, idx)` so sánh theo chỉ số. Đáp án đúng không được đánh dấu trong `public_view()`; chỉ trả `correct_idx`/`correct_text` sau khi chấm. Hàm `_norm` dùng khi gom/loại trùng đáp án nhiễu, **không dùng để chấm câu trả lời dạng gõ**.
- **Matching:** ghép `term` với `definition`, gửi `pairs` (ID thuật ngữ → chỉ số định nghĩa), chấm theo ID; `MatchingGame.check(pairs)` trả kết quả.
- **Quiz:** mỗi item có 4 `options` trong JSON và `answer` là chỉ số nguyên 0–3. `EnglishQuizGame.check_one(qid, idx)` chấm từng câu.

**Khác nhau:** Fill Blank tự sinh phương án từ những câu khác trong cùng bộ dữ liệu; Quiz nhận sẵn đúng 4 phương án từ dữ liệu JSON. **Không được tự đổi Fill Blank thành ô nhập văn bản** trừ khi người dùng/nhóm đưa yêu cầu mới.

## 6. Quy tắc chấm điểm còn chờ nhóm

- Kế hoạch ghi 5 điểm/câu, mỗi game tối đa 100 điểm (cần 20 câu/game), nhưng file dữ liệu mẫu có ít câu hơn.
- Cách tính điểm hiển thị cuối cùng: 5 điểm cố định hay chuẩn hóa `score / total × 100`: **[Cần chốt]**. Giữ `score` là số câu đúng.
- **Final Test demo:** Quiz một đáp án, dùng tất cả câu từ ba game trong cùng chương, tối đa 30; trên giới hạn chọn ngẫu nhiên đều không ép tỷ lệ. Không áp dụng cơ cấu 3–3–4 hay 50 câu.
- Fill Blank và Matching được chuyển thành câu Quiz, có 2–4 phương án khác nhau; thiếu tối thiểu 2 phương án thì báo lỗi. Giữ `source_game`/`source_id`; không lộ đáp án qua public API. `score` vẫn là số câu đúng.
- Điểm thang 10 = `10 × score / total`; giữ độ chính xác trong logic, giao diện hiển thị hai chữ số thập phân. Xem `docs/02-kiem-thu-final-test.md`.
- `games/final_test.py`, các route Final Test và trang tổng kết đã được tích hợp vào demo; kiểm thử trong `tests/test_final_test.py` và `tests/test_game_flow.py`.
- Cách tích hợp Streamlit với `server.py`, đơn vị sinh `id`, phân công sửa `quiz.py`: **[Cần chốt]** theo đúng người phụ trách.

## 7. Quy tắc làm việc với Agent

- Ba skill độc lập: `.claude/skills/edu-game-coding/SKILL.md`, `edu-game-testing/SKILL.md`, `edu-game-documentation/SKILL.md`. `CLAUDE.md` chứa luật chung; skill thực hiện quy trình chuyên môn.
- Trước khi sửa: xác định file/hàm liên quan, liệt kê phạm vi và lý do, thực hiện quy trình xin duyệt với người dùng. Nếu yêu cầu đã cho phép sửa tài liệu cụ thể, chỉ sửa trong phạm vi được giao.
- Giữ thay đổi nhỏ, tập trung, có test cho thay đổi hành vi. Không sửa/xóa test chỉ để pass, không tự thêm dependency, không đổi hợp đồng kết quả, không sửa file nhóm khác, không commit thay người dùng.
- Không tiết lộ đáp án trong `public_view()`, không đẩy khóa API lên Git; `.env` phải ở ngoài Git. Không làm lộ dữ liệu riêng của người học.
- Sau khi sửa code: chạy `python -m unittest discover -s tests -v`, kiểm tra giao diện nếu có liên quan, `git diff --check`/`git diff` nếu có Git, báo thay đổi, test đã chạy và rủi ro còn lại. Không nói "pass" nếu chưa chạy thực tế.
