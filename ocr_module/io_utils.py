"""
Module tiện ích đọc/ghi dữ liệu ảnh (io_utils.py).
Hỗ trợ:
- Đọc ảnh từ đường dẫn, bytes (Streamlit UploadedFile), PIL Image, OpenCV BGR
- Tự động chuẩn hóa hướng xoay theo thông tin EXIF
- Đọc định dạng HEIC (từ iPhone) qua pillow-heif
- Đọc PDF scan thành danh sách ảnh PIL qua pypdfium2
- Chuyển đổi qua lại giữa PIL và OpenCV (BGR)
"""

import io
from typing import Union, List
import numpy as np
from PIL import Image, ImageOps

# Kiểm tra hỗ trợ HEIC
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

# Kiểm tra hỗ trợ PDF
try:
    import pypdfium2 as pdfium
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    """Chuyển PIL Image sang OpenCV BGR ndarray."""
    rgb = np.array(pil_img.convert("RGB"))
    import cv2
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv2_img: np.ndarray) -> Image.Image:
    """Chuyển OpenCV BGR ndarray sang PIL Image."""
    import cv2
    rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def apply_exif_transpose(image: Image.Image) -> tuple[Image.Image, bool]:
    """
    Sửa hướng xoay tự động theo EXIF (rất phổ biến với ảnh chụp điện thoại).
    Trả về (ảnh_sau_khi_xoay, có_bị_xoay_không).
    """
    try:
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None and transposed is not image:
            return transposed, True
        return image, False
    except Exception:
        return image, False


def load_image_from_bytes(data: bytes, apply_exif: bool = True) -> tuple[Image.Image, list[str]]:
    """
    Nạp ảnh từ mảng bytes (ví dụ từ Streamlit UploadedFile).
    Trả về (PIL.Image, danh_sách_cảnh_báo).
    """
    warnings = []
    bio = io.BytesIO(data)
    try:
        pil_img = Image.open(bio)
        pil_img.load()  # Tải toàn bộ pixel vào RAM
    except Exception as e:
        raise ValueError(f"Không thể đọc định dạng ảnh: {e}")

    if apply_exif:
        pil_img, rotated = apply_exif_transpose(pil_img)
        if rotated:
            warnings.append("Đã tự động chỉnh hướng ảnh theo thông tin EXIF.")

    return pil_img.convert("RGB"), warnings


def load_images_from_pdf(pdf_bytes_or_path: Union[bytes, str], scale: float = 2.0) -> List[Image.Image]:
    """
    Chuyển đổi từng trang của file PDF thành ảnh PIL với độ phân giải cao.
    `scale=2.0` tương đương khoảng 144 DPI (đủ rõ nét cho OCR).
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("Thư viện pypdfium2 chưa được cài đặt. Vui lòng chạy: pip install pypdfium2")

    pdf = pdfium.PdfDocument(pdf_bytes_or_path)
    images = []
    for page_idx in range(len(pdf)):
        page = pdf.get_page(page_idx)
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        images.append(pil_image.convert("RGB"))
    return images
