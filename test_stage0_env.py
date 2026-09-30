"""
Tập lệnh kiểm tra môi trường Giai đoạn 0 (test_stage0_env.py).
Kiểm tra:
1. Thư viện phần cứng & PyTorch CUDA (RTX 2050 4GB VRAM)
2. Các thư viện phụ thuộc (OpenCV, PIL, Transformers, Timm, Streamlit, Editdistance)
3. Kiểm tra tính toàn vẹn của các module trong ocr_module
4. Chạy thử quy trình tiền xử lý và hậu xử lý trên một ảnh giả lập
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=" * 60)
print("KIỂM TRA MÔI TRƯỜNG GIAI ĐOẠN 0: OCR MODULE")
print("=" * 60)

# 1. Kiểm tra Python & Thư viện cơ bản
print(f"[*] Python Version: {sys.version.split()[0]}")

try:
    import torch
    print(f"[+] PyTorch: {torch.__version__}")
    cuda_avail = torch.cuda.is_available()
    print(f"    - CUDA khả dụng: {cuda_avail}")
    if cuda_avail:
        print(f"    - Tên GPU: {torch.cuda.get_device_name(0)}")
        total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
        print(f"    - VRAM: {total_vram:.0f} MB")
except ImportError as e:
    print(f"[-] PyTorch: Chưa cài đặt ({e})")

# 2. Kiểm tra các gói liên quan
packages = [
    ("cv2", "OpenCV"),
    ("PIL", "Pillow"),
    ("transformers", "Hugging Face Transformers"),
    ("timm", "PyTorch Image Models (timm)"),
    ("accelerate", "Accelerate"),
    ("streamlit", "Streamlit"),
    ("editdistance", "Editdistance"),
    ("pypdfium2", "PyPDFium2 (PDF support)"),
    ("pillow_heif", "Pillow-HEIF (iPhone HEIC support)"),
]

for mod_name, disp_name in packages:
    try:
        mod = __import__(mod_name)
        ver = getattr(mod, "__version__", "OK")
        print(f"[+] {disp_name:<30}: {ver}")
    except ImportError:
        print(f"[-] {disp_name:<30}: Chưa cài đặt")

# 3. Kiểm tra import các module nội bộ
print("\n" + "-" * 60)
print("KIỂM TRA CÁC MODULE TRONG ocr_module/")
print("-" * 60)

sys.path.insert(0, os.path.abspath("."))

try:
    from ocr_module.config import OCRModuleConfig
    print("[+] ocr_module.config: OK")
except Exception as e:
    print(f"[-] ocr_module.config: Lỗi ({e})")

try:
    from ocr_module.io_utils import pil_to_cv2, cv2_to_pil
    print("[+] ocr_module.io_utils: OK")
except Exception as e:
    print(f"[-] ocr_module.io_utils: Lỗi ({e})")

try:
    from ocr_module.quality import measure_image_quality, evaluate_quality
    print("[+] ocr_module.quality: OK")
except Exception as e:
    print(f"[-] ocr_module.quality: Lỗi ({e})")

try:
    from ocr_module.preprocess import run_preprocessing_pipeline
    print("[+] ocr_module.preprocess: OK")
except Exception as e:
    print(f"[-] ocr_module.preprocess: Lỗi ({e})")

try:
    from ocr_module.postprocess import clean_and_gate_text
    print("[+] ocr_module.postprocess: OK")
except Exception as e:
    print(f"[-] ocr_module.postprocess: Lỗi ({e})")

# 4. Kiểm tra thử nghiệm tiền xử lý & hậu xử lý trên dữ liệu mẫu
print("\n" + "-" * 60)
print("KIỂM TRA THỰC THI LOGIC TIỀN XỬ LÝ & HẬU XỬ LÝ")
print("-" * 60)

try:
    import numpy as np
    # Tạo ảnh trắng 800x600 có chữ giả lập
    test_img = np.full((600, 800, 3), 245, dtype=np.uint8)
    import cv2
    cv2.putText(test_img, "Kiem tra tien xu ly anh OCR Vintern 1B", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
    cv2.putText(test_img, "Chao mung ban den voi he thong on tap bang game!", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 30, 30), 2)

    cfg = OCRModuleConfig()
    proc_bgr, passed, reason, warnings, metrics = run_preprocessing_pipeline(
        test_img, 
        prep_cfg=cfg.preprocess, 
        quality_cfg=cfg.quality
    )
    print(f"[+] Tiền xử lý ảnh thành công:")
    print(f"    - Độ nét (Laplacian): {metrics['blur']:.2f}")
    print(f"    - Độ sáng TB: {metrics['brightness']:.1f}")
    print(f"    - Độ tương phản: {metrics['contrast']:.1f}")
    print(f"    - Vượt qua cổng chất lượng: {passed}")

    # Thử nghiệm hậu xử lý
    sample_raw = "### Tiêu đề bài học\n**Định nghĩa:** Quang hợp là quá trình cây xanh tổng hợp chất hữu cơ.<s>"
    cleaned, gate_ok, gate_reason, gate_warnings = clean_and_gate_text(sample_raw, cfg.gate)
    print(f"[+] Hậu xử lý văn bản:")
    print(f"    - Văn bản gốc: {repr(sample_raw)}")
    print(f"    - Văn bản sạch: {repr(cleaned)}")
    print(f"    - Đạt chuẩn: {gate_ok}")

except Exception as e:
    print(f"[-] Lỗi kiểm tra luồng logic: {e}")

print("\n" + "=" * 60)
