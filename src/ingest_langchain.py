"""
Document Ingestion - LangChain Version

Thay thế populate_milvus.py bằng LangChain document loaders.
Giữ nguyên tất cả tính năng:
- PDF parsing
- Chunking with overlap
- Metadata tracking (page, source)
- Milvus vectorstore
"""

import sys
from pathlib import Path
from typing import List, Optional

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# Local imports
from src.config import (
    EMBEDDING_MODEL_NAME,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)
from src.logging_config import get_logger

logger = get_logger(__name__)


class DocumentIngestion:
    """
    LangChain-based document ingestion pipeline.
    
    Features:
    - PDF loading with PyPDFLoader
    - Recursive text splitting
    - Metadata preservation
    - Milvus vectorstore
    """
    
    def __init__(
        self,
        collection_name: str = COLLECTION_NAME,
        embedding_model_name: str = EMBEDDING_MODEL_NAME,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            collection_name: Milvus collection name
            embedding_model_name: HuggingFace model name
            chunk_size: Max characters per chunk
            chunk_overlap: Overlap between chunks
        """
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(f"🤖 Loading embedding model: {embedding_model_name}")
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name,
            model_kwargs={'device': 'cuda'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        logger.info(f"✅ Ingestion pipeline initialized")
        logger.info(f"   Chunk size: {chunk_size}")
        logger.info(f"   Overlap: {chunk_overlap}")
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """
        Load single PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of Document objects
        """
        logger.info(f"📄 Loading PDF: {pdf_path}")
        
        try:
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            # Add pdf_source metadata
            pdf_name = Path(pdf_path).name
            for doc in documents:
                doc.metadata['pdf_source'] = pdf_name
            
            logger.info(f"✅ Loaded {len(documents)} pages from {pdf_name}")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Failed to load {pdf_path}: {e}")
            return []
    
    def load_directory(self, directory_path: str) -> List[Document]:
        """
        Load all PDFs from directory.
        
        Args:
            directory_path: Path to directory with PDFs
            
        Returns:
            List of Document objects
        """
        logger.info(f"📁 Loading PDFs from: {directory_path}")
        
        try:
            loader = DirectoryLoader(
                directory_path,
                glob="**/*.pdf",
                loader_cls=PyPDFLoader,
                show_progress=True
            )
            documents = loader.load()
            
            # Add pdf_source metadata
            for doc in documents:
                if 'source' in doc.metadata:
                    pdf_name = Path(doc.metadata['source']).name
                    doc.metadata['pdf_source'] = pdf_name
            
            logger.info(f"✅ Loaded {len(documents)} pages from directory")
            return documents
            
        except Exception as e:
            logger.error(f"❌ Failed to load directory {directory_path}: {e}")
            return []
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of chunked Document objects
        """
        logger.info(f"✂️  Splitting {len(documents)} documents...")
        
        chunks = self.text_splitter.split_documents(documents)
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        logger.info(f"   Avg chunk size: {sum(len(c.page_content) for c in chunks) // len(chunks)} chars")
        
        return chunks
    
    def ingest_to_milvus(
        self,
        chunks: List[Document],
        drop_old: bool = False
    ) -> Milvus:
        """
        Ingest chunks to Milvus vectorstore.
        
        Args:
            chunks: List of chunked documents
            drop_old: Whether to drop existing collection
            
        Returns:
            Milvus vectorstore instance
        """
        logger.info(f"📤 Ingesting {len(chunks)} chunks to Milvus...")
        logger.info(f"   Collection: {self.collection_name}")
        logger.info(f"   Drop old: {drop_old}")
        
        try:
            vectorstore = Milvus.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                collection_name=self.collection_name,
                connection_args={
                    "host": "localhost",
                    "port": "19530"
                },
                drop_old=drop_old
            )
            
            logger.info(f"✅ Successfully ingested to Milvus")
            return vectorstore
            
        except Exception as e:
            logger.error(f"❌ Failed to ingest to Milvus: {e}")
            raise
    
    def ingest_pdf(
        self,
        pdf_path: str,
        drop_old: bool = False
    ) -> Optional[Milvus]:
        """
        Complete pipeline: Load PDF → Split → Ingest.
        
        Args:
            pdf_path: Path to PDF file
            drop_old: Whether to drop existing collection
            
        Returns:
            Milvus vectorstore or None if failed
        """
        # Load
        documents = self.load_pdf(pdf_path)
        if not documents:
            return None
        
        # Split
        chunks = self.split_documents(documents)
        
        # Ingest
        vectorstore = self.ingest_to_milvus(chunks, drop_old=drop_old)
        
        return vectorstore
    
    def ingest_directory(
        self,
        directory_path: str,
        drop_old: bool = False
    ) -> Optional[Milvus]:
        """
        Complete pipeline: Load directory → Split → Ingest.
        
        Args:
            directory_path: Path to directory with PDFs
            drop_old: Whether to drop existing collection
            
        Returns:
            Milvus vectorstore or None if failed
        """
        # Load
        documents = self.load_directory(directory_path)
        if not documents:
            return None
        
        # Split
        chunks = self.split_documents(documents)
        
        # Ingest
        vectorstore = self.ingest_to_milvus(chunks, drop_old=drop_old)
        
        return vectorstore


