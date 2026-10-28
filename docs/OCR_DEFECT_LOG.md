# Defect log và rủi ro còn lại

| ID | Phân loại | Bằng chứng trước sửa | Khắc phục / test |
|---|---|---|---|
| D01 | Tái hiện, môi trường/import | Baseline discovery lỗi 3 module do config import torch | Lazy engine, core dependency profile, test_imports |
| D02 | Tái hiện, UI | PDF continue trước nút chuyển; ảnh chỉ ghi session_state | Adapter gọi consumer, UI chung, AppTest ảnh/PDF |
| D03 | Tái hiện, stale state | Widget text key tồn tại qua extraction mới | Generation/context và review theo digest; AppTest |
| D04 | Tái hiện, IO | run_pipeline([corrupt bytes]) raise ValueError ra caller | Failure contract và test_resource_safety |
| D05 | Tái hiện, chẩn đoán | Lỗi trang sau ghi đè reason trang trước | Tổng hợp reason và per_page; giữ pages rỗng tại trang lỗi |
| D06 | Tái hiện, EXIF | PNG không EXIF vẫn cảnh báo đã xoay vì ImageOps trả copy | Đọc orientation tag, test PNG/JPEG orientation=6 |
| D07 | Tái hiện, cờ cấu hình | perspective/strip_target_lines đổi nhưng không có hiệu lực | Từ chối cấu hình chưa hỗ trợ; không thêm transform |
| D08 | Tái hiện, memory/OOM giả lập | Weakref tensor lỗi còn sống lúc fallback tạo tensor mới | Phạm vi tensor riêng và retry ngoài except; test_inference_mock |
| D09 | Tái hiện, đánh giá | Dataset rỗng trả CER=0; thiếu truth bị bỏ qua | Fail rõ trước inference, test_eval |
| R01 | Rủi ro tĩnh | PDF trước đây render tất cả trang vào list | Pipeline dùng iterator; benchmark render-only và test đóng handles |
| R02 | Rủi ro tĩnh | Cache toàn cục có thể nạp đôi khi concurrent | RLock và test concurrent loader bằng model giả |
| R03 | Chưa đủ bằng chứng | Model revision=None và trust_remote_code=True | Cảnh báo; chưa pin SHA chưa được review, production còn bị chặn |
| R04 | Chưa đủ bằng chứng | CER/false reject thật, GPU OOM/VRAM, nhiều người dùng | Cần GPU, weights/revision đã review, dữ liệu có consent + truth |
| R05 | Chưa tích hợp ngoài phạm vi | Consumer game thật không có trong nhánh OCR | Interface và fake consumer đã test; nhóm game cần nối callback thật |

Không dùng việc mock pass để đóng R03–R05. Các thay đổi không nới quality gate hoặc đổi model/prompt/dtype/tiles mặc định.
