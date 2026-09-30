# Module OCR & Tiền xử lý ảnh tài liệu - Dự án EduGame

> **Phân hệ**: Tiền xử lý ảnh tài liệu học tập → Trích xuất văn bản qua Vintern-1B v3.5 → Giao diện Upload & Bàn giao dữ liệu cho bước sinh câu hỏi ôn tập bằng game.  
> **Thành viên phụ trách**: `maitoan2408`  
> **Nhánh phát triển**: `toanbranch`  
> **Dự án**: [EduGame](https://github.com/TAnh05/EduGame) (Nhóm 5 người, Python + Streamlit).

---

## 1. Tổng quan Kiến trúc

Hệ thống được thiết kế theo 4 nguyên tắc cốt lõi:
1. **Đo trước, xử lý sau**: Mọi bước tiền xử lý đều có cờ bật/tắt độc lập và đo lường CER (Character Error Rate) qua Ablation Study.
2. **Không làm hỏng ảnh**: Giữ ảnh màu/xám tự nhiên, tuyệt đối không nhị phân hóa cứng (Otsu/Binarization) gây mất nét chữ với Vision-Language Model.
3. **Cổng kiểm tra chất lượng 2 đầu (Quality Gates)**:
   - *Cổng đầu vào (Ảnh)*: Đo độ mờ (Laplacian variance), độ sáng, tương phản; từ chối ảnh quá mờ hoặc quá tối kèm cảnh báo cụ thể.
   - *Cổng đầu ra (Văn bản)*: Kiểm tra độ dài tối thiểu, tỷ lệ ký tự hợp lệ, phát hiện model loop (n-gram repetition) và tỷ lệ dấu tiếng Việt.
4. **Giao diện dữ liệu chuẩn (`OCRResult`)**: Đóng gói đầu ra độc lập với backend, giúp module sinh câu hỏi ôn tập dễ dàng tích hợp.

```
Đọc ảnh / PDF / HEIC 
   ↓
Sửa góc EXIF → Resize an toàn → Đo chất lượng ảnh
   ↓
Chỉnh nghiêng dòng (Deskew) → Cân bằng sáng (CLAHE + Background Division)
   ↓
Cắt dải ngang (Horizontal Histogram) nếu tài liệu dày chữ
   ↓
Mô hình Vintern-1B v3.5 (Tự động hạ max_num nếu OOM trên GPU 4GB)
   ↓
Hậu xử lý (Chuẩn hóa NFC, dọn markdown, khử lặp) → Cổng chất lượng văn bản
   ↓
Đầu ra chuẩn OCRResult → Giao diện Streamlit / Module tạo câu hỏi Game
```

---

## 2. Cấu trúc thư mục

```
ocr_module/
├── __init__.py
├── config.py          # Ngưỡng chất lượng, kích thước tối đa, tham số sinh & cờ ablation
├── io_utils.py        # Đọc ảnh, EXIF transpose, hỗ trợ HEIC (iPhone) & PDF scan đa trang
├── quality.py         # Đo độ mờ (Laplacian var), độ sáng, tương phản, độ phân giải
├── preprocess.py      # Chuỗi tiền xử lý: Resize, xoay, deskew, nắn sáng CLAHE, khử nhiễu
├── ocr_vintern.py     # Nạp Vintern-1B v3.5, load_image chuẩn, cắt dải ảnh, xử lý OOM fallback
├── postprocess.py     # Chuẩn hóa Unicode NFC, lọc markdown, khử lặp dòng/n-gram, cổng chất lượng
├── pipeline.py        # Điều phối toàn bộ luồng: run_pipeline(source) -> OCRResult
├── ui_upload.py       # Giao diện Web Streamlit hoàn chỉnh (so sánh ảnh, xoay 90°, sửa text)
└── eval/
    ├── images/        # Bộ ảnh kiểm thử mẫu (sạch, nghiêng, bóng đổ)
    ├── truth/         # Văn bản đáp án chuẩn (ground truth)
    └── run_eval.py    # Đo CER (Levenshtein distance) và chạy Ablation Study 5 cấu hình (A -> E)

run_single_test.py     # Script kiểm tra nhanh 1 ảnh từ dòng lệnh
test_stage0_env.py     # Script kiểm tra môi trường, GPU CUDA và logic module
requirements.txt       # Danh sách thư viện phụ thuộc
.gitignore             # Chặn file rác, file tạm, cache và model weights
```

---

## 3. Định dạng dữ liệu đầu ra (`OCRResult`)

```python
@dataclass
class OCRResult:
    text: str                          # Toàn bộ văn bản đã được làm sạch và chuẩn hóa NFC
    ok: bool                           # Vượt qua cả 2 cổng chất lượng (Ảnh & Văn bản) chưa
    reason: str                        # Lý do cụ thể nếu bị từ chối (để UI hướng dẫn người dùng chụp lại)
    warnings: list[str]                # Danh sách cảnh báo ("Ảnh hơi mờ", "Đã xoay 90°", v.v.)
    pages: list[str]                   # Danh sách văn bản theo từng trang (khi upload file PDF đa trang)
    metrics: dict                      # Các chỉ số đo đạc vật lý của ảnh (độ nét, sáng, tương phản)
    processed_preview: Optional[Image] # Ảnh sau khi qua chuỗi tiền xử lý để hiển thị so sánh
```

---

## 4. Hướng dẫn cài đặt & Chạy

### 4.1 Cài đặt môi trường

1. **Cài PyTorch với GPU CUDA** (nếu máy có GPU NVIDIA):
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
   ```
2. **Cài đặt các gói phụ thuộc**:
   ```bash
   pip install -r requirements.txt
   ```

### 4.2 Chạy kiểm tra môi trường
```bash
python test_stage0_env.py
```

### 4.3 Chạy thử nghiệm trích xuất 1 ảnh (CLI)
```bash
# Thử nghiệm trên ảnh mẫu:
python run_single_test.py

# Hoặc thử nghiệm ảnh bất kỳ của bạn:
python run_single_test.py "duong_dan_anh.jpg"
```

### 4.4 Khởi động Giao diện Web Streamlit
```bash
streamlit run app.py
# hoặc:
streamlit run ocr_module/ui_upload.py
```
- Truy cập `http://localhost:8501`.
- Kéo thả ảnh hoặc PDF scan, so sánh ảnh gốc và ảnh đã xử lý trực quan.
- Tùy chỉnh xoay 90° nếu ảnh ngược, xem các chỉ số chất lượng ảnh.
- Nhận diện văn bản, chỉnh sửa trực tiếp trên giao diện và bấm nút chuyển tiếp sang module tạo câu hỏi game.

### 4.5 Đánh giá độ chính xác & Ablation Study
```bash
python -m ocr_module.eval.run_eval
```
Script sẽ so sánh 5 cấu hình tiền xử lý:
- **A**: Ảnh gốc (Baseline)
- **B**: A + EXIF + Resize
- **C**: B + Chỉnh nghiêng (Deskew)
- **D**: C + Cân bằng sáng & Khử bóng (CLAHE)
- **E**: D + Khử nhiễu & Làm nét
In ra bảng tổng hợp gồm CER trung bình, thời gian xử lý và tỷ lệ từ chối.
