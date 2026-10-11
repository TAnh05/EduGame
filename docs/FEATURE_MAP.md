# Bản đồ tính năng và kiểm soát mã nguồn

Tài liệu này là điểm xuất phát khi demo hoặc bảo trì. Mỗi thay đổi phải được truy về một tính năng, một vị trí code, một cấu hình và một cách kiểm chứng.

| Tính năng | Điểm vào / file chính | Cấu hình hoặc dữ liệu liên quan | Cách kiểm chứng |
|---|---|---|---|
| Upload ảnh/PDF | `ocr_module/ui_upload.py:main`, `ocr_module/pipeline.py:run_pipeline` | bytes/path/PIL; `pdf_start_page`, `pdf_max_pages` | Upload ảnh; chọn 1 trang PDF; test `test_pipeline_safety` |
| Đọc PDF, HEIC, EXIF | `ocr_module/io_utils.py` | `PDF_AVAILABLE`, `HEIF_AVAILABLE`, `PreprocessConfig.enable_exif` | PDF nhiều trang, ảnh điện thoại xoay EXIF |
| Cổng chất lượng ảnh | `ocr_module/quality.py:evaluate_quality` | `QualityThresholds` trong `config.py` | Ảnh quá nhỏ/mờ; kiểm tra `ok`, `reason`, `warnings` |
| Tiền xử lý | `ocr_module/preprocess.py:run_preprocessing_pipeline` | các cờ `enable_resize`, `enable_deskew`, `enable_illumination_fix`, `enable_denoise`, `enable_sharpen` | So sánh A/B bằng `ocr_module.eval.run_eval` |
| OCR Vintern và OOM | `ocr_module/ocr_vintern.py:ocr_image_vintern` | `ModelConfig`, `StripSplittingConfig` | Chạy một ảnh trên GPU; quan sát fallback/log khi OOM |
| Hậu xử lý/gate văn bản | `ocr_module/postprocess.py:clean_and_gate_text` | `QualityGateConfig` | Unit test text ngắn, ký tự rác, lặp n-gram, Anh/Việt |
| Hợp đồng kết quả | `ocr_module/pipeline.py:OCRResult` | trường `text`, `ok`, `reason`, `warnings`, `pages`, `metrics`, `processed_preview` | `tests/test_contract.py` |
| UI và xuất TXT | `ocr_module/ui_upload.py` | Streamlit `session_state`; cấu hình sidebar | Smoke test import; manual checklist trong `DEFENSE_GUIDE.md` |
| CER/Ablation | `ocr_module/eval/run_eval.py` | ảnh/truth cùng basename trong `ocr_module/eval/` | `python -m ocr_module.eval.run_eval` |

## Cách trả lời khi bị hỏi “sửa ở đâu?”

1. Xác định tính năng trong bảng trên.
2. Nêu file/hàm và config thay đổi, không chỉ nêu tên thư mục.
3. Chỉ ra test hoặc lệnh xác nhận trước/sau thay đổi.
4. Nếu thay đổi ảnh hưởng `OCRResult`, kiểm tra consumer và contract test trước khi sửa.

Ví dụ: “Muốn tắt làm nét, sửa `PreprocessConfig.enable_sharpen` hoặc checkbox UI; `run_preprocessing_pipeline()` chỉ gọi `mild_sharpen()` khi cờ bật; regression test xác nhận cờ tắt không làm nét ngầm.”
