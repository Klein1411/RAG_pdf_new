import os
from dotenv import load_dotenv
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection
)
from src.logging_config import get_logger

logger = get_logger(__name__)

# 1. Tải các biến môi trường
load_dotenv()
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
DEFAULT_ALIAS = "default"

# --- CÁC HÀM ĐỂ TƯƠNG TÁC VỚI MILVUS ---

def connect_to_milvus():
    """
    Kết nối đến server Milvus.
    Hàm này an toàn để gọi nhiều lần.
    """
    try:
        # Kiểm tra xem đã có kết nối với alias này chưa
        if not connections.has_connection(DEFAULT_ALIAS):
            logger.info(f"Kết nối đến Milvus tại {MILVUS_HOST}:{MILVUS_PORT}")
            print(f"🔌 Đang kết nối đến Milvus tại {MILVUS_HOST}:{MILVUS_PORT}...")
            connections.connect(
                alias=DEFAULT_ALIAS,
                host=MILVUS_HOST,
                port=MILVUS_PORT
            )
            logger.info("Kết nối Milvus thành công")
            print("✅ Kết nối Milvus thành công!")
        else:
            logger.debug("Đã có kết nối Milvus sẵn")
    except Exception as e:
        logger.error(f"Không thể kết nối đến Milvus: {e}")
        print(f"❌ Lỗi không thể kết nối đến Milvus: {e}")
        raise

def get_or_create_collection(collection_name: str, dim: int = 768, recreate: bool = True) -> Collection:
    """
    Lấy hoặc tạo mới một collection trong Milvus.

    Args:
        collection_name (str): Tên của collection.
        dim (int): Số chiều của vector embedding.
        recreate (bool): Nếu True, sẽ xóa collection cũ nếu tồn tại và tạo lại.

    Returns:
        Collection: Đối tượng collection của Pymilvus.
    """
    connect_to_milvus() # Đảm bảo đã kết nối

    # Nếu yêu cầu tạo lại, sẽ xóa collection cũ
    if recreate and utility.has_collection(collection_name, using=DEFAULT_ALIAS):
        logger.info(f"Yêu cầu tạo lại, xóa collection '{collection_name}'")
        print(f"🗑️ Yêu cầu tạo lại, đang xóa collection '{collection_name}'...")
        utility.drop_collection(collection_name, using=DEFAULT_ALIAS)
        logger.info(f"Đã xóa collection '{collection_name}'")
        print(f"   -> Đã xóa collection '{collection_name}'.")

    # Kiểm tra lại sự tồn tại của collection
    if utility.has_collection(collection_name, using=DEFAULT_ALIAS):
        logger.info(f"Collection '{collection_name}' đã tồn tại, đang tải")
        print(f"✔️ Collection '{collection_name}' đã tồn tại. Đang tải...")
        return Collection(collection_name, using=DEFAULT_ALIAS)
    
    # --- Nếu collection chưa tồn tại, tạo mới ---
    logger.info(f"Collection '{collection_name}' chưa tồn tại, tạo mới")
    print(f"🆕 Collection '{collection_name}' chưa tồn tại. Đang tạo mới...")
    
    # Định nghĩa schema
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535, description="Nội dung của đoạn văn bản"),
        FieldSchema(name="pdf_source", dtype=DataType.VARCHAR, max_length=1024, description="Tên file PDF nguồn"),
        FieldSchema(name="page", dtype=DataType.INT64, description="Số trang trong file PDF")
    ]
    schema = CollectionSchema(fields, description=f"Embeddings for {collection_name}")

    # Tạo collection
    collection = Collection(
        name=collection_name,
        schema=schema,
        using=DEFAULT_ALIAS,
        consistency_level="Strong" # Đảm bảo dữ liệu được nhất quán
    )
    
    logger.info(f"Đã tạo collection '{collection_name}' thành công")
    print(f"   -> ✅ Đã tạo collection '{collection_name}' thành công.")
    
    logger.info("Tạo index cho collection")
    print("   -> Đang tạo index cho collection...")
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    logger.info("Index đã được tạo")
    print("      -> ✅ Index đã được tạo.")

    return collection

# --- KHỐI ĐỂ CHẠY THỬ NGHIỆM ---
if __name__ == "__main__":
    COLLECTION_NAME = "pdf_vectors_test"
    
    logger.info("=== BẮT ĐẦU KIỂM TRA MODULE MILVUS ===")
    print("--- BẮT ĐẦU KIỂM TRA MODULE MILVUS ---")
    
    # 1. Kết nối
    connect_to_milvus()
    
    # 2. Lấy hoặc tạo collection (với tùy chọn xóa và tạo lại)
    # Đặt recreate=True để đảm bảo collection luôn mới khi chạy file này
    collection = get_or_create_collection(COLLECTION_NAME, recreate=True)
    
    # 3. In thông tin
    logger.info(f"Thông tin collection: {collection.name}, {collection.num_entities} entities")
    print("\n--- THÔNG TIN COLLECTION ---")
    print(f"Tên: {collection.name}")
    print(f"Schema: {collection.schema}")
    print(f"Số lượng thực thể: {collection.num_entities}")
    
    # 4. Xóa collection test để dọn dẹp
    logger.info("Dọn dẹp collection test")
    print(f"\n--- DỌN DẸP ---")
    utility.drop_collection(COLLECTION_NAME, using=DEFAULT_ALIAS)
    logger.info(f"Đã xóa collection test '{COLLECTION_NAME}'")
    print(f"🗑️ Đã xóa collection test '{COLLECTION_NAME}'.")
    
    logger.info("=== KIỂM TRA HOÀN TẤT ===")
    print("\n--- KIỂM TRA HOÀN TẤT ---")