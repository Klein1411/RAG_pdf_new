# coding: utf-8
"""
Topic Tool - Tool gợi ý chủ đề từ documents
Trích xuất topics và tạo câu hỏi mẫu
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.topic_suggester import TopicSuggester, get_topic_suggester
from src.logging_config import get_logger

logger = get_logger(__name__)


class TopicTool:
    """
    Tool gợi ý topics và câu hỏi từ PDF collections
    Wrapper cho TopicSuggester để sử dụng trong Agent tool system
    """
    
    def __init__(self, topic_suggester: Optional[TopicSuggester] = None):
        """
        Args:
            topic_suggester: TopicSuggester instance (optional, sẽ dùng singleton nếu không có)
        """
        self.name = "topic_tool"
        self.description = "Extract topics and suggest questions from PDF documents"
        
        # Sử dụng suggester được truyền vào hoặc lấy singleton
        self.suggester = topic_suggester or get_topic_suggester()
    
    def build_topics(self, collection_names: List[str], sample_size: int = 30) -> bool:
        """
        Build topics từ danh sách collections
        
        Args:
            collection_names: Danh sách collection names
            sample_size: Số documents để sample mỗi collection
            
        Returns:
            True nếu thành công
        """
        logger.info(f"Building topics from {len(collection_names)} collections")
        
        try:
            self.suggester.build_topics_from_collections(collection_names, sample_size)
            logger.info("Topics built successfully")
            return True
        except Exception as e:
            logger.error(f"Error building topics: {e}")
            return False
    
    def get_suggestions(self, max_suggestions: int = 5, collection_names: Optional[List[str]] = None) -> List[str]:
        """
        Lấy gợi ý câu hỏi
        
        Args:
            max_suggestions: Số câu hỏi tối đa
            collection_names: Danh sách collections (None = tất cả)
            
        Returns:
            List of suggested questions
        """
        return self.suggester.get_suggestions(collection_names, max_suggestions)
    
    def get_topic_summary(self) -> str:
        """
        Lấy tóm tắt các topics
        
        Returns:
            Formatted topic summary
        """
        return self.suggester.get_topic_summary()
    
    def clear_cache(self):
        """Xóa cache topics"""
        self.suggester.clear_cache()
        logger.info("Topic cache cleared")
    
    def has_topics(self) -> bool:
        """
        Kiểm tra có topics không
        
        Returns:
            True nếu có topics trong cache
        """
        return bool(self.suggester.topics_cache)
    
    def format_suggestions(self, suggestions: List[str]) -> str:
        """
        Format suggestions thành string đẹp
        
        Args:
            suggestions: List of questions
            
        Returns:
            Formatted string
        """
        if not suggestions:
            return "Không có gợi ý câu hỏi nào."
        
        formatted = "📚 **Các câu hỏi gợi ý:**\n\n"
        for i, question in enumerate(suggestions, 1):
            formatted += f"{i}. {question}\n"
        
        return formatted.strip()


# Singleton instance (optional)
_topic_tool_instance = None

def get_topic_tool(topic_suggester: Optional[TopicSuggester] = None) -> TopicTool:
    """
    Lấy instance của TopicTool (singleton pattern)
    
    Args:
        topic_suggester: TopicSuggester instance (optional)
    """
    global _topic_tool_instance
    if _topic_tool_instance is None:
        _topic_tool_instance = TopicTool(topic_suggester=topic_suggester)
        logger.info("TopicTool instance created")
    return _topic_tool_instance


# Test function
def test_topic_tool():
    """Test TopicTool"""
    from pymilvus import connections, utility
    
    # Connect to Milvus
    connections.connect(host="localhost", port="19530")
    
    # Get available collections
    collections = utility.list_collections()
    print("\n" + "="*70)
    print("TEST TOPIC TOOL")
    print("="*70)
    print(f"\nAvailable collections: {collections}")
    
    if not collections:
        print("\nNo collections found. Please add some PDFs first.")
        return
    
    # Test tool
    tool = TopicTool()
    
    print(f"\nBuilding topics from collections...")
    success = tool.build_topics(collections[:3], sample_size=20)  # Test with first 3
    
    if success:
        print("✅ Topics built successfully\n")
        
        # Get summary
        summary = tool.get_topic_summary()
        print(summary)
        
        # Get suggestions
        suggestions = tool.get_suggestions(max_suggestions=3)
        print(f"\n{tool.format_suggestions(suggestions)}")
        
        # Check cache
        print(f"\nHas topics: {tool.has_topics()}")
        
        # Clear cache
        tool.clear_cache()
        print(f"After clear: {tool.has_topics()}")
    else:
        print("❌ Failed to build topics")


if __name__ == "__main__":
    test_topic_tool()
