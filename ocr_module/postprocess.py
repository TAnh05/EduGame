"""
Module hậu xử lý và Cổng chất lượng văn bản (postprocess.py).
Bao gồm:
- Chuẩn hóa Unicode NFC (chống lệch dấu tổ hợp tiếng Việt)
- Làm sạch định dạng markdown thừa từ model sinh ra
- Chuẩn hóa ngắt dòng, khoảng trắng (giữ cấu trúc 'Thuật ngữ: Định nghĩa')
- Phát hiện và loại bỏ dòng lặp liên tiếp hoặc kẹt vòng lặp n-gram
- Cổng chất lượng (Quality Gate): đánh giá tính hợp lệ của văn bản trích xuất
"""

import re
import unicodedata
from typing import Tuple, List
from collections import Counter
from .config import QualityGateConfig


VIETNAMESE_DIACRITICS = set(
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ"
    "ÈÉẺẼẸÊỀẾỂỄỆ"
    "ÌÍỈĨỊ"
    "ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ"
    "ÙÚỦŨỤƯỪỨỬỮỰ"
    "ỲÝỶỸỴĐ"
)


def normalize_unicode_nfc(text: str) -> str:
    """Chuẩn hóa chuỗi văn bản về chuẩn Unicode NFC dựng sẵn."""
    return unicodedata.normalize("NFC", text)


def clean_markdown_and_artifacts(text: str) -> str:
    """Loại bỏ các ký tự định dạng markdown thừa mà model có thể tự chèn vào."""
    # Xóa các thẻ markdown đậm/nghiêng như **, __, *
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*", r"\1", cleaned)
    
    # Xóa ký hiệu tiêu đề markdown (# ## ###) ở đầu dòng
    cleaned = re.sub(r"^[ \t]*#+[ \t]*", "", cleaned, flags=re.MULTILINE)
    
    # Xóa các tag giả lập của model như <s>, </s>, <image>, assistant, user
    cleaned = re.sub(r"</?(?:s|image|assistant|user)>", "", cleaned, flags=re.IGNORECASE)
    
    return cleaned


def deduplicate_consecutive_lines(text: str) -> str:
    """Loại bỏ các dòng bị lặp lại liên tiếp do hiện tượng lặp của Vision-Language Model."""
    lines = text.split("\n")
    cleaned_lines: List[str] = []
    prev_line = None
    for line in lines:
        stripped = line.strip()
        if stripped != prev_line or not stripped:
            cleaned_lines.append(line)
            if stripped:
                prev_line = stripped
    return "\n".join(cleaned_lines)


def normalize_whitespace_and_paragraphs(text: str) -> str:
    """
    Chuẩn hóa khoảng trắng và liên kết dòng:
    - Giữ nguyên các dòng có định dạng thuật ngữ/mục lục (VD: 'Từ khóa:', '1.', '- ')
    - Gộp các dòng bị ngắt câu bất thường giữa chừng.
    """
    lines = text.split("\n")
    merged_lines: List[str] = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if merged_lines and merged_lines[-1] != "":
                merged_lines.append("")
            continue
            
        # Chuẩn hóa khoảng trắng nội bộ trong dòng
        norm_line = re.sub(r"[ \t]+", " ", stripped)
        
        # Nếu dòng trước kết thúc không phải dấu câu ngắt dòng (., :, ?, !)
        # và dòng hiện tại không phải là đầu mục (chữ hoa/số/gạch đầu dòng),
        # ta nối tiếp vào dòng trước đó.
        is_bullet = re.match(r"^(?:[-*•]|\d+[\.\)])\s+", norm_line)
        is_key_value = ":" in norm_line and len(norm_line.split(":", 1)[0]) < 35
        
        if (
            merged_lines 
            and merged_lines[-1] 
            and not is_bullet 
            and not is_key_value 
            and not merged_lines[-1].endswith((".", ":", "?", "!", ";"))
        ):
            merged_lines[-1] += " " + norm_line
        else:
            merged_lines.append(norm_line)
            
    return "\n".join(merged_lines).strip()


