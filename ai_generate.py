"""
ai_generate.py
Module xử lý sinh dữ liệu câu hỏi ôn tập và kiểm tra Schema hợp đồng bằng Pydantic.

Tuân thủ nghiêm ngặt các quy tắc trong Báo cáo kế hoạch & thiết kế hệ thống:
- Mục 6.1: Cấu trúc hợp đồng JSON chapter.json
- Mục 6.2: Quy tắc kiểm tra Pydantic & loại bỏ markdown fence
- Mục 7.2: Trách nhiệm của Sang:
    + Đầu vào: văn bản sạch (clean_text) và subject ('english' | 'philosophy')
    + Đầu ra: chapter.json
    + Chia văn bản thành 3 phần cho 3 game
    + Dùng prompt riêng cho từng game (từ prompts.py)
    + Yêu cầu AI chỉ dùng văn bản cung cấp và trả JSON
    + Parse và kiểm tra Pydantic
    + Cơ chế retry tối đa 2 lần khi AI trả JSON lỗi / sai schema
    + Lưu kết quả ra file chapter.json
    + Bảo mật: Quản lý API key qua .env (python-dotenv), không hardcode key trong mã nguồn
- Mục 11 & TC08: Cơ chế fallback sang JSON mẫu dự phòng khi gặp lỗi bất khả kháng
"""

import os
import re
import json
import logging
from typing import List, Literal, Union, Optional, Callable
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

# Tải biến môi trường từ .env (Quy tắc bảo mật: Không để API key trong mã nguồn)
load_dotenv()

# Cấu hình logging
logger = logging.getLogger(__name__)


# =====================================================================
# 1. KHUNG KIỂM TRA PYDANTIC (PYDANTIC SCHEMA CONTRACT - MỤC 6.1 & 6.2)
# =====================================================================

class FillBlankItem(BaseModel):
    """Quy tắc Game 1 (Mục 6.2): sentence chứa đúng 1 '___' và answer không rỗng"""
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
    """Quy tắc Game 2 (Mục 6.2): term và definition đều không rỗng"""
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
    """Quy tắc Game 3 (Mục 6.2): đúng 4 options, answer là số nguyên trong khoảng 0..3"""
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
    Hợp đồng JSON cấp cao nhất đại diện cho toàn bộ chapter.json (Mục 6.1)
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
# 2. XỬ LÝ VĂN BẢN & LOẠI BỎ CODE FENCE (MỤC 6.2 & 7.2)
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


def save_chapter_to_file(chapter: Union[ChapterModel, dict], file_path: str = "data/sample_chapter.json") -> None:
    """
    Quy tắc 7.2: Lưu kết quả ra file chapter.json theo đúng hợp đồng.
    Tự động tạo thư mục cha nếu chưa tồn tại.
    """
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    data_to_dump = chapter.model_dump() if isinstance(chapter, ChapterModel) else chapter
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_to_dump, f, ensure_ascii=False, indent=2)


# =====================================================================
# 3. KẾT NỐI GEMINI API & CƠ CHẾ RETRY TỐI ĐA 2 LẦN (MỤC 7.2, 9, 11)
# =====================================================================

