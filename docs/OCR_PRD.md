# Đặc tả phân hệ OCR — MVP

Ngày đánh giá: 28/10/2026 (Asia/Bangkok). Đây là đặc tả từ yêu cầu chủ phân hệ và kiểm tra code, chưa phải kết quả phỏng vấn người dùng ngoài nhóm.

## Phạm vi

Người học đưa ảnh/PDF vào hệ thống, xem cảnh báo chất lượng, trích xuất bằng Vintern, sửa văn bản và bàn giao string cho consumer do nhóm game cung cấp. Người phát triển tích hợp qua callback đồng bộ, không cần biết model bên trong.

Trong phạm vi: JPG/JPEG/PNG/WebP, HEIC/HEIF khi có pillow-heif; PDF scan render bằng PDFium; EXIF, xoay bội 90°, các transform hiện có, hai quality gate, TXT export, adapter string, chẩn đoán từng trang.
Ngoài phạm vi: đọc Word, sinh câu hỏi, luật game, tài khoản, lịch sử học tập, database, HTTP API và hosting. PDF có text cũng được render qua OCR, chưa có đường đọc text-native.

Giới hạn: Python 3.12; 20 MiB/file, 20 triệu pixel/ảnh hoặc trang PDF sau render, tối đa 50 trang/lượt. UI mặc định một trang PDF. Vượt giới hạn báo lỗi, không cắt tài liệu âm thầm. Các giới hạn có thể cấu hình qua `OCRModuleConfig.limits`.

## Yêu cầu và nghiệm thu

| ID | User story / Given–When–Then | Kiểm chứng |
|---|---|---|
| OCR-01 | Given ảnh hợp lệ, When trích xuất, Then trả OCRResult và cho sửa/xuất TXT | pipeline mock, AppTest ảnh |
| OCR-02 | Given PDF nhiều trang, When chọn phạm vi, Then chỉ render phạm vi đó, lần lượt từng trang | test_pdf_streaming |
| OCR-03 | Given ảnh/PDF hỏng hoặc quá giới hạn, When xử lý, Then trả lỗi rõ, không crash UI | test_resource_safety, test_pdf_streaming |
| OCR-04 | Given trang không đạt gate, When ghép kết quả, Then ok=False, pages giữ vị trí rỗng và reason giữ mọi lỗi | test_keeps_all_page_failures_and_metrics |
| OCR-05 | Given text hợp lệ và context hiện tại, When chuyển, Then consumer nhận chính xác một string | test_handoff, test_handoff_integration |
| OCR-06 | Given text sửa tay hoặc OCR ok=False, When chưa xác nhận, Then chặn; xác nhận vẫn không bỏ qua text gate | test_handoff, AppTest sửa tay |
| OCR-07 | Given kết quả cũ, When đổi file/config/góc/phạm vi hoặc OCR lại, Then không chuyển lại editor cũ | test_ui_handoff |
| OCR-08 | Given chưa có consumer hoặc consumer raise, When chuyển, Then không báo nhận thành công | test_handoff, UI standalone |
| OCR-09 | Given OOM, When còn khả năng giảm tile, Then giải phóng tensor và retry một lần bằng nửa max_num | test_inference_mock — OOM mô phỏng |
| OCR-10 | Given dataset rỗng/thiếu truth, When đánh giá, Then báo lỗi và không kết luận CER | test_eval |

## Phi chức năng và ranh giới bằng chứng

- Tính đúng: các tham số model/prompt/dtype/tiles và thuật toán preprocess mặc định giữ nguyên. Không nới quality gate để che lỗi.
- Bộ nhớ: pipeline không giữ toàn bộ raster PDF; model được cache và inference tuần tự giữa các session trong cùng process.
- Bảo mật: không lưu upload ra đĩa; không commit tài liệu riêng tư hoặc weights. `trust_remote_code=True` là rủi ro còn lại; production cần review mã model và pin immutable SHA.
- Tái lập: CI CPU không tải weights, kiểm tra contract/unit/integration/UI. Job CPU inference sử dụng model giả và coverage tối thiểu 75%.
- Chất lượng thật: chưa có SLO CER/latency được chủ sản phẩm xác nhận, chưa có dataset thật có consent và ground truth. Không suy từ mock/synthetic ra độ chính xác thực tế.

## Quyết định cần nhóm xác nhận

Consumer game thực, model SHA đã review, phần cứng demo và mục tiêu CER/latency; dữ liệu thật tối thiểu 30 trang phân theo Việt/Anh/song ngữ và điều kiện chụp. Codex có thể chạy đo sau khi có các đầu vào này; không tự đặt số liệu hay quyền sử dụng dữ liệu.