def main():
    """Main ingestion CLI."""
    import argparse
    
    logger.info("=== Starting LangChain Document Ingestion ===")
    print("=" * 70)
    print("📚 LANGCHAIN DOCUMENT INGESTION")
    print("=" * 70)
    
    # Parse args
    parser = argparse.ArgumentParser(description="Ingest PDFs to Milvus using LangChain")
    parser.add_argument(
        "path",
        type=str,
        help="Path to PDF file or directory"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing collection before ingestion"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=COLLECTION_NAME,
        help=f"Collection name (default: {COLLECTION_NAME})"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        help=f"Chunk size (default: {CHUNK_SIZE})"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=CHUNK_OVERLAP,
        help=f"Chunk overlap (default: {CHUNK_OVERLAP})"
    )
    
    args = parser.parse_args()
    
    # Validate path
    path = Path(args.path)
    if not path.exists():
        print(f"\n❌ Path not found: {args.path}")
        return
    
    # Initialize pipeline
    print(f"\n📋 Configuration:")
    print(f"   Collection: {args.collection}")
    print(f"   Chunk size: {args.chunk_size}")
    print(f"   Chunk overlap: {args.chunk_overlap}")
    print(f"   Drop old: {args.drop}")
    
    ingestion = DocumentIngestion(
        collection_name=args.collection,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    # Ingest
    print(f"\n🚀 Starting ingestion from: {args.path}")
    print("-" * 70)
    
    try:
        if path.is_file():
            vectorstore = ingestion.ingest_pdf(
                str(path),
                drop_old=args.drop
            )
        else:
            vectorstore = ingestion.ingest_directory(
                str(path),
                drop_old=args.drop
            )
        
        if vectorstore:
            print("-" * 70)
            print(f"\n✅ Ingestion complete!")
            print(f"   Collection: {args.collection}")
            print(f"   Ready for queries")
        else:
            print(f"\n❌ Ingestion failed")
    
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure:")
        print("   1. Milvus is running (localhost:19530)")
        print("   2. PDF files are valid")
        print("   3. Enough disk space available")


if __name__ == "__main__":
    main()


# ===== COMPATIBILITY FUNCTIONS FOR AGENT =====
# These functions provide backward compatibility with the old populate_milvus.py API

def get_embedding_model():
    """
    Get embedding model for backward compatibility with agent/collection_manager.py
    
    Returns:
        SentenceTransformer model
    """
    from sentence_transformers import SentenceTransformer
    from src.config import EMBEDDING_MODEL_NAME
    
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return model


def chunk_text(text: str, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None) -> list:
    """
    Chunk text using LangChain text splitter for backward compatibility.
    
    Args:
        text: Text to chunk
        chunk_size: Max characters per chunk (default from config)
        chunk_overlap: Overlap between chunks (default from config)
        
    Returns:
        List of text chunks
    """
    from src.config import CHUNK_SIZE, CHUNK_OVERLAP
    
    chunk_size = chunk_size or CHUNK_SIZE
    chunk_overlap = chunk_overlap or CHUNK_OVERLAP
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    return chunks
