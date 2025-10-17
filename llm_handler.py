# llm_handler.py

import time
import requests

# Sử dụng GeminiClient mới, một class quản lý stateful
from gemini_client import GeminiClient
from config import OLLAMA_API_URL, OLLAMA_MODELS, GEMINI_INPUT_TOKEN_LIMIT
from logging_config import get_logger

logger = get_logger(__name__)

# --- CẤU HÌNH ---
MAX_RETRIES = 3
RETRY_DELAY = 2 # Giây

# --- CÁC HÀM GỌI MODEL (CÓ XỬ LÝ LỖI) ---

def call_ollama(prompt: str, model_name: str) -> str:
    """
    Gửi yêu cầu đến Ollama local API. Ném ra Exception nếu có lỗi.
    """
    logger.info(f"Gửi yêu cầu đến model Ollama '{model_name}'")
    print(f"   -> 💬 Đang gửi yêu cầu đến model local '{model_name}' qua Ollama...")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        result = response_data.get("response", "").strip()
        logger.info(f"Nhận được phản hồi từ Ollama (độ dài: {len(result)} ký tự)")
        return result
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Không thể kết nối đến Ollama tại {OLLAMA_API_URL}")
        raise ConnectionError(f"Không thể kết nối đến Ollama tại {OLLAMA_API_URL}. Bạn đã bật Ollama chưa?") from e
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 404:
            logger.error(f"Endpoint Ollama không tồn tại: {OLLAMA_API_URL}")
            raise FileNotFoundError(f"Lỗi 404: Endpoint '{OLLAMA_API_URL}' không tồn tại. URL trong config.py có thể sai.") from e
        logger.error(f"Lỗi khi gọi Ollama API: {e}")
        raise IOError(f"Lỗi khi gọi Ollama API: {e}") from e

def call_gemini(prompt: str, gemini_client: GeminiClient) -> str:
    """
    Gửi yêu cầu đến Gemini API thông qua GeminiClient.
    Client sẽ tự động quản lý xoay vòng key.
    """
    if not gemini_client:
        logger.error("Gemini client chưa được khởi tạo")
        raise ValueError("Gemini client chưa được khởi tạo.")

    # Kiểm tra token chủ động
    try:
        logger.info("Đếm token cho prompt")
        print(f"   -> ℹ️ Đang đếm token cho prompt...")
        token_count = gemini_client.count_tokens(prompt).total_tokens
        logger.info(f"Prompt có {token_count} tokens")
        print(f"   -> ℹ️ Ước tính prompt có {token_count} tokens.")
        if token_count > GEMINI_INPUT_TOKEN_LIMIT:
            logger.error(f"Prompt quá lớn: {token_count} tokens > {GEMINI_INPUT_TOKEN_LIMIT}")
            raise ValueError(f"Prompt quá lớn ({token_count} tokens), vượt ngưỡng an toàn {GEMINI_INPUT_TOKEN_LIMIT} tokens.")
    except Exception as e:
        raise e

    # generate_content của client đã bao gồm logic xoay vòng key
    logger.info("Gửi yêu cầu tới Gemini API")
    result = gemini_client.generate_content(prompt)
    logger.info(f"Nhận được phản hồi từ Gemini (độ dài: {len(result)} ký tự)")
    return result

# --- HÀM LOGIC CHÍNH (RETRY & FALLBACK) ---

