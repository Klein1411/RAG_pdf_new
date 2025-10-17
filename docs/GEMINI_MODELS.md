# Cấu hình Gemini Models với Auto-Fallback

> 📖 **Xem hướng dẫn đầy đủ tại:** [README.md](./README.md) | [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md)

## 📋 Tổng quan

Dự án sử dụng hệ thống **tự động fallback** cho Gemini API với nhiều model và nhiều API key:

### 🎯 Chiến lược Fallback

1. **Model Fallback**: Tự động chuyển sang model dự phòng khi model chính thất bại
2. **Key Rotation**: Tự động xoay vòng qua các API key khi gặp lỗi quota
3. **Smart Retry**: Xử lý thông minh các lỗi khác nhau (quota, invalid key, model not found)

## 🔧 Cấu hình Model (config.py)

```python
GEMINI_MODELS = [
    "gemini-2.0-flash-exp",  # Model chính - Gemini 2.0 Flash Experimental
    "gemini-1.5-flash",      # Dự phòng 1 - Gemini 1.5 Flash (ổn định)
    "gemini-1.5-flash-8b"    # Dự phòng 2 - Gemini 1.5 Flash 8B (nhẹ)
]
```

### Thứ tự ưu tiên:
1. **Gemini 2.0 Flash Experimental** (`gemini-2.0-flash-exp`)
   - Model mới nhất, mạnh nhất
   - Hỗ trợ đến **1M tokens** input
   - Có thể không ổn định (experimental)

2. **Gemini 1.5 Flash** (`gemini-1.5-flash`)
   - Model ổn định, production-ready
   - Hỗ trợ đến **1M tokens** input
   - Cân bằng tốt giữa tốc độ và chất lượng

3. **Gemini 1.5 Flash 8B** (`gemini-1.5-flash-8b`)
   - Model nhẹ nhất, nhanh nhất
   - Tiêu thụ ít tài nguyên
   - Phù hợp cho tác vụ đơn giản

## 🔑 Cấu hình API Keys (.env)

```env
GEMINI_API_KEY_1=your_first_key_here
GEMINI_API_KEY_2=your_second_key_here
GEMINI_API_KEY_3=your_third_key_here
# ... có thể thêm đến GEMINI_API_KEY_9
```

## 🚀 Cách hoạt động

### Quy trình Fallback

```
┌─────────────────────────────────────┐
│  Model 1: gemini-2.0-flash-exp      │
│  ├─ Key 1 → Thử                     │
│  ├─ Key 2 → Thử (nếu Key 1 fail)   │
│  └─ Key 3 → Thử (nếu Key 2 fail)   │
└─────────────────────────────────────┘
              ↓ (tất cả key fail)
┌─────────────────────────────────────┐
│  Model 2: gemini-1.5-flash          │
│  ├─ Key 1 → Thử (reset về Key 1)   │
│  ├─ Key 2 → Thử                     │
│  └─ Key 3 → Thử                     │
└─────────────────────────────────────┘
              ↓ (tất cả key fail)
┌─────────────────────────────────────┐
│  Model 3: gemini-1.5-flash-8b       │
│  ├─ Key 1 → Thử (reset về Key 1)   │
│  ├─ Key 2 → Thử                     │
│  └─ Key 3 → Thử                     │
└─────────────────────────────────────┘
              ↓
        Success hoặc Error
```

### Xử lý lỗi thông minh

| Loại lỗi | Hành động |
|-----------|-----------|
| **429 Quota Exceeded** | Chuyển sang key tiếp theo |
| **Invalid API Key** | Chuyển sang key tiếp theo |
| **404 Model Not Found** | Chuyển sang model tiếp theo ngay |
| **Other Errors** | Raise exception (không retry) |

## 💻 Sử dụng trong code

### Cách 1: Sử dụng model mặc định từ config

```python
from gemini_client import GeminiClient

# Tự động sử dụng danh sách model từ config.py
client = GeminiClient()

# Tự động fallback qua các model và key
response = client.generate_content("Your prompt here")
```

### Cách 2: Chỉ định danh sách model tùy chỉnh

```python
from gemini_client import GeminiClient

# Sử dụng danh sách model tùy chỉnh
custom_models = ["gemini-2.0-flash-exp", "gemini-1.5-pro"]
client = GeminiClient(model_names=custom_models)

response = client.generate_content("Your prompt here")
```

## 📊 Logging

Hệ thống ghi log chi tiết quá trình fallback:

```
INFO: 🔑 Đang cấu hình Gemini với API Key #1, Model: gemini-2.0-flash-exp
WARNING: ⚠️ Lỗi khi gọi API: 429 Quota exceeded
WARNING: Key #1 đã hết quota/rate limit
INFO: 🔄 Chuyển sang API Key #2
INFO: 🔑 Đang cấu hình Gemini với API Key #2, Model: gemini-2.0-flash-exp
INFO: ✅ Request thành công với gemini-2.0-flash-exp, trả về text
```

## ⚙️ Tùy chỉnh

### Thay đổi thứ tự model

Chỉnh sửa `config.py`:

```python
GEMINI_MODELS = [
    "gemini-1.5-flash",      # Đổi lên làm model chính
    "gemini-2.0-flash-exp",  # Đổi xuống làm dự phòng
    "gemini-1.5-flash-8b"
]
```

### Thêm model mới

```python
GEMINI_MODELS = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",        # Model mới
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b"
]
```

### Giới hạn token

```python
GEMINI_INPUT_TOKEN_LIMIT = 1000000  # 1M tokens cho Gemini 2.0/1.5
```

## 🔍 Troubleshooting

### Lỗi: "Tất cả các API key và model của Gemini đều đã thất bại"

**Nguyên nhân:**
- Tất cả API key đều hết quota
- Tất cả model đều không khả dụng
- Kết nối mạng có vấn đề

**Giải pháp:**
1. Kiểm tra quota tại [Google AI Studio](https://aistudio.google.com/)
2. Thêm nhiều API key vào `.env`
3. Kiểm tra kết nối internet
4. Đợi quota reset (thường reset hàng ngày)

### Model không tồn tại

**Hiện tượng:**
```
ERROR: Model gemini-2.0-flash-exp không tồn tại hoặc không khả dụng
```

**Giải pháp:**
- Model experimental có thể bị gỡ bỏ
- Cập nhật `GEMINI_MODELS` với model còn khả dụng
- Xem danh sách model tại [Google AI Documentation](https://ai.google.dev/models/gemini)

## 📈 Best Practices

1. **Luôn có ít nhất 2-3 API key** để đảm bảo uptime cao
2. **Sử dụng model experimental cho development**, stable cho production
3. **Monitor logs** để phát hiện sớm vấn đề về quota
4. **Đặt token limit hợp lý** để tránh chi phí cao
5. **Test fallback** định kỳ để đảm bảo hệ thống hoạt động

## 📚 Tham khảo

### Documentation nội bộ
- [README.md](./README.md) - Hướng dẫn đầy đủ về toàn bộ hệ thống
- [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md) - Quick start cho Gemini
- [TESTING.md](./TESTING.md) - Testing và coverage
- [GETTING_STARTED.md](./GETTING_STARTED.md) - Quick start 5 phút

### Documentation bên ngoài
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Gemini Models Overview](https://ai.google.dev/models/gemini)
- [Rate Limits & Quotas](https://ai.google.dev/pricing)
