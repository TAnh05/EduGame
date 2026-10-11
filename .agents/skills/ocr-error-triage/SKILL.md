---
name: ocr-error-triage
description: Diagnose an incorrect, missing, duplicated, garbled, or unexpectedly rejected Image-to-Text OCR result before proposing a fix. Do not use for planned feature work without a concrete OCR failure.
---

# OCR error triage

Establish root cause before editing. Reproduce using an authorized input, its exact `OCRModuleConfig`, manual rotation, environment/model details, and the resulting `OCRResult` (`ok`, `reason`, `warnings`, `metrics`, `pages`). Never paste sensitive document content into an issue or commit.

Trace the same sample through layers: input loading (`io_utils.py`), preprocessing (`preprocess.py`), input gate (`quality.py`), Vintern/strip merge (`ocr_vintern.py`), cleanup/output gate (`postprocess.py`), then orchestration (`pipeline.py`). In debug work, preserve intermediate artifacts only in an approved non-versioned location and delete them according to retention rules.

Classify the failure, formulate one mechanism-based hypothesis, and write a minimal regression test before the fix. A successful repair must be evaluated against both its regression sample and the relevant labeled set; do not mask inference errors by weakening gates or broad text deletion.

Special cases: repeated adjacent lines can originate in `deduplicate_consecutive_lines()` or `merge_strip_texts()`; over-merged lines can originate in `normalize_whitespace_and_paragraphs()`; image rejection is decided by `evaluate_quality()`; output rejection is decided by `validate_extracted_text()`. The Vietnamese-diacritic check currently emits a warning, not rejection.

Read [error taxonomy](references/error-taxonomy.md) to classify and document the case.
