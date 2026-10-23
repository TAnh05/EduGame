---
name: edu-game-documentation
description: Đọc và giải thích tài liệu thiết kế, README, UML, hợp đồng dữ liệu rồi lần theo code Edu_game để chỉ ra vị trí tính năng, trạng thái đã làm/chưa làm và sự khác biệt tài liệu–hiện thực. Dùng khi người dùng hỏi cách đọc tài liệu, kiến trúc, luồng chương trình, chuẩn bị thuyết trình hoặc cập nhật docs.
---

# Edu_game — Documentation Reading & Traceability

## Nhiệm vụ
Giúp người học **đọc hiểu tài liệu kỹ thuật và đối chiếu với mã nguồn**, không chỉ tóm tắt Markdown. Nếu người dùng hỏi về cách trích chữ từ PDF/DOCX của bài học, lưu ý đó là bài toán `preprocess.py` và khác với đọc tài liệu dự án.

## Trình tự đọc
1. `README.md`: hiểu mục tiêu, tính năng F1–F7 và phân biệt chức năng đang chạy với lộ trình hoàn thiện.
2. `CLAUDE.md`: quyền sửa, dữ liệu, kiến trúc, điều cấm, và các quyết định chưa chốt. Kiểm tra đường dẫn được nhắc đến có tồn tại.
3. `docs/01-kich-ban.md`: yêu cầu nghiệp vụ, tiêu chí, phần `[Cần chốt]`.
4. `docs/01-UML-phan-game.md`: sơ đồ use-case/class/sequence/state; **không giả định các class dự kiến đã tồn tại**.
5. `docs/viec-can-lam.md`: danh sách tác vụ; xác minh trạng thái "Đã xong" với test/code.
6. `server.py`, `games/*.py`, `web/*.html`, `data/*.json`, `tests/*.py`: xác minh hành vi đang triển khai.

## Truy vết từ yêu cầu đến mã nguồn
- Với một tính năng F1–F7, tìm mô tả trong `docs/01-kich-ban.md`, định vị UI, route, handler, game logic, dữ liệu, test tương ứng.
- Đọc định nghĩa hàm/class và cả nơi nó được gọi; nêu **đầu vào → xử lý → đầu ra → nơi kiểm thử**.
- Kiểm tra trạng thái **Đã triển khai / Một phần / Chưa triển khai / Chỉ là thiết kế**; dẫn file và symbol thật. Dẫn số dòng chỉ khi đã xem đúng phiên bản file.
- Nếu có mâu thuẫn, lập bảng `Tài liệu ghi | Code thực tế | Ảnh hưởng | Đề xuất cập nhật`. Không tự chọn phương án khi quyết định chưa chốt.
- Với sơ đồ UML, đối chiếu quan hệ và phương thức với code, đề nghị cập nhật Mermaid/PlantUML dạng text nếu khác. Không trình bày `GameFlow`, `QuizGame` như class hiện có khi không tìm được định nghĩa.

## Bản đồ nhanh
| Tính năng | Mã nguồn để đọc | Tình trạng cần lưu ý |
|---|---|---|
| F1 Tải và đọc PDF/Word | `preprocess.py`, `app.py` | Mới có khung/TODO |
| F2 Điền chỗ trống | `web/fill_blank.html`, `server.py`, `games/fill_blank.py` | Đã chốt chọn 2–4 phương án tự sinh từ các `answer`; không gõ văn bản |
| F3 Nối từ | `web/matching.html`, `server.py`, `games/matching.py` | Có logic và HTTP |
| F4 Quiz | `web/quiz.html`, `server.py`, `games/quiz.py` | Có logic và HTTP |
| F5 Kiểm tra cuối | `games/final_test.py`, `server.py`, `web/final_test.html` | Đã có demo: tổng hợp câu trong cùng chương, tối đa 30, Quiz 2–4 lựa chọn |
| F6 Tổng kết | `server.py` | Hiển thị điểm ba game, điểm thang 10 và câu sai của Final Test; chưa lưu lâu dài |
| F7 Ôn câu sai | `result().wrong`, `only_ids` trong server | Có luồng ôn riêng ở từng game; truy vết câu sai Final Test qua `source_game`/`source_id` |

## Cách giải thích cho người học / bài vấn đáp
Với từng tính năng, trả lời theo cấu trúc:
1. **Mục đích:** chức năng để làm gì, nguồn yêu cầu từ file nào.
2. **Vị trí:** file, class/hàm, route; chỉ tên được tìm thấy thực tế.
3. **Cách hoạt động:** đi theo một yêu cầu HTTP hoặc một câu hỏi từ đầu đến cuối.
4. **Nếu cần thay đổi:** sửa ở đâu, test nào phải bổ sung/chạy lại, tác động đến contract nào.
5. **Chứng cứ:** đường dẫn, symbol, đoạn code/tình huống test liên quan.

## Khi cập nhật tài liệu
- Ưu tiên sửa phần sai, tránh lặp lại toàn bộ `CLAUDE.md` trong từng file.
- Bản thiết kế có thể đi trước code, nhưng phải gắn nhãn **Dự kiến**, **Chưa triển khai**.
- Những mục `[Cần chốt]` phải giữ trạng thái chờ nhóm xác nhận.
- Không bịa ra `docs/02-viec-can-lam.md` hoặc `references/*.md`: đường dẫn hiện có là `docs/viec-can-lam.md`. Không giả định `GAME_ORDER`, `GameFlow` hoặc class `FinalTest` tồn tại; Final Test hiện được dựng bằng `games.final_test.build_final_quiz()` và chấm qua `EnglishQuizGame`. Khi mô tả Fill Blank, phải ghi **chọn đáp án**, không dùng mô tả cũ “gõ đáp án”.
