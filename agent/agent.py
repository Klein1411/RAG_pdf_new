"""
Main Agent Class - Orchestrates tools và conversation.

Agent có khả năng:
1. Hiểu user intent
2. Chọn tool phù hợp
3. Call tool và xử lý response
4. Duy trì conversation context
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config
from agent.config import (
    AGENT_NAME,
    AGENT_DESCRIPTION,
    AGENT_SYSTEM_PROMPT,
    ENABLE_RAG_TOOL,
    MAX_CONVERSATION_HISTORY
)

# Import tools
from agent.tools.rag_tool import RAGTool

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class Agent:
    """
    Main Agent class để orchestrate tools và conversation.
    
    Attributes:
        name: Tên agent
        description: Mô tả agent
        system_prompt: System prompt cho agent
        tools: Dict các tools đã register
        conversation_history: Lịch sử hội thoại
    """
    
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Khởi tạo Agent.
        
        Args:
            name: Tên agent (optional, dùng từ config nếu không có)
            description: Mô tả agent (optional)
        """
        self.name = name or AGENT_NAME
        self.description = description or AGENT_DESCRIPTION
        self.system_prompt = AGENT_SYSTEM_PROMPT
        
        # Tool registry
        self.tools: Dict[str, Any] = {}
        
        # Conversation history
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize tools
        self._initialize_tools()
        
        logger.info(f"🤖 Agent '{self.name}' đã khởi tạo với {len(self.tools)} tool(s)")
    
    def _initialize_tools(self):
        """Khởi tạo các tools."""
        logger.info("Đang khởi tạo tools...")
        
        # RAG Tool
        if ENABLE_RAG_TOOL:
            try:
                rag_tool = RAGTool()
                self.register_tool(rag_tool)
                logger.info("✅ RAG Tool đã được register")
            except Exception as e:
                logger.error(f"❌ Không thể khởi tạo RAG Tool: {e}")
        
        # Future: Thêm các tools khác
        # - Web search tool
        # - Calculator tool
        # - Code execution tool
    
    def register_tool(self, tool: Any):
        """
        Register một tool mới.
        
        Args:
            tool: Tool object (phải có get_info() method)
        """
        tool_info = tool.get_info()
        tool_name = tool_info['name']
        
        self.tools[tool_name] = {
            'instance': tool,
            'info': tool_info
        }
        
        logger.info(f"📌 Tool '{tool_name}' đã được register")
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tools có sẵn.
        
        Returns:
            List các tool info
        """
        return [tool_data['info'] for tool_data in self.tools.values()]
    
    def _should_use_rag(self, message: str) -> bool:
        """
        Quyết định có nên sử dụng RAG tool không.
        
        Simple heuristic: Sử dụng RAG nếu:
        - Câu hỏi yêu cầu thông tin cụ thể (có từ khóa như: gì, là, định nghĩa, giải thích, etc.)
        - Không phải greeting hoặc chitchat
        
        Args:
            message: User message
            
        Returns:
            True nếu nên dùng RAG, False nếu không
        """
        message_lower = message.lower()
        
        # Chitchat keywords
        chitchat_keywords = ['xin chào', 'hello', 'hi', 'chào', 'cảm ơn', 'thank']
        if any(keyword in message_lower for keyword in chitchat_keywords):
            return False
        
        # Question keywords (should use RAG)
        question_keywords = [
            'gì', 'là', 'nghĩa', 'định nghĩa', 'giải thích', 'what', 'is', 'define', 
            'explain', 'how', 'why', 'when', 'where', 'who', 'tại sao', 'như thế nào',
            'khi nào', 'ở đâu', 'ai', 'nào', 'which', 'tìm', 'search', 'find'
        ]
        
        if any(keyword in message_lower for keyword in question_keywords):
            return True
        
        # Default: use RAG (better to search than miss information)
        return True
    
    def _format_rag_response(self, rag_result: Dict[str, Any]) -> str:
        """
        Format RAG response để trả về user.
        
        Args:
            rag_result: Kết quả từ RAG tool
            
        Returns:
            Formatted response string
        """
        answer = rag_result.get('answer', '')
        sources = rag_result.get('sources', [])
        
        # Build response
        response = answer
        
        # Add sources if available
        if sources:
            response += "\n\n📚 **Nguồn tài liệu:**"
            for i, source in enumerate(sources, 1):
                source_name = source.get('source', 'Unknown')
                page = source.get('page', 'N/A')
                response += f"\n{i}. {source_name} (Trang {page})"
        
        return response
    
    def chat(self, message: str, use_rag: Optional[bool] = None) -> str:
        """
        Main chat method - process user message và return response.
        
        Args:
            message: User message
            use_rag: Force sử dụng RAG (None = auto decide)
            
        Returns:
            Agent response
        """
        logger.info(f"💬 User: {message}")
        
        # Add to conversation history
        self.conversation_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Decide tool usage
        should_use_rag = use_rag if use_rag is not None else self._should_use_rag(message)
        
        # Process message
        if should_use_rag and 'search_documents' in self.tools:
            logger.info("🔍 Sử dụng RAG tool để trả lời")
            
            try:
                rag_tool = self.tools['search_documents']['instance']
                rag_result = rag_tool.ask(message, top_k=15)  # Tăng top_k lên 15
                
                if rag_result['success']:
                    response = self._format_rag_response(rag_result)
                else:
                    response = "Xin lỗi, tôi gặp lỗi khi tìm kiếm thông tin. Vui lòng thử lại."
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi sử dụng RAG tool: {e}")
                response = "Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi của bạn."
        
        else:
            # Fallback: Chitchat response (no LLM, just simple rules)
            logger.info("💭 Xử lý như chitchat")
            response = self._chitchat_response(message)
        
        # Add to conversation history
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Trim history if too long
        if len(self.conversation_history) > MAX_CONVERSATION_HISTORY * 2:
            self.conversation_history = self.conversation_history[-(MAX_CONVERSATION_HISTORY * 2):]
        
        logger.info(f"🤖 Assistant: {response[:100]}...")
        return response
    
    def _chitchat_response(self, message: str) -> str:
        """
        Simple chitchat responses (không dùng LLM).
        
        Args:
            message: User message
            
        Returns:
            Chitchat response
        """
        message_lower = message.lower()
        
        # Greetings
        if any(word in message_lower for word in ['xin chào', 'hello', 'hi', 'chào']):
            return f"Xin chào! Tôi là {self.name}. Tôi có thể giúp bạn tìm kiếm thông tin từ tài liệu PDF. Bạn muốn hỏi gì?"
        
        # Thanks
        if any(word in message_lower for word in ['cảm ơn', 'thank', 'thanks', 'cám ơn']):
            return "Không có gì! Hãy hỏi tôi bất cứ điều gì bạn muốn biết từ tài liệu."
        
        # Help
        if any(word in message_lower for word in ['help', 'giúp', 'trợ giúp', 'hướng dẫn']):
            return f"""Tôi có thể giúp bạn:
