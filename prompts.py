"""
prompts.py
Tập hợp các mẫu prompt chuyên biệt cho 3 game (Điền từ, Nối từ, Trắc nghiệm)
dành cho 2 môn học: Tiếng Anh ('english') và Triết học ('philosophy').

Tuân thủ nghiêm ngặt các quy tắc:
1. Chống bịa đặt (Anti-hallucination): Chỉ dùng nội dung văn bản cung cấp.
2. Trả về đúng JSON theo hợp đồng schema dự án.
3. Đúng quy ước game:
   - Part 1 (fill_blank): Có đúng một ký hiệu '___', answer không rỗng.
   - Part 2 (matching): term và definition không rỗng.
   - Part 3 (quiz): Có đúng 4 options, answer là số nguyên 0..3.
"""

# ==========================================
# 1. PROMPTS DÀNH CHO PHẦN 1: ĐIỀN VÀO CHỖ TRỐNG (fill_blank)
# ==========================================

PROMPT_PART1_FILL_BLANK_PHILOSOPHY = """
Bạn là chuyên gia giảng dạy Triết học Mác - Lênin.
Nhiệm vụ: Trích xuất các câu khái niệm, mệnh đề quan trọng từ văn bản được cung cấp để tạo trò chơi "Điền vào chỗ trống".

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng nội dung có trong văn bản được cung cấp bên dưới, TUYỆT ĐỐI không bịa đặt kiến thức ngoài.
2. Mỗi câu hỏi ('sentence') BẮT BUỘC phải chứa ĐÚNG MỘT ký hiệu '___' (ba dấu gạch dưới liên tiếp).
3. 'answer' là từ/cụm từ chính xác cần điền vào chỗ '___', không được để rỗng.
4. Trả về ĐÚNG định dạng JSON theo mẫu bên dưới, KHÔNG kèm bất kỳ lời chào hay giải thích nào.

CẤU TRÚC JSON YÊU CẦU:
{{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {{
      "id": "p1_1",
      "sentence": "Vật chất là một phạm trù triết học dùng để chỉ thực tại ___ được đem lại cho con người trong cảm giác.",
      "answer": "khách quan"
    }},
    {{
      "id": "p1_2",
      "sentence": "Ý thức là hình ảnh chủ quan của thế giới ___.",
      "answer": "khách quan"
    }}
  ]
}}

VĂN BẢN ĐẦU VÀO:
\"\"\"
{text_part}
\"\"\"
"""

PROMPT_PART1_FILL_BLANK_ENGLISH = """
You are an English language teaching specialist.
Task: Create a "Fill in the Blank" game from the provided reading text to test vocabulary and grammar.

STRICT RULES:
1. ONLY use information from the provided text below. DO NOT make up information.
2. Each 'sentence' MUST contain EXACTLY ONE blank denoted as '___' (three underscores).
3. 'answer' is the exact word/phrase that fills '___', non-empty.
4. Return ONLY valid JSON matching the format below. No markdown explanations.

JSON SCHEMA:
{{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {{
      "id": "p1_1",
      "sentence": "The study shows that climate change has a direct ___ on agriculture.",
      "answer": "impact"
    }}
  ]
}}

INPUT TEXT:
\"\"\"
{text_part}
\"\"\"
"""


# ==========================================
# 2. PROMPTS DÀNH CHO PHẦN 2: NỐI TỪ / ĐỊNH NGHĨA (matching)
# ==========================================

PROMPT_PART2_MATCHING_PHILOSOPHY = """
Bạn là chuyên gia giảng dạy Triết học Mác - Lênin.
Nhiệm vụ: Trích xuất các cặp (Thuật ngữ - Định nghĩa) từ văn bản được cung cấp để tạo trò chơi "Nối từ".

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng nội dung có trong văn bản được cung cấp bên dưới, TUYỆT ĐỐI không lấy kiến thức bên ngoài.
2. 'term' là tên khái niệm/phạm trù triết học (ngắn gọn, không rỗng).
3. 'definition' là định nghĩa/ý nghĩa chính xác được nêu trong văn bản (không rỗng).
4. Trả về ĐÚNG định dạng JSON theo mẫu bên dưới, KHÔNG kèm bất kỳ lời chào hay giải thích nào.

CẤU TRÚC JSON YÊU CẦU:
{{
  "part": 2,
  "game": "matching",
  "items": [
    {{
      "id": "p2_1",
      "term": "Vật chất",
      "definition": "Thực tại khách quan tồn tại độc lập với ý thức con người và được ý thức phản ánh."
    }},
    {{
      "id": "p2_2",
      "term": "Thực tiễn",
      "definition": "Toàn bộ hoạt động vật chất - cảm tính có mục đích, mang tính lịch sử - xã hội của con người."
    }}
  ]
}}

VĂN BẢN ĐẦU VÀO:
\"\"\"
{text_part}
\"\"\"
"""

