"""
Tích hợp LangChain LLM - Giao diện LLM hợp nhất sử dụng LangChain

Hybrid approach:
- Gemini: google-generativeai trực tiếp (vì LangChain v1beta API không support nhiều models mới)
- Ollama: LangChain wrapper (hoạt động tốt)

Lợi ích:
- Gemini: Truy cập đầy đủ 41+ models mới nhất (gemini-2.5-flash, gemini-2.0-flash, v.v.)
- Ollama: Dùng LangChain cho tích hợp tốt và streaming
- Interface thống nhất cho cả hai
- Auto-fallback qua multiple keys và models
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv

# Thêm thư mục gốc vào sys.path để import được src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Nhập LangChain (cho Ollama)
from langchain_core.language_models import BaseLanguageModel
from langchain_community.llms import Ollama

# Nhập google-generativeai trực tiếp (cho Gemini)
import google.generativeai as genai

from src.logging_config import get_logger

logger = get_logger(__name__)

# Tải biến môi trường
load_dotenv()

# Nhập các model Gemini từ config
try:
    from src.config import GEMINI_MODELS
except ImportError:
    # Fallback nếu không có trong config  
    GEMINI_MODELS = [
        "models/gemini-2.5-flash",     # Mới nhất
        "models/gemini-2.0-flash",     # Dự phòng
        "models/gemini-flash-latest",  # Stable alias
        "models/gemini-pro-latest"     # Fallback
    ]
    logger.warning("Không tìm thấy GEMINI_MODELS trong config, dùng danh sách mặc định")


class LLMManager:
    """
    Trình quản lý LLM hợp nhất.
    
    Hybrid approach:
    - Google Gemini: Dùng google-generativeai trực tiếp (genai.GenerativeModel)
    - Ollama: Dùng LangChain wrapper (langchain-community.llms.Ollama)
    
    Tính năng:
    - Tự động chọn nhà cung cấp
    - Tự động chuyển đổi API key khi gặp lỗi (Gemini)
    - Tự động thử các model fallback (Gemini)
    - Logic thử lại với auto-recovery
    - Xử lý lỗi thống nhất
    - Interface generate() chung cho cả 2 providers
    """
    
    def __init__(
        self,
        provider: str = "gemini",  # "gemini" hoặc "ollama"
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """
        Khởi tạo Trình quản lý LLM.
        
        Đối số:
            provider: Nhà cung cấp LLM ("gemini" hoặc "ollama")
            model_name: Tên mô hình (nếu None, sử dụng mặc định)
            temperature: Nhiệt độ lấy mẫu (0-1)
            max_tokens: Số lượng token tối đa để tạo
        """
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Type: Union vì Gemini dùng GenerativeModel, Ollama dùng LangChain
        self.llm: Optional[Union[Any, BaseLanguageModel]] = None  # type: ignore
        
        # Quản lý API keys và models cho Gemini
        self.gemini_api_keys: List[str] = []
        self.current_key_index: int = 0
        self.available_models: List[str] = GEMINI_MODELS.copy()
        self.current_model_index: int = 0
        
        # Initialize LLM
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Khởi tạo LangChain LLM dựa trên nhà cung cấp."""
        if self.provider == "gemini":
            self._initialize_gemini()
        elif self.provider == "ollama":
            self._initialize_ollama()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _initialize_gemini(self):
        """Khởi tạo Google Gemini qua LangChain với auto-retry."""
        # Lấy tất cả API keys
        self.gemini_api_keys = self._get_gemini_api_keys()
        
        if not self.gemini_api_keys:
            raise ValueError("❌ Không tìm thấy Gemini API key trong .env")
        
        logger.info(f"📋 Tìm thấy {len(self.gemini_api_keys)} Gemini API key(s)")
        logger.info(f"📋 Có {len(self.available_models)} model(s): {', '.join(self.available_models)}")
        
        # Thử tất cả các kết hợp key + model cho đến khi thành công
        for key_idx in range(len(self.gemini_api_keys)):
            self.current_key_index = key_idx
            for model_idx in range(len(self.available_models)):
                self.current_model_index = model_idx
                
                if self._try_initialize_gemini():
                    return  # Thành công!
        
        # Đã thử hết tất cả kết hợp
        raise RuntimeError("❌ Không thể khởi tạo Gemini với bất kỳ API key hoặc model nào")
    
    def _try_initialize_gemini(self) -> bool:
        """
        Thử khởi tạo Gemini với key và model hiện tại.
        Dùng google-generativeai trực tiếp.
        Returns True nếu thành công.
        """
        try:
            api_key = self.gemini_api_keys[self.current_key_index]
            
            # Luôn dùng model từ available_models theo index (để loop qua tất cả)
            model = self.available_models[self.current_model_index]
            
            # Mask API key cho log
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            logger.info(f"🔑 Đang thử API key [{self.current_key_index + 1}/{len(self.gemini_api_keys)}]: {masked_key}")
            logger.info(f"🤖 Đang thử model [{self.current_model_index + 1}/{len(self.available_models)}]: {model}")
            
            # Configure google-generativeai
            genai.configure(api_key=api_key)
            
            # Khởi tạo model
            generation_config = {
                "temperature": self.temperature,
            }
            if self.max_tokens:
                generation_config["max_output_tokens"] = self.max_tokens
            
            self.llm = genai.GenerativeModel(
                model_name=model,
                generation_config=generation_config
            )
            
            # Test với prompt đơn giản
            test_response = self.llm.generate_content("Hi")
            
            logger.info(f"✅ Khởi tạo thành công Gemini: {model} (Key {self.current_key_index + 1})")
            logger.info(f"   Test response: {test_response.text[:50]}...")
            self.model_name = model  # Cập nhật model_name
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Thất bại với key {self.current_key_index + 1}, model {model}: {str(e)[:100]}")
            return False
    
    def _initialize_ollama(self):
        """Initialize Ollama via LangChain."""
        try:
            # Default model if not specified
            model = self.model_name or "llama3:latest"
            
            # Initialize LangChain Ollama
            self.llm = Ollama(
                model=model,
                temperature=self.temperature,
                num_predict=self.max_tokens
            )
            
            logger.info(f"✅ Initialized Ollama LLM: {model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            raise
    
    def _get_gemini_api_keys(self) -> List[str]:
        """
        Lấy tất cả Gemini API keys từ môi trường.
        Hỗ trợ: 
        - GEMINI_API_KEY hoặc GEMINI_API_KEY_1
        - GEMINI_API_KEY_2
        - GEMINI_API_KEY_3
        - GEMINI_API_KEY_4
        """
        keys = []
        for i in range(1, 5):  # Hỗ trợ tới 4 keys
            # Thử cả 2 format: GEMINI_API_KEY và GEMINI_API_KEY_1
            if i == 1:
                key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_1"]
            else:
                key_names = [f"GEMINI_API_KEY_{i}"]
            
            for key_name in key_names:
                key = os.getenv(key_name)
                if key and key.strip():
                    keys.append(key.strip())
                    logger.debug(f"✓ Tìm thấy {key_name}")
                    break  # Đã tìm thấy key cho slot này, không cần thử format khác
        
        return keys
    
    def switch_gemini_key(self) -> bool:
        """
        Chuyển sang API key tiếp theo.
        Returns True nếu còn key để thử.
        """
        if self.provider != "gemini":
            return False
        
        self.current_key_index += 1
        
        if self.current_key_index >= len(self.gemini_api_keys):
            logger.warning("⚠️ Đã hết API key để thử")
            self.current_key_index = 0  # Reset về key đầu
            return False
        
        logger.info(f"🔄 Chuyển sang API key {self.current_key_index + 1}/{len(self.gemini_api_keys)}")
        
        # Thử khởi tạo lại với key mới
        return self._try_initialize_gemini()
    
    def switch_gemini_model(self) -> bool:
        """
        Chuyển sang model tiếp theo trong danh sách GEMINI_MODELS.
        Returns True nếu còn model để thử.
        """
        if self.provider != "gemini":
            return False
        
        self.current_model_index += 1
        
        if self.current_model_index >= len(self.available_models):
            logger.warning("⚠️ Đã thử hết tất cả models")
            self.current_model_index = 0  # Reset về model đầu
            return False
        
        logger.info(f"🔄 Chuyển sang model {self.current_model_index + 1}/{len(self.available_models)}")
        
        # Thử khởi tạo lại với model mới
        return self._try_initialize_gemini()
    
    def auto_recover(self) -> bool:
        """
        Tự động khôi phục khi gặp lỗi bằng cách thử:
        1. Model tiếp theo với key hiện tại
        2. Key tiếp theo với model đầu tiên
        
        Returns True nếu khôi phục thành công.
        """
        if self.provider != "gemini":
            return False
        
        logger.info("🔧 Đang tự động khôi phục...")
        
        # Thử 1: Chuyển model
        if self.switch_gemini_model():
            return True
        
        # Thử 2: Chuyển key (reset model về đầu)
        self.current_model_index = 0
        if self.switch_gemini_key():
            return True
        
        logger.error("❌ Không thể tự động khôi phục")
        return False
    
    def generate(self, prompt: str, auto_retry: bool = True, **kwargs) -> str:
        """
        Generate text from prompt với tự động retry.
        
        Hybrid approach:
        - Gemini: Dùng google-generativeai.GenerativeModel.generate_content()
        - Ollama: Dùng LangChain invoke()
        
        Args:
            prompt: Input prompt
            auto_retry: Tự động thử lại với key/model khác nếu lỗi
            **kwargs: Additional arguments for LLM
            
        Returns:
            Generated text
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if self.llm is None:
                    raise RuntimeError("LLM chưa được khởi tạo")
                
                # Gemini: Dùng generate_content() trực tiếp
                if self.provider == "gemini":
                    response = self.llm.generate_content(prompt, **kwargs)  # type: ignore
                    return response.text  # type: ignore
                
                # Ollama: Dùng LangChain invoke()
                else:
                    response = self.llm.invoke(prompt, **kwargs)
                    # Extract text from response
                    if hasattr(response, 'content'):
                        return str(response.content)
                    else:
                        return str(response)
                    
            except Exception as e:
                error_msg = str(e).lower()
                retry_count += 1
                
                logger.error(f"❌ Lỗi generation (lần {retry_count}/{max_retries}): {e}")
                
                # Kiểm tra nếu là lỗi API key hoặc quota
                is_api_error = any(keyword in error_msg for keyword in [
                    'api key', 'quota', 'rate limit', 'invalid', 'expired',
                    'permission', 'forbidden', '429', '401', '403', '404'
                ])
                
                if auto_retry and is_api_error and self.provider == "gemini":
                    logger.info("🔄 Đang thử khôi phục tự động...")
                    
                    if self.auto_recover():
                        logger.info("✅ Khôi phục thành công, thử lại...")
                        continue
                    else:
                        logger.error("❌ Không thể khôi phục")
                        raise
                else:
                    # Lỗi khác hoặc hết lượt retry
                    if retry_count >= max_retries:
                        logger.error(f"❌ Đã thử {max_retries} lần, vẫn thất bại")
                    raise
        
        # Fallback nếu vượt quá max_retries (không nên đến đây)
        raise RuntimeError("Đã vượt quá số lần thử tối đa")
    
    def generate_with_history(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Generate with conversation history.
        
        NOTE: Hiện tại chỉ support cho Ollama (dùng LangChain messages).
        Gemini sẽ dùng format khác (chưa implement).
        
        Args:
            prompt: Current prompt
            history: List of {'role': 'user'/'assistant', 'content': str}
            **kwargs: Additional arguments
            
        Returns:
            Generated text
        """
        if self.provider == "gemini":
            # Gemini dùng google-generativeai chat format (chưa implement)
            # Tạm thời fallback về generate() thông thường
            logger.warning("generate_with_history chưa support Gemini, dùng generate() thay thế")
            return self.generate(prompt, **kwargs)
        
        # Ollama: Dùng LangChain messages (cần import)
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            
            if self.llm is None:
                raise RuntimeError("LLM not initialized")
            
            # Build messages from history
            messages = []
            
            if history:
                for msg in history:
                    if msg['role'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        messages.append(SystemMessage(content=msg['content']))
            
            # Add current prompt
            messages.append(HumanMessage(content=prompt))
            
            # Generate
            response = self.llm.invoke(messages, **kwargs)
            
            # Extract text
            if hasattr(response, 'content'):
                return str(response.content)  # type: ignore
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Generation with history error: {e}")
            raise
    
    def switch_provider(self, provider: str, model_name: Optional[str] = None):
        """
        Switch to different provider.
        
        Args:
            provider: New provider name
            model_name: Optional model name
        """
        self.provider = provider
        if model_name:
            self.model_name = model_name
        self._initialize_llm()
    
    def get_info(self) -> Dict[str, Any]:
        """Lấy thông tin LLM hiện tại."""
        info = {
            'provider': self.provider,
            'model': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        if self.provider == "gemini":
            info.update({
                'current_key_index': self.current_key_index + 1,
                'total_keys': len(self.gemini_api_keys),
                'current_model_index': self.current_model_index + 1,
                'available_models': self.available_models
            })
        
        return info
    
    def get_langchain_llm(self) -> BaseLanguageModel:
        """
        Trả về LangChain-compatible LLM cho RAG chains.
        
        NOTE: Gemini hiện dùng google-generativeai trực tiếp (không phải LangChain Runnable).
        Method này chỉ support Ollama cho LangChain chains.
        
        Nếu provider là Gemini, sẽ raise error vì không tương thích với LangChain chains.
        Khuyến nghị: Dùng generate() method trực tiếp thay vì LangChain chains.
        
        Returns:
            BaseLanguageModel cho LangChain chains (chỉ Ollama)
            
        Raises:
            ValueError nếu provider là Gemini
        """
        if self.provider == "gemini":
            raise ValueError(
                "Gemini không support LangChain chains (dùng google-generativeai trực tiếp). "
                "Khuyến nghị: Dùng llm_manager.generate() thay vì chains, "
                "hoặc switch sang Ollama với llm_manager.switch_provider('ollama')"
            )
        
        if self.llm is None:
            raise RuntimeError("LLM chưa được khởi tạo")
        
        return self.llm  # type: ignore


# Convenience functions (backward compatibility)

def initialize_and_select_llm_langchain() -> tuple[str, LLMManager]:
    """
    Interactive LLM selection (LangChain version).
    
    Returns:
        (model_choice, llm_manager)
        model_choice: "1" for Gemini, "2" for Ollama
    """
    print("\n🤖 Chọn LLM Provider:")
    print("1. Google Gemini (Cloud API - Auto fallback)")
    print("2. Ollama (Local)")
    
    choice = input("Chọn (1/2): ").strip()
    
    if choice == "1":
        # Gemini - hiển thị models từ config
        print(f"\n📋 Available Gemini models ({len(GEMINI_MODELS)}):")
        for i, model in enumerate(GEMINI_MODELS, 1):
            print(f"{i}. {model}")
        
        model_idx = input(f"Chọn model (1-{len(GEMINI_MODELS)}) [default: 1]: ").strip()
        model_idx = int(model_idx) if model_idx else 1
        model_name = GEMINI_MODELS[model_idx - 1] if 1 <= model_idx <= len(GEMINI_MODELS) else GEMINI_MODELS[0]
        
        print(f"\n🔑 Đang khởi tạo Gemini với auto-fallback...")
        llm_manager = LLMManager(
            provider="gemini",
            model_name=model_name,
            temperature=0.7
        )
        
        print(f"✅ Đã sẵn sàng với: {llm_manager.model_name}")
        return "1", llm_manager
        
    elif choice == "2":
        # Ollama
        print("\n💡 Nhập tên Ollama model (ví dụ: llama2, mistral)")
        model_name = input("Tên model [mặc định: llama2]: ").strip() or "llama2"
        
        llm_manager = LLMManager(
            provider="ollama",
            model_name=model_name,
            temperature=0.7
        )
        
        return "2", llm_manager
        
    else:
        print("❌ Lựa chọn không hợp lệ, mặc định dùng Gemini")
        llm_manager = LLMManager(provider="gemini")
        return "1", llm_manager


def get_gemini_llm(model: str = "gemini-1.5-flash") -> LLMManager:
    """Quick Gemini LLM."""
    return LLMManager(provider="gemini", model_name=model)


def get_ollama_llm(model: str = "llama3:latest") -> LLMManager:
    """Quick Ollama LLM."""
    return LLMManager(provider="ollama", model_name=model)


# Example usage
if __name__ == "__main__":
    print("="*70)
    print("TEST: LangChain LLM Integration")
    print("="*70)
    
    # Test Gemini
    print("\n1. Testing Gemini...")
    try:
        gemini_llm = get_gemini_llm()
        print(f"   Info: {gemini_llm.get_info()}")
        
        response = gemini_llm.generate("Say hello in 5 words")
        print(f"   Response: {response}")
        print("   ✅ Gemini works!")
    except Exception as e:
        print(f"   ❌ Gemini failed: {e}")
    
    # Test Ollama (if available)
    print("\n2. Testing Ollama...")
    try:
        ollama_llm = get_ollama_llm()
        print(f"   Info: {ollama_llm.get_info()}")
        
        response = ollama_llm.generate("Say hello in 5 words")
        print(f"   Response: {response}")
        print("   ✅ Ollama works!")
    except Exception as e:
        print(f"   ⚠️  Ollama not available: {e}")
    
    print("\n" + "="*70)
    print("✅ LangChain LLM integration test complete")
