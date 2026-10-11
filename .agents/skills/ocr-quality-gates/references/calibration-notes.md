# Gate calibration notes

For input gates, retain `blur`, `brightness`, `contrast`, `w`, and `h` from `measure_image_quality()`. For output gates, retain cleaned length, valid-character ratio, 4-gram repetition rate, and language label. Do not label OCR quality solely by these proxies; pair them with review of whether the output was usable for its intended educational workflow.

Report threshold, dataset slice, counts of false accepts/rejects, and examples by category. Choose the policy according to harm: a conservative reject prevents wasted inference but may block usable notes; a warning preserves access but may pass poor text. Escalate that product trade-off to the user rather than silently choosing it.
