"""Trang chính Streamlit: điều hướng các bước (upload -> duyệt -> chơi -> tổng kết)."""
import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
SUBJECTS = {"english": "Tiếng Anh", "philosophy": "Triết học"}
GAMES = ("fill_blank", "matching", "quiz")


def load_sample_chapter(subject: str) -> dict:
    """Ghép 3 file mẫu của một môn thành 1 chapter đầy đủ."""
    parts, title = [], None
    for game in GAMES:
        path = DATA_DIR / f"sample_{subject}_{game}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        title = data["chapter_title"]
        parts.extend(data["parts"])
    parts.sort(key=lambda p: p["part"])
    return {"subject": subject, "chapter_title": title, "parts": parts}


def main():
    st.set_page_config(page_title="Web ôn tập bằng game", page_icon="🎮")
    st.title("🎮 Web ôn tập bằng game")

    if "chapter" not in st.session_state:
        st.session_state.chapter = None

    # TODO (Sơn Phạm): trang tải tệp, duyệt câu hỏi, điều hướng, tổng kết.
    subject = st.selectbox("Chọn môn", list(SUBJECTS), format_func=SUBJECTS.get)
    if st.button("Dùng dữ liệu mẫu"):
        st.session_state.chapter = load_sample_chapter(subject)

    chapter = st.session_state.chapter
    if chapter:
        st.subheader(chapter["chapter_title"])
        for part in chapter["parts"]:
            st.write(f"Phần {part['part']}: {part['game']} ({len(part['items'])} mục)")


if __name__ == "__main__":
    main()