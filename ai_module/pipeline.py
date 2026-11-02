"""
pipeline.py
Hàm điều phối toàn bộ quy trình: tiền xử lý, gọi prompt từng phần, retry và fallback.
"""

import os
import json
import logging
import hashlib
from typing import List, Union, Optional, Callable

from .models import (
    FillBlankItem, MatchingItem, QuizItem,
    Part1FillBlank, Part2Matching, Part3Quiz,
    ChapterModel
)
from .gemini_client import (
    strip_markdown_fence, call_gemini_api, AIProcessingError
)

logger = logging.getLogger(__name__)

# Giới hạn độ dài văn bản (TC04, TC06)
MIN_TEXT_LENGTH = 50
MAX_TEXT_LENGTH = 15000


def compute_text_hash(text: str) -> str:
    """Tính mã băm SHA-256 duy nhất đại diện cho nội dung văn bản (chuẩn hóa khoảng trắng)."""
    normalized = " ".join(text.strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def split_text_into_three_parts(text: str) -> List[str]:
    """Chia văn bản thành 3 phần logic cho 3 game."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return ["", "", ""]

    total = len(paragraphs)
    if total < 3:
        n = len(text)
        p1 = text[: n // 3].strip()
        p2 = text[n // 3 : 2 * n // 3].strip()
        p3 = text[2 * n // 3 :].strip()
        return [p1, p2, p3]

    step = total // 3
    part1 = "\n\n".join(paragraphs[:step])
    part2 = "\n\n".join(paragraphs[step : 2 * step])
    part3 = "\n\n".join(paragraphs[2 * step :])
    return [part1, part2, part3]


def validate_input_text(clean_text: str) -> str:
    """Kiểm tra ca biên TC04, TC05, TC06."""
    if not clean_text or not clean_text.strip():
        raise AIProcessingError("Lỗi (TC05): Văn bản đầu vào rỗng. Vui lòng cung cấp nội dung tài liệu học tập.")

    text_stripped = clean_text.strip()
    if len(text_stripped) < MIN_TEXT_LENGTH:
        raise AIProcessingError(
            f"Lỗi (TC04): Văn bản quá ngắn ({len(text_stripped)} ký tự < {MIN_TEXT_LENGTH} ký tự tối thiểu). "
            "Không đủ nội dung để tạo 3 trò chơi ôn tập. Vui lòng tải tài liệu đầy đủ hơn."
        )

    if len(text_stripped) > MAX_TEXT_LENGTH:
        logger.warning(
            f"Cảnh báo (TC06): Văn bản vượt quá giới hạn ({len(text_stripped)} > {MAX_TEXT_LENGTH} ký tự). "
            "Hệ thống sẽ tự động cắt tỉa lấy đoạn đầu phù hợp để tiết kiệm quota API và tránh timeout."
        )
        text_stripped = text_stripped[:MAX_TEXT_LENGTH]

    return text_stripped


def validate_chapter_data(raw_data: Union[str, dict]) -> ChapterModel:
    """Parse JSON/Dict sang ChapterModel Pydantic."""
    if isinstance(raw_data, str):
        cleaned_str = strip_markdown_fence(raw_data)
        data_dict = json.loads(cleaned_str)
    elif isinstance(raw_data, dict):
        data_dict = raw_data
    else:
        raise TypeError("raw_data phải là chuỗi JSON hoặc dictionary")

    return ChapterModel(**data_dict)


def load_chapter_from_file(file_path: str) -> ChapterModel:
    """Đọc và kiểm tra file JSON có sẵn trên đĩa."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ChapterModel(**data)


def save_chapter_to_file(chapter: Union[ChapterModel, dict], file_path: str = "chapter.json") -> None:
    """Lưu kết quả ra file JSON theo đúng hợp đồng."""
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    data_to_dump = chapter.model_dump() if isinstance(chapter, ChapterModel) else chapter
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_to_dump, f, ensure_ascii=False, indent=2)


def parse_and_validate_part(part_num: int, raw_text: str) -> Union[Part1FillBlank, Part2Matching, Part3Quiz]:
    """Parse JSON và kiểm tra schema Pydantic cho từng phần."""
    cleaned_json_str = strip_markdown_fence(raw_text)
    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as jde:
        raise AIProcessingError(f"AI trả về dữ liệu không phải cú pháp JSON: {jde}")

    prefixes = {1: "p1", 2: "p2", 3: "p3"}
    prefix = prefixes.get(part_num, f"p{part_num}")

    if part_num == 1:
        if "part" not in data:
            data["part"] = 1
        if "game" not in data:
            data["game"] = "fill_blank"
        part = Part1FillBlank(**data)
        # Tự động gán id nếu AI trả về rỗng
        for i, item in enumerate(part.items):
            if not item.id:
                item.id = f"{prefix}-{i+1:02d}"
        return part
    elif part_num == 2:
        if "part" not in data:
            data["part"] = 2
        if "game" not in data:
            data["game"] = "matching"
        part = Part2Matching(**data)
        for i, item in enumerate(part.items):
            if not item.id:
                item.id = f"{prefix}-{i+1:02d}"
        return part
    elif part_num == 3:
        if "part" not in data:
            data["part"] = 3
        if "game" not in data:
            data["game"] = "quiz"
        part = Part3Quiz(**data)
        for i, item in enumerate(part.items):
            if not item.id:
                item.id = f"{prefix}-{i+1:02d}"
        return part
    else:
        raise ValueError(f"part_num không hợp lệ: {part_num}")


