"""
Module điều phối toàn bộ Pipeline (pipeline.py).
Ghép nối các tầng:
IO -> Preprocess -> Quality Check -> OCR Engine (Vintern-1B v3.5) -> Postprocess & Quality Gate.
Trả về dataclass chuẩn OCRResult sẵn sàng tích hợp với module tạo câu hỏi ôn tập.
"""

from dataclasses import dataclass, field
from typing import List, Union, Optional, Dict, Any, Tuple
import numpy as np
from PIL import Image

from .config import OCRModuleConfig
from .io_utils import (
    load_image_from_bytes, 
    pil_to_cv2, 
    cv2_to_pil, 
    load_images_from_pdf,
    PDF_AVAILABLE
)
from .preprocess import run_preprocessing_pipeline
from .postprocess import clean_and_gate_text
from .ocr_vintern import ocr_image_vintern


@dataclass
class OCRResult:
    """Đầu ra chuẩn để bàn giao cho module tạo câu hỏi ôn tập / sinh game."""
    text: str
    ok: bool                                 # Có vượt qua các cổng kiểm tra chất lượng không
    reason: str = ""                         # Lý do cụ thể nếu ok=False (để giao diện hướng dẫn người dùng chụp lại)
    warnings: List[str] = field(default_factory=list)  # Các cảnh báo (VD: "Ảnh hơi mờ", "Đã xoay 90°", v.v.)
    pages: List[str] = field(default_factory=list)     # Nội dung text theo từng trang / từng ảnh
    metrics: Dict[str, Any] = field(default_factory=dict) # Các chỉ số đo lường ảnh (độ mờ, sáng, tương phản)
    processed_preview: Optional[Image.Image] = None     # Ảnh PIL sau tiền xử lý để hiển thị so sánh trên UI


def process_single_image(
    pil_img: Image.Image,
    cfg: OCRModuleConfig,
    manual_rotation_deg: int = 0
) -> Tuple[str, bool, str, List[str], Dict[str, Any], Image.Image]:
    """
    Xử lý tiền xử lý, OCR và hậu xử lý cho một ảnh PIL duy nhất.
    """
    # 1. Chuyển sang OpenCV BGR
    img_bgr = pil_to_cv2(pil_img)
    
    # 2. Tiền xử lý ảnh (Resize, Quality, Deskew, Illumination, ...)
    proc_bgr, q_passed, q_reason, prep_warnings, metrics = run_preprocessing_pipeline(
        img_bgr, 
        prep_cfg=cfg.preprocess, 
        quality_cfg=cfg.quality, 
        manual_rotation_deg=manual_rotation_deg
    )
    
    preview_pil = cv2_to_pil(proc_bgr)
    
    # Nếu ảnh không qua cổng chất lượng đầu vào (quá mờ, quá tối, hỏng nặng)
    if not q_passed:
        return "", False, q_reason, prep_warnings, metrics, preview_pil

    # 3. Thực thi nhận dạng chữ bằng Vintern-1B v3.5
    try:
        raw_text = ocr_image_vintern(preview_pil, cfg.model, cfg.strip)
    except Exception as e:
        return "", False, f"Lỗi trong quá trình nhận dạng mô hình Vintern: {str(e)}", prep_warnings, metrics, preview_pil

    # 4. Hậu xử lý văn bản và Cổng chất lượng đầu ra
    clean_text, gate_ok, gate_reason, post_warnings = clean_and_gate_text(raw_text, cfg.gate)
    
    all_warnings = prep_warnings + post_warnings
    return clean_text, gate_ok, gate_reason, all_warnings, metrics, preview_pil


def run_pipeline(
    source: Union[bytes, str, Image.Image, List[Any]],
    cfg: Optional[OCRModuleConfig] = None,
    manual_rotation_deg: int = 0
) -> OCRResult:
    """
    Hàm entry point chính của module:
    Nhận đầu vào linh hoạt (bytes từ UploadedFile, đường dẫn file, PIL Image, hoặc file PDF)
    và trả về đối tượng chuẩn OCRResult.
    """
    if cfg is None:
        cfg = OCRModuleConfig()

    # Xác định danh sách ảnh PIL cần xử lý
    images_to_process: List[Image.Image] = []
    initial_warnings: List[str] = []

    if isinstance(source, bytes):
        # Kiểm tra xem có phải định dạng PDF không (magic bytes %PDF-)
        if source.startswith(b"%PDF-"):
            if not PDF_AVAILABLE:
                return OCRResult(
                    text="", 
                    ok=False, 
                    reason="Tập tin tải lên là PDF nhưng hệ thống chưa có pypdfium2.", 
                    warnings=[]
                )
            images_to_process = load_images_from_pdf(source)
            initial_warnings.append(f"Tài liệu PDF gồm {len(images_to_process)} trang.")
        else:
            img_pil, w = load_image_from_bytes(source, apply_exif=cfg.preprocess.enable_exif)
            initial_warnings.extend(w)
            images_to_process.append(img_pil)

    elif isinstance(source, str):
        if source.lower().endswith(".pdf"):
            images_to_process = load_images_from_pdf(source)
            initial_warnings.append(f"Tài liệu PDF gồm {len(images_to_process)} trang.")
        else:
            with open(source, "rb") as f:
                img_pil, w = load_image_from_bytes(f.read(), apply_exif=cfg.preprocess.enable_exif)
                initial_warnings.extend(w)
                images_to_process.append(img_pil)

    elif isinstance(source, Image.Image):
        images_to_process.append(source)

    elif isinstance(source, list):
        for item in source:
            if isinstance(item, Image.Image):
                images_to_process.append(item)
            elif isinstance(item, bytes):
                img_pil, w = load_image_from_bytes(item, apply_exif=cfg.preprocess.enable_exif)
                initial_warnings.extend(w)
                images_to_process.append(img_pil)

    if not images_to_process:
        return OCRResult(text="", ok=False, reason="Không tìm thấy ảnh hợp lệ để xử lý.", warnings=initial_warnings)

    page_texts: List[str] = []
    all_warnings: List[str] = list(initial_warnings)
    all_metrics: Dict[str, Any] = {}
    last_preview: Optional[Image.Image] = None
    overall_ok = True
    overall_reason = ""

    for idx, img in enumerate(images_to_process):
        text, ok, reason, warnings, metrics, preview = process_single_image(
            img, 
            cfg=cfg, 
            manual_rotation_deg=manual_rotation_deg
        )
        last_preview = preview
        all_metrics = metrics
        
        # Thêm tiền tố số trang nếu nhiều hơn 1 trang
        prefix = f"[Trang {idx + 1}] " if len(images_to_process) > 1 else ""
        for w in warnings:
            all_warnings.append(f"{prefix}{w}")
            
        if not ok:
            overall_ok = False
            overall_reason = f"{prefix}{reason}"
            page_texts.append("")
        else:
            page_texts.append(text)

    combined_text = "\n\n--- HẾT TRANG ---\n\n".join([p for p in page_texts if p]).strip()
    if not combined_text and overall_ok:
        combined_text = "\n\n".join(page_texts).strip()

    return OCRResult(
        text=combined_text,
        ok=overall_ok,
        reason=overall_reason,
        warnings=all_warnings,
        pages=page_texts,
        metrics=all_metrics,
        processed_preview=last_preview
    )
