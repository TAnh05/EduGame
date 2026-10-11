# Current generation and image knobs

`ModelConfig` currently uses `input_size=448`, `min_num=1`, `max_num=2`, `max_new_tokens=1024`, `do_sample=False`, `num_beams=1`, and `repetition_penalty=1.2`. `ocr_image_vintern()` passes the latter four generation values to `model.chat()`.

`StripSplittingConfig` defaults to enabled, `split_height_threshold=2400`, `strip_target_lines=15`, and `overlap_margin_px=60`. Note that `strip_target_lines` is configured but not read by the current splitting implementation; verify code before relying on it.
