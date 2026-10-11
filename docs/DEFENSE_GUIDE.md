# Kịch bản bảo vệ dự án

## Demo 5–7 phút

1. Mở README, giải thích pipeline: Input/PDF → preprocessing → Vintern → postprocess/gate → `OCRResult` → UI.
2. Mở `FEATURE_MAP.md`; chỉ rõ nơi sửa PDF, deskew, quality gate và OCR result.
3. Chạy `python test_stage0_env.py`, sau đó `python -m unittest discover -s tests -v`.
4. Mở một PDF, chọn một trang trước để demo thời gian xử lý và lỗi chọn trang ngoài phạm vi.
5. Mở `AGENT_WORKFLOW.md`: trình bày Agent hỗ trợ nhưng nhóm review diff/test/commit.
6. Mở GitHub: `git log --oneline`, diff của hai commit PDF và sharpen, workflow CI.
7. Kết thúc bằng limitation trung thực: chỉ có 3 sample synthetic; chưa tuyên bố accuracy production cho đến khi có tập thật có consent.

## Câu hỏi thường gặp

**“Tính năng X ở đâu?”**  Trả lời theo `FEATURE_MAP.md`: file, hàm, config, test. Không chỉ nói “trong module OCR”.

**“Agent làm hết thì nhóm hiểu gì?”**  Agent không được merge. Nhóm đặt acceptance criteria, đọc diff, kiểm tra API/contract, chạy test và chịu trách nhiệm về quyết định.

**“Làm sao biết thành viên hiệu quả?”**  Dựa trên PR/issue/diff/CI/test, regression được ngăn chặn, bàn giao và chất lượng giao tiếp; không dựa vào số dòng code.

**“Test nâng cao ở đâu?”**  CI chạy compile + unit/contract. Pipeline có test failure handling; evaluator CER/A–E dùng cho thay đổi OCR. Với thay đổi model/preprocess, báo cáo cần per-image CER, rejection và latency.

**“Vì sao không đổi threshold để ảnh nào cũng qua?”**  Đó là đánh đổi false reject/false accept. Chỉ hiệu chuẩn từ dữ liệu thật có nhãn, phân theo ngôn ngữ và loại tài liệu.

## Checklist trước ngày bảo vệ

- [ ] Cài Python/venv/GPU đúng máy demo; chạy smoke test thành công.
- [ ] Có PDF/ảnh được phép sử dụng, không có dữ liệu nhạy cảm.
- [ ] CI xanh ở nhánh demo.
- [ ] Mỗi người biết ít nhất một feature và một commit mình phụ trách.
- [ ] Chuẩn bị danh sách limitation thật, không tuyên bố benchmark chưa chạy.
