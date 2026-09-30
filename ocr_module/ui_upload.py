"""
Giao diện Streamlit: Upload ảnh tài liệu, xem trước ảnh tiền xử lý,
xoay thủ công, trích xuất text qua Vintern-1B v3.5 và chỉnh sửa/xuất dữ liệu.
"""

import hashlib
import io
import streamlit as st
from PIL import Image

from ocr_module.config import OCRModuleConfig
from ocr_module.io_utils import (
    load_image_from_bytes, 
    pil_to_cv2, 
    cv2_to_pil, 
    load_images_from_pdf, 
    PDF_AVAILABLE
)
from ocr_module.preprocess import run_preprocessing_pipeline
from ocr_module.pipeline import run_pipeline, OCRResult


def get_file_md5(data: bytes) -> str:
    """Tạo mã băm MD5 từ dữ liệu file để quản lý cache theo nội dung."""
    return hashlib.md5(data).hexdigest()


def preview_processed_image(
    file_bytes: bytes, 
    rotation_deg: int, 
    cfg: OCRModuleConfig
) -> tuple[Image.Image, Image.Image, list[str], dict, bool, str]:
    """Tạo ảnh xem trước: ảnh gốc và ảnh sau khi qua chuỗi tiền xử lý."""
    orig_pil, _ = load_image_from_bytes(file_bytes, apply_exif=cfg.preprocess.enable_exif)
    img_bgr = pil_to_cv2(orig_pil)
    
    proc_bgr, passed, reason, warnings, metrics = run_preprocessing_pipeline(
        img_bgr,
        prep_cfg=cfg.preprocess,
        quality_cfg=cfg.quality,
        manual_rotation_deg=rotation_deg
    )
    proc_pil = cv2_to_pil(proc_bgr)
    return orig_pil, proc_pil, warnings, metrics, passed, reason


def render_sidebar_configs() -> OCRModuleConfig:
    """Sidebar tùy chỉnh tham số tiền xử lý và mô hình (cho phép bật/tắt để thử nghiệm)."""
    st.sidebar.header("⚙️ Cấu hình OCR Module")
    
    cfg = OCRModuleConfig()
    
    with st.sidebar.expander("🛠️ Tiền xử lý ảnh", expanded=False):
        cfg.preprocess.enable_exif = st.checkbox("Sửa góc theo EXIF", value=cfg.preprocess.enable_exif)
        cfg.preprocess.enable_resize = st.checkbox("Giới hạn kích thước (Resize)", value=cfg.preprocess.enable_resize)
        cfg.preprocess.max_dimension = st.slider("Cạnh tối đa (px)", 1200, 3000, cfg.preprocess.max_dimension, step=100)
        cfg.preprocess.enable_deskew = st.checkbox("Chỉnh nghiêng nhỏ (Deskew)", value=cfg.preprocess.enable_deskew)
        cfg.preprocess.enable_illumination_fix = st.checkbox("Cân bằng sáng & Khử bóng", value=cfg.preprocess.enable_illumination_fix)
        cfg.preprocess.enable_sharpen = st.checkbox("Làm nét nhẹ (Unsharp Mask)", value=cfg.preprocess.enable_sharpen)
        cfg.preprocess.enable_denoise = st.checkbox("Khử nhiễu nhẹ (Denoise)", value=cfg.preprocess.enable_denoise)
        
    with st.sidebar.expander("🤖 Mô hình Vintern-1B v3.5", expanded=False):
        cfg.model.max_num = st.slider("Số ô chia ảnh (max_num)", 1, 8, cfg.model.max_num, 
                                     help="Số lượng ô ảnh càng cao càng rõ nét nhưng tốn VRAM hơn. 4 là tối ưu cho GPU 4GB.")
        cfg.model.num_beams = st.selectbox("Beam Search (num_beams)", [1, 3], index=0 if cfg.model.num_beams == 1 else 1)
        cfg.model.repetition_penalty = st.slider("Phạt lặp từ (repetition_penalty)", 1.0, 2.5, cfg.model.repetition_penalty, step=0.1)
        cfg.model.max_new_tokens = st.slider("Tokens tối đa sinh ra", 256, 2048, cfg.model.max_new_tokens, step=128)
        
    with st.sidebar.expander("🛡️ Ngưỡng chất lượng", expanded=False):
        cfg.quality.blur_threshold = st.number_input("Ngưỡng mờ (Laplacian)", value=cfg.quality.blur_threshold)
        cfg.quality.min_brightness = st.number_input("Độ sáng tối thiểu", value=cfg.quality.min_brightness)
        cfg.quality.max_brightness = st.number_input("Độ sáng tối đa (lóa)", value=cfg.quality.max_brightness)
        
    return cfg


