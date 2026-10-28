import tempfile
from pathlib import Path
import unittest
import unicodedata
from unittest.mock import patch

from ocr_module.config import OCRModuleConfig
from ocr_module.pipeline import OCRResult
from ocr_module.eval.run_eval import calculate_cer, evaluate_dataset, run_ablation_study


class EvaluationTests(unittest.TestCase):
    def test_empty_or_incomplete_dataset_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            cfg = OCRModuleConfig()
            self.assertIn('error', evaluate_dataset(folder, folder, cfg))
            (path / 'missing.png').write_bytes(b'fixture')
            (path / 'valid.png').write_bytes(b'fixture')
            (path / 'valid.txt').write_text('valid text', encoding='utf-8')
            with patch('ocr_module.eval.run_eval.run_pipeline', return_value=OCRResult(text='valid text', ok=True)) as run:
                self.assertIn('error', evaluate_dataset(folder, folder, cfg))
                run.assert_not_called()

    def test_details_include_rejection_without_raw_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'a.png').write_bytes(b'fixture')
            (path / 'a.txt').write_text('valid text', encoding='utf-8')
            with patch('ocr_module.eval.run_eval.run_pipeline', return_value=OCRResult(text='', ok=False, reason='failed')):
                data = evaluate_dataset(folder, folder, OCRModuleConfig())
            self.assertEqual(data['cer_avg'], 1)
            self.assertEqual(data['rejection_rate'], 1)
            self.assertEqual(data['details'][0]['reason'], 'failed')
            self.assertNotIn('text', data['details'][0])

    def test_normalization_does_not_count_canonical_unicode_or_whitespace(self):
        self.assertEqual(calculate_cer(unicodedata.normalize('NFD', 'Tiếng Việt\n rõ'), 'Tiếng Việt rõ'), 0)
        self.assertEqual(calculate_cer('cat', 'cut'), 1/3)
        self.assertEqual(calculate_cer('', ''), 0)
        self.assertEqual(calculate_cer('x', ''), 1)

    def test_ablation_retains_details_for_every_unchanged_variant(self):
        data = dict(total_samples=1, cer_avg=0, avg_time_sec=0.1, rejection_rate=0,
                    details=[dict(image='fixture.png', cer=0, ok=True, time_sec=0.1)])
        with patch('ocr_module.eval.run_eval.evaluate_dataset', return_value=data):
            report = run_ablation_study('images', 'truth', revision='a' * 40)
        self.assertEqual(len(report), 5)
        for result in report.values():
            self.assertEqual(result['details'], data['details'])
            self.assertEqual(result['config']['model']['revision'], 'a' * 40)
        with patch('ocr_module.eval.run_eval.evaluate_dataset', return_value={'error':'missing data'}):
            self.assertEqual(run_ablation_study('images', 'truth'), {'error':'missing data'})
