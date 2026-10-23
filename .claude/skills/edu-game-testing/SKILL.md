---
name: edu-game-testing
description: Lập kế hoạch, viết, chạy và đánh giá test cho Edu_game; kiểm tra logic 3 game, API HTTP, luồng mở khóa, dữ liệu đầu vào và hồi quy. Dùng khi người dùng yêu cầu test, tìm lỗi, xác minh tính năng hoặc giải thích vì sao test pass/fail.
---

# Edu_game — Testing

## Nguồn xác định expected behavior
- Đọc `CLAUDE.md` và `docs/01-kich-ban.md` để hiểu yêu cầu và hợp đồng.
- Đối chiếu với **code hiện tại**; khi tài liệu và code khác nhau, ghi rõ `SPEC MISMATCH`. Không viết test mặc định hợp thức hóa lỗi triển khai, cũng không tự đổi yêu cầu đang `[Cần chốt]`.
- Skill này chỉ kiểm thử/đề nghị thay đổi. Nếu cần sửa tính năng, chuyển sang quy trình của `edu-game-coding`.

## Bước thực hiện
1. Xác định chức năng, đầu vào, kết quả kỳ vọng, các nhánh và mức rủi ro.
2. Xem test hiện có trong `tests/test_game_flow.py`; kiểm tra cách test reset trạng thái (`FLOW_STATE`, `ACTIVE_*`, kho game) trước mỗi test.
3. Lập test matrix: happy path, đầu vào sai, thiếu/rỗng, biên, lặp ID, gọi sai thứ tự, request lỗi và hồi quy.
4. Viết test độc lập, đặt tên phản ánh hành vi. Unit test lớp game và integration test qua `ThreadingHTTPServer` trên cổng 0 cho API; cleanup server trong `finally`.
5. Chạy baseline: `python -m unittest discover -s tests -v` từ thư mục gốc dự án; báo chính xác số test chạy/pass/fail/skipped. Chỉ dùng `pytest -q` nếu pytest đã có hoặc việc cài đã được phê duyệt (dự án hiện viết test bằng unittest).
6. Nếu thất bại, cung cấp cách tái hiện, expected/actual, stack trace tiêu biểu, phân loại lỗi code/test/yêu cầu chưa rõ; không sửa hoặc xóa test chỉ để pass.
7. Khi sửa xong, chạy lại test ảnh hưởng và toàn suite; trình bày mức bao phủ còn thiếu, không diễn giải "test pass" thành "không còn lỗi".

## Các nhóm test ưu tiên
- **FillBlankGame (đã chốt giữ chọn):** sinh 2–4 lựa chọn từ `answer` của các câu trong bộ; tối thiểu 2 đáp án khác nhau sau `_norm`; chỉ số `idx` hợp lệ/âm/bool/ngoài biên; đúng/sai; không chọn lại sau `check_one`; đủ câu mới gọi được `result`; `public_view()` không đánh dấu lựa chọn đúng. `_norm` phục vụ loại trùng phương án nhiễu, không phải so khớp đáp án do người chơi gõ.
- **MatchingGame:** đúng/sai, trộn định nghĩa, ID trùng, thiếu cặp, chỉ số lặp/âm/bool/ngoài biên, payload lạ, kết quả và review.
- **EnglishQuizGame:** bốn lựa chọn, đáp án 0..3 nhưng không phải bool, lặp ID, chấm từng câu, không đổi đáp án sau check, result chỉ cho phép khi đã làm hết.
- **Hợp đồng dữ liệu:** subject, parts, ID, loại trường, JSON không hợp lệ, thiếu trường; chú ý mỗi file `data/sample_*.json` hiện chỉ chứa một `part`.
- **HTTP/API:** 200/303/400/404, chuyển trang khi chưa mở khóa, body JSON hỏng, body không phải object, lỗi validation phải trả HTTP phù hợp thay vì ngắt kết nối.
- **An toàn dữ liệu:** `public_view()` không lộ đáp án hoặc `correct_idx`; so sánh ở server và không tin dữ liệu từ client.
- **Final Test:** `tests/test_final_test.py` kiểm tra ghép ba nguồn trong cùng chương, giới hạn 30 câu, Quiz 2–4 phương án, ID nguồn, bảo vệ `public_view`, `score` là số câu đúng và điểm thang 10 theo `10 × score / total`. `tests/test_game_flow.py` kiểm tra khóa/mở khóa, cùng chương, HTTP endpoints và tổng kết. Báo riêng PASS/FAIL/SKIP theo kết quả thật. Đọc `docs/02-kiem-thu-final-test.md`.
- **Trạng thái phiên:** trạng thái hiện tại dùng biến toàn cục; kiểm tra nguy cơ người dùng A tác động đến người dùng B, khi chuyển sang hỗ trợ multi-user.

## Mẫu báo cáo kết quả
- **Phạm vi:** chức năng/phiên bản/tệp cần kiểm.
- **Lệnh chạy:** ghi nguyên lệnh đã thực hiện.
- **Kết quả:** passed, failed, skipped; lỗi có vị trí tái hiện.
- **Phân loại:** `BUG`, `SPEC MISMATCH`, `TEST GAP`, `[Cần chốt]`.
- **Mức độ ưu tiên:** P0 chặn luồng/bảo mật; P1 sai tính năng chính; P2 trường hợp biên; P3 cải thiện.
- **Kết luận:** những gì đã chứng minh được và những gì chưa kiểm chứng.
