import os
import dotenv
import google.generativeai as genai

# Tải các biến môi trường
dotenv.load_dotenv()

# Lấy danh sách API keys từ .env
API_KEYS = [key for key in [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 4)] if key]

# Danh sách các model để thử
GENERATIVE_MODELS = ["gemini-2.5-flash",
                     "gemini-2.0-flash",
                     "gemini-1.5-flash"]

def configure_gemini():
    """
    Tự động tìm và cấu hình API key và model generative tốt nhất hoạt động.
    Trả về model đã được khởi tạo nếu thành công, ngược lại trả về None.
    """
    if not API_KEYS:
        print("⚠️ Không tìm thấy API key nào trong file .env.")
        return None

    print("🔄 Đang tìm API key và model phù hợp...")
    for i, key in enumerate(API_KEYS):
        print(f"🔑 Thử với API Key #{i + 1}...")
        genai.configure(api_key=key)
        
        # Thử với các model generative
        for model_name in GENERATIVE_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                model.generate_content("test")
                print(f"   -> ✅ Key #{i + 1} và model '{model_name}' đã sẵn sàng.")
                # Trả về model đầu tiên hoạt động
                return model
            except Exception as e:
                # In lỗi ra để người dùng biết chi tiết
                # print(f"   -> ❌ Lỗi với model '{model_name}': {e}")
                # Chỉ thông báo model không hoạt động cho gọn
                print(f"   -> ❌ Model '{model_name}' không hoạt động với key này.")
                continue # Thử model tiếp theo
    
    print("❌ Không tìm thấy API key hoặc model nào hoạt động.")
    return None

if __name__ == "__main__":
    # Chạy cấu hình và kiểm tra
    active_model = configure_gemini()
    
    if active_model:
        print(f"\n✅ Cấu hình thành công! Model '{active_model.model_name}' đang được sử dụng.")
    else:
        print("\n❌ Không thể cấu hình Gemini. Vui lòng kiểm tra lại API keys và quyền truy cập.")
