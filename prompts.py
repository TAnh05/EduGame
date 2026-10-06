
# ==========================================
# 1. PROMPTS DÀNH CHO PHẦN 1: ĐIỀN VÀO CHỖ TRỐNG (fill_blank)
# ==========================================

PROMPT_PART1_FILL_BLANK_PHILOSOPHY = """
Bạn là chuyên gia giảng dạy Triết học Mác - Lênin.
Nhiệm vụ: Đọc kỹ đoạn văn bản dưới đây và trích xuất dữ liệu để tạo trò chơi "Điền vào chỗ trống".

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
      "id": "p1-01",
      "sentence": "Vật chất là phạm trù triết học chỉ ___ khách quan được đem lại cho con người trong cảm giác.",
      "answer": "thực tại"
    }},
    {{
      "id": "p1-02",
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
Task: Read the provided text and extract data to create a "Fill in the Blank" game.

STRICT RULES:
1. ONLY use information from the provided text below. DO NOT make up information.
2. Each 'sentence' MUST contain EXACTLY ONE blank denoted as '___' (three underscores).
3. 'answer' is the exact word/phrase that fills '___', non-empty.
4. Return ONLY valid JSON matching the format below. No greetings or explanations.

JSON STRUCTURE:
{{
  "part": 1,
  "game": "fill_blank",
  "items": [
    {{
      "id": "p1-01",
      "sentence": "She ___ lived in Hanoi since 2020.",
      "answer": "has"
    }},
    {{
      "id": "p1-02",
      "sentence": "They have ___ finished their homework.",
      "answer": "already"
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
Nhiệm vụ: Đọc kỹ đoạn văn bản dưới đây và trích xuất dữ liệu để tạo trò chơi "Nối từ".

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
      "id": "p2-01",
      "term": "Vật chất",
      "definition": "Thực tại khách quan tồn tại độc lập với ý thức con người."
    }},
    {{
      "id": "p2-02",
      "term": "Vận động",
      "definition": "Mọi sự biến đổi nói chung, là phương thức tồn tại của vật chất."
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
Task: Read the provided text and extract data to create a "Matching" game.

STRICT RULES:
1. ONLY use terms and definitions found in the text below. DO NOT invent terms.
2. 'term' is the keyword, vocabulary word, or grammar term (non-empty).
3. 'definition' is the meaning, explanation, or Vietnamese translation (non-empty).
4. Return ONLY valid JSON matching the format below. No greetings or explanations.

JSON STRUCTURE:
{{
  "part": 2,
  "game": "matching",
  "items": [
    {{
      "id": "p2-01",
      "term": "since",
      "definition": "used with a specific point in time in the past"
    }},
    {{
      "id": "p2-02",
      "term": "for",
      "definition": "used with a period of time"
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
Nhiệm vụ: Đọc kỹ đoạn văn bản dưới đây và soạn câu hỏi trắc nghiệm để tạo trò chơi "Trắc nghiệm".

QUY TẮC BẮT BUỘC:
1. CHỈ sử dụng nội dung có trong văn bản được cung cấp bên dưới, TUYỆT ĐỐI không bịa đặt.
2. 'q' là câu hỏi lý thuyết rõ ràng, bám sát văn bản (không rỗng).
3. 'options' BẮT BUỘC có ĐÚNG 4 phương án lựa chọn dạng chuỗi (không để trống bất kỳ phương án nào).
4. 'answer' là CHỈ SỐ SỐ NGUYÊN (0, 1, 2, hoặc 3) chỉ vị trí của đáp án đúng trong mảng 'options'.
5. Trả về ĐÚNG định dạng JSON theo mẫu bên dưới, KHÔNG kèm bất kỳ lời chào hay giải thích nào.

CẤU TRÚC JSON YÊU CẦU:
{{
  "part": 3,
  "game": "quiz",
  "items": [
    {{
      "id": "p3-01",
      "q": "Theo quan điểm duy vật biện chứng, mối quan hệ giữa vật chất và ý thức là gì?",
      "options": [
        "Ý thức quyết định vật chất",
        "Vật chất quyết định ý thức, ý thức tác động trở lại vật chất",
        "Vật chất và ý thức độc lập hoàn toàn",
        "Vật chất và ý thức là một"
      ],
      "answer": 1
    }},
    {{
      "id": "p3-02",
      "q": "Phương thức tồn tại của vật chất là gì?",
      "options": [
        "Đứng im",
        "Cảm giác",
        "Ý chí",
        "Vận động"
      ],
      "answer": 3
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
Task: Read the provided text and create multiple-choice questions for a "Quiz" game.

STRICT RULES:
1. ONLY base questions and answers on the provided text. DO NOT invent information.
2. 'q' is the question string (non-empty).
3. 'options' MUST contain EXACTLY 4 string choices (no empty choices).
4. 'answer' MUST be an INTEGER index (0, 1, 2, or 3) representing the correct option's position in 'options'.
5. Return ONLY valid JSON matching the format below. No greetings or explanations.

JSON STRUCTURE:
{{
  "part": 3,
  "game": "quiz",
  "items": [
    {{
      "id": "p3-01",
      "q": "Which sentence uses the Present Perfect correctly?",
      "options": [
        "She has lived here since five years.",
        "She has lived here for five years.",
        "She lives here for five years.",
        "She have lived here for five years."
      ],
      "answer": 1
    }},
    {{
      "id": "p3-02",
      "q": "I haven't finished my report ___.",
      "options": [
        "already",
        "ago",
        "yet",
        "since"
      ],
      "answer": 2
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
    Hàm trả về prompt tương ứng cho từng phần (game) và môn học.
    Mỗi phần nhận đúng 1/3 văn bản sạch đã được chia từ trước (Mục 7.2).

    - part_num = 1: fill_blank  (nhận phần 1 của văn bản)
    - part_num = 2: matching    (nhận phần 2 của văn bản)
    - part_num = 3: quiz        (nhận phần 3 của văn bản)
    - subject: 'philosophy' hoặc 'english'
    - text_part: 1/3 văn bản sạch tương ứng với phần này
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

    raise ValueError(f"Không hỗ trợ môn học '{subject}' hoặc phần '{part_num}'.")
