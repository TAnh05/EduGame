---
name: codebase-graphify
description: Kiểm soát đồ thị phụ thuộc (Dependency Graph / Call Hierarchy), ngăn chặn import vòng tròn và duy trì kiến trúc phân tầng sạch
author: Sang
version: 1.0.0
tags: [architecture, graphify, dependency-graph, clean-code, refactoring]
---

# SKILL: CODEBASE GRAPH MANAGEMENT (GRAPHIFY)

## 1. MỤC TIÊU VÀ PHẠM VI
Skill này đóng vai trò Codebase Graph Manager, đảm bảo cấu trúc dự án tuân thủ kiến trúc phân tầng sạch (Clean Architecture), ngăn chặn triệt để hiện tượng import vòng tròn (circular dependencies) giữa các module.

---

## 2. SƠ ĐỒ ĐỒ THỊ PHỤ THUỘC (DEPENDENCY CALL GRAPH)

Luồng phụ thuộc trong dự án bắt buộc phải đi theo một chiều (hướng xuống), không được phép import ngược lại:

```text
[ demo.py / External UI ] (Pipeline Runner / Entrypoint)
    │
    ▼
[ ai_generate.py ] (Facade Entrypoint)
    │
    ▼
[ ai_module/pipeline.py ] (Pipeline Orchestration)
    │
    ├──► [ ai_module/models.py ] (Pydantic V2 Schemas)
    ├──► [ ai_module/gemini_client.py ] (Gemini API & Code Fence Stripping)
    ├──► [ ai_module/final_quiz.py ] (3-3-4 Final Quiz Aggregator)
    ├──► [ prompts.py ] (Prompt Templates & Few-Shot Examples)
    └──► [ data/sample_chapter.json ] (Fallback Store)

[ test_1.py, test_2.py, test_3.py ] (Testing Suite)
    │
    ▼
[ ai_generate.py / ai_module ] (Kiểm thử độc lập qua Mock Callers)
```

---

## 3. CÁC NGUYÊN TẮC BẢO VỆ KIẾN TRÚC

1. **Không Import Vòng Tròn (No Circular Import):**
   - `ai_module/pipeline.py` import hàm `get_game_prompt` từ `prompts.py`.
   - `prompts.py` TUYỆT ĐỐI KHÔNG ĐƯỢC import ngược lại bất kỳ module nào từ `ai_module` hay `ai_generate.py`.
2. **Kiến Trúc Phân Tầng Độc Lập (Layered Architecture):**
   - `models.py`: Tầng dữ liệu thuần túy (Data Layer), độc lập hoàn toàn, không phụ thuộc vào Gemini hay mạng.
   - `gemini_client.py`: Tầng giao tiếp ngoại vi (Infrastructure Layer), chỉ lo kết nối API.
   - `pipeline.py`: Tầng nghiệp vụ điều phối (Service Layer).
   - `ai_generate.py`: Tầng cổng mặt tiền (Facade Layer).
   - `demo.py`: Chỉ chịu trách nhiệm giao diện console và gọi hàm điều phối, không can thiệp sâu vào thuật toán nội bộ.
3. **Mocking Độc Lập Khi Test:**
   - Các file test sử dụng tham số `custom_caller` để truyền hàm giả lập, không phụ thuộc vào kết nối mạng thật khi chạy test suite.
