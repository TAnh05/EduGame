"""Regression tests for public pipeline failure handling and preprocessing flags."""

import unittest
from unittest.mock import patch

import numpy as np

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import run_pipeline
from ocr_module.preprocess import run_preprocessing_pipeline


class PipelineSafetyTests(unittest.TestCase):
    def test_invalid_image_bytes_return_failed_result(self):
        result = run_pipeline(b"not an image")

        self.assertFalse(result.ok)
        self.assertIn("Không thể đọc ảnh", result.reason)

    def test_disabled_sharpen_never_runs_implicitly_for_blurry_image(self):
        cfg = OCRModuleConfig()
        cfg.preprocess.enable_quality_check = False
        cfg.preprocess.enable_deskew = False
        cfg.preprocess.enable_illumination_fix = False
        cfg.preprocess.enable_denoise = False
        cfg.preprocess.enable_sharpen = False
        blurry = np.full((400, 400, 3), 128, dtype=np.uint8)

        with patch("ocr_module.preprocess.mild_sharpen") as sharpen:
            _, ok, _, warnings, _ = run_preprocessing_pipeline(
                blurry,
                prep_cfg=cfg.preprocess,
                quality_cfg=cfg.quality,
            )

        self.assertTrue(ok)
        sharpen.assert_not_called()
        self.assertNotIn("Đã tăng cường độ sắc nét cho viền chữ.", warnings)


if __name__ == "__main__":
    unittest.main()
