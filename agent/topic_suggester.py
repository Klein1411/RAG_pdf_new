# coding: utf-8
"""
Topic Suggester - Đề xuất chủ đề từ tài liệu PDF
Giúp user biết có thể hỏi gì khi không biết hỏi gì hoặc không tìm thấy thông tin

Tính năng:
- Đọc metadata từ collections
- Trích xuất các chủ đề/keywords từ tài liệu
- Tạo câu hỏi gợi ý (suggestions)
- Cache tạm thời (xóa khi tắt agent hoặc clear)
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import re
from collections import Counter, defaultdict

# Thêm project root vào path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.logging_config import get_logger

logger = get_logger(__name__)


class TopicSuggester:
    """
    Tạo và quản lý topic suggestions từ tài liệu
    Cache tạm thời - reset khi clear hoặc tắt agent
    """
    
    def __init__(self):
        # Cache topics theo collection
        self.topics_cache: Dict[str, List[Dict]] = {}
        
        # Keywords quan trọng (dùng để trích xuất topics)
        self.important_keywords = {
            # NLP/AI terms
            'rouge', 'bleu', 'metric', 'evaluation', 'summarization',
            'nlp', 'transformer', 'bert', 'gpt', 'model', 'training',
            'accuracy', 'precision', 'recall', 'f1', 'score',
            'dataset', 'benchmark', 'performance', 'neural', 'network',
            
            # Vietnamese NLP
            'tiếng việt', 'vietnamese', 'ngôn ngữ', 'xử lý', 'phân tích',
            'mô hình', 'huấn luyện', 'đánh giá', 'dữ liệu',
            
            # Research terms
            'method', 'approach', 'algorithm', 'technique', 'framework',
            'phương pháp', 'thuật toán', 'kỹ thuật', 'cách tiếp cận',
            'experiment', 'result', 'conclusion', 'thí nghiệm', 'kết quả',
            
            # General topics
            'introduction', 'background', 'literature', 'review',
            'giới thiệu', 'tổng quan', 'nghiên cứu', 'liên quan',
        }
        
        # Stop words (từ bỏ qua) - MỞ RỘNG
        self.stop_words = {
            # English common words
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'when',
            'where', 'why', 'how', 'can', 'not', 'no', 'yes',
            # Pronouns & common words
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'ours', 'theirs',
            'am', 'been', 'being', 'get', 'got', 'make', 'made', 'use', 'used',
            'see', 'seen', 'know', 'think', 'take', 'come', 'give', 'find', 'tell',
            'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call', 'need', 'become',
            # Vietnamese
            'là', 'của', 'và', 'với', 'trong', 'được', 'có', 'này', 'đó',
            'các', 'để', 'từ', 'một', 'không', 'như', 'về', 'cho', 'theo',
            'tôi', 'bạn', 'anh', 'chị', 'em', 'chúng', 'họ', 'ta',
            # Single characters & short words
            'tóm', 'tắt', 'cần', 'bản', 'đề', 'mục', 'số', 'ví', 'dụ',
        }
        
        logger.info("TopicSuggester initialized")
    
    def extract_topics_from_collection(
        self, 
        collection_name: str,
        sample_texts: List[str],
        max_topics: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Trích xuất topics từ sample texts của collection
        Cải thiện: lấy cả n-grams (cụm từ) không chỉ từ đơn
        
        Args:
            collection_name: Tên collection
            sample_texts: Danh sách text mẫu từ collection
            max_topics: Số lượng topics tối đa
            
        Returns:
            List of topics với format:
            {
                'keyword': str,
                'frequency': int,
                'questions': List[str]
            }
        """
        # Trích xuất cả unigrams và bigrams
        all_unigrams = []
        all_bigrams = []
        
        for text in sample_texts:
            # Lấy từ từ text (lowercase, remove punctuation)
            words = re.findall(r'\b[a-zA-Zàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+\b', text.lower())
            
            # Unigrams (single words)
            all_unigrams.extend(words)
            
            # Bigrams (2-word phrases)
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                all_bigrams.append(bigram)
        
        # Đếm frequency
        unigram_counts = Counter(all_unigrams)
        bigram_counts = Counter(all_bigrams)
        
        # Filter unigrams: bỏ stop words, chỉ giữ từ dài >= 4 ký tự (tránh "tóm", "tắt")
        filtered_unigrams = {
            word: count 
            for word, count in unigram_counts.items() 
            if word not in self.stop_words 
            and len(word) >= 4  # Tăng từ 3 lên 4
            and count >= 2  # Xuất hiện ít nhất 2 lần
        }
        
        # Filter bigrams: bỏ những cụm có stop words
        filtered_bigrams = {}
        for bigram, count in bigram_counts.items():
            words = bigram.split()
            # Chỉ giữ nếu cả 2 từ đều không phải stop word và count >= 2
            if (len(words) == 2 
                and all(w not in self.stop_words for w in words)
                and all(len(w) >= 3 for w in words)
                and count >= 2):
                filtered_bigrams[bigram] = count
        
        # Ưu tiên important keywords (unigrams)
        prioritized_unigrams = {}
        for word, count in filtered_unigrams.items():
            if word in self.important_keywords:
                prioritized_unigrams[word] = count * 3  # Boost important words
            else:
                prioritized_unigrams[word] = count
        
        # Ưu tiên bigrams chứa important keywords
        prioritized_bigrams = {}
        for bigram, count in filtered_bigrams.items():
            # Check if any word in bigram is important
            has_important = any(word in self.important_keywords for word in bigram.split())
            if has_important:
                prioritized_bigrams[bigram] = count * 2  # Boost bigrams with important words
            else:
                prioritized_bigrams[bigram] = count
        
        # Gộp unigrams và bigrams
        all_keywords = {**prioritized_unigrams, **prioritized_bigrams}
        
        # Lấy top keywords
        top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:max_topics]
        
        # Tạo topics với câu hỏi gợi ý
        topics = []
        for keyword, freq in top_keywords:
            topic = {
                'keyword': keyword,
                'frequency': freq,
                'questions': self._generate_questions(keyword)
            }
            topics.append(topic)
        
        logger.info(f"Extracted {len(topics)} topics from {collection_name}: {[t['keyword'] for t in topics]}")
        return topics
    
    def _generate_questions(self, keyword: str) -> List[str]:
        """
        Tạo câu hỏi gợi ý từ keyword
        
        Args:
            keyword: Từ khóa chủ đề (có thể là bigram)
            
        Returns:
            Danh sách câu hỏi
        """
        # Check if keyword is a phrase (bigram)
        is_phrase = ' ' in keyword
        
        if is_phrase:
            # Bigram - câu hỏi phù hợp với cụm từ
            questions = [
                f"Giải thích về {keyword}",
                f"{keyword.title()} là gì?",
                f"Tài liệu có đề cập gì về {keyword}?",
                f"Ưu điểm và nhược điểm của {keyword}",
                f"Phương pháp {keyword} hoạt động như thế nào?",
            ]
        else:
            # Unigram - câu hỏi cho từ đơn
            questions = [
                f"{keyword.title()} là gì?",
                f"Giải thích về {keyword}",
                f"Tài liệu có đề cập gì về {keyword}?",
                f"Phương pháp {keyword} hoạt động như thế nào?",
                f"Ưu điểm và nhược điểm của {keyword}",
            ]
        
        # Chọn 2-3 câu hỏi ngẫu nhiên
        import random
        return random.sample(questions, min(3, len(questions)))
    
    def build_topics_from_collections(
        self,
        collection_names: List[str],
        sample_size: int = 50
    ) -> Dict[str, List[Dict]]:
        """
        Xây dựng topics từ nhiều collections
        
        Args:
            collection_names: Danh sách tên collection
            sample_size: Số lượng documents lấy mẫu từ mỗi collection
            
        Returns:
            Dict mapping collection_name -> topics
        """
        from pymilvus import Collection
        
        all_topics = {}
        
        for col_name in collection_names:
            try:
                # Load collection
                collection = Collection(col_name)
                collection.load()
                
                # Lấy sample documents
                # Query random documents
                results = collection.query(
                    expr="id >= 0",
                    output_fields=["text", "pdf_source"],  # Sửa từ 'source' thành 'pdf_source'
                    limit=sample_size
                )
                
                if not results:
                    logger.warning(f"No data in {col_name}")
                    continue
                
                # Trích xuất texts
                sample_texts = [doc.get('text', '') for doc in results if doc.get('text')]
                
                # Extract topics
                topics = self.extract_topics_from_collection(col_name, sample_texts)
                all_topics[col_name] = topics
                
                # Cache
                self.topics_cache[col_name] = topics
                
                logger.info(f"✅ Built topics for {col_name}: {len(topics)} topics")
                
            except Exception as e:
                logger.error(f"Error building topics for {col_name}: {e}")
                continue
        
        return all_topics
    
    def get_suggestions(
        self,
        collection_names: Optional[List[str]] = None,
        max_suggestions: int = 5
    ) -> List[str]:
        """
        Lấy danh sách câu hỏi gợi ý
        
        Args:
            collection_names: Danh sách collection cần gợi ý (None = tất cả)
            max_suggestions: Số lượng gợi ý tối đa
            
        Returns:
            Danh sách câu hỏi gợi ý
        """
        all_questions = []
        
        # Nếu chưa có cache, báo lỗi
        if not self.topics_cache:
            logger.warning("No topics cached. Call build_topics_from_collections first.")
            return [
                "Hãy hỏi tôi về nội dung tài liệu",
                "Bạn muốn tìm hiểu điều gì?",
                "Tôi có thể giúp bạn tìm thông tin từ PDF"
            ]
        
        # Lấy topics từ collections được chỉ định
        if collection_names:
            target_collections = collection_names
        else:
            target_collections = list(self.topics_cache.keys())
        
        # Tổng hợp câu hỏi từ topics
        for col_name in target_collections:
            if col_name in self.topics_cache:
                topics = self.topics_cache[col_name]
                for topic in topics:
                    all_questions.extend(topic['questions'])
        
        # Loại bỏ trùng lặp và shuffle
        import random
        unique_questions = list(set(all_questions))
        random.shuffle(unique_questions)
        
        return unique_questions[:max_suggestions]
    
    def get_topic_summary(self, collection_names: Optional[List[str]] = None) -> str:
        """
        Tạo tóm tắt các chủ đề có sẵn
        
        Args:
            collection_names: Danh sách collection (None = tất cả)
            
        Returns:
            String tóm tắt các topics
        """
        if not self.topics_cache:
            return "Chưa có thông tin về chủ đề. Vui lòng setup trước."
        
        # Lấy collections
        if collection_names:
            target_collections = collection_names
        else:
            target_collections = list(self.topics_cache.keys())
        
        # Tạo summary
        summary_lines = ["📚 CÁC CHỦ ĐỀ CÓ SẴN TRONG TÀI LIỆU:\n"]
        
        for col_name in target_collections:
            if col_name not in self.topics_cache:
                continue
            
            topics = self.topics_cache[col_name]
            if not topics:
                continue
            
            # Lấy tên PDF từ collection name (loại bỏ prefix)
            pdf_name = col_name.replace('collection_', '').replace('_', ' ')
            summary_lines.append(f"\n📄 {pdf_name}:")
            
            # Liệt kê top 5 topics
            for i, topic in enumerate(topics[:5], 1):
                keyword = topic['keyword'].title()
                summary_lines.append(f"   {i}. {keyword}")
        
        return "\n".join(summary_lines)
    
    def clear_cache(self):
        """Xóa tất cả cache topics"""
        self.topics_cache.clear()
        logger.info("Topics cache cleared")
    
    def has_topics(self) -> bool:
        """Kiểm tra xem có topics trong cache không"""
        return len(self.topics_cache) > 0


