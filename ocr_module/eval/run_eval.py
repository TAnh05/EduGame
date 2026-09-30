"""
Module đánh giá độ chính xác và Ablation Study (run_eval.py).
Đo các chỉ số:
- Character Error Rate (CER) với chuẩn hóa Unicode NFC
- Thời gian xử lý trung bình mỗi trang (Latency)
- Tỉ lệ ảnh bị cổng chất lượng từ chối
- So sánh các cấu hình tiền xử lý (Ablation Study: A, B, C, D, E)
"""

import os
import sys
import glob
import time
import re
import unicodedata
from typing import Dict, Any, List, Tuple
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def levenshtein_distance(s1: str, s2: str) -> int:
    """Tính khoảng cách Levenshtein (hỗ trợ rapidfuzz, editdistance hoặc pure-python fallback)."""
    try:
        from rapidfuzz.distance import Levenshtein
        return Levenshtein.distance(s1, s2)
    except ImportError:
        pass

    try:
        import editdistance
        return editdistance.eval(s1, s2)
    except ImportError:
        pass

    # Pure Python fallback (DP tối ưu bộ nhớ 2 hàng)
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CURRENT_DIR))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import torch

try:
    from ocr_module.config import OCRModuleConfig
    from ocr_module.pipeline import run_pipeline, OCRResult
except ImportError:
    from config import OCRModuleConfig
    from pipeline import run_pipeline, OCRResult


def clean_text_for_cer(text: str) -> str:
    """Chuẩn hóa văn bản về Unicode NFC và gộp khoảng trắng để đo CER công bằng."""
    normalized = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def calculate_cer(pred: str, truth: str) -> float:
    """
    Tính Character Error Rate (CER):
    CER = Levenshtein_Distance(pred, truth) / max(len(truth), 1)
    """
    p_clean = clean_text_for_cer(pred)
    t_clean = clean_text_for_cer(truth)
    
    if not t_clean and not p_clean:
        return 0.0
    if not t_clean:
        return 1.0
        
    distance = levenshtein_distance(p_clean, t_clean)
    return float(distance) / float(len(t_clean))


def get_ablation_configs() -> Dict[str, OCRModuleConfig]:
    """
    Định nghĩa 5 cấu hình thí nghiệm theo kế hoạch để đo lường hiệu quả từng bước:
    A. Ảnh gốc, không xử lý (Baseline)
    B. A + EXIF + Resize (Cơ bản)
    C. B + Chỉnh nghiêng (Deskew)
    D. C + Chỉnh sáng & Khử bóng (Illumination)
    E. D + Khử nhiễu / Làm nét nhẹ
    """
    # Cấu hình A: Baseline thuần túy
    cfg_a = OCRModuleConfig()
    cfg_a.preprocess.enable_exif = False
    cfg_a.preprocess.enable_resize = False
    cfg_a.preprocess.enable_deskew = False
    cfg_a.preprocess.enable_illumination_fix = False
    cfg_a.preprocess.enable_denoise = False
    cfg_a.preprocess.enable_sharpen = False
    
    # Cấu hình B: EXIF + Resize
    cfg_b = OCRModuleConfig()
    cfg_b.preprocess.enable_exif = True
    cfg_b.preprocess.enable_resize = True
    cfg_b.preprocess.enable_deskew = False
    cfg_b.preprocess.enable_illumination_fix = False
    cfg_b.preprocess.enable_denoise = False
    cfg_b.preprocess.enable_sharpen = False

    # Cấu hình C: B + Chỉnh nghiêng
    cfg_c = OCRModuleConfig()
    cfg_c.preprocess.enable_exif = True
    cfg_c.preprocess.enable_resize = True
    cfg_c.preprocess.enable_deskew = True
    cfg_c.preprocess.enable_illumination_fix = False
    cfg_c.preprocess.enable_denoise = False
    cfg_c.preprocess.enable_sharpen = False

    # Cấu hình D: C + Chỉnh sáng (Illumination fix)
    cfg_d = OCRModuleConfig()
    cfg_d.preprocess.enable_exif = True
    cfg_d.preprocess.enable_resize = True
    cfg_d.preprocess.enable_deskew = True
    cfg_d.preprocess.enable_illumination_fix = True
    cfg_d.preprocess.enable_denoise = False
    cfg_d.preprocess.enable_sharpen = False

    # Cấu hình E: D + Khử nhiễu & Làm nét
    cfg_e = OCRModuleConfig()
    cfg_e.preprocess.enable_exif = True
    cfg_e.preprocess.enable_resize = True
    cfg_e.preprocess.enable_deskew = True
    cfg_e.preprocess.enable_illumination_fix = True
    cfg_e.preprocess.enable_denoise = True
    cfg_e.preprocess.enable_sharpen = True

    return {
        "A (Baseline - Ảnh gốc)": cfg_a,
        "B (A + EXIF + Resize)": cfg_b,
        "C (B + Deskew)": cfg_c,
        "D (C + Chỉnh sáng CLAHE)": cfg_d,
        "E (D + Khử nhiễu/Làm nét)": cfg_e,
    }


