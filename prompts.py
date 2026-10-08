"""Prompt cho từng môn và từng phần. Luôn yêu cầu: chỉ dùng văn bản đã cho, chỉ trả JSON."""

PROMPTS = {
    "english": {
        1: "Bạn là giáo viên tiếng Anh. Dựa CHỈ trên văn bản bên dưới, hãy tạo 8 câu điền vào chỗ trống. "
           "Mỗi câu có đúng 1 chỗ trống ký hiệu ___ .\n"
           'Chỉ trả về JSON hợp lệ, theo mẫu: {{"items": [{{"sentence": "She ___ to Paris.", "answer": "went"}}]}}\n'
           "VĂN BẢN:\n{text}",
        2: "TODO",
        3: "TODO",
    },
    "philosophy": {
        1: "TODO",
        2: "TODO",
        3: "TODO",
    },
}
