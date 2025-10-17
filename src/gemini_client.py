import os
import logging
from typing import Union, List, Optional
import dotenv
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Một trình quản lý stateful cho API của Google Gemini với hỗ trợ fallback model.

    Class này sẽ quản lý:
    1. Danh sách các API key và tự động xoay vòng qua các key khi gặp lỗi quota
    2. Danh sách các model và tự động fallback khi model chính thất bại
    
    Attributes:
        api_keys: Danh sách các API key được load từ .env
        current_key_index: Index của key hiện tại đang được sử dụng
        model_names: Danh sách các model theo thứ tự ưu tiên
        current_model_index: Index của model hiện tại đang được sử dụng
        model: Instance của GenerativeModel
    """
    def __init__(self, model_names: Optional[List[str]] = None) -> None:
        dotenv.load_dotenv()
        self.api_keys: List[str] = [key for key in [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10)] if key]
        if not self.api_keys:
            logger.error("Không tìm thấy biến môi trường GEMINI_API_KEY nào trong file .env")
            raise ValueError("Không tìm thấy biến môi trường GEMINI_API_KEY nào trong file .env")

        # Nếu không truyền model_names, sử dụng từ config
        if model_names is None:
            try:
                from src.config import GEMINI_MODELS
                self.model_names: List[str] = GEMINI_MODELS
            except ImportError:
                # Fallback nếu không import được config
                self.model_names: List[str] = ["gemini-2.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-flash-8b"]
        else:
            self.model_names: List[str] = model_names

        self.current_key_index: int = 0
        self.current_model_index: int = 0
        self.model: Optional[genai.GenerativeModel] = None
        self._configure_client()
        logger.info(f"✅ GeminiClient đã khởi tạo với {len(self.api_keys)} API key(s) và {len(self.model_names)} model(s)")

    def _configure_client(self) -> bool:
        """
        Cấu hình client genai với key và model hiện tại.
        
        Returns:
            True nếu cấu hình thành công, False nếu đã hết key
        """
        if self.current_key_index >= len(self.api_keys):
            logger.warning("Đã hết key để thử")
            return False
        
        if self.current_model_index >= len(self.model_names):
            logger.warning("Đã hết model để thử")
            return False
        
        current_key = self.api_keys[self.current_key_index]
        current_model = self.model_names[self.current_model_index]
        logger.info(f"🔑 Đang cấu hình Gemini với API Key #{self.current_key_index + 1}, Model: {current_model}")
        genai.configure(api_key=current_key)
        self.model = genai.GenerativeModel(current_model)
        return True

    def _switch_to_next_key(self) -> bool:
        """
        Chuyển sang API key tiếp theo và cấu hình lại client.
        
        Returns:
            True nếu chuyển thành công, False nếu đã hết key
        """
        self.current_key_index += 1
        if self.current_key_index < len(self.api_keys):
            logger.info(f"🔄 Chuyển sang API Key #{self.current_key_index + 1}")
            self._configure_client()
            return True
        else:
            logger.error("❌ Đã thử hết tất cả các API key của Gemini")
            return False

    def _switch_to_next_model(self) -> bool:
        """
        Chuyển sang model tiếp theo trong danh sách fallback.
        Reset lại key index về 0 khi chuyển model.
        
        Returns:
            True nếu chuyển thành công, False nếu đã hết model
        """
        self.current_model_index += 1
        if self.current_model_index < len(self.model_names):
            logger.info(f"🔄 Chuyển sang model dự phòng: {self.model_names[self.current_model_index]}")
            self.current_key_index = 0  # Reset lại key về đầu khi đổi model
            self._configure_client()
            return True
        else:
            logger.error("❌ Đã thử hết tất cả các model fallback")
            return False

    def generate_content(
        self, 
        prompt: Union[str, List], 
        return_full_response: bool = False
    ) -> Union[str, GenerateContentResponse]:
        """
        Tạo nội dung với tự động xử lý key rotation và model fallback.
        
        Thứ tự thử:
        1. Model chính với tất cả các key
        2. Model dự phòng 1 với tất cả các key
        3. Model dự phòng 2 với tất cả các key
        
        Args:
            prompt: Có thể là string (text prompt) hoặc list (cho vision tasks với ảnh)
            return_full_response: Nếu True, trả về response object; nếu False, chỉ trả về text
        
        Returns:
            str hoặc GenerateContentResponse tùy thuộc vào return_full_response
            
        Raises:
            ConnectionError: Khi tất cả API key và model đều thất bại
        """
        if not self.model:
            logger.error("Model chưa được cấu hình")
            raise RuntimeError("Model chưa được cấu hình")
        
        # Vòng lặp qua các model
        while self.current_model_index < len(self.model_names):
            # Vòng lặp qua các key của model hiện tại
            while self.current_key_index < len(self.api_keys):
                try:
                    current_model_name = self.model_names[self.current_model_index]
                    logger.debug(f"Đang gửi request với Model: {current_model_name}, API Key #{self.current_key_index + 1}")
                    # Thử tạo nội dung với key và model hiện tại
                    response = self.model.generate_content(prompt)
                    
                    if return_full_response:
                        logger.info(f"✅ Request thành công với {current_model_name}, trả về full response")
                        return response
                    else:
                        logger.info(f"✅ Request thành công với {current_model_name}, trả về text")
                        return response.text.strip()
                        
                except Exception as e:
                    error_str = str(e).lower()
                    logger.warning(f"⚠️ Lỗi khi gọi API: {e}")
                    
                    # Nếu là lỗi quota hoặc key không hợp lệ, chuyển sang key tiếp theo
                    if "429" in error_str or "quota" in error_str:
                        logger.warning(f"Key #{self.current_key_index + 1} đã hết quota/rate limit")
                        if not self._switch_to_next_key():
                            # Hết key cho model này, thử model tiếp theo
                            logger.warning(f"Đã hết key cho model {self.model_names[self.current_model_index]}")
                            break
                    elif "api key not valid" in error_str or "invalid" in error_str:
                        logger.warning(f"Key #{self.current_key_index + 1} không hợp lệ")
                        if not self._switch_to_next_key():
                            break
                    elif "404" in error_str or "not found" in error_str:
                        # Model không tồn tại, chuyển sang model tiếp theo luôn
                        logger.error(f"Model {self.model_names[self.current_model_index]} không tồn tại hoặc không khả dụng")
                        break
                    else:
                        # Nếu là lỗi khác (ví dụ: lỗi nội dung không an toàn), ném ra ngay
                        logger.error(f"Lỗi không thể xử lý: {e}")
                        raise e
            
            # Đã thử hết key cho model này, chuyển sang model tiếp theo
            if not self._switch_to_next_model():
                # Đã hết model để thử
                break
        
        # Nếu vòng lặp kết thúc mà không thành công, nghĩa là đã hết tất cả key và model
        logger.error("Tất cả các API key và model của Gemini đều đã thất bại")
        raise ConnectionError("Tất cả các API key và model của Gemini đều đã thất bại.")

    def count_tokens(self, prompt: Union[str, List]) -> int:
        """
        Đếm số lượng token trong prompt.
        
        Args:
            prompt: Text hoặc list để đếm token
            
        Returns:
            Số lượng token
            
        Raises:
            RuntimeError: Nếu model chưa được cấu hình
        """
        if not self.model:
            logger.error("Model chưa được cấu hình")
            raise RuntimeError("Model chưa được cấu hình")
            
        try:
            token_count = self.model.count_tokens(prompt).total_tokens
            logger.debug(f"Token count: {token_count}")
            return token_count
        except Exception as e:
            logger.error(f"Lỗi khi đếm token: {e}")
            raise