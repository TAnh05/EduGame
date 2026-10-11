# CER interpretation

`clean_text_for_cer()` in `ocr_module/eval/run_eval.py` applies Unicode NFC and collapses all whitespace. Thus CER measures character edits after those normalizations; it does not assess layout, line breaks, semantic correctness, answer-choice structure, or readability.

Compare the same truth and same sample list in every run. Examine per-image CER deltas because averages hide regressions. Preserve raw OCR output separately when diagnosing postprocessing effects. Do not change the evaluator's normalization to make a candidate look better; if a new metric is needed, add it alongside CER and document its purpose.
