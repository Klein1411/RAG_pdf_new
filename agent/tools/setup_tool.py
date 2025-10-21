"""
Setup Tool - Tool xử lý setup workflow cho Agent.

Tách toàn bộ logic setup từ agent.py.
Handles: PDF selection, MD export, collection creation, topic building.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple

# Add project root
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.pdf_manager import get_pdf_manager
from agent.collection_manager import get_collection_manager
from agent.tools.collection_tool import get_collection_tool
from agent.tools.export_tool import get_export_tool
from agent.tools.topic_tool import get_topic_tool
from src.export_md import convert_to_markdown
from src.logging_config import get_logger

logger = get_logger(__name__)


class SetupTool:
    """
    Tool xử lý setup workflow cho Agent.
    
    Workflow:
    1. Select PDFs
    2. Export MD (nếu chưa có)
    3. Create/select collections
    4. Build topics
    """
    
    def __init__(
        self,
        pdf_manager=None,
        collection_manager=None,
        collection_tool=None,
        export_tool=None,
        topic_tool=None
    ):
        """
        Khởi tạo Setup Tool.
        
        Args:
            pdf_manager: PDFManager instance
            collection_manager: CollectionManager instance
            collection_tool: CollectionTool instance
            export_tool: ExportTool instance
            topic_tool: TopicTool instance
        """
        self.pdf_manager = pdf_manager or get_pdf_manager()
        self.collection_manager = collection_manager or get_collection_manager()
        self.collection_tool = collection_tool or get_collection_tool()
        self.export_tool = export_tool or get_export_tool()
        self.topic_tool = topic_tool or get_topic_tool()
        
        logger.info("✅ SetupTool initialized")
    
    def setup_workflow(self, re_setup: bool = False) -> Dict[str, Any]:
        """
        Complete setup workflow - interactive.
        
        Args:
            re_setup: Nếu True, cho phép re-setup
            
        Returns:
            Dict với keys:
                - success: bool
                - selected_pdfs: List[Path]
                - selected_collections: List[str]
                - topics_built: bool
                - message: str
        """
        print("\n" + "="*70)
        print("SETUP AGENT - Multi-PDF RAG System")
        print("="*70)
        
        # Step 1: Select PDFs
        selected_pdfs = self.interactive_select_pdfs()
        if not selected_pdfs:
            return {
                'success': False,
                'selected_pdfs': [],
                'selected_collections': [],
                'topics_built': False,
                'message': 'Chưa chọn PDF nào'
            }
        
        # Step 2: Export MD
        md_results = self.batch_export_md(selected_pdfs)
        
        # Step 3: Create/select collections
        collection_results = self.batch_create_collections(selected_pdfs)
        selected_collections = collection_results['selected_collections']
        
        if not selected_collections:
            return {
                'success': False,
                'selected_pdfs': selected_pdfs,
                'selected_collections': [],
                'topics_built': False,
                'message': 'Không có collection nào sẵn sàng'
            }
        
        # Step 4: Build topics
        topics_built = self.build_topics(selected_collections)
        
        print("\n" + "="*70)
        print(f"SẴN SÀNG! PDFs: {len(selected_pdfs)} | Collections: {len(selected_collections)}")
        print("="*70)
        
        return {
            'success': True,
            'selected_pdfs': selected_pdfs,
            'selected_collections': selected_collections,
            'topics_built': topics_built,
            'message': f'Setup thành công với {len(selected_pdfs)} PDFs và {len(selected_collections)} collections'
        }
    
    def interactive_select_pdfs(self) -> List[Path]:
        """
        Interactive PDF selection.
        
        Returns:
            List of selected PDF paths
        """
        print("\nSTEP 1: Select PDF files")
        print("-" * 70)
        
        pdfs = self.pdf_manager.list_pdfs()
        if not pdfs:
            print(f"\nKhông tìm thấy file PDF trong: {self.pdf_manager.pdf_dir}")
            return []
        
        # Hiển thị danh sách PDF với thông tin chi tiết
        print(f"\n{len(pdfs)} file PDF:")
        for i, pdf in enumerate(pdfs, 1):
            info = self.pdf_manager.get_file_info(pdf)
            size_mb = info['pdf_size'] / (1024 * 1024)
            col_name = self.collection_manager.get_collection_name(pdf.name)
            has_collection = self.collection_manager.collection_exists(col_name)
            md_status = "✓MD" if info['md_exists'] else "  "
            col_status = "✓Col" if has_collection else "   "
            print(f"{i}. [{md_status}][{col_status}] {pdf.name} ({size_mb:.1f}MB)")
        
        print("\nChọn: 'all', số (1,2,3), hoặc tên file")
        choice = input("Chọn PDF: ").strip().lower()
        
        # Xử lý lựa chọn
        if not choice or choice == 'all':
            selected = pdfs
        else:
            selected = []
            items = [item.strip() for item in choice.split(',')]
            for item in items:
                if item.isdigit():
                    idx = int(item) - 1
                    if 0 <= idx < len(pdfs):
                        selected.append(pdfs[idx])
                else:
                    for pdf in pdfs:
                        if item in pdf.name.lower():
                            selected.append(pdf)
                            break
        
        print(f"\nĐã chọn {len(selected)} PDF")
        return selected
    
    def batch_export_md(self, pdf_paths: List[Path], force: bool = False) -> Dict[str, Any]:
        """
        Export nhiều PDFs sang MD.
        
        Args:
            pdf_paths: List PDF paths
            force: Nếu True, export lại dù đã có MD
            
        Returns:
            Dict với keys:
                - exported_count: int
                - skipped_count: int
                - failed_count: int
                - results: List[Dict]
        """
        print("\nSTEP 2: Export MD files")
        print("-" * 70)
        
        # Tìm PDF cần export
        pdfs_need_export = []
        for pdf in pdf_paths:
            info = self.pdf_manager.get_file_info(pdf)
            if force or not info['md_exists']:
                pdfs_need_export.append(pdf)
        
        if not pdfs_need_export:
            print("\n✅ Tất cả PDF đã có file MD")
            return {
                'exported_count': 0,
                'skipped_count': len(pdf_paths),
                'failed_count': 0,
                'results': []
            }
        
        # Hỏi user
        print(f"\n{len(pdfs_need_export)} PDF cần export sang MD")
        export_choice = input(f"Export MD cho các PDF này? (Y/n): ").strip().lower()
        
        if export_choice not in ['', 'y', 'yes', 'có']:
            print("⏭️  Bỏ qua export MD")
            return {
                'exported_count': 0,
                'skipped_count': len(pdf_paths),
                'failed_count': 0,
                'results': []
            }
        
        # Export
        print(f"\nĐang export {len(pdfs_need_export)} file MD...")
        exported = 0
        failed = 0
        results = []
        
        for i, pdf in enumerate(pdfs_need_export, 1):
            try:
                print(f"[{i}/{len(pdfs_need_export)}] {pdf.name}...", end=" ")
                md_content = convert_to_markdown(str(pdf))
                md_path = self.pdf_manager.get_md_path(pdf)
                md_path.write_text(md_content, encoding='utf-8')
                print("✅ OK")
                exported += 1
                results.append({
                    'pdf': str(pdf),
                    'success': True,
                    'md_path': str(md_path)
                })
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                failed += 1
                results.append({
                    'pdf': str(pdf),
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'exported_count': exported,
            'skipped_count': len(pdf_paths) - len(pdfs_need_export),
            'failed_count': failed,
            'results': results
        }
    
    def batch_create_collections(
        self, 
        pdf_paths: List[Path],
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Tạo collections cho nhiều PDFs.
        
        Args:
            pdf_paths: List PDF paths
            force_rebuild: Nếu True, rebuild collections đã tồn tại
            
        Returns:
            Dict với keys:
                - created_count: int
                - reused_count: int
                - failed_count: int
                - selected_collections: List[str]
        """
        print("\nSTEP 3: Create/select collections")
        print("-" * 70)
        
        pdfs_need_collection = []
        existing_collections = []
        pdfs_with_existing = []
        
        # Phân loại PDF
        for pdf in pdf_paths:
            col_name = self.collection_manager.get_collection_name(pdf.name)
            if self.collection_manager.collection_exists(col_name):
                pdfs_with_existing.append((pdf, col_name))
                existing_collections.append(col_name)
            else:
                pdfs_need_collection.append(pdf)
        
        # Xử lý collections đã tồn tại
        rebuild_all = False
        
        if pdfs_with_existing and not force_rebuild:
            print(f"\n✅ {len(pdfs_with_existing)} PDF đã có collection:")
            for pdf, col_name in pdfs_with_existing:
                print(f"   - {pdf.name} → {col_name}")
            
            print("\nTùy chọn:")
            print("  1. Sử dụng lại (nhanh)")
            print("  2. Rebuild tất cả (chậm)")
            
            rebuild_choice = input("\nChọn (1/2, mặc định=1): ").strip()
            
            if rebuild_choice == '2':
                rebuild_all = True
                print("\n🔄 Sẽ rebuild tất cả collection...")
                for pdf, col_name in pdfs_with_existing:
                    print(f"   Đang xóa {col_name}...")
                    self.collection_manager.delete_collection(col_name)
                    pdfs_need_collection.append(pdf)
                existing_collections = []
            else:
                print("\n✅ Sử dụng lại collections hiện có")
        
        # Tạo collections mới
        created = 0
        failed = 0
        
        if pdfs_need_collection:
            action = "rebuild" if rebuild_all else "tạo"
            print(f"\n{len(pdfs_need_collection)} PDF cần {action} collection")
            create_choice = input(f"{action.capitalize()} collection? (Y/n): ").strip().lower()
            
            if create_choice in ['', 'y', 'yes', 'có']:
                for i, pdf in enumerate(pdfs_need_collection, 1):
                    try:
                        print(f"[{i}/{len(pdfs_need_collection)}] Đang index {pdf.name}...")
                        col_name, success = self.collection_manager.create_and_populate_collection(str(pdf))
                        if success:
                            existing_collections.append(col_name)
                            created += 1
                            print(f"   ✅ OK: {col_name}")
                        else:
                            failed += 1
                            print(f"   ❌ Failed")
                    except Exception as e:
                        failed += 1
                        print(f"   ❌ Lỗi: {e}")
        
        reused = len(pdfs_with_existing) if not rebuild_all else 0
        
        print(f"\n📊 Kết quả: {created} tạo mới | {reused} sử dụng lại | {failed} lỗi")
        
        return {
            'created_count': created,
            'reused_count': reused,
            'failed_count': failed,
            'selected_collections': existing_collections
        }
    
    def build_topics(
        self, 
        collection_names: List[str],
        sample_size: int = 30
    ) -> bool:
        """
        Build topic suggestions từ collections.
        
        Args:
            collection_names: List collection names
            sample_size: Số documents sample từ mỗi collection
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        print("\nSTEP 4: Build topic suggestions")
        print("-" * 70)
        
        try:
            print("Đang phân tích tài liệu để tạo gợi ý chủ đề...")
            self.topic_tool.build_topics(
                collection_names=collection_names,
                sample_size=sample_size
            )
            print("✅ Đã xây dựng topic suggestions")
            return True
        except Exception as e:
            logger.warning(f"Could not build topics: {e}")
            print("⚠️  Không thể tạo topic suggestions (có thể tiếp tục)")
            return False
    
    def quick_setup(
        self,
        pdf_paths: Optional[List[Path]] = None,
        auto_export: bool = True,
        auto_create_collections: bool = True,
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        Quick setup không cần interaction.
        
        Args:
            pdf_paths: List PDF paths (nếu None, chọn tất cả)
            auto_export: Tự động export MD
            auto_create_collections: Tự động tạo collections
            force_rebuild: Rebuild collections đã tồn tại
            
        Returns:
            Dict với kết quả setup
        """
        logger.info("🚀 Quick setup started")
        
        # Select PDFs
        if pdf_paths is None:
            pdf_paths = self.pdf_manager.list_pdfs()
        
        if not pdf_paths:
            return {
                'success': False,
                'selected_pdfs': [],
                'selected_collections': [],
                'message': 'No PDFs found'
            }
        
        # Export MD
        if auto_export:
            self.batch_export_md(pdf_paths, force=False)
        
        # Create collections
        selected_collections = []
        if auto_create_collections:
            results = self.batch_create_collections(pdf_paths, force_rebuild)
            selected_collections = results['selected_collections']
        
        # Build topics
        topics_built = False
        if selected_collections:
            topics_built = self.build_topics(selected_collections)
        
        return {
            'success': len(selected_collections) > 0,
            'selected_pdfs': pdf_paths,
            'selected_collections': selected_collections,
            'topics_built': topics_built,
            'message': f'Quick setup: {len(pdf_paths)} PDFs, {len(selected_collections)} collections'
        }


# Singleton pattern
_setup_tool = None

def get_setup_tool(
    pdf_manager=None,
    collection_manager=None,
    collection_tool=None,
    export_tool=None,
    topic_tool=None
) -> SetupTool:
    """
    Get hoặc tạo SetupTool instance (singleton).
    
    Returns:
        SetupTool instance
    """
    global _setup_tool
    if _setup_tool is None:
        _setup_tool = SetupTool(
            pdf_manager=pdf_manager,
            collection_manager=collection_manager,
            collection_tool=collection_tool,
            export_tool=export_tool,
            topic_tool=topic_tool
        )
    return _setup_tool


def reset_setup_tool():
    """Reset singleton (dùng cho testing)."""
    global _setup_tool
    _setup_tool = None


if __name__ == "__main__":
    # Test SetupTool
    tool = get_setup_tool()
    
    print("\n=== Testing SetupTool ===")
    print("\n1. Quick setup test:")
    
    result = tool.quick_setup(
        pdf_paths=None,  # Use all PDFs
        auto_export=False,  # Skip export for test
        auto_create_collections=False  # Skip creation for test
    )
    
    print(f"\nResult: {result['success']}")
    print(f"Message: {result['message']}")
    
    print("\n✅ Test completed")
