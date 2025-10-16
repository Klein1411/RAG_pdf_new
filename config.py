# Nơi tập trung các cấu hình cho dự án.

# **QUAN TRỌNG**: Đặt đường dẫn đến file PDF của bạn ở đây.
# Ví dụ: "C:\Users\MyUser\Documents\file.pdf"
# Hoặc có thể dùng đường dẫn tương đối nếu muốn, ví dụ: "data/file.pdf"
PDF_PATH = "d:/Project_self/metric.pdf"


# --- CẤU HÌNH CHUNG CHO MODEL VÀ MILVUS ---

# Model embedding. 
# 'paraphrase-multilingual-mpnet-base-v2' (768 dims) là một model nhẹ và nhanh.
# 'intfloat/multilingual-e5-large-instruct' (1024 dims) là model mạnh hơn, cho kết quả tốt hơn.
EMBEDDING_MODEL_NAME = 'intfloat/multilingual-e5-large-instruct'

# Số chiều của vector embedding, phải tương ứng với model ở trên.
EMBEDDING_DIM = 1024

# Tên collection trong Milvus để lưu trữ các vector.
COLLECTION_NAME = "pdf_rag_collection"