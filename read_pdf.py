import os
import logging
import pdfplumber
from typing import List, Dict
import warnings
from PIL import Image
import numpy as np
import torch
import easyocr

# Import hàm cấu hình Gemini từ client
from gemini_client import configure_gemini

# --- SETUP ---
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)

# --- HÀM XỬ LÝ VỚI GEMINI ---
def describe_slide(img: Image.Image, model) -> str:
    if not model:
        return "[Lỗi Gemini: Model chưa được cấu hình]"
    try:
        prompt = '''Bạn là một chuyên gia phân tích tài liệu, slide thuyết trình, bài viết báo cáo.
Nhiệm vụ của bạn là xem hình ảnh của một slide và chuyển đổi nó thành một văn bản Markdown chi tiết, có cấu trúc.
- Giữ lại các tiêu đề, đề mục.
- Chuyển đổi các danh sách (bullet points) thành danh sách Markdown.
- Trích xuất và tái tạo lại các bảng biểu một cách chính xác nhất có thể ở định dạng Markdown table.
- Diễn giải và tóm tắt nội dung chính của slide một cách mạch lạc.
- Luôn trả lời bằng ngôn ngữ gốc của văn bản.'''
        response = model.generate_content([prompt, img])
        return response.text.strip()
    except Exception as e:
        print(f"      -> ❌ Lỗi khi gọi Gemini Vision: {e}")
        return "[Lỗi Gemini: Không thể phân tích ảnh]"

# --- PHƯƠNG ÁN DỰ PHÒNG: OCR ---
_ocr_reader = None
def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            print("🔎 Khởi tạo trình đọc OCR (phương án dự phòng)...")
            use_gpu = torch.cuda.is_available()
            print(f"   -> EasyOCR sẽ sử dụng {'GPU' if use_gpu else 'CPU'}.")
            _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=use_gpu)
        except Exception as e:
            print(f"   -> Lỗi nghiêm trọng khi khởi tạo EasyOCR: {e}")
            return None
    return _ocr_reader

def ocr_on_page(page) -> str:
    reader = get_ocr_reader()
    if not reader:
        return "[Lỗi OCR: Không thể khởi tạo trình đọc]"
    try:
        img = page.to_image(resolution=300).original
        results = reader.readtext(np.array(img))
        return "\n".join([text for _, text, _ in results])
    except Exception as e:
        return f"[Lỗi khi đang chạy OCR trên trang: {e}]"

# --- HÀM TRÍCH XUẤT CHÍNH (Logic kết hợp) ---
def extract_pdf_pages(path: str) -> List[Dict]:
    print("✨ Cấu hình Gemini...")
    model = configure_gemini()
    if not model:
        print("   -> ⚠️ Không thể cấu hình Gemini. Sẽ chuyển sang phương án dự phòng.")

    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            print(f"(｡◕‿◕｡) Đang phân tích trang {i}/{len(pdf.pages)}...")
            page_data = {"page_number": i, "text": "", "tables": [], "source": ""}

            if model:
                print("   -> Thử phương án 1: Phân tích bằng Gemini Vision...")
                img = page.to_image(resolution=300).original
                gemini_description = describe_slide(img, model)
            else:
                gemini_description = "[Lỗi Gemini: Model không được cấu hình]"

            if "[Lỗi Gemini" in gemini_description:
                print("   -> (╥_╥)  Gemini không khả dụng, chuyển sang phương án 2: Phân tích thủ công...")
                page_data["source"] = "manual"
                text = page.extract_text(layout=True) or ""
                tables = page.extract_tables() or []
                
                if len(text.strip()) < 100 and not tables:
                    print(f"      -> Trang {i} có ít văn bản, đang chạy OCR...")
                    page_data["text"] = ocr_on_page(page)
                    page_data["source"] = "ocr"
                else:
                    page_data["text"] = text
                    page_data["tables"] = tables
            else:
                print("      -> (*≧ω≦*) Gemini phân tích thành công!")
                page_data["source"] = "gemini"
                page_data["text"] = gemini_description

            pages.append(page_data)
    return pages

# --- MAIN SCRIPT EXECUTION ---
def main():
    from config import PDF_PATH
    if not os.path.exists(PDF_PATH):
        print(f"Lỗi: Không tìm thấy file PDF tại đường dẫn trong config.py: `{PDF_PATH}`")
        return
    
    try:
        print(f"🚀 Bắt đầu xử lý file: {PDF_PATH}...")
        extracted_pages = extract_pdf_pages(PDF_PATH)
        print(f"\n✅ Hoàn thành! Trích xuất được {len(extracted_pages)} trang.\n")
        
        if extracted_pages:
            p1 = extracted_pages[0]
            print("--- PREVIEW TRANG 1 ---")
            print(f"Nguồn: {p1['source']}")
            print(f"Nội dung: {p1['text'][:500]}...")
            if p1['tables']:
                print(f"Tìm thấy {len(p1['tables'])} bảng.")
            
    except Exception as e:
        print(f"\nĐã xảy ra lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()