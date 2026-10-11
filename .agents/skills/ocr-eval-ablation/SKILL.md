---
name: ocr-eval-ablation
description: Evaluate Image-to-Text OCR changes with CER and paired ablations, or add labeled evaluation data. Use for accuracy, latency, preprocessing, prompt, or inference comparisons; do not use for UI-only edits or a single anecdotal OCR result.
---

# OCR evaluation and ablation

Use the repository evaluator in `ocr_module/eval/run_eval.py`; do not reimplement CER. Its `calculate_cer()` normalizes to NFC and collapses whitespace, and `get_ablation_configs()` defines the current A–E preprocessing variants.

## Before measuring

1. State the hypothesis, the exact configuration delta, and the decision that the result will support. Change one causal factor per comparison.
2. Inspect the matched image/truth pairs under `ocr_module/eval/images/` and `truth/`. The bundled three samples are synthetic smoke tests only; label results accordingly.
3. For real data, retain only authorized documents. Track source type, language (Vietnamese, English, mixed), capture/device condition, document class, and error tags without putting sensitive text in reports.

## Run and report

Run `python -m ocr_module.eval.run_eval` for the established A–E study. For another configuration, call `evaluate_dataset(images_dir, truth_dir, cfg)` and retain its `details` rather than reporting only its mean.

For every pair of configurations, report: sample count, mean CER, rejection rate, mean latency, CER delta per image, number improved/tied/regressed, and the worst regressions with error category. A rejection is currently scored as CER `1.0`; report it separately so a lower average cannot conceal unsafe gate behavior.

Do not declare a winner from three synthetic examples, a lone mean, or a difference plausibly explained by run variance. Keep defaults unchanged when evidence is insufficient. Put approved experiment reports in `docs/experiments/` with data scope, commands/configuration, commit, and limitations.

Read [dataset rules](references/dataset-rules.md) before adding data and [CER interpretation](references/cer-normalization.md) before changing evaluation or interpreting CER.
