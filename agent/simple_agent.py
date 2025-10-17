"""
Simple Agent - Phiên bản đơn giản của Agent với RAG capability

Agent này có thể:
1. Nhận câu hỏi từ user
2. Sử dụng RAG tool để tìm kiếm thông tin
3. Trả lời dựa trên thông tin tìm được
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Thêm thư mục gốc project vào sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.config import (
    AGENT_NAME,
    AGENT_DESCRIPTION,
    AGENT_SYSTEM_PROMPT,
    MAX_CONVERSATION_HISTORY
)
from agent.tools.rag_tool import create_rag_tool
from src.logging_config import get_logger

logger = get_logger(__name__)


class SimpleAgent:
    """
    Agent đơn giản với khả năng sử dụng RAG tool.
    
    Attributes:
        name: Tên của agent
        description: Mô tả agent
        rag_tool: RAG tool instance
        conversation_history: Lịch sử hội thoại
    """
    
    def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
        """
        Khởi tạo Agent.
        
        Args:
            name: Tên agent (mặc định từ config)
            description: Mô tả agent (mặc định từ config)
        """
        self.name = name or AGENT_NAME
        self.description = description or AGENT_DESCRIPTION
        self.system_prompt = AGENT_SYSTEM_PROMPT
        
        logger.info(f"🤖 Khởi tạo Agent: {self.name}")
        logger.info(f"   Mô tả: {self.description}")
        
        # Khởi tạo RAG tool
        self.rag_tool = create_rag_tool()
        
        # Lịch sử hội thoại
        self.conversation_history: List[Dict[str, Any]] = []
        
        logger.info("✅ Agent đã sẵn sàng")
    
    def _add_to_history(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Thêm message vào lịch sử hội thoại.
        
        Args:
            role: 'user' hoặc 'assistant'
            content: Nội dung message
            metadata: Metadata bổ sung
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        
        # Giới hạn số lượng history
        if len(self.conversation_history) > MAX_CONVERSATION_HISTORY * 2:
            # Giữ lại các message gần đây nhất
            self.conversation_history = self.conversation_history[-(MAX_CONVERSATION_HISTORY * 2):]
    
    def _should_use_rag(self, question: str) -> bool:
        """
        Quyết định có nên sử dụng RAG tool hay không.
        
        Logic đơn giản: Luôn dùng RAG cho mọi câu hỏi.
        Sau này có thể improve bằng intent classification.
        
        Args:
            question: Câu hỏi của user
            
        Returns:
            True nếu nên dùng RAG
        """
        # Simple version: Luôn dùng RAG
        return True
    
    def ask(self, question: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Hỏi Agent một câu hỏi.
        
        Args:
            question: Câu hỏi
            verbose: In thêm thông tin chi tiết
            
        Returns:
            Dict chứa answer và metadata
        """
        logger.info(f"❓ User question: '{question}'")
        
        # Thêm question vào history
        self._add_to_history("user", question)
        
        try:
            # Quyết định có dùng RAG không
            use_rag = self._should_use_rag(question)
            
            if use_rag:
                if verbose:
                    print("🔍 Đang tìm kiếm thông tin trong tài liệu...")
                
                # Sử dụng RAG tool
                rag_result = self.rag_tool.ask(question, top_k=5, return_context=verbose)
                
                if rag_result["success"]:
                    answer = rag_result["answer"]
                    sources = rag_result["sources"]
                    
                    # Thêm vào history
                    self._add_to_history(
                        "assistant",
                        answer,
                        metadata={
                            "method": "rag",
                            "sources": sources,
                            "source_count": len(sources)
                        }
                    )
                    
                    result = {
                        "success": True,
                        "answer": answer,
                        "sources": sources,
                        "method": "rag"
                    }
                    
                    if verbose and "context" in rag_result:
                        result["context"] = rag_result["context"]
                    
                    return result
                else:
                    # RAG failed, trả về message lỗi
                    answer = rag_result["answer"]
                    self._add_to_history("assistant", answer, metadata={"method": "rag_failed"})
                    
                    return {
                        "success": False,
                        "answer": answer,
                        "sources": [],
                        "method": "rag_failed"
                    }
            else:
                # Không dùng RAG, trả lời trực tiếp (future: dùng LLM thuần)
                answer = "Xin lỗi, tôi chỉ có thể trả lời câu hỏi liên quan đến tài liệu đã được index."
                self._add_to_history("assistant", answer, metadata={"method": "direct"})
                
                return {
                    "success": False,
                    "answer": answer,
                    "sources": [],
                    "method": "direct"
                }
                
        except Exception as e:
            logger.error(f"Lỗi khi xử lý câu hỏi: {e}")
            error_message = f"Xin lỗi, đã có lỗi xảy ra: {str(e)}"
            
            self._add_to_history("assistant", error_message, metadata={"method": "error"})
            
            return {
                "success": False,
                "answer": error_message,
                "sources": [],
                "method": "error"
            }
    
    def get_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử hội thoại.
        
        Args:
            last_n: Số message gần nhất (None = tất cả)
            
        Returns:
            List các messages
        """
        if last_n is None:
            return self.conversation_history.copy()
        else:
            return self.conversation_history[-last_n:]
    
    def clear_history(self):
        """Xóa lịch sử hội thoại."""
        self.conversation_history = []
        logger.info("Đã xóa lịch sử hội thoại")
    
    def get_info(self) -> Dict[str, Any]:
        """Lấy thông tin về Agent."""
        return {
            "name": self.name,
            "description": self.description,
            "tools": ["rag_tool"],
            "conversation_length": len(self.conversation_history),
            "rag_tool_info": self.rag_tool.get_info()
        }


# --- INTERACTIVE MODE ---

def run_interactive():
    """Chạy agent ở chế độ interactive."""
    print("="*60)
    print(f"🤖 {AGENT_NAME}")
    print(f"   {AGENT_DESCRIPTION}")
    print("="*60)
    print("\nCommands:")
    print("  /help     - Hiển thị help")
    print("  /history  - Xem lịch sử")
    print("  /clear    - Xóa lịch sử")
    print("  /info     - Thông tin agent")
    print("  /quit     - Thoát")
    print("\n" + "="*60 + "\n")
    
    # Khởi tạo agent
    print("Đang khởi tạo agent...")
    agent = SimpleAgent()
    print("✅ Agent đã sẵn sàng!\n")
    
    while True:
        try:
            # Nhận input từ user
            question = input("💬 You: ").strip()
            
            if not question:
                continue
            
            # Xử lý commands
            if question.startswith('/'):
                command = question.lower()
                
                if command == '/quit' or command == '/exit':
                    print("\n👋 Tạm biệt!")
                    break
                
                elif command == '/help':
                    print("\n📖 Help:")
                    print("  - Đặt câu hỏi bất kỳ liên quan đến tài liệu")
                    print("  - Agent sẽ tìm kiếm và trả lời dựa trên thông tin trong PDF")
                    print("  - Sử dụng /commands để xem các lệnh khác\n")
                
                elif command == '/history':
                    history = agent.get_history()
                    print(f"\n📜 Lịch sử ({len(history)} messages):")
                    for msg in history[-10:]:  # Show last 10
                        role_emoji = "💬" if msg["role"] == "user" else "🤖"
                        print(f"  {role_emoji} [{msg['timestamp']}] {msg['content'][:80]}...")
                    print()
                
                elif command == '/clear':
                    agent.clear_history()
                    print("\n✅ Đã xóa lịch sử hội thoại\n")
                
                elif command == '/info':
                    info = agent.get_info()
                    print(f"\n🤖 Agent Info:")
                    print(f"  Name: {info['name']}")
                    print(f"  Description: {info['description']}")
                    print(f"  Tools: {', '.join(info['tools'])}")
                    print(f"  Conversation length: {info['conversation_length']}")
                    print(f"  RAG collection: {info['rag_tool_info']['collection']}")
                    print()
                
                else:
                    print(f"\n❌ Unknown command: {command}")
                    print("   Type /help for available commands\n")
                
                continue
            
            # Hỏi agent
            print("\n🤖 Assistant: ", end="", flush=True)
            result = agent.ask(question, verbose=False)
            print(result["answer"])
            
            # Hiển thị sources nếu có
            if result["sources"]:
                print(f"\n📚 Nguồn: {len(result['sources'])} tài liệu")
                for i, source in enumerate(result["sources"][:3], 1):
                    print(f"   {i}. Trang {source['page']} (score: {source['score']:.2f})")
            
            print()  # Empty line
            
        except KeyboardInterrupt:
            print("\n\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"\n❌ Lỗi: {e}\n")


# --- MAIN ---
if __name__ == "__main__":
    run_interactive()
