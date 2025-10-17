# 📂 Project Structure

Giải thích chi tiết về cấu trúc và chức năng của từng file trong project.

---

## 📁 Root Directory

```
RAG_pdf_new/
├── 📄 Python Files (Core)
├── 📝 Configuration Files
├── 🧪 Test Files
├── 📚 Documentation Files
└── 🔧 Utility Files
```

---

## 📄 Core Python Files

### 1. `gemini_client.py` (152 lines)
**Chức năng:** Gemini API client với multi-model và multi-key fallback

**Features:**
- ✅ Tự động rotation qua nhiều API keys
- ✅ Tự động fallback qua nhiều models (2.0 Flash → 1.5 Flash → 1.5 Flash 8B)
- ✅ Error handling thông minh (quota, invalid key, model not found)
- ✅ Token counting
- ✅ Support text và vision tasks

**Sử dụng:**
```python
from gemini_client import GeminiClient

client = GeminiClient()  # Auto-load models từ config
response = client.generate_content("Your prompt")
```

---

### 2. `read_pdf.py` (234 lines)
**Chức năng:** Trích xuất nội dung từ PDF với OCR

**Features:**
- ✅ Method 1: Gemini Vision (nhanh, chính xác)
- ✅ Method 2: Manual extraction + EasyOCR
- ✅ Phát hiện và trích xuất bảng biểu
- ✅ User choice: interactive selection

**Sử dụng:**
```bash
python read_pdf.py
# Chọn Y/N cho Gemini Vision
```

---

### 3. `export_md.py` (86 lines)
**Chức năng:** Convert kết quả PDF extraction sang Markdown

**Features:**
- ✅ Format tables thành Markdown tables
- ✅ Preserve page numbers
- ✅ Handle both Gemini và manual extraction sources

**Sử dụng:**
```bash
python export_md.py
# Output: document.md
```

---

### 4. `populate_milvus.py` (210 lines)
**Chức năng:** ETL pipeline - PDF → Markdown → Chunks → Embeddings → Milvus

**Features:**
- ✅ Auto-create Markdown nếu chưa có
- ✅ Smart chunking với NLTK (sentence-based)
- ✅ Batch embedding với SentenceTransformer
- ✅ Insert vào Milvus với metadata (page, source)

**Sử dụng:**
```bash
python populate_milvus.py
# Tự động đồng bộ toàn bộ
```

---

### 5. `milvus.py` (139 lines)
**Chức năng:** Milvus connection và collection management

**Features:**
- ✅ Auto-connect với retry
- ✅ Create collection với schema chuẩn
- ✅ IVF_FLAT index cho fast search
- ✅ Collection recreate option

**Sử dụng:**
```python
from milvus import get_or_create_collection

collection = get_or_create_collection("my_collection", recreate=False)
```

---

### 6. `llm_handler.py` (187 lines)
**Chức năng:** LLM abstraction layer - Gemini + Ollama với fallback

**Features:**
- ✅ Gemini API calls với token checking
- ✅ Ollama local model support
- ✅ Auto-fallback: Primary model → Fallback model
- ✅ User model selection (interactive)

**Sử dụng:**
```python
from llm_handler import initialize_and_select_llm, generate_answer_with_fallback

model_choice, gemini_client, ollama_model = initialize_and_select_llm()
answer = generate_answer_with_fallback(prompt, model_choice, gemini_client, ollama_model)
```

---

### 7. `qa_app.py` (194 lines)
**Chức năng:** Main Q&A application - RAG pipeline

**Features:**
- ✅ Semantic search với Milvus
- ✅ Context expansion (lấy thêm trang trước/sau)
- ✅ LLM generation với retry và fallback
- ✅ Display sources (PDF page numbers)
- ✅ Interactive loop (gõ 'exit' để thoát)

**Sử dụng:**
```bash
python qa_app.py
# Đặt câu hỏi và nhận câu trả lời
```

---

### 8. `logging_config.py` (45 lines)
**Chức năng:** Centralized logging configuration

**Features:**
- ✅ Consistent format cho toàn bộ project
- ✅ Configurable level và output
- ✅ Factory function: `get_logger(__name__)`

**Sử dụng:**
```python
from logging_config import get_logger

logger = get_logger(__name__)
logger.info("Message")
```

---

### 9. `config.py` (42 lines)
**Chức năng:** Cấu hình tập trung cho toàn bộ project

**Settings:**
- 📄 `PDF_PATH`: Đường dẫn tới PDF
- 🤖 `GEMINI_MODELS`: Danh sách models theo thứ tự ưu tiên
- 🔢 `GEMINI_INPUT_TOKEN_LIMIT`: Token limit
- 📊 `EMBEDDING_MODEL_NAME`: Model embedding
- 🗄️ `COLLECTION_NAME`: Tên collection Milvus
- 🔧 `OLLAMA_*`: Cấu hình Ollama

---

## 🧪 Test Files

### 10. `test_gemini_client.py` (300+ lines)
**Chức năng:** Unit tests cho GeminiClient

