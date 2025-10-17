"""
Unit tests cho GeminiClient class.
Chạy với: pytest tests/test_gemini_client.py -v
Hoặc: python tests/test_gemini_client.py (chạy trực tiếp)
"""

import sys
from pathlib import Path

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.gemini_client import GeminiClient


class TestGeminiClientInitialization:
    """Test khởi tạo GeminiClient"""
    
    @patch('src.gemini_client.dotenv.load_dotenv')  # Mock load_dotenv
    @patch.dict(os.environ, {
        "GEMINI_API_KEY_1": "test_key_1",
        "GEMINI_API_KEY_2": "test_key_2"
    }, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_init_with_multiple_keys(self, mock_model, mock_configure, mock_load_dotenv):
        """Test khởi tạo với nhiều API keys"""
        client = GeminiClient()
        
        assert len(client.api_keys) == 2
        assert client.api_keys[0] == "test_key_1"
        assert client.api_keys[1] == "test_key_2"
        assert client.current_key_index == 0
        mock_configure.assert_called_once_with(api_key="test_key_1")
        mock_load_dotenv.assert_called_once()
    
    @patch('src.gemini_client.dotenv.load_dotenv')
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_keys_raises_error(self, mock_load_dotenv):
        """Test khởi tạo khi không có API key sẽ raise ValueError"""
        with pytest.raises(ValueError, match="Không tìm thấy biến môi trường GEMINI_API_KEY"):
            GeminiClient()
    
    @patch('src.gemini_client.dotenv.load_dotenv')
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key_1"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_init_with_custom_model_names(self, mock_model, mock_configure, mock_load_dotenv):
        """Test khởi tạo với model names tùy chỉnh"""
        client = GeminiClient(model_names=["gemini-pro"])
        
        assert client.model_names == ["gemini-pro"]
        assert len(client.api_keys) == 1


class TestKeyRotation:
    """Test chức năng xoay vòng API keys"""
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY_1": "key_1",
        "GEMINI_API_KEY_2": "key_2",
        "GEMINI_API_KEY_3": "key_3"
    }, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_switch_to_next_key(self, mock_model, mock_configure):
        """Test chuyển sang key tiếp theo"""
        client = GeminiClient()
        mock_configure.reset_mock()
        
        # Chuyển sang key thứ 2
        result = client._switch_to_next_key()
        
        assert result is True
        assert client.current_key_index == 1
        mock_configure.assert_called_once_with(api_key="key_2")
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "key_1"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_switch_to_next_key_when_no_more_keys(self, mock_model, mock_configure):
        """Test chuyển key khi đã hết key"""
        client = GeminiClient()
        client.current_key_index = 0
        
        # Thử chuyển sang key thứ 2 (không tồn tại)
        result = client._switch_to_next_key()
        
        assert result is False
        assert client.current_key_index == 1  # Index đã tăng nhưng không có key


class TestGenerateContent:
    """Test hàm generate_content"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_success(self, mock_model_class, mock_configure):
        """Test generate content thành công"""
        # Setup mock
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated text response"
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        result = client.generate_content("Test prompt")
        
        assert result == "Generated text response"
        mock_model_instance.generate_content.assert_called_once_with("Test prompt")
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_with_full_response(self, mock_model_class, mock_configure):
        """Test generate content trả về full response"""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        result = client.generate_content("Test prompt", return_full_response=True)
        
        assert result == mock_response
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY_1": "key_1",
        "GEMINI_API_KEY_2": "key_2"
    }, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_auto_retry_on_quota_error(self, mock_model_class, mock_configure):
        """Test tự động retry khi gặp lỗi quota"""
        mock_model_instance = MagicMock()
        
        # Key đầu tiên bị lỗi quota
        quota_error = Exception("429 quota exceeded")
        # Key thứ 2 thành công
        mock_response = MagicMock()
        mock_response.text = "Success with second key"
        
        mock_model_instance.generate_content.side_effect = [quota_error, mock_response]
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        result = client.generate_content("Test prompt")
        
        assert result == "Success with second key"
        assert client.current_key_index == 1
        assert mock_model_instance.generate_content.call_count == 2
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "invalid_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_raises_on_all_keys_fail(self, mock_model_class, mock_configure):
        """Test raise exception khi tất cả key đều fail"""
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("API key not valid")
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        
        with pytest.raises(ConnectionError, match="Tất cả các API key và model"):
            client.generate_content("Test prompt")


class TestCountTokens:
    """Test hàm count_tokens"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_count_tokens_success(self, mock_model_class, mock_configure):
        """Test đếm token thành công"""
        mock_model_instance = MagicMock()
        mock_token_result = MagicMock()
        mock_token_result.total_tokens = 42
        mock_model_instance.count_tokens.return_value = mock_token_result
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        result = client.count_tokens("Test prompt")
        
        assert result == 42
        mock_model_instance.count_tokens.assert_called_once_with("Test prompt")
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_count_tokens_with_list_prompt(self, mock_model_class, mock_configure):
        """Test đếm token với list prompt (vision)"""
        mock_model_instance = MagicMock()
        mock_token_result = MagicMock()
        mock_token_result.total_tokens = 100
        mock_model_instance.count_tokens.return_value = mock_token_result
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        prompt_list = ["Text prompt", "image_data"]
        result = client.count_tokens(prompt_list)
        
        assert result == 100


class TestEdgeCases:
    """Test các trường hợp đặc biệt"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_with_empty_string(self, mock_model_class, mock_configure):
        """Test với prompt rỗng"""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        result = client.generate_content("")
        
        assert result == ""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY_1": "test_key"}, clear=True)
    @patch('src.gemini_client.genai.configure')
    @patch('src.gemini_client.genai.GenerativeModel')
    def test_generate_content_with_very_long_prompt(self, mock_model_class, mock_configure):
        """Test với prompt rất dài"""
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_model_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model_instance
        
        client = GeminiClient()
        long_prompt = "A" * 100000
        result = client.generate_content(long_prompt)
        
        assert result == "Response"
        mock_model_instance.generate_content.assert_called_once_with(long_prompt)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

