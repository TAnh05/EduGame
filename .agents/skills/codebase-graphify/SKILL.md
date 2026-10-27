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
[ demo.py ] (Pipeline Runner / Entrypoint)
    │
    ▼
[ ai_generate.py ] (Core Engine & Pydantic Validation)
    │
    ├────────► [ prompts.py ] (Templates & Few-Shot Examples)
    │
    └────────► [ data/sample_chapter.json ] (Fallback Store)

[ test_1.py, test_2.py, test_3.py ] (Testing Suite)
    │
    ▼
[ ai_generate.py ] (Kiểm thử độc lập qua Mock Callers)
```

---

## 3. CÁC NGUYÊN TẮC BẢO VỆ KIẾN TRÚC

1. **Không Import Vòng Tròn (No Circular Import):**
   - `ai_generate.py` import hàm `get_game_prompt` từ `prompts.py`.
   - `prompts.py` TUYỆT ĐỐI KHÔNG ĐƯỢC import ngược lại bất kỳ class hay hàm nào từ `ai_generate.py`.
2. **Tách Biệt Trách Nhiệm (Single Responsibility Principle):**
   - `prompts.py`: Chỉ chứa chuỗi văn bản kịch bản hướng dẫn AI, không chứa logic gọi API hay logic validate.
   - `ai_generate.py`: Chịu trách nhiệm logic xử lý, kết nối mạng và kiểm định Pydantic.
   - `demo.py`: Chỉ chịu trách nhiệm giao diện console và gọi hàm điều phối, không can thiệp sâu vào thuật toán nội bộ.
3. **Mocking Độc Lập Khi Test:**
   - Các file test sử dụng tham số `custom_caller` để truyền hàm giả lập, không phụ thuộc vào kết nối mạng thật khi chạy test suite.
