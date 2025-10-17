"""
Module xử lý làm sạch văn bản được trích xuất từ PDF.

Chức năng:
- Loại bỏ dòng trống thừa
- Loại bỏ khoảng trắng thừa
- Chuẩn hóa định dạng văn bản
- Xử lý các ký tự đặc biệt
"""

import sys
from pathlib import Path
import re
from typing import Optional

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.logging_config import get_logger

logger = get_logger(__name__)


def clean_whitespace(text: str) -> str:
    """
    Loại bỏ khoảng trắng thừa trong văn bản.
    
    Args:
        text: Văn bản cần xử lý
        
    Returns:
        Văn bản đã loại bỏ khoảng trắng thừa
    """
    if not text:
        return ""
    
    # Loại bỏ nhiều khoảng trắng liên tiếp thành 1 khoảng trắng
    text = re.sub(r' +', ' ', text)
    
    # Loại bỏ khoảng trắng ở đầu và cuối mỗi dòng
    lines = [line.strip() for line in text.split('\n')]
    
    return '\n'.join(lines)


def remove_empty_lines(text: str, max_consecutive: int = 1) -> str:
    """
    Loại bỏ dòng trống thừa, chỉ giữ tối đa N dòng trống liên tiếp.
    
    Args:
        text: Văn bản cần xử lý
        max_consecutive: Số dòng trống tối đa được giữ lại (mặc định: 1)
        
    Returns:
        Văn bản đã loại bỏ dòng trống thừa
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    empty_count = 0
    
    for line in lines:
        if line.strip():  # Dòng có nội dung
            cleaned_lines.append(line)
            empty_count = 0
        else:  # Dòng trống
            empty_count += 1
            if empty_count <= max_consecutive:
                cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def remove_special_chars(text: str, keep_chars: Optional[str] = None) -> str:
    """
    Loại bỏ các ký tự đặc biệt không mong muốn.
    
    Args:
        text: Văn bản cần xử lý
        keep_chars: Các ký tự đặc biệt muốn giữ lại (mặc định: giữ dấu câu cơ bản)
        
    Returns:
        Văn bản đã loại bỏ ký tự đặc biệt
    """
    if not text:
        return ""
    
    # Giữ lại: chữ cái, số, dấu câu cơ bản, xuống dòng, tab
    if keep_chars is None:
        keep_chars = r'.,!?;:()[]{}"\'-\n\t '
    
    # Loại bỏ các ký tự control characters (trừ \n và \t)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    return text


def normalize_line_breaks(text: str) -> str:
    """
    Chuẩn hóa các loại xuống dòng khác nhau thành \n.
    
    Args:
        text: Văn bản cần xử lý
        
    Returns:
        Văn bản đã chuẩn hóa xuống dòng
    """
    if not text:
        return ""
    
    # Chuyển \r\n và \r thành \n
    text = text.replace('\r\n', '\n')
    text = text.replace('\r', '\n')
    
    return text


def fix_hyphenation(text: str) -> str:
    """
    Sửa các từ bị ngắt dòng bởi dấu gạch nối (hyphenation).
    
    Ví dụ: "exam-\nple" → "example"
    
    Args:
        text: Văn bản cần xử lý
        
    Returns:
        Văn bản đã sửa hyphenation
    """
    if not text:
        return ""
    
    # Tìm pattern: chữ cái + dấu gạch nối + xuống dòng + chữ cái
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    
    return text


def merge_broken_sentences(text: str) -> str:
    """
    Ghép các câu bị ngắt dòng không đúng chỗ.
    
    Logic: Nếu dòng không kết thúc bằng dấu câu và dòng tiếp theo bắt đầu bằng chữ thường,
    thì ghép chúng lại.
    
    Args:
        text: Văn bản cần xử lý
        
    Returns:
        Văn bản đã ghép câu
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    merged_lines = []
    i = 0
    
    while i < len(lines):
        current_line = lines[i].strip()
        
        # Nếu không phải dòng cuối và dòng hiện tại không kết thúc bằng dấu câu
        if i < len(lines) - 1 and current_line and not current_line[-1] in '.!?;:':
            next_line = lines[i + 1].strip()
            
            # Nếu dòng tiếp theo bắt đầu bằng chữ thường, ghép lại
            if next_line and next_line[0].islower():
                merged_lines.append(current_line + ' ' + next_line)
                i += 2
                continue
        
        merged_lines.append(current_line)
        i += 1
    
    return '\n'.join(merged_lines)