**Coverage:**
- ✅ Initialization tests (4 tests)
- ✅ Key rotation tests (2 tests)
- ✅ Content generation tests (4 tests)
- ✅ Token counting tests (2 tests)
- ✅ Edge cases (2 tests)

**Sử dụng:**
```bash
pytest test_gemini_client.py -v
pytest test_gemini_client.py --cov=gemini_client --cov-report=html
```

---

### 11. `test_gemini_setup.py` (150 lines)
**Chức năng:** Integration test - verify Gemini setup

**Tests:**
- ✅ Client initialization
- ✅ Text generation
- ✅ Token counting
- ✅ Config verification

**Sử dụng:**
```bash
python test_gemini_setup.py
```

---

### 12. `run_tests.py` (50 lines)
**Chức năng:** Test runner script

**Sử dụng:**
```bash
python run_tests.py
```

---
 
## 📝 Configuration Files

### 13. `.env` (Không commit)
**Chức năng:** Environment variables

**Format:**
```env
GEMINI_API_KEY_1=AIzaSy...
GEMINI_API_KEY_2=AIzaSy...
GEMINI_API_KEY_3=AIzaSy...
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

### 14. `requirements.txt`
**Chức năng:** Python dependencies

**Main packages:**
- google-generativeai (Gemini API)
- pymilvus (Vector database)
- sentence-transformers (Embeddings)
- langchain (LLM framework)
- pdfplumber (PDF parsing)
- easyocr (OCR)
- pytest, pytest-cov (Testing)

---

### 15. `.gitignore`
**Chức năng:** Git ignore rules

**Ignores:**
- Python artifacts (*.pyc, __pycache__)
- Virtual environments (venv/, env/)
- IDE files (.vscode/, .idea/)
- Test artifacts (htmlcov/, .coverage)
- Sensitive data (.env)
- Generated files (*.md from PDFs)

---

## 📚 Documentation Files

### 16. `README.md` (400+ lines)
**Chức năng:** Main documentation

**Sections:**
- ✨ Features
- 🏗️ Architecture
- ⚡ Quick Start
- 📦 Installation
- 🔧 Configuration
- 🎯 Usage
- 📝 Logging
- 🧪 Testing
- 🛠️ Troubleshooting

---

### 17. `GETTING_STARTED.md` (80 lines)
**Chức năng:** 5-minute quick start guide

**Target:** Người dùng mới muốn chạy nhanh

---

### 18. `QUICK_START_GEMINI.md` (200 lines)
**Chức năng:** Gemini setup quick start

**Covers:**
- API key setup
- Model configuration
- Basic usage examples

---

### 19. `GEMINI_MODELS.md` (300+ lines)
**Chức năng:** Chi tiết về multi-model fallback system

**Covers:**
- Model fallback logic
- Key rotation mechanism
- Error handling strategies
- Troubleshooting
- Best practices

---

### 20. `TESTING.md` (100 lines)
**Chức năng:** Testing guide

**Covers:**
- Chạy tests
- Coverage reports
- Test structure
- Mocking strategies

---

### 21. `IMPROVEMENTS.md`
**Chức năng:** Changelog và improvements summary

---

### 22. `DOCS_INDEX.md` (150 lines)
**Chức năng:** Navigation hub cho tất cả documentation

**Features:**
- Learning paths
- Quick reference
- Keyword search guide

---

## 🎯 File Dependencies

```
config.py
    ↓
gemini_client.py ←──────┐
    ↓                   │
read_pdf.py             │
    ↓                   │
export_md.py            │
    ↓                   │
populate_milvus.py ─────┤
    ↓                   │
milvus.py               │
    ↓                   │
llm_handler.py ─────────┘
    ↓
qa_app.py
```

---

## 📊 File Statistics

| Category | Files | Lines |
|----------|-------|-------|
| Core Python | 9 | ~1,500 |
| Tests | 3 | ~500 |
| Documentation | 7 | ~1,500 |
| Configuration | 3 | ~100 |
| **Total** | **22** | **~3,600** |

---

## 🔍 Tìm file theo chức năng

### PDF Processing
- `read_pdf.py` - Extract
- `export_md.py` - Convert to MD

### Data Pipeline
- `populate_milvus.py` - ETL
- `milvus.py` - Database

### AI/LLM
- `gemini_client.py` - Gemini API
- `llm_handler.py` - LLM abstraction

### Application
- `qa_app.py` - Main app

### Infrastructure
- `config.py` - Settings
- `logging_config.py` - Logs
- `.env` - Secrets

### Testing
- `test_gemini_client.py` - Unit tests
- `test_gemini_setup.py` - Integration test
- `run_tests.py` - Test runner

### Documentation
- `README.md` - Main
- `GETTING_STARTED.md` - Quick start
- `GEMINI_MODELS.md` - AI details
- `TESTING.md` - Test guide
- `DOCS_INDEX.md` - Navigation

---

## 💡 File Naming Convention

- `*_config.py` - Configuration modules
- `test_*.py` - Test files (pytest convention)
- `*.md` - Markdown documentation
- `*_app.py` - Application entry points
- `*.txt` - Text data files (requirements, etc.)

---

<div align="center">

**📂 Hiểu rõ structure = Code tốt hơn! 📂**

</div>
