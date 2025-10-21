"""
Intent Detector - Phát hiện ý định từ user message.

Tách logic intent detection ra khỏi Agent class.
Simple keyword-based detection, có thể upgrade thành ML model sau.
"""

from typing import Dict, Any, List


class IntentDetector:
    """
    Simple keyword-based intent detector.
    
    Intents:
    - greeting: Xin chào, hello
    - farewell: Tạm biệt, bye
    - thanks: Cảm ơn, thank you
    - help: Hướng dẫn, help
    - command_export: Export to MD
    - command_check: Check collection
    - no_idea: Không biết hỏi gì, gợi ý chủ đề
    - question: Câu hỏi (default)
    """
    
    def __init__(self):
        """Initialize intent detector với keyword patterns."""
        self.patterns = self._build_patterns()
    
    def _build_patterns(self) -> Dict[str, List[str]]:
        """
        Build keyword patterns cho mỗi intent.
        
        Returns:
            Dict[intent_name, List[keywords]]
        """
        return {
            'greeting': ['hello', 'hi', 'hey', 'xin chào', 'chào', 'halo'],
            'farewell': ['bye', 'goodbye', 'tạm biệt', 'see you', 'exit', 'quit'],
            'thanks': ['thank', 'thanks', 'cảm ơn', 'cám ơn', 'thanks you'],
            'help': ['help', 'hướng dẫn', 'giúp', 'how to'],
            'command_export': ['export', 'xuất'],
            'command_check': ['check collection', 'kiểm tra collection'],
            'no_idea': [
                'không biết hỏi gì', 'không biết hỏi', 'đề xuất', 'gợi ý',
                'tôi nên hỏi gì', 'có thể hỏi gì', 'chủ đề nào',
                "don't know what to ask", 'suggest topics', 'what can i ask'
            ],
            'question': ['what', 'why', 'how', 'when', 'where', 'who', 
                        'gì', 'sao', 'như thế nào', 'khi nào', 'ở đâu', 'ai', 'là']
        }
    
    def detect(self, message: str) -> Dict[str, Any]:
        """
        Detect intent từ message.
        
        Args:
            message: User message
            
        Returns:
            Dict với keys:
                - intent: str (intent name)
                - confidence: float (0-1)
        """
        message_lower = message.lower()
        
        # Check patterns theo thứ tự ưu tiên
        
        # 1. Greeting (highest priority for short messages)
        if any(keyword in message_lower for keyword in self.patterns['greeting']):
            return {'intent': 'greeting', 'confidence': 0.9}
        
        # 2. Farewell
        if any(keyword in message_lower for keyword in self.patterns['farewell']):
            return {'intent': 'farewell', 'confidence': 0.9}
        
        # 3. Thanks
        if any(keyword in message_lower for keyword in self.patterns['thanks']):
            return {'intent': 'thanks', 'confidence': 0.9}
        
        # 4. Help
        if any(keyword in message_lower for keyword in self.patterns['help']):
            return {'intent': 'help', 'confidence': 0.8}
        
        # 5. Commands (specific)
        if any(keyword in message_lower for keyword in self.patterns['command_export']):
            return {'intent': 'command_export', 'confidence': 0.85}
        
        if any(keyword in message_lower for keyword in self.patterns['command_check']):
            return {'intent': 'command_check', 'confidence': 0.85}
        
        # 6. No idea / suggest topics
        if any(keyword in message_lower for keyword in self.patterns['no_idea']):
            return {'intent': 'no_idea', 'confidence': 0.8}
        
        # 7. Question (check for question words or '?')
        has_question_word = any(keyword in message_lower for keyword in self.patterns['question'])
        has_question_mark = '?' in message
        
        if has_question_word or has_question_mark:
            confidence = 0.8 if has_question_mark else 0.7
            return {'intent': 'question', 'confidence': confidence}
        
        # 8. Default to question (assume user wants to ask something)
        return {'intent': 'question', 'confidence': 0.5}
    
    def add_pattern(self, intent: str, keywords: List[str]) -> None:
        """
        Add new keywords to an existing intent.
        
        Args:
            intent: Intent name
            keywords: List of keywords to add
        """
        if intent not in self.patterns:
            self.patterns[intent] = []
        self.patterns[intent].extend(keywords)
    
    def create_intent(self, intent: str, keywords: List[str]) -> None:
        """
        Create new intent with keywords.
        
        Args:
            intent: New intent name
            keywords: List of keywords
        """
        self.patterns[intent] = keywords
    
    def get_intents(self) -> List[str]:
        """Get list of available intents."""
        return list(self.patterns.keys())
    
    def get_keywords(self, intent: str) -> List[str]:
        """Get keywords for an intent."""
        return self.patterns.get(intent, [])


# Singleton pattern
_intent_detector = None

def get_intent_detector() -> IntentDetector:
    """
    Get or create IntentDetector instance (singleton).
    
    Returns:
        IntentDetector instance
    """
    global _intent_detector
    if _intent_detector is None:
        _intent_detector = IntentDetector()
    return _intent_detector


def reset_intent_detector():
    """Reset singleton (for testing)."""
    global _intent_detector
    _intent_detector = None


if __name__ == "__main__":
    # Test IntentDetector
    detector = IntentDetector()
    
    print("=== Test IntentDetector ===")
    
    test_cases = [
        ("hello", "greeting"),
        ("xin chào", "greeting"),
        ("bye", "farewell"),
        ("tạm biệt", "farewell"),
        ("thank you", "thanks"),
        ("cảm ơn", "thanks"),
        ("help me", "help"),
        ("export to MD", "command_export"),
        ("check collection", "command_check"),
        ("không biết hỏi gì", "no_idea"),
        ("what is python?", "question"),
        ("how to use this?", "question"),
        ("Python là gì?", "question"),
        ("random text here", "question"),  # default
    ]
    
    print("\nTest cases:")
    passed = 0
    for message, expected in test_cases:
        result = detector.detect(message)
        intent = result['intent']
        confidence = result['confidence']
        
        status = "✅" if intent == expected else "❌"
        print(f"{status} '{message}' → {intent} ({confidence:.2f}) [expected: {expected}]")
        
        if intent == expected:
            passed += 1
    
    print(f"\nResults: {passed}/{len(test_cases)} passed ({passed/len(test_cases)*100:.0f}%)")
    
    # Test get_intents
    print(f"\nAvailable intents: {detector.get_intents()}")
    
    print("\n✅ Test completed")
