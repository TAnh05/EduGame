import importlib.util
import unittest
from unittest.mock import patch

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import OCRResult


@unittest.skipUnless(importlib.util.find_spec('torch'), 'CPU inference CI job')
class ProfileTests(unittest.TestCase):
    def test_profile_reports_metrics_without_document_text(self):
        from tools.profile_ocr import measure
        cfg = OCRModuleConfig()
        cfg.model.device = 'cpu'
        with patch('ocr_module.pipeline.run_pipeline', return_value=OCRResult(text='private lesson', ok=True, pages=['private lesson'])):
            result = measure(b'fixture', cfg, truth='private lesson')
        self.assertEqual(result['cer'], 0)
        self.assertEqual(result['page_count'], 1)
        self.assertFalse(result['cuda_available'])
        self.assertIsNone(result['cuda_peak_allocated_bytes'])
        self.assertNotIn('private lesson', str(result))

    def test_rejection_is_not_scored_as_successful_cer(self):
        from tools.profile_ocr import measure
        cfg = OCRModuleConfig()
        cfg.model.device = 'cpu'
        with patch('ocr_module.pipeline.run_pipeline', return_value=OCRResult(text='', ok=False, reason='failed')):
            result = measure(b'fixture', cfg, truth='ground truth')
        self.assertFalse(result['ok'])
        self.assertIsNone(result['cer'])
