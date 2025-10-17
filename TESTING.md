# Testing Guide

## Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## Chạy Unit Tests

### Chạy tất cả tests
```bash
pytest test_gemini_client.py -v
```

### Chạy với coverage report
```bash
pytest test_gemini_client.py -v --cov=gemini_client --cov-report=html
```

### Chạy một test cụ thể
```bash
pytest test_gemini_client.py::TestGeminiClientInitialization::test_init_with_multiple_keys -v
```

### Chạy tests theo class
```bash
pytest test_gemini_client.py::TestKeyRotation -v
```

## Logging

### Cấu hình logging level

Mặc định, logging được set ở level INFO. Để thay đổi:

```python
import logging
logging.getLogger('gemini_client').setLevel(logging.DEBUG)
```

### Xem logs khi chạy tests
```bash
pytest test_gemini_client.py -v -s
```

## Coverage Report

Sau khi chạy với `--cov-report=html`, mở file:
```bash
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## Test Structure

- `TestGeminiClientInitialization`: Tests cho khởi tạo client
- `TestKeyRotation`: Tests cho chức năng xoay vòng API keys
- `TestGenerateContent`: Tests cho hàm tạo nội dung
- `TestCountTokens`: Tests cho hàm đếm tokens
- `TestEdgeCases`: Tests cho các trường hợp đặc biệt

## Mocking

Tests sử dụng `unittest.mock` để mock:
- `genai.configure()`: Mock việc cấu hình API key
- `genai.GenerativeModel()`: Mock model instance
- Environment variables: Mock API keys từ `.env`

## Best Practices

1. **Isolation**: Mỗi test độc lập, không phụ thuộc vào test khác
2. **Mocking**: Mock tất cả external dependencies (API calls, env vars)
3. **Coverage**: Đảm bảo coverage > 90%
4. **Naming**: Tên test rõ ràng, mô tả chính xác behavior đang test
