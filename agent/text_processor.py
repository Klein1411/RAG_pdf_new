"""
Text Processing Utilities cho Agent.

Bao gồm:
- Spell checking (Vietnamese + English)
- Intent detection
- Text correction
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Add project root
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from spellchecker import SpellChecker
from src.logging_config import get_logger

logger = get_logger(__name__)


class TextProcessor:
    """
    Text processor cho spell checking và intent detection.
    """
    
    def __init__(self):
        """Khởi tạo text processor."""
        # Spell checkers
        self.spell_en = SpellChecker(language='en')
        # Note: pyspellchecker không có Vietnamese, sẽ dùng custom dict hoặc skip
        
        # Common Vietnamese words (để không flag là lỗi)
        self.vi_common_words = {
            'là', 'gì', 'của', 'trong', 'với', 'được', 'có', 'và', 'này', 'đó',
            'các', 'để', 'từ', 'một', 'không', 'như', 'về', 'đến', 'theo', 'cho',
            'khi', 'nào', 'sao', 'bao', 'nhiêu', 'thế', 'vậy', 'hơn', 'nhất',
            'chỉ', 'số', 'metric', 'rouge', 'bleu', 'tóm', 'tắt', 'chatbot'
        }
        
        logger.info("✅ TextProcessor đã khởi tạo")
    
    def check_spelling(self, text: str) -> Dict[str, any]:
        """
        Kiểm tra chính tả trong text.
        
        Args:
            text: Text cần kiểm tra
            
        Returns:
            Dict với keys: has_errors, misspelled, corrections
        """
        # Tách từ
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter Vietnamese common words
        en_words = [w for w in words if w not in self.vi_common_words and not w.isdigit()]
        
        # Check spelling
        misspelled = self.spell_en.unknown(en_words)
        
        # Get corrections
        corrections = {}
        for word in misspelled:
            correction = self.spell_en.correction(word)
            # Chỉ thêm vào nếu correction hợp lệ và khác từ gốc
            if correction and correction != word and isinstance(correction, str):
                corrections[word] = correction
        
        result = {
            'has_errors': len(corrections) > 0,
            'misspelled': list(misspelled),
            'corrections': corrections
        }
        
        if result['has_errors']:
            logger.info(f"🔍 Phát hiện lỗi chính tả: {corrections}")
        
        return result
    
    def correct_text(self, text: str, auto_correct: bool = False) -> str:
        """
        Sửa lỗi chính tả trong text.
        
        Args:
            text: Text cần sửa
            auto_correct: Tự động sửa không hỏi
            
        Returns:
            Corrected text
        """
        spelling_check = self.check_spelling(text)
        
        if not spelling_check['has_errors']:
            return text
        
        corrected = text
        for wrong, correct in spelling_check['corrections'].items():
            # Skip nếu correction là None hoặc empty
            if not correct or correct == wrong:
                continue
                
            if auto_correct:
                # Replace (case-insensitive)
                try:
                    corrected = re.sub(
                        r'\b' + re.escape(wrong) + r'\b',
                        correct,
                        corrected,
                        flags=re.IGNORECASE
                    )
                except Exception as e:
                    logger.warning(f"Cannot replace '{wrong}' with '{correct}': {e}")
                    continue
        
        return corrected
    
    def detect_intent(self, text: str) -> Dict[str, any]:
        """
        Phát hiện ý định của user từ text.
        
        Intent types:
        - greeting: Chào hỏi
        - farewell: Tạm biệt
        - question: Câu hỏi (cần RAG)
        - thanks: Cảm ơn
        - help: Yêu cầu trợ giúp
        - command: Command đặc biệt (export, check, etc.)
        
        Args:
            text: User message
            
        Returns:
            Dict với keys: intent, confidence, keywords
        """
        text_lower = text.lower()
        
        # Intent patterns
        intents = {
            'greeting': {
                'keywords': ['xin chào', 'chào', 'hello', 'hi', 'hey'],
                'confidence': 0.0
            },
            'farewell': {
                'keywords': ['tạm biệt', 'bye', 'goodbye', 'thoát', 'exit', 'quit'],
                'confidence': 0.0
            },
            'thanks': {
                'keywords': ['cảm ơn', 'cám ơn', 'thank', 'thanks'],
                'confidence': 0.0
            },
            'help': {
                'keywords': ['giúp', 'help', 'hướng dẫn', 'trợ giúp', 'làm gì', 'hỗ trợ'],
                'confidence': 0.0
            },
            'command_export': {
                'keywords': ['export', 'xuất', 'chạy lại', 'tạo lại', 'export md', 'tạo md'],
                'confidence': 0.0
            },
            'command_check': {
                'keywords': ['check', 'kiểm tra', 'xem', 'collection', 'pdf'],
                'confidence': 0.0
            },
            'no_idea': {
                'keywords': ['không biết', 'ko biết', 'chưa biết', 'đề xuất', 'đề cử', 
                           'gợi ý', 'suggest', 'recommend', 'chủ đề', 'topics', 'topic',
                           'hỏi gì', 'nói gì', 'tìm hiểu gì'],
                'confidence': 0.0
            },
            'question': {
                'keywords': ['gì', 'là', 'what', 'is', 'how', 'why', 'when', 'where', 
                           'tại sao', 'như thế nào', 'khi nào', 'ở đâu', 'nào', 'which',
                           'định nghĩa', 'giải thích', 'explain', 'define', 'tìm', 'search'],
                'confidence': 0.0
            }
        }
        
        # Calculate confidence for each intent
        for intent_name, intent_data in intents.items():
            matches = sum(1 for kw in intent_data['keywords'] if kw in text_lower)
            if matches > 0:
                # Confidence = số match / tổng số keywords (nhưng cap ở 1.0)
                intent_data['confidence'] = min(matches * 0.3, 1.0)  # Mỗi match = 0.3 điểm
        
        # Check message characteristics
        word_count = len(text.split())
        has_question_mark = '?' in text
        
        # Ưu tiên no_idea nếu có keywords mạnh
        if intents['no_idea']['confidence'] >= 0.6:
            # no_idea có độ ưu tiên cao
            pass
        # Ưu tiên question nếu câu dài (>10 từ) và có dấu hỏi
        elif word_count > 10 or has_question_mark:
            # Boost question confidence nhưng không override no_idea
            if intents['no_idea']['confidence'] < 0.6:
                intents['question']['confidence'] = max(intents['question']['confidence'], 0.7)
        
        # Get best intent
        best_intent = max(intents.items(), key=lambda x: x[1]['confidence'])
        intent_name = best_intent[0]
        confidence = best_intent[1]['confidence']
        
        # If no clear intent, default to question
        if confidence == 0:
            intent_name = 'question'
            confidence = 0.5
        
        result = {
            'intent': intent_name,
            'confidence': confidence,
            'all_intents': {k: v['confidence'] for k, v in intents.items() if v['confidence'] > 0}
        }
        
        logger.info(f"🎯 Intent detected: {intent_name} (confidence: {confidence:.2f})")
        return result


# --- CONVENIENCE FUNCTIONS ---

_text_processor = None

def get_text_processor() -> TextProcessor:
    """Get singleton text processor instance."""
    global _text_processor
    if _text_processor is None:
        _text_processor = TextProcessor()
    return _text_processor


# --- TEST ---
if __name__ == "__main__":
    print("=== Testing TextProcessor ===\n")
    
    processor = TextProcessor()
    
    # Test spelling
    print("1. Spell checking:")
    test_texts = [
        "What is artficial inteligence?",  # Có lỗi
        "ROUGE là gì?",  # Tiếng Việt, OK
        "Explain the metrcs for chatbot"  # Có lỗi
    ]
    
    for text in test_texts:
        print(f"\n   Text: {text}")
        result = processor.check_spelling(text)
        print(f"   Errors: {result['has_errors']}")
        if result['corrections']:
            print(f"   Corrections: {result['corrections']}")
            corrected = processor.correct_text(text, auto_correct=True)
            print(f"   Corrected: {corrected}")
    
    # Test intent
    print("\n\n2. Intent detection:")
    test_intents = [
        "Xin chào",
        "ROUGE là gì?",
        "Tạm biệt",
        "Export MD file",
        "Check collection",
        "Giúp tôi với"
    ]
    
    for text in test_intents:
        print(f"\n   Text: {text}")
        result = processor.detect_intent(text)
        print(f"   Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
    
    print("\n=== Test completed ===")
