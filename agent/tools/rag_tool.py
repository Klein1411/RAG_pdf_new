"""
RAG Tool - Tool để Agent gọi vào RAG system

Tool này wrap các chức năng của qa_app.py để Agent có thể sử dụng.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Thêm thư mục gốc project vào sys.path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.config import (
    RAG_TOOL_NAME,
    RAG_TOOL_DESCRIPTION,
    RAG_MAX_RESULTS,
    RAG_SIMILARITY_THRESHOLD
)

# Import từ src
import torch
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL_NAME, COLLECTION_NAME
from src.milvus import get_or_create_collection
from src.llm_handler import initialize_and_select_llm, generate_answer_with_fallback
from src.logging_config import get_logger

logger = get_logger(__name__)


class RAGTool:
    """
    Tool cho Agent để search và truy vấn thông tin từ RAG system.
    
    Attributes:
        name: Tên của tool
        description: Mô tả chức năng
        embedding_model: Model để encode queries
        collection: Milvus collection
        llm_client: LLM client để generate answers
    """
    
    def __init__(self):
        """Khởi tạo RAG Tool với các dependencies cần thiết."""
        self.name = RAG_TOOL_NAME
        self.description = RAG_TOOL_DESCRIPTION
        
        logger.info(f"Đang khởi tạo RAG Tool: {self.name}")
        
        # Khởi tạo embedding model
        self.embedding_model = self._init_embedding_model()
        
        # Kết nối Milvus
        self.collection = self._init_milvus_collection()
        
        # Khởi tạo LLM client
        self.llm_client, self.model_choice, self.ollama_model_name = self._init_llm_client()
        
        logger.info("✅ RAG Tool đã sẵn sàng")
    
    def _init_embedding_model(self) -> SentenceTransformer:
        """Khởi tạo embedding model."""
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Tải embedding model '{EMBEDDING_MODEL_NAME}' trên {device}")
        
        try:
            model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            model.to(device)
            return model
        except Exception as e:
            logger.error(f"Lỗi khi tải embedding model: {e}")
            raise
    
    def _init_milvus_collection(self):
        """Kết nối đến Milvus collection."""
        logger.info(f"Kết nối đến Milvus collection: {COLLECTION_NAME}")
        
        try:
            collection = get_or_create_collection(
                collection_name=COLLECTION_NAME,
                dim=self.embedding_model.get_sentence_embedding_dimension(),
                recreate=False  # Không tạo mới, chỉ kết nối
            )
            collection.load()
            return collection
        except Exception as e:
            logger.error(f"Lỗi khi kết nối Milvus: {e}")
            raise
    
    def _init_llm_client(self):
        """
        Khởi tạo LLM client.
        
        Returns:
            Tuple of (llm_client, model_choice, ollama_model_name)
        """
        logger.info("Khởi tạo LLM client cho RAG")
        
        try:
            model_choice, gemini_client, ollama_model_name = initialize_and_select_llm()
            
            # Lưu thông tin model
            if model_choice == '1':
                self.llm_name = "Gemini"
                logger.info(f"Sử dụng LLM: {self.llm_name}")
                return gemini_client, model_choice, ollama_model_name
            else:
                self.llm_name = f"Ollama ({ollama_model_name})"
                logger.info(f"Sử dụng LLM: {self.llm_name}")
                return None, model_choice, ollama_model_name
                
        except Exception as e:
            logger.error(f"Lỗi khi khởi tạo LLM: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Search thông tin trong RAG system.
        
        Args:
            query: Câu hỏi/từ khóa tìm kiếm
            top_k: Số kết quả trả về (mặc định từ config)
            threshold: Ngưỡng similarity (mặc định từ config)
            
        Returns:
            Dict chứa results và metadata
        """
        top_k = top_k or RAG_MAX_RESULTS
        threshold = threshold or RAG_SIMILARITY_THRESHOLD
        
        logger.info(f"🔍 Search query: '{query}' (top_k={top_k}, threshold={threshold})")
        
        try:
            # Encode query
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search trong Milvus (sử dụng L2 distance thay vì COSINE)
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=None,
                output_fields=["text", "page", "pdf_source"]
            )
            
            # Parse results
            if not results or not results[0]:
                logger.warning("Không tìm thấy kết quả phù hợp")
                return {
                    "success": False,
                    "message": "Không tìm thấy thông tin liên quan",
                    "results": [],
                    "count": 0
                }
            
            # Filter by threshold và format results
            # Với L2 distance: càng nhỏ càng giống nhau
            # L2 distance range: [0, ∞), nên càng nhỏ càng tốt
            # Để dễ hiểu: chuyển L2 sang similarity score [0, 1]
            # similarity = 1 / (1 + distance)
            formatted_results = []
            
            logger.info(f"📊 Distances from Milvus:")
            for hit in results[0]:
                # Chuyển L2 distance thành similarity score
                similarity = 1.0 / (1.0 + hit.distance)
                logger.info(f"   - Distance: {hit.distance:.4f}, Similarity: {similarity:.4f}")
                
                # Chỉ lấy kết quả có similarity >= threshold
                if similarity >= threshold:
                    formatted_results.append({
                        "text": hit.entity.get('text'),
                        "page": hit.entity.get('page'),
                        "source": hit.entity.get('pdf_source'),
                        "score": float(similarity)
                    })
            
            logger.info(f"✅ Tìm thấy {len(formatted_results)} kết quả")
            
            return {
                "success": True,
                "results": formatted_results,
                "count": len(formatted_results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi search: {e}")
            return {
                "success": False,
                "message": f"Lỗi: {str(e)}",
                "results": [],
                "count": 0
            }
    
    def ask(
        self, 
        question: str,
        top_k: Optional[int] = None,
        return_context: bool = False
    ) -> Dict[str, Any]:
        """
        Hỏi câu hỏi và nhận câu trả lời từ RAG system.
        
        Args:
            question: Câu hỏi
            top_k: Số context documents (mặc định từ config)
            return_context: Có trả về context không
            
        Returns:
            Dict chứa answer, sources và metadata
        """
        top_k = top_k or RAG_MAX_RESULTS
        
        logger.info(f"❓ Question: '{question}'")
        
        try:
            # Search context
            search_result = self.search(question, top_k=top_k)
            
            if not search_result["success"] or search_result["count"] == 0:
                return {
                    "success": False,
                    "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn.",
                    "sources": [],
                    "context": None
                }
            
            # Build context từ search results
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_result["results"], 1):
                context_parts.append(f"[Đoạn {i} - Trang {result['page']}]:\n{result['text']}")
                sources.append({
                    "page": result["page"],
                    "source": result["source"],
                    "score": result["score"]
                })
            
            context = "\n\n".join(context_parts)
            
            # Build prompt
            prompt = f"""Dựa trên các thông tin sau đây từ tài liệu:

{context}

Hãy trả lời câu hỏi: {question}

Lưu ý:
- Chỉ sử dụng thông tin từ context được cung cấp
- Trích dẫn số trang khi có thể
- Nếu không đủ thông tin, hãy nói rõ
- Trả lời ngắn gọn, súc tích
"""
            
            # Generate answer
            logger.info("Đang generate câu trả lời...")
            answer = generate_answer_with_fallback(
                prompt,
                self.model_choice,
                self.llm_client,
                self.ollama_model_name
            )
            
            logger.info("✅ Đã generate câu trả lời")
            
            result = {
                "success": True,
                "answer": answer,
                "sources": sources,
                "query": question
            }
            
            if return_context:
                result["context"] = context
            
            return result
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý câu hỏi: {e}")
            return {
                "success": False,
                "answer": f"Xin lỗi, đã có lỗi xảy ra: {str(e)}",
                "sources": [],
                "context": None
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Lấy thông tin về tool."""
        return {
            "name": self.name,
            "description": self.description,
            "collection": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "max_results": RAG_MAX_RESULTS,
            "threshold": RAG_SIMILARITY_THRESHOLD
        }


# --- TOOL INTERFACE CHO AGENT ---

def create_rag_tool() -> RAGTool:
    """
    Factory function để tạo RAG tool.
    
    Returns:
        RAGTool instance
    """
    return RAGTool()


# --- TEST & DEMO ---
if __name__ == "__main__":
    print("=== Testing RAG Tool ===\n")
    
    # Khởi tạo tool
    print("1. Khởi tạo RAG Tool...")
    tool = create_rag_tool()
    print(f"   ✅ Tool info: {tool.get_info()}\n")
    
    # Test search
    print("2. Test search...")
    search_result = tool.search("chỉ số ROUGE", top_k=15)  # Vietnamese query, top_k=15
    print(f"   Found: {search_result['count']} results")
    if search_result['results']:
        print(f"   Top result: {search_result['results'][0]['text'][:100]}...")
        print(f"   Score: {search_result['results'][0]['score']:.4f}\n")
    
    # Test ask
    print("\n3. Test ask...")
    answer_result = tool.ask("ROUGE là gì?", top_k=15)  # Vietnamese question, top_k=15
    print(f"   Answer: {answer_result['answer'][:200]}...")
    print(f"   Sources: {len(answer_result['sources'])} documents\n")
    
    print("=== Test completed ===")
