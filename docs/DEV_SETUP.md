# 🛠️ Development Setup Guide

## 🐍 Python Environment

### 1. Virtual Environment

Dự án sử dụng Python virtual environment (`venv`):

```bash
# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate venv (Windows CMD)
.\venv\Scripts\activate.bat

# Deactivate
deactivate
```

### 2. VS Code Settings

File `.vscode/settings.json` đã được cấu hình để:
- ✅ Tự động activate venv khi mở terminal mới
- ✅ Sử dụng Python interpreter từ venv
- ✅ Cấu hình pytest cho testing
- ✅ Bypass PowerShell execution policy

**Nếu terminal không tự động activate venv:**
1. Reload VS Code window: `Ctrl+Shift+P` → "Reload Window"
2. Hoặc mở terminal mới: `Ctrl+Shift+\``
3. Kiểm tra Python interpreter: `Ctrl+Shift+P` → "Python: Select Interpreter" → Chọn venv

---

## 📂 Import Module 'src'

### Vấn đề

Khi chạy trực tiếp file Python trong folder `src/`, có thể gặp lỗi:
```
ModuleNotFoundError: No module named 'src'
```

### Giải pháp đã áp dụng

Tất cả các file Python trong `src/` đã được thêm đoạn code sau ở đầu file:

```python
import sys
from pathlib import Path

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

### Files đã được fix

- ✅ `src/gemini_client.py`
- ✅ `src/read_pdf.py`
- ✅ `src/export_md.py`
- ✅ `src/populate_milvus.py`
- ✅ `src/milvus.py`
- ✅ `src/llm_handler.py`
- ✅ `src/qa_app.py`
- ✅ `tests/test_gemini_client.py`
- ✅ `tests/test_gemini_setup.py`

### Cách chạy file

Bây giờ bạn có thể chạy file theo **3 cách**:

#### 1. Chạy trực tiếp (khuyến nghị khi develop)
```bash
python src/export_md.py
python src/qa_app.py
python src/populate_milvus.py
```

#### 2. Chạy như module
```bash
python -m src.export_md
python -m src.qa_app
python -m src.populate_milvus
```

#### 3. Chạy tests
```bash
# Unit tests
pytest tests/test_gemini_client.py -v

# Integration tests
python tests/test_gemini_setup.py

# All tests with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 🔧 Troubleshooting

### Issue: Terminal không activate venv tự động

**Giải pháp:**
1. Kiểm tra Python interpreter đã chọn đúng:
   - `Ctrl+Shift+P` → "Python: Select Interpreter"
   - Chọn: `Python 3.12.10 64-bit ('venv': venv)`

2. Reload VS Code window:
   - `Ctrl+Shift+P` → "Developer: Reload Window"

3. Manual activate:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

### Issue: PowerShell execution policy

**Lỗi:**
```
cannot be loaded because running scripts is disabled on this system
```

**Giải pháp:**
```powershell
# Tạm thời cho session hiện tại
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Hoặc cho user (cần admin)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: Import không tìm thấy module 'src'

**Kiểm tra:**
1. File có đoạn code `sys.path.insert()` ở đầu chưa?
2. Đang chạy từ thư mục gốc project (`D:\Project_self`) chứ không phải từ `src/`?

**Chạy từ đúng thư mục:**
```bash
# Sai (ở trong src/)
cd src
python export_md.py  # ❌ Lỗi!

# Đúng (ở thư mục gốc)
cd D:\Project_self
python src/export_md.py  # ✅ OK!
```

---

## 📦 Package Installation

### Install requirements
```bash
pip install -r requirements.txt
```

### Install development packages
```bash
pip install pytest pytest-cov pytest-mock
```

### Verify installation
```bash
pip list | Select-String "pytest"
pip list | Select-String "google-generativeai"
```

---

## 🎯 Quick Start

```bash
# 1. Activate venv
.\venv\Scripts\Activate.ps1

# 2. Verify environment
python --version  # Should be 3.12.10
pip list

# 3. Run tests
pytest tests/ -v

# 4. Run main application
python src/qa_app.py
```

---

## 📚 Related Documentation

- [README.md](../README.md) - Main documentation
- [TESTING.md](./TESTING.md) - Testing guide
- [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md) - Gemini setup
- [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) - Project structure

---

## 💡 Tips

1. **Luôn activate venv trước khi làm việc**
2. **Chạy file từ thư mục gốc project** (không phải từ `src/`)
3. **Sử dụng pytest cho testing** (không cần file `run_tests.py`)
4. **Check imports nếu gặp ModuleNotFoundError**
5. **Reload VS Code nếu settings không apply**