def calculate_repetition_rate(text: str, n: int = 4) -> float:
    """
    Tính tỉ lệ lặp n-gram từ (mặc định 4 từ liên tiếp) để phát hiện kẹt vòng lặp.
    """
    words = [w.lower() for w in re.findall(r"\w+", text)]
    if len(words) < n * 2:
        return 0.0
    ngrams = [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]
    counts = Counter(ngrams)
    repeated_count = sum(c - 1 for c in counts.values() if c > 1)
    return float(repeated_count) / float(len(ngrams))


def validate_extracted_text(
    text: str, 
    cfg: QualityGateConfig
) -> Tuple[bool, str, List[str]]:
    """
    Kiểm tra chất lượng văn bản sau trích xuất:
    - Độ dài tối thiểu
    - Tỉ lệ ký tự hợp lệ
    - Tỉ lệ lặp từ n-gram
    - Tỉ lệ dấu tiếng Việt (nếu phát hiện là văn bản tiếng Việt)
    """
    warnings: List[str] = []
    cleaned_len = len(text.strip())
    
    # 1. Kiểm tra độ dài tối thiểu
    if cleaned_len < cfg.min_char_count:
        return (
            False,
            f"Văn bản trích xuất quá ngắn ({cleaned_len} ký tự). Model có thể không đọc được hoặc trang rỗng.",
            warnings
        )
        
    # 2. Tỉ lệ ký tự hợp lệ (chữ cái, chữ số, dấu câu)
    valid_chars = sum(1 for c in text if c.isalnum() or c in " \n\t.,;:?!-_'\"()[]{}/@#%&+=")
    valid_ratio = valid_chars / max(cleaned_len, 1)
    if valid_ratio < cfg.min_valid_char_ratio:
        return (
            False,
            f"Chất lượng chữ kém, xuất hiện nhiều ký tự rác (tỉ lệ hợp lệ chỉ đạt {valid_ratio * 100:.1f}%).",
            warnings
        )
        
    # 3. Phát hiện kẹt vòng lặp (Repetition Loop)
    rep_ratio = calculate_repetition_rate(text, n=4)
    if rep_ratio > cfg.max_ngram_repetition_ratio:
        return (
            False,
            f"Phát hiện văn bản bị lặp lại bất thường (tỉ lệ lặp {rep_ratio * 100:.1f}%). Model bị kẹt vòng lặp suy luận.",
            warnings
        )
    elif rep_ratio > 0.15:
        warnings.append("Văn bản có một số cụm từ lặp lại nhiều lần.")
        
    # 4. Kiểm tra dấu tiếng Việt nếu có dấu hiệu tiếng Việt
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters > 20:
        diacritic_chars = sum(1 for c in text if c in VIETNAMESE_DIACRITICS)
        diacritic_ratio = diacritic_chars / total_letters
        # Nếu có chữ cái tiếng Việt nhưng tỉ lệ dấu quá thấp (ví dụ < 1%)
        if 0 < diacritic_ratio < cfg.min_vietnamese_diacritic_ratio:
            warnings.append(
                f"Tỉ lệ dấu tiếng Việt thấp ({diacritic_ratio * 100:.1f}%), có thể văn bản bị mất dấu hoặc là tiếng Anh/song ngữ."
            )

    return True, "", warnings


def clean_and_gate_text(
    raw_text: str, 
    cfg: QualityGateConfig
) -> Tuple[str, bool, str, List[str]]:
    """
    Quy trình hậu xử lý hoàn chỉnh:
    Làm sạch -> Chuẩn hóa -> Cổng chất lượng.
    """
    # Bước 1: Chuẩn hóa NFC
    text = normalize_unicode_nfc(raw_text)
    
    # Bước 2: Dọn markdown và artifacts
    text = clean_markdown_and_artifacts(text)
    
    # Bước 3: Khử dòng lặp liên tiếp
    text = deduplicate_consecutive_lines(text)
    
    # Bước 4: Chuẩn hóa khoảng trắng & ngắt đoạn
    text = normalize_whitespace_and_paragraphs(text)
    
    # Bước 5: Cổng kiểm tra chất lượng
    ok, reason, warnings = validate_extracted_text(text, cfg)
    
    return text, ok, reason, warnings
