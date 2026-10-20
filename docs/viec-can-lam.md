# Việc cần làm ( lần 1 ): Đã xong
Sửa server.py cho chơi theo thứ tự
- Đảm bảo: Không vào được game 2 khi chưa xong game 1; xong game 3 có kết quả
- Test: bỏ màn hình chọn game

# Việc cần làm ( lần 2 ): Đã xong
- Vấn đề: sau khi chơi xong trò fill_blank, UI không chuyển sang trò tiếp theo vì không có cơ chế chuyển game.
- Bổ sung: nút "Tiếp tục" cho fill blank.html, matching.html 
- Test: nút "Tiếp tục" hoạt động và chuyển sang game khác như kế hoạch ban đầu trong server.py

# Việc cần làm ( lần 3 ): Đã xong
- Chuẩn hóa import Quiz về `games.quiz`; giữ `server_english_quiz.py` làm lệnh chạy tương thích dùng chung Handler của `server.py`.
- Tích hợp trang, API và mở khóa Quiz sau khi hoàn thành Matching trong GameFlow.
- Chuyển tiếp Matching → Quiz theo môn học; sau khi hoàn thành Quiz hiển thị trạng thái hoàn tất.
- Test: luồng HTTP và logic xác nhận Fill Blank → Matching → Quiz, cùng khóa game khi bước trước chưa hoàn thành.

# Chưa triển khai (phạm vi sau)
- Bài kiểm tra cuối; chưa quyết định số câu, cách chia câu và cách tính điểm.