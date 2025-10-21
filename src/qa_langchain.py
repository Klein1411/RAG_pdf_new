"""
QA App - LangChain RAG Version

Thay thế src/qa_app.py bằng LangChain RetrievalQA chain.
Giữ nguyên tất cả tính năng:
- Context expansion (pages ±1-2)
- Multi-source tracking
- Gemini/Ollama support
- Error handling
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# LangChain imports
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings

# Local imports
from src.config import EMBEDDING_MODEL_NAME, COLLECTION_NAME
from src.llm_langchain import LLMManager, initialize_and_select_llm_langchain
from src.logging_config import get_logger

logger = get_logger(__name__)


class RAGChain:
    """
    LangChain-based RAG với context expansion.
    
    Features:
    - RetrievalQA pattern
    - Context expansion (±1-2 pages)
    - Source tracking
    - Custom prompt templates
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        collection_name: str = COLLECTION_NAME,
        embedding_model_name: str = EMBEDDING_MODEL_NAME
    ):
        """
        Initialize RAG chain.
        
        Args:
            llm_manager: LangChain LLM manager
            collection_name: Milvus collection name
            embedding_model_name: HuggingFace model name
        """
        self.llm_manager = llm_manager
        self.collection_name = collection_name
        
        logger.info(f"🤖 Loading embedding model: {embedding_model_name}")
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs={'device': 'cuda'},  # Use GPU if available
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize Milvus vectorstore
        logger.info(f"🔌 Connecting to Milvus collection: {collection_name}")
        self.vectorstore = Milvus(
            embedding_function=self.embeddings,
            collection_name=collection_name,
            connection_args={
                "host": "localhost",
                "port": "19530"
            },
            drop_old=False  # Don't recreate
        )
        
        # Build chain
        self._build_chain()
        
        logger.info("✅ RAG chain initialized")
    
    def _build_chain(self):
        """Build LangChain RAG chain with custom prompt."""
        
        # Custom prompt template
        template = """Dựa vào các thông tin được cung cấp dưới đây từ tài liệu PDF:

{context}

Hãy trả lời câu hỏi sau một cách chi tiết và chính xác. 
Chỉ sử dụng thông tin được cung cấp, không bịa đặt. 
Nếu thông tin không đủ để trả lời, hãy nói rằng "Thông tin không có trong tài liệu".

Câu hỏi: {question}

Câu trả lời:"""
        
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
        
        # Build retriever
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 15}  # Top 15 results
        )
        
        # Build chain based on provider
        # Gemini: Không support LangChain chains → dùng manual approach
        # Ollama: Support LangChain chains → dùng chain pipeline
        if self.llm_manager.provider == "gemini":
            logger.info("ℹ️ Gemini provider: Sẽ dùng manual retrieval + generate()")
            self.chain = None  # Không dùng chain, xử lý manual trong answer_question()
        else:
            # Ollama: Build full chain
            logger.info("ℹ️ Ollama provider: Build LangChain chain")
            self.chain = (
                {
                    "context": self.retriever | self._format_docs,
                    "question": RunnablePassthrough()
                }
                | self.prompt
                | self.llm_manager.get_langchain_llm()
                | StrOutputParser()
            )
    
    def _format_docs(self, docs):
        """
        Format retrieved documents with context expansion.
        
        Expands context by ±1-2 pages like original qa_app.py
        """
        if not docs:
            return ""
        
        # Get pages from initial results
        hit_pages = sorted(list(set([
            doc.metadata.get('page', 0) for doc in docs
        ])))
        
        logger.info(f"📄 Hit pages: {hit_pages}")
        
        if not hit_pages:
            # Fallback: concatenate docs
            return "\n\n".join([doc.page_content for doc in docs])
        
        # Expand context: ±1-2 pages
        min_page = min(hit_pages)
        max_page = max(hit_pages)
        context_min = max(1, min_page - 1)
        context_max = max_page + 2
        
        logger.info(f"📚 Expanding context: pages {context_min}-{context_max}")
        
        # Query expanded pages from Milvus
        try:
            from pymilvus import connections, Collection
            
            # Use existing connection
            if not connections.has_connection("default"):
                connections.connect(
                    alias="default",
                    host="localhost",
                    port="19530"
                )
            
            collection = Collection(self.collection_name)
            
            # Query by page range
            expr = f"page >= {context_min} && page <= {context_max}"
            expanded_results = collection.query(
                expr=expr,
                output_fields=["text", "page"],
                limit=1000
            )
            
            logger.info(f"📖 Retrieved {len(expanded_results)} chunks from expanded range")
            
            # Group by page
            context_map = {}
            for hit in expanded_results:
                page_num = hit.get('page', 0)
                text = hit.get('text', '')
                if page_num not in context_map:
                    context_map[page_num] = []
                context_map[page_num].append(text)
            
            # Build final context
            final_context = ""
            for page_num in sorted(context_map.keys()):
                final_context += f"--- Nội dung từ Trang {page_num} ---\n"
                final_context += "\n".join(context_map[page_num]) + "\n\n"
            
            return final_context if final_context else "\n\n".join([doc.page_content for doc in docs])
            
        except Exception as e:
            logger.warning(f"⚠️  Context expansion failed: {e}")
            # Fallback to simple concatenation
            return "\n\n".join([doc.page_content for doc in docs])
    
    def ask(self, question: str) -> dict:
        """
        Ask a question and get answer with sources.
        
        Args:
            question: User question
            
        Returns:
            {
                'answer': str,
                'sources': List[str],
                'pages': List[int]
            }
        """
        logger.info(f"❓ Question: {question[:100]}...")
        
        try:
            # Retrieve documents first for source tracking
            docs = self.retriever.get_relevant_documents(question)
            
            if not docs:
                logger.warning("No relevant documents found")
                return {
                    'answer': "⚠️ Không tìm thấy thông tin liên quan trong tài liệu.",
                    'sources': [],
                    'pages': []
                }
            
            # Generate answer based on provider
            if self.chain is not None:
                # Ollama: Dùng LangChain chain
                answer = self.chain.invoke(question)
            else:
                # Gemini: Manual retrieval + generate()
                # Format context từ retrieved docs
                context = self._format_docs(docs)
                
                # Build prompt manually
                prompt_text = f"""Dựa vào các thông tin được cung cấp dưới đây từ tài liệu PDF:

{context}

Hãy trả lời câu hỏi sau một cách chi tiết và chính xác. 
Chỉ sử dụng thông tin được cung cấp, không bịa đặt. 
Nếu thông tin không đủ để trả lời, hãy nói rằng "Thông tin không có trong tài liệu".

Câu hỏi: {question}

Câu trả lời:"""
                
                # Generate với Gemini
                answer = self.llm_manager.generate(prompt_text)
            
            # Extract sources
            sources = []
            pages = set()
            for doc in docs[:15]:  # Top 15 for source display
                source = doc.metadata.get('pdf_source', 'Unknown')
                page = doc.metadata.get('page', 0)
                pages.add(page)
                if source not in sources:
                    sources.append(source)
            
            logger.info(f"✅ Generated answer with {len(sources)} sources")
            
            return {
                'answer': answer,
                'sources': sources,
                'pages': sorted(list(pages))
            }
            
        except Exception as e:
            logger.error(f"❌ Error during QA: {e}")
            return {
                'answer': f"[LỖI HỆ THỐNG] {str(e)}",
                'sources': [],
                'pages': []
            }


