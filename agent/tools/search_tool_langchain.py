# coding: utf-8
"""
Search Tool - Phiên bản LangChain
Tool tìm kiếm trong nhiều collection với giao diện LangChain Tool

Migration từ search_tool.py:
- Giữ nguyên core logic (SentenceTransformer + Milvus)
- Thêm LangChain Tool decorator và interface
- Tương thích với LangGraph agents
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Annotated
import json

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import torch
from pymilvus import Collection
from sentence_transformers import SentenceTransformer

# LangChain imports
from langchain_core.tools import tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import EMBEDDING_MODEL_NAME
from src.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Pydantic schemas cho tool inputs
# ============================================================================

class SearchInput(BaseModel):
    """Input schema cho search_collections tool."""
    query: str = Field(description="Câu hỏi hoặc từ khóa tìm kiếm")
    collection_names: List[str] = Field(description="Danh sách tên các collection cần search")
    top_k: int = Field(default=15, description="Số lượng kết quả mỗi collection")
    similarity_threshold: float = Field(default=0.15, description="Ngưỡng độ tương đồng tối thiểu (0-1)")


class SearchSingleInput(BaseModel):
    """Input schema cho search_single_collection tool."""
    query: str = Field(description="Câu hỏi hoặc từ khóa tìm kiếm")
    collection_name: str = Field(description="Tên collection cần search")
    top_k: int = Field(default=15, description="Số lượng kết quả trả về")
    similarity_threshold: float = Field(default=0.15, description="Ngưỡng độ tương đồng tối thiểu (0-1)")


# ============================================================================
# Core SearchTool class (giữ nguyên logic cũ)
# ============================================================================

class SearchToolLangChain:
    """
    Vector search tool với giao diện LangChain.
    
    Có thể dùng như:
    1. Standalone class (backward compatible)
    2. LangChain tools qua get_langchain_tools()
    """
    
    def __init__(self, embedding_model: Optional[SentenceTransformer] = None):
        """
        Args:
            embedding_model: Model SentenceTransformer đã load sẵn (tùy chọn)
        """
        self.name = "search_tool_langchain"
        self.description = "Tìm kiếm trong nhiều PDF collection bằng vector similarity"
        
        # Dùng model được truyền vào hoặc load mới
        if embedding_model:
            self.embedding_model = embedding_model
        else:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME).to(device)
            logger.info(f"🔧 Đã load embedding model trên {device}")
    
    def search_multi_collections(
        self,
        query: str,
        collection_names: List[str],
        top_k: int = 15,
        similarity_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trong nhiều collections.
        
        Args:
            query: Câu hỏi tìm kiếm
            collection_names: Danh sách tên collections
            top_k: Số kết quả tối đa mỗi collection
            similarity_threshold: Ngưỡng similarity tối thiểu
            
        Returns:
            List kết quả đã sort theo score
        """
        logger.info(f"🔍 Đang search trong {len(collection_names)} collections: {collection_names}")
        
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
                
                # Execute search
                results = collection.search(
                    data=[query_vector.tolist()],
                    anns_field="embedding",
                    param=search_params,
                    limit=top_k,
                    output_fields=["text", "page", "pdf_source"]
                )
                
                # Process results
                for hit in results[0]:
                    score = 1.0 / (1.0 + hit.distance)  # Chuyển L2 distance sang similarity
                    
                    if score >= similarity_threshold:
                        all_results.append({
                            'text': hit.entity.get('text'),
                            'page': hit.entity.get('page'),
                            'pdf_source': hit.entity.get('pdf_source'),
                            'collection': col_name,
                            'score': score,
                            'distance': hit.distance
                        })
                
                logger.debug(f"✅ Tìm thấy {len([r for r in results[0] if 1.0/(1.0+r.distance) >= similarity_threshold])} kết quả trong {col_name}")
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi search collection {col_name}: {e}")
                continue
        
        # Sort theo score giảm dần
        all_results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"📊 Tổng số kết quả: {len(all_results)}")
        return all_results
    
    def search_single_collection(
        self,
        query: str,
        collection_name: str,
        top_k: int = 15,
        similarity_threshold: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm trong một collection (convenience method).
        
        Args:
            query: Câu hỏi tìm kiếm
            collection_name: Tên collection
            top_k: Số kết quả tối đa
            similarity_threshold: Ngưỡng similarity tối thiểu
            
        Returns:
            List kết quả đã sort theo score
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
        max_results: Optional[int] = None
    ) -> str:
        """
        Format search results thành context string cho LLM.
        
        Args:
            results: List kết quả từ search_multi_collections
            max_results: Số lượng kết quả tối đa (None = tất cả)
            
        Returns:
            Context string đã format sẵn
        """
        if not results:
            return "Không tìm thấy thông tin liên quan."
        
        # Limit results if specified
        if max_results:
            results = results[:max_results]
        
        # Format mỗi result thành text block
        context_parts = []
        for i, result in enumerate(results, 1):
            text = result.get('text', '')
            source = result.get('pdf_source', 'Unknown')
            page = result.get('page', 'N/A')
            collection = result.get('collection', 'N/A')
            score = result.get('score', 0.0)
            
            context_parts.append(
                f"[{i}] (Score: {score:.3f})\n"
                f"Source: {source} (Page {page}, Collection: {collection})\n"
                f"{text}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def get_langchain_tools(self) -> List[BaseTool]:
        """
        Lấy LangChain tools để dùng trong agent.
        
        Returns:
            List chứa 2 LangChain tools
        """
        # Tạo tools với quyền truy cập self
        tools = []
        
        # Tool 1: Search nhiều collections
        @tool(args_schema=SearchInput)
        def search_collections(
            query: str,
            collection_names: List[str],
            top_k: int = 15,
            similarity_threshold: float = 0.15
        ) -> str:
            """Search for relevant documents across multiple PDF collections.
            
            Use this when you need to find information from specific collections.
            Returns top matching text chunks with their sources and scores.
            """
            results = self.search_multi_collections(
                query=query,
                collection_names=collection_names,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Format thành JSON string cho LLM
            return json.dumps({
                "total_results": len(results),
                "results": results[:20]  # Giới hạn top 20 để tiết kiệm context
            }, ensure_ascii=False, indent=2)
        
        # Tool 2: Search một collection
        @tool(args_schema=SearchSingleInput)
        def search_single_collection(
            query: str,
            collection_name: str,
            top_k: int = 15,
            similarity_threshold: float = 0.15
        ) -> str:
            """Search for relevant documents in a single PDF collection.
            
            Use this when you know the specific collection to search.
            Faster than multi-collection search.
            """
            results = self.search_single_collection(
                query=query,
                collection_name=collection_name,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Format thành JSON string cho LLM
            return json.dumps({
                "total_results": len(results),
                "results": results[:20]
            }, ensure_ascii=False, indent=2)
        
        tools.append(search_collections)
        tools.append(search_single_collection)
        
        return tools


# ============================================================================
# Standalone tool functions (để dùng độc lập, không cần khởi tạo class)
# ============================================================================

# Global instance (lazy loaded)
_global_search_tool: Optional[SearchToolLangChain] = None

def get_global_search_tool() -> SearchToolLangChain:
    """Lấy hoặc tạo global SearchToolLangChain instance (singleton)."""
    global _global_search_tool
    if _global_search_tool is None:
        _global_search_tool = SearchToolLangChain()
    return _global_search_tool


@tool(args_schema=SearchInput)
def search_collections_tool(
    query: str,
    collection_names: List[str],
    top_k: int = 15,
    similarity_threshold: float = 0.15
) -> str:
    """Search for relevant documents across multiple PDF collections.
    
    Use this when you need to find information from multiple collections.
    Returns top matching text chunks with their sources and scores.
    
    Args:
        query: Câu hỏi hoặc query tìm kiếm
        collection_names: Danh sách tên các collections cần search
        top_k: Số kết quả tối đa mỗi collection (mặc định 15)
        similarity_threshold: Ngưỡng similarity tối thiểu 0-1 (mặc định 0.15)
    """
    tool = get_global_search_tool()
    results = tool.search_multi_collections(
        query=query,
        collection_names=collection_names,
        top_k=top_k,
        similarity_threshold=similarity_threshold
    )
    
    return json.dumps({
        "total_results": len(results),
        "results": results[:20]
    }, ensure_ascii=False, indent=2)


# ============================================================================
# Backward compatibility (tương thích với code cũ)
# ============================================================================

# Alias để code cũ vẫn chạy được
SearchTool = SearchToolLangChain


if __name__ == "__main__":
    """Script test nhanh"""
    print("=" * 70)
    print("🧪 Testing SearchToolLangChain")
    print("=" * 70)
    
    # Test 1: Tạo tool
    print("\n1️⃣ Đang tạo SearchToolLangChain...")
    search_tool = SearchToolLangChain()
    print(f"   ✅ Đã tạo: {search_tool.name}")
    
    # Test 2: Lấy LangChain tools
    print("\n2️⃣ Lấy LangChain tools...")
    tools = search_tool.get_langchain_tools()
    print(f"   ✅ Có {len(tools)} tools:")
    for tool in tools:
        print(f"      - {tool.name}: {tool.description[:60]}...")
    
    # Test 3: Standalone tool
    print("\n3️⃣ Test standalone tool...")
    print(f"   ✅ search_collections_tool: {search_collections_tool.name}")
    
    print("\n" + "=" * 70)
    print("✅ Tất cả tests passed!")
    print("=" * 70)
