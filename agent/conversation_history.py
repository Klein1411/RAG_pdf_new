"""
Conversation History Manager - Quản lý lịch sử hội thoại.

Tách logic lưu trữ lịch sử hội thoại ra khỏi Agent class.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json


class ConversationHistory:
    """
    Quản lý lịch sử hội thoại.
    
    Features:
    - Add messages (user/assistant)
    - Auto-truncate when exceeding limit
    - Get recent history
    - Clear history
    - Export/Import (optional)
    """
    
    def __init__(self, max_messages: int = 20):
        """
        Initialize conversation history.
        
        Args:
            max_messages: Maximum number of messages to keep (x2 for user+assistant pairs)
        """
        self.max_messages = max_messages
        self.history: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to history.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
        """
        self.history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Auto-truncate if exceeding limit
        if len(self.history) > self.max_messages * 2:
            self.history = self.history[-(self.max_messages * 2):]
    
    def add_user_message(self, content: str) -> None:
        """Add user message."""
        self.add_message('user', content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add assistant message."""
        self.add_message('assistant', content)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all history."""
        return self.history.copy()
    
    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent n message pairs (user + assistant).
        
        Args:
            n: Number of message pairs to get
            
        Returns:
            List of recent messages (last n*2 messages)
        """
        if n <= 0:
            return []
        return self.history[-(n * 2):] if len(self.history) > 0 else []
    
    def clear(self) -> None:
        """Clear all history."""
        self.history = []
    
    def count(self) -> int:
        """Get number of messages."""
        return len(self.history)
    
    def is_empty(self) -> bool:
        """Check if history is empty."""
        return len(self.history) == 0
    
    def export_to_file(self, filepath: Path) -> None:
        """
        Export history to JSON file.
        
        Args:
            filepath: Path to output file
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def import_from_file(self, filepath: Path) -> None:
        """
        Import history from JSON file.
        
        Args:
            filepath: Path to input file
        """
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get conversation summary.
        
        Returns:
            Dict with stats: total_messages, user_messages, assistant_messages
        """
        user_msgs = sum(1 for msg in self.history if msg['role'] == 'user')
        assistant_msgs = sum(1 for msg in self.history if msg['role'] == 'assistant')
        
        return {
            'total_messages': len(self.history),
            'user_messages': user_msgs,
            'assistant_messages': assistant_msgs,
            'max_messages': self.max_messages * 2
        }
    
    def __len__(self) -> int:
        """Support len() operator."""
        return len(self.history)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"ConversationHistory(messages={len(self.history)}, max={self.max_messages*2})"


# Singleton pattern (optional)
_conversation_history = None

def get_conversation_history(max_messages: int = 20) -> ConversationHistory:
    """
    Get or create ConversationHistory instance (singleton).
    
    Args:
        max_messages: Maximum number of message pairs to keep
        
    Returns:
        ConversationHistory instance
    """
    global _conversation_history
    if _conversation_history is None:
        _conversation_history = ConversationHistory(max_messages)
    return _conversation_history


def reset_conversation_history():
    """Reset singleton (for testing)."""
    global _conversation_history
    _conversation_history = None


if __name__ == "__main__":
    # Test ConversationHistory
    history = ConversationHistory(max_messages=3)
    
    print("=== Test ConversationHistory ===")
    
    # Add messages
    history.add_user_message("Hello")
    history.add_assistant_message("Hi! How can I help?")
    history.add_user_message("What is Python?")
    history.add_assistant_message("Python is a programming language...")
    
    print(f"\n1. History: {history}")
    print(f"   Messages: {history.count()}")
    
    # Get recent
    recent = history.get_recent(1)
    print(f"\n2. Recent 1 pair: {len(recent)} messages")
    
    # Auto-truncate test
    for i in range(5):
        history.add_user_message(f"Question {i}")
        history.add_assistant_message(f"Answer {i}")
    
    print(f"\n3. After adding 5 more pairs:")
    print(f"   Total messages: {history.count()} (should be 6 max)")
    
    # Summary
    summary = history.get_summary()
    print(f"\n4. Summary: {summary}")
    
    print("\n✅ Test completed")