def generate_part_with_retry(
    part_num: int,
    subject: str,
    text_part: str,
    max_retries: int = 2,
    custom_caller: Optional[Callable[[str], str]] = None
) -> Union[Part1FillBlank, Part2Matching, Part3Quiz]:
    """Quy tắc nghiệp vụ: Retry tối đa 2 lần nếu JSON sai hoặc vi phạm schema."""
    from prompts import get_game_prompt

    prompt = get_game_prompt(part_num, subject, text_part)
    caller = custom_caller or call_gemini_api

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            raw_response = caller(prompt)
            validated_part = parse_and_validate_part(part_num, raw_response)
            return validated_part
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"[Part {part_num}] Lỗi sinh dữ liệu lần {attempt + 1}: {e}. Đang thử lại (lần {attempt + 2}/{max_retries + 1})..."
                )
            else:
                logger.error(
                    f"[Part {part_num}] Đã thử lại tối đa {max_retries} lần nhưng vẫn thất bại: {e}"
                )

    raise AIProcessingError(
        f"Không thể sinh dữ liệu hợp lệ cho Phần {part_num} sau {max_retries} lần thử lại (TC07). Chi tiết lỗi: {last_error}"
    )


def generate_chapter(
    clean_text: str,
    subject: str,
    chapter_title: str = "Chương ôn tập",
    output_path: str = "chapter.json",
    max_retries: int = 2,
    custom_caller: Optional[Callable[[str], str]] = None,
    use_fallback_on_failure: bool = True,
    use_cache: bool = True
) -> ChapterModel:
    """Điều phối toàn bộ pipeline sinh câu hỏi ôn tập."""
    subject_norm = subject.strip().lower()
    if subject_norm not in ["english", "philosophy"]:
        raise ValueError("subject chỉ nhận giá trị 'english' hoặc 'philosophy'")

    # Kiểm tra ca biên (TC04, TC05, TC06)
    valid_text = validate_input_text(clean_text)
    text_hash = compute_text_hash(valid_text)
    hash_file = f"{output_path}.hash"

    # Cơ chế Cache theo Hash văn bản (F09)
    if use_cache and os.path.exists(output_path):
        is_cache_match = False
        if os.path.exists(hash_file):
            try:
                with open(hash_file, "r", encoding="utf-8") as hf:
                    saved_hash = hf.read().strip()
                if saved_hash == text_hash:
                    is_cache_match = True
            except Exception as e:
                logger.debug(f"Không thể đọc file hash: {e}")
        else:
            # Chưa có file hash thì không được xem là khớp cache
            is_cache_match = False

        if is_cache_match:
            try:
                cached_chapter = load_chapter_from_file(output_path)
                if cached_chapter.subject == subject_norm:
                    logger.info(f"Kích hoạt cơ chế Cache (F09): Tái sử dụng dữ liệu hợp lệ từ {output_path} (Hash: {text_hash})")
                    return cached_chapter
            except Exception as cache_err:
                logger.warning(f"File cache {output_path} không hợp lệ, sẽ tiến hành sinh mới: {cache_err}")

    parts_text = split_text_into_three_parts(valid_text)

    try:
        part1 = generate_part_with_retry(1, subject_norm, parts_text[0], max_retries, custom_caller)
        part2 = generate_part_with_retry(2, subject_norm, parts_text[1], max_retries, custom_caller)
        part3 = generate_part_with_retry(3, subject_norm, parts_text[2], max_retries, custom_caller)

        chapter = ChapterModel(
            subject=subject_norm,
            chapter_title=chapter_title,
            parts=[part1, part2, part3]
        )

        save_chapter_to_file(chapter, output_path)
        # Ghi kèm mã hash văn bản để nhận diện cache cho các lần gọi sau
        try:
            with open(hash_file, "w", encoding="utf-8") as hf:
                hf.write(text_hash)
        except Exception as he:
            logger.debug(f"Không thể ghi file hash: {he}")

        return chapter

    except Exception as e:
        logger.error(f"Lỗi trong quá trình sinh chapter: {e}")
        if use_fallback_on_failure:
            # Chọn file fallback đúng theo môn học (không nhầm philosophy với english)
            _data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
            _data_dir = os.path.normpath(_data_dir)
            fallback_name = "sample_chapter.json" if subject_norm == "philosophy" else "sample_chapter_english.json"
            fallback_path_abs = os.path.join(_data_dir, fallback_name)
            # Nếu file theo môn không tồn tại thì dùng file mặc định
            if not os.path.exists(fallback_path_abs):
                fallback_path_abs = os.path.join(_data_dir, "sample_chapter.json")
            if os.path.exists(fallback_path_abs):
                logger.info(f"Kích hoạt cơ chế dự phòng (TC08): Tải dữ liệu mẫu từ {fallback_path_abs}")
                fallback_chapter = load_chapter_from_file(fallback_path_abs)
                save_chapter_to_file(fallback_chapter, output_path)
                # Xoá file hash cũ để cache không nhớ sai sau khi fallback ghi đè
                if os.path.exists(hash_file):
                    try:
                        os.remove(hash_file)
                        logger.debug(f"Đã xoá file hash {hash_file} sau khi ghi fallback")
                    except Exception as he:
                        logger.debug(f"Không thể xoá file hash: {he}")
                return fallback_chapter
        raise e
