"""Linux render-only comparison. Synthetic blank PDF; no OCR/quality claims."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import resource
import time

import pypdfium2 as pdfium


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['eager', 'stream'], required=True)
    parser.add_argument('--pages', type=int, default=10)
    parser.add_argument('--io-module', type=Path, default=Path(__file__).resolve().parents[1] / 'ocr_module/io_utils.py')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('benchmark_io', args.io_module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    document = pdfium.PdfDocument.new()
    for _ in range(args.pages):
        page = document.new_page(600, 800)
        page.close()
    data = io.BytesIO()
    document.save(data)
    document.close()
    digest = hashlib.sha256()
    before, cpu = time.perf_counter(), time.process_time()
    if args.mode == 'eager':
        images = module.load_images_from_pdf(data.getvalue())
    else:
        images = module.iter_images_from_pdf(data.getvalue())
    count = 0
    for image in images:
        digest.update(image.tobytes())
        count += 1
        image.close()
    print(json.dumps(dict(mode=args.mode, pages=count, raster='1200x1600 RGB',
        elapsed_seconds=time.perf_counter()-before, cpu_seconds=time.process_time()-cpu,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        digest=digest.hexdigest(), python=platform.python_version(), platform=platform.system(),
        scope='render-only synthetic PDF; no inference')))


if __name__ == '__main__':
    main()
