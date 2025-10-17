"""
Collection Manager - Quản lý Milvus collections cho từng PDF.

Strategy:
- Mỗi PDF file có 1 collection riêng (tên = tên file PDF)
- LRU cache: Giữ N collections gần đây nhất
- Manual control: User có thể list/delete collections
- Auto-cleanup khi vượt limit
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

# Add project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pymilvus import Collection, connections, utility
from src.config import EMBEDDING_DIM
from src.logging_config import get_logger

logger = get_logger(__name__)


class CollectionManager:
    """
    Quản lý collections cho từng PDF file.
    """
    
    # Collection limit (LRU cache size)
    MAX_COLLECTIONS = 5  # Giữ tối đa 5 collections
    
    # Metadata file để track usage
    METADATA_FILE = Path("data/collection_metadata.json")
    
    def __init__(self):
        """Khởi tạo Collection Manager."""
        self.metadata = self._load_metadata()
        self._connect_milvus()
        logger.info("✅ CollectionManager đã khởi tạo")
    
    def _connect_milvus(self):
        """Connect to Milvus."""
        try:
            connections.connect(host="localhost", port="19530")
            logger.info("✅ Kết nối Milvus thành công")
        except Exception as e:
            logger.error(f"❌ Không thể kết nối Milvus: {e}")
            raise
    
    def _load_metadata(self) -> Dict:
        """Load collection metadata từ file."""
        if self.METADATA_FILE.exists():
            try:
                with open(self.METADATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Không thể load metadata: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """Save collection metadata to file."""
        try:
            self.METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            logger.info("✅ Đã lưu metadata")
        except Exception as e:
            logger.error(f"❌ Không thể lưu metadata: {e}")
    
    def get_collection_name(self, pdf_name: str) -> str:
        """
        Lấy collection name từ PDF name.
        
        Args:
            pdf_name: Tên file PDF (có thể có hoặc không có .pdf)
            
        Returns:
            Collection name (sanitized)
        """
        # Remove .pdf extension if exists
        if pdf_name.endswith('.pdf'):
            pdf_name = pdf_name[:-4]
        
        # Sanitize: chỉ giữ chữ, số, underscore (Milvus requirement)
        # Replace spaces, hyphen và special chars với underscore
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', pdf_name)
        
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Lowercase
        collection_name = sanitized.lower()
        
        # Ensure không bắt đầu bằng số
        if collection_name and collection_name[0].isdigit():
            collection_name = 'pdf_' + collection_name
        
        # Truncate if too long (Milvus limit is 255 chars)
        if len(collection_name) > 200:
            collection_name = collection_name[:200]
        
        logger.info(f"📛 Collection name: {collection_name} (from: {pdf_name})")
        return collection_name
    
    def collection_exists(self, collection_name: str) -> bool:
        """Kiểm tra collection có tồn tại không."""
        try:
            return utility.has_collection(collection_name)
        except Exception as e:
            logger.error(f"❌ Lỗi khi check collection: {e}")
            return False
    
    def create_collection(self, pdf_name: str) -> str:
        """
        Tạo collection mới cho PDF.
        
        Args:
            pdf_name: Tên PDF file
            
        Returns:
            Collection name
        """
        from pymilvus import CollectionSchema, FieldSchema, DataType
        
        collection_name = self.get_collection_name(pdf_name)
        
        # Check if exists
        if self.collection_exists(collection_name):
            logger.info(f"✅ Collection '{collection_name}' đã tồn tại")
            self._update_access_time(collection_name, pdf_name)
            return collection_name
        
        # Create schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="page", dtype=DataType.INT64),
            FieldSchema(name="pdf_source", dtype=DataType.VARCHAR, max_length=512)
        ]
        
        schema = CollectionSchema(fields, description=f"Collection for {pdf_name}")
        
        # Create collection
        collection = Collection(collection_name, schema)
        
        # Create index
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        collection.create_index("embedding", index_params)
        
        logger.info(f"✅ Đã tạo collection '{collection_name}'")
        
        # Update metadata
        self._update_access_time(collection_name, pdf_name)
        
        # Check và cleanup nếu vượt limit
        self._auto_cleanup()
        
        return collection_name
    
    def get_collection(self, pdf_name: str) -> Collection:
        """
        Lấy collection cho PDF.
        
        Args:
            pdf_name: Tên PDF file
            
        Returns:
            Collection instance
        """
        collection_name = self.get_collection_name(pdf_name)
        
        if not self.collection_exists(collection_name):
            logger.info(f"⚠️ Collection '{collection_name}' không tồn tại, tạo mới...")
            collection_name = self.create_collection(pdf_name)
        
        collection = Collection(collection_name)
        collection.load()
        
        # Update access time
        self._update_access_time(collection_name, pdf_name)
        
        return collection
    
    def _update_access_time(self, collection_name: str, pdf_name: str):
        """Update last access time của collection."""
        self.metadata[collection_name] = {
            'pdf_name': pdf_name,
            'last_accessed': datetime.now().isoformat(),
            'created': self.metadata.get(collection_name, {}).get('created', datetime.now().isoformat())
        }
        self._save_metadata()
    
    def list_collections(self) -> List[Dict]:
        """
        List tất cả collections với metadata.
        
        Returns:
            List of collection info
        """
        collections = []
        
        try:
            # Get all collections from Milvus
            all_collections = utility.list_collections()
            
            for col_name in all_collections:
                # Get metadata
                meta = self.metadata.get(col_name, {})
                
                # Get collection stats
                try:
                    collection = Collection(col_name)
                    collection.load()
                    num_entities = collection.num_entities
                except Exception as e:
                    logger.warning(f"⚠️ Không thể load collection {col_name}: {e}")
                    num_entities = 0
                
                collections.append({
                    'name': col_name,
                    'pdf_name': meta.get('pdf_name', 'Unknown'),
                    'num_entities': num_entities,
                    'last_accessed': meta.get('last_accessed', 'Unknown'),
                    'created': meta.get('created', 'Unknown')
                })
            
            # Sort by last accessed (newest first)
            collections.sort(key=lambda x: x['last_accessed'], reverse=True)
            
            logger.info(f"📋 Tìm thấy {len(collections)} collections")
            return collections
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi list collections: {e}")
            return []
    
    def delete_collection(self, collection_name_or_index: str, collections_list: Optional[List[Dict]] = None) -> bool:
        """
        Xóa một collection bằng tên hoặc số thứ tự.
        
        Args:
            collection_name_or_index: Tên collection hoặc số thứ tự (string)
            collections_list: List collections để resolve index (optional)
            
        Returns:
            True nếu xóa thành công
        """
        try:
            # Resolve collection name
            collection_name = None
            
            # Check if input is a number (index)
            if collection_name_or_index.isdigit():
                idx = int(collection_name_or_index) - 1  # Convert to 0-based index
                
                # Get collections list if not provided
                if collections_list is None:
                    collections_list = self.list_collections()
                
                # Validate index
                if 0 <= idx < len(collections_list):
                    collection_name = collections_list[idx]['name']
                    logger.info(f"🔢 Resolved index {idx+1} → {collection_name}")
                else:
                    logger.warning(f"⚠️ Index {idx+1} không hợp lệ (có {len(collections_list)} collections)")
                    return False
            else:
                # Input is collection name
                collection_name = collection_name_or_index
            
            # Check exists
            if not self.collection_exists(collection_name):
                logger.warning(f"⚠️ Collection '{collection_name}' không tồn tại")
                return False
            
            # Drop collection
            utility.drop_collection(collection_name)
            
            # Remove from metadata
            if collection_name in self.metadata:
                del self.metadata[collection_name]
                self._save_metadata()
            
            logger.info(f"✅ Đã xóa collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi xóa collection: {e}")
            return False
    
    def _auto_cleanup(self):
        """
        Auto cleanup collections cũ khi vượt limit.
        LRU strategy: Giữ N collections gần đây nhất.
        """
        collections = self.list_collections()
        
        if len(collections) <= self.MAX_COLLECTIONS:
            logger.info(f"✅ Số collections ({len(collections)}) trong giới hạn ({self.MAX_COLLECTIONS})")
            return
        
        # Xóa collections cũ nhất
        num_to_delete = len(collections) - self.MAX_COLLECTIONS
        collections_to_delete = collections[-num_to_delete:]
        
        logger.info(f"🗑️ Auto cleanup: Xóa {num_to_delete} collections cũ")
        
        for col_info in collections_to_delete:
            col_name = col_info['name']
            logger.info(f"   - Xóa: {col_name} (last accessed: {col_info['last_accessed']})")
            self.delete_collection(col_name)
    
    def delete_multiple_collections(self, indices_or_names: List[str]) -> int:
        """
        Xóa nhiều collections cùng lúc.
        
        Args:
            indices_or_names: List các số thứ tự hoặc tên collections
            
        Returns:
            Số collections đã xóa thành công
        """
        collections = self.list_collections()
        deleted_count = 0
        
        for item in indices_or_names:
            if self.delete_collection(item, collections):
                deleted_count += 1
        
        return deleted_count
    
    def cleanup_old_collections(self, keep_n: Optional[int] = None):
        """
        Manual cleanup: Giữ lại N collections gần đây nhất.
        
        Args:
            keep_n: Số collections giữ lại (None = dùng MAX_COLLECTIONS)
        """
        keep_n = keep_n or self.MAX_COLLECTIONS
        collections = self.list_collections()
        
        if len(collections) <= keep_n:
            print(f"\n✅ Chỉ có {len(collections)} collections, không cần cleanup")
            return
        
        # Show collections
        print(f"\n📋 Collections hiện tại ({len(collections)}):")
        for i, col in enumerate(collections, 1):
            status = "🔵 KEEP" if i <= keep_n else "🔴 DELETE"
            print(f"   {i}. {status} {col['name']}")
            print(f"      PDF: {col['pdf_name']}, Docs: {col['num_entities']}")
            print(f"      Last accessed: {col['last_accessed']}")
        
        # Confirm
        try:
            choice = input(f"\n⚠️ Xóa {len(collections) - keep_n} collections cũ? (y/N): ").strip().lower()
            if choice in ['y', 'yes', 'có']:
                deleted = 0
                for col in collections[keep_n:]:
                    if self.delete_collection(col['name']):
                        deleted += 1
                print(f"\n✅ Đã cleanup: Xóa {deleted} collections, giữ lại {keep_n} collections")
            else:
                print("\n⚠️ Đã hủy cleanup")
        except KeyboardInterrupt:
            print("\n⚠️ Đã hủy")
    
    def create_and_populate_collection(self, pdf_path: str) -> Tuple[Optional[str], bool]:
        """
        Tạo collection và index dữ liệu từ PDF.
        
        Args:
            pdf_path: Đường dẫn đến file PDF
            
        Returns:
            (collection_name, success)
        """
        from pathlib import Path
        
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            logger.error(f"❌ File PDF không tồn tại: {pdf_path}")
            return (None, False)
        
        pdf_name = pdf_path_obj.name
        
        # Create collection
        collection_name = self.create_collection(pdf_name)
        
        logger.info(f"📊 Đang index dữ liệu từ {pdf_name}...")
        
        try:
            # Import necessary modules
            from src.populate_milvus import get_embedding_model, chunk_text
            from pathlib import Path
            
            # Get collection
            collection = Collection(collection_name)
            
            # ĐỌC TỪ FILE MD thay vì extract từ PDF
            # Tìm file MD tương ứng trong thư mục OUTPUT_DIR
            from src.config import OUTPUT_DIR
            md_filename = pdf_path_obj.stem + '.md'  # Tên file không có .pdf
            md_path = Path(OUTPUT_DIR) / md_filename
            
            if not md_path.exists():
                logger.error(f"❌ Không tìm thấy file MD: {md_path}")
                logger.info(f"💡 Chạy 'export' để tạo file MD từ PDF trước")
                return (collection_name, False)
            
            logger.info(f"📄 Đọc từ file MD: {md_path}")
            
            # Đọc nội dung MD
            try:
                md_content = md_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"❌ Lỗi đọc file MD: {e}")
                return (collection_name, False)
            
            if not md_content or not md_content.strip():
                logger.warning(f"⚠️ File MD rỗng: {md_path}")
                return (collection_name, False)
            
            # Get embedding model
            embedding_model = get_embedding_model()
            
            # PHÂN TÍCH FILE MD THÀNH CÁC TRANG
            # File MD có format: "--- Trang X (Nguồn: ...) ---" để đánh dấu từng trang
            import re
            pages_dict = {}
            current_page = 1
            current_content = []
            
            for line in md_content.split('\n'):
                # Kiểm tra marker trang: "--- Trang 3 (Nguồn: gemini) ---"
                match = re.match(r'^---\s*Trang\s+(\d+)', line)
                if match:
                    # Lưu nội dung trang trước
                    if current_content:
                        pages_dict[current_page] = '\n'.join(current_content)
                        current_content = []
                    # Lấy số trang mới
                    current_page = int(match.group(1))
                else:
                    current_content.append(line)
            
            # Lưu trang cuối
            if current_content:
                pages_dict[current_page] = '\n'.join(current_content)
            
            # Nếu không có page markers, coi toàn bộ là page 1
            if not pages_dict:
                pages_dict[1] = md_content
            
            logger.info(f"📖 Tìm thấy {len(pages_dict)} trang trong file MD")
            
            # Prepare data
            all_texts = []
            all_pages = []
            all_sources = []
            
            # Chunk từng trang
            for page_num, text in pages_dict.items():
                if not text or not text.strip():
                    continue
                
                # Chunk text
                chunks = chunk_text(text)
                
                for chunk in chunks:
                    if chunk.strip():  # Chỉ thêm chunk không rỗng
                        all_texts.append(chunk)
                        all_pages.append(page_num)
                        all_sources.append(pdf_name)
            
            if not all_texts:
                logger.warning(f"⚠️ Không có text để index từ {pdf_name}")
                return (collection_name, False)
            
            logger.info(f"📝 Đang encode {len(all_texts)} chunks...")
            
            # Generate embeddings
            embeddings = embedding_model.encode(all_texts, show_progress_bar=True)
            
            # Insert to Milvus
            logger.info(f"💾 Đang insert vào collection {collection_name}...")
            
            data = [
                embeddings.tolist(),
                all_texts,
                all_pages,
                all_sources
            ]
            
            collection.insert(data)
            collection.flush()
            
            logger.info(f"✅ Đã index {len(all_texts)} chunks vào collection {collection_name}")
            
            return (collection_name, True)
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi index: {e}", exc_info=True)
            return (collection_name, False)
    
    def get_total_entities(self) -> int:
        """Tính tổng số entities trong tất cả collections."""
        total = 0
        for col_info in self.list_collections():
            total += col_info['num_entities']
        return total
    
    def print_status(self):
        """In ra status của tất cả collections."""
        collections = self.list_collections()
        total_entities = sum(col['num_entities'] for col in collections)
        
        print("\n" + "="*70)
        print("📊 COLLECTION STATUS")
        print("="*70)
        print(f"\nTổng số collections: {len(collections)} / {self.MAX_COLLECTIONS} (limit)")
        print(f"Tổng số documents: {total_entities}")
        
        if not collections:
            print("\n⚠️ Không có collection nào")
            return
        
        print("\n📋 Danh sách collections (sorted by last accessed):")
        print("-"*70)
        
        for i, col in enumerate(collections, 1):
            print(f"\n{i}. Collection: {col['name']}")
            print(f"   PDF: {col['pdf_name']}")
            print(f"   Documents: {col['num_entities']}")
            print(f"   Last accessed: {col['last_accessed']}")
            print(f"   Created: {col['created']}")
        
        print("\n" + "="*70)


# --- CONVENIENCE FUNCTIONS ---

_collection_manager = None

def get_collection_manager() -> CollectionManager:
    """Get singleton collection manager instance."""
    global _collection_manager
    if _collection_manager is None:
        _collection_manager = CollectionManager()
    return _collection_manager


# --- TEST & CLI ---

if __name__ == "__main__":
    print("=== Collection Manager CLI ===\n")
    
    manager = CollectionManager()
    
    while True:
        print("\n" + "="*50)
        print("🔧 Collection Manager")
        print("="*50)
        print("\n1. List collections")
        print("2. Create collection for PDF (chỉ tạo structure)")
        print("3. Create & Populate collection (tạo + index data)")
        print("4. Delete collection")
        print("5. Delete multiple collections")
        print("6. Cleanup old collections")
        print("7. Show status")
        print("8. Exit")
        
        try:
            choice = input("\n👉 Chọn (1-8): ").strip()
            
            if choice == '1':
                collections = manager.list_collections()
                if collections:
                    print(f"\n📋 {len(collections)} collections:")
                    for col in collections:
                        print(f"\n   - {col['name']}")
                        print(f"     PDF: {col['pdf_name']}")
                        print(f"     Docs: {col['num_entities']}")
                        print(f"     Last accessed: {col['last_accessed']}")
                else:
                    print("\n⚠️ Không có collection nào")
            
            elif choice == '2':
                # Import PDF_DIR để list PDFs
                from src.config import PDF_DIR
                from pathlib import Path
                
                pdf_dir = Path(PDF_DIR)
                if not pdf_dir.exists():
                    print(f"\n❌ Thư mục PDF không tồn tại: {PDF_DIR}")
                    continue
                
                # List PDF files
                pdf_files = sorted(pdf_dir.glob("*.pdf"))
                
                if not pdf_files:
                    print(f"\n⚠️ Không có file PDF nào trong {PDF_DIR}")
                    continue
                
                print(f"\n📚 Danh sách PDF files ({len(pdf_files)}):")
                print("-" * 70)
                
                for i, pdf_path in enumerate(pdf_files, 1):
                    pdf_name = pdf_path.name
                    collection_name = manager.get_collection_name(pdf_name)
                    exists = manager.collection_exists(collection_name)
                    
                    # Get collection info if exists
                    status = "✅ Đã có collection" if exists else "❌ Chưa có collection"
                    
                    size_mb = pdf_path.stat().st_size / (1024 * 1024)
                    
                    print(f"\n{i}. {pdf_name}")
                    print(f"   Size: {size_mb:.2f} MB")
                    print(f"   Collection: {collection_name}")
                    print(f"   Status: {status}")
                    
                    if exists:
                        try:
                            from pymilvus import Collection
                            col = Collection(collection_name)
                            col.load()
                            print(f"   Documents: {col.num_entities}")
                        except:
                            pass
                
                print("\n" + "-" * 70)
                
                # Get input
                pdf_input = input(f"\n📄 Chọn PDF (1-{len(pdf_files)}) hoặc nhập tên: ").strip()
                
                if not pdf_input:
                    print("\n⚠️ Đã hủy")
                    continue
                
                # Resolve PDF name
                pdf_name = None
                if pdf_input.isdigit():
                    idx = int(pdf_input) - 1
                    if 0 <= idx < len(pdf_files):
                        pdf_name = pdf_files[idx].name
                    else:
                        print(f"\n❌ Số thứ tự không hợp lệ")
                        continue
                else:
                    pdf_name = pdf_input
                    # Add .pdf if not present
                    if not pdf_name.endswith('.pdf'):
                        pdf_name += '.pdf'
                
                # Create collection
                print(f"\n⚙️ Đang tạo collection cho: {pdf_name}")
                
                col_name = manager.create_collection(pdf_name)
                print(f"\n✅ Collection đã tạo/sẵn sàng: {col_name}")
                print(f"\n💡 Lưu ý: Collection này sẽ được dùng để index dữ liệu từ {pdf_name}")
                print(f"   Bạn cần chạy populate/index để thêm dữ liệu vào collection.")
            
            elif choice == '3':
                # Create & Populate collection
                from src.config import PDF_DIR
                from pathlib import Path
                
                pdf_dir = Path(PDF_DIR)
                if not pdf_dir.exists():
                    print(f"\n❌ Thư mục PDF không tồn tại: {PDF_DIR}")
                    continue
                
                # List PDF files
                pdf_files = sorted(pdf_dir.glob("*.pdf"))
                
                if not pdf_files:
                    print(f"\n⚠️ Không có file PDF nào trong {PDF_DIR}")
                    continue
                
                print(f"\n📚 Danh sách PDF files ({len(pdf_files)}):")
                print("-" * 70)
                
                for i, pdf_path in enumerate(pdf_files, 1):
                    pdf_name = pdf_path.name
                    collection_name = manager.get_collection_name(pdf_name)
                    exists = manager.collection_exists(collection_name)
                    
                    status = "✅ Đã có" if exists else "❌ Chưa có"
                    size_mb = pdf_path.stat().st_size / (1024 * 1024)
                    
                    print(f"\n{i}. {pdf_name} ({size_mb:.2f} MB)")
                    print(f"   Collection: {collection_name} - {status}")
                
                print("\n" + "-" * 70)
                
                # Get input
                pdf_input = input(f"\n📄 Chọn PDF để index (1-{len(pdf_files)}): ").strip()
                
                if not pdf_input or not pdf_input.isdigit():
                    print("\n⚠️ Đã hủy")
                    continue
                
                idx = int(pdf_input) - 1
                if not (0 <= idx < len(pdf_files)):
                    print(f"\n❌ Số thứ tự không hợp lệ")
                    continue
                
                selected_pdf = pdf_files[idx]
                
                # Confirm
                print(f"\n⚙️ Sẽ tạo collection và index dữ liệu từ: {selected_pdf.name}")
                confirm = input("   Tiếp tục? (y/N): ").strip().lower()
                
                if confirm not in ['y', 'yes', 'có']:
                    print("\n⚠️ Đã hủy")
                    continue
                
                # Create and populate
                print(f"\n🚀 Đang xử lý {selected_pdf.name}...")
                col_name, success = manager.create_and_populate_collection(str(selected_pdf))
                
                if success:
                    print(f"\n✅ Hoàn thành! Collection: {col_name}")
                else:
                    print(f"\n❌ Có lỗi xảy ra, check logs để biết chi tiết")
            
            elif choice == '4':
                # Delete single collection
                collections = manager.list_collections()
                
                if not collections:
                    print("\n⚠️ Không có collection nào để xóa")
                else:
                    print(f"\n📋 Danh sách collections ({len(collections)}):")
                    for i, col in enumerate(collections, 1):
                        print(f"   {i}. {col['name']}")
                        print(f"      PDF: {col['pdf_name']}, Docs: {col['num_entities']}")
                        print(f"      Last accessed: {col['last_accessed']}")
                    
                    # Get input
                    col_input = input(f"\n🗑️ Nhập số (1-{len(collections)}) hoặc tên collection: ").strip()
                    
                    if col_input:
                        # Confirm
                        confirm = input(f"⚠️ Xác nhận xóa? (y/N): ").strip().lower()
                        if confirm in ['y', 'yes', 'có']:
                            if manager.delete_collection(col_input, collections):
                                print(f"\n✅ Đã xóa collection")
                            else:
                                print(f"\n❌ Không thể xóa collection")
                        else:
                            print("\n⚠️ Đã hủy")
            
            elif choice == '5':
                # Delete multiple collections
                collections = manager.list_collections()
                
                if not collections:
                    print("\n⚠️ Không có collection nào để xóa")
                else:
                    print(f"\n📋 Danh sách collections ({len(collections)}):")
                    for i, col in enumerate(collections, 1):
                        print(f"   {i}. {col['name']}")
                        print(f"      PDF: {col['pdf_name']}, Docs: {col['num_entities']}")
                    
                    # Get input
                    print("\n💡 Nhập số hoặc tên, cách nhau bằng dấu phẩy")
                    print("   Ví dụ: 1,3,5 hoặc collection1,collection2")
                    col_input = input("\n🗑️ Nhập: ").strip()
                    
                    if col_input:
                        # Parse input
                        items = [item.strip() for item in col_input.split(',')]
                        
                        # Confirm
                        confirm = input(f"\n⚠️ Xác nhận xóa {len(items)} collection(s)? (y/N): ").strip().lower()
                        if confirm in ['y', 'yes', 'có']:
                            deleted = manager.delete_multiple_collections(items)
                            print(f"\n✅ Đã xóa {deleted}/{len(items)} collections")
                        else:
                            print("\n⚠️ Đã hủy")
            
            elif choice == '6':
                manager.cleanup_old_collections()
            
            elif choice == '7':
                manager.print_status()
            
            elif choice == '8':
                print("\n👋 Tạm biệt!")
                break
            
            else:
                print("\n❌ Lựa chọn không hợp lệ")
        
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            logger.error(f"Error: {e}", exc_info=True)
