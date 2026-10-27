# Bàn giao văn bản OCR cho nhóm game

## Interface

`main(text_consumer: Callable[[str], None] | None = None)` trong `ocr_module.ui_upload` là điểm nhúng UI.
Consumer là hàm đồng bộ nhận duy nhất một `str`, trả về sau khi nhận dữ liệu hoặc raise exception nếu nhận thất bại.
Không cần import Vintern, torch, PIL hay `OCRResult` trong consumer của game.

```python
from ocr_module.ui_upload import main

def accept_learning_text(text: str) -> None:
    # Nhóm game nối hàm thật của mình ở đây; raise nếu không nhận được.
    receive_text_in_game_module(text)

main(text_consumer=accept_learning_text)
```

`receive_text_in_game_module` là điểm nối do nhóm game cung cấp, không được triển khai trong phân hệ OCR.
Khi chạy `streamlit run app.py` độc lập, nút chuyển bị vô hiệu hóa vì chưa có consumer.
UI chỉ báo nhận thành công sau khi callback trả về. Điều này chưa chứng minh sinh câu hỏi hoặc game đã chạy.
`game_raw_text` được cập nhật để tương thích sau khi callback thành công, không dùng làm bằng chứng giao nhận.

## Điều kiện chuyển

- `OCRResult` giữ nguyên bảy trường, kiểu và default. `ok` biểu thị kiểm tra OCR; xác nhận tay không sửa `ok` thành True.
- `deliver_text(...)` kiểm tra context file/config/góc xoay/phạm vi PDF khớp kết quả hiện tại.
- Chuỗi phải không rỗng và qua `validate_extracted_text`; không tự dọn hoặc sửa bản người dùng đã xác nhận.
- Bất kỳ sửa tay hoặc `result.ok=False` đều cần checkbox xác nhận đúng nội dung hiện tại.
- Xác nhận không bỏ qua gate văn bản. Ví dụ PDF có trang lỗi: người dùng phải kiểm tra bản thiếu trang trước khi xác nhận; nội dung gốc không được coi là đầy đủ.
- Đổi file, cấu hình, góc xoay, phạm vi trang hoặc chạy OCR lại làm mất hiệu lực kết quả cũ. Đổi nội dung làm mất hiệu lực xác nhận cũ.
- Ngoại lệ consumer được hiển thị; không lưu trạng thái giao thành công.

## Kiểm chứng

`tests/test_handoff.py`: contract string, empty/rejected/stale/review/consumer exception.
`tests/test_handoff_integration.py`: PDFium thật → pipeline với OCR mock → receiver nhận string.
`tests/test_ui_handoff.py`: Streamlit AppTest cho ảnh/PDF, sửa tay, context và thay kết quả.
Các test dùng receiver giả; nhóm game cần nối và kiểm thử consumer thật trong nhánh tích hợp của nhóm.
