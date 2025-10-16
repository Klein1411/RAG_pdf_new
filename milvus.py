# %% [markdown]
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# .\venv\Scripts\activate

# %%
import os
from dotenv import load_dotenv

load_dotenv()  
MILVUS_HOST      = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT      = os.getenv("MILVUS_PORT", "19530")
print(f" Loaded GEMINI_API_KEY, Milvus at {MILVUS_HOST}:{MILVUS_PORT}")

# %%
from pymilvus import utility

existing = utility.list_collections()
collection_name = "pdf_vectors"
if collection_name in existing:
    utility.drop_collection(collection_name)
    print(f"🗑 Đã xóa collection `{collection_name}`")
else:
    print(f"ℹ️ Collection `{collection_name}` không tồn tại, bỏ qua bước xóa")

# %%
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

#  Định nghĩa schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)
]
schema = CollectionSchema(fields, description="RAG PDF embeddings")

#  Tạo hoặc load collection
collection_name = "pdf_vectors"
existing = utility.list_collections()
if collection_name not in existing:
    collection = Collection(name=collection_name, schema=schema)
    print(f"🆕 Created collection `{collection_name}`")
else:
    collection = Collection(name=collection_name)
    print(f"✔️ Loaded existing collection `{collection_name}`")


# %%



