---
name: ocr-quality-gates
description: Calibrate, change, or investigate Image-to-Text input or output quality-gate thresholds and rejection behavior. Do not use for ordinary OCR tuning, preprocessing changes, or UI presentation of an unchanged gate.
---

# OCR quality gates

Input thresholds live in `QualityThresholds` and are applied by `evaluate_quality()` in `ocr_module/quality.py`. Output thresholds live in `QualityGateConfig` and are applied by `validate_extracted_text()` after cleanup in `ocr_module/postprocess.py`.

## Calibration protocol

Define the gate’s decision: reject, warn, or pass. Assemble authorized, labeled examples spanning accepted and unacceptable images/text, with language labels for Vietnamese, English, and mixed content. Measure confusion counts: true/false accept and true/false reject, plus rejection rate by language and document class. Keep baseline and candidate thresholds in the same report.

Never hand-tune a production threshold from a few samples. Never turn a warning into rejection without evidence and user-impact review. A warning must not be represented in the UI as a hard failure.

Current behavior matters: tiny images and extremely blurred images reject; low brightness, high brightness, and low contrast warn. Text length, valid-character ratio, and high 4-gram repetition reject. The Vietnamese-diacritic ratio warns only when nonzero and below its threshold; it must stay language-sensitive and must not reject English or mixed documents without a validated detector.

Keep measurement and policy separate: add metrics first, then calibrate a threshold. Pair gate changes with `$ocr-eval-ablation` so OCR accuracy, false rejection, and latency are visible together. Preserve a regression case for every fixed false decision.

Read [calibration notes](references/calibration-notes.md) before proposing a new threshold.
