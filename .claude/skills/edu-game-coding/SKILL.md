---
name: edu-game-coding
description: Định vị, giải thích, sửa lỗi và triển khai tính năng trong Edu_game (Python, server.py, games, web HTML/JS). Dùng khi người dùng hỏi code của tính năng nằm ở đâu, muốn sửa hành vi, thêm ràng buộc, debug hoặc review một thay đổi.
---

# Edu_game — Coding

## Nguyên tắc nền
- Trước tiên đọc `CLAUDE.md` để biết quyền sửa file, hợp đồng và điều cấm. Skill này KHÔNG thay thế `CLAUDE.md`.
- Đọc `docs/01-kich-ban.md` để biết yêu cầu đã chốt/chưa chốt; đối chiếu `docs/01-UML-phan-game.md` và `docs/viec-can-lam.md` khi liên quan.
- Luôn phân biệt **yêu cầu mong muốn**, **code đang chạy** và **thiết kế dự kiến**. Không coi class trong UML là đã được hiện thực nếu không tìm thấy ở code.
- Không tự thay đổi file do thành viên khác quản lý; xem danh sách trong `CLAUDE.md`.

## Quy trình cho mỗi yêu cầu
1. Viết lại hành vi mong muốn và tiêu chí hoàn thành dạng có thể kiểm thử. Với quyết định chưa chốt, ghi rõ `[Cần chốt]` và không âm thầm chọn thay nhóm.
2. Định vị luồng liên quan: HTML/JS trong `web/` → HTTP handler/API trong `server.py` → logic trong `games/` → dữ liệu trong `data/` → test trong `tests/`.
3. Dùng tìm kiếm symbol/route thực tế (`rg -n`, `grep -R`, hoặc IDE search); kiểm tra định nghĩa, nơi gọi, đầu vào, đầu ra và tác dụng phụ. Nếu được hỏi "code nằm ở đâu", trả tên file, hàm/class, mô tả và cách kiểm chứng; đừng vội sửa.
4. Trước khi chỉnh sửa, báo danh sách file dự định thay đổi và lý do; thực hiện quy trình xin duyệt trong `CLAUDE.md`.
5. Sửa theo phạm vi nhỏ nhất, không đổi hợp đồng ngoài yêu cầu. Với mỗi hành vi thay đổi, viết test tương ứng; không sửa/xóa test để che lỗi.
6. Chạy `python -m unittest discover -s tests -v`, kiểm tra `git diff --check` và `git diff` nếu có Git; nếu phù hợp, kiểm tra thủ công giao diện.
7. Báo cáo ngắn: vấn đề gốc, file/hàm đã chỉnh, test chạy và kết quả, thay đổi ngoài phạm vi nếu có, rủi ro còn lại. Không khẳng định đã test nếu chưa thực sự chạy.

## Bản đồ code đã kiểm tra
- `server.py`: `Handler.do_GET` / `do_POST` phân phối request; `fill_api_new/check/result`, `matching_api_new/check`, `quiz_api_new/check/result` xử lý API.
- `games/fill_blank.py`: `FillBlankGame`, `validate_items`, `_norm`; sinh tối đa 4 phương án từ các `answer` và chấm `check_one(qid, idx)` (đã chốt giữ chọn đáp án).
- `games/matching.py`: `MatchingGame`, `score_pairs`, `wrong_ids`.
- `games/quiz.py`: `EnglishQuizGame`, `validate_items`.
- `web/fill_blank.html`, `web/matching.html`, `web/quiz.html`: giao diện JS gọi API.
- `data/sample_*.json`: mẫu dữ liệu riêng từng trò chơi; KHÔNG thay thế kiểm tra hợp đồng chapter.json hoàn chỉnh.
- `tests/test_game_flow.py`: test điều hướng và API; KHÔNG phải bộ test đầy đủ cho mọi game.
- `games/final_test.py`: dựng đề tối đa 30 câu, giữ truy vết nguồn, tính điểm thang 10; `server.py` tích hợp API/luồng; `web/final_test.html` làm bài. `preprocess.py`, `ai_generate.py`, `summary.py`, `app.py` vẫn có chức năng chưa triển khai đầy đủ.

## Điều kiện bắt buộc khi viết code
- `public_view()` không phát trường đáp án/chỉ số đúng trước lúc chấm.
- `score` nghĩa là **số câu đúng**, `total` tổng câu, `wrong` danh sách ID; bảo toàn kiểu và tên trường.
- Chấm bài và kiểm tra input ở server, không phụ thuộc kiểm tra ở trình duyệt. `bool` không được chấp nhận làm chỉ số nguyên.
- Nếu thay đổi luồng game, kiểm tra khóa/mở khóa và ảnh hưởng của trạng thái toàn cục.
- Không thêm thư viện, đổi JSON schema, hoặc tự commit khi chưa được phép.

## Quyết định nghiệp vụ hiện hành: Fill Blank
**Giữ Fill Blank dạng chọn đáp án**, không tự chuyển sang gõ. `sentence` chứa đúng một `___`, `answer` là chuỗi; class chọn đáp án đúng và tối đa ba đáp án nhiễu từ những câu khác, rồi xáo vị trí, cho ra 2–4 lựa chọn. Bộ items yêu cầu ít nhất hai đáp án khác nhau sau chuẩn hóa. UI gửi `qid`, `idx`, server gọi `check_one(qid, idx)`. Không đưa `correct_idx` vào `public_view()` trước khi chấm. Khác Quiz (có sẵn 4 `options` ở từng câu). Khi người dùng yêu cầu đổi thiết kế mới cần xin duyệt, sửa tài liệu và test cùng code.
