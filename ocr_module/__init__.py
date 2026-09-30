"""
OCR Module cho Hệ thống Web Ôn tập bằng Game.
Pipeline: Tiền xử lý ảnh -> Vintern-1B v3.5 -> Hậu xử lý & Cổng chất lượng -> UI / Data Output.
"""

from .pipeline import run_pipeline, OCRResult

__all__ = ["run_pipeline", "OCRResult"]
