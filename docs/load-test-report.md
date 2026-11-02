# Edu Game - Báo cáo kiểm thử tải

## Môi trường và điều kiện

- Thời điểm chạy: 2026-11-02.
- Hệ điều hành: Windows 11 `10.0.26100`.
- CPU: Intel64 Family 6 Model 141 Stepping 1; 12 logical CPU.
- RAM vật lý: 7.78 GiB.
- Python: 3.12.10; SQLite: 3.49.1.
- Server: `ThreadingHTTPServer` trong cùng tiến trình, bind `127.0.0.1`; client chạy đồng thời trên loopback.
- Database: file SQLite tạm mới cho mỗi mức tải; journal mode WAL; ghi dùng `BEGIN IMMEDIATE`. Database bị xóa cùng thư mục tạm khi mỗi lần chạy kết thúc.
- Workload: mỗi client dùng session/cookie riêng và hoàn tất Fill Blank (5 câu), Matching (6 cặp), Quiz (5 câu), Final Test (16 câu) với bộ dữ liệu mẫu English.
- Cấu hình áp dụng: 120 POST/phút/session; body tối đa 2 MiB; một worker thread cho mỗi client.
- Mỗi run kiểm tra HTTP status, độ trễ từng request, điểm qua API, kết quả đã lưu trong attempt, số lượng snapshot SQLite, tính riêng biệt session/attempt và WAL. Chỉ số latency là thời gian end-to-end của mỗi request loopback, không phải thời gian xử lý server thuần.

## Kết quả

| Concurrent clients | Requests | Thời gian (s) | Throughput (req/s) | Lỗi HTTP | Error rate | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) | Max (ms) | Audit dữ liệu |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 370 | 2.39 | 154.94 | 0 | 0% | 49.47 | 16.93 | 169.96 | 578.42 | 1301.12 | PASS: 10 session, 10 attempt, 40 snapshot |
| 50 | 1,850 | 11.65 | 158.74 | 0 | 0% | 240.22 | 25.92 | 1788.67 | 3787.34 | 7378.13 | PASS: 50 session, 50 attempt, 200 snapshot |
| 100 | 3,700 | 23.37 | 158.34 | 0 | 0% | 467.02 | 23.74 | 3155.85 | 7527.53 | 16338.68 | PASS: 100 session, 100 attempt, 400 snapshot |

Tất cả request hợp lệ trả HTTP 200. Điểm từng game trong DB khớp với kết quả API; không có attempt/session dùng chung giữa client; mỗi attempt có đủ bốn snapshot game. Không phát hiện lỗi dữ liệu.

Ở mức 100 client, tail latency tăng đáng kể (P95 khoảng 3.16 giây, tối đa khoảng 16.34 giây) dù không có lỗi hoặc sai lệch dữ liệu. Đây là tải cạnh tranh writer SQLite trên một máy Windows/loopback, không đại diện cho môi trường production có reverse proxy hoặc nhiều máy. Cần đo lại trên cấu hình triển khai thật và đặt SLO độ trễ trước khi đánh giá khả năng đáp ứng production.

## Chạy lại

Từ thư mục `Edu_game`:

```powershell
py -3.12 tests\load_test.py --clients 10 50 100
```

Script in cấu hình máy/runtime thực tế và JSON kết quả từng mức. Có thể chạy riêng từng mức, ví dụ:

```powershell
py -3.12 tests\load_test.py --clients 100
```

Mỗi mức tải dùng database tạm riêng, vì vậy kết quả không phụ thuộc dữ liệu trong `data\edugame.sqlite3`.
