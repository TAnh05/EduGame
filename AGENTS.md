# Image-to-Text: working rules

## Project map

- `ocr_module/pipeline.py`: public orchestration API: `run_pipeline()` and `OCRResult`.
- `ocr_module/config.py`: all tunable thresholds, ablation flags, and Vintern generation settings.
- `ocr_module/preprocess.py`, `quality.py`: image transformation and input quality gate.
- `ocr_module/ocr_vintern.py`: Vintern loading, strip splitting, and CUDA OOM fallback.
- `ocr_module/postprocess.py`: text cleanup and output quality gate.
- `ocr_module/eval/run_eval.py`: existing CER and A–E preprocessing ablation runner.

## Commands

- Environment smoke test: `python test_stage0_env.py`
- One OCR run: `python run_single_test.py [image-path]`
- Existing evaluation/ablation: `python -m ocr_module.eval.run_eval`
- UI: `streamlit run app.py`

## Non-negotiable engineering rules

1. Preserve `OCRResult` as the integration contract. Before changing its fields, defaults, or semantics, identify every caller and add/update a contract test; obtain approval if a downstream consumer must change.
2. Do not introduce hard binarization into the image sent to Vintern. Otsu may be used only for analysis (as `deskew_image` and strip splitting currently do), never as the OCR image output.
3. Every new preprocessing transform must be independently switchable in `PreprocessConfig`, unit-tested, and compared against its disabled version using the existing evaluation runner before becoming a default.
4. Treat synthetic samples as smoke tests, not performance evidence. Do not claim an accuracy gain or retune defaults from the current three generated samples. Record provenance and consent/privacy constraints for real evaluation documents.
5. Keep model loading reproducible: pin an immutable Vintern revision before production use. Do not silently change `model_name_or_path`, prompt, generation parameters, dtype, or tile count without paired evaluation.
6. On CUDA, retain float16 unless hardware support and measured results justify another dtype. Preserve and test the OOM fallback in `ocr_image_vintern` whenever inference changes.
7. Diagnose at the correct layer—input, preprocessing, inference, postprocessing, or gate—before editing code. A repaired defect becomes a labeled regression case when permission to retain the document exists.
8. Do not add runtime dependencies, download external corpora, alter licenses, or change document-retention behavior without user approval.

## Gate semantics

- A rejection prevents OCR and must be supported by labeled evidence.
- A warning informs the user but must not be presented as a rejection.
- Language-sensitive signals (including Vietnamese-diacritic ratio) remain warnings until language detection and calibration demonstrate a safe rejection rule for Vietnamese, English, and mixed text.
