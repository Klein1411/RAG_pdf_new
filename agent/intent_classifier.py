# coding: utf-8
"""
Intent Classifier - Phân loại câu hỏi có liên quan đến PDF hay không
Giúp Agent quyết định có cần gọi RAG tool hay chỉ chat bình thường
"""

import sys
from pathlib import Path
import re
from typing import Dict, List

# Thêm project root vào path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.logging_config import get_logger

logger = get_logger(__name__)


class IntentClassifier:
    """
    Phân loại ý định của user:
    - pdf_related: Câu hỏi liên quan đến nội dung PDF (cần RAG)
    - general_chat: Chat bình thường (không cần RAG)
    """
    
    def __init__(self):
        # Từ khóa cho thấy câu hỏi liên quan đến tài liệu
        self.pdf_keywords = [
            # Tiếng Việt
            'tài liệu', 'pdf', 'file', 'văn bản', 'nội dung',
            'trang', 'phần', 'chương', 'mục', 'đoạn',
            'theo', 'trong', 'ở', 'từ', 'đề cập', 'nói về',
            'giải thích', 'định nghĩa', 'khái niệm', 'là gì',
            'như thế nào', 'ra sao', 'thế nào',
            'tìm', 'tìm kiếm', 'tra cứu', 'xem', 'đọc',
            
            # Tiếng Anh
            'document', 'paper', 'article', 'section',
            'according', 'mention', 'describe', 'explain',
            'what is', 'how to', 'define', 'definition',
            'find', 'search', 'look for', 'show me',
        ]
        
        # Từ khóa cho thấy là chat bình thường
        self.general_chat_keywords = [
            # Chào hỏi
            'xin chào', 'chào', 'hello', 'hi', 'hey',
            'chào bạn', 'chào buổi', 'good morning', 'good afternoon',
            
            # Tạm biệt
            'tạm biệt', 'bye', 'goodbye', 'see you', 'hẹn gặp lại',
            
            # Cảm ơn
            'cảm ơn', 'thanks', 'thank you', 'cảm ơn bạn',
            
            # Hỏi về agent
            'bạn là ai', 'bạn tên gì', 'giới thiệu', 'bạn có thể',
            'who are you', 'what is your name', 'introduce yourself',
            
            # Trò chuyện thông thường
            'thời tiết', 'hôm nay', 'bây giờ',
            'weather', 'today', 'now', 'time',
            
            # Ý kiến cá nhân
            'bạn nghĩ sao', 'ý kiến', 'quan điểm',
            'what do you think', 'opinion', 'your view',
        ]
        
        # Mẫu câu hỏi liên quan đến tài liệu
        self.document_question_patterns = [
            r'(.*)(là gì|nghĩa là gì|có nghĩa|định nghĩa)(.*)',
            r'(.*)(giải thích|mô tả|trình bày)(.*)',
            r'(.*)(phương pháp|cách thức|quy trình)(.*)',
            r'(.*)(ưu điểm|nhược điểm|lợi ích|hạn chế)(.*)',
            r'(.*)(so sánh|khác nhau|giống nhau)(.*)',
            r'(what is|what are|how does|how to)(.*)',
            r'(explain|describe|define|compare)(.*)',
            r'(.*)(advantage|disadvantage|benefit|limitation)(.*)',
        ]
        
        # Mẫu câu chat bình thường
        self.general_chat_patterns = [
            r'^(xin chào|chào|hello|hi|hey)',
            r'^(tạm biệt|bye|goodbye)',
            r'^(cảm ơn|thanks|thank you)',
            r'(bạn là ai|bạn tên gì|who are you|what.*your name)',
            r'(thời tiết|weather)(.*)(thế nào|hôm nay|today)',
        ]
    
    def classify(self, message: str) -> Dict[str, any]:
        """
        Phân loại câu hỏi
        
        Returns:
            {
                'intent': 'pdf_related' hoặc 'general_chat',
                'confidence': float (0-1),
                'reason': str (giải thích)
            }
        """
        message_lower = message.lower().strip()
        
        # Kiểm tra các mẫu chat bình thường trước
        for pattern in self.general_chat_patterns:
            if re.match(pattern, message_lower):
                return {
                    'intent': 'general_chat',
                    'confidence': 0.95,
                    'reason': 'Khớp với mẫu chat bình thường'
                }
        
        # Kiểm tra các mẫu câu hỏi về tài liệu
        for pattern in self.document_question_patterns:
            if re.match(pattern, message_lower):
                return {
                    'intent': 'pdf_related',
                    'confidence': 0.85,
                    'reason': 'Khớp với mẫu câu hỏi về tài liệu'
                }
        
        # Đếm từ khóa liên quan đến PDF
        pdf_keyword_count = sum(
            1 for keyword in self.pdf_keywords 
            if keyword.lower() in message_lower
        )
        
        # Đếm từ khóa chat bình thường
        general_keyword_count = sum(
            1 for keyword in self.general_chat_keywords 
            if keyword.lower() in message_lower
        )
        
        # Quyết định dựa trên số lượng từ khóa
        if pdf_keyword_count > general_keyword_count:
            confidence = min(0.5 + (pdf_keyword_count * 0.15), 0.9)
            return {
                'intent': 'pdf_related',
                'confidence': confidence,
                'reason': f'Tìm thấy {pdf_keyword_count} từ khóa liên quan đến tài liệu'
            }
        elif general_keyword_count > pdf_keyword_count:
            confidence = min(0.5 + (general_keyword_count * 0.15), 0.9)
            return {
                'intent': 'general_chat',
                'confidence': confidence,
                'reason': f'Tìm thấy {general_keyword_count} từ khóa chat bình thường'
            }
        else:
            # Nếu không rõ, kiểm tra độ dài câu
            # Câu ngắn (< 5 từ) thường là chat bình thường
            word_count = len(message.split())
            if word_count < 5:
                return {
                    'intent': 'general_chat',
                    'confidence': 0.6,
                    'reason': 'Câu ngắn, có thể là chat bình thường'
                }
            else:
                # Câu dài hơn, có thể là câu hỏi về tài liệu
                return {
                    'intent': 'pdf_related',
                    'confidence': 0.55,
                    'reason': 'Câu hỏi dài, giả định liên quan đến tài liệu'
                }
    
    def is_pdf_related(self, message: str, threshold: float = 0.6) -> bool:
        """
        Kiểm tra nhanh xem câu hỏi có liên quan đến PDF không
        
        Args:
            message: Câu hỏi từ user
            threshold: Ngưỡng confidence (mặc định 0.6)
        
        Returns:
            True nếu liên quan đến PDF, False nếu là chat bình thường
        """
        result = self.classify(message)
        return result['intent'] == 'pdf_related' and result['confidence'] >= threshold


