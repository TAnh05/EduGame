"""
ai_generate.py
Module xử lý trích xuất văn bản, sinh câu hỏi ôn tập bằng AI và thẩm định Schema JSON bằng Pydantic.

Quy trình xử lý:
1. Đầu vào: Văn bản thô (clean_text) và tên môn học (subject: 'english' | 'philosophy').
2. Tiền xử lý: Kiểm tra độ dài, cắt tỉa an toàn và phân đoạn thành 3 phần cho 3 game.
3. Sinh dữ liệu: Tích hợp Gemini API với prompt chuyên biệt cho từng loại game.
4. Thẩm định (Validation): Kiểm tra tính hợp lệ của cấu trúc JSON bằng Pydantic.
5. Khả năng chịu lỗi: Cơ chế retry tối đa 2 lần khi dữ liệu sai format và fallback mẫu dự phòng.
6. Đầu ra: Lưu kết quả chuẩn hóa ra file chapter.json phục vụ các module trò chơi.
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


# 1. KHUNG KIỂM TRA PYDANTIC

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


# 2. XỬ LÝ VĂN BẢN & LOẠI BỎ CODE FENCE

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


def split_text_into_three_parts(text: str) -> List[str]:
    """
    Chia văn bản thành 3 phần logic cho 3 game.
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


def save_chapter_to_file(chapter: Union[ChapterModel, dict], file_path: str = "chapter.json") -> None:
    """
    Lưu kết quả ra file chapter.json theo đúng hợp đồng.
    Tự động tạo thư mục cha nếu chưa tồn tại.
    """
    dir_name = os.path.dirname(file_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    data_to_dump = chapter.model_dump() if isinstance(chapter, ChapterModel) else chapter
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_to_dump, f, ensure_ascii=False, indent=2)


# 3. KẾT NỐI GEMINI API, XỬ LÝ LỖI & CA NGOẠI LỆ

# Giới hạn độ dài văn bản để tiết kiệm chi phí & tránh timeout
MIN_TEXT_LENGTH = 50         # Tối thiểu 50 ký tự (TC04: kiểm tra văn bản đủ dài)
MAX_TEXT_LENGTH = 15000      # Tối đa 15.000 ký tự (TC06)


class AIProcessingError(RuntimeError):
    """Lỗi xử lý trong pipeline AI (thông báo tiếng Việt thân thiện theo Yêu cầu 2.2)"""
    pass


def validate_input_text(clean_text: str) -> str:
    """
    Kiểm tra tính hợp lệ của văn bản đầu vào theo các ca kiểm thử:
    - TC05: File rỗng / văn bản rỗng
    - TC04: Văn bản quá ngắn hoặc không đọc được
    - TC06: Giới hạn độ dài văn bản quá lớn
    """
    if not clean_text or not clean_text.strip():
        raise AIProcessingError("Lỗi (TC05): Văn bản đầu vào rỗng. Vui lòng cung cấp nội dung tài liệu học tập.")

    text_stripped = clean_text.strip()
    if len(text_stripped) < MIN_TEXT_LENGTH:
        raise AIProcessingError(
            f"Lỗi (TC04): Văn bản quá ngắn ({len(text_stripped)} ký tự < {MIN_TEXT_LENGTH} ký tự tối thiểu). "
            "Không đủ nội dung để tạo 3 trò chơi ôn tập. Vui lòng tải tài liệu đầy đủ hơn."
        )

    # Giới hạn độ dài an toàn: Tự động cắt tỉa để tránh quá tải/hết quota
    if len(text_stripped) > MAX_TEXT_LENGTH:
        logger.warning(
            f"Cảnh báo (TC06): Văn bản vượt quá giới hạn ({len(text_stripped)} > {MAX_TEXT_LENGTH} ký tự). "
            "Hệ thống sẽ tự động cắt tỉa lấy đoạn đầu phù hợp để tiết kiệm quota API và tránh timeout."
        )
        text_stripped = text_stripped[:MAX_TEXT_LENGTH]

    return text_stripped


