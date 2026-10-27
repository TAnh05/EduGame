"""Streamlit OCR UI. Embedders inject a consumer accepting a plain string."""
import hashlib
import os
import sys
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from ocr_module.config import OCRModuleConfig
from ocr_module.handoff import TextConsumer, deliver_text
from ocr_module.io_utils import (
    PDF_AVAILABLE, HEIF_AVAILABLE, load_image_from_bytes, pil_to_cv2, cv2_to_pil,
)
from ocr_module.pipeline import OCRResult, run_pipeline
from ocr_module.preprocess import run_preprocessing_pipeline


def get_file_md5(data: bytes) -> str:
    """Content identity only; this digest is not used for security."""
    return hashlib.md5(data).hexdigest()


def invalidate_result(state: dict) -> None:
    state.update(result=None, user_text="", result_context="")
    state["generation"] = state.get("generation", 0) + 1
    state.pop("processing_time", None)
    st.session_state.pop("game_raw_text", None)


def preview_processed_image(file_bytes, rotation_deg, cfg):
    original, _ = load_image_from_bytes(file_bytes, apply_exif=cfg.preprocess.enable_exif)
    processed, ok, reason, warnings, metrics = run_preprocessing_pipeline(
        pil_to_cv2(original), cfg.preprocess, cfg.quality, rotation_deg,
    )
    return original, cv2_to_pil(processed), warnings, metrics, ok, reason


def render_sidebar_configs() -> OCRModuleConfig:
    cfg = OCRModuleConfig()
    st.sidebar.header("Cấu hình OCR")
    with st.sidebar.expander("Tiền xử lý ảnh"):
        for flag, label in [
            ("exif", "Sửa hướng EXIF"), ("resize", "Giới hạn kích thước"),
            ("deskew", "Chỉnh nghiêng"), ("illumination_fix", "Cân bằng sáng"),
            ("sharpen", "Làm nét nhẹ"), ("denoise", "Khử nhiễu nhẹ"),
        ]:
            name = "enable_" + flag
            setattr(cfg.preprocess, name, st.checkbox(label, value=getattr(cfg.preprocess, name)))
        cfg.preprocess.max_dimension = st.slider("Cạnh tối đa (px)", 1200, 3000, cfg.preprocess.max_dimension, step=100)
    with st.sidebar.expander("Vintern"):
        cfg.model.max_num = st.slider("Số ô ảnh tối đa", 1, 8, cfg.model.max_num)
        cfg.model.num_beams = st.selectbox("Số beam", [1, 3])
        cfg.model.repetition_penalty = st.slider("Phạt lặp từ", 1.0, 2.5, cfg.model.repetition_penalty, step=0.1)
        cfg.model.max_new_tokens = st.slider("Token tối đa", 256, 2048, cfg.model.max_new_tokens, step=128)
    with st.sidebar.expander("Ngưỡng chất lượng"):
        cfg.quality.blur_threshold = st.number_input("Ngưỡng mờ", min_value=0.0, value=cfg.quality.blur_threshold)
        cfg.quality.min_brightness = st.number_input("Độ sáng tối thiểu", min_value=0.0, max_value=255.0, value=cfg.quality.min_brightness)
        cfg.quality.max_brightness = st.number_input("Độ sáng tối đa", min_value=cfg.quality.min_brightness, max_value=255.0, value=max(cfg.quality.max_brightness, cfg.quality.min_brightness))
    return cfg


def render_result(state: dict, file_key: str, filename: str, cfg: OCRModuleConfig,
                  context: str, consumer: TextConsumer | None) -> None:
    """Shared by image and PDF; changing generation resets editor widget state."""
    result = state.get("result")
    if result is None:
        return
    if result.ok:
        st.success("Trích xuất hoàn tất. Hãy kiểm tra văn bản trước khi sử dụng.")
    else:
        st.error(result.reason)
    for warning in result.warnings:
        st.warning(warning)
    editor_key = f"text_{file_key}_{state.get('generation', 0)}"
    state["user_text"] = st.text_area(
        "Văn bản bàn giao (có thể chỉnh sửa)", value=state.get("user_text", result.text),
        key=editor_key, height=300,
        on_change=lambda: st.session_state.pop("game_raw_text", None),
    )
    text = state["user_text"]
    review_needed = not result.ok or text != result.text
    reviewed = False
    if review_needed:
        # An acknowledgement belongs to the exact editor contents, not a previous edit.
        digest = hashlib.sha256(text.encode()).hexdigest()
        reviewed = st.checkbox("Tôi đã kiểm tra và xác nhận nội dung này", key=f"review_{editor_key}_{digest}")
    st.download_button("Tải văn bản .txt", text, file_name=f"ocr_{filename.rsplit('.', 1)[0]}.txt", mime="text/plain", key=f"download_{file_key}")
    if consumer is None:
        st.info("Chưa kết nối game. Bạn có thể tải văn bản hoặc nhờ nhóm tích hợp nơi tiếp nhận.")
    if st.button("Chuyển văn bản sang game", key=f"send_{file_key}", disabled=consumer is None):
        st.session_state.pop("game_raw_text", None)
        try:
            deliver_text(result=result, text=text, consumer=consumer, gate=cfg.gate,
                         reviewed=reviewed, result_context=state.get("result_context", ""), current_context=context)
        except Exception as exc:
            st.error(f"Chưa chuyển văn bản: {exc}")
        else:
            st.session_state["game_raw_text"] = text  # Compatibility, only AFTER receipt.
            st.success("Nơi tiếp nhận đã nhận văn bản.")


