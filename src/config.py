# Nơi tập trung các cấu hình cho dự án.

# **QUAN TRỌNG**: Đặt đường dẫn đến file PDF của bạn ở đây.
# Ví dụ: "C:\Users\MyUser\Documents\file.pdf"
# Hoặc có thể dùng đường dẫn tương đối nếu muốn, ví dụ: "data/pdfs/file.pdf"
PDF_PATH = "d:/Project_self/data/pdfs/metric.pdf"

# Thư mục chứa PDF files
PDF_DIR = "data/pdfs"

# Thư mục lưu file Markdown output
OUTPUT_DIR = "data/outputs"


# --- CẤU HÌNH CHUNG CHO MODEL VÀ MILVUS ---

# Model embedding. 
# 'paraphrase-multilingual-mpnet-base-v2' (768 dims) là một model nhẹ và nhanh.
# 'intfloat/multilingual-e5-large-instruct' (1024 dims) là model mạnh hơn, cho kết quả tốt hơn.
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'

# Số chiều của vector embedding, phải tương ứng với model ở trên.
EMBEDDING_DIM = 768

# Tên collection trong Milvus để lưu trữ các vector.
COLLECTION_NAME = "pdf_rag_collection"

# --- CẤU HÌNH CHO CHUNKING ---
# Kích thước chunk (ký tự) khi chia tài liệu
CHUNK_SIZE = 1000

# Số ký tự overlap giữa các chunk
CHUNK_OVERLAP = 200

# --- CẤU HÌNH CHO OLLAMA ---

# URL của Ollama API endpoint
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Danh sách các model Ollama để lựa chọn.
# Model đầu tiên trong danh sách sẽ là lựa chọn mặc định.
# Đảm bảo model đã được pull: ollama pull llama3:latest
OLLAMA_MODELS = [
    "llama3:latest",   # Llama 3 (mới nhất, khuyên dùng)
    "llama2",          # Llama 2 (cũ hơn)
    "mistral:latest"   # Mistral (nhẹ, nhanh)
]

# --- CẤU HÌNH CHO GEMINI ---
# Danh sách các model Gemini theo thứ tự ưu tiên (model đầu tiên là chính, các model sau là dự phòng)
# QUAN TRỌNG: Dùng format "models/..." để tương thích với google-generativeai library
GEMINI_MODELS = [
    "models/gemini-2.5-flash",     # Model mới nhất - Gemini 2.5 Flash (2025) ⚡
    "models/gemini-2.0-flash",     # Dự phòng 1 - Gemini 2.0 Flash (2024)
    "models/gemini-flash-latest",  # Dự phòng 2 - Alias cho model Flash mới nhất (stable)
    "models/gemini-pro-latest"     # Dự phòng 3 - Alias cho model Pro mới nhất (fallback)
]

GEMINI_INPUT_TOKEN_LIMIT = 1000000 # Giới hạn token an toàn cho prompt gửi đến Gemini (2.0 Flash hỗ trợ đến 1M tokens)
