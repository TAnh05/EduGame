# Kiến trúc OCR và các quyết định

## Sơ đồ module

```mermaid
flowchart TD
    User[Người học] --> UI[Streamlit UI và trạng thái editor]
    UI --> Pipeline[run_pipeline]
    Pipeline --> IO[IO và giới hạn tài nguyên]
    IO --> PDF[PDFium render từng trang]
    IO --> Image[Pillow và EXIF]
    Pipeline --> Pre[Preprocessing và input quality gate]
    Pipeline --> Engine[Vintern - cache và lock]
    Pipeline --> Post[Postprocess và output gate]
    Post --> Result[OCRResult và metrics từng trang]
    Result --> UI
    UI --> Adapter[deliver_text - context, review và text gate]
    Adapter --> Consumer[Consumer do nhóm game cung cấp]
    Consumer --> String[Văn bản thuần string]
```

## Luồng OCR → Game

```mermaid
sequenceDiagram
    actor Learner as Người học
    participant UI as Streamlit
    participant P as Pipeline
    participant IO as PDF/Image IO
    participant M as Vintern
    participant H as Handoff adapter
    participant G as Game consumer
    Learner->>UI: Upload, chọn trang/config/góc
    UI->>UI: Invalidate kết quả và payload cũ
    UI->>P: run_pipeline(source, cfg, range)
    loop Từng trang trong phạm vi và giới hạn
        P->>IO: Decode hoặc render một trang
        IO-->>P: Ảnh độc lập và đóng PDFium page/bitmap
        P->>P: Preprocess và input gate
        alt Ảnh đạt gate
            P->>M: Inference dưới lock
            M-->>P: Raw text hoặc lỗi
            P->>P: Postprocess và output gate
        else Không đạt
            P->>P: Ghi lỗi trang, không gọi model
        end
    end
    P-->>UI: OCRResult giữ cả lỗi và chẩn đoán
    Learner->>UI: Kiểm tra, có thể sửa text
    opt Đã sửa hoặc OCR bị từ chối
        Learner->>UI: Xác nhận thủ công bản hiện tại
    end
    UI->>H: result, text, context, reviewed, callback
    H->>H: Chặn stale/rỗng/chưa review/text gate fail
    alt Dữ liệu hợp lệ và có consumer
        H->>G: consume(text: str)
        G-->>H: Return hoặc raise
        H-->>UI: Thành công chỉ sau return
    else Chưa đủ điều kiện
        H-->>UI: Lỗi rõ ràng, không chuyển
    end
```

## Mô hình dữ liệu nội bộ

```mermaid
classDiagram
    class OCRResult {
        str text
        bool ok
        str reason
        list warnings
        list pages
        dict metrics
        Image processed_preview
    }
    class ResourceLimits {
        int max_file_bytes
        int max_page_pixels
        int max_pages
    }
    class UIState {
        str context
        str result_context
        str user_text
        int generation
        int rot
    }
    UIState --> OCRResult : kết quả hiện tại
    ResourceLimits --> OCRResult : giới hạn xử lý
```

Không có bảng database trong phân hệ này nên không tạo ERD giả. Nhóm tổng thể chịu trách nhiệm ERD nếu có lưu tiến độ hoặc tài khoản.

## ADR

| Quyết định | Lý do và hệ quả |
|---|---|
| Giữ Streamlit và Python callback | Đủ cho phạm vi OCR cục bộ, consumer chỉ phụ thuộc str. Không thêm API server/framework/DB/Docker khi chưa có nhu cầu triển khai tương ứng. |
| Giữ bảy trường OCRResult | Tất cả consumer hiện có nằm trong pipeline, UI, CLI và eval; contract test giữ defaults. metrics bổ sung per_page, giữ khóa trang cuối cho caller cũ. |
| PDF iterator và resource guard | Giới hạn RAM raster; ảnh đầu vào vẫn render cùng scale. List API cũ vẫn tồn tại để tương thích. |
| Lock quanh cache và inference | Tránh nạp đôi model hoặc session thay cache khi session khác dùng. Đánh đổi: throughput cùng process bị tuần tự, chưa có benchmark nhiều người dùng. |
| Giữ nguyên ngưỡng/thuật toán OCR | Chưa có paired evaluation trên dữ liệu thật để chọn default khác. Perspective chưa triển khai sẽ báo lỗi khi bật. strip_target_lines là trường dự phòng, đổi khỏi 15 sẽ báo lỗi. |
| Dùng Mermaid cho sơ đồ | Tài liệu quy trình cho phép PlantUML; LuuY yêu cầu sửa bằng Mermaid. Chọn Mermaid để đáp ứng yêu cầu chấm cụ thể hơn. |

Rủi ro chưa giải quyết: mặc định resize 1600 có thể khiến strip threshold 2400 không được chạm tới; khử lặp có thể xóa nội dung lặp hợp lệ; threshold chưa hiệu chuẩn. Các điểm này cần dữ liệu có nhãn, không tự đổi thuật toán theo suy đoán.
