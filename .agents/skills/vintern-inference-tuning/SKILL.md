---
name: vintern-inference-tuning
description: Tune or diagnose Vintern loading, generation, tiling, strip splitting, CUDA memory, or OOM fallback in Image-to-Text. Do not use for image preprocessing experiments, output text cleanup, or quality-threshold calibration.
---

# Vintern inference tuning

Use `ocr_module/ocr_vintern.py` with `ModelConfig` and `StripSplittingConfig` from `ocr_module/config.py`. First reproduce the issue and capture device, dtype, model revision, image dimensions, strip count, `max_num`, prompt, generation settings, latency, and peak allocated/reserved CUDA memory when CUDA is present.

## Constraints

- Pin an immutable Hugging Face `revision` before treating a model change as reproducible. The current `ModelConfig` has no revision field: add one only with caller review and a compatible loader change.
- Preserve float16 on current CUDA paths unless measured hardware support and evaluation justify a change. CPU remains float32.
- Treat `max_num`, `max_new_tokens`, `num_beams`, `repetition_penalty`, prompt, `input_size`, and split settings as experimental variables—not guesses. Compare with `$ocr-eval-ablation`.
- Keep `torch.inference_mode()`, cached model/tokenizer behavior, and the CUDA OOM retry that halves `max_num`. Verify both normal and fallback paths after relevant changes, and ensure fallback activation is observable in logs.
- `split_image_into_strips()` delegates to `find_horizontal_split_points()` and joins with `merge_strip_texts()`. Test dense multi-strip pages, including overlap boundaries, for lost or duplicated lines.

Do not claim VRAM or quality improvements without measurements. Read [generation parameters](references/generation-params.md) for the exact current knobs and [memory notes](references/vram-notes.md) for a reproducible diagnostic checklist.