1. 🔍 Tìm kiếm thông tin trong tài liệu PDF đã được index
2. ❓ Trả lời câu hỏi dựa trên nội dung tài liệu
3. 📊 Tóm tắt và phân tích thông tin

Chỉ cần hỏi tôi bất kỳ câu hỏi nào liên quan đến tài liệu!"""
        
        # Default
        return "Tôi có thể tìm kiếm thông tin trong tài liệu để trả lời câu hỏi của bạn. Bạn muốn hỏi gì?"
    
    def get_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lấy conversation history.
        
        Args:
            last_n: Số lượt cuối cùng (None = all)
            
        Returns:
            List conversation history
        """
        if last_n is None:
            return self.conversation_history
        return self.conversation_history[-last_n*2:] if last_n > 0 else []
    
    def clear_history(self):
        """Xóa conversation history."""
        self.conversation_history = []
        logger.info("🗑️ Đã xóa conversation history")
    
    def __repr__(self) -> str:
        return f"Agent(name='{self.name}', tools={list(self.tools.keys())})"


# --- SIMPLE CLI INTERFACE ---

def run_cli():
    """Chạy simple CLI để test agent."""
    print("=" * 60)
    print(f"🤖 {AGENT_NAME}")
    print(f"📝 {AGENT_DESCRIPTION}")
    print("=" * 60)
    print("\nĐang khởi tạo agent...")
    
    try:
        agent = Agent()
        print(f"\n✅ Agent đã sẵn sàng với {len(agent.tools)} tool(s)")
        print("\nTools available:")
        for tool_info in agent.get_available_tools():
            print(f"  - {tool_info['name']}: {tool_info['description']}")
        
        print("\n" + "=" * 60)
        print("💬 Bắt đầu chat (gõ 'exit' hoặc 'quit' để thoát)")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'thoát']:
                    print("\n👋 Tạm biệt!")
                    break
                
                # Special commands
                if user_input.lower() == 'history':
                    print("\n📜 Conversation History:")
                    for entry in agent.get_history(last_n=5):
                        role = "You" if entry['role'] == 'user' else "Agent"
                        print(f"\n{role}: {entry['content']}")
                    continue
                
                if user_input.lower() == 'clear':
                    agent.clear_history()
                    print("\n✅ Đã xóa history")
                    continue
                
                # Get response
                response = agent.chat(user_input)
                print(f"\n🤖 Agent: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Tạm biệt!")
                break
            except Exception as e:
                print(f"\n❌ Lỗi: {e}")
                logger.error(f"Lỗi trong chat loop: {e}", exc_info=True)
        
    except Exception as e:
        print(f"\n❌ Không thể khởi tạo agent: {e}")
        logger.error(f"Lỗi khởi tạo agent: {e}", exc_info=True)


if __name__ == "__main__":
    run_cli()
