# d:\Project_self\export_md.py

# 1. Import hàm cần thiết từ file read_pdf.py của bạn
from read_pdf import extract_pdf_pages
import os

def convert_to_markdown(pdf_path: str) -> str:
    """
    Trích xuất nội dung từ PDF và chuyển thành định dạng Markdown đơn giản.
    """
    if not os.path.exists(pdf_path):
        return f"# Lỗi\n\nKhông tìm thấy file PDF tại đường dẫn: `{pdf_path}`"

    print(f"Đang xử lý file: {pdf_path}")
    try:
        # 2. Gọi hàm đã import để lấy nội dung PDF
        pages_data = extract_pdf_pages(pdf_path)
        
        markdown_content = f"# Nội dung từ {os.path.basename(pdf_path)}\n\n"
        
        # 3. Xử lý dữ liệu đã trích xuất và định dạng thành Markdown
        for i, page_content in enumerate(pages_data, 1):
            markdown_content += f"## Trang {i}\n\n"
            
            if page_content.get("text"):
                markdown_content += "### Văn bản gốc:\n"
                markdown_content += page_content["text"] + "\n\n"
            
            if page_content.get("ocr"):
                markdown_content += "### Văn bản OCR:\n"
                markdown_content += page_content["ocr"] + "\n\n"

            if page_content.get("tables"):
                markdown_content += "### Bảng:\n"
                for j, table in enumerate(page_content["tables"], 1):
                    markdown_content += f"**Bảng {j}**\n"
                    # Biểu diễn bảng đơn giản
                    for row in table:
                        markdown_content += "| " + " | ".join(map(str, row)) + " |\n"
                    markdown_content += "\n"

        return markdown_content

    except Exception as e:
        return f"# Lỗi\n\nĐã có lỗi xảy ra khi xử lý file PDF: {e}"

if __name__ == "__main__":
    # 4. **QUAN TRỌNG**: Đặt đường dẫn đến file PDF của bạn ở đây
    PDF_FILE_PATH = "d:\\Project_self\\metric.pdf"
    
    # Lấy nội dung markdown
    markdown_output = convert_to_markdown(PDF_FILE_PATH)
    
    # Xác định đường dẫn file markdown đầu ra
    output_filename = os.path.splitext(os.path.basename(PDF_FILE_PATH))[0] + ".md"
    output_filepath = os.path.join(os.path.dirname(PDF_FILE_PATH), output_filename)

    # 5. Lưu kết quả ra file .md
    print(f"Lưu kết quả vào file: {output_filepath}")
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_output)
        
    print("✅ Hoàn thành!")
