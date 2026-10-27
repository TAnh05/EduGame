---
name: pydantic-game-validator
description: Chuyên gia thiết kế, thẩm định Schema dữ liệu và kiểm soát hợp đồng JSON cho 3 mini-game giáo dục bằng Pydantic V2
author: Sang
version: 1.0.0
tags: [backend, pydantic-v2, validation, schema-contract, ai-generate]
---

# SKILL: PYDANTIC GAME VALIDATOR (BACKEND ENGINE)

## 1. MỤC TIÊU VÀ PHẠM VI
Skill này đóng vai trò kiến trúc sư dữ liệu Backend cho module `ai_generate.py`, đảm bảo mọi câu hỏi sinh ra từ AI hoặc người dùng đều phải tuân thủ nghiêm ngặt hợp đồng dữ liệu `chapter.json` trước khi chuyển sang các module trò chơi.

---

## 2. QUY TẮC RÀNG BUỘC CỦA 3 MINI-GAME (PYDANTIC V2)

Mọi Data Model bắt buộc phải kế thừa `pydantic.BaseModel` và sử dụng cú pháp Pydantic V2 (`@field_validator`, `@model_validator`):

### 2.1. Game 1: Điền vào chỗ trống (`FillBlankItem`)
- **Trường dữ liệu:** `id: str`, `sentence: str`, `answer: str`.
- **Ràng buộc `sentence`:**
  - Bắt buộc phải có đúng **MỘT** ký hiệu đục lỗ `___` (3 dấu gạch dưới).
  - Sử dụng logic: `s.count("___") == 1`. Nếu khác 1 (0 chỗ hoặc từ 2 chỗ trở lên) -> ném `ValueError`.
- **Ràng buộc `answer`:**
  - Không được để chuỗi rỗng sau khi `strip()`.

### 2.2. Game 2: Nối từ / Định nghĩa (`MatchingItem`)
- **Trường dữ liệu:** `id: str`, `term: str`, `definition: str`.
- **Ràng buộc:** Cả `term` (thuật ngữ) và `definition` (định nghĩa) đều phải có nội dung chữ, không được để khoảng trắng rỗng.

### 2.3. Game 3: Trắc nghiệm khách quan (`QuizItem`)
- **Trường dữ liệu:** `id: str`, `q: str`, `options: List[str]`, `answer: int`.
- **Ràng buộc `options`:**
  - Bắt buộc danh sách phải có đúng **4 phương án** (`len(options) == 4`).
  - Không phương án nào được để rỗng.
- **Ràng buộc `answer`:**
  - Bắt buộc là số nguyên có giá trị nằm trong tập `[0, 1, 2, 3]` (đại diện cho vị trí đáp án đúng).

---

## 3. CẤU TRÚC HỢP ĐỒNG `chapter.json` (`ChapterModel`)

```json
{
  "subject": "english | philosophy",
  "chapter_title": "string",
  "parts": [
    { "part": 1, "game": "fill_blank", "items": [...] },
    { "part": 2, "game": "matching", "items": [...] },
    { "part": 3, "game": "quiz", "items": [...] }
  ]
}
```

- `subject`: Chỉ nhận giá trị hợp lệ là `"english"` hoặc `"philosophy"`.
- `parts`: Phải chứa đủ 3 phần tương ứng với 3 game.

---

## 4. CƠ CHẾ CHỊU LỖI & PHỤC HỒI (RESILIENCE PATTERNS)

1. **Bóc tách Markdown Code Fence:** AI trả về thường bị bọc bởi ` ```json ... ``` `. Luôn dùng Regex `r"^```(?:json)?\s*([\s\S]*?)\s*```$"` để làm sạch chuỗi trước khi parse.
2. **Cơ chế Retry (Tối đa 2 lần):**
   - Nếu `json.loads` lỗi cú pháp hoặc Pydantic ném `ValidationError`: Ghi `logger.warning`, tăng biến đếm và gọi lại AI.
   - Nếu sau 3 lần gọi (1 lần đầu + 2 lần retry) vẫn thất bại: Ném ngoại lệ `AIProcessingError`.
3. **Cơ chế Fallback an toàn (TC08):**
   - Khi mất kết nối API hoặc hết quota, tự động nạp dữ liệu mẫu từ `data/sample_chapter.json` để hệ thống không bị crash lúc demo.

---

## 5. HƯỚNG DẪN KHI MỞ RỘNG (VIBE CODING PROTOCOL)
Khi người dùng yêu cầu thêm game mới (ví dụ Game 4: `SortingItem`):
1. Định nghĩa Data Model mới kế thừa `BaseModel`.
2. Tạo class Part tương ứng kế thừa `PartBase`.
3. Cập nhật `Union` trong `ChapterModel`.
4. Không được phá vỡ các trường của 3 game cũ.
