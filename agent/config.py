"""
Cấu hình cho Agent system.

File này chứa các settings cho agent, có thể override từ root config.
"""

import sys
from pathlib import Path

# Thêm thư mục gốc project vào sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import từ root config
from src.config import (
    GEMINI_MODELS,
    GEMINI_INPUT_TOKEN_LIMIT,
    EMBEDDING_MODEL_NAME,
    COLLECTION_NAME,
    OUTPUT_DIR
)

# --- AGENT SPECIFIC SETTINGS ---

# Agent persona và behavior
AGENT_NAME = "RAG Assistant"
AGENT_DESCRIPTION = "AI Assistant với khả năng truy vấn thông tin từ tài liệu PDF"

# Agent system prompt
AGENT_SYSTEM_PROMPT = """Bạn là một AI Assistant thông minh có khả năng:
1. Trả lời câu hỏi dựa trên tài liệu đã được index
2. Tìm kiếm thông tin chính xác trong database
3. Tổng hợp và phân tích thông tin
4. Trả lời bằng tiếng Việt hoặc tiếng Anh tùy ngôn ngữ câu hỏi

Khi trả lời:
- Luôn dựa vào context được cung cấp từ tài liệu
- Nếu không tìm thấy thông tin, hãy nói rõ
- Trích dẫn nguồn (số trang) khi có thể
- Trả lời ngắn gọn, súc tích nhưng đầy đủ
"""

# Tool settings
ENABLE_RAG_TOOL = True  # Bật/tắt RAG tool
ENABLE_SEARCH_TOOL = False  # Bật/tắt search tool (future)
ENABLE_CALCULATOR_TOOL = False  # Bật/tắt calculator (future)

# RAG tool settings
RAG_TOOL_NAME = "search_documents"
RAG_TOOL_DESCRIPTION = "Tìm kiếm thông tin trong tài liệu PDF đã được index. Sử dụng khi cần tra cứu thông tin cụ thể."
RAG_MAX_RESULTS = 15  # Số kết quả tối đa từ RAG (tăng lên 15)
RAG_SIMILARITY_THRESHOLD = 0.15  # Ngưỡng similarity (0-1), giảm xuống cho L2 distance

# Conversation settings
MAX_CONVERSATION_HISTORY = 10  # Số lượt hội thoại giữ lại
CONVERSATION_SAVE_PATH = "data/conversations"  # Nơi lưu lịch sử chat

# Agent model settings (có thể khác với RAG model)
AGENT_MODEL = GEMINI_MODELS[0]  # Sử dụng model đầu tiên từ config
AGENT_TEMPERATURE = 0.7  # Creativity (0-1)
AGENT_MAX_TOKENS = 2048  # Max tokens cho response

# Logging
AGENT_LOG_LEVEL = "INFO"
AGENT_LOG_FILE = "logs/agent.log"

# --- FUTURE TOOLS CONFIG ---

# Calculator tool
CALCULATOR_PRECISION = 10

# Web search tool
WEB_SEARCH_MAX_RESULTS = 5
WEB_SEARCH_TIMEOUT = 10  # seconds
