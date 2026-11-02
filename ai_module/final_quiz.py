"""
final_quiz.py
Thuật toán tổng hợp câu hỏi Game cuối theo tỷ lệ 3-3-4 (Mục 6.3 trong Báo cáo).
"""

import random
from typing import List
from .models import ChapterModel


def create_final_quiz_pool(chapter: ChapterModel, num_part1: int = 3, num_part2: int = 3, num_part3: int = 4) -> List[dict]:
    """
    Game cuối lấy ngẫu nhiên khoảng 10 câu theo tỷ lệ 3–3–4 từ ba phần
    và chuyển sang dạng trắc nghiệm.
    Việc ánh xạ item gốc sang quiz cuối cần lưu id nguồn hoặc thông tin phần/câu
    để truy nguyên câu sai trong màn hình tổng kết.
    """
    p1_items = chapter.parts[0].items
    p2_items = chapter.parts[1].items
    p3_items = chapter.parts[2].items

    final_pool = []

    # 1. Lấy từ Phần 1 (Điền từ -> Chuyển thành quiz với đáp án đúng là answer)
    sample_p1 = random.sample(p1_items, min(num_part1, len(p1_items)))
    all_answers_p1 = [it.answer for it in p1_items]
    for it in sample_p1:
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
