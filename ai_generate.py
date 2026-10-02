"""Gọi AI, tạo chapter.json, kiểm tra bằng Pydantic. (Phụ trách: Sang)"""

MAX_RETRIES = 2


def generate_chapter(text: str, subject: str) -> dict:
    """Văn bản sạch + môn học -> dict đúng hợp đồng chapter.json."""
    # TODO: gọi prompt từng phần (prompts.py), parse JSON, kiểm tra Pydantic, retry tối đa 2 lần.
    raise NotImplementedError