def call_gemini_api(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    """
    Gọi Google Gemini API sinh dữ liệu JSON theo prompt.
    API key được lấy từ biến môi trường GEMINI_API_KEY (.env).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or "your_gemini_api_key_here" in api_key:
        raise ValueError(
            "Chưa cấu hình GEMINI_API_KEY hợp lệ trong file .env! "
            "Vui lòng thêm GEMINI_API_KEY=AIzaSy... vào .env trước khi gọi API."
        )

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text


def parse_and_validate_part(part_num: int, raw_text: str) -> Union[Part1FillBlank, Part2Matching, Part3Quiz]:
    """
    Loại bỏ code fence, parse JSON và kiểm tra schema Pydantic cho từng phần.
    """
    cleaned_json_str = strip_markdown_fence(raw_text)
    data = json.loads(cleaned_json_str)

    # Đảm bảo trường part và game khớp với phần đang xử lý
    if part_num == 1:
        if "part" not in data:
            data["part"] = 1
        if "game" not in data:
            data["game"] = "fill_blank"
        return Part1FillBlank(**data)
    elif part_num == 2:
        if "part" not in data:
            data["part"] = 2
        if "game" not in data:
            data["game"] = "matching"
        return Part2Matching(**data)
    elif part_num == 3:
        if "part" not in data:
            data["part"] = 3
        if "game" not in data:
            data["game"] = "quiz"
        return Part3Quiz(**data)
    else:
        raise ValueError(f"part_num không hợp lệ: {part_num}")


def generate_part_with_retry(
    part_num: int,
    subject: str,
    text_part: str,
    max_retries: int = 2,
    custom_caller: Optional[Callable[[str], str]] = None
) -> Union[Part1FillBlank, Part2Matching, Part3Quiz]:
    """
    Quy tắc 7.2 & 6.2: Gọi AI sinh dữ liệu cho từng phần; retry tối đa 2 lần nếu JSON sai hoặc không hợp lệ.
    
    Tham số:
    - part_num: 1 (fill_blank), 2 (matching), hoặc 3 (quiz)
    - subject: 'english' hoặc 'philosophy'
    - text_part: 1/3 nội dung văn bản sạch tương ứng
    - max_retries: Số lần thử lại tối đa khi lỗi (mặc định 2 lần theo báo cáo)
    - custom_caller: Hàm gọi AI tùy chỉnh (dùng cho unit test / mock mà không cần tốn quota API)
    """
    from prompts import get_game_prompt

    prompt = get_game_prompt(part_num, subject, text_part)
    caller = custom_caller or call_gemini_api

    last_error = None
    # Tổng số lần thử = 1 lần đầu + max_retries lần retry (tổng cộng 3 lần gọi)
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

    raise RuntimeError(
        f"Không thể sinh dữ liệu hợp lệ cho Phần {part_num} sau {max_retries} lần thử lại. Chi tiết lỗi: {last_error}"
    )


def generate_chapter(
    clean_text: str,
    subject: str,
    chapter_title: str = "Chương ôn tập",
    output_path: str = "chapter.json",
    max_retries: int = 2,
    custom_caller: Optional[Callable[[str], str]] = None,
    use_fallback_on_failure: bool = True
) -> ChapterModel:
    """
    Hàm tổng thể toàn bộ pipeline Tuần 2 của Sang (Mục 7.2):
    1. Nhận clean_text và subject.
    2. Chia văn bản thành 3 phần logic.
    3. Dùng prompt riêng cho từng game, gọi AI có retry tối đa 2 lần.
    4. Kiểm tra Pydantic toàn diện theo hợp đồng chapter.json (Mục 6.1, 6.2).
    5. Lưu kết quả ra file chapter.json.
    6. Nếu gặp lỗi bất khả kháng (API ngắt kết nối/hết quota) và use_fallback_on_failure=True,
       sẽ nạp dữ liệu mẫu dự phòng theo Mục 11 & TC08.
    """
    subject_norm = subject.strip().lower()
    if subject_norm not in ["english", "philosophy"]:
        raise ValueError("subject chỉ nhận giá trị 'english' hoặc 'philosophy'")

    if not clean_text or not clean_text.strip():
        raise ValueError("clean_text không được để trống")

    parts_text = split_text_into_three_parts(clean_text)

    try:
        part1 = generate_part_with_retry(1, subject_norm, parts_text[0], max_retries, custom_caller)
        part2 = generate_part_with_retry(2, subject_norm, parts_text[1], max_retries, custom_caller)
        part3 = generate_part_with_retry(3, subject_norm, parts_text[2], max_retries, custom_caller)

        chapter = ChapterModel(
            subject=subject_norm,
            chapter_title=chapter_title,
            parts=[part1, part2, part3]
        )

        # Lưu file kết quả
        save_chapter_to_file(chapter, output_path)
        return chapter

    except Exception as e:
        logger.error(f"Lỗi trong quá trình sinh chapter: {e}")
        # Mục 11 & TC08: Fallback sang JSON mẫu dự phòng khi API lỗi
        if use_fallback_on_failure:
            fallback_sample_path = os.path.join("data", "sample_chapter.json")
            if os.path.exists(fallback_sample_path):
                logger.info(f"Kích hoạt cơ chế dự phòng: Tải dữ liệu từ {fallback_sample_path}")
                fallback_chapter = load_chapter_from_file(fallback_sample_path)
                save_chapter_to_file(fallback_chapter, output_path)
                return fallback_chapter
        raise e