# Singleton instance
_classifier_instance = None

def get_intent_classifier() -> IntentClassifier:
    """Lấy instance của IntentClassifier (singleton pattern)"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
        logger.info("IntentClassifier initialized")
    return _classifier_instance


# Test function
def test_classifier():
    """Test các trường hợp phân loại"""
    classifier = IntentClassifier()
    
    test_cases = [
        # PDF related
        "ROUGE là gì?",
        "Giải thích về BLEU metric",
        "So sánh ROUGE và BLEU",
        "Tài liệu có đề cập gì về NLP không?",
        "Phương pháp đánh giá summarization là gì?",
        
        # General chat
        "Xin chào",
        "Bạn tên gì?",
        "Cảm ơn bạn",
        "Thời tiết hôm nay thế nào?",
        "Bạn có thể làm gì?",
        
        # Ambiguous
        "Nghiên cứu này thế nào?",
        "Phân tích dữ liệu",
    ]
    
    print("\n" + "="*70)
    print("TEST INTENT CLASSIFIER")
    print("="*70)
    
    for message in test_cases:
        result = classifier.classify(message)
        print(f"\nCâu hỏi: {message}")
        print(f"Intent: {result['intent']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Lý do: {result['reason']}")


if __name__ == "__main__":
    test_classifier()
