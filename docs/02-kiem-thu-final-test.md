# Đặc tả và kế hoạch kiểm thử — Bài kiểm tra cuối (Final Test)

**Trạng thái:** Đã tích hợp demo logic dựng đề, tính điểm, API, giao diện và tổng kết. Tài liệu này ghi hợp đồng hiện tại cùng các giới hạn cần lưu ý.

## Phạm vi đã xác định cho bản demo

1. Final Test **chỉ có dạng Quiz**. Câu Fill Blank/Matching có 2–4 phương án phân biệt; câu Quiz gốc giữ 4 phương án.
2. Lấy **tất cả các câu hỏi hiện có** từ ba nhóm trong *cùng một chương*: `fill_blank`, `matching`, `quiz`. **Tổng tối đa 30 câu**.
3. Khi có dưới 30 câu, lấy hết; khi nhiều hơn 30, lấy ngẫu nhiên đều 30 câu không trùng. **Không áp dụng chia tỷ lệ 3–3–4, 17–17–16 hoặc 50 câu**.
4. Chuyển `fill_blank` thành câu chỗ trống có các lựa chọn từ các đáp án khác trong cùng phần, `matching` thành câu hỏi thuật ngữ → định nghĩa với các định nghĩa khác trong phần; `quiz` giữ câu hỏi và 4 phương án. `EnglishQuizGame` hỗ trợ cấu hình 2–4 lựa chọn dành riêng cho Final Test; Quiz thông thường vẫn yêu cầu đúng 4.
5. Mỗi câu phải giữ `source_game` và `source_id`, cùng `id` duy nhất trong bài thi, để truy xuất câu sai về đúng nơi xuất phát. Không sửa các ID nguồn trong `chapter.json`.
6. Không đưa chỉ số/phương án đánh dấu đúng ra API public trước khi người dùng chấm bài.
7. `score` tiếp tục là **số câu đúng**, `total` là **tổng câu**, `wrong` là danh sách ID câu làm sai (theo hợp đồng đang có).
8. Điểm cuối trên thang 10: **điểm bài thi = `10 × score / total`**. Không làm tròn trong logic; giao diện hiển thị hai chữ số thập phân. Ví dụ: đúng 12/16 → 7,5/10.
9. Khi chưa hoàn tất ba game, UI/API không cho làm Final Test. Các nguồn phải trùng `subject` và `chapter_title`; trạng thái demo lưu RAM, chưa cô lập theo người dùng.

**Quy mô dữ liệu mẫu:** mỗi môn English/Philosophy có 5 Fill Blank + 6 Matching + 5 Quiz = **16 câu**. Các mẫu lưu trong 3 JSON riêng, test ghép theo cùng `subject` và `chapter_title` trước khi tạo Final Test.

## Hợp đồng dự kiến để viết test

`games/final_test.py` cung cấp `build_final_quiz(chapter)` trả `list[dict]`; mỗi item tối thiểu có:

```python
{
    "id": "unique-id-across-final-exam",
    "q": "Câu hỏi trắc nghiệm?",  # có thể dùng `sentence` cho câu chỗ trống
    "options": ["A", "B"],  # 2–4 lựa chọn phân biệt
    "answer": 0,  # chỉ số hợp lệ, dữ liệu NỘI BỘ của server
    "source_game": "fill_blank",  # hoặc matching, quiz
    "source_id": "p1-01",
}
```

`EnglishQuizGame(..., allow_variable_options=True)` dùng các item này để ẩn đáp án trước chấm và tạo kết quả `score`, `total`, `wrong`, `review`. `calculate_grade_10(score, total)` tính điểm thang 10.

Bộ test dự kiến có thêm hàm `calculate_grade_10(score, total)` **chưa tồn tại** trong `games/final_test.py`. Nếu lựa chọn API khác, cần đồng bộ test và tài liệu **trước khi** code để tránh nhầm kết quả.

## Chạy test

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s tests -p 'test_final_test.py' -v
```

- **CHẠY ĐƯỢC NGAY:** Test dữ liệu mẫu và bảo mật/kết quả của `EnglishQuizGame`.
- Acceptance tests cho `build_final_quiz()` và `calculate_grade_10()` chạy đầy đủ.
- `tests/test_game_flow.py` kiểm tra endpoint HTTP Final Test, khóa bước, cùng chương và trang tổng kết.

## Những quy tắc chưa quyết định

- Nếu một câu không thể tạo ít nhất 2 phương án khác nhau, Final Test báo lỗi dữ liệu; hiện không bổ sung distractor từ game khác.
- Kết quả lưu trong bộ nhớ server, không lưu lâu dài; chỉ phù hợp demo một người dùng.
- Tỷ lệ mẫu ngẫu nhiên giữa các game không bị ràng buộc.