def call_gemini_api(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
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

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Lỗi khi gọi Gemini API: {e}")
        raise AIProcessingError(f"Lỗi kết nối Gemini API (TC08): {str(e)}")


def parse_and_validate_part(part_num: int, raw_text: str) -> Union[Part1FillBlank, Part2Matching, Part3Quiz]:
    """
    Loại bỏ code fence, parse JSON và kiểm tra schema Pydantic cho từng phần.
    """
    cleaned_json_str = strip_markdown_fence(raw_text)
    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as jde:
        raise AIProcessingError(f"AI trả về dữ liệu không phải cú pháp JSON: {jde}")

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
    Quy tắc nghiệp vụ: Gọi AI sinh dữ liệu cho từng phần; retry tối đa 2 lần nếu JSON sai hoặc không hợp lệ.
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
    """
    Hàm điều phối toàn bộ pipeline sinh câu hỏi ôn tập:
    1. Kiểm tra văn bản đầu vào: rỗng (TC05), quá ngắn (TC04), quá dài (TC06).
    2. Cơ chế Cache (F09): Nếu file output đã tồn tại và hợp lệ, nạp lại không gọi AI.
    3. Chia 3 phần logic, gọi prompt với retry tối đa 2 lần (TC07).
    4. Thẩm định Pydantic schema hợp đồng JSON.
    5. Lưu kết quả ra file chapter.json.
    6. Cơ chế Fallback an toàn (TC08): Nạp sample_chapter.json nếu API bị sự cố.
    """
    subject_norm = subject.strip().lower()
    if subject_norm not in ["english", "philosophy"]:
        raise ValueError("subject chỉ nhận giá trị 'english' hoặc 'philosophy'")

    # Kiểm tra ca biên của văn bản đầu vào (TC04, TC05, TC06)
    valid_text = validate_input_text(clean_text)

    # Cơ chế Cache (F09): Đọc JSON đã có để không tốn quota gọi lại
    if use_cache and os.path.exists(output_path):
        try:
            cached_chapter = load_chapter_from_file(output_path)
            if cached_chapter.subject == subject_norm:
                logger.info(f"Đã tìm thấy cache hợp lệ tại {output_path}. Tái sử dụng để tiết kiệm API quota (F09).")
                return cached_chapter
        except Exception:
            logger.warning(f"Cache tại {output_path} không hợp lệ, tiến hành gọi AI sinh mới.")

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

        # Lưu file kết quả
        save_chapter_to_file(chapter, output_path)
        return chapter

    except Exception as e:
        logger.error(f"Lỗi trong quá trình sinh chapter: {e}")
        # Fallback sang JSON mẫu dự phòng khi API lỗi (TC08)
        if use_fallback_on_failure:
            fallback_sample_path = os.path.join("data", "sample_chapter.json")
            if os.path.exists(fallback_sample_path):
                logger.info(f"Kích hoạt cơ chế dự phòng (TC08): Tải dữ liệu mẫu từ {fallback_sample_path}")
                fallback_chapter = load_chapter_from_file(fallback_sample_path)
                save_chapter_to_file(fallback_chapter, output_path)
                return fallback_chapter
        raise e


# 4. HỖ TRỢ GAME CUỐI THEO TỶ LỆ 3-3-4

def create_final_quiz_pool(chapter: ChapterModel, num_part1: int = 3, num_part2: int = 3, num_part3: int = 4) -> List[dict]:
    """
    Game cuối lấy ngẫu nhiên khoảng 10 câu theo tỷ lệ 3–3–4 từ ba phần
    và chuyển sang dạng trắc nghiệm.
    Việc ánh xạ item gốc sang quiz cuối cần lưu id nguồn hoặc thông tin phần/câu
    để truy nguyên câu sai trong màn hình tổng kết.
    """
    import random

    p1_items = chapter.parts[0].items
    p2_items = chapter.parts[1].items
    p3_items = chapter.parts[2].items

    final_pool = []

    # 1. Lấy từ Phần 1 (Điền từ -> Chuyển thành quiz với đáp án đúng là answer)
    sample_p1 = random.sample(p1_items, min(num_part1, len(p1_items)))
    all_answers_p1 = [it.answer for it in p1_items]
    for it in sample_p1:
        # Tạo distractors từ các câu khác trong cùng chương
        distractors = [ans for ans in all_answers_p1 if ans != it.answer]
        while len(distractors) < 3:
            distractors.append(f"Lựa chọn khác {len(distractors) + 1}")
        chosen_distractors = random.sample(distractors, 3)
        options = [it.answer] + chosen_distractors
        random.shuffle(options)
        final_pool.append({
            "source_part": 1,
            "source_id": it.id,
            "q": f"Điền từ vào chỗ trống: {it.sentence}",
            "options": options,
            "answer": options.index(it.answer)
        })

    # 2. Lấy từ Phần 2 (Nối từ -> Chuyển thành quiz hỏi định nghĩa của term)
    sample_p2 = random.sample(p2_items, min(num_part2, len(p2_items)))
    all_defs_p2 = [it.definition for it in p2_items]
    for it in sample_p2:
        distractors = [d for d in all_defs_p2 if d != it.definition]
        while len(distractors) < 3:
            distractors.append(f"Định nghĩa khác {len(distractors) + 1}")
        chosen_distractors = random.sample(distractors, 3)
        options = [it.definition] + chosen_distractors
        random.shuffle(options)
        final_pool.append({
            "source_part": 2,
            "source_id": it.id,
            "q": f"Khái niệm '{it.term}' có định nghĩa là gì?",
            "options": options,
            "answer": options.index(it.definition)
        })

    # 3. Lấy từ Phần 3 (Quiz gốc)
    sample_p3 = random.sample(p3_items, min(num_part3, len(p3_items)))
    for it in sample_p3:
        final_pool.append({
            "source_part": 3,
            "source_id": it.id,
            "q": it.q,
            "options": it.options,
            "answer": it.answer
        })

    return final_pool
