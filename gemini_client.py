import os
# Tắt log chi tiết của gRPC, vốn gây ra thông báo "ALTS creds ignored"
os.environ['GRPC_VERBOSITY'] = 'ERROR'

import dotenv
import google.generativeai as genai
from PIL import Image

# Tải các biến môi trường từ file .env
dotenv.load_dotenv()

# Đọc tất cả các API key có sẵn theo định dạng GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
API_KEYS = [key for key in [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4)] if key]

if not API_KEYS:
    print("⚠️ Không tìm thấy key Gemini nào theo định dạng GEMINI_API_KEY_1, ... trong file .env.")

# Bạn có thể thay đổi tên model ở đây nếu cần. Model 'gemini-2.5-flash' chưa tồn tại, sử dụng 'gemini-1.5-flash'.
MODEL_NAME = "gemini-2.5-flash"

def describe_slide(img: Image.Image) -> str:
    """
    Sử dụng Gemini để mô tả hình ảnh của một slide, với cơ chế tự động xoay vòng API key khi gặp lỗi.
    """
    if not API_KEYS:
        return "[Chức năng mô tả ảnh bị tắt do thiếu API Keys]"

    # Lặp qua từng key để thử
    for i, key in enumerate(API_KEYS):
        try:
            print(f"🔑 Thử với API Key #{i + 1}...")
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            
            prompt = '''Bạn là một chuyên gia phân tích tài liệu và slide thuyết trình.
Nhiệm vụ của bạn là xem hình ảnh của một slide và chuyển đổi nó thành một văn bản Markdown chi tiết, có cấu trúc.
- Giữ lại các tiêu đề, đề mục.
- Chuyển đổi các danh sách (bullet points) thành danh sách Markdown.
- Trích xuất và tái tạo lại các bảng biểu một cách chính xác nhất có thể ở định dạng Markdown table.
- Diễn giải và tóm tắt nội dung chính của slide một cách mạch lạc.
- Luôn trả lời bằng ngôn ngữ gốc của văn bản.'''
            
            response = model.generate_content([prompt, img])
            print(f"   -> ✅ Key #{i + 1} thành công!")
            return response.text.strip()
        
        except Exception as e:
            print(f"   -> ❌ Lỗi với Key #{i + 1}: {e}")
            # Nếu là key cuối cùng mà vẫn lỗi, vòng lặp sẽ kết thúc
            continue
    
    # Trả về thông báo lỗi chung nếu tất cả các key đều thất bại
    return "[Tất cả các API key đều gặp lỗi. Vui lòng kiểm tra lại.]"
