import io
import unittest
import unicodedata
from unittest.mock import patch

import numpy as np
from PIL import Image

from ocr_module.config import OCRModuleConfig, QualityThresholds
from ocr_module.io_utils import load_image_from_bytes
from ocr_module.pipeline import run_pipeline
from ocr_module.preprocess import resize_image, rotate_orthogonal, run_preprocessing_pipeline
from ocr_module.quality import measure_image_quality, evaluate_quality
from ocr_module.postprocess import clean_and_gate_text, validate_extracted_text


class CoreEdgeTests(unittest.TestCase):
    def test_gate_empty_small_blurry_dark_bright_and_low_contrast(self):
        t = QualityThresholds()
        self.assertFalse(evaluate_quality(measure_image_quality(None), t)[0])
        base = dict(valid=True, w=400, h=400, blur=100, brightness=100, contrast=30)
        for change in [dict(w=10), dict(blur=0)]:
            self.assertFalse(evaluate_quality(base | change, t)[0])
        for change in [dict(blur=40), dict(brightness=10), dict(brightness=250), dict(contrast=1)]:
            ok, _, warnings = evaluate_quality(base | change, t)
            self.assertTrue(ok)
            self.assertTrue(warnings)

    def test_blank_and_short_text_stop_before_consumer(self):
        cfg = OCRModuleConfig()
        self.assertFalse(clean_and_gate_text('  ', cfg.gate)[1])
        self.assertFalse(validate_extracted_text('💥' * 40, cfg.gate)[0])
        for language in ['Tiếng Việt có dấu và nội dung học tập rõ ràng.', 'An English paragraph for language neutrality.']:
            self.assertTrue(clean_and_gate_text(language, cfg.gate)[1])
        mixed = 'This is a very long English paragraph with exactly one accented letter é and more ordinary letters.'
        ok, _, warnings = validate_extracted_text(mixed, cfg.gate)
        self.assertTrue(ok)
        self.assertTrue(warnings)

    def test_unicode_and_markdown_cleanup(self):
        cfg = OCRModuleConfig()
        text = unicodedata.normalize('NFD', '### **Tiếng Việt**\n\n- Mục thứ nhất.\n- Mục thứ hai.<s>')
        cleaned, ok, _, _ = clean_and_gate_text(text, cfg.gate)
        self.assertTrue(ok)
        self.assertEqual(cleaned, 'Tiếng Việt\n\n- Mục thứ nhất.\n- Mục thứ hai.')

    def test_exif_actual_rotation_and_pixel_guard(self):
        image = Image.new('RGB', (400, 300))
        exif = Image.Exif()
        exif[274] = 6
        buf = io.BytesIO()
        image.save(buf, format='JPEG', exif=exif)
        rotated, warnings = load_image_from_bytes(buf.getvalue())
        self.assertEqual(rotated.size, (300, 400))
        self.assertEqual(len(warnings), 1)
        with self.assertRaises(ValueError):
            load_image_from_bytes(buf.getvalue(), max_pixels=1)

    def test_resize_rotation_and_transform_flags(self):
        image = np.arange(600 * 400 * 3, dtype=np.uint8).reshape(600, 400, 3)
        resized, changed = resize_image(image, 300)
        self.assertTrue(changed)
        self.assertEqual(resized.shape[:2], (300, 200))
        self.assertEqual(rotate_orthogonal(image, 90).shape[:2], (400, 600))
        self.assertTrue(np.array_equal(rotate_orthogonal(image, 180), image[::-1, ::-1]))
        self.assertEqual(rotate_orthogonal(image, 270).shape[:2], (400, 600))
        cfg = OCRModuleConfig()
        cfg.preprocess.enable_quality_check = False
        cfg.preprocess.enable_deskew = False
        cfg.preprocess.enable_sharpen = True
        cfg.preprocess.enable_denoise = True
        _, ok, _, warnings, _ = run_preprocessing_pipeline(image, cfg.preprocess, cfg.quality, 90)
        self.assertTrue(ok)
        self.assertEqual(len(warnings), 3)

    def test_input_gate_and_inference_error_contract(self):
        with patch('ocr_module.pipeline.ocr_image_vintern') as infer:
            self.assertFalse(run_pipeline(Image.new('RGB', (400, 400), 'white')).ok)
            infer.assert_not_called()
        cfg = OCRModuleConfig()
        cfg.preprocess.enable_quality_check = False
        cfg.preprocess.enable_illumination_fix = False
        with patch('ocr_module.pipeline.ocr_image_vintern', side_effect=RuntimeError('engine failed')):
            result = run_pipeline(Image.new('RGB', (400, 400)), cfg)
        self.assertFalse(result.ok)
        self.assertIn('engine failed', result.reason)
        self.assertFalse(run_pipeline([]).ok)
        self.assertFalse(run_pipeline('/missing/file.png').ok)
        self.assertFalse(run_pipeline(b'bad', manual_rotation_deg=12).ok)
