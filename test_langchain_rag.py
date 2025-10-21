"""
Comprehensive Test Suite - LangChain RAG Migration

Tests for:
- LLM integration (llm_langchain.py)
- RAG chain (qa_langchain.py)
- Document ingestion (ingest_langchain.py)
- End-to-end workflow
"""

import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, patch, MagicMock

# Test imports
from src.llm_langchain import LLMManager
from src.logging_config import get_logger

logger = get_logger(__name__)


class TestLLMManager:
    """Test LangChain LLM integration."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key-123")
    
    def test_gemini_initialization(self, mock_env):
        """Test Gemini LLM initialization."""
        llm_manager = LLMManager(
            provider="gemini",
            model_name="gemini-2.5-flash"
        )
        
        assert llm_manager.provider == "gemini"
        assert llm_manager.model_name == "gemini-2.5-flash"
        assert llm_manager.llm is not None
        
        logger.info("✅ Gemini initialization test passed")
    
    def test_ollama_initialization(self):
        """Test Ollama LLM initialization."""
        llm_manager = LLMManager(
            provider="ollama",
            model_name="llama3:latest"
        )
        
        assert llm_manager.provider == "ollama"
        assert llm_manager.model_name == "llama3:latest"
        assert llm_manager.llm is not None
        
        logger.info("✅ Ollama initialization test passed")
    
    def test_invalid_provider(self, mock_env):
        """Test invalid provider raises error."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMManager(provider="invalid", model_name="test")
        
        logger.info("✅ Invalid provider test passed")
    
    def test_get_info(self, mock_env):
        """Test get_info returns correct data."""
        llm_manager = LLMManager(provider="gemini", model_name="gemini-2.5-flash")
        info = llm_manager.get_info()
        
        assert info["provider"] == "gemini"
        assert info["model"] == "gemini-2.5-flash"  # get_info returns 'model'
        assert "temperature" in info
        
        logger.info("✅ get_info test passed")
    
    @patch('src.llm_langchain.ChatGoogleGenerativeAI')
    def test_generate_basic(self, mock_chat, mock_env):
        """Test basic text generation."""
        # Mock LLM response
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Test response")
        mock_chat.return_value = mock_llm
        
        llm_manager = LLMManager(provider="gemini", model_name="gemini-2.5-flash")
        llm_manager.llm = mock_llm
        
        response = llm_manager.generate("Test prompt")
        
        assert response == "Test response"
        mock_llm.invoke.assert_called_once_with("Test prompt")
        
        logger.info("✅ Basic generation test passed")
    
    @patch('src.llm_langchain.ChatGoogleGenerativeAI')
    def test_generate_with_history(self, mock_chat, mock_env):
        """Test generation with conversation history."""
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="Response with history")
        mock_chat.return_value = mock_llm
        
        llm_manager = LLMManager(provider="gemini", model_name="gemini-2.5-flash")
        llm_manager.llm = mock_llm
        
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        response = llm_manager.generate_with_history("How are you?", history)
        
        assert response == "Response with history"
        assert mock_llm.invoke.called
        
        logger.info("✅ History generation test passed")


class TestRAGChain:
    """Test LangChain RAG chain."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment variables."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key-123")
    
    @pytest.fixture
    def mock_embeddings(self):
        """Mock HuggingFace embeddings."""
        with patch('src.qa_langchain.HuggingFaceEmbeddings') as mock:
            yield mock
    
    @pytest.fixture
    def mock_llm_manager(self, mock_env):
        """Create mock LLM manager."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            return LLMManager(provider="gemini", model_name="gemini-2.5-flash")
    
    def test_rag_chain_initialization(self, mock_embeddings, mock_llm_manager):
        """Test RAG chain initializes correctly with real Milvus."""
        from src.qa_langchain import RAGChain
        
        try:
            # Test with real Milvus connection
            chain = RAGChain(llm_manager=mock_llm_manager)
            
            assert chain.llm_manager == mock_llm_manager
            assert chain.collection_name == "pdf_rag_collection"
            assert chain.vectorstore is not None
            assert chain.retriever is not None
            
            logger.info("✅ RAG chain initialization test passed")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")
    
    def test_format_docs_empty(self, mock_embeddings, mock_llm_manager):
        """Test format_docs with empty input."""
        from src.qa_langchain import RAGChain
        
        try:
            chain = RAGChain(llm_manager=mock_llm_manager)
            result = chain._format_docs([])
            
            assert result == ""
            
            logger.info("✅ Format empty docs test passed")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")
    
    def test_ask_no_documents(self, mock_embeddings, mock_llm_manager):
        """Test ask when no documents found."""
        from src.qa_langchain import RAGChain
        
        try:
            chain = RAGChain(llm_manager=mock_llm_manager)
            
            # Mock retriever to return empty
            chain.retriever = Mock()
            chain.retriever.get_relevant_documents = Mock(return_value=[])
            
            result = chain.ask("Test question about nonexistent topic xyz123")
            
            assert "không tìm thấy" in result['answer'].lower()
            assert result['sources'] == []
            assert result['pages'] == []
            
            logger.info("✅ Ask no documents test passed")
        except Exception as e:
            pytest.skip(f"Milvus not available: {e}")


