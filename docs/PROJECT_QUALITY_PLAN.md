# Kế hoạch nâng chất lượng Image-to-Text

## Mục tiêu

Nâng độ tin cậy của OCR mà không làm giảm khả năng đọc tài liệu hợp lệ, đặc biệt với tiếng Anh, tiếng Việt và tài liệu song ngữ. Mọi thay đổi mặc định phải có bằng chứng từ dữ liệu thật được phép sử dụng.

## Giai đoạn 0 — thiết lập đường cơ sở

- Chạy `python test_stage0_env.py` sau khi sửa môi trường; hiện lệnh này bị chặn trước khi vào test vì trình khởi chạy Python đang trỏ tới `C:\Users\PC\AppData\Local\Programs\Python\Python313\python.exe` không tồn tại.
- Chạy `python -m ocr_module.eval.run_eval` khi môi trường Python đã hoạt động; ghi lại commit, GPU/CPU, phiên bản dependency và A–E baseline.
- Xác nhận ba cặp mẫu dưới `ocr_module/eval/` là smoke test tổng hợp, không dùng chúng để kết luận chất lượng.

**Tiêu chí hoàn tất:** có baseline lặp lại được và biết chính xác môi trường chạy.

## Giai đoạn 1 — tập đánh giá thực tế

- Thu tối thiểu 30 trang có quyền sử dụng và ground truth UTF-8 khớp từng ảnh.
- Cân bằng tối thiểu theo tiếng Việt, tiếng Anh, song ngữ; ảnh điện thoại/scan; sáng tối/bóng/xiên; trang dày gây strip splitting.
- Lưu manifest với ID mẫu, ngôn ngữ, điều kiện chụp, loại tài liệu, nhãn lỗi và quyền lưu giữ; không commit dữ liệu nhạy cảm.

**Tiêu chí hoàn tất:** mỗi cấu hình có cùng danh sách mẫu, có thể báo CER theo từng ảnh và theo lát dữ liệu.

## Giai đoạn 2 — sửa an toàn các điểm rủi ro hiện hữu

1. Giữ `min_vietnamese_diacritic_ratio` ở mức cảnh báo. Hiện `validate_extracted_text()` không từ chối theo tiêu chí này; chỉ chuyển thành reject sau khi có nhận diện ngôn ngữ và số liệu false-reject trên cả ba nhóm ngôn ngữ.
2. Hiệu chuẩn các ngưỡng `blur_threshold`, brightness và contrast bằng phân bố dữ liệu đã gán nhãn; đo false accept/reject thay vì đặt tay.
3. A/B `repetition_penalty=1.2`, `max_num=2`, `max_new_tokens=1024`, prompt và các cờ preprocess riêng lẻ. Báo cáo ảnh tốt lên, xấu đi, bị từ chối và latency—không chỉ CER trung bình.
4. Kiểm thử hồi quy cho xử lý lặp: `deduplicate_consecutive_lines()`, `merge_strip_texts()` và overlap 60px phải giữ được đáp án/đầu mục lặp hợp lệ.
5. Ghim immutable revision cho Vintern trước khi dùng kết quả như benchmark hoặc phát hành; giữ đường OOM fallback có log và test.

**Tiêu chí hoàn tất:** không có thay đổi mặc định nào thiếu báo cáo paired evaluation và regression case.

## Giai đoạn 3 — độ bền hợp đồng và vận hành

- Thêm test contract cho `OCRResult` trước khi tích hợp sang module sinh câu hỏi; thay đổi cấu trúc cần có xác nhận của consumer.
- Tách rõ warning và reject ở UI để tài liệu dùng được không bị trình bày như lỗi cứng.
- Với mỗi lỗi đã sửa, thêm một case eval hồi quy nếu quyền giữ tài liệu cho phép.
- Chỉ sau dữ liệu đủ rộng mới chọn default mới; nếu kết quả không rõ ràng, giữ default hiện tại.

## Cách dùng bộ skill

- `$ocr-eval-ablation`: đo CER, chạy A/B/ablation, hoặc thêm eval data.
- `$ocr-preprocess-experiment`: thêm/tinh chỉnh deskew, CLAHE, resize, denoise, sharpen, perspective.
- `$vintern-inference-tuning`: chỉnh Vintern, prompt/generation, tiles, strip splitting, VRAM/OOM.
- `$ocr-error-triage`: một lỗi OCR cụ thể, bắt đầu từ root cause.
- `$ocr-quality-gates`: ngưỡng hoặc quyết định warn/reject ở đầu vào/đầu ra.
