# 🧪 Testing Guide

Hướng dẫn chạy tests cho RAG PDF project.

---

## 📦 Cài đặt

```bash
pip install pytest pytest-cov pytest-mock
```

---

## 🎯 Có 2 loại tests

### 1. Unit Tests (`test_gemini_client.py`)
- **Mục đích:** Test logic code với mocking
- **Đặc điểm:** Nhanh, không gọi API thật
- **Coverage:** 85%+

### 2. Integration Tests (`test_gemini_setup.py`)
- **Mục đích:** Test setup thực tế với API
- **Đặc điểm:** Gọi API thật, verify cấu hình
- **Yêu cầu:** Có `.env` với API keys hợp lệ

---

## 🚀 Chạy Tests

### Chạy tất cả tests
```bash
# Tất cả tests
pytest tests/ -v

# Chỉ unit tests
pytest tests/test_gemini_client.py -v

# Chỉ integration test
python -m tests.test_gemini_setup
```

### Chạy với coverage
```bash
# Coverage report trong terminal
pytest tests/test_gemini_client.py --cov=src.gemini_client --cov-report=term-missing

# Generate HTML report
pytest tests/test_gemini_client.py --cov=src.gemini_client --cov-report=html
```

### Chạy test cụ thể
```bash
# Chạy 1 test function
pytest tests/test_gemini_client.py::TestGeminiClientInitialization::test_init_with_multiple_keys -v

# Chạy 1 test class
pytest tests/test_gemini_client.py::TestKeyRotation -v
```

---

## 📊 Coverage Report

Sau khi chạy với `--cov-report=html`:

```bash
# Windows
start htmlcov/index.html

# Linux/Mac  
open htmlcov/index.html
```

**Target coverage:** > 85%

---

## 🔍 Test Structure

### Unit Tests (`test_gemini_client.py`)

| Test Class | Mô tả |
|-----------|-------|
| `TestGeminiClientInitialization` | Tests khởi tạo client |
| `TestKeyRotation` | Tests rotation API keys |
| `TestGenerateContent` | Tests tạo nội dung |
| `TestCountTokens` | Tests đếm tokens |
| `TestEdgeCases` | Tests edge cases |

### Integration Tests (`test_gemini_setup.py`)

| Test Function | Mô tả |
|--------------|-------|
| `test_gemini_basic()` | Khởi tạo GeminiClient |
| `test_text_generation()` | Generate text thật |
| `test_token_counting()` | Đếm tokens |
| `test_config()` | Verify config |

---

## 🛠️ Advanced

### Xem logs chi tiết
```bash
pytest tests/ -v -s --log-cli-level=INFO
```

### Chạy parallel (nhanh hơn)
```bash
pip install pytest-xdist
pytest tests/ -v -n auto
```

### Debug test
```bash
pytest tests/test_gemini_client.py::test_name -v --pdb
```

---

## ✅ Best Practices

1. **Isolation:** Mỗi test độc lập, không phụ thuộc nhau
2. **Mocking:** Mock external dependencies (API, env vars)
3. **Coverage:** Maintain > 85% coverage
4. **Fast:** Unit tests phải chạy nhanh (< 1s mỗi test)
5. **Clear naming:** Tên test mô tả rõ ràng behavior

---

## 📚 Xem thêm

- [../README.md](../README.md) - Main documentation
- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start
- [QUICK_START_GEMINI.md](QUICK_START_GEMINI.md) - Gemini setup
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project structure
