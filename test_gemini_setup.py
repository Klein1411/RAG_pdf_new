#!/usr/bin/env python3
"""
Test script để kiểm tra cấu hình Gemini với multi-model fallback
"""

from gemini_client import GeminiClient
from config import GEMINI_MODELS
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gemini_basic():
    """Test cơ bản: khởi tạo và gọi API"""
    print("\n" + "="*60)
    print("TEST 1: Khởi tạo GeminiClient")
    print("="*60)
    
    try:
        client = GeminiClient()
        print(f"✅ Khởi tạo thành công với {len(client.model_names)} model(s):")
        for i, model in enumerate(client.model_names, 1):
            print(f"   {i}. {model}")
        print(f"✅ Có {len(client.api_keys)} API key(s) khả dụng")
        return client
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        return None

def test_text_generation(client):
    """Test sinh văn bản đơn giản"""
    print("\n" + "="*60)
    print("TEST 2: Text Generation")
    print("="*60)
    
    if not client:
        print("⏭️ Bỏ qua test (client không khả dụng)")
        return
    
    test_prompt = "Viết 1 câu ngắn về AI (tiếng Việt)"
    
    try:
        print(f"📝 Prompt: '{test_prompt}'")
        print("⏳ Đang gửi request...")
        
        response = client.generate_content(test_prompt)
        
        print(f"\n✅ Phản hồi thành công!")
        print(f"📄 Nội dung: {response}")
        print(f"🎯 Model được sử dụng: {client.model_names[client.current_model_index]}")
        print(f"🔑 API Key index: #{client.current_key_index + 1}")
        
        return True
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_token_counting(client):
    """Test đếm token"""
    print("\n" + "="*60)
    print("TEST 3: Token Counting")
    print("="*60)
    
    if not client:
        print("⏭️ Bỏ qua test (client không khả dụng)")
        return
    
    test_text = "Hello Gemini! This is a test prompt for counting tokens."
    
    try:
        print(f"📝 Text: '{test_text}'")
        print("⏳ Đang đếm token...")
        
        token_count = client.count_tokens(test_text)
        
        print(f"✅ Token count: {token_count}")
        return True
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def test_config():
    """Test cấu hình từ config.py"""
    print("\n" + "="*60)
    print("TEST 4: Config Verification")
    print("="*60)
    
    print(f"📋 Models trong config.py:")
    for i, model in enumerate(GEMINI_MODELS, 1):
        print(f"   {i}. {model}")
    
    print(f"\n✅ Tổng cộng {len(GEMINI_MODELS)} model(s) được cấu hình")

def main():
    """Chạy tất cả tests"""
    print("\n" + "🚀 "*20)
    print(" GEMINI MULTI-MODEL FALLBACK TEST SUITE")
    print("🚀 "*20)
    
    # Test 1: Khởi tạo
    client = test_gemini_basic()
    
    # Test 2: Text generation
    if client:
        test_text_generation(client)
    
    # Test 3: Token counting
    if client:
        test_token_counting(client)
    
    # Test 4: Config
    test_config()
    
    # Tổng kết
    print("\n" + "="*60)
    print("📊 KẾT THÚC TEST SUITE")
    print("="*60)
    print("\n💡 Lưu ý:")
    print("   - Nếu test thất bại, kiểm tra file .env")
    print("   - Đảm bảo có ít nhất 1 API key hợp lệ")
    print("   - Kiểm tra quota tại https://aistudio.google.com/")
    print("\n📖 Xem thêm: GEMINI_MODELS.md và QUICK_START_GEMINI.md")
    print()

if __name__ == "__main__":
    main()
