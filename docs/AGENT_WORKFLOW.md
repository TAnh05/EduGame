# Quy trình xây dựng hệ thống với Agent

## Nguyên tắc

Agent (Copilot, Cursor, Claude, Codex…) là công cụ hỗ trợ phân tích, sinh phương án và viết phần lặp lại. Thành viên chịu trách nhiệm hiểu kiến trúc, kiểm tra diff, chạy test và quyết định merge. Không đưa token, tài liệu riêng tư hoặc dữ liệu người học chưa được phép lưu vào prompt.

## Chu trình làm việc bắt buộc

1. **Nêu nhiệm vụ và tiêu chí chấp nhận.** Ví dụ: “PDF chọn trang 2–3, không render các trang còn lại, PDF lỗi trả `OCRResult(ok=False)`.”
2. **Yêu cầu Agent đọc map dự án trước.** Dùng `AGENTS.md` và `FEATURE_MAP.md`; Agent phải nêu file/hàm có thể ảnh hưởng.
3. **Yêu cầu Agent đề xuất diff nhỏ.** Không đổi nhiều hành vi, dependency, model revision hay threshold trong cùng một lần.
4. **Con người review diff.** Kiểm tra input/output, exception, hiệu năng, bảo mật, contract `OCRResult`, và điều gì Agent chưa chứng minh.
5. **Chạy test phù hợp.** Unit/contract trước; PDF/UI manual; CER/A-B nếu thay đổi OCR/preprocess/model.
6. **Commit có truy vết.** Một commit giải quyết một mục đích, message dạng `type(scope): outcome`; ghi limitation nếu chưa benchmark được.

## Hai ví dụ từ dự án

### PDF page range

- Vấn đề: OCR toàn bộ PDF dài tốn RAM/VRAM và UI không cho giới hạn trang.
- Agent hỗ trợ: đề xuất thêm `start_page`, `max_pages`, đóng `page`/`bitmap`.
- Người review: giữ tương thích API, kiểm tra lỗi chọn trang ngoài phạm vi trả về `OCRResult` thay vì crash.
- Bằng chứng: commit `cbb4137`; test PDF/manual render.

### Sharpen bị bật ngầm

- Vấn đề: `enable_sharpen=False` nhưng ảnh mờ vẫn bị `mild_sharpen()`; ablation không trung thực.
- Agent hỗ trợ: định vị điều kiện trong `run_preprocessing_pipeline()`.
- Người review: sửa chỉ theo cờ, thêm regression test, không khẳng định cải thiện CER khi chưa có tập dữ liệu thật.
- Bằng chứng: commit `4bf5b3e`; `tests/test_pipeline_safety.py`.

## Demo skill

| Prompt demo | Skill nên kích hoạt | Kết quả cần trình bày |
|---|---|---|
| “So sánh deskew bật/tắt trên tập eval” | `ocr-eval-ablation` | CER từng ảnh, latency, rejection, không chỉ average |
| “Thêm/tinh chỉnh CLAHE” | `ocr-preprocess-experiment` | cờ config, test, A/B, quyết định default |
| “Vintern OOM hoặc max_num” | `vintern-inference-tuning` | GPU/dtype/VRAM, fallback và benchmark |
| “OCR mất dòng/lặp chữ” | `ocr-error-triage` | tái hiện, định vị layer, regression case |
| “Đổi blur threshold hoặc reject policy” | `ocr-quality-gates` | confusion matrix và warn/reject theo ngôn ngữ |

Không cần dùng skill cho việc chỉ đổi màu nút hoặc sửa chính tả README. Skill giúp Agent đi đúng quy trình; không thay thế review của nhóm.
