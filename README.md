# 🚀 RAG PDF System với Gemini AI

Hệ thống Retrieval-Augmented Generation (RAG) để xử lý PDF với OCR, embedding và Q&A sử dụng Gemini AI, Milvus vector database và LangChain.

---

## 📋 Mục lục

- [✨ Tính năng](#-tính-năng)
- [🏗️ Kiến trúc hệ thống](#️-kiến-trúc-hệ-thống)
- [⚡ Quick Start](#-quick-start)
- [📦 Cài đặt](#-cài-đặt)
- [🔧 Cấu hình](#-cấu-hình)
- [🎯 Sử dụng](#-sử-dụng)
- [🤖 Gemini Multi-Model](#-gemini-multi-model)
- [📝 Logging](#-logging)
- [🧪 Testing](#-testing)
- [📚 Documentation](#-documentation)
- [🛠️ Troubleshooting](#️-troubleshooting)

---

## ✨ Tính năng

### 🔍 Xử lý PDF
- ✅ Trích xuất text từ PDF với **pdfplumber**
- ✅ OCR hình ảnh với **Gemini Vision** hoặc **EasyOCR**
- ✅ Phát hiện và trích xuất bảng biểu
- ✅ Hỗ trợ PDF nhiều trang

### 🧠 AI & RAG
- ✅ **Multi-model Gemini** với auto-fallback (2.0 Flash → 1.5 Flash → 1.5 Flash 8B)
- ✅ **Multi-key rotation** tự động khi hết quota
- ✅ Vector embedding với **SentenceTransformer**
- ✅ Semantic search với **Milvus** vector database
- ✅ Context expansion cho câu trả lời chính xác hơn
- ✅ Fallback Ollama cho local inference

### 📊 Data Pipeline
- ✅ Chunking thông minh dựa trên ranh giới câu (NLTK)
- ✅ Export sang Markdown
- ✅ Đồng bộ tự động vào Milvus
- ✅ Logging chi tiết cho toàn bộ pipeline

### 💬 Q&A Application
- ✅ Interactive Q&A với streaming
- ✅ Hiển thị nguồn tham khảo (trang PDF)
- ✅ Retry và fallback thông minh
- ✅ Token counting để tránh vượt limit

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                      RAG PDF SYSTEM                         │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PDF File   │────▶│  read_pdf.py │────▶│ export_md.py │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                     ┌──────▼──────┐              │
                     │ Gemini OCR  │              │
                     │ EasyOCR     │              │
                     └─────────────┘              │
                                                  │
                     ┌────────────────────────────▼────┐
                     │      Markdown Output            │
                     └────────────────┬────────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │   populate_milvus.py            │
                     │   - Chunking (NLTK)             │
                     │   - Embedding (SentenceTransf.) │
                     │   - Insert to Milvus            │
                     └────────────────┬────────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │      Milvus Vector DB           │
                     │      (IVF_FLAT Index)           │
                     └────────────────┬────────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │         qa_app.py               │
                     │   - User Query                  │
                     │   - Semantic Search             │
                     │   - Context Expansion           │
                     │   - LLM Generation (Gemini)     │
                     └─────────────────────────────────┘
```

---

## ⚡ Quick Start

### 1️⃣ Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Cấu hình API Keys

Tạo file `.env`:

```env
# Gemini API Keys (ít nhất 2-3 keys để đảm bảo uptime)
GEMINI_API_KEY_1=AIzaSy...your_key_here
GEMINI_API_KEY_2=AIzaSy...your_key_here
GEMINI_API_KEY_3=AIzaSy...your_key_here

# Milvus Configuration
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

**💡 Lấy API Key miễn phí:** https://aistudio.google.com/

### 3️⃣ Cấu hình PDF path

Sửa file `config.py`:

```python
PDF_PATH = "d:/path/to/your/document.pdf"
```

### 4️⃣ Chạy pipeline

```bash
# Bước 1: Đồng bộ PDF vào Milvus
python populate_milvus.py

# Bước 2: Chạy Q&A app
python qa_app.py
```

---

## 📦 Cài đặt

### Yêu cầu hệ thống

- **Python**: 3.9+
- **Milvus**: 2.3.0+ (Docker hoặc standalone)
- **RAM**: Tối thiểu 4GB (8GB khuyến nghị)
- **GPU**: Tùy chọn (cho EasyOCR và embeddings)

### Cài đặt đầy đủ

```bash
# Clone repository
git clone https://github.com/Klein1411/RAG_pdf_new.git
cd RAG_pdf_new

# Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

### Cài đặt Milvus (Docker)

```bash
# Pull Milvus image
docker pull milvusdb/milvus:latest

# Run Milvus standalone
docker run -d --name milvus_standalone \
  -p 19530:19530 -p 9091:9091 \
  -v milvus_data:/var/lib/milvus \
  milvusdb/milvus:latest
```

---

## 🔧 Cấu hình

### File: `config.py`

```python
# PDF path
PDF_PATH = "path/to/your/document.pdf"

# Embedding model
EMBEDDING_MODEL_NAME = 'paraphrase-multilingual-mpnet-base-v2'
EMBEDDING_DIM = 768

# Milvus
COLLECTION_NAME = "pdf_rag_collection"

# Gemini models (theo thứ tự ưu tiên)
GEMINI_MODELS = [
    "gemini-2.0-flash-exp",  # Model chính
    "gemini-1.5-flash",      # Dự phòng 1
    "gemini-1.5-flash-8b"    # Dự phòng 2
]

# Gemini token limit
GEMINI_INPUT_TOKEN_LIMIT = 1000000  # 1M tokens

# Ollama (nếu dùng local models)
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODELS = ["llama3:latest"]
```

### File: `.env`

```env
# Gemini API Keys (thêm nhiều key để tăng uptime)
GEMINI_API_KEY_1=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GEMINI_API_KEY_2=AIzaSyYYYYYYYYYYYYYYYYYYYYYYYYYYYY
GEMINI_API_KEY_3=AIzaSyZZZZZZZZZZZZZZZZZZZZZZZZZZZZ

# Milvus (nếu không dùng localhost)
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

## 🎯 Sử dụng

### 1. Trích xuất PDF và tạo Markdown

```bash
python export_md.py
```

**Output:** `document.md` (cùng thư mục với PDF)

### 2. Đồng bộ dữ liệu vào Milvus

```bash
python populate_milvus.py
```

**Quy trình:**
1. ✅ Đọc file Markdown (tự động tạo nếu chưa có)
2. ✅ Chunking văn bản với NLTK
3. ✅ Tạo embeddings
4. ✅ Insert vào Milvus collection

### 3. Chạy Q&A Application

```bash
python qa_app.py
```

**Tính năng:**
- 💬 Đặt câu hỏi bằng tiếng Việt hoặc tiếng Anh
- 📄 Hiển thị nguồn tham khảo (trang PDF)
- 🔄 Tự động retry và fallback
- 🚀 Context expansion cho câu trả lời chính xác

**Ví dụ:**
```
❓ Đặt câu hỏi của bạn: Machine learning là gì?

✅ Câu trả lời:
Machine learning là một nhánh của trí tuệ nhân tạo...

Nguồn tham khảo: Artificial-Intelligence.pdf (Trang 3, Trang 4)
```

### 4. Test PDF extraction

```bash
python read_pdf.py
```

Chọn phương án:
- **1**: Gemini Vision (nhanh, chính xác)
- **2**: Manual extraction + OCR (chậm hơn)

---

## 🤖 Gemini Multi-Model

### Hệ thống Auto-Fallback

```
Request → Model 2.0 Flash (Key 1,2,3)
            ↓ fail
          Model 1.5 Flash (Key 1,2,3)
            ↓ fail
          Model 1.5 Flash 8B (Key 1,2,3)
            ↓ fail
          Error
```

### So sánh Models

| Model | Tốc độ | Độ chính xác | Token Limit | Trạng thái |
|-------|--------|--------------|-------------|------------|
| **2.0 Flash Exp** | ⚡⚡⚡ | 🎯🎯🎯 | 1M | Experimental |
| **1.5 Flash** | ⚡⚡ | 🎯🎯🎯 | 1M | Stable |
| **1.5 Flash 8B** | ⚡⚡⚡⚡ | 🎯🎯 | 1M | Stable (Fast) |

### Test Setup

```bash
python test_gemini_setup.py
```

**Chi tiết:** [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md)

---

## 📝 Logging

Toàn bộ hệ thống sử dụng **Python logging** với cấu hình tập trung.

### Cấu hình logging level

File: `logging_config.py`

```python
from logging_config import get_logger

logger = get_logger(__name__)
logger.info("Thông tin hệ thống")
logger.warning("Cảnh báo")
logger.error("Lỗi nghiêm trọng")
```

### Log levels

- `DEBUG`: Chi tiết kỹ thuật (API calls, intermediate values)
- `INFO`: Thông tin chính về tiến trình ✅
- `WARNING`: Cảnh báo không nghiêm trọng ⚠️
- `ERROR`: Lỗi nghiêm trọng ❌
- `CRITICAL`: Lỗi cực kỳ nghiêm trọng 🚨

### Xem logs

Logs được xuất ra console với format:
```
2025-10-17 13:01:01,287 - gemini_client - INFO - ✅ Request thành công
```

---

## 🧪 Testing

### Chạy unit tests

```bash
# Tất cả tests
pytest test_gemini_client.py -v

# Với coverage
pytest test_gemini_client.py -v --cov=gemini_client --cov-report=html

# Test cụ thể
pytest test_gemini_client.py::TestKeyRotation -v
```

### Test coverage

- ✅ GeminiClient initialization (4 tests)
- ✅ Key rotation (2 tests)
- ✅ Content generation (4 tests)
- ✅ Token counting (2 tests)
- ✅ Edge cases (2 tests)

**Target coverage:** > 90%

### Test setup nhanh

```bash
python test_gemini_setup.py
```

**Chi tiết:** [TESTING.md](./TESTING.md)

---

## 📚 Documentation

### 📖 Hướng dẫn chi tiết

> 🗺️ **Navigation Hub:** [DOCS_INDEX.md](./DOCS_INDEX.md) - Tìm document nhanh chóng

| File | Thời gian | Mô tả |
|------|-----------|-------|
| [GETTING_STARTED.md](./GETTING_STARTED.md) | 5 phút | 🚀 Quick start siêu ngắn gọn |
| [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md) | 10 phút | 🤖 Quick start cho Gemini setup |
| [GEMINI_MODELS.md](./GEMINI_MODELS.md) | 20 phút | 🔧 Chi tiết về multi-model fallback |
| [TESTING.md](./TESTING.md) | 10 phút | 🧪 Hướng dẫn testing và coverage |
| [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) | 15 phút | 📂 Chi tiết cấu trúc và chức năng files |
| [IMPROVEMENTS.md](./IMPROVEMENTS.md) | 5 phút | ✨ Tổng kết các cải tiến đã thực hiện |

### 📁 Cấu trúc project

> 📖 **Chi tiết đầy đủ:** [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)

```
RAG_pdf_new/
├── 📄 Core Python Files
│   ├── config.py                 # Cấu hình tập trung
│   ├── gemini_client.py          # Gemini client với multi-model
│   ├── logging_config.py         # Logging configuration
│   ├── read_pdf.py               # PDF extraction & OCR
│   ├── export_md.py              # Export sang Markdown
│   ├── populate_milvus.py        # ETL pipeline vào Milvus
│   ├── milvus.py                 # Milvus connection & collection
│   ├── llm_handler.py            # LLM abstraction (Gemini/Ollama)
│   └── qa_app.py                 # Q&A application
│
├── 🧪 Test Files
│   ├── test_gemini_client.py     # Unit tests
│   ├── test_gemini_setup.py      # Setup test script
│   └── run_tests.py              # Test runner
│
├── 📚 Documentation
│   ├── README.md                 # 👈 Bạn đang đọc file này
│   ├── GETTING_STARTED.md        # Quick start 5 phút
│   ├── QUICK_START_GEMINI.md     # Quick start Gemini
│   ├── GEMINI_MODELS.md          # Multi-model docs
│   ├── TESTING.md                # Testing guide
│   ├── IMPROVEMENTS.md           # Changelog
│   ├── DOCS_INDEX.md             # Documentation navigation
│   └── PROJECT_STRUCTURE.md      # Chi tiết cấu trúc project
│
└── 📝 Configuration
    ├── .env                      # API keys (không commit)
    ├── requirements.txt          # Python dependencies
    └── .gitignore                # Git ignore rules
```

---

## 🛠️ Troubleshooting

### ❌ "Không tìm thấy biến môi trường GEMINI_API_KEY"

**Giải pháp:**
1. Tạo file `.env` ở root folder
2. Thêm `GEMINI_API_KEY_1=your_key_here`
3. Restart terminal/IDE

### ❌ "Tất cả các API key đều đã hết quota"

**Giải pháp:**
1. Thêm nhiều API key vào `.env`
2. Đợi quota reset (thường 24h)
3. Check quota tại: https://aistudio.google.com/

### ❌ "Không thể kết nối đến Milvus"

**Giải pháp:**
1. Kiểm tra Milvus đang chạy: `docker ps`
2. Kiểm tra port 19530: `netstat -an | findstr 19530`
3. Restart Milvus: `docker restart milvus_standalone`

### ❌ "Model không tồn tại"

**Giải pháp:**
- Model experimental có thể bị gỡ
- Hệ thống sẽ tự động fallback sang model ổn định
- Cập nhật `GEMINI_MODELS` trong `config.py`

### ❌ "CUDA out of memory"

**Giải pháp:**
1. Giảm batch size khi encode
2. Sử dụng CPU: `device='cpu'`
3. Dùng model nhẹ hơn: `gemini-1.5-flash-8b`

### ❌ "PDF không có text"

**Giải pháp:**
- PDF có thể là ảnh scan
- Chọn phương án 1 (Gemini Vision) khi chạy `read_pdf.py`
- Hoặc phương án 2 sẽ dùng OCR tự động

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork repository
2. Tạo branch mới: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Tạo Pull Request

---

## 📄 License

Dự án này sử dụng các thư viện open-source:
- LangChain (MIT)
- Milvus (Apache 2.0)
- SentenceTransformers (Apache 2.0)
- Google Generative AI (Google Terms)

---

## 📞 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/Klein1411/RAG_pdf_new/issues)
- 📧 **Email:** klein1411@example.com
- 💬 **Discussions:** [GitHub Discussions](https://github.com/Klein1411/RAG_pdf_new/discussions)

---

## 🌟 Acknowledgments

- **Google Gemini AI** - Powerful multimodal AI
- **Milvus** - High-performance vector database
- **LangChain** - LLM application framework
- **SentenceTransformers** - State-of-the-art embeddings

---

## 📈 Roadmap

- [ ] Web UI với Streamlit/Gradio
- [ ] Multi-PDF support
- [ ] Cloud deployment (AWS/GCP)
- [ ] Advanced RAG techniques (HyDE, Query Expansion)
- [ ] Multi-language support
- [ ] Document comparison features
- [ ] Export answers to PDF/DOCX

---

<div align="center">

**⭐ Nếu project hữu ích, đừng quên star repo! ⭐**

Made with ❤️ by Klein1411

</div>
