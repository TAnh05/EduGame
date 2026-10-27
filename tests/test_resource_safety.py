import unittest
from unittest.mock import Mock, patch

from PIL import Image

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import run_pipeline
from ocr_module.io_utils import load_image_from_bytes


class ResourceSafetyTests(unittest.TestCase):
    def test_bad_list_member_returns_failure_instead_of_raising(self):
        result = run_pipeline([b'corrupt'])
        self.assertFalse(result.ok)
        self.assertTrue(result.reason)

    def test_invalid_list_member_is_not_silently_ignored(self):
        result = run_pipeline([object()])
        self.assertFalse(result.ok)
        self.assertIn('không hỗ trợ', result.reason)

    def test_keeps_all_page_failures_and_metrics(self):
        images = [Image.new('RGB', (400, 400)) for _ in range(3)]
        outcomes = [("", False, "bad one", ["w1"], {"blur": 1}, images[0]),
                    ("", False, "bad two", ["w2"], {"blur": 2}, images[1]),
                    ("good page text", True, "", [], {"blur": 3}, images[2])]
        with patch('ocr_module.pipeline.process_single_image', side_effect=outcomes):
            result = run_pipeline(images)
        self.assertFalse(result.ok)
        self.assertIn('bad one', result.reason)
        self.assertIn('bad two', result.reason)
        self.assertEqual(result.pages, ["", "", "good page text"])
        self.assertEqual(result.metrics['blur'], 3)  # existing top-level contract
        self.assertEqual([m['metrics']['blur'] for m in result.metrics['per_page']], [1, 2, 3])

    def test_exif_warning_only_when_orientation_changes(self):
        import io
        stream = io.BytesIO()
        Image.new('RGB', (400, 300)).save(stream, format='PNG')
        _, warnings = load_image_from_bytes(stream.getvalue())
        self.assertEqual(warnings, [])

    def test_unsupported_perspective_flag_fails_explicitly(self):
        cfg = OCRModuleConfig()
        cfg.preprocess.enable_perspective_warp = True
        result = run_pipeline(Image.new('RGB', (400, 400)), cfg)
        self.assertFalse(result.ok)
        self.assertIn('perspective', result.reason)
