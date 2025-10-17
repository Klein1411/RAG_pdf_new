# 📂 Project Structure# 📂 Project Structure



Giải thích về cấu trúc và chức năng chính của từng module trong project.Giải thích chi tiết về cấu trúc và chức năng của từng file trong project.



------



## 📁 Cấu trúc tổng quan## 📁 Root Directory



``````

RAG_pdf_new/RAG_pdf_new/

├── src/                      # Core modules├── 📄 Python Files (Core)

│   ├── config.py            # Cấu hình (API keys, paths, models)├── 📝 Configuration Files

│   ├── gemini_client.py     # Gemini API với multi-model fallback├── 🧪 Test Files

│   ├── read_pdf.py          # Trích xuất PDF với OCR├── 📚 Documentation Files

│   ├── export_md.py         # Export sang Markdown└── 🔧 Utility Files

│   ├── populate_milvus.py   # ETL pipeline: PDF → Milvus```

│   ├── milvus.py            # Milvus vector database

│   ├── llm_handler.py       # LLM abstraction (Gemini + Ollama)---

│   ├── qa_app.py            # Q&A application

│   └── logging_config.py    # Logging configuration## 📄 Core Python Files

│

├── tests/                    # Unit tests & integration tests### 1. `gemini_client.py` (152 lines)

│   ├── test_gemini_client.py**Chức năng:** Gemini API client với multi-model và multi-key fallback

│   ├── test_gemini_setup.py

│   └── run_tests.py**Features:**

│- ✅ Tự động rotation qua nhiều API keys

├── docs/                     # Documentation- ✅ Tự động fallback qua nhiều models (2.0 Flash → 1.5 Flash → 1.5 Flash 8B)

│   ├── GETTING_STARTED.md- ✅ Error handling thông minh (quota, invalid key, model not found)

│   ├── QUICK_START_GEMINI.md- ✅ Token counting

│   ├── GEMINI_MODELS.md- ✅ Support text và vision tasks

│   ├── TESTING.md

│   └── PROJECT_STRUCTURE.md  # (file này)**Sử dụng:**

│```python

├── data/from gemini_client import GeminiClient

│   ├── pdfs/                # Input PDF files

│   └── outputs/             # Generated Markdown filesclient = GeminiClient()  # Auto-load models từ config

│response = client.generate_content("Your prompt")

├── .env                      # API keys (không commit)```

├── requirements.txt

└── README.md---

```

### 2. `read_pdf.py` (234 lines)

---**Chức năng:** Trích xuất nội dung từ PDF với OCR



## 📄 Core Modules**Features:**

- ✅ Method 1: Gemini Vision (nhanh, chính xác)

### 1. `config.py`- ✅ Method 2: Manual extraction + EasyOCR

**Cấu hình tập trung cho toàn bộ project**- ✅ Phát hiện và trích xuất bảng biểu

- ✅ User choice: interactive selection

```python

# Gemini Models (theo thứ tự ưu tiên)**Sử dụng:**

GEMINI_MODELS = [```bash

    "gemini-2.0-flash-exp",  # Primarypython read_pdf.py

    "gemini-1.5-flash",      # Backup 1# Chọn Y/N cho Gemini Vision

    "gemini-1.5-flash-8b"    # Backup 2```

]

---

# Paths

PDF_PATH = "data/pdfs/your_document.pdf"### 3. `export_md.py` (86 lines)

**Chức năng:** Convert kết quả PDF extraction sang Markdown

# Embedding

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"**Features:**

EMBEDDING_DIM = 768- ✅ Format tables thành Markdown tables

- ✅ Preserve page numbers

# Milvus- ✅ Handle both Gemini và manual extraction sources

COLLECTION_NAME = "pdf_chunks"

**Sử dụng:**

# Ollama (optional)```bash

OLLAMA_API_URL = "http://localhost:11434/api/generate"python export_md.py

```# Output: document.md

```

---

---

### 2. `gemini_client.py`

**Gemini API client với multi-model & multi-key fallback**### 4. `populate_milvus.py` (210 lines)

**Chức năng:** ETL pipeline - PDF → Markdown → Chunks → Embeddings → Milvus

**Features:**

