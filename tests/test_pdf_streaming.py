import unittest
from unittest.mock import MagicMock, Mock, patch

from PIL import Image

from ocr_module.config import OCRModuleConfig
from ocr_module.io_utils import iter_images_from_pdf
from ocr_module.pipeline import run_pipeline


class PdfStreamingTests(unittest.TestCase):
    def document(self, count=3, size=(200, 200)):
        doc = MagicMock()
        doc.__len__.return_value = count
        pages = []
        for _ in range(count):
            page = Mock()
            page.get_size.return_value = size
            page.render.return_value.to_pil.return_value = Image.new('RGB', (400, 400))
            pages.append(page)
        doc.get_page.side_effect = lambda index: pages[index]
        return doc, pages

    def test_renders_only_as_consumed_and_closes_handles_on_early_exit(self):
        doc, pages = self.document()
        with patch('ocr_module.io_utils.pdfium.PdfDocument', return_value=doc):
            iterator = iter_images_from_pdf(b'%PDF-test')
            first = next(iterator)
            pages[0].render.assert_called_once()
            pages[1].render.assert_not_called()
            pages[0].close.assert_called_once()
            pages[0].render.return_value.close.assert_called_once()
            iterator.close()
            doc.close.assert_called_once()
            self.assertEqual(first.size, (400, 400))
            first.close()

    def test_limits_checked_before_render(self):
        for count, size, options in [(51, (200, 200), {}), (1, (100_000, 100_000), {})]:
            doc, pages = self.document(count, size)
            with patch('ocr_module.io_utils.pdfium.PdfDocument', return_value=doc):
                with self.assertRaises(ValueError):
                    list(iter_images_from_pdf(b'%PDF-test', **options))
            for page in pages:
                page.render.assert_not_called()
            doc.close.assert_called_once()

    def test_inference_interleaves_with_render_and_uses_real_page_numbers(self):
        doc, pages = self.document()
        rendered = []
        def process(image, cfg, rotation):
            rendered.append(sum(p.render.call_count for p in pages))
            return 'valid page text', True, '', ['page warning'], {'blur': 123}, Image.new('RGB', (10, 10))
        with patch('ocr_module.io_utils.pdfium.PdfDocument', return_value=doc), patch('ocr_module.pipeline.process_single_image', side_effect=process):
            result = run_pipeline(b'%PDF-test', pdf_start_page=1, pdf_max_pages=2)
        self.assertTrue(result.ok)
        self.assertEqual(rendered, [1, 2])
        self.assertEqual([p['page'] for p in result.metrics['per_page']], [2, 3])
        self.assertIn('[Trang 2]', result.warnings[1])
        pages[0].render.assert_not_called()
        doc.close.assert_called_once()

    def test_bytes_pixel_file_and_page_limits_return_failed_contract(self):
        cfg = OCRModuleConfig()
        cfg.limits.max_file_bytes = 1
        self.assertFalse(run_pipeline(b'too long', cfg).ok)
        cfg.limits.max_page_pixels = 10
        self.assertFalse(run_pipeline(Image.new('RGB', (20, 20)), cfg).ok)
        cfg.limits.max_pages = 1
        self.assertFalse(run_pipeline([Image.new('RGB', (2, 2))] * 2, cfg).ok)
        self.assertFalse(run_pipeline(b'%PDF-corrupt').ok)

    def test_render_failure_closes_page_bitmap_and_document(self):
        doc, pages = self.document(1)
        pages[0].render.return_value.to_pil.side_effect = RuntimeError('failed conversion')
        with patch('ocr_module.io_utils.pdfium.PdfDocument', return_value=doc):
            result = run_pipeline(b'%PDF-test')
        self.assertFalse(result.ok)
        self.assertIn('failed conversion', result.reason)
        pages[0].render.return_value.close.assert_called_once()
        pages[0].close.assert_called_once()
        doc.close.assert_called_once()
