# coding: utf-8
"""
Search Tool - Tool tìm kiếm trong nhiều collection
Cho phép Agent search qua nhiều PDF collection cùng lúc
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import torch
from pymilvus import Collection
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL_NAME
from src.logging_config import get_logger

logger = get_logger(__name__)


class SearchTool:
    """
    Tool tìm kiếm vector trong nhiều Milvus collections
    Hỗ trợ tìm kiếm đồng thời qua nhiều PDF collections
    """
    
    def __init__(self, embedding_model: Optional[SentenceTransformer] = None):
        """
        Args:
            embedding_model: Model đã được load sẵn (optional)
        """
        self.name = "search_tool"
        self.description = "Search across multiple PDF collections using vector similarity"
        
        # Sử dụng model được truyền vào hoặc tải mới
        if embedding_model:
            self.embedding_model = embedding_model
        else:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME).to(device)
            logger.info(f"Loaded embedding model on {device}")
    
    def search_multi_collections(
        self,
        query: str,
        collection_names: List[str],
        top_k: int = 15,
        similarity_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trong nhiều collections
        
        Args:
            query: Câu hỏi/query
            collection_names: Danh sách collection names
            top_k: Số kết quả tối đa mỗi collection
            similarity_threshold: Ngưỡng similarity tối thiểu
            
        Returns:
            List of results sorted by score
        """
        logger.info(f"Searching in {len(collection_names)} collections: {collection_names}")
        
        # Encode query
        query_vector = self.embedding_model.encode([query])[0]
        
        all_results = []
        
        for col_name in collection_names:
            try:
                # Load collection
                collection = Collection(col_name)
                collection.load()
                
                # Search parameters
                search_params = {
                    "metric_type": "L2",
                    "params": {"nprobe": 10}
                }
                
                # Search
                results = collection.search(
                    data=[query_vector.tolist()],
                    anns_field="embedding",
                    param=search_params,
                    limit=top_k,
                    output_fields=["text", "page", "pdf_source"]
                )
                
                # Process results
                for hit in results[0]:
                    # Convert L2 distance to similarity (0-1)
                    similarity = 1.0 / (1.0 + hit.distance)
                    
                    if similarity >= similarity_threshold:
                        all_results.append({
                            'text': hit.entity.get('text'),
                            'page': hit.entity.get('page'),
                            'source': hit.entity.get('pdf_source'),
                            'collection': col_name,
                            'score': float(similarity),
                            'distance': float(hit.distance)
                        })
                
                logger.debug(f"Found {len([r for r in results[0] if 1.0/(1.0+r.distance) >= similarity_threshold])} results in {col_name}")
                
            except Exception as e:
                logger.error(f"Error searching {col_name}: {e}")
                continue
        
        # Sort by score (highest first)
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Total results: {len(all_results)}")
        return all_results
    
    def search_single_collection(
        self,
        query: str,
        collection_name: str,
        top_k: int = 15,
        similarity_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trong 1 collection (wrapper cho search_multi_collections)
        
        Args:
            query: Câu hỏi/query
            collection_name: Collection name
            top_k: Số kết quả tối đa
            similarity_threshold: Ngưỡng similarity
            
        Returns:
            List of results
        """
        return self.search_multi_collections(
            query=query,
            collection_names=[collection_name],
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
    
    def format_results_for_context(
        self,
        results: List[Dict[str, Any]],
        max_results: int = 10
    ) -> str:
        """
        Format kết quả thành context string cho LLM
        
        Args:
            results: List of search results
            max_results: Số kết quả tối đa để format
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant information found."
        
        context_parts = []
        for i, result in enumerate(results[:max_results], 1):
            context_parts.append(
                f"[{i}] (from {result['source']}, page {result['page']}, score: {result['score']:.3f}):\n{result['text']}"
            )
        
        return "\n\n".join(context_parts)


# Singleton instance (optional)
_search_tool_instance = None

def get_search_tool(embedding_model: Optional[SentenceTransformer] = None) -> SearchTool:
    """
    Lấy instance của SearchTool (singleton pattern)
    
    Args:
        embedding_model: Model đã load sẵn (optional)
    """
    global _search_tool_instance
    if _search_tool_instance is None:
        _search_tool_instance = SearchTool(embedding_model=embedding_model)
        logger.info("SearchTool instance created")
    return _search_tool_instance


# Test function
def test_search_tool():
    """Test SearchTool"""
    tool = SearchTool()
    
    # Example search
    query = "What is ROUGE?"
    collections = ["metric", "bert_paper"]  # Example collection names
    
    print("\n" + "="*70)
    print("TEST SEARCH TOOL")
    print("="*70)
    print(f"\nQuery: {query}")
    print(f"Collections: {collections}")
    
    results = tool.search_multi_collections(query, collections, top_k=5)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Source: {result['source']} (page {result['page']})")
        print(f"   Text: {result['text'][:100]}...")
    
    # Test format
    context = tool.format_results_for_context(results, max_results=3)
    print(f"\n\nFormatted context:\n{context[:300]}...")


if __name__ == "__main__":
    test_search_tool()