- ✅ Auto-rotation qua nhiều API keys**Features:**

- ✅ Auto-fallback qua 3 models: 2.0 Flash → 1.5 Flash → 1.5 Flash 8B- ✅ Auto-create Markdown nếu chưa có

- ✅ Smart error handling (quota, invalid key, model not found)- ✅ Smart chunking với NLTK (sentence-based)

- ✅ Token counting để tránh vượt limit- ✅ Batch embedding với SentenceTransformer

- ✅ Insert vào Milvus với metadata (page, source)

**Sử dụng:**

```python**Sử dụng:**

from src.gemini_client import GeminiClient```bash

python populate_milvus.py

client = GeminiClient()  # Auto-load từ config# Tự động đồng bộ toàn bộ

response = client.generate_content("Your prompt")```

tokens = client.count_tokens("Your text")

```---



**Fallback logic:**### 5. `milvus.py` (139 lines)

```**Chức năng:** Milvus connection và collection management

Request → Model 1 (Key 1,2,3) → Model 2 (Key 1,2,3) → Model 3 (Key 1,2,3) → Error

```**Features:**

- ✅ Auto-connect với retry

---- ✅ Create collection với schema chuẩn

- ✅ IVF_FLAT index cho fast search

### 3. `read_pdf.py`- ✅ Collection recreate option

**Trích xuất nội dung từ PDF với OCR**

**Sử dụng:**

**2 phương pháp:**```python

1. **Gemini Vision** (recommended) - Nhanh, chính xác, hiểu contextfrom milvus import get_or_create_collection

2. **Manual extraction + EasyOCR** - Dùng khi không có Gemini

collection = get_or_create_collection("my_collection", recreate=False)

**Sử dụng:**```

```bash

python -m src.read_pdf---

# Chọn Y/N cho Gemini Vision

```### 6. `llm_handler.py` (187 lines)

**Chức năng:** LLM abstraction layer - Gemini + Ollama với fallback

**Features:**

- Trích xuất text + images**Features:**

- OCR cho hình ảnh- ✅ Gemini API calls với token checking

- Phát hiện và trích xuất bảng biểu- ✅ Ollama local model support

- Metadata: page numbers, source- ✅ Auto-fallback: Primary model → Fallback model

- ✅ User model selection (interactive)

---

**Sử dụng:**

### 4. `export_md.py````python

**Convert kết quả PDF extraction sang Markdown**from llm_handler import initialize_and_select_llm, generate_answer_with_fallback



**Sử dụng:**model_choice, gemini_client, ollama_model = initialize_and_select_llm()

```bashanswer = generate_answer_with_fallback(prompt, model_choice, gemini_client, ollama_model)

python -m src.export_md```

# Output: data/outputs/document.md

```---



**Features:**### 7. `qa_app.py` (194 lines)

- Format tables thành Markdown tables**Chức năng:** Main Q&A application - RAG pipeline

- Preserve page numbers

- Clean formatting**Features:**

- ✅ Semantic search với Milvus

---- ✅ Context expansion (lấy thêm trang trước/sau)

- ✅ LLM generation với retry và fallback

### 5. `populate_milvus.py`- ✅ Display sources (PDF page numbers)

**ETL pipeline: PDF → Markdown → Chunks → Embeddings → Milvus**- ✅ Interactive loop (gõ 'exit' để thoát)



**Sử dụng:****Sử dụng:**

```bash```bash

python -m src.populate_milvuspython qa_app.py

```# Đặt câu hỏi và nhận câu trả lời

```

**Pipeline:**

1. Đọc/tạo Markdown từ PDF---

2. Smart chunking với NLTK (sentence-based)

3. Generate embeddings (SentenceTransformer)### 8. `logging_config.py` (45 lines)

4. Insert vào Milvus collection**Chức năng:** Centralized logging configuration



**Features:****Features:**

- Auto-create Markdown nếu chưa có- ✅ Consistent format cho toàn bộ project

- Batch processing cho performance- ✅ Configurable level và output

- Metadata tracking (page, source, chunk_id)- ✅ Factory function: `get_logger(__name__)`



---**Sử dụng:**

```python

### 6. `milvus.py`from logging_config import get_logger

**Milvus vector database connection & management**

