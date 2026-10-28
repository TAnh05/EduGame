# Benchmark PDF render — 28/10/2026

Giả thuyết: render tuần tự giảm peak RAM so với giữ raster của toàn bộ PDF. Chỉ đổi cách giữ/tiêu thụ trang; scale=2.0 và dữ liệu đầu vào giống nhau.

Môi trường: Linux, Python 3.12.14, Pillow 13.0.0, NumPy 2.5.4, PDFium binding pypdfium2 5.14.0. Baseline IO: e3eeaf8; implementation streaming: 76b8ba7. Mỗi phép chạy là process mới; peak RSS đo bằng getrusage. Fixture tự sinh trong RAM: PDF trắng 10 trang 600×800 point, raster 1200×1600 RGB. Không tài liệu thật, không tải weights.

| Lần | Eager RSS KiB | Streaming RSS KiB | Eager elapsed s | Streaming elapsed s | Eager CPU s | Streaming CPU s |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 130064 | 69216 | 0.182159 | 0.126080 | 0.184555 | 0.111128 |
| 2 | 131116 | 68584 | 0.104395 | 0.142815 | 0.093429 | 0.111970 |
| 3 | 129784 | 68536 | 0.156328 | 0.110429 | 0.094361 | 0.110408 |

Median RSS giảm từ 130064 xuống 68584 KiB, khoảng 47.3%. Digest raster của mọi lần giống nhau:
`8f7ff12f423640b48384463fa708740732850e308ef69408cfda9902adf566fa`.

Thời gian có dao động; không kết luận inference nhanh hơn. Peak RSS là toàn process, không phải riêng allocation của ảnh. Không đo GPU/VRAM, model latency, CER hoặc chất lượng người học. Ba ảnh synthetic đi kèm repo không được dùng làm bằng chứng tăng accuracy.

Tái lập từ root repo, mỗi lệnh chạy process riêng:

```bash
python tools/benchmark_pdf_resources.py --mode eager --io-module /path/to/baseline/ocr_module/io_utils.py
python tools/benchmark_pdf_resources.py --mode stream
```

Để đo OCR thật sau khi có model SHA đã review, weights và dữ liệu có quyền sử dụng:

```bash
python tools/profile_ocr.py /path/to/image.png --revision APPROVED_40_CHAR_SHA --truth /path/to/truth.txt
python -m ocr_module.eval.run_eval --images-dir /path/to/images --truth-dir /path/to/truth --revision APPROVED_40_CHAR_SHA --output /path/to/private-report.json
```

Thay placeholder bằng SHA thật, không dùng nguyên văn. profile_ocr báo wall time, CPU time, peak process RSS và CUDA allocated/reserved peak khi có GPU; không in nội dung tài liệu. Đo cold start ở process mới và warm run trong cùng process riêng biệt. Eval giữ CER chuẩn hóa NFC/whitespace; rejection được báo riêng, chi tiết từng ảnh được giữ trong JSON. Không commit báo cáo riêng tư.
