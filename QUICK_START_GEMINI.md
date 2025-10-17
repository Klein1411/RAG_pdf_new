# 🚀 Quick Start: Gemini Multi-Model Setup

> 📖 **Xem hướng dẫn đầy đủ tại:** [README.md](./README.md) | [GETTING_STARTED.md](./GETTING_STARTED.md)

## ⚡ TL;DR

Dự án sử dụng **3 model Gemini** với **tự động fallback**:
1. 🔥 **Gemini 2.0 Flash Experimental** (chính)
2. ⚡ **Gemini 1.5 Flash** (dự phòng 1)
3. 🪶 **Gemini 1.5 Flash 8B** (dự phòng 2)

## 📝 Cấu hình nhanh

### Bước 1: Tạo file `.env`

```env
# Thêm ít nhất 2-3 API key để đảm bảo uptime
GEMINI_API_KEY_1=AIzaSy...your_key_here
GEMINI_API_KEY_2=AIzaSy...your_key_here
GEMINI_API_KEY_3=AIzaSy...your_key_here

# Cấu hình Milvus (nếu cần)
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### Bước 2: Lấy API Key miễn phí

1. Truy cập: https://aistudio.google.com/
2. Click "Get API Key"
3. Tạo key mới hoặc copy key có sẵn
4. Dán vào file `.env`

**💡 Mẹo:** Tạo nhiều key từ các Google Account khác nhau để có quota cao hơn!

### Bước 3: Kiểm tra cấu hình

```python
# Test nhanh trong Python
from gemini_client import GeminiClient

client = GeminiClient()
print(client.generate_content("Hello Gemini!"))
```

## 🎯 Cấu hình Model (Tùy chọn)

Mặc định sử dụng model từ `config.py`:

```python
GEMINI_MODELS = [
    "gemini-2.0-flash-exp",  # Model chính
    "gemini-1.5-flash",      # Dự phòng 1
    "gemini-1.5-flash-8b"    # Dự phòng 2
]
```

**Muốn thay đổi?** Chỉnh sửa `config.py` theo ý bạn!

## 🔄 Cách hoạt động

```
┌───────────────────────────────────────────┐
│ Request đến Gemini                        │
└─────────────┬─────────────────────────────┘
              │
              ▼
    ┌─────────────────────┐
    │ Model 2.0 Flash     │──→ Success? ✅ → Return
    └─────────────────────┘
              │ Fail (quota/error)
              ▼
    ┌─────────────────────┐
    │ Model 1.5 Flash     │──→ Success? ✅ → Return
    └─────────────────────┘
              │ Fail
              ▼
    ┌─────────────────────┐
    │ Model 1.5 Flash 8B  │──→ Success? ✅ → Return
    └─────────────────────┘
              │ All failed
              ▼
            ❌ Error
```

## 📊 So sánh Model

| Model | Tốc độ | Độ chính xác | Token Limit | Ghi chú |
|-------|--------|--------------|-------------|---------|
| **2.0 Flash Exp** | ⚡⚡⚡ | 🎯🎯🎯 | 1M | Mới nhất, experimental |
| **1.5 Flash** | ⚡⚡ | 🎯🎯🎯 | 1M | Ổn định, production |
| **1.5 Flash 8B** | ⚡⚡⚡⚡ | 🎯🎯 | 1M | Nhanh nhất, nhẹ |

## ⚠️ Xử lý lỗi

### "Đã hết quota"
- ✅ **Tự động fallback** sang key tiếp theo
- ✅ Không cần làm gì, hệ thống tự xử lý

### "Tất cả key đều fail"
- ❌ Quota đã hết cho tất cả key
- 🔧 **Giải pháp:** Thêm key mới hoặc đợi quota reset (24h)

### "Model không tồn tại"
- ❌ Model experimental có thể bị gỡ
- 🔧 **Giải pháp:** Tự động fallback sang model ổn định

## 🎓 Ví dụ sử dụng

### Text generation
```python
from gemini_client import GeminiClient

client = GeminiClient()
response = client.generate_content("Giải thích AI là gì?")
print(response)
```

### Vision tasks (PDF OCR)
```python
from gemini_client import GeminiClient
from PIL import Image

client = GeminiClient()
img = Image.open("page.png")
response = client.generate_content([
    "Trích xuất toàn bộ text từ ảnh này:",
    img
])
print(response)
```

### Count tokens
```python
client = GeminiClient()
token_count = client.count_tokens("Your long prompt here...")
print(f"Token count: {token_count}")
```

## 📖 Chi tiết đầy đủ

Xem file [GEMINI_MODELS.md](./GEMINI_MODELS.md) để biết:
- Cách hoạt động chi tiết của fallback system
- Tùy chỉnh nâng cao
- Troubleshooting
- Best practices

## 🆘 Hỗ trợ

- 📚 Docs: [GEMINI_MODELS.md](./GEMINI_MODELS.md)
- 🔗 Gemini API: https://ai.google.dev/docs
- 🔑 Get API Key: https://aistudio.google.com/

---

## 📚 Xem thêm

- [README.md](./README.md) - Hướng dẫn đầy đủ về toàn bộ hệ thống
- [GEMINI_MODELS.md](./GEMINI_MODELS.md) - Chi tiết về multi-model fallback
- [TESTING.md](./TESTING.md) - Testing và coverage
- [GETTING_STARTED.md](./GETTING_STARTED.md) - Quick start 5 phút

---

**Lưu ý:** Model Gemini 2.0 Flash Experimental có thể thay đổi hoặc gỡ bỏ bất kỳ lúc nào. Hệ thống sẽ tự động fallback sang model ổn định.
