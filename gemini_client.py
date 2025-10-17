import os
import dotenv
import google.generativeai as genai

class GeminiClient:
    """
    Một trình quản lý stateful cho API của Google Gemini.

    Class này sẽ quản lý một danh sách các API key và tự động xoay vòng
    qua các key khi gặp lỗi có thể thử lại (ví dụ: lỗi quota).
    """
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        dotenv.load_dotenv()
        self.api_keys = [key for key in [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10)] if key]
        if not self.api_keys:
            raise ValueError("Không tìm thấy biến môi trường GEMINI_API_KEY nào trong file .env")

        self.current_key_index = 0
        self.model_name = model_name # Sử dụng model_name được truyền vào
        self._configure_client()

    def _configure_client(self):
        """Cấu hình client genai với key hiện tại."""
        if self.current_key_index >= len(self.api_keys):
            return False # Đã hết key để thử
        
        current_key = self.api_keys[self.current_key_index]
        print(f"🔑 Đang cấu hình Gemini với API Key #{self.current_key_index + 1}")
        genai.configure(api_key=current_key)
        self.model = genai.GenerativeModel(self.model_name)
        return True

    def _switch_to_next_key(self) -> bool:
        """
        Chuyển sang API key tiếp theo và cấu hình lại client.
        Trả về True nếu chuyển thành công, False nếu đã hết key.
        """
        self.current_key_index += 1
        if self.current_key_index < len(self.api_keys):
            self._configure_client()
            return True
        else:
            print("   -> ❌ Đã thử hết tất cả các API key của Gemini.")
            return False

    def generate_content(self, prompt, return_full_response: bool = False):
        """
        Tạo nội dung và tự động xử lý việc xoay vòng key khi gặp lỗi.
        
        Args:
            prompt: Có thể là string (text prompt) hoặc list (cho vision tasks với ảnh)
            return_full_response: Nếu True, trả về response object; nếu False, chỉ trả về text
        
        Returns:
            str hoặc response object tùy thuộc vào return_full_response
        """
        while self.current_key_index < len(self.api_keys):
            try:
                # Thử tạo nội dung với key hiện tại
                response = self.model.generate_content(prompt)
                
                if return_full_response:
                    return response
                else:
                    return response.text.strip()
                    
            except Exception as e:
                error_str = str(e).lower()
                # Nếu là lỗi quota hoặc key không hợp lệ, chuyển sang key tiếp theo
                if "429" in error_str and "quota" in error_str:
                    print(f"   -> ⚠️ Key #{self.current_key_index + 1} đã hết quota. Đang chuyển key...")
                    if not self._switch_to_next_key():
                        # Nếu không còn key nào, ném ra lỗi cuối cùng
                        raise ConnectionError("Tất cả các API key của Gemini đều đã hết quota.")
                elif "api key not valid" in error_str:
                    print(f"   -> ⚠️ Key #{self.current_key_index + 1} không hợp lệ. Đang chuyển key...")
                    if not self._switch_to_next_key():
                        raise ConnectionError("Tất cả các API key của Gemini đều không hợp lệ.")
                else:
                    # Nếu là lỗi khác (ví dụ: lỗi nội dung không an toàn), ném ra ngay
                    raise e
        
        # Nếu vòng lặp kết thúc mà không thành công, nghĩa là đã hết key
        raise ConnectionError("Tất cả các API key của Gemini đều đã được thử và thất bại.")

    def count_tokens(self, prompt: str):
        """Wrapper cho hàm count_tokens của model hiện tại."""
        return self.model.count_tokens(prompt)