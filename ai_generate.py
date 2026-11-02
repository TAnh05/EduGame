"""
ai_generate.py
Module xuất bản các giao diện chính cho việc sinh câu hỏi và kiểm định dữ liệu Pydantic.
"""

from ai_module import (
    FillBlankItem, MatchingItem, QuizItem,
    Part1FillBlank, Part2Matching, Part3Quiz,
    ChapterModel, AIProcessingError,
    call_gemini_api, strip_markdown_fence,
    generate_chapter, generate_part_with_retry,
    validate_input_text, validate_chapter_data,
    load_chapter_from_file, save_chapter_to_file,
    split_text_into_three_parts, create_final_quiz_pool
)

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
