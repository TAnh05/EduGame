# Quy trình nhóm, log, diff và vai trò leader

## Luồng Git

- `main`: chỉ nhận phiên bản đã review và pass CI.
- `toanbranch`: nhánh tích hợp của phân hệ OCR hiện tại.
- Mỗi thành viên làm nhánh ngắn từ nhánh tích hợp: `feature/<ten>-<muc-tieu>` hoặc `fix/<ten>-<bug>`.
- Không push trực tiếp lên nhánh tích hợp nếu nhóm dùng pull request. Một PR chỉ xử lý một mục tiêu có acceptance criteria.

## Checklist review diff

1. Diff có đúng phạm vi issue không? Có file/dependency/dữ liệu thừa không?
2. Đầu vào hỏng, PDF nhiều trang, CPU/GPU/OOM có xử lý rõ ràng không?
3. `OCRResult` có thay đổi trường, kiểu, default hoặc semantics không? Nếu có, contract test và consumer đã được cập nhật chưa?
4. Cờ preprocess có default, test và A/B chưa? Không hard-binarize ảnh đưa vào Vintern.
5. Với ngưỡng chất lượng/model/generation: có báo cáo dữ liệu, language slice, CER, latency, false reject không?
6. Test/CI có pass? Nếu chưa chạy được, PR phải nêu nguyên nhân và rủi ro.

## Leader dùng log/diff để đánh giá hiệu quả

Leader không đánh giá bằng số dòng code hay số commit. Mỗi tuần xem issue/PR, `git log`, diff review, kết quả CI/test, báo cáo eval và blocker.

| Tiêu chí | Bằng chứng khách quan |
|---|---|
| Hoàn thành đúng mục tiêu | Issue/acceptance criteria được đóng, demo hoạt động |
| Chất lượng kỹ thuật | Diff nhỏ, dễ review, không sửa ngoài phạm vi, CI pass |
| Không tạo regression | Test mới/cũ pass; case lỗi được thêm vào regression suite |
| Tác động OCR có căn cứ | CER per-image, rejection, latency, dataset scope |
| Hợp tác | PR mô tả rõ, phản hồi review, bàn giao file/config/cách chạy |
| Chủ động quản lý rủi ro | Nêu limitation, không che lỗi bằng threshold hoặc mock kết quả |

## Log tối thiểu cho mỗi PR

```text
Mục tiêu:
File/hàm thay đổi:
Acceptance criteria:
Lệnh test và kết quả:
Ảnh hưởng OCR/performance (nếu có):
Rủi ro/limitation còn lại:
Reviewer và quyết định:
```

Lưu log trong PR/Issue GitHub; không đưa dữ liệu nhạy cảm hoặc toàn bộ nội dung tài liệu học viên vào đó.
