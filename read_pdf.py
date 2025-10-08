import os
import logging
import pdfplumber
from typing import List, Dict
import numpy as np    
# --- Thêm EasyOCR ---
import easyocr

# 1) Tắt bớt warning của pdfplumber
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

# 2) Khởi tạo EasyOCR reader 1 lần (chỉ hỗ trợ CPU ở đây)
reader = easyocr.Reader(['vi','en'], gpu=False)

def ocr_on_page(page) -> str:
    """
    OCR toàn trang với EasyOCR, trả về chuỗi.
    """
    # Render toàn trang thành ảnh PIL
    img = page.to_image(resolution=300).original  # PIL.Image

    # EasyOCR nhận PIL.Image trực tiếp
    results = reader.readtext(np.array(img))
    # results: list of (bbox, text, confidence)

    # Gom text theo thứ tự đọc
    texts = [text for _, text, _ in results]
    return "\n".join(texts)


def extract_pdf_pages(path: str) -> List[Dict]:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # Text + decode
            raw = page.extract_text() or ""
            text = raw.encode("utf-8", "ignore").decode("utf-8", "ignore")

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


if __name__ == "__main__":
    pdf_path = "metric.pdf"
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy `{pdf_path}`")

    pg = extract_pdf_pages(pdf_path)
    print(f"✅ Loaded {len(pg)} pages from `{pdf_path}`\n")

    # In preview trang 1
    p1 = pg[0]
    print("🔹 Text (1000 chars):", p1["text"][:1000].replace("\n"," "), "...")
    if p1["table_infos"]:
        for i,info in enumerate(p1["table_infos"],1):
            print(f"🔸 Table {i}: {info['rows']}×{info['cols']}")
    else:
        print("🔸 No tables on page 1")
    if p1["ocr"]:
        print("🔹 OCR (100 chars):", p1["ocr"][:100].replace("\n"," "), "...")
    else:
        print("🔸 No text detected by OCR on page 1")
