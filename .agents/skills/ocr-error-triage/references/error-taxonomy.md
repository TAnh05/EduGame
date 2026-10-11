# Error taxonomy

- `input-decode-or-orientation`: unsupported/corrupt input, EXIF or manual rotation.
- `input-gate-false-reject` / `input-gate-missed-reject`: blur, size, brightness, or contrast rule.
- `transform-artifact`: lost diacritic, crop, resampling/deskew/illumination/denoise damage.
- `inference-substitution` / `inference-omission`: wrong or missing content before cleanup.
- `strip-boundary-duplicate` / `strip-boundary-omission`: overlap merge behavior.
- `postprocess-deletion` / `postprocess-overmerge`: cleanup altered valid structure.
- `output-gate-false-reject` / `output-gate-missed-reject`: length, valid-character, repetition, or language-sensitive check.
- `performance-or-oom`: load, memory, fallback, or latency.

Record the primary category, evidence layer, hypothesis, fix, regression sample ID, and any remaining uncertainty.
