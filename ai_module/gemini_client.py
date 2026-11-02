"""
gemini_client.py
Kết nối Google Gemini API và xử lý bóc tách Markdown code fence.
"""

import os
import re
import logging
from dotenv import load_dotenv

# Tải biến môi trường từ .env
load_dotenv()
logger = logging.getLogger(__name__)


class AIProcessingError(RuntimeError):
    """Lỗi xử lý trong pipeline AI (thông báo tiếng Việt thân thiện theo Yêu cầu 2.2)"""
    pass


def strip_markdown_fence(text: str) -> str:
    """
    Nếu AI trả code fence (```json ... ``` hoặc ``` ... ```),
    hệ thống loại bỏ fence trước khi parse JSON.
    """
    s = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        return match.group(1).strip()
    return s


def call_gemini_api(prompt: str, model_name: str = "gemini-3.5-flash-lite") -> str:
    """
    Gọi Google Gemini API sinh dữ liệu JSON theo prompt.
    API key được lấy từ biến môi trường GEMINI_API_KEY (.env).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or "your_gemini_api_key_here" in api_key:
        raise AIProcessingError(
            "Chưa cấu hình GEMINI_API_KEY hợp lệ trong file .env! "
            "Vui lòng thêm GEMINI_API_KEY=AIzaSy... vào .env trước khi gọi API."
        )

    target_model = os.getenv("GEMINI_MODEL", model_name)
    timeout_sec = int(os.getenv("GEMINI_TIMEOUT", "45"))
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt, request_options={"timeout": timeout_sec})
        return response.text
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {e}")
        raise AIProcessingError(f"Lỗi kết nối Gemini API (TC08): {str(e)}")
