"""
Tập lệnh tạo dữ liệu mẫu cho bộ kiểm thử eval/ (create_eval_samples.py).
Tạo:
- 1 ảnh sạch chuẩn: sample_clean.png + sample_clean.txt
- 1 ảnh hơi nghiêng nhẹ: sample_skewed.png + sample_skewed.txt
- 1 ảnh bị tối / bóng đổ nhẹ: sample_shadow.png + sample_shadow.txt
"""

import os
import sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

base_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(base_dir, "ocr_module", "eval", "images")
tru_dir = os.path.join(base_dir, "ocr_module", "eval", "truth")

os.makedirs(img_dir, exist_ok=True)
os.makedirs(tru_dir, exist_ok=True)

# Nội dung văn bản mẫu cho tài liệu ôn tập
sample_text_1 = (
    "Chương 1: Khái niệm cơ bản về Hệ quản trị cơ sở dữ liệu\n"
    "1. Khái niệm dữ liệu và thông tin:\n"
    "Dữ liệu là các sự kiện, số liệu thô chưa qua xử lý phản ánh thế giới khách quan.\n"
    "Thông tin là dữ liệu đã được xử lý để mang lại ý nghĩa cho người sử dụng.\n"
    "2. Khóa chính (Primary Key):\n"
    "Là một hoặc tập hợp các thuộc tính dùng để xác định duy nhất mỗi bộ trong quan hệ."
)

sample_text_2 = (
    "Bài 3: Định luật Ôm đối với toàn mạch\n"
    "Cường độ dòng điện chạy trong mạch kín tỉ lệ thuận với suất điện động của nguồn điện\n"
    "và tỉ lệ nghịch với điện trở toàn phần của mạch đó.\n"
    "Công thức: I = E / (R + r)\n"
    "Trong đó: E là suất điện động, R là điện trở mạch ngoài, r là điện trở trong."
)


def create_image_from_text(text: str, width: int = 1200, height: int = 700) -> Image.Image:
    """Tạo ảnh PIL chứa văn bản rõ nét."""
    img = Image.new("RGB", (width, height), color=(252, 252, 250))
    draw = ImageDraw.Draw(img)

    # Thử nạp font hệ thống Windows
    font = None
    system_fonts = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\times.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf"
    ]
    for sf in system_fonts:
        if os.path.exists(sf):
            try:
                font = ImageFont.truetype(sf, size=24)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    y = 50
    for line in text.split("\n"):
        draw.text((60, y), line, fill=(30, 30, 30), font=font)
        y += 45

    return img


# 1. Tạo mẫu Clean
img_clean = create_image_from_text(sample_text_1)
img_clean.save(os.path.join(img_dir, "sample_clean.png"))
with open(os.path.join(tru_dir, "sample_clean.txt"), "w", encoding="utf-8") as f:
    f.write(sample_text_1)

# 2. Tạo mẫu Skewed (nghiêng khoảng 3.5 độ)
img_skew = img_clean.rotate(3.5, expand=False, fillcolor=(255, 255, 255))
img_skew.save(os.path.join(img_dir, "sample_skewed.png"))
with open(os.path.join(tru_dir, "sample_skewed.txt"), "w", encoding="utf-8") as f:
    f.write(sample_text_1)

# 3. Tạo mẫu Shadow (bị gradient bóng đổ từ góc)
cv_img = cv2.cvtColor(np.array(create_image_from_text(sample_text_2)), cv2.COLOR_RGB2BGR)
h, w = cv_img.shape[:2]
# Tạo gradient mặt nạ sáng/tối
x_grad = np.linspace(0.4, 1.0, w)
y_grad = np.linspace(0.5, 1.0, h)
xx, yy = np.meshgrid(x_grad, y_grad)
shadow_mask = xx * yy
shadow_mask = np.repeat(shadow_mask[:, :, np.newaxis], 3, axis=2)
cv_shadow = np.clip(cv_img * shadow_mask, 0, 255).astype(np.uint8)

cv2.imwrite(os.path.join(img_dir, "sample_shadow.png"), cv_shadow)
with open(os.path.join(tru_dir, "sample_shadow.txt"), "w", encoding="utf-8") as f:
    f.write(sample_text_2)

print("Đã tạo thành công 3 ảnh kiểm thử mẫu và file đáp án chuẩn ground truth trong ocr_module/eval/!")
