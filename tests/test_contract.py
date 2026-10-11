"""Contract tests for the public OCR result and text postprocessing behavior."""

import unittest

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import OCRResult
from ocr_module.postprocess import clean_and_gate_text


class OCRContractTests(unittest.TestCase):
    def test_ocr_result_public_fields_and_defaults(self):
        result = OCRResult(text="example", ok=True)

        self.assertEqual(result.text, "example")
        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "")
        self.assertEqual(result.warnings, [])
        self.assertEqual(result.pages, [])
        self.assertEqual(result.metrics, {})
        self.assertIsNone(result.processed_preview)

    def test_low_vietnamese_diacritic_ratio_is_a_warning_not_rejection(self):
        cfg = OCRModuleConfig().gate
        text = "This English paragraph has enough letters to exercise the language-sensitive quality warning."

        cleaned, ok, reason, warnings = clean_and_gate_text(text, cfg)

        self.assertEqual(cleaned, text)
        self.assertTrue(ok)
        self.assertEqual(reason, "")
        self.assertEqual(warnings, [])

    def test_repetition_loop_is_rejected(self):
        cfg = OCRModuleConfig().gate
        text = "alpha beta gamma delta " * 20

        _, ok, reason, _ = clean_and_gate_text(text, cfg)

        self.assertFalse(ok)
        self.assertIn("lặp lại bất thường", reason)


if __name__ == "__main__":
    unittest.main()