def generate_answer_with_fallback(prompt, model_choice, gemini_client, ollama_model_name):
    """
    Hàm chính để sinh câu trả lời, với logic fallback đã được cập nhật.
    """
    primary_func, primary_name, fallback_func, fallback_name = (None, None, None, None)
    answer = None

    if model_choice == '1':
        primary_func = lambda: call_gemini(prompt, gemini_client)
        primary_name = "Gemini"
        fallback_func = lambda: call_ollama(prompt, ollama_model_name)
        fallback_name = "Ollama"
    else:
        primary_func = lambda: call_ollama(prompt, ollama_model_name)
        primary_name = "Ollama"
        fallback_func = lambda: call_gemini(prompt, gemini_client)
        fallback_name = "Gemini"

    # --- Thử model chính ---
    logger.info(f"Thử model chính: {primary_name}")
    print(f"\n▶️ Đang thử model chính: {primary_name}...")
    try:
        answer = primary_func()
        logger.info(f"Model chính {primary_name} thành công")
        return answer
    except Exception as e:
        # Các lỗi như hết key, prompt quá lớn, connection error sẽ được bắt ở đây
        logger.error(f"Model chính ({primary_name}) thất bại: {e}")
        print(f"   -> ⚠️ Model chính ({primary_name}) thất bại hoàn toàn: {e}")

    # --- Thử model dự phòng ---
    logger.info(f"Chuyển sang model dự phòng: {fallback_name}")
    print(f"\n↪️ Chuyển sang model dự phòng: {fallback_name}...")
    try:
        answer = fallback_func()
        logger.info(f"Model dự phòng {fallback_name} thành công")
        return answer
    except Exception as e:
        logger.error(f"Model dự phòng ({fallback_name}) thất bại: {e}")
        print(f"   -> ❌ Model dự phòng ({fallback_name}) cũng thất bại: {e}")

    logger.critical("Cả hai model chính và dự phòng đều thất bại")
    return "[LỖI HỆ THỐNG] Cả hai model chính và dự phòng đều không thể phản hồi."


# --- HÀM KHỞI TẠO VÀ LỰA CHỌN ---

def initialize_and_select_llm():
    """
    Xử lý việc cấu hình và lựa chọn model của người dùng.
    Trả về: (model_choice, gemini_client, ollama_model_name)
    """
    logger.info("Bắt đầu cấu hình model sinh câu trả lời")
    print("\n✨ Đang cấu hình các model sinh câu trả lời...")
    gemini_client = None
    try:
        gemini_client = GeminiClient()
        logger.info("Khởi tạo Gemini Client thành công")
        print("   -> ✅ Gemini đã sẵn sàng (với trình quản lý API key).")
    except Exception as e:
        logger.warning(f"Không thể khởi tạo Gemini Client: {e}")
        print(f"   -> ⚠️ Không thể khởi tạo Gemini Client: {e}. Nó sẽ không khả dụng.")

    ollama_model_name = ""
    model_choice = ""
    
    while True:
        print("\nVui lòng chọn model CHÍNH để sinh câu trả lời:")
        prompt_text = "   1: Gemini (Cloud API)\n   2: Ollama (Local)\nLựa chọn của bạn: "
        model_choice = input(prompt_text).strip()
        
        if model_choice == '1':
            if gemini_client:
                logger.info("Người dùng chọn Gemini làm model chính")
                print("   -> ✅ Model chính là Gemini.")
                return model_choice, gemini_client, ollama_model_name
            else:
                logger.warning("Gemini chưa được cấu hình, yêu cầu chọn Ollama")
                print("   -> ❌ Gemini chưa được cấu hình, vui lòng chọn Ollama.")
        elif model_choice == '2':
            if not OLLAMA_MODELS:
                logger.warning("Danh sách model Ollama trong config.py đang trống")
                print("   -> ❌ Danh sách model Ollama trong config.py đang trống.")
                continue

            print("   -> Vui lòng chọn model Ollama:")
            for i, model in enumerate(OLLAMA_MODELS):
                default_text = " (mặc định)" if i == 0 else ""
                print(f"      {i+1}: {model}{default_text}")

            while True:
                choice = input(f"   -> Lựa chọn của bạn (nhấn Enter để chọn mặc định): ").strip()
                if not choice:
                    ollama_model_name = OLLAMA_MODELS[0]
                    break
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(OLLAMA_MODELS):
                        ollama_model_name = OLLAMA_MODELS[choice_idx]
                        break
                    else:
                        print("      -> Lựa chọn không hợp lệ.")
                except ValueError:
                    print("      -> Vui lòng nhập một số.")
            
            logger.info(f"Người dùng chọn model Ollama: {ollama_model_name}")
            print(f"   -> ✅ Model chính là '{ollama_model_name}' từ Ollama.")
            return model_choice, gemini_client, ollama_model_name
        else:
            logger.warning(f"Lựa chọn không hợp lệ: {model_choice}")
            print("   -> Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")