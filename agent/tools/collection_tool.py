"""
Collection Tool - Tool quản lý Milvus collections.

Tách logic quản lý collection từ agent.py.
Wrap CollectionManager với interface thân thiện cho Agent.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add project root
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.collection_manager import get_collection_manager
from src.logging_config import get_logger

logger = get_logger(__name__)


class CollectionTool:
    """
    Tool quản lý Milvus collections.
    
    Chức năng:
    - List collections với metadata
    - Add/remove collections
    - Check collection status
    - Select collections cho agent
    """
    
    def __init__(self, collection_manager=None):
        """
        Khởi tạo Collection Tool.
        
        Args:
            collection_manager: CollectionManager instance (optional, sẽ tạo mới nếu không có)
        """
        self.collection_manager = collection_manager or get_collection_manager()
        logger.info("✅ CollectionTool initialized")
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """
        List tất cả collections với metadata.
        
        Returns:
            List of dicts với keys: name, num_entities, created_time
        """
        try:
            collections = self.collection_manager.list_collections()
            logger.info(f"📋 Found {len(collections)} collections")
            return collections
        except Exception as e:
            logger.error(f"❌ Error listing collections: {e}")
            return []
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin chi tiết của collection.
        
        Args:
            collection_name: Tên collection
            
        Returns:
            Dict với metadata hoặc None nếu không tồn tại
        """
        try:
            if not self.collection_manager.collection_exists(collection_name):
                logger.warning(f"⚠️ Collection '{collection_name}' không tồn tại")
                return None
            
            # Get info từ list_collections
            all_collections = self.collection_manager.list_collections()
            for col in all_collections:
                if col['name'] == collection_name:
                    logger.info(f"ℹ️ Collection '{collection_name}': {col}")
                    return col
            
            return None
        except Exception as e:
            logger.error(f"❌ Error getting collection info: {e}")
            return None
    
    def add_collection(self, pdf_path: str, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Tạo collection mới từ PDF.
        
        Args:
            pdf_path: Path đến file PDF
            force_rebuild: Nếu True, xóa collection cũ nếu có
            
        Returns:
            Dict với keys:
                - success: bool
                - collection_name: str
                - message: str
                - num_entities: int (nếu success)
        """
        try:
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                return {
                    'success': False,
                    'collection_name': None,
                    'message': f"PDF file không tồn tại: {pdf_path}"
                }
            
            collection_name = self.collection_manager.get_collection_name(pdf_path_obj.name)
            
            # Kiểm tra nếu đã tồn tại
            if self.collection_manager.collection_exists(collection_name):
                if force_rebuild:
                    logger.info(f"🔄 Rebuilding collection '{collection_name}'")
                    self.collection_manager.delete_collection(collection_name)
                else:
                    return {
                        'success': False,
                        'collection_name': collection_name,
                        'message': f"Collection '{collection_name}' đã tồn tại. Dùng force_rebuild=True để tạo lại."
                    }
            
            # Tạo collection
            logger.info(f"📦 Creating collection from {pdf_path_obj.name}...")
            col_name, success = self.collection_manager.create_and_populate_collection(str(pdf_path_obj))
            
            if success:
                # Get info từ list_collections
                info = self.get_collection_info(col_name)
                return {
                    'success': True,
                    'collection_name': col_name,
                    'message': f"Đã tạo collection '{col_name}' thành công",
                    'num_entities': info.get('num_entities', 0) if info else 0
                }
            else:
                return {
                    'success': False,
                    'collection_name': col_name,
                    'message': f"Không thể tạo collection cho {pdf_path_obj.name}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error creating collection: {e}")
            return {
                'success': False,
                'collection_name': None,
                'message': f"Lỗi: {str(e)}"
            }
    
    def remove_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        Xóa collection.
        
        Args:
            collection_name: Tên collection cần xóa
            
        Returns:
            Dict với keys:
                - success: bool
                - message: str
        """
        try:
            if not self.collection_manager.collection_exists(collection_name):
                return {
                    'success': False,
                    'message': f"Collection '{collection_name}' không tồn tại"
                }
            
            self.collection_manager.delete_collection(collection_name)
            logger.info(f"🗑️ Deleted collection '{collection_name}'")
            
            return {
                'success': True,
                'message': f"Đã xóa collection '{collection_name}'"
            }
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
            return {
                'success': False,
                'message': f"Lỗi khi xóa: {str(e)}"
            }
    
    def check_collection_status(self, collection_name: str) -> Dict[str, Any]:
        """
        Kiểm tra trạng thái collection.
        
        Args:
            collection_name: Tên collection
            
        Returns:
            Dict với keys:
                - exists: bool
                - num_entities: int (nếu exists)
                - status: str
                - message: str
        """
        try:
            if not self.collection_manager.collection_exists(collection_name):
                return {
                    'exists': False,
                    'status': 'not_found',
                    'message': f"Collection '{collection_name}' không tồn tại"
                }
            
            # Get info từ list_collections
            info = self.get_collection_info(collection_name)
            num_entities = info.get('num_entities', 0) if info else 0
            
            return {
                'exists': True,
                'num_entities': num_entities,
                'status': 'ready',
                'message': f"Collection '{collection_name}' sẵn sàng với {num_entities} entities"
            }
        except Exception as e:
            logger.error(f"❌ Error checking collection: {e}")
            return {
                'exists': False,
                'status': 'error',
                'message': f"Lỗi: {str(e)}"
            }
    
    def rebuild_collection(self, collection_name: str) -> Dict[str, Any]:
        """
        Rebuild collection (xóa và tạo lại).
        
        Args:
            collection_name: Tên collection
            
        Returns:
            Dict với keys:
                - success: bool
                - message: str
        """
        try:
            if not self.collection_manager.collection_exists(collection_name):
                return {
                    'success': False,
                    'message': f"Collection '{collection_name}' không tồn tại"
                }
            
            # Get PDF path from collection metadata
            # (Collection name là sanitized PDF name)
            # Cần tìm PDF file tương ứng
            from agent.pdf_manager import get_pdf_manager
            pdf_manager = get_pdf_manager()
            
            # Tìm PDF file
            pdfs = pdf_manager.list_pdfs()
            pdf_path = None
            for pdf in pdfs:
                if self.collection_manager.get_collection_name(pdf.name) == collection_name:
                    pdf_path = pdf
                    break
            
            if not pdf_path:
                return {
                    'success': False,
                    'message': f"Không tìm thấy PDF cho collection '{collection_name}'"
                }
            
            # Delete và recreate
            logger.info(f"🔄 Rebuilding collection '{collection_name}'...")
            self.collection_manager.delete_collection(collection_name)
            
            return self.add_collection(str(pdf_path), force_rebuild=False)
            
        except Exception as e:
            logger.error(f"❌ Error rebuilding collection: {e}")
            return {
                'success': False,
                'message': f"Lỗi khi rebuild: {str(e)}"
            }
    
    def batch_add_collections(
        self, 
        pdf_paths: List[str], 
        force_rebuild: bool = False,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Tạo nhiều collections cùng lúc.
        
        Args:
            pdf_paths: List các PDF paths
            force_rebuild: Nếu True, rebuild collections đã tồn tại
            show_progress: Hiển thị progress
            
        Returns:
            Dict với keys:
                - success_count: int
                - failed_count: int
                - results: List[Dict] - kết quả cho từng PDF
        """
        results = []
        success_count = 0
        failed_count = 0
        
        for i, pdf_path in enumerate(pdf_paths, 1):
            if show_progress:
                print(f"[{i}/{len(pdf_paths)}] Processing {Path(pdf_path).name}...")
            
            result = self.add_collection(pdf_path, force_rebuild)
            results.append({
                'pdf_path': pdf_path,
                **result
            })
            
            if result['success']:
                success_count += 1
                if show_progress:
                    print(f"   ✅ {result['message']}")
            else:
                failed_count += 1
                if show_progress:
                    print(f"   ❌ {result['message']}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }
    
    def get_collections_for_pdfs(self, pdf_names: List[str]) -> List[str]:
        """
        Lấy collection names từ PDF names.
        
        Args:
            pdf_names: List tên PDF (có thể có hoặc không có .pdf)
            
        Returns:
            List collection names
        """
        collection_names = []
        for pdf_name in pdf_names:
            col_name = self.collection_manager.get_collection_name(pdf_name)
            if self.collection_manager.collection_exists(col_name):
                collection_names.append(col_name)
            else:
                logger.warning(f"⚠️ Collection cho '{pdf_name}' không tồn tại")
        
        return collection_names
    
    def interactive_select_collections(
        self, 
        current_selection: Optional[List[str]] = None
    ) -> List[str]:
        """
        Interactive menu để chọn collections.
        
        Args:
            current_selection: Collections hiện đang được chọn
            
        Returns:
            List collection names được chọn
        """
        current_selection = current_selection or []
        all_collections = self.list_collections()
        
        if not all_collections:
            print("\n❌ Không có collection nào")
            return current_selection
        
        print("\n" + "="*60)
        print("CHỌN COLLECTIONS")
        print("="*60)
        
        print(f"\nCó sẵn ({len(all_collections)}):")
        for i, col in enumerate(all_collections, 1):
            status = "✓ ĐANG DÙNG" if col['name'] in current_selection else "  "
            print(f"{i}. [{status}] {col['name']} ({col['num_entities']} docs)")
        
        print(f"\nĐang dùng: {len(current_selection)} collections")
        
        print("\nTùy chọn:")
        print("  all      - Chọn tất cả")
        print("  none     - Bỏ chọn tất cả")
        print("  1,2,3    - Chọn theo số")
        print("  <Enter>  - Giữ nguyên")
        
        choice = input("\nChọn: ").strip().lower()
        
        if not choice:
            return current_selection
        elif choice == 'all':
            return [col['name'] for col in all_collections]
        elif choice == 'none':
            return []
        else:
            # Parse numbers
            selected = []
            for item in choice.split(','):
                item = item.strip()
                if item.isdigit():
                    idx = int(item) - 1
                    if 0 <= idx < len(all_collections):
                        selected.append(all_collections[idx]['name'])
            return selected


# Singleton pattern
_collection_tool = None

def get_collection_tool(collection_manager=None) -> CollectionTool:
    """
    Get hoặc tạo CollectionTool instance (singleton).
    
    Args:
        collection_manager: CollectionManager instance (optional)
        
    Returns:
        CollectionTool instance
    """
    global _collection_tool
    if _collection_tool is None:
        _collection_tool = CollectionTool(collection_manager)
    return _collection_tool


def reset_collection_tool():
    """Reset singleton (dùng cho testing)."""
    global _collection_tool
    _collection_tool = None


if __name__ == "__main__":
    # Test CollectionTool
    tool = get_collection_tool()
    
    print("\n=== Testing CollectionTool ===")
    
    # List collections
    print("\n1. List all collections:")
    collections = tool.list_collections()
    for col in collections:
        print(f"   - {col['name']}: {col['num_entities']} docs")
    
    # Check status
    if collections:
        print(f"\n2. Check status of first collection:")
        status = tool.check_collection_status(collections[0]['name'])
        print(f"   Status: {status}")
    
    print("\n✅ Test completed")