def main():
    st.set_page_config(
        page_title="OCR Tài liệu Học tập - Vintern 1B", 
        page_icon="📖", 
        layout="wide"
    )

    st.title("📖 OCR Trích xuất Tài liệu Ôn tập")
    st.caption("Chuyển ảnh sách vở, giáo trình sang văn bản chuẩn bị dữ liệu tạo câu hỏi ôn tập bằng game.")

    cfg = render_sidebar_configs()

    # Hỗ trợ nhiều định dạng ảnh và file PDF scan
    allowed_types = ["jpg", "jpeg", "png", "webp"]
    if PDF_AVAILABLE:
        allowed_types.append("pdf")

    uploaded_files = st.file_uploader(
        "Tải lên một hoặc nhiều ảnh tài liệu:",
        type=allowed_types,
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("👆 Vui lòng kéo thả hoặc tải lên ảnh chụp trang sách, đề bài hoặc tài liệu học tập để bắt đầu.")
        return

    # Quản lý trạng thái theo session_state
    if "ocr_states" not in st.session_state:
        st.session_state.ocr_states = {}

    for file_idx, f in enumerate(uploaded_files):
        file_bytes = f.getvalue()
        file_key = get_file_md5(file_bytes)
        
        # Khởi tạo state cho từng file
        if file_key not in st.session_state.ocr_states:
            st.session_state.ocr_states[file_key] = {
                "rot": 0,
                "result": None,
                "user_text": "",
                "file_name": f.name
            }

        state = st.session_state.ocr_states[file_key]

        st.markdown(f"--- \n ### 📄 Tập tin #{file_idx + 1}: `{f.name}`")

        # Kiểm tra nếu là file PDF
        if f.name.lower().endswith(".pdf"):
            st.info("Tập tin PDF phát hiện. Bấm 'Trích xuất toàn bộ trang' bên dưới để xử lý từng trang.")
            if st.button(f"🚀 Trích xuất text từ PDF: {f.name}", key=f"btn_pdf_{file_key}"):
                with st.spinner("Đang xử lý từng trang của tài liệu PDF..."):
                    res = run_pipeline(file_bytes, cfg=cfg, manual_rotation_deg=0)
                    state["result"] = res
                    state["user_text"] = res.text
                    st.rerun()

            res = state.get("result")
            if res:
                if not res.ok:
                    st.error(f"❌ Không đạt cổng chất lượng: {res.reason}")
                for w in res.warnings:
                    st.warning(f"⚠️ {w}")
                state["user_text"] = st.text_area(
                    "Văn bản trích xuất (có thể trực tiếp chỉnh sửa nếu có sai sót):",
                    value=state["user_text"],
                    height=300,
                    key=f"txt_{file_key}"
                )
            continue

        # Đối với ảnh thông thường: Hiển thị So sánh Trước & Sau xử lý + Xoay thủ công
        orig_pil, proc_pil, warnings, metrics, q_passed, q_reason = preview_processed_image(
            file_bytes, state["rot"], cfg
        )

        col_img1, col_img2 = st.columns(2)
        with col_img1:
            st.image(orig_pil, caption=f"Ảnh gốc ({orig_pil.width}x{orig_pil.height})", use_container_width=True)

        with col_img2:
            st.image(proc_pil, caption=f"Sau tiền xử lý ({proc_pil.width}x{proc_pil.height})", use_container_width=True)
            
            # Các nút thao tác xoay ảnh thủ công
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("↺ Xoay trái 90°", key=f"rot_left_{file_key}"):
                    state["rot"] = (state["rot"] - 90) % 360
                    st.rerun()
            with btn_col2:
                if st.button("↻ Xoay phải 90°", key=f"rot_right_{file_key}"):
                    state["rot"] = (state["rot"] + 90) % 360
                    st.rerun()
            with btn_col3:
                if st.button("🔄 Đặt lại góc 0°", key=f"rot_reset_{file_key}"):
                    state["rot"] = 0
                    st.rerun()

        # Hiển thị thông số chất lượng đo được
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Độ nét (Laplacian)", f"{metrics['blur']:.1f}")
        metric_col2.metric("Độ sáng TB", f"{metrics['brightness']:.1f} / 255")
        metric_col3.metric("Độ tương phản (Std)", f"{metrics['contrast']:.1f}")

        # Hiển thị các cảnh báo tiền xử lý
        for w in warnings:
            st.warning(f"⚠️ {w}")

        if not q_passed:
            st.error(f"🚫 Cảnh báo chất lượng: {q_reason}")
            st.info("💡 Bạn nên chụp lại tài liệu đủ sáng, giữ thẳng và lấy nét rõ trước khi gửi vào hệ thống.")

        # Nút bấm kích hoạt trích xuất
        if st.button(f"🔍 Trích xuất văn bản", key=f"btn_ocr_{file_key}", type="primary"):
            with st.spinner("Đang chạy mô hình Vintern-1B v3.5 trích xuất văn bản..."):
                res = run_pipeline(file_bytes, cfg=cfg, manual_rotation_deg=state["rot"])
                state["result"] = res
                state["user_text"] = res.text
                st.rerun()

        # Hiển thị kết quả OCR và ô chỉnh sửa văn bản
        res: OCRResult = state.get("result")
        if res:
            if not res.ok:
                st.error(f"❌ Cổng chất lượng từ chối: {res.reason}")
            else:
                st.success("✅ Trích xuất văn bản thành công!")

            for w in res.warnings:
                st.warning(f"⚠️ {w}")

            state["user_text"] = st.text_area(
                "Văn bản trích xuất (Bạn có thể kiểm tra và sửa nhanh lỗi chính tả tại đây):",
                value=state["user_text"],
                height=300,
                key=f"txt_{file_key}"
            )

            # Các nút xuất dữ liệu
            down_col1, down_col2 = st.columns([1, 2])
            with down_col1:
                st.download_button(
                    label="💾 Tải về file .txt",
                    data=state["user_text"],
                    file_name=f"ocr_{f.name.rsplit('.', 1)[0]}.txt",
                    mime="text/plain",
                    key=f"dl_{file_key}"
                )
            with down_col2:
                if st.button("🎮 Dùng text này để tạo câu hỏi ôn tập", key=f"game_btn_{file_key}"):
                    st.session_state["game_raw_text"] = state["user_text"]
                    st.success("🎉 Đã lưu văn bản vào bộ nhớ chuẩn bị sinh câu hỏi cho game ôn tập!")


if __name__ == "__main__":
    main()
