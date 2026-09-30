"""
Module tiền xử lý ảnh (preprocess.py).
Thứ tự chuẩn theo thiết kế:
1. EXIF (đã xử lý ở io_utils)
2. Resize (giới hạn cạnh dài, giữ tỉ lệ, cv2.INTER_AREA, không phóng to ảnh nhỏ)
3. Đo & Kiểm tra chất lượng (quality.py)
4. Xoay góc 90°/180° (thủ công hoặc phát hiện)
5. Nắn phối cảnh (tùy chọn)
6. Chỉnh nghiêng nhỏ (deskew trong khoảng [-15°, 15°])
7. Cân bằng sáng & khử bóng đổ (LAB + Background Division + CLAHE)
8. Khử nhiễu nhẹ (chỉ khi cần)
9. Làm nét nhẹ (unsharp mask nhẹ)
"""

from typing import Tuple, List, Dict, Any, Optional
import cv2
import numpy as np

from .config import PreprocessConfig, QualityThresholds
from .quality import measure_image_quality, evaluate_quality


def resize_image(img_bgr: np.ndarray, max_dim: int = 2200) -> Tuple[np.ndarray, bool]:
    """
    Giới hạn cạnh dài của ảnh để tránh tràn VRAM / chậm suy luận.
    Không phóng to nếu ảnh nhỏ hơn max_dim.
    """
    h, w = img_bgr.shape[:2]
    long_edge = max(h, w)
    if long_edge <= max_dim:
        return img_bgr, False

    scale = max_dim / float(long_edge)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, True


def rotate_orthogonal(img_bgr: np.ndarray, angle_deg: int) -> np.ndarray:
    """Xoay các góc trực giao: 90°, 180°, 270° theo chiều kim đồng hồ."""
    angle = angle_deg % 360
    if angle == 90:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img_bgr, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img_bgr


def deskew_image(img_bgr: np.ndarray, max_angle: float = 15.0) -> Tuple[np.ndarray, float]:
    """
    Chỉnh nghiêng nhỏ (deskew) dựa trên góc định hướng của các đường viền/vùng chữ.
    Chỉ nắn khi góc lệch thuộc [-max_angle, max_angle] để tránh làm hỏng layout.
    """
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Nhị phân hóa Otsu để tìm cấu trúc dòng chữ
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Giãn nhẹ theo chiều ngang để liên kết các chữ cái thành cụm dòng
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    angles = []
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 100:
            continue
        rect = cv2.minAreaRect(cnt)
        (center_x, center_y), (rect_w, rect_h), angle = rect
        
        # Chuẩn hóa góc quay OpenCV
        if rect_w < rect_h:
            angle = angle + 90.0
        
        # OpenCV trả về góc trong [-90, 0) hoặc [0, 90)
        if angle > 45.0:
            angle -= 90.0
        elif angle < -45.0:
            angle += 90.0
            
        if -max_angle <= angle <= max_angle and abs(angle) > 0.5:
            angles.append(angle)
            
    if not angles or len(angles) < 5:
        return img_bgr, 0.0

    # Lấy trung vị góc để tránh nhiễu do hình ảnh minh họa
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return img_bgr, 0.0

    # Xoay ảnh quanh tâm, bù viền màu trắng (255, 255, 255)
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    deskewed = cv2.warpAffine(
        img_bgr, rot_mat, (w, h), 
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_CONSTANT, 
        borderValue=(255, 255, 255)
    )
    return deskewed, median_angle


def fix_illumination(img_bgr: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """
    Cân bằng sáng, khử bóng đổ không đều bằng kỹ thuật ước lượng nền (background division)
    kết hợp CLAHE trên kênh L (không gian màu LAB).
    Giữ nguyên ảnh màu / xám mượt mà, TUYỆT ĐỐI không nhị phân hóa cứng.
    """
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Kernel lẻ tỉ lệ theo kích thước ảnh
    k = max(31, (min(l.shape) // 8) | 1)
    
    # Ước lượng nền bằng Morphological Close + Gaussian Blur
    struct_elem = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    bg = cv2.morphologyEx(l, cv2.MORPH_CLOSE, struct_elem)
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=k / 3.0)
    
    # Phép chia nền: L / Background * 255
    l_div = cv2.divide(l, bg, scale=255)
    l_norm = cv2.normalize(l_div, None, 0, 255, cv2.NORM_MINMAX)
    
    # Tăng cường tương phản cục bộ bằng CLAHE
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_norm)
    
    result_lab = cv2.merge([l_enhanced, a, b])
    return cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)


