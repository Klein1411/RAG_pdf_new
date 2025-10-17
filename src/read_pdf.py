import os
import logging
import pdfplumber
from typing import List, Dict
import warnings
from PIL import Image
import numpy as np
import torch
import easyocr

# Import class GeminiClient
from src.gemini_client import GeminiClient
from src.logging_config import get_logger

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

# --- HÀM TRÍCH XUẤT CHÍNH (Logic kết hợp) ---
def extract_pdf_pages(path: str) -> List[Dict]:
    logger.info("✨ Cấu hình Gemini...")
    gemini_client = None
    vision_client = None
    
    try:
        # Khởi tạo client - sẽ tự động sử dụng danh sách model từ config.py
        # Model mặc định: gemini-2.0-flash-exp → gemini-1.5-flash → gemini-1.5-flash-8b
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
    with pdfplumber.open(path) as pdf:
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
            
            text = page.extract_text(layout=True) or ""
            tables = page.extract_tables() or []
            
            # Nếu trang có ít text và không có bảng -> khả năng là ảnh -> dùng OCR
            if len(text.strip()) < 100 and not tables:
                # Ưu tiên dùng Gemini Vision nếu có
                if vision_client:
                    page_data["text"] = gemini_ocr_on_page(page, vision_client)
                    page_data["source"] = "gemini-ocr"
                else:
                    logger.info(f"Trang {i} có ít văn bản, đang chạy OCR (EasyOCR)...")
                    page_data["text"] = ocr_on_page(page)
                    page_data["source"] = "ocr"
            else:
                page_data["text"] = text
                page_data["tables"] = tables
            
            pages.append(page_data)
            
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