logger = get_logger(__name__)

**Functions:**logger.info("Message")

- `get_or_create_collection()` - Tạo/load collection```

- Auto-connect với retry

- Create schema: id, text, embedding, page, source---

- IVF_FLAT index cho fast search

### 9. `config.py` (42 lines)

**Sử dụng:****Chức năng:** Cấu hình tập trung cho toàn bộ project

```python

from src.milvus import get_or_create_collection**Settings:**

- 📄 `PDF_PATH`: Đường dẫn tới PDF

collection = get_or_create_collection("my_collection", recreate=False)- 🤖 `GEMINI_MODELS`: Danh sách models theo thứ tự ưu tiên

```- 🔢 `GEMINI_INPUT_TOKEN_LIMIT`: Token limit

- 📊 `EMBEDDING_MODEL_NAME`: Model embedding

---- 🗄️ `COLLECTION_NAME`: Tên collection Milvus

- 🔧 `OLLAMA_*`: Cấu hình Ollama

### 7. `llm_handler.py`

**LLM abstraction layer - Gemini + Ollama fallback**---



**Functions:**## 🧪 Test Files

- `initialize_and_select_llm()` - User chọn model

- `generate_answer_with_fallback()` - Generate với retry### 10. `test_gemini_client.py` (300+ lines)

**Chức năng:** Unit tests cho GeminiClient

**Features:**

- Gemini API với token checking**Coverage:**

- Ollama local model support- ✅ Initialization tests (4 tests)

- Auto-fallback: Primary → Fallback model- ✅ Key rotation tests (2 tests)

- Retry logic với exponential backoff- ✅ Content generation tests (4 tests)

- ✅ Token counting tests (2 tests)

**Sử dụng:**- ✅ Edge cases (2 tests)

```python

from src.llm_handler import initialize_and_select_llm, generate_answer_with_fallback**Sử dụng:**

```bash

model_choice, gemini_client, ollama_model = initialize_and_select_llm()pytest test_gemini_client.py -v

answer = generate_answer_with_fallback(prompt, model_choice, gemini_client, ollama_model)pytest test_gemini_client.py --cov=gemini_client --cov-report=html

``````



------



### 8. `qa_app.py`### 11. `test_gemini_setup.py` (150 lines)

**Main Q&A application - RAG pipeline****Chức năng:** Integration test - verify Gemini setup



**Sử dụng:****Tests:**

```bash- ✅ Client initialization

python -m src.qa_app- ✅ Text generation

# Nhập câu hỏi, gõ 'exit' để thoát- ✅ Token counting

```- ✅ Config verification



**Features:****Sử dụng:**

- Semantic search với Milvus```bash

- Context expansion (lấy thêm trang trước/sau)python test_gemini_setup.py

- LLM generation với retry```

- Display sources (PDF page numbers)

- Interactive loop---



**Flow:**### 12. `run_tests.py` (50 lines)

```**Chức năng:** Test runner script

Question → Embedding → Search Milvus → Expand context → LLM → Answer + Sources

```**Sử dụng:**

```bash

---python run_tests.py

```

### 9. `logging_config.py`

**Centralized logging configuration**---

 

**Sử dụng:**## 📝 Configuration Files

```python

from src.logging_config import get_logger### 13. `.env` (Không commit)

**Chức năng:** Environment variables

logger = get_logger(__name__)

logger.info("Message")**Format:**

``````env

GEMINI_API_KEY_1=AIzaSy...

**Features:**GEMINI_API_KEY_2=AIzaSy...

- Consistent format cho toàn projectGEMINI_API_KEY_3=AIzaSy...

- Configurable levelMILVUS_HOST=localhost

- Timestamp, module name, level, messageMILVUS_PORT=19530

```

---

---

## 🧪 Tests

### 14. `requirements.txt`

### `test_gemini_client.py`**Chức năng:** Python dependencies

Unit tests cho GeminiClient - mocking, coverage 85%+

**Main packages:**

**Run:**- google-generativeai (Gemini API)

```bash- pymilvus (Vector database)

pytest tests/test_gemini_client.py -v- sentence-transformers (Embeddings)

pytest tests/test_gemini_client.py --cov=src.gemini_client- langchain (LLM framework)

