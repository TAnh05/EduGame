name: ocr-latency-profiling
description: Phân tích thời gian xử lý OCR trong EduGame, xác định giai đoạn gây độ trễ cao và đề xuất cách cải thiện dựa trên số liệu thực tế. Sử dụng khi người dùng yêu cầu kiểm tra OCR chạy chậm hoặc so sánh thời gian xử lý. Không dùng cho việc chỉ chỉnh sửa giao diện hoặc các lỗi không liên quan đến hiệu năng OCR.
Phân tích thời gian xử lý OCR
Mục tiêu
Xác định bước nào trong pipeline OCR tốn nhiều thời gian nhất, tìm nguyên nhân có bằng chứng và đề xuất cải tiến mà không làm giảm chất lượng nhận dạng văn bản.

Giai đoạn 1: Xác định phạm vi
Đọc yêu cầu để xác định vấn đề: OCR chậm ở lần đầu, chậm ở mọi lần, hay chỉ chậm với ảnh/PDF cụ thể.
Kiểm tra các file liên quan:
ocr_module/pipeline.py: điều phối toàn bộ quá trình OCR.
ocr_module/io_utils.py: đọc ảnh và chuyển PDF thành ảnh.
ocr_module/preprocess.py: tiền xử lý ảnh.
ocr_module/quality.py: kiểm tra chất lượng ảnh.
ocr_module/ocr_vintern.py: tải mô hình và nhận dạng văn bản.
ocr_module/postprocess.py: làm sạch và kiểm tra văn bản đầu ra.
ocr_module/config.py: cấu hình của các bước xử lý.
Xác định dữ liệu thử nghiệm, phần cứng CPU/GPU, phiên bản mô hình và cấu hình OCR.
Chưa chỉnh sửa mã nguồn trong giai đoạn này.
Giai đoạn 2: Đo thời gian xử lý
Đo tổng thời gian OCR và, khi có phương tiện đo phù hợp, đo riêng:
Thời gian đọc ảnh hoặc render PDF.
Thời gian tiền xử lý và kiểm tra chất lượng ảnh.
Thời gian tải mô hình Vintern.
Thời gian Vintern nhận dạng văn bản.
Thời gian hậu xử lý văn bản.
Sử dụng cùng dữ liệu, cấu hình và phần cứng khi so sánh. Chạy nhiều lần (ưu tiên ít nhất 3 lần) và ghi lại kết quả thay vì chỉ đo một lần.
Phân biệt lần chạy đầu có thể phải tải mô hình (cold start) với lần chạy khi mô hình đã được tải (warm run).
Nếu đo GPU bằng thời gian thực, cần đồng bộ CUDA phù hợp trước và sau đoạn cần đo để tránh sai lệch do xử lý bất đồng bộ.
Nếu công cụ hiện có chỉ đo tổng thời gian thì phải ghi rõ chưa có số đo riêng từng bước; không tự suy đoán số liệu.
Ghi lại trường hợp bị từ chối, lỗi hoặc hết VRAM (OOM) riêng với các lần OCR hoàn thành bình thường.
Giai đoạn 3: Phân tích nguyên nhân
So sánh các kết quả đo để xác định bước tốn thời gian nhất nếu có số liệu theo từng bước.
Phân biệt rõ điểm nghẽn đã được đo và nguyên nhân mới chỉ là giả thuyết.
Kiểm tra các khả năng phù hợp với bằng chứng: PDF nhiều trang, ảnh quá lớn, tiền xử lý nặng, thời gian tải mô hình, số dải/ô ảnh, số token sinh, lỗi OOM hoặc xử lý văn bản.
Đề xuất phương án giảm thời gian và cách kiểm chứng tác động. Không mặc định giảm chất lượng ảnh hoặc tăng mức xử lý song song sẽ nhanh hơn.
Nếu một phương án có thể ảnh hưởng kết quả nhận dạng, đề xuất so sánh CER trên cùng bộ dữ liệu có đáp án chuẩn bằng Skill ocr-eval-ablation.
Giai đoạn 4: Báo cáo
Báo cáo bằng tiếng Việt, gồm:

Phạm vi: dữ liệu thử nghiệm, cấu hình, môi trường và số lần đo.
Kết quả: thời gian từng giai đoạn (nếu có), tổng thời gian và mức sử dụng RAM/VRAM (nếu đo được).
Phân tích: điểm nghẽn được chứng minh, giả thuyết cần kiểm tra thêm.
Đề xuất: phương án cải tiến, lợi ích dự kiến, rủi ro và cách đánh giá lại.
Giới hạn: những thông tin chưa đo hoặc chưa đủ bằng chứng để kết luận.
Những lưu ý quan trọng
Mặc định chỉ phân tích và báo cáo, không tự ý sửa code, thay đổi API, cấu trúc file, cấu hình mặc định hoặc mô hình Vintern.
Không tự cài thư viện, tải mô hình/dữ liệu mới, hoặc commit/push lên GitHub khi chưa được cho phép.
Chỉ dùng dữ liệu được phép sử dụng; không ghi nội dung tài liệu nhạy cảm vào báo cáo hoặc log.
Không khẳng định một thay đổi giúp OCR nhanh hơn hoặc giữ nguyên CER nếu chưa có kết quả kiểm chứng thực tế.
Nếu môi trường không cho phép chạy benchmark, được phân tích mã nguồn nhưng phải ghi rõ chưa đo thực nghiệm.