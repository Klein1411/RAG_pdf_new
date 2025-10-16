import os
import logging
import argparse
import pdfplumber
from typing import List, Dict
import numpy as np
# --- Thêm EasyOCR ---
import easyocr  # type: ignore
import torch

# 1) Tắt bớt warning của pdfplumber
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

# 2) Khởi tạo EasyOCR reader 1 lần. Tự động sử dụng GPU nếu có thể.
use_gpu = torch.cuda.is_available()
print(f"ℹ️ EasyOCR sẽ sử dụng {'GPU' if use_gpu else 'CPU'}.")
reader = easyocr.Reader(['vi', 'en'], gpu=use_gpu)

def ocr_on_page(page) -> str:
    """
    OCR toàn trang với EasyOCR, trả về chuỗi.
    """
    # Render toàn trang thành ảnh PIL với độ phân giải 300 DPI
    img = page.to_image(resolution=300).original

    # EasyOCR nhận ảnh dưới dạng numpy array
    results = reader.readtext(np.array(img))
    # results: list of (bbox, text, confidence)

    # Gom text theo thứ tự đọc
    texts = [text for _, text, _ in results]
    return "\n".join(texts)


def extract_pdf_pages(path: str) -> List[Dict]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # Trích xuất văn bản gốc từ PDF
            text = page.extract_text() or ""

            # Tables
            tables = page.extract_tables()
            table_infos = [{"rows": len(tbl),
                            "cols": max(len(r) for r in tbl) if tbl else 0}
                           for tbl in tables]

            # OCR với EasyOCR
            ocr_text = ocr_on_page(page)

            pages.append({
                "text": text,
                "tables": tables,
                "table_infos": table_infos,
                "ocr": ocr_text
            })
    return pages


def main():
    """
    Hàm chính để chạy script, xử lý tham số dòng lệnh và in kết quả.
    """
    parser = argparse.ArgumentParser(description="Trích xuất nội dung từ file PDF, bao gồm văn bản, bảng và OCR.")
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

        # In preview trang đầu tiên nếu có
        if extracted_pages:
            p1 = extracted_pages[0]
            print("--- PREVIEW TRANG 1 ---")
            print(f"🔹 Văn bản (1000 ký tự đầu): {p1['text'][:1000].replace(os.linesep, ' ')}...")
            if p1["table_infos"]:
                for i, info in enumerate(p1["table_infos"], 1):
                    print(f"🔸 Bảng {i}: {info['rows']} hàng × {info['cols']} cột")
            else:
                print("🔸 Không tìm thấy bảng nào trên trang 1.")
            if p1["ocr"]:
                print(f"🔹 OCR (100 ký tự đầu): {p1['ocr'][:100].replace(os.linesep, ' ')}...")
            else:
                print("🔸 OCR không nhận dạng được văn bản trên trang 1.")
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()
