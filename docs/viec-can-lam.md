# Việc cần làm ( lần 1 ): Đã xong
Sửa server.py cho chơi theo thứ tự
- Đảm bảo: Không vào được game 2 khi chưa xong game 1; xong game 3 có kết quả
- Test: bỏ màn hình chọn game

# Việc cần làm ( lần 2 ): Đã xong
- Vấn đề: sau khi chơi xong trò fill_blank, UI không chuyển sang trò tiếp theo vì không có cơ chế chuyển game.
- Bổ sung: nút "Tiếp tục" cho `web/fill_blank.html`, `web/matching.html` 
- Test: nút "Tiếp tục" hoạt động và chuyển sang game khác như kế hoạch ban đầu trong server.py

# Việc cần làm ( lần 3 ): Đã xong
- Chuẩn hóa import Quiz về `games.quiz`, dùng chung Handler của `server.py`. **Không có `server_english_quiz.py` trong bản dự án hiện tại**; không coi đây là file đã triển khai.
- Tích hợp trang, API và mở khóa Quiz sau khi hoàn thành Matching trong `server.py` (`FLOW_STATE`).
- Giao diện chuyển tiếp Matching → Quiz có mang theo môn học. Ở lần 3 chưa có kiểm tra ràng buộc môn/chương; kiểm tra cùng chương được bổ sung trong lần 4.
- Test: luồng HTTP và logic xác nhận Fill Blank → Matching → Quiz, cùng khóa game khi bước trước chưa hoàn thành. Đã mở rộng luồng sau này tới Final Test.

# Việc cần làm (lần 4): Final Test demo — Đã xong
- Dựng bài Quiz từ các câu Fill Blank, Matching và Quiz cùng môn/chương; lấy hết nếu dưới 30, nếu vượt thì lấy ngẫu nhiên 30 câu không trùng.
- Dùng 2–4 lựa chọn khác nhau; nếu câu không có ít nhất 2 phương án hợp lệ thì trả lỗi dữ liệu.
- Tính điểm thang 10 bằng `10 × score / total`; giữ điểm số chưa làm tròn trong logic.
- Tích hợp API, khóa/mở trang sau khi xong ba game, trang làm bài và tổng kết; kết quả sai truy vết qua `source_game`/`source_id`.
- Test: `tests/test_final_test.py`, `tests/test_game_flow.py`; acceptance tests được thực thi, không còn SKIP do thiếu code.
- Phạm vi còn lại: upload tài liệu, sinh câu hỏi AI, tích hợp Streamlit và hỗ trợ nhiều phiên/người dùng.

# Cập nhật tài liệu (quyết định hiện hành): Fill Blank giữ dạng chọn đáp án
- Xác nhận **không chuyển Fill Blank sang ô gõ đáp án**.
- Đồng bộ `CLAUDE.md`, `README.md`, `docs/01-kich-ban.md`, `docs/01-UML-phan-game.md` và ba skill để phản ánh `FillBlankGame.check_one(qid, idx)`.
- Lựa chọn Fill Blank được sinh từ các `answer` trong bộ items (2–4 lựa chọn), không phải 4 `options` có sẵn như Quiz.
- Không thay đổi code game, HTML, server hoặc test trong đợt cập nhật tài liệu này.
