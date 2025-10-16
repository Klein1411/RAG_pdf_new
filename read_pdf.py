import os
import logging
import argparse
import pdfplumber
from typing import List, Dict
import warnings
from PIL import Image
import numpy as np
import torch
import easyocr

# Import hàm xử lý Gemini từ file client mới
from gemini_client import describe_slide

# --- SETUP ---
# Tắt bớt warning không cần thiết
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)

# --- PHƯƠNG ÁN DỰ PHÒNG: OCR ---

# Khởi tạo EasyOCR một cách "lười biếng" (chỉ khi nào cần mới chạy)
_ocr_reader = None
def get_ocr_reader():
    """Khởi tạo và trả về một thực thể của EasyOCR reader."""
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
    """Chạy OCR trên một trang và trả về văn bản."""
    reader = get_ocr_reader()
    if not reader:
        return "[Lỗi OCR: Không thể khởi tạo trình đọc]"
    try:
        img = page.to_image(resolution=300).original
        results = reader.readtext(np.array(img))
        texts = [text for _, text, _ in results]
        return "\n".join(texts)
    except Exception as e:
        return f"[Lỗi khi đang chạy OCR trên trang: {e}]"


# --- HÀM TRÍCH XUẤT CHÍNH (Logic kết hợp) ---
def extract_pdf_pages(path: str) -> List[Dict]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            print(f"📄 Đang phân tích trang {i}/{len(pdf.pages)}...")
            
            # --- Ưu tiên 1: Thử phân tích bằng Gemini Vision ---
            print("   -> Thử phương án 1: Phân tích bằng Gemini Vision...")
            img = page.to_image(resolution=300).original
            gemini_description = describe_slide(img)

            # --- Kiểm tra và chuyển sang phương án 2 nếu cần ---
            if "[Tất cả các API key đều gặp lỗi" in gemini_description:
                print("   -> ⚠️ Gemini không khả dụng, chuyển sang phương án 2: Phân tích thủ công...")
                
                # Dùng pdfplumber để trích xuất văn bản
                text = page.extract_text(layout=True) or ""
                
                # Nếu văn bản quá ít, coi đó là ảnh và chạy OCR
                if len(text.strip()) < 100:
                    print(f"      -> Trang {i} có ít văn bản, đang chạy OCR...")
                    final_text = ocr_on_page(page)
                else:
                    final_text = text
            else:
                # Nếu Gemini hoạt động, sử dụng mô tả của nó
                final_text = gemini_description

            pages.append({
                "page_number": i,
                "text": final_text,
            })
    return pages

# --- MAIN SCRIPT EXECUTION ---
def main():
    parser = argparse.ArgumentParser(description="Trích xuất nội dung từ file PDF bằng Gemini Vision với phương án dự phòng thủ công.")
    parser.add_argument("pdf_path", help="Đường dẫn đến file PDF cần xử lý.")
    args = parser.parse_args()
    pdf_path = args.pdf_path
    if not os.path.exists(pdf_path):
        print(f"Lỗi: Không tìm thấy file `{pdf_path}`")
        return
    try:
        print(f"🚀 Bắt đầu xử lý file: {pdf_path}...")
        extracted_pages = extract_pdf_pages(pdf_path)
        print(f"✅ Hoàn thành! Trích xuất được {len(extracted_pages)} trang.\n")
        if extracted_pages:
            p1 = extracted_pages[0]
            print("--- PREVIEW TRANG 1 ---")
            print(f"{p1['text'][:1000]}...")
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()