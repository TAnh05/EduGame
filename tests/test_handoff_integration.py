import unittest
from unittest.mock import patch

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import run_pipeline
from ocr_module.handoff import deliver_text
from test_pdf_io import make_one_page_pdf


class MockOCRIntegrationTests(unittest.TestCase):
    def test_pdf_pipeline_to_consumer_with_no_weights(self):
        cfg = OCRModuleConfig()
        cfg.preprocess.enable_quality_check = False  # blank synthetic PDF fixture
        cfg.preprocess.enable_illumination_fix = False
        received = []
        expected = "Valid English lesson material from a mocked OCR engine."
        with patch('ocr_module.pipeline.ocr_image_vintern', return_value=expected):
            result = run_pipeline(make_one_page_pdf(), cfg, pdf_max_pages=1)
        self.assertTrue(result.ok, result.reason)
        deliver_text(result=result, text=result.text, consumer=received.append, gate=cfg.gate,
                     result_context='pdf-page-1', current_context='pdf-page-1')
        self.assertEqual(received, [expected])
