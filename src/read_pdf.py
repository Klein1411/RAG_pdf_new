import os
import sys
from pathlib import Path
import logging
import pdfplumber
from typing import List, Dict
import warnings
from PIL import Image
import numpy as np
import torch
import easyocr
import fitz  # pymupdf
import pytesseract
import io

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.logging_config import get_logger
from src.clean_pdf import clean_extracted_text, clean_table_text

# --- SETUP ---
logger = get_logger(__name__)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)

# --- Removed Gemini Vision functions - using manual extraction only ---

# --- PHƯƠNG ÁN DỰ PHÒNG: OCR ---
_ocr_reader = None
def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        try:
            logger.info("🔎 Khởi tạo trình đọc OCR (phương án dự phòng)...")
            use_gpu = torch.cuda.is_available()
            logger.info(f"EasyOCR sẽ sử dụng {'GPU' if use_gpu else 'CPU'}")
            _ocr_reader = easyocr.Reader(['vi', 'en'], gpu=use_gpu)
        except Exception as e:
            logger.error(f"Lỗi nghiêm trọng khi khởi tạo EasyOCR: {e}")
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

# Gemini OCR functions removed - using EasyOCR/Tesseract only


# Tesseract OCR function for image-based PDFs
def tesseract_ocr_on_page(page_image: Image.Image) -> str:
    """
    Sử dụng Tesseract OCR để đọc text từ một trang PDF (dạng ảnh).
    
    Args:
        page_image: PIL Image của trang PDF
        
    Returns:
        Text đã OCR
    """
    try:
        logger.debug("🔍 Đang OCR trang bằng Tesseract...")
        text = pytesseract.image_to_string(page_image, lang='eng')
        return text
    except Exception as e:
        logger.error(f"❌ Lỗi Tesseract OCR: {e}")
        return "[Lỗi Tesseract: Không thể OCR trang]"


# Gemini OCR functions removed - using standard OCR methods only

def extract_pdf_with_tesseract(pdf_path: str) -> List[Dict]:
    """
    Extract toàn bộ PDF bằng pymupdf + Tesseract OCR.
    Dùng cho image-based PDF có nhiều ảnh (>= 20 ảnh).
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        
    Returns:
        List các trang với text đã OCR
    """
    logger.info("🔄 Chuyển sang phương án Tesseract OCR (pymupdf + Tesseract)")
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        logger.info(f"📄 PDF có {total_pages} trang, đang OCR...")
        
        pages = []
        
        for page_num in range(total_pages):
            logger.info(f"   OCR trang {page_num + 1}/{total_pages}...")
            
            page = doc[page_num]
            
            # Convert page to image (300 DPI cho OCR tốt)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            
            # OCR
            text = tesseract_ocr_on_page(image)
            
            # Clean text
            text = clean_extracted_text(text)
            
            # Tạo page data
            page_data = {
                "page_number": page_num + 1,
                "text": text,
                "tables": [],  # Tesseract không extract table
                "source": "tesseract-ocr"
            }
            
            pages.append(page_data)
        
        doc.close()
        
        logger.info(f"✅ Hoàn thành OCR {total_pages} trang bằng Tesseract")
        return pages
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi OCR bằng Tesseract: {e}")
        return []

# --- HÀM TRÍCH XUẤT CHÍNH (Chỉ dùng phương án thủ công/OCR) ---
def extract_pdf_pages(path: str) -> List[Dict]:
    logger.info("📄 Bắt đầu phân tích PDF bằng pdfplumber + OCR...")
    pages = []
    
    # Thử mở bằng pdfplumber trước
    try:
        pdf = pdfplumber.open(path)
        has_pages = pdf.pages and len(pdf.pages) > 0
    except Exception as e:
        logger.error(f"❌ Không thể mở PDF bằng pdfplumber: {e}")
        has_pages = False
        pdf = None
    
    # Kiểm tra nếu PDF không có pages (image-based PDF hoặc corrupt)
    if not has_pages:
        logger.error("❌ pdfplumber không đọc được cấu trúc PDF (có thể là image-based PDF)")
        
        # Đếm số trang bằng PyPDF2
        try:
            import PyPDF2
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                logger.warning(f"⚠️ PDF có {num_pages} trang nhưng là IMAGE-BASED")
        except:
            num_pages = "unknown"
        
        if pdf:
            pdf.close()
        
        # Sử dụng Tesseract OCR cho image-based PDF
        logger.info("📊 Sử dụng Tesseract OCR cho image-based PDF")
        return extract_pdf_with_tesseract(path)
    
    # PDF hợp lệ, tiếp tục với pdfplumber
    # --- Phân tích từng trang với pdfplumber + OCR ---
    logger.info("Đang phân tích từng trang (pdfplumber + EasyOCR)...")
    for i, page in enumerate(pdf.pages, 1):
        logger.debug(f"Đang xử lý trang {i}/{len(pdf.pages)}...")
        page_data = {"page_number": i, "text": "", "tables": [], "source": "manual"}
        
        text = page.extract_text(layout=False) or ""  # layout=False để giảm khoảng trắng
        text = clean_extracted_text(text)  # Làm sạch văn bản
        tables = page.extract_tables() or []
        
        # Làm sạch bảng nếu có
        if tables:
            tables = [clean_table_text(table) for table in tables]
        
        # Nếu trang có ít text và không có bảng -> khả năng là ảnh -> dùng OCR
        if len(text.strip()) < 100 and not tables:
            logger.info(f"Trang {i} có ít văn bản, đang chạy OCR (EasyOCR)...")
            ocr_text = ocr_on_page(page)
            page_data["text"] = clean_extracted_text(ocr_text)
            page_data["source"] = "ocr"
        else:
            page_data["text"] = text
            page_data["tables"] = tables
        
        pages.append(page_data)
    
    # Đóng PDF
    pdf.close()
    
    return pages

# --- MAIN SCRIPT EXECUTION ---
def main():
    from src.config import PDF_PATH
    if not os.path.exists(PDF_PATH):
        logger.error(f"Không tìm thấy file PDF tại đường dẫn trong config.py: `{PDF_PATH}`")
        return
    
    try:
        logger.info(f"🚀 Bắt đầu xử lý file: {PDF_PATH}...")
        extracted_pages = extract_pdf_pages(PDF_PATH)
        logger.info(f"✅ Hoàn thành! Trích xuất được {len(extracted_pages)} trang")
        
        if extracted_pages:
            p1 = extracted_pages[0]
            print("\n--- PREVIEW TRANG 1 ---")  # Giữ print cho output
            print(f"Nguồn: {p1['source']}")
            print(f"Nội dung: {p1['text'][:500]}...")
            if p1['tables']:
                print(f"Tìm thấy {len(p1['tables'])} bảng.")
            
    except Exception as e:
        logger.error(f"Đã xảy ra lỗi không mong muốn: {e}", exc_info=True)

if __name__ == "__main__":
    main()