def evaluate_dataset(
    images_dir: str, 
    truth_dir: str, 
    cfg: OCRModuleConfig
) -> Dict[str, Any]:
    """Chạy đánh giá trên tập ảnh và ground truth tương ứng."""
    image_paths = sorted(glob.glob(os.path.join(images_dir, "*.*")))
    image_paths = [p for p in image_paths if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    
    if not image_paths:
        print(f"Không tìm thấy ảnh nào trong thư mục: {images_dir}")
        return {"cer_avg": 0.0, "total_samples": 0}

    results = []
    total_time = 0.0
    rejected_count = 0

    for img_path in image_paths:
        base_name = Path(img_path).stem
        truth_path = os.path.join(truth_dir, f"{base_name}.txt")
        
        if not os.path.exists(truth_path):
            continue
            
        with open(truth_path, "r", encoding="utf-8") as f:
            ground_truth = f.read()

        t0 = time.time()
        res: OCRResult = run_pipeline(img_path, cfg=cfg)
        elapsed = time.time() - t0
        total_time += elapsed

        if not res.ok:
            rejected_count += 1
            # Khi bị cổng từ chối, CER = 1.0 (hoặc ghi nhận riêng)
            sample_cer = 1.0
        else:
            sample_cer = calculate_cer(res.text, ground_truth)

        results.append({
            "image": Path(img_path).name,
            "cer": sample_cer,
            "ok": res.ok,
            "time_sec": elapsed
        })

    n = len(results)
    if n == 0:
        return {"error": "Không có cặp ảnh và truth nào khớp tên."}

    avg_cer = sum(r["cer"] for r in results) / n
    avg_time = total_time / n

    return {
        "total_samples": n,
        "cer_avg": avg_cer,
        "avg_time_sec": avg_time,
        "rejection_rate": rejected_count / n,
        "details": results
    }


def run_ablation_study(images_dir: str, truth_dir: str):
    """Thực thi toàn bộ thí nghiệm ablation và in bảng tổng kết so sánh."""
    configs = get_ablation_configs()
    print("=" * 75)
    print("BẮT ĐẦU CHẠY THÍ NGHIỆM ABLATION STUDY CHO TIỀN XỬ LÝ ẢNH")
    print("=" * 75)

    summary_table = []
    for name, cfg in configs.items():
        print(f"\n--- Đang đánh giá: {name} ---")
        metrics = evaluate_dataset(images_dir, truth_dir, cfg)
        if "error" in metrics:
            print(f"Lỗi: {metrics['error']}")
            return
            
        summary_table.append({
            "Cấu hình": name,
            "CER Trung bình": f"{metrics['cer_avg'] * 100:.2f}%",
            "Thời gian/trang": f"{metrics['avg_time_sec']:.2f}s",
            "Tỉ lệ từ chối": f"{metrics['rejection_rate'] * 100:.1f}%"
        })

    print("\n" + "=" * 75)
    print(f"{'Cấu hình':<30} | {'CER Trung bình':<15} | {'Thời gian':<12} | {'Từ chối'}")
    print("-" * 75)
    for row in summary_table:
        print(f"{row['Cấu hình']:<30} | {row['CER Trung bình']:<15} | {row['Thời gian/trang']:<12} | {row['Tỉ lệ từ chối']}")
    print("=" * 75)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(current_dir, "images")
    tru_dir = os.path.join(current_dir, "truth")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(tru_dir, exist_ok=True)
    
    print(f"Thư mục ảnh test: {img_dir}")
    print(f"Thư mục đáp án chuẩn: {tru_dir}")
    
    if len(os.listdir(img_dir)) == 0:
        print("\n[Hướng dẫn] Hãy thêm các ảnh mẫu (.jpg, .png) vào ocr_module/eval/images/")
        print("và tạo file text đáp án chuẩn tương ứng (.txt) vào ocr_module/eval/truth/ để bắt đầu đo CER.")
    else:
        run_ablation_study(img_dir, tru_dir)