def mild_denoise(img_bgr: np.ndarray) -> np.ndarray:
    """Khử nhiễu nhẹ với Non-local Means (cường độ thấp để tránh làm mất dấu tiếng Việt)."""
    return cv2.fastNlMeansDenoisingColored(img_bgr, None, h=3, hColor=3, templateWindowSize=7, searchWindowSize=21)


def mild_sharpen(img_bgr: np.ndarray) -> np.ndarray:
    """Làm nét nhẹ bằng Unsharp Masking."""
    blurred = cv2.GaussianBlur(img_bgr, (0, 0), sigmaX=2.0)
    sharpened = cv2.addWeighted(img_bgr, 1.25, blurred, -0.25, 0)
    return sharpened


def run_preprocessing_pipeline(
    img_bgr: np.ndarray,
    prep_cfg: PreprocessConfig,
    quality_cfg: QualityThresholds,
    manual_rotation_deg: int = 0
) -> Tuple[np.ndarray, bool, str, List[str], Dict[str, Any]]:
    """
    Thực thi chuỗi tiền xử lý hoàn chỉnh.
    Trả về:
    - processed_bgr: np.ndarray
    - ok: bool (có vượt qua kiểm tra chất lượng hay không)
    - reject_reason: str (lý do nếu bị từ chối)
    - warnings: list[str]
    - metrics: dict (các thông số chất lượng đo được)
    """
    warnings: List[str] = []
    
    # 1. Xoay thủ công từ giao diện nếu có
    if manual_rotation_deg % 360 != 0:
        img_bgr = rotate_orthogonal(img_bgr, manual_rotation_deg)
        warnings.append(f"Đã xoay ảnh {manual_rotation_deg}°.")

    # 2. Resize nếu vượt kích thước
    if prep_cfg.enable_resize:
        img_bgr, resized = resize_image(img_bgr, prep_cfg.max_dimension)
        if resized:
            warnings.append(f"Đã giảm kích thước ảnh về cạnh tối đa {prep_cfg.max_dimension}px để tối ưu VRAM.")

    # 3. Đo lường và kiểm tra chất lượng
    metrics = measure_image_quality(img_bgr)
    if prep_cfg.enable_quality_check:
        passed, reason, q_warnings = evaluate_quality(metrics, quality_cfg)
        warnings.extend(q_warnings)
        if not passed:
            return img_bgr, False, reason, warnings, metrics

    # 4. Chỉnh nghiêng nhỏ (Deskew)
    if prep_cfg.enable_deskew:
        img_bgr, deskew_angle = deskew_image(img_bgr, prep_cfg.max_deskew_angle)
        if abs(deskew_angle) > 0.5:
            warnings.append(f"Đã nắn độ nghiêng dòng chữ: {deskew_angle:+.1f}°.")

    # 5. Cân bằng sáng & khử bóng đổ
    if prep_cfg.enable_illumination_fix:
        img_bgr = fix_illumination(img_bgr, prep_cfg.illumination_clip_limit)

    # 6. Khử nhiễu nhẹ (nếu cấu hình bật)
    if prep_cfg.enable_denoise:
        img_bgr = mild_denoise(img_bgr)
        warnings.append("Đã áp dụng bộ lọc khử nhiễu nhẹ.")

    # 7. Làm nét nhẹ (nếu ảnh hơi mờ và được cấu hình bật)
    if prep_cfg.enable_sharpen or (metrics["blur"] < quality_cfg.blur_threshold):
        img_bgr = mild_sharpen(img_bgr)
        warnings.append("Đã tăng cường độ sắc nét cho viền chữ.")

    return img_bgr, True, "", warnings, metrics