# Singleton instance
_suggester_instance = None

def get_topic_suggester() -> TopicSuggester:
    """Lấy instance của TopicSuggester (singleton)"""
    global _suggester_instance
    if _suggester_instance is None:
        _suggester_instance = TopicSuggester()
        logger.info("TopicSuggester instance created")
    return _suggester_instance


def reset_topic_suggester():
    """Reset singleton instance (dùng khi cần clear hoàn toàn)"""
    global _suggester_instance
    if _suggester_instance:
        _suggester_instance.clear_cache()
    _suggester_instance = None
    logger.info("TopicSuggester instance reset")


# Test function
def test_suggester():
    """Test TopicSuggester"""
    suggester = TopicSuggester()
    
    # Test với sample texts
    sample_texts = [
        "ROUGE is a metric for evaluating summarization quality.",
        "BLEU score measures machine translation quality.",
        "The transformer model revolutionized NLP tasks.",
        "BERT uses bidirectional training for language understanding.",
        "Evaluation metrics include precision, recall, and F1 score.",
    ]
    
    topics = suggester.extract_topics_from_collection(
        "test_collection",
        sample_texts
    )
    
    print("\n" + "="*70)
    print("TEST TOPIC SUGGESTER")
    print("="*70)
    
    print(f"\nExtracted {len(topics)} topics:")
    for topic in topics:
        print(f"\n🔑 Keyword: {topic['keyword']} (frequency: {topic['frequency']})")
        print("   Suggested questions:")
        for q in topic['questions']:
            print(f"   - {q}")
    
    # Cache và test suggestions
    suggester.topics_cache['test_collection'] = topics
    suggestions = suggester.get_suggestions(max_suggestions=5)
    
    print(f"\n\n💡 Random suggestions ({len(suggestions)}):")
    for i, q in enumerate(suggestions, 1):
        print(f"{i}. {q}")


if __name__ == "__main__":
    test_suggester()
