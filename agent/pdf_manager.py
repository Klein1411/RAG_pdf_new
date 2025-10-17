"""
PDF Manager cho Agent.

Quản lý:
- Danh sách PDF files
- Export MD status
- Collection sync
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# Add project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import PDF_DIR, OUTPUT_DIR, COLLECTION_NAME
from src.logging_config import get_logger
from pymilvus import Collection, connections

logger = get_logger(__name__)


class PDFManager:
    """
    Quản lý PDF files và export status.
    """
    
    def __init__(self):
        """Khởi tạo PDF Manager."""
        self.pdf_dir = Path(PDF_DIR)
        self.output_dir = Path(OUTPUT_DIR)
        self.current_pdf = None  # Current active PDF
        
        # Ensure directories exist
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ PDFManager đã khởi tạo")
    
    def list_pdfs(self) -> List[Path]:
        """
        Lấy danh sách tất cả PDF files.
        
        Returns:
            List of PDF file paths
        """
        pdfs = sorted(self.pdf_dir.glob("*.pdf"))
        logger.info(f"📄 Tìm thấy {len(pdfs)} PDF files")
        return pdfs
    
    def get_md_path(self, pdf_path: Path) -> Path:
        """
        Lấy đường dẫn MD file tương ứng với PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Path to MD file
        """
        md_filename = pdf_path.stem + ".md"
        return self.output_dir / md_filename
    
    def check_md_exists(self, pdf_path: Path) -> bool:
        """
        Kiểm tra MD file có tồn tại không.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True nếu MD exists
        """
        md_path = self.get_md_path(pdf_path)
        exists = md_path.exists()
        
        if exists:
            logger.info(f"✅ MD file exists: {md_path.name}")
        else:
            logger.info(f"❌ MD file not found: {md_path.name}")
        
        return exists
    
    def get_file_info(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Lấy thông tin về PDF và MD file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict với file info
        """
        md_path = self.get_md_path(pdf_path)
        md_exists = md_path.exists()
        
        info = {
            'pdf_name': pdf_path.name,
            'pdf_path': str(pdf_path),
            'pdf_size': pdf_path.stat().st_size if pdf_path.exists() else 0,
            'md_name': md_path.name,
            'md_path': str(md_path),
            'md_exists': md_exists,
            'md_size': md_path.stat().st_size if md_exists else 0,
            'pdf_modified': datetime.fromtimestamp(pdf_path.stat().st_mtime) if pdf_path.exists() else None,
            'md_modified': datetime.fromtimestamp(md_path.stat().st_mtime) if md_exists else None
        }
        
        # Check if MD is outdated
        if md_exists and info['pdf_modified'] and info['md_modified']:
            info['md_outdated'] = info['pdf_modified'] > info['md_modified']
        else:
            info['md_outdated'] = False
        
        return info
    
    def select_pdf(self, pdf_name: Optional[str] = None) -> Optional[Path]:
        """
        Chọn PDF file để làm việc.
        
        Args:
            pdf_name: Tên PDF file (None = hỏi user chọn)
            
        Returns:
            Path to selected PDF, hoặc None nếu không chọn
        """
        pdfs = self.list_pdfs()
        
        if not pdfs:
            logger.warning("⚠️ Không có PDF nào trong thư mục")
            print("\n⚠️ Không tìm thấy PDF nào trong thư mục data/pdfs/")
            return None
        
        # If pdf_name specified, find it
        if pdf_name:
            for pdf in pdfs:
                if pdf.name == pdf_name or pdf.stem == pdf_name:
                    self.current_pdf = pdf
                    logger.info(f"📄 Đã chọn PDF: {pdf.name}")
                    return pdf
            
            logger.warning(f"⚠️ Không tìm thấy PDF: {pdf_name}")
            print(f"\n⚠️ Không tìm thấy PDF: {pdf_name}")
            return None
        
        # Otherwise, show menu
        print("\n📚 Danh sách PDF files:")
        for i, pdf in enumerate(pdfs, 1):
            info = self.get_file_info(pdf)
            size_mb = info['pdf_size'] / (1024 * 1024)
            status = "✅ (có MD)" if info['md_exists'] else "❌ (chưa MD)"
            outdated = " ⚠️ MD cũ" if info.get('md_outdated') else ""
            print(f"   {i}. {pdf.name} ({size_mb:.2f} MB) {status}{outdated}")
        
        # Get selection
        try:
            choice = input(f"\n👉 Chọn PDF (1-{len(pdfs)}) hoặc Enter để dùng tất cả: ").strip()
            
            if not choice:
                logger.info("📄 Sử dụng tất cả PDF files")
                self.current_pdf = None
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(pdfs):
                self.current_pdf = pdfs[idx]
                logger.info(f"📄 Đã chọn PDF: {self.current_pdf.name}")
                return self.current_pdf
            else:
                print("❌ Lựa chọn không hợp lệ")
                return None
                
        except ValueError:
            print("❌ Vui lòng nhập số")
            return None
        except KeyboardInterrupt:
            print("\n⚠️ Đã hủy")
            return None
    
    def should_export_md(self, pdf_path: Path) -> bool:
        """
        Hỏi user có muốn export MD không.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True nếu cần export
        """
        info = self.get_file_info(pdf_path)
        
        if not info['md_exists']:
            print(f"\n📝 MD file chưa tồn tại cho {pdf_path.name}")
            print("   ➡️ Cần export MD trước khi sử dụng RAG")
            return True
        
        if info.get('md_outdated'):
            print(f"\n⚠️ MD file cũ hơn PDF ({pdf_path.name})")
            print(f"   PDF modified: {info['pdf_modified']}")
            print(f"   MD modified: {info['md_modified']}")
        else:
            print(f"\n✅ MD file đã tồn tại cho {pdf_path.name}")
            print(f"   MD file: {info['md_name']} ({info['md_size'] / 1024:.2f} KB)")
        
        # Ask user
        try:
            choice = input("\n👉 Bạn có muốn export lại MD? (y/N): ").strip().lower()
            return choice in ['y', 'yes', 'có']
        except KeyboardInterrupt:
            print("\n⚠️ Giữ nguyên MD hiện tại")
            return False
    
    def check_collection(self) -> Dict[str, Any]:
        """
        Kiểm tra Milvus collection status.
        
        Returns:
            Dict với collection info
        """
        try:
            # Connect
            connections.connect(host="localhost", port="19530")
            
            # Load collection
            collection = Collection(COLLECTION_NAME)
            collection.load()
            
            num_entities = collection.num_entities
            
            info = {
                'exists': True,
                'name': COLLECTION_NAME,
                'num_entities': num_entities,
                'empty': num_entities == 0
            }
            
            logger.info(f"📊 Collection: {COLLECTION_NAME} ({num_entities} entities)")
            return info
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra collection: {e}")
            return {
                'exists': False,
                'name': COLLECTION_NAME,
                'error': str(e)
            }
    
    def should_reindex(self, will_export: bool) -> bool:
        """
        Hỏi user có muốn reindex collection không.
        
        Args:
            will_export: Có export MD mới không
            
        Returns:
            True nếu cần reindex
        """
        collection_info = self.check_collection()
        
        if not collection_info['exists']:
            print(f"\n❌ Collection '{COLLECTION_NAME}' không tồn tại")
            print("   ➡️ Cần tạo và index collection")
            return True
        
        if collection_info['empty']:
            print(f"\n⚠️ Collection '{COLLECTION_NAME}' đang trống")
            print("   ➡️ Cần index dữ liệu")
            return True
        
        print(f"\n✅ Collection đã có {collection_info['num_entities']} documents")
        
        if will_export:
            print("   ⚠️ Vì bạn sẽ export MD mới, nên cần reindex để đồng bộ")
            return True
        
        # Ask user
        try:
            choice = input("\n👉 Bạn có muốn reindex collection? (y/N): ").strip().lower()
            return choice in ['y', 'yes', 'có']
        except KeyboardInterrupt:
            print("\n⚠️ Giữ nguyên collection hiện tại")
            return False
    
    def get_current_pdf(self) -> Optional[Path]:
        """Lấy current PDF đang active."""
        return self.current_pdf


# --- CONVENIENCE FUNCTIONS ---

_pdf_manager = None

def get_pdf_manager() -> PDFManager:
    """Get singleton PDF manager instance."""
    global _pdf_manager
    if _pdf_manager is None:
        _pdf_manager = PDFManager()
    return _pdf_manager


# --- TEST ---
if __name__ == "__main__":
    print("=== Testing PDFManager ===\n")
    
    manager = PDFManager()
    
    # List PDFs
    print("1. Danh sách PDF files:")
    pdfs = manager.list_pdfs()
    for pdf in pdfs:
        info = manager.get_file_info(pdf)
        print(f"\n   PDF: {info['pdf_name']}")
        print(f"   Size: {info['pdf_size'] / 1024:.2f} KB")
        print(f"   MD exists: {info['md_exists']}")
        if info['md_exists']:
            print(f"   MD size: {info['md_size'] / 1024:.2f} KB")
            print(f"   Outdated: {info['md_outdated']}")
    
    # Check collection
    print("\n\n2. Collection status:")
    collection_info = manager.check_collection()
    print(f"   Exists: {collection_info.get('exists')}")
    if collection_info.get('exists'):
        print(f"   Entities: {collection_info.get('num_entities')}")
    
    print("\n=== Test completed ===")
