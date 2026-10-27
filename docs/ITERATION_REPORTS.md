# Các vòng hoàn thiện OCR

## A — Core CPU và CI (28/10/2026, Asia/Bangkok)

| Trường | Nội dung |
|---|---|
| Task | Tách import engine và môi trường test khỏi ML/GPU |
| Nguyên nhân | Baseline tại e3eeaf8: discovery lỗi cả 3 module test do config import torch; workflow không cài torch |
| Files changed | config.py, pipeline.py, requirements*.txt, ci.yml, test_stage0_env.py, test_imports.py, README, coverage config |
| Tests | PASS: 7 tests, core smoke, compileall, pip check trên venv Python 3.12.14 Linux không torch |
| Regression | 6 test cũ + 1 import-isolation test pass |
| Performance | Chưa benchmark; inference chưa chạy |
| Coverage | 29% branch+statement toàn bộ OCR; bao gồm engine/UI chưa kiểm thử |
| Commit | Xem Git log với message fix(ci): isolate CPU contracts from inference dependencies |
| Push | Xác minh bằng remote SHA sau commit; không dùng báo cáo này làm bằng chứng push |
| Rủi ro còn lại | Chưa xác minh CI hosted; inference dependencies/model weights chưa cài |
| Tiếp theo | B: adapter nhận string, kiểm soát chất lượng và trạng thái UI/PDF |
