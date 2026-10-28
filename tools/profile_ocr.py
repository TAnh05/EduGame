"""Explicit, immutable-revision OCR measurement; prints metadata, never document text."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def measure(source, cfg, truth=None):
    import torch
    from ocr_module.pipeline import run_pipeline
    from ocr_module.eval.run_eval import calculate_cer
    cuda = cfg.model.device == 'cuda' and torch.cuda.is_available()
    if cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    before, cpu = time.perf_counter(), time.process_time()
    result = run_pipeline(source, cfg)
    if cuda:
        torch.cuda.synchronize()
    record = dict(ok=result.ok, reason=result.reason, page_count=len(result.pages), char_count=len(result.text),
                  elapsed_seconds=time.perf_counter()-before, cpu_seconds=time.process_time()-cpu,
                  cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated() if cuda else None,
                  cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved() if cuda else None,
                  cuda_available=cuda, torch=str(torch.__version__), config=asdict(cfg),
                  python=platform.python_version(), platform=platform.platform())
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record['process_peak_rss_bytes'] = peak if sys.platform == 'darwin' else peak * 1024
    except ImportError:
        record['process_peak_rss_bytes'] = None
    # Rejection is reported separately; do not score a rejected result as an accurate OCR.
    record['cer'] = calculate_cer(result.text, truth) if truth is not None and result.ok else None
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('--revision', required=True, help='Approved immutable 40-character model SHA')
    parser.add_argument('--truth', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-fA-F]{40}', args.revision):
        parser.error('--revision must be an immutable 40-character SHA')
    from ocr_module.config import OCRModuleConfig
    cfg = OCRModuleConfig()
    cfg.model.revision = args.revision
    truth = args.truth.read_text(encoding='utf-8') if args.truth else None
    report = measure(args.source, cfg, truth)
    print(json.dumps(report, ensure_ascii=False, default=str))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