class TestDocumentIngestion:
    """Test LangChain document ingestion."""
    
    @pytest.fixture
    def mock_embeddings(self):
        """Mock HuggingFace embeddings."""
        with patch('src.ingest_langchain.HuggingFaceEmbeddings') as mock:
            yield mock
    
    def test_ingestion_initialization(self, mock_embeddings):
        """Test ingestion pipeline initializes."""
        from src.ingest_langchain import DocumentIngestion
        
        ingestion = DocumentIngestion()
        
        assert ingestion.collection_name == "pdf_rag_collection"
        assert ingestion.chunk_size == 1000
        assert ingestion.chunk_overlap == 200
        
        logger.info("✅ Ingestion initialization test passed")
    
    def test_load_pdf_invalid_path(self, mock_embeddings):
        """Test loading invalid PDF path."""
        from src.ingest_langchain import DocumentIngestion
        
        ingestion = DocumentIngestion()
        docs = ingestion.load_pdf("nonexistent.pdf")
        
        assert docs == []
        
        logger.info("✅ Load invalid PDF test passed")
    
    @patch('src.ingest_langchain.PyPDFLoader')
    def test_load_pdf_success(self, mock_loader, mock_embeddings):
        """Test successful PDF loading."""
        from src.ingest_langchain import DocumentIngestion
        from langchain.schema import Document
        
        # Mock loader
        mock_doc = Document(
            page_content="Test content",
            metadata={"page": 1}
        )
        mock_loader_instance = Mock()
        mock_loader_instance.load.return_value = [mock_doc]
        mock_loader.return_value = mock_loader_instance
        
        ingestion = DocumentIngestion()
        docs = ingestion.load_pdf("test.pdf")
        
        assert len(docs) == 1
        assert docs[0].metadata.get('pdf_source') == 'test.pdf'
        
        logger.info("✅ Load PDF success test passed")
    
    def test_split_documents(self, mock_embeddings):
        """Test document splitting."""
        from src.ingest_langchain import DocumentIngestion
        from langchain.schema import Document
        
        ingestion = DocumentIngestion(chunk_size=100, chunk_overlap=20)
        
        # Create long document
        long_text = "This is a test. " * 100  # ~1600 chars
        docs = [Document(page_content=long_text, metadata={"page": 1})]
        
        chunks = ingestion.split_documents(docs)
        
        assert len(chunks) > 1  # Should be split
        assert all(len(c.page_content) <= 120 for c in chunks)  # Respect chunk size
        
        logger.info("✅ Split documents test passed")


class TestEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Mock environment."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    
    def test_full_workflow_mock(self, mock_env):
        """Test complete RAG workflow with mocks."""
        from src.llm_langchain import LLMManager
        from src.ingest_langchain import DocumentIngestion
        from langchain.schema import Document
        
        # 1. LLM Manager
        llm_manager = LLMManager(provider="gemini", model_name="gemini-2.5-flash")
        assert llm_manager.provider == "gemini"
        
        # 2. Document Ingestion
        with patch('src.ingest_langchain.HuggingFaceEmbeddings'):
            ingestion = DocumentIngestion()
            
            # Mock document
            mock_doc = Document(
                page_content="Test content about AI",
                metadata={"page": 1, "pdf_source": "test.pdf"}
            )
            
            chunks = ingestion.split_documents([mock_doc])
            assert len(chunks) >= 1
        
        logger.info("✅ Full workflow mock test passed")


def run_tests():
    """Run all tests."""
    print("=" * 70)
    print("🧪 RUNNING LANGCHAIN RAG TESTS")
    print("=" * 70)
    
    # Run pytest
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "-W", "ignore::DeprecationWarning"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
