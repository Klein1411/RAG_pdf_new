"""
Script test để kiểm tra logic đếm ảnh và chọn phương án OCR
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.read_pdf import count_images_in_pdf
from src.config import PDF_DIR

def test_image_counting():
    """Test đếm ảnh trong các PDF"""
    
    print("=" * 70)
    print("TEST LOGIC ĐẾM ẢNH TRONG PDF")
    print("=" * 70)
    
    pdf_dir = Path(PDF_DIR)
    
    if not pdf_dir.exists():
        print(f"❌ Thư mục PDF không tồn tại: {pdf_dir}")
        return
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ Không có file PDF nào trong {pdf_dir}")
        return
    
    print(f"\n📁 Tìm thấy {len(pdf_files)} file PDF\n")
    
    results = []
    
    for pdf_file in pdf_files:
        print(f"📄 Đang kiểm tra: {pdf_file.name}")
        
        try:
            image_count = count_images_in_pdf(str(pdf_file))
            file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
            
            # Quyết định phương án OCR
            if image_count < 20:
                ocr_method = "🧠 GEMINI OCR (< 20 ảnh)"
            else:
                ocr_method = "🔍 TESSERACT OCR (>= 20 ảnh)"
            
            results.append({
                'name': pdf_file.name,
                'images': image_count,
                'size_mb': file_size_mb,
                'method': ocr_method
            })
            
            print(f"   ✅ {image_count} ảnh | {file_size_mb:.2f} MB | {ocr_method}")
            
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
    
    # Tổng kết
    print("\n" + "=" * 70)
    print("TỔNG KẾT")
    print("=" * 70)
    
    if results:
        print(f"\n{'File':<40} {'Ảnh':>8} {'Size (MB)':>12} {'Phương án':<25}")
        print("-" * 90)
        
        for r in results:
            print(f"{r['name']:<40} {r['images']:>8} {r['size_mb']:>12.2f} {r['method']:<25}")
        
        # Thống kê
        gemini_count = sum(1 for r in results if '🧠' in r['method'])
        tesseract_count = sum(1 for r in results if '🔍' in r['method'])
        
        print("\n" + "-" * 90)
        print(f"📊 Thống kê:")
        print(f"   • {gemini_count} file sẽ dùng Gemini OCR (< 20 ảnh)")
        print(f"   • {tesseract_count} file sẽ dùng Tesseract OCR (>= 20 ảnh)")
    
    print("\n✅ KIỂM TRA HOÀN TẤT!")
    print("=" * 70)

if __name__ == "__main__":
    test_image_counting()
