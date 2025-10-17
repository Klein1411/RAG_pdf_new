# Clean PDF Module Documentation

## 📋 Tổng quan

Module `clean_pdf.py` cung cấp các hàm để làm sạch và chuẩn hóa văn bản được trích xuất từ PDF.

## 🎯 Mục đích

Khi trích xuất văn bản từ PDF (bằng pdfplumber, OCR, v.v.), thường gặp các vấn đề:
- ❌ Nhiều khoảng trắng thừa
- ❌ Dòng trống liên tiếp
- ❌ Từ bị ngắt dòng (hyphenation)
- ❌ Câu bị ngắt không đúng chỗ
- ❌ Ký tự đặc biệt không mong muốn

Module này giải quyết tất cả các vấn đề trên.

---

## 🔧 Các hàm chính

### 1. `clean_extracted_text(text, aggressive=False)`

**Hàm làm sạch chính** - áp dụng tất cả các bước xử lý.

```python
from src.clean_pdf import clean_extracted_text

# Làm sạch đơn giản (mặc định)
cleaned = clean_extracted_text(raw_text)

# Làm sạch aggressive (ghép câu bị ngắt)
cleaned = clean_extracted_text(raw_text, aggressive=True)
```

**Các bước xử lý:**
1. Chuẩn hóa xuống dòng (\r\n → \n)
2. Loại bỏ ký tự đặc biệt
3. Sửa từ bị ngắt dòng (exam-\nple → example)
4. Loại bỏ khoảng trắng thừa
5. Ghép câu bị ngắt (nếu aggressive=True)
6. Loại bỏ dòng trống thừa

**Khi nào dùng aggressive=True:**
- ✅ Văn bản liên tục (sách, bài báo)
- ❌ Danh sách, mục lục (cần giữ cấu trúc)

---

### 2. `clean_table_text(table)`

Làm sạch văn bản trong các ô của bảng.

```python
from src.clean_pdf import clean_table_text

# table = [[cell1, cell2, ...], [cell1, cell2, ...], ...]
cleaned_table = clean_table_text(table)
```

**Xử lý:**
- Loại bỏ khoảng trắng thừa trong mỗi ô
- Chuyển xuống dòng trong cell thành khoảng trắng
- Xử lý giá trị None thành ""

---

### 3. `quick_clean(text)`

Làm sạch nhanh, không aggressive.

```python
from src.clean_pdf import quick_clean

cleaned = quick_clean(text)
```

**Áp dụng:**
- Chuẩn hóa xuống dòng
- Loại bỏ khoảng trắng thừa
- Loại bỏ dòng trống thừa

**Khi nào dùng:**
- Văn bản đã khá sạch
- Cần giữ nguyên cấu trúc gốc
- Xử lý nhanh

---

## 🛠️ Các hàm tiện ích

### `clean_whitespace(text)`
Loại bỏ khoảng trắng thừa.

### `remove_empty_lines(text, max_consecutive=1)`
Loại bỏ dòng trống thừa, giữ tối đa N dòng trống liên tiếp.

### `remove_special_chars(text, keep_chars=None)`
Loại bỏ ký tự đặc biệt.

### `normalize_line_breaks(text)`
Chuẩn hóa xuống dòng: \r\n, \r → \n

### `fix_hyphenation(text)`
Sửa từ bị ngắt dòng: "exam-\nple" → "example"

### `merge_broken_sentences(text)`
Ghép câu bị ngắt không đúng chỗ.

---

## 📝 Ví dụ sử dụng

### Ví dụ 1: Làm sạch text từ pdfplumber

```python
import pdfplumber
from src.clean_pdf import clean_extracted_text

with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        raw_text = page.extract_text()
        clean_text = clean_extracted_text(raw_text)
        print(clean_text)
```

### Ví dụ 2: Làm sạch bảng

```python
import pdfplumber
from src.clean_pdf import clean_table_text

with pdfplumber.open("file.pdf") as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            cleaned = clean_table_text(table)
            print(cleaned)
```

### Ví dụ 3: Xử lý văn bản từ OCR

```python
from src.clean_pdf import clean_extracted_text

# OCR text thường rất bẩn
ocr_text = easyocr_result(image)

# Làm sạch aggressive
clean_text = clean_extracted_text(ocr_text, aggressive=True)
```

---

## 🔄 Tích hợp với read_pdf.py

Module `read_pdf.py` đã được refactor để sử dụng `clean_pdf.py`:

```python
from src.clean_pdf import clean_extracted_text, clean_table_text

# Làm sạch text
text = page.extract_text(layout=False)
text = clean_extracted_text(text)

# Làm sạch tables
tables = page.extract_tables()
if tables:
    tables = [clean_table_text(table) for table in tables]
```

---

## 🧪 Testing

Chạy file trực tiếp để test:

```bash
python src/clean_pdf.py
```

Output sẽ hiển thị kết quả của các hàm clean với sample text.

---

## 📊 So sánh Before/After

### Before (raw pdfplumber output):
```
           Các            chỉ        số       đánh               giá      
                                                                           
                                                                           
           chatbot                                                        
```

### After (clean_extracted_text):
```
Các chỉ số đánh giá chatbot
```

---

## ⚙️ Tùy chỉnh

### Giữ lại ký tự đặc biệt cụ thể

```python
from src.clean_pdf import remove_special_chars

# Giữ thêm @ và #
text = remove_special_chars(text, keep_chars=r'.,!?;:()[]{}"\'-@#\n\t ')
```

### Giữ nhiều dòng trống hơn

```python
from src.clean_pdf import remove_empty_lines

# Giữ tối đa 2 dòng trống liên tiếp
text = remove_empty_lines(text, max_consecutive=2)
```

---

## 💡 Best Practices

1. **Luôn làm sạch text từ PDF** - Văn bản raw từ PDF thường rất bẩn
2. **Dùng aggressive=False cho danh sách** - Để giữ cấu trúc
3. **Dùng aggressive=True cho văn bản liên tục** - Để ghép câu
4. **Làm sạch table riêng** - Dùng `clean_table_text()` cho bảng
5. **Test với PDF thật** - Mỗi PDF có layout khác nhau

---

## 🐛 Troubleshooting

### Vấn đề: Mất mất cấu trúc danh sách

**Nguyên nhân:** Sử dụng `aggressive=True`

**Giải pháp:**
```python
cleaned = clean_extracted_text(text, aggressive=False)
```

### Vấn đề: Vẫn còn nhiều dòng trống

**Nguyên nhân:** max_consecutive quá cao

**Giải pháp:**
```python
from src.clean_pdf import remove_empty_lines
text = remove_empty_lines(text, max_consecutive=0)  # Loại bỏ tất cả dòng trống
```

### Vấn đề: Mất ký tự quan trọng

**Nguyên nhân:** `remove_special_chars()` loại bỏ quá mức

**Giải pháp:**
```python
# Bỏ qua bước remove_special_chars
text = clean_whitespace(text)
text = remove_empty_lines(text)
```

---

## 📚 Related Documentation

- [read_pdf.py](./read_pdf.py) - Module trích xuất PDF
- [export_md.py](./export_md.py) - Module export Markdown
- [DEV_SETUP.md](../docs/DEV_SETUP.md) - Development setup

---

## 🔮 Future Enhancements

- [ ] Hỗ trợ nhiều ngôn ngữ (tiếng Việt, tiếng Trung, v.v.)
- [ ] Phát hiện và giữ lại code blocks
- [ ] Cải thiện merge_broken_sentences với ML
- [ ] Hỗ trợ làm sạch footnotes và headers
- [ ] Performance optimization cho văn bản lớn
