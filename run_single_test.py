"""
Tập lệnh chạy thử 1 ảnh duy nhất qua toàn bộ Pipeline (run_single_test.py).
Dùng để kiểm tra nhanh mô hình Vintern-1B v3.5 trên GPU RTX 2050 và xem kết quả.
"""

import sys
import os
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm thư mục hiện tại vào sys.path
sys.path.insert(0, os.path.abspath("."))

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import run_pipeline, OCRResult


def main():
    # Ảnh mẫu mặc định
    default_img = os.path.join("ocr_module", "eval", "images", "sample_clean.png")
    
    # Cho phép người dùng truyền đường dẫn ảnh từ dòng lệnh: python run_single_test.py path/to/image.jpg
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        img_path = default_img

    if not os.path.exists(img_path):
        print(f"[-] Không tìm thấy ảnh: {img_path}")
        print("[*] Bạn có thể truyền đường dẫn ảnh: python run_single_test.py đường_dẫn_ảnh.jpg")
        return

    print("=" * 65)
    print("CHẠY THỬ NGHIỆM TRÍCH XUẤT 1 ẢNH - VINTERN-1B v3.5")
    print("=" * 65)
    print(f"[*] Ảnh thử nghiệm: {img_path}")

    cfg = OCRModuleConfig()
    print(f"[*] Thiết bị suy luận: {cfg.model.device.upper()} ({cfg.model.torch_dtype})")
    print(f"[*] Cấu hình ô ảnh (max_num): {cfg.model.max_num}")
    print("[*] Đang bắt đầu xử lý pipeline (Tiền xử lý -> Vintern OCR -> Hậu xử lý)...")
    print("-" * 65)

    start_time = time.time()
    result: OCRResult = run_pipeline(img_path, cfg=cfg)
    elapsed_time = time.time() - start_time

    print("KẾT QUẢ TRÍCH XUẤT:")
    print("-" * 65)
    if result.ok:
        print("[+] Trạng thái: THÀNH CÔNG (Qua cổng chất lượng)")
    else:
        print(f"[-] Trạng thái: THẤT BẠI / TỪ CHỐI ({result.reason})")

    if result.warnings:
        print("\n[!] Cảnh báo:")
        for w in result.warnings:
            print(f"    - {w}")

    print("\n--- VĂN BẢN TRÍCH XUẤT ĐƯỢC ---")
    print(result.text if result.text else "(Không có văn bản)")
    print("------------------------------")
    print(f"[*] Thời gian xử lý: {elapsed_time:.2f} giây")
    print("=" * 65)


if __name__ == "__main__":
    main()
