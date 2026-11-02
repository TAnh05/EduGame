"""
ai_module
Package xử lý AI & Kiểm định dữ liệu Pydantic V2 cho 3 trò chơi giáo dục.
"""

from .models import (
    FillBlankItem, MatchingItem, QuizItem,
    Part1FillBlank, Part2Matching, Part3Quiz,
    ChapterModel
)
from .gemini_client import (
    call_gemini_api, strip_markdown_fence, AIProcessingError
)
from .pipeline import (
    generate_chapter, generate_part_with_retry,
    validate_input_text, validate_chapter_data,
    load_chapter_from_file, save_chapter_to_file,
    split_text_into_three_parts
)
from .final_quiz import create_final_quiz_pool

__all__ = [
    "FillBlankItem", "MatchingItem", "QuizItem",
    "Part1FillBlank", "Part2Matching", "Part3Quiz",
    "ChapterModel", "AIProcessingError",
    "call_gemini_api", "strip_markdown_fence",
    "generate_chapter", "generate_part_with_retry",
    "validate_input_text", "validate_chapter_data",
    "load_chapter_from_file", "save_chapter_to_file",
    "split_text_into_three_parts", "create_final_quiz_pool"
]
