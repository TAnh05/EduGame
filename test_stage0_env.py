"""Exit nonzero on missing dependencies or broken core logic; never load weights."""
import argparse
import importlib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", action="store_true", help="CPU IO/UI tests without ML dependencies")
    args = parser.parse_args()
    modules = ["cv2", "PIL", "numpy", "streamlit", "rapidfuzz", "pypdfium2", "pillow_heif"]
    if not args.core:
        modules += ["torch", "torchvision", "transformers", "timm", "accelerate", "einops"]
    failures = []
    print(f"Python {sys.version.split()[0]} | {'core' if args.core else 'inference'} environment")
    for name in modules:
        try:
            module = importlib.import_module(name)
            print(f"OK {name}: {getattr(module, '__version__', 'available')}")
        except Exception as exc:
            failures.append(name)
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    if failures:
        return 1
    try:
        import numpy as np
        import cv2
        from ocr_module.config import OCRModuleConfig
        from ocr_module.preprocess import run_preprocessing_pipeline
        from ocr_module.postprocess import clean_and_gate_text
        cfg = OCRModuleConfig()
        image = np.full((600, 800, 3), 245, dtype=np.uint8)
        cv2.putText(image, "OCR smoke test", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (20, 20, 20), 2)
        _, ok, reason, _, _ = run_preprocessing_pipeline(image, cfg.preprocess, cfg.quality)
        assert ok, reason
        _, ok, reason, _ = clean_and_gate_text("A valid English OCR paragraph for the smoke test.", cfg.gate)
        assert ok, reason
        if not args.core:
            import torch
            print(f"CUDA available: {torch.cuda.is_available()} (no model inference performed)")
        print("Core logic OK; model inference NOT tested")
    except Exception as exc:
        print(f"FAIL core logic: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