def main(text_consumer: TextConsumer | None = None):
    st.set_page_config(page_title="OCR Tài liệu Học tập", page_icon="📖", layout="wide")
    st.title("OCR tài liệu ôn tập")
    cfg = render_sidebar_configs()
    allowed = ["jpg", "jpeg", "png", "webp"]
    if PDF_AVAILABLE:
        allowed.append("pdf")
    if HEIF_AVAILABLE:
        allowed.extend(["heic", "heif"])
    uploaded = st.file_uploader("Tải ảnh hoặc PDF", type=allowed, accept_multiple_files=True)
    identities = tuple(f"{index}:{f.name}:{get_file_md5(f.getvalue())}" for index, f in enumerate(uploaded or []))
    upload_context = (identities, repr(cfg))
    if st.session_state.get("upload_context") != upload_context:
        st.session_state.pop("game_raw_text", None)
        st.session_state["ocr_states"] = {}
        # Old editor/acknowledgement widgets must not restore stale data.
        for key in list(st.session_state):
            if key.startswith(("text_", "review_")):
                del st.session_state[key]
        st.session_state["upload_context"] = upload_context
    if not uploaded:
        st.info("Tải tài liệu để bắt đầu.")
        return
    for identity, file in zip(identities, uploaded):
        file_key = hashlib.sha256(identity.encode()).hexdigest()
        data = file.getvalue()
        state = st.session_state.ocr_states.setdefault(file_key, {"rot": 0, "generation": 0})
        st.subheader(file.name)
        is_pdf = file.name.lower().endswith(".pdf")
        start, count = 0, None
        if is_pdf:
            start = int(st.number_input("Trang bắt đầu", min_value=1, value=1, step=1, key=f"start_{file_key}")) - 1
            count = int(st.number_input("Số trang", min_value=1, max_value=50, value=1, step=1, key=f"count_{file_key}"))
        else:
            for column, (label, delta) in zip(st.columns(3), [("Xoay trái", -90), ("Xoay phải", 90), ("Đặt lại", 0)]):
                if column.button(label, key=f"{label}_{file_key}"):
                    state["rot"] = (state["rot"] + delta) % 360 if delta else 0
                    invalidate_result(state)
            try:
                original, preview, warnings, metrics, ok, reason = preview_processed_image(data, state["rot"], cfg)
            except (ValueError, OSError, RuntimeError) as exc:
                invalidate_result(state)
                st.error(f"Không thể đọc ảnh: {exc}")
                continue
            left, right = st.columns(2)
            left.image(original, caption="Ảnh gốc")
            right.image(preview, caption="Sau tiền xử lý")
            for warning in warnings:
                st.warning(warning)
            if not ok:
                st.error(reason)
            st.caption(f"Độ nét: {metrics['blur']:.1f}; độ sáng: {metrics['brightness']:.1f}")
        context = repr((identity, repr(cfg), state["rot"], start, count))
        if state.get("context") != context:
            invalidate_result(state)
            state["context"] = context
        if st.button("Trích xuất văn bản", key=f"ocr_{file_key}"):
            invalidate_result(state)
            with st.spinner("Đang nhận dạng tài liệu..."):
                before = time.perf_counter()
                result = run_pipeline(data, cfg, manual_rotation_deg=state["rot"], pdf_start_page=start, pdf_max_pages=count)
                state.update(result=result, user_text=result.text, result_context=context,
                             processing_time=time.perf_counter() - before)
        if "processing_time" in state:
            st.caption(f"Thời gian xử lý: {state['processing_time']:.2f}s")
        render_result(state, file_key, file.name, cfg, context, text_consumer)


if __name__ == "__main__":
    main()