def clean_extracted_text(text: str, aggressive: bool = False) -> str:
    """
    Hàm chính để làm sạch văn bản được trích xuất từ PDF.
    
    Áp dụng tất cả các bước làm sạch theo thứ tự:
    1. Chuẩn hóa xuống dòng
    2. Loại bỏ ký tự đặc biệt
    3. Sửa hyphenation
    4. Loại bỏ khoảng trắng thừa
    5. Ghép câu bị ngắt (nếu aggressive=True)
    6. Loại bỏ dòng trống thừa
    
    Args:
        text: Văn bản cần làm sạch
        aggressive: Nếu True, áp dụng thêm các bước xử lý sâu hơn
        
    Returns:
        Văn bản đã được làm sạch
    """
    if not text:
        return ""
    
    logger.debug("Bắt đầu làm sạch văn bản...")
    
    # 1. Chuẩn hóa xuống dòng
    text = normalize_line_breaks(text)
    
    # 2. Loại bỏ ký tự đặc biệt không mong muốn
    text = remove_special_chars(text)
    
    # 3. Sửa hyphenation (từ bị ngắt dòng)
    text = fix_hyphenation(text)
    
    # 4. Loại bỏ khoảng trắng thừa
    text = clean_whitespace(text)
    
    # 5. Ghép câu bị ngắt (chỉ khi aggressive=True)
    if aggressive:
        text = merge_broken_sentences(text)
    
    # 6. Loại bỏ dòng trống thừa (giữ tối đa 1 dòng trống)
    text = remove_empty_lines(text, max_consecutive=1)
    
    logger.debug(f"Hoàn thành làm sạch. Độ dài: {len(text)} ký tự")
    
    return text


def clean_table_text(table: list[list[str]]) -> list[list[str]]:
    """
    Làm sạch văn bản trong các ô của bảng.
    
    Args:
        table: Bảng dạng list of lists
        
    Returns:
        Bảng đã được làm sạch
    """
    if not table:
        return []
    
    cleaned_table = []
    for row in table:
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                # Làm sạch từng ô trong bảng (không aggressive)
                cleaned_cell = clean_extracted_text(str(cell), aggressive=False)
                # Loại bỏ xuống dòng trong cell (chuyển thành khoảng trắng)
                cleaned_cell = cleaned_cell.replace('\n', ' ')
                cleaned_row.append(cleaned_cell)
        cleaned_table.append(cleaned_row)
    
    return cleaned_table


def quick_clean(text: str) -> str:
    """
    Làm sạch nhanh cho văn bản (không aggressive).
    Phù hợp cho text đã khá sạch hoặc cần giữ nguyên cấu trúc.
    
    Args:
        text: Văn bản cần làm sạch
        
    Returns:
        Văn bản đã được làm sạch đơn giản
    """
    if not text:
        return ""
    
    text = normalize_line_breaks(text)
    text = clean_whitespace(text)
    text = remove_empty_lines(text, max_consecutive=1)
    
    return text


# --- TEST & DEMO ---
if __name__ == "__main__":
    # Test các hàm
    sample_text = """
    This    is   a    test     text   with   multiple    spaces.
    
    
    
    And   multiple    empty   lines.
    
    This is a hyphen-
    ated word that spans lines.
    
    This line does not end with punctuation
    but the next line continues the sentence.
    """
    
    print("=== Original Text ===")
    print(repr(sample_text))
    
    print("\n=== Quick Clean ===")
    print(repr(quick_clean(sample_text)))
    
    print("\n=== Full Clean (aggressive=False) ===")
    print(repr(clean_extracted_text(sample_text, aggressive=False)))
    
    print("\n=== Full Clean (aggressive=True) ===")
    print(repr(clean_extracted_text(sample_text, aggressive=True)))
