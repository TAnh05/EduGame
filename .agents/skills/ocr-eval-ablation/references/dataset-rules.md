# Evaluation data rules

Each image needs a same-stem UTF-8 ground-truth `.txt` file. `run_eval.py` currently accepts `.png`, `.jpg`, `.jpeg`, and `.webp`; PDF and HEIC must be rendered/converted deliberately before inclusion.

Keep a separate manifest outside or beside sensitive data with: sample ID, authorization/retention status, source type, language, device/capture conditions, document class, and one or more error tags. Avoid committing private educational records or identifiers. Include difficult real cases only when retention is authorized: skew, shadow, blur, dense pages/strip splitting, Vietnamese, English, and mixed language.

Use synthetic samples only to verify that the harness and a code path run. They are not a calibration set and should not drive threshold or default changes.
