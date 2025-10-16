# Nơi tập trung các cấu hình cho dự án.

# **QUAN TRỌNG**: Đặt đường dẫn đến file PDF của bạn ở đây.
# Ví dụ: "C:\Users\MyUser\Documents\file.pdf"
# Hoặc có thể dùng đường dẫn tương đối nếu muốn, ví dụ: "data/file.pdf"
PDF_PATH = "d:/Project_self/Artificial-Intelligence-A-Modern-Approach-3rd-Edition (Ingles).pdf"


# --- CẤU HÌNH CHUNG CHO MODEL VÀ MILVUS ---

# Model embedding. 
# 'paraphrase-multilingual-mpnet-base-v2' (768 dims) là một model nhẹ và nhanh.
# 'intfloat/multilingual-e5-large-instruct' (1024 dims) là model mạnh hơn, cho kết quả tốt hơn.
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'

# Số chiều của vector embedding, phải tương ứng với model ở trên.
EMBEDDING_DIM = 768

# Tên collection trong Milvus để lưu trữ các vector.
COLLECTION_NAME = "pdf_rag_collection"

# --- CẤU HÌNH CHO OLLAMA ---

# URL của Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Danh sách các model Ollama để lựa chọn.
# Model đầu tiên trong danh sách sẽ là lựa chọn mặc định.
# Thêm các model khác vào đây, ví dụ: OLLAMA_MODELS = ["llama3:latest", "mistral:latest"]
OLLAMA_MODELS = [
    "llama3:latest"
]
