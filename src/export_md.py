import os
import sys
from pathlib import Path

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.read_pdf import extract_pdf_pages
from src.logging_config import get_logger
from src.clean_pdf import clean_extracted_text

logger = get_logger(__name__)


def is_valid_table(table: list[list[str]]) -> bool:
    """
    Kiểm tra xem bảng có hợp lệ không.
    
    Bảng hợp lệ nếu:
    - Có ít nhất 2 hàng
    - Có ít nhất 2 cột
    - Không phải toàn bộ cells đều rỗng
    """
    if not table or len(table) < 2:
        return False
    
    # Kiểm tra số cột
    num_cols = len(table[0]) if table else 0
    if num_cols < 2:
        return False
    
    # Kiểm tra có ít nhất 1 cell có nội dung
    has_content = False
    for row in table:
        for cell in row:
            if cell and str(cell).strip():
                has_content = True
                break
        if has_content:
            break
    
    return has_content


def format_table_as_markdown(table: list[list[str]]) -> str:
    """
    Định dạng một bảng (danh sách của các danh sách) thành một bảng Markdown.
    """
    markdown_table = ""
    if not table:
        return ""
    
    # Đảm bảo tất cả hàng có cùng số cột
    max_cols = max(len(row) for row in table)
    normalized_table = []
    for row in table:
        # Pad thêm cells rỗng nếu thiếu
        normalized_row = row + [''] * (max_cols - len(row))
        # Clean và trim mỗi cell
        normalized_row = [str(cell).strip() if cell else '' for cell in normalized_row]
        normalized_table.append(normalized_row)
    
    # Tạo hàng tiêu đề
    header = normalized_table[0]
    markdown_table += "| " + " | ".join(header) + " |\n"
    
    # Tạo hàng phân cách
    markdown_table += "| " + " | ".join(["---"] * len(header)) + " |\n"
    
    # Tạo các hàng nội dung
    for row in normalized_table[1:]:
        markdown_table += "| " + " | ".join(row) + " |\n"
        
    return markdown_table + "\n"

def convert_to_markdown(pdf_path: str) -> str:
    """
    Sử dụng hàm extract_pdf_pages để lấy dữ liệu có cấu trúc và chuyển đổi
    thành một file Markdown hoàn chỉnh, xử lý đúng theo nguồn dữ liệu.
    
    Cải tiến:
    - Lọc bỏ bảng không hợp lệ (rỗng, 1 cột, v.v.)
    - Tránh trùng lặp giữa text và table
    - Format Markdown tốt hơn
    """
    if not os.path.exists(pdf_path):
        logger.error(f"Không tìm thấy file PDF: {pdf_path}")
        return f"# Lỗi\n\nKhông tìm thấy file PDF tại đường dẫn: `{pdf_path}`"

    logger.info(f"Bắt đầu tạo file Markdown cho: {pdf_path}")
    print(f"▶️  Bắt đầu quá trình tạo file Markdown cho: {pdf_path}")
    try:
        pages_data = extract_pdf_pages(pdf_path)
        
        if not pages_data:
            logger.warning(f"Không thể trích xuất nội dung từ {pdf_path}")
            
            # Thông báo chi tiết cho user
            error_msg = f"""# Lỗi: Không thể trích xuất nội dung

## File PDF: `{pdf_path}`

### Nguyên nhân có thể:
1. **PDF dạng ảnh (Image-based PDF)**: PDF được scan từ sách giấy, không có text layer
   - Cần dùng **Gemini Vision** (chọn Y khi được hỏi) để OCR toàn bộ PDF
   - Hoặc dùng công cụ OCR khác

2. **PDF bị corrupt**: File bị hỏng hoặc không đúng format

3. **PDF bị mã hóa/bảo vệ**: File có password hoặc bị protect

### Giải pháp:
- Chạy lại và chọn **Y** (Gemini Vision) khi được hỏi
- Hoặc convert PDF sang version mới hơn
- Hoặc dùng công cụ OCR riêng để tạo PDF có text layer
"""
            return error_msg

        markdown_content = f"# Nội dung từ {os.path.basename(pdf_path)}\n\n"
        
        for page_content in pages_data:
            page_num = page_content["page_number"]
            source = page_content["source"]
            text = page_content["text"]
            tables = page_content["tables"]

            markdown_content += f"--- Trang {page_num} (Nguồn: {source}) ---\n\n"
            
            # Nếu nguồn là Gemini, văn bản đã là Markdown.
            if source == "gemini":
                markdown_content += text + "\n\n"
            # Nếu nguồn là thủ công, cần xử lý thêm
            else:
                # Lọc bảng hợp lệ
                valid_tables = [table for table in tables if is_valid_table(table)]
                
                # Chỉ hiển thị text nếu không có bảng hợp lệ hoặc text có nội dung độc lập
                if text and (not valid_tables or len(text.strip()) > 200):
                    markdown_content += "### Nội dung văn bản:\n\n"
                    # Không bọc trong code block, format như Markdown bình thường
                    markdown_content += text + "\n\n"
                
                # Hiển thị bảng
                if valid_tables:
                    markdown_content += "### Bảng:\n\n"
                    for j, table in enumerate(valid_tables, 1):
                        if len(valid_tables) > 1:
                            markdown_content += f"**Bảng {j}:**\n\n"
                        markdown_content += format_table_as_markdown(table)

        logger.info("Ghép nối nội dung Markdown hoàn tất")
        print("(´｡• ᵕ •｡`) Ghép nối nội dung Markdown hoàn tất.")
        return markdown_content

    except Exception as e:
        logger.error(f"Lỗi trong quá trình tạo Markdown: {e}")
        return f"# Lỗi\n\nĐã có lỗi xảy ra trong quá trình tạo Markdown: {e}"

if __name__ == "__main__":
    from src.config import PDF_PATH, OUTPUT_DIR
    
    markdown_output = convert_to_markdown(PDF_PATH)
    
    # Tạo thư mục output nếu chưa tồn tại
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    output_filename = os.path.splitext(os.path.basename(PDF_PATH))[0] + ".md"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename)

    logger.info(f"Lưu kết quả vào file: {output_filepath}")
    print(f"（*＾3＾)/~☆ Lưu kết quả vào file: {output_filepath}")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_output)
    
    logger.info("Hoàn thành tạo file Markdown")
    print("*    ~    o(≧▽≦)o    ♪ Hoàn thành! File Markdown đã được tạo.")
