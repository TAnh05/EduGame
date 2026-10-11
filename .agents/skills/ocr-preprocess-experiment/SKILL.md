---
name: ocr-preprocess-experiment
description: Safely add, modify, or tune Image-to-Text image preprocessing such as resize, deskew, illumination, denoise, sharpen, or perspective correction. Do not use for model-generation tuning, text cleanup, or UI styling.
---

# OCR preprocessing experiments

Work in `ocr_module/preprocess.py` and expose behavior through `PreprocessConfig` in `ocr_module/config.py`. Preserve the current order in `run_preprocessing_pipeline`: manual rotation, resize, input measurement/gate, deskew, illumination, optional denoise, optional sharpen.

## Change discipline

- Start with a reproducible failure and determine whether it is an image transformation problem rather than inference, postprocessing, or a gate issue.
- Implement one pure image function with a narrowly named `enable_*` flag and defaults that preserve current behavior. Do not create hidden automatic transformations.
- Keep the OCR-bound image color/grayscale-natural. Do not hard-binarize it. Analysis-only masks are allowed when they never replace the image passed to Vintern.
- Add focused tests for no-op/shape/dtype behavior and the observed failure. Inspect Vietnamese diacritics, small Latin characters, tables, and line boundaries visually when the transform resamples or denoises.
- Compare off versus on with `$ocr-eval-ablation`; do not enable a new default without authorized, diverse real-data evidence.

Existing specifics: `resize_image()` never enlarges an image; `deskew_image()` restricts corrections to `max_deskew_angle`; `fix_illumination()` uses LAB/background division/CLAHE; `mild_denoise()` and `mild_sharpen()` are intentionally off by default. `enable_perspective_warp` exists in config but no implemented pipeline stage currently consumes it—do not imply otherwise.

Read [experiment template](references/step-template.md) when designing a new step.
