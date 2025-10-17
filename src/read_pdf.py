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

# Import class GeminiClient
from src.gemini_client import GeminiClient
from src.logging_config import get_logger
from src.clean_pdf import clean_extracted_text, clean_table_text

# --- SETUP ---
logger = get_logger(__name__)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)

# --- HÀM XỬ LÝ VỚI GEMINI ---
def describe_pdf_with_gemini(images: List[Image.Image], gemini_client: GeminiClient) -> str:
    """
    Gửi tất cả ảnh của các trang PDF đến Gemini trong một yêu cầu duy nhất.
    """
    if not gemini_client:
        return "[Lỗi Gemini: Client chưa được cấu hình]"

    # Xây dựng prompt với hướng dẫn chi tiết
    prompt_parts = [
        '''Bạn là một chuyên gia phân tích tài liệu và slide thuyết trình.
Nhiệm vụ của bạn là xem một loạt hình ảnh của các trang tài liệu và chuyển đổi TOÀN BỘ tài liệu đó thành một văn bản Markdown chi tiết, có cấu trúc.

QUY TẮC QUAN TRỌNG:
1.  Xử lý từng ảnh theo thứ tự được cung cấp.
2.  Với mỗi ảnh (mỗi trang), hãy BẮT ĐẦU phần nội dung của trang đó bằng một dòng duy nhất chứa `--- PAGE [số trang] ---`. Ví dụ: `--- PAGE 1 ---`, `--- PAGE 2 ---`.
3.  Sau dòng phân cách đó, hãy trích xuất nội dung của trang đó theo định dạng Markdown:
    - Giữ lại các tiêu đề, đề mục.
    - Chuyển đổi các danh sách (bullet points) thành danh sách Markdown.
    - Trích xuất và tái tạo lại các bảng biểu một cách chính xác nhất có thể ở định dạng Markdown table.
    - Diễn giải và tóm tắt nội dung chính của trang một cách mạch lạc.
4.  Luôn trả lời bằng ngôn ngữ gốc của văn bản trong tài liệu.
5.  Đảm bảo rằng MỖI trang đều có một dòng phân cách `--- PAGE [số trang] ---` ở đầu.

Bây giờ, hãy bắt đầu xử lý các trang sau:
'''
    ]

    # Thêm tất cả các ảnh vào danh sách các phần của prompt
    prompt_parts.extend(images)

    try:
        logger.info(f"🧠 Đang gửi {len(images)} trang đến Gemini...")
        # generate_content của GeminiClient đã tự động trả về text
        response_text = gemini_client.generate_content(prompt_parts)
        return response_text
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi Gemini Vision cho toàn bộ PDF: {e}")
        return "[Lỗi Gemini: Không thể phân tích PDF]"

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

def gemini_ocr_on_page(page, vision_client: GeminiClient) -> str:
    """
    Sử dụng Gemini Vision để OCR một trang duy nhất.
    """
    if not vision_client:
        return "[Lỗi Gemini: Vision client chưa được cấu hình]"
    try:
        logger.debug("🧠 Gửi trang đến Gemini Vision để OCR...")
        img = page.to_image(resolution=300).original
        response_text = vision_client.generate_content(["Trích xuất toàn bộ văn bản từ hình ảnh này.", img])
        return response_text
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi Gemini Vision cho trang: {e}")
        return "[Lỗi Gemini: Không thể OCR trang]"

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

def count_images_in_pdf(pdf_path: str) -> int:
    """
    Đếm số lượng ảnh trong PDF.
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        
    Returns:
        Số lượng ảnh trong PDF
    """
    try:
        doc = fitz.open(pdf_path)
        total_images = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=False)
            total_images += len(image_list)
        
        doc.close()
        logger.info(f"📊 PDF có tổng cộng {total_images} ảnh")
        return total_images
        
    except Exception as e:
        logger.warning(f"⚠️ Không thể đếm ảnh trong PDF: {e}, mặc định = 0")
        return 0

def extract_pdf_with_gemini_ocr(pdf_path: str, gemini_client: GeminiClient) -> List[Dict]:
    """
    Extract toàn bộ PDF bằng Gemini OCR (cho PDF có ít ảnh).
    
    Args:
        pdf_path: Đường dẫn đến file PDF
        gemini_client: Gemini client đã khởi tạo
        
    Returns:
        List các trang với text đã OCR bằng Gemini
    """
    logger.info("🧠 Chuyển sang phương án Gemini OCR (chất lượng cao)")
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        logger.info(f"📄 PDF có {total_pages} trang, đang OCR bằng Gemini...")
        
        pages = []
        
        for page_num in range(total_pages):
            logger.info(f"   OCR trang {page_num + 1}/{total_pages} bằng Gemini...")
            
            page = doc[page_num]
            
            # Convert page to image (300 DPI)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            
            # OCR bằng Gemini
            text = gemini_ocr_on_page_from_image(image, gemini_client)
            
            # Clean text
            text = clean_extracted_text(text)
            
            # Tạo page data
            page_data = {
                "page_number": page_num + 1,
                "text": text,
                "tables": [],
                "source": "gemini-ocr"
            }
            
            pages.append(page_data)
        
        doc.close()
        
        logger.info(f"✅ Hoàn thành OCR {total_pages} trang bằng Gemini")
        return pages
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi OCR bằng Gemini: {e}")
        return []

