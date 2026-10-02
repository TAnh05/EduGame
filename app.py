"""Trang chính Streamlit: điều hướng các bước (upload -> duyệt -> chơi -> tổng kết)."""
import json
from pathlib import Path

import streamlit as st

SAMPLE_PATH = Path(__file__).parent / "data" / "sample_chapter.json"


def load_sample_chapter() -> dict:
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    st.set_page_config(page_title="Web ôn tập bằng game", page_icon="🎮")
    st.title("🎮 Web ôn tập bằng game")

    if "chapter" not in st.session_state:
        st.session_state.chapter = None

    # TODO (Sơn Phạm): trang tải tệp, duyệt câu hỏi, điều hướng, tổng kết.
    if st.button("Dùng dữ liệu mẫu"):
        st.session_state.chapter = load_sample_chapter()

    chapter = st.session_state.chapter
    if chapter:
        st.subheader(chapter["chapter_title"])
        for part in chapter["parts"]:
            st.write(f"Phần {part['part']}: {part['game']} ({len(part['items'])} mục)")


if __name__ == "__main__":
    main()
