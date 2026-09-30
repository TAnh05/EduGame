"""
Điểm khởi chạy chính cho ứng dụng Web Streamlit (app.py).
Cho phép nhóm chạy nhanh từ thư mục gốc:
    streamlit run app.py
hoặc:
    streamlit run ocr_module/ui_upload.py
"""

import sys
import os

# Đảm bảo đường dẫn thư mục gốc nằm trong sys.path
_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from ocr_module.ui_upload import main

if __name__ == "__main__":
    main()
