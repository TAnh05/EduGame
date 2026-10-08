"""Đọc PDF / Word / ảnh -> văn bản sạch, kiểm tra đạt/không đạt. (Phụ trách: Toàn)"""

MIN_TEXT_LENGTH = 200  # văn bản ngắn hơn mức này coi là không đạt


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Trả về văn bản sạch hoặc raise ValueError kèm thông báo lỗi tiếng Việt."""
    # TODO: PDF -> PyMuPDF (fitz); .docx -> python-docx; ảnh/PDF scan -> OCR.
    raise NotImplementedError