def main():
    """Main QA application."""
    logger.info("=== Starting LangChain RAG QA App ===")
    print("=" * 70)
    print("🚀 LANGCHAIN RAG QA APPLICATION")
    print("=" * 70)
    
    # Step 1: Initialize LLM
    print("\n📋 Step 1: Select LLM Provider")
    model_choice, llm_manager = initialize_and_select_llm_langchain()
    
    print(f"\n✅ LLM initialized:")
    info = llm_manager.get_info()
    print(f"   Provider: {info['provider']}")
    print(f"   Model: {info['model']}")
    
    # Step 2: Initialize RAG chain
    print("\n📋 Step 2: Initialize RAG Chain")
    try:
        rag_chain = RAGChain(
            llm_manager=llm_manager,
            collection_name=COLLECTION_NAME
        )
        print("✅ RAG chain ready!")
    except Exception as e:
        logger.error(f"Failed to initialize RAG chain: {e}")
        print(f"\n❌ Failed to initialize: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Milvus running (localhost:19530)")
        print("   2. Collection populated (run populate_milvus.py)")
        return
    
    # Step 3: QA Loop
    print("\n📋 Step 3: Ask Questions")
    print("=" * 70)
    print("Type 'exit' to quit, 'info' for help")
    print("=" * 70)
    
    try:
        while True:
            question = input("\n❓ Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() == 'exit':
                logger.info("User ended session")
                break
            
            if question.lower() == 'info':
                print("\n📖 RAG QA Help:")
                print("   - Ask questions about your documents")
                print("   - Context automatically expanded (±1-2 pages)")
                print("   - Sources tracked and displayed")
                print("   - Type 'exit' to quit")
                continue
            
            # Ask question
            print("\n🔍 Searching...")
            result = rag_chain.ask(question)
            
            # Display answer
            print("\n✅ Answer:")
            print("-" * 70)
            print(result['answer'])
            print("-" * 70)
            
            # Display sources
            if result['sources'] and result['pages']:
                print(f"\n📚 Sources:")
                for source in result['sources']:
                    print(f"   📄 {source}")
                print(f"   📖 Pages: {', '.join(map(str, result['pages']))}")
    
    except KeyboardInterrupt:
        logger.info("User interrupted (Ctrl+C)")
        print("\n\n👋 Interrupted by user")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Error: {e}")
    
    finally:
        print("\n" + "=" * 70)
        print("👋 Thank you for using LangChain RAG QA!")
        print("=" * 70)


if __name__ == "__main__":
    main()
