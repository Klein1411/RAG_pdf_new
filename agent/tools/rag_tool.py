# coding: utf-8
"""
RAG Tool - Complete RAG Workflow
Tách toàn bộ logic RAG từ agent.py để dễ test và maintain

Chức năng:
- Answer questions using RAG
- Split complex multi-part questions
- Multi-collection search
- Context formatting
- LLM answer generation
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.tools.search_tool import SearchTool
from src.logging_config import get_logger

logger = get_logger(__name__)


class RagTool:
    """
    Tool thực hiện complete RAG workflow
    Độc lập, testable, reusable
    """
    
    def __init__(
        self,
        search_tool: SearchTool,
        llm_client: Any,
        llm_type: str,
        ollama_model: Optional[str] = None
    ):
        """
        Khởi tạo RagTool
        
        Args:
            search_tool: SearchTool instance để search vectors
            llm_client: LLM client (Gemini hoặc Ollama)
            llm_type: 'gemini' hoặc 'ollama'
            ollama_model: Tên model Ollama nếu dùng Ollama
        """
        self.name = "rag_tool"
        self.description = "RAG tool for answering questions from documents"
        
        self.search_tool = search_tool
        self.llm_client = llm_client
        self.llm_type = llm_type
        self.ollama_model = ollama_model
        
        logger.info(f"✅ RagTool initialized with LLM type: {llm_type}")
    
    def answer_question(
        self,
        question: str,
        collection_names: List[str],
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = 15
    ) -> Dict[str, Any]:
        """
        Complete RAG workflow để trả lời câu hỏi
        
        Args:
            question: Câu hỏi từ user
            collection_names: List các collection cần search
            conversation_history: Lịch sử hội thoại (optional)
            top_k: Số kết quả tối đa
            
        Returns:
            Dict với keys:
            - 'success': bool
            - 'answer': str (câu trả lời)
            - 'sources': List[Dict] (nguồn trích dẫn)
            - 'search_results': List[Dict] (kết quả search)
            - 'error': str (nếu có lỗi)
        """
        try:
            logger.info(f"RAG: Answering question in {len(collection_names)} collections")
            
            # BƯỚC 1: Kiểm tra câu hỏi có phức tạp không (multi-part)
            sub_questions = self.split_complex_question(question)
            
            if len(sub_questions) > 1:
                # Câu hỏi phức tạp → xử lý từng phần
                logger.info(f"📝 Phát hiện {len(sub_questions)} câu hỏi con")
                return self._handle_complex_question(
                    sub_questions,
                    collection_names,
                    conversation_history,
                    top_k
                )
            else:
                # Câu hỏi đơn giản
                return self._handle_simple_question(
                    question,
                    collection_names,
                    conversation_history,
                    top_k
                )
        
        except Exception as e:
            logger.error(f"❌ RAG error: {e}", exc_info=True)
            return {
                'success': False,
                'answer': f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi: {str(e)}",
                'sources': [],
                'search_results': [],
                'error': str(e)
            }
    
    def _handle_simple_question(
        self,
        question: str,
        collection_names: List[str],
        conversation_history: Optional[List[Dict]],
        top_k: int
    ) -> Dict[str, Any]:
        """Xử lý câu hỏi đơn giản"""
        
        # BƯỚC 2: Search trong collections
        search_results = self.search_tool.search_multi_collections(
            query=question,
            collection_names=collection_names,
            top_k=top_k,
            similarity_threshold=0.10
        )
        
        if not search_results:
            return {
                'success': True,
                'answer': "Xin lỗi, tôi không tìm thấy thông tin liên quan trong tài liệu.",
                'sources': [],
                'search_results': []
            }
        
        # BƯỚC 3: Format context cho LLM
        context = self.search_tool.format_results_for_context(
            search_results,
            max_results=top_k
        )
        
        # BƯỚC 4: Generate answer với LLM
        answer = self._generate_answer(
            question=question,
            context=context,
            conversation_history=conversation_history
        )
        
        # BƯỚC 5: Extract sources
        sources = self._extract_sources(search_results)
        
        return {
            'success': True,
            'answer': answer,
            'sources': sources,
            'search_results': search_results
        }
    
    def _handle_complex_question(
        self,
        sub_questions: List[str],
        collection_names: List[str],
        conversation_history: Optional[List[Dict]],
        top_k: int
    ) -> Dict[str, Any]:
        """Xử lý câu hỏi phức tạp (multi-part)"""
        
        all_answers = []
        all_sources = []
        all_search_results = []
        
        # Trả lời từng câu hỏi con
        for i, sub_q in enumerate(sub_questions, 1):
            logger.info(f"  [{i}/{len(sub_questions)}] {sub_q}")
            
            result = self._handle_simple_question(
                question=sub_q,
                collection_names=collection_names,
                conversation_history=conversation_history,
                top_k=top_k // len(sub_questions)  # Chia đều top_k
            )
            
            if result['success']:
                all_answers.append(f"**{i}. {sub_q}**\n{result['answer']}")
                all_sources.extend(result['sources'])
                all_search_results.extend(result['search_results'])
        
        # Combine answers
        combined_answer = "\n\n".join(all_answers)
        
        # Deduplicate sources
        unique_sources = self._deduplicate_sources(all_sources)
        
        return {
            'success': True,
            'answer': combined_answer,
            'sources': unique_sources,
            'search_results': all_search_results
        }
    
    def split_complex_question(self, question: str) -> List[str]:
        """
        Tách câu hỏi phức tạp thành các câu hỏi con
        
        Args:
            question: Câu hỏi gốc
            
        Returns:
            List các câu hỏi con (nếu là câu hỏi phức tạp)
            hoặc [question] nếu là câu hỏi đơn giản
        """
        # Patterns cho complex questions
        patterns = [
            r'(\d+[\.\)])',  # Numbered: 1. 2. hoặc 1) 2)
            r'([a-z][\.\)])',  # Lettered: a. b. hoặc a) b)
            r'\band\b',  # "and" separator
            r'\bvà\b',  # "và" separator (Vietnamese)
        ]
        
        # Check patterns
        for pattern in patterns[:2]:  # Chỉ check numbered/lettered
            matches = re.findall(pattern, question)
            if len(matches) >= 2:
                # Có pattern numbered/lettered
                parts = re.split(pattern, question)
                
                sub_questions = []
                for part in parts:
                    cleaned = part.strip()
                    # Bỏ số/chữ cái ở đầu
                    cleaned = re.sub(r'^[\d\w][\.\)]\s*', '', cleaned)
                    
                    if len(cleaned) > 10:  # Câu hỏi tối thiểu 10 ký tự
                        sub_questions.append(cleaned)
                
                if len(sub_questions) >= 2:
                    logger.debug(f"Split into {len(sub_questions)} sub-questions")
                    return sub_questions
        
        # Check "and"/"và" separator
        if ' and ' in question.lower() or ' và ' in question.lower():
            # Tách bằng "and" hoặc "và"
            separator = ' and ' if ' and ' in question.lower() else ' và '
            parts = question.split(separator)
            
            if len(parts) == 2:
                # Chỉ split nếu cả 2 phần đều dài đủ
                if all(len(p.strip()) > 10 for p in parts):
                    sub_questions = [p.strip() for p in parts]
                    logger.debug(f"Split by '{separator}': {len(sub_questions)} parts")
                    return sub_questions
        
        # Không phải câu hỏi phức tạp
        return [question]
    
    def _generate_answer(
        self,
        question: str,
        context: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate answer sử dụng LLM
        
        Args:
            question: Câu hỏi
            context: Context từ search results
            conversation_history: Lịch sử hội thoại
            
        Returns:
            Answer string
        """
        # Build prompt
        prompt = f"""Based on the following information, answer the question accurately.

Context from documents:
{context}

Question: {question}

Instructions:
- Answer based ONLY on the provided context
- Be concise and clear
- If context doesn't contain relevant info, say "I cannot find information about this"
- Use the same language as the question (Vietnamese or English)

Answer:"""
        
        try:
            if self.llm_type == 'gemini':
                # Gemini
                answer = self.llm_client.generate_content(prompt)
                return answer.strip() if answer else "Xin lỗi, không thể tạo câu trả lời."
            
            elif self.llm_type == 'ollama':
                # Ollama
                response = self.llm_client.chat(
                    model=self.ollama_model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                answer = response['message']['content'].strip()
                return answer
            
            else:
                return f"Unsupported LLM type: {self.llm_type}"
        
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return f"Xin lỗi, gặp lỗi khi tạo câu trả lời: {str(e)}"
    
    def _extract_sources(self, search_results: List[Dict]) -> List[Dict]:
        """
        Extract unique sources từ search results
        
        Args:
            search_results: List các search results
            
        Returns:
            List unique sources với format:
            [{'pdf': str, 'page': int, 'collection': str}, ...]
        """
        sources = []
        seen = set()
        
        for result in search_results:
            key = (result.get('source', ''), result.get('page', 0))
            
            if key not in seen:
                seen.add(key)
                sources.append({
                    'pdf': result.get('source', 'unknown'),
                    'page': result.get('page', 0),
                    'collection': result.get('collection', 'unknown')
                })
        
        return sources
    
    def _deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """Loại bỏ sources trùng lặp"""
        unique_sources = []
        seen = set()
        
        for source in sources:
            key = (source.get('pdf', ''), source.get('page', 0))
            if key not in seen:
                seen.add(key)
                unique_sources.append(source)
        
        return unique_sources


# Singleton instance
_rag_tool = None

def get_rag_tool(
    search_tool: SearchTool,
    llm_client: Any,
    llm_type: str,
    ollama_model: Optional[str] = None
) -> RagTool:
    """
    Get hoặc create RagTool instance
    
    Note: Không dùng singleton vì cần pass dynamic params
    """
    return RagTool(
        search_tool=search_tool,
        llm_client=llm_client,
        llm_type=llm_type,
        ollama_model=ollama_model
    )