```- pdfplumber (PDF parsing)

- easyocr (OCR)

### `test_gemini_setup.py`- pytest, pytest-cov (Testing)

Integration test - verify Gemini setup thực tế

---

**Run:**

```bash### 15. `.gitignore`

python -m tests.test_gemini_setup**Chức năng:** Git ignore rules

```

**Ignores:**

---- Python artifacts (*.pyc, __pycache__)

- Virtual environments (venv/, env/)

## 🎯 Data Flow- IDE files (.vscode/, .idea/)

- Test artifacts (htmlcov/, .coverage)

```- Sensitive data (.env)

1. PDF Input (data/pdfs/)- Generated files (*.md from PDFs)

   ↓

2. read_pdf.py (Extraction + OCR)---

   ↓

3. export_md.py (Markdown conversion)## 📚 Documentation Files

   ↓

4. data/outputs/*.md### 16. `README.md` (400+ lines)

   ↓**Chức năng:** Main documentation

5. populate_milvus.py (Chunking + Embedding)

   ↓**Sections:**

6. Milvus Vector DB- ✨ Features

   ↓- 🏗️ Architecture

7. qa_app.py (Search + LLM Generation)- ⚡ Quick Start

   ↓- 📦 Installation

8. Answer với sources- 🔧 Configuration

```- 🎯 Usage

- 📝 Logging

---- 🧪 Testing

- 🛠️ Troubleshooting

## 📊 Dependencies

---

| Module | Main Dependencies |

|--------|------------------|### 17. `GETTING_STARTED.md` (80 lines)

| `gemini_client.py` | google-generativeai, dotenv |**Chức năng:** 5-minute quick start guide

| `read_pdf.py` | pdfplumber, easyocr, PIL, torch |

| `populate_milvus.py` | sentence-transformers, nltk, torch |**Target:** Người dùng mới muốn chạy nhanh

| `milvus.py` | pymilvus |

| `llm_handler.py` | requests (cho Ollama) |---

| `qa_app.py` | sentence-transformers, pymilvus |

### 18. `QUICK_START_GEMINI.md` (200 lines)

**Install:****Chức năng:** Gemini setup quick start

```bash

pip install -r requirements.txt**Covers:**

```- API key setup

- Model configuration

---- Basic usage examples



## 💡 Quick Reference---



### Chạy full pipeline### 19. `GEMINI_MODELS.md` (300+ lines)

```bash**Chức năng:** Chi tiết về multi-model fallback system

# 1. Extract PDF

python -m src.read_pdf**Covers:**

- Model fallback logic

# 2. Sync to Milvus- Key rotation mechanism

python -m src.populate_milvus- Error handling strategies

- Troubleshooting

# 3. Run Q&A- Best practices

python -m src.qa_app

```---



### Test### 20. `TESTING.md` (100 lines)

```bash**Chức năng:** Testing guide

# Quick test

python -m tests.test_gemini_setup**Covers:**

- Chạy tests

# Full test suite- Coverage reports

pytest tests/ -v- Test structure

```- Mocking strategies



### Development---

```python

# Import modules### 21. `IMPROVEMENTS.md`

from src.gemini_client import GeminiClient**Chức năng:** Changelog và improvements summary

from src.config import PDF_PATH, GEMINI_MODELS

from src.milvus import get_or_create_collection---

```

### 22. `DOCS_INDEX.md` (150 lines)

---**Chức năng:** Navigation hub cho tất cả documentation



## 📚 Xem thêm**Features:**

- Learning paths

- **Quick Start:** [GETTING_STARTED.md](GETTING_STARTED.md)- Quick reference

- **Gemini Setup:** [QUICK_START_GEMINI.md](QUICK_START_GEMINI.md)- Keyword search guide

- **Multi-Model:** [GEMINI_MODELS.md](GEMINI_MODELS.md)

- **Testing:** [TESTING.md](TESTING.md)---

- **Main Docs:** [../README.md](../README.md)

## 🎯 File Dependencies

---

```

<div align="center">config.py

    ↓

**📂 Hiểu rõ structure = Code tốt hơn! 📂**gemini_client.py ←──────┐

    ↓                   │

</div>read_pdf.py             │

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
