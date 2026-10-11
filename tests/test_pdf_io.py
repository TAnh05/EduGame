"""Integration tests for PDF rendering without external or private fixtures."""

import tempfile
import unittest
from pathlib import Path

from ocr_module.io_utils import load_images_from_pdf


def make_one_page_pdf() -> bytes:
    """Build a standards-compliant blank one-page PDF for the PDFium integration test."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


class PdfIoTests(unittest.TestCase):
    def test_render_page_and_validate_page_range(self):
        temporary_root = Path(__file__).parent / ".tmp"
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as temp_dir:
            pdf_path = Path(temp_dir) / "one-page.pdf"
            pdf_path.write_bytes(make_one_page_pdf())

            pages = load_images_from_pdf(str(pdf_path), scale=1.0, max_pages=1)

            self.assertEqual(len(pages), 1)
            self.assertGreater(pages[0].width, 0)
            self.assertGreater(pages[0].height, 0)
            with self.assertRaises(ValueError):
                load_images_from_pdf(str(pdf_path), start_page=1, max_pages=1)


if __name__ == "__main__":
    unittest.main()
