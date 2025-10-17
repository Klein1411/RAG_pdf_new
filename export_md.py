import os
from read_pdf import extract_pdf_pages
from logging_config import get_logger

logger = get_logger(__name__)

def format_table_as_markdown(table: list[list[str]]) -> str:
    """
    Định dạng một bảng (danh sách của các danh sách) thành một bảng Markdown.
    """
    markdown_table = ""
    if not table:
        return ""
        
    # Tạo hàng tiêu đề
    header = [str(cell) if cell is not None else '' for cell in table[0]]
    markdown_table += "| " + " | ".join(header) + " |\n"
    
    # Tạo hàng phân cách
    markdown_table += "| " + " | ".join(["---"] * len(header)) + " |\n"
    
    # Tạo các hàng nội dung
    for row in table[1:]:
        str_row = [str(cell) if cell is not None else '' for cell in row]
        markdown_table += "| " + " | ".join(str_row) + " |\n"
        
    return markdown_table + "\n"

def convert_to_markdown(pdf_path: str) -> str:
    """
    Sử dụng hàm extract_pdf_pages để lấy dữ liệu có cấu trúc và chuyển đổi
    thành một file Markdown hoàn chỉnh, xử lý đúng theo nguồn dữ liệu.
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
            return f"# Lỗi\n\nKhông thể trích xuất bất kỳ nội dung nào từ file: `{pdf_path}`"

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
                if text:
                    markdown_content += "### Nội dung trang:\n"
                    # Bọc văn bản thô trong khối code để giữ nguyên định dạng
                    markdown_content += f"```\n{text}\n```\n\n"
                
                if tables:
                    markdown_content += "### Bảng trích xuất:\n"
                    for j, table in enumerate(tables, 1):
                        markdown_content += f"**Bảng {j}**\n"
                        markdown_content += format_table_as_markdown(table)

        logger.info("Ghép nối nội dung Markdown hoàn tất")
        print("(´｡• ᵕ •｡`) Ghép nối nội dung Markdown hoàn tất.")
        return markdown_content

    except Exception as e:
        logger.error(f"Lỗi trong quá trình tạo Markdown: {e}")
        return f"# Lỗi\n\nĐã có lỗi xảy ra trong quá trình tạo Markdown: {e}"

if __name__ == "__main__":
    from config import PDF_PATH
    
    markdown_output = convert_to_markdown(PDF_PATH)
    
    output_filename = os.path.splitext(os.path.basename(PDF_PATH))[0] + ".md"
    output_filepath = os.path.join(os.path.dirname(PDF_PATH), output_filename)

    logger.info(f"Lưu kết quả vào file: {output_filepath}")
    print(f"（*＾3＾)/~☆ Lưu kết quả vào file: {output_filepath}")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_output)
    
    logger.info("Hoàn thành tạo file Markdown")
    print("*    ~    o(≧▽≦)o    ♪ Hoàn thành! File Markdown đã được tạo.")
