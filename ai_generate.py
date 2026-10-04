"""
ai_generate.py
Module xử lý sinh dữ liệu câu hỏi ôn tập và kiểm tra Schema hợp đồng bằng Pydantic.

Quy tắc nghiệp vụ tuân thủ báo cáo (Mục 6.1, 6.2, 7.2):
1. Đầu vào: clean_text (văn bản sạch) và subject ('english' hoặc 'philosophy').
2. Chia văn bản thành 3 phần logic cho 3 game.
3. Kiểm tra Pydantic:
   - subject chỉ nhận 'english' hoặc 'philosophy', chapter_title không rỗng.
   - parts có đúng 3 phần với part lần lượt 1, 2, 3.
   - game tương ứng đúng: fill_blank, matching, quiz.
   - fill_blank: sentence chứa đúng một ký hiệu '___', answer không rỗng.
   - matching: term và definition không rỗng.
   - quiz: đúng 4 options, answer là số nguyên 0..3.
4. Tách bỏ code fence markdown nếu AI trả về bọc ```json ... ```.
5. Sẵn sàng khung retry tối đa 2 lần và nạp API key an toàn qua python-dotenv.
"""

import os
import re
import json
from typing import List, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

# Tải biến môi trường từ .env (Quy tắc bảo mật: Không để API key trong mã nguồn)
load_dotenv()


# =====================================================================
# 1. KHUNG KIỂM TRA PYDANTIC (PYDANTIC SCHEMA CONTRACT)
# =====================================================================

class FillBlankItem(BaseModel):
    """Quy tắc Game 1: sentence chứa đúng 1 '___' và answer không rỗng"""
    id: str = Field(default="")
    sentence: str
    answer: str

    @field_validator("sentence")
    def validate_sentence(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("sentence không được để trống")
        count_blank = s.count("___")
        if count_blank != 1:
            raise ValueError(f"sentence phải chứa đúng MỘT ký hiệu '___' (hiện có: {count_blank})")
        return s

    @field_validator("answer")
    def validate_answer(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("answer không được để trống")
        return s


class MatchingItem(BaseModel):
    """Quy tắc Game 2: term và definition đều không rỗng"""
    id: str = Field(default="")
    term: str
    definition: str

    @field_validator("term")
    def validate_term(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("term không được để trống")
        return s

    @field_validator("definition")
    def validate_definition(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("definition không được để trống")
        return s


class QuizItem(BaseModel):
    """Quy tắc Game 3: đúng 4 options, answer là số nguyên 0..3"""
    id: str = Field(default="")
    q: str
    options: List[str]
    answer: int

    @field_validator("q")
    def validate_q(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("q (câu hỏi trắc nghiệm) không được để trống")
        return s

    @field_validator("options")
    def validate_options(cls, v: List[str]) -> List[str]:
        if len(v) != 4:
            raise ValueError(f"quiz phải có đúng 4 options (hiện có: {len(v)})")
        if any(not opt.strip() for opt in v):
            raise ValueError("Tất cả 4 lựa chọn trong options đều không được để trống")
        return v

    @field_validator("answer")
    def validate_answer(cls, v: int) -> int:
        if v not in [0, 1, 2, 3]:
            raise ValueError(f"answer của quiz phải là số nguyên trong khoảng 0..3 (nhận được: {v})")
        return v


class Part1FillBlank(BaseModel):
    part: Literal[1] = 1
    game: Literal["fill_blank"] = "fill_blank"
    items: List[FillBlankItem]


class Part2Matching(BaseModel):
    part: Literal[2] = 2
    game: Literal["matching"] = "matching"
    items: List[MatchingItem]


class Part3Quiz(BaseModel):
    part: Literal[3] = 3
    game: Literal["quiz"] = "quiz"
    items: List[QuizItem]


class ChapterModel(BaseModel):
    """
    Hợp đồng JSON cấp cao nhất đại diện cho toàn bộ chapter.json
    """
    subject: Literal["english", "philosophy"]
    chapter_title: str
    parts: List[Union[Part1FillBlank, Part2Matching, Part3Quiz]]

    @field_validator("chapter_title")
    def validate_chapter_title(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("chapter_title không được để trống")
        return s

    @model_validator(mode="after")
    def validate_structure(self):
        # 1. Kiểm tra parts phải có đúng 3 phần
        if len(self.parts) != 3:
            raise ValueError(f"parts phải có đúng 3 phần (hiện có: {len(self.parts)})")

        # 2. part phải lần lượt là 1, 2, 3
        part_nums = [p.part for p in self.parts]
        if part_nums != [1, 2, 3]:
            raise ValueError(f"part phải lần lượt là 1, 2, 3 (hiện tại: {part_nums})")

        # 3. game phải khớp fill_blank, matching, quiz tương ứng
        expected_games = ["fill_blank", "matching", "quiz"]
        actual_games = [p.game for p in self.parts]
        if actual_games != expected_games:
            raise ValueError(f"game phải lần lượt là {expected_games} (hiện tại: {actual_games})")

        return self


# =====================================================================
# 2. CÁC HÀM XỬ LÝ DỮ LIỆU & LOẠI BỎ CODE FENCE
# =====================================================================

def strip_markdown_fence(text: str) -> str:
    """
    Quy tắc 6.2: Nếu AI trả code fence (```json ... ``` hoặc ``` ... ```),
    hệ thống loại bỏ fence trước khi parse JSON.
    """
    s = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        return match.group(1).strip()
    return s


def split_text_into_three_parts(text: str) -> List[str]:
    """
    Quy tắc 7.2: Chia văn bản thành 3 phần logic cho 3 game.
    Tách theo các đoạn văn bản (paragraphs) để giữ nguyên ngữ cảnh.
    """
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs:
        return ["", "", ""]

    total = len(paragraphs)
    if total < 3:
        # Nếu ít hơn 3 đoạn văn, phân chia theo số lượng ký tự
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


def validate_chapter_data(raw_data: Union[str, dict]) -> ChapterModel:
    """
    Parse chuỗi JSON hoặc Dictionary thành ChapterModel Pydantic.
    Ném lỗi ValidationError nếu không thỏa mãn bất kỳ quy tắc nào trong hợp đồng.
    """
    if isinstance(raw_data, str):
        cleaned_str = strip_markdown_fence(raw_data)
        data_dict = json.loads(cleaned_str)
    elif isinstance(raw_data, dict):
        data_dict = raw_data
    else:
        raise TypeError("raw_data phải là chuỗi JSON hoặc dictionary")

    # Kiểm tra Pydantic
    return ChapterModel(**data_dict)


def load_chapter_from_file(file_path: str) -> ChapterModel:
    """Đọc và kiểm tra file JSON có sẵn trên đĩa"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ChapterModel(**data)


def save_chapter_to_file(chapter: ChapterModel, file_path: str = "chapter.json") -> None:
    """Lưu ChapterModel thành file JSON theo đúng định dạng hợp đồng"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(chapter.model_dump(), f, ensure_ascii=False, indent=2)
