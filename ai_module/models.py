"""
models.py
Định nghĩa toàn bộ Schema dữ liệu và quy tắc thẩm định (Pydantic V2) cho 3 mini-game.
"""

from typing import List, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class FillBlankItem(BaseModel):
    """Game 1: sentence chứa đúng 1 '___' và answer không rỗng"""
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
    """Game 2: term và definition đều không rỗng"""
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
    """Game 3: đúng 4 options, answer là số nguyên trong khoảng 0..3"""
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

    @field_validator("items")
    def validate_items(cls, v: List[FillBlankItem]) -> List[FillBlankItem]:
        if not v:
            raise ValueError("Part 1 items không được để rỗng")
        return v


class Part2Matching(BaseModel):
    part: Literal[2] = 2
    game: Literal["matching"] = "matching"
    items: List[MatchingItem]

    @field_validator("items")
    def validate_items(cls, v: List[MatchingItem]) -> List[MatchingItem]:
        if not v:
            raise ValueError("Part 2 items không được để rỗng")
        return v


class Part3Quiz(BaseModel):
    part: Literal[3] = 3
    game: Literal["quiz"] = "quiz"
    items: List[QuizItem]

    @field_validator("items")
    def validate_items(cls, v: List[QuizItem]) -> List[QuizItem]:
        if not v:
            raise ValueError("Part 3 items không được để rỗng")
        return v


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
