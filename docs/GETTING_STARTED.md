# 🎯 Getting Started - 5 Phút Bắt Đầu

Hướng dẫn siêu ngắn gọn để chạy được RAG PDF System!

---

## ⚡ Cài đặt siêu nhanh

### 1. Clone & Install (2 phút)

```bash
git clone https://github.com/Klein1411/RAG_pdf_new.git
cd RAG_pdf_new
pip install -r requirements.txt
```

### 2. Tạo file `.env` (30 giây)

```env
GEMINI_API_KEY_1=AIzaSy...  # Lấy tại https://aistudio.google.com
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. Cấu hình PDF (10 giây)

Sửa `config.py`:
```python
PDF_PATH = "d:/path/to/your/file.pdf"
```

### 4. Chạy (30 giây)

```bash
# Bước 1: Đồng bộ PDF
python populate_milvus.py

# Bước 2: Hỏi đáp
python qa_app.py
```

---

## 🎊 Xong rồi!

Giờ bạn có thể:
- ❓ Đặt câu hỏi về nội dung PDF
- 📄 Xem nguồn tham khảo (số trang)
- 🔄 Hệ thống tự động fallback khi lỗi

---

## 📚 Muốn tìm hiểu thêm?

| Nội dung | File |
|----------|------|
| 📖 Hướng dẫn đầy đủ | [README.md](./README.md) |
| 🚀 Gemini setup | [QUICK_START_GEMINI.md](./QUICK_START_GEMINI.md) |
| 🤖 Multi-model chi tiết | [GEMINI_MODELS.md](./GEMINI_MODELS.md) |
| 🧪 Testing | [TESTING.md](./TESTING.md) |

---

## 🆘 Lỗi thường gặp

### "Không tìm thấy API key"
→ Tạo file `.env` với `GEMINI_API_KEY_1=...`

### "Không kết nối Milvus"
→ Chạy: `docker run -d -p 19530:19530 milvusdb/milvus:latest`

### "Hết quota"
→ Thêm nhiều key vào `.env`: `GEMINI_API_KEY_2=...`, `GEMINI_API_KEY_3=...`

---

**Happy coding! 🎉**