def gemini_ocr_on_page_from_image(image: Image.Image, vision_client: GeminiClient) -> str:
    """
    Sử dụng Gemini Vision để OCR từ ảnh PIL.
    """
    if not vision_client:
        return "[Lỗi Gemini: Vision client chưa được cấu hình]"
    try:
        logger.debug("🧠 Gửi ảnh đến Gemini Vision để OCR...")
        prompt = "Hãy trích xuất TOÀN BỘ văn bản trong ảnh này. Giữ nguyên định dạng, bảng biểu và cấu trúc."
        response = vision_client.generate_content([prompt, image])
        return response if response else "[Lỗi: Gemini không trả về kết quả]"
    except Exception as e:
        logger.error(f"❌ Lỗi khi gọi Gemini Vision cho ảnh: {e}")
        return f"[Lỗi Gemini OCR: {str(e)}]"

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

# --- HÀM TRÍCH XUẤT CHÍNH (Logic kết hợp) ---
def extract_pdf_pages(path: str) -> List[Dict]:
    logger.info("✨ Cấu hình Gemini...")
    gemini_client = None
    vision_client = None
    
    try:
        gemini_client = GeminiClient()
        logger.info("✅ Gemini text client đã sẵn sàng với model fallback")
    except Exception as e:
        logger.warning(f"⚠️ Không thể cấu hình Gemini: {e}. Sẽ tự động dùng phương án 2")
    
    try:
        # Khởi tạo client cho vision tasks (có thể dùng cùng model hoặc model khác)
        vision_client = GeminiClient()
        logger.info("✅ Gemini vision client đã sẵn sàng với model fallback")
    except Exception as e:
        logger.warning(f"⚠️ Không thể cấu hình Gemini Vision: {e}. OCR bằng Gemini sẽ không khả dụng")

    # --- Hỏi người dùng lựa chọn phương án ---
    use_gemini = False
    if gemini_client: # Chỉ hỏi nếu Gemini có sẵn
        while True:
            choice = input("✨ Bạn có muốn sử dụng phương án 1 (Phân tích bằng Gemini Vision)? (Y/N): ").strip().upper()
            if choice in ['Y', 'N']:
                break
            print("   -> Lựa chọn không hợp lệ, vui lòng nhập Y hoặc N.")
        
        if choice == 'Y':
            use_gemini = True
            print("   -> Bạn đã chọn phương án 1 (Gemini Vision).")
        else:
            print("   -> Bạn đã chọn phương án 2 (Phân tích thủ công/OCR).")

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
        
        # ĐẾM SỐ ẢNH TRONG PDF ĐỂ CHỌN PHƯƠNG ÁN OCR
        image_count = count_images_in_pdf(path)
        
        # PHƯƠNG ÁN 2: CHỌN OCR DỰA TRÊN SỐ LƯỢNG ẢNH
        if image_count < 20 and gemini_client:
            logger.info(f"� PDF có {image_count} ảnh (< 20) → Sử dụng Gemini OCR (chất lượng cao)")
            return extract_pdf_with_gemini_ocr(path, gemini_client)
        else:
            if image_count >= 20:
                logger.info(f"📊 PDF có {image_count} ảnh (>= 20) → Sử dụng Tesseract OCR (tốc độ cao)")
            else:
                logger.info("📊 Gemini không khả dụng → Sử dụng Tesseract OCR")
            return extract_pdf_with_tesseract(path)
    
    # PDF hợp lệ, tiếp tục với pdfplumber
    # --- PHƯƠNG ÁN 1: DÙNG GEMINI (BULK) ---
    if use_gemini and gemini_client:
            logger.info(f"Đang chuẩn bị hình ảnh từ {len(pdf.pages)} trang cho Gemini...")
            all_page_images = [page.to_image(resolution=300).original for page in pdf.pages]
            
            # Gọi hàm mới để xử lý tất cả ảnh cùng lúc
            full_pdf_description = describe_pdf_with_gemini(all_page_images, gemini_client)

            # Nếu Gemini gặp lỗi, chuyển sang phương án 2
            if "[Lỗi Gemini" in full_pdf_description:
                logger.warning("Gemini gặp lỗi khi xử lý hàng loạt, chuyển sang phương án 2: Phân tích thủ công...")
                use_gemini = False # Đặt lại cờ để chạy logic fallback
            else:
                logger.info("Gemini phân tích toàn bộ PDF thành công! Đang xử lý kết quả...")
                # Tách kết quả trả về thành từng trang
                page_contents = full_pdf_description.split("--- PAGE ")
                
                for page_content in page_contents:
                    if not page_content.strip():
                        continue
                    
                    try:
                        # Tách số trang và nội dung
                        page_num_str, content = page_content.split(" ---", 1)
                        page_num = int(page_num_str.strip())
                        content = content.strip()
                        
                        pages.append({
                            "page_number": page_num,
                            "text": content,
                            "tables": [], # Gemini đã chuyển bảng thành Markdown trong text
                            "source": "gemini" # Đổi lại thành "gemini" để tương thích
                        })
                    except ValueError:
                        logger.warning(f"⚠️ Không thể phân tích nội dung trả về cho một trang: {page_content[:100]}...")
                        continue
                
                # Sắp xếp lại các trang để đảm bảo đúng thứ tự
                pages.sort(key=lambda p: p['page_number'])
                logger.info(f"✅ Đã xử lý và lưu lại {len(pages)} trang từ kết quả của Gemini")
                return pages # Trả về kết quả và kết thúc sớm

    # --- PHƯƠNG ÁN 2: THỦ CÔNG / OCR (FALLBACK) ---
    # Logic này sẽ chạy nếu người dùng không chọn Gemini ban đầu,
    # hoặc nếu Gemini gặp lỗi ở bước trên.
    logger.info("Đang phân tích từng trang theo phương án 2 (Thủ công/OCR)...")
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
            # Ưu tiên dùng Gemini Vision nếu có
            if vision_client:
                ocr_text = gemini_ocr_on_page(page, vision_client)
                page_data["text"] = clean_extracted_text(ocr_text)
                page_data["source"] = "gemini-ocr"
            else:
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