PROMPT_PART2_MATCHING_ENGLISH = """
You are an English language teaching specialist.
Task: Extract pairs of (Term/Vocabulary - Definition/Synonym) from the text to create a "Matching" game.

STRICT RULES:
1. ONLY use terms and definitions found in the text below. DO NOT invent terms.
2. 'term' is the keyword or idiom (non-empty).
3. 'definition' is the meaning, explanation or synonym (non-empty).
4. Return ONLY valid JSON matching the format below.

JSON SCHEMA:
{{
  "part": 2,
  "game": "matching",
  "items": [
    {{
      "id": "p2_1",
      "term": "Sustainable",
      "definition": "Able to be maintained at a certain rate or level without exhausting natural resources."
    }}
  ]
}}

INPUT TEXT:
\"\"\"
{text_part}
\"\"\"
"""


# ==========================================
# 3. PROMPTS DÀNH CHO PHẦN 3: TRẮC NGHIỆM (quiz)
# ==========================================

PROMPT_PART3_QUIZ_PHILOSOPHY = """
Bạn là chuyên gia giảng dạy Triết học Mác - Lênin.
Nhiệm vụ: Soạn các câu hỏi trắc nghiệm 4 lựa chọn từ văn bản được cung cấp để tạo trò chơi "Trắc nghiệm".

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng nội dung có trong văn bản được cung cấp bên dưới, TUYỆT ĐỐI không bịa đặt.
2. 'q' là câu hỏi lý thuyết rõ ràng, bám sát văn bản (không rỗng).
3. 'options' BẮT BUỘC có ĐÚNG 4 phương án lựa chọn dạng chuỗi (không để trống bất kỳ phương án nào).
4. 'answer' là CHỈ SỐ SỐ NGUYÊN (0, 1, 2, hoặc 3) chỉ vị trí của đáp án đúng trong mảng 'options'. (Ví dụ: nếu phương án đầu tiên đúng thì answer là 0).
5. Trả về ĐÚNG định dạng JSON theo mẫu bên dưới, KHÔNG kèm bất kỳ lời chào hay giải thích nào.

CẤU TRÚC JSON YÊU CẦU:
{{
  "part": 3,
  "game": "quiz",
  "items": [
    {{
      "id": "p3_1",
      "q": "Theo quan điểm triết học Mác - Lênin, thuộc tính cơ bản nhất của vật chất là gì?",
      "options": [
        "Tính có thể nhận thức được",
        "Tồn tại khách quan độc lập với ý thức",
        "Tính luôn luôn biến đổi",
        "Có khối lượng và kích thước"
      ],
      "answer": 1
    }}
  ]
}}

VĂN BẢN ĐẦU VÀO:
\"\"\"
{text_part}
\"\"\"
"""

PROMPT_PART3_QUIZ_ENGLISH = """
You are an English language teaching specialist.
Task: Create multiple-choice reading comprehension and grammar questions from the text for a "Quiz" game.

STRICT RULES:
1. ONLY base questions and answers on the provided text.
2. 'q' is the question string (non-empty).
3. 'options' MUST contain EXACTLY 4 string choices.
4. 'answer' MUST be an INTEGER index (0, 1, 2, or 3) representing the index of the correct option in 'options'.
5. Return ONLY valid JSON matching the format below.

JSON SCHEMA:
{{
  "part": 3,
  "game": "quiz",
  "items": [
    {{
      "id": "p3_1",
      "q": "What is the main topic of the reading passage?",
      "options": [
        "Renewable energy solutions",
        "Historical linguistic shifts",
        "Economic recession",
        "Space exploration"
      ],
      "answer": 0
    }}
  ]
}}

INPUT TEXT:
\"\"\"
{text_part}
\"\"\"
"""


def get_game_prompt(part_num: int, subject: str, text_part: str) -> str:
    """
    Hàm tiện ích trả về prompt tương ứng theo từng phần (game) và môn học.
    - part_num = 1: fill_blank
    - part_num = 2: matching
    - part_num = 3: quiz
    - subject: 'philosophy' hoặc 'english'
    """
    subject_norm = subject.strip().lower()
    if subject_norm == "philosophy":
        if part_num == 1:
            return PROMPT_PART1_FILL_BLANK_PHILOSOPHY.format(text_part=text_part)
        elif part_num == 2:
            return PROMPT_PART2_MATCHING_PHILOSOPHY.format(text_part=text_part)
        elif part_num == 3:
            return PROMPT_PART3_QUIZ_PHILOSOPHY.format(text_part=text_part)
    elif subject_norm == "english":
        if part_num == 1:
            return PROMPT_PART1_FILL_BLANK_ENGLISH.format(text_part=text_part)
        elif part_num == 2:
            return PROMPT_PART2_MATCHING_ENGLISH.format(text_part=text_part)
        elif part_num == 3:
            return PROMPT_PART3_QUIZ_ENGLISH.format(text_part=text_part)

    raise ValueError(f"Không hỗ trợ môn học '{subject}' hoặc phần '{part_num}'")
