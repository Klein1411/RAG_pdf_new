# coding: utf-8
"""
Main Agent - Agent RAG với kiến trúc Tool-based
Tính năng:
- Chọn PDF và collection linh hoạt
- Export MD hàng loạt (batch)
- RAG workflow với RagTool
- Phát hiện ý định (intent detection)
- Tìm kiếm đa collection (SearchTool)
- Gợi ý topics (TopicTool)
- Export to MD (ExportTool)
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Thêm project root vào path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.config import AGENT_NAME, AGENT_DESCRIPTION, MAX_CONVERSATION_HISTORY
from agent.pdf_manager import get_pdf_manager
from agent.collection_manager import get_collection_manager
from agent.intent_classifier import get_intent_classifier
from agent.topic_suggester import get_topic_suggester
from agent.conversation_history import ConversationHistory
from agent.intent_detector import IntentDetector

# Import tools
from agent.tools.search_tool import get_search_tool
from agent.tools.topic_tool import get_topic_tool
from agent.tools.export_tool import get_export_tool
from agent.tools.rag_tool import get_rag_tool
from agent.tools.collection_tool import get_collection_tool
from agent.tools.setup_tool import get_setup_tool

# Import export function
from src.export_md import convert_to_markdown

from src.logging_config import get_logger

logger = get_logger(__name__)


class Agent:
    """Agent chính hỗ trợ nhiều PDF và nhiều collection"""
    
    def __init__(self, name: str = "Agent", auto_setup: bool = False):
        """
        Khởi tạo Agent với các thành phần cần thiết
        
        Args:
            name: Tên của agent
            auto_setup: Nếu True, sẽ tự động chạy setup() sau khi khởi tạo
        """
        self.name = name
        self.pdf_manager = get_pdf_manager()  # Quản lý file PDF
        self.collection_manager = get_collection_manager()  # Quản lý collection trong Milvus
        self.intent_classifier = get_intent_classifier()  # Phân loại câu hỏi (PDF hay chat)
        self.topic_suggester = get_topic_suggester()  # Đề xuất chủ đề từ tài liệu
        
        # Conversation and intent management
        self.conversation_history = ConversationHistory(max_messages=MAX_CONVERSATION_HISTORY)
        self.intent_detector = IntentDetector()
        
        # Initialize tools (lazy loading)
        self.search_tool = None  # SearchTool - sẽ được khởi tạo khi cần embedding
        self.topic_tool = get_topic_tool(self.topic_suggester)  # TopicTool
        self.export_tool = get_export_tool()  # ExportTool
        self.rag_tool = None  # RagTool - sẽ được khởi tạo sau khi có LLM
        self.collection_tool = None  # CollectionTool - quản lý collections
        self.setup_tool = None  # SetupTool - xử lý setup workflow
        
        self.llm_client = None  # Client LLM (Gemini/Ollama)
        self.llm_type = None  # Loại LLM đang dùng
        self.ollama_model = None  # Tên model Ollama nếu dùng Ollama
        self.initialized = False  # Trạng thái khởi tạo
        
        self.selected_pdfs = []  # Danh sách PDF đã chọn
        self.selected_collections = []  # Danh sách collection đã chọn
        
        # Auto setup if requested
        if auto_setup:
            logger.info("🚀 Auto setup enabled, running setup...")
            try:
                self.setup()
                if self.initialized:
                    logger.info("✅ Auto setup completed successfully")
                else:
                    logger.warning("⚠️  Auto setup completed but agent not initialized")
            except Exception as e:
                logger.error(f"❌ Auto setup failed: {e}")
                raise
    
    def _ensure_llm_initialized(self):
        """Khởi tạo LLM client nếu chưa có"""
        if self.llm_client is None:
            logger.info("Initializing LLM client...")
            from src.llm_handler import initialize_and_select_llm
            try:
                # initialize_and_select_llm trả về (model_choice, gemini_client, ollama_model_name)
                # model_choice: "1" (Gemini) hoặc "2" (Ollama)
                model_choice, gemini_client, ollama_model = initialize_and_select_llm()
                
                if model_choice == '1':
                    # Gemini
                    self.llm_client = gemini_client
                    self.llm_type = 'gemini'
                elif model_choice == '2':
                    # Ollama - cần import client
                    from ollama import Client
                    self.llm_client = Client()
                    self.llm_type = 'ollama'
                    self.ollama_model = ollama_model
                else:
                    raise ValueError(f"Unknown model choice: {model_choice}")
                
                logger.info(f"✅ LLM initialized: {self.llm_type}")
                logger.debug(f"LLM client type: {type(self.llm_client)}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                raise
    
    def _ensure_search_tool_initialized(self):
        """Khởi tạo SearchTool với embedding model nếu chưa có"""
        if self.search_tool is None:
            logger.info("Initializing SearchTool...")
            import torch
            from sentence_transformers import SentenceTransformer
            from src.config import EMBEDDING_MODEL_NAME
            
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME).to(device)
            self.search_tool = get_search_tool(embedding_model)
            logger.info(f"✅ SearchTool initialized on {device}")
    
    def _ensure_rag_tool_initialized(self):
        """Khởi tạo RagTool nếu chưa có"""
        if self.rag_tool is None:
            logger.info("Initializing RagTool...")
            
            # Ensure dependencies
            self._ensure_llm_initialized()
            self._ensure_search_tool_initialized()
            
            # Create RagTool
            self.rag_tool = get_rag_tool(
                search_tool=self.search_tool,
                llm_client=self.llm_client,
                llm_type=self.llm_type,
                ollama_model=self.ollama_model
            )
            logger.info("✅ RagTool initialized")
    
    def _ensure_collection_tool_initialized(self):
        """Khởi tạo CollectionTool nếu chưa có"""
        if self.collection_tool is None:
            logger.info("Initializing CollectionTool...")
            self.collection_tool = get_collection_tool(self.collection_manager)
            logger.info("✅ CollectionTool initialized")
    
    def _ensure_setup_tool_initialized(self):
        """Khởi tạo SetupTool nếu chưa có"""
        if self.setup_tool is None:
            logger.info("Initializing SetupTool...")
            
            # Ensure CollectionTool
            self._ensure_collection_tool_initialized()
            
            # Create SetupTool
            self.setup_tool = get_setup_tool(
                pdf_manager=self.pdf_manager,
                collection_manager=self.collection_manager,
                collection_tool=self.collection_tool,
                export_tool=self.export_tool,
                topic_tool=self.topic_tool
            )
            logger.info("✅ SetupTool initialized")
    
    def setup(self):
        """Setup agent using SetupTool - delegate to tool"""
        if self.initialized:
            choice = input("\nAgent already setup. Re-run? (y/N): ").strip().lower()
            if choice not in ['y', 'yes']:
                return
            self.initialized = False
        
        # Delegate to SetupTool
        self._ensure_setup_tool_initialized()
        result = self.setup_tool.setup_workflow(re_setup=True)
        
        if result['success']:
            self.selected_pdfs = result['selected_pdfs']
            self.selected_collections = result['selected_collections']
            self.initialized = True
            
            # Initialize LLM for RAG
            print("\nSTEP 4: Initialize RAG")
            self._ensure_llm_initialized()
            
            print("\nLệnh: collections | history | clear | setup | exit | topics")
            print("💡 Gõ 'topics' hoặc 'suggest' để xem gợi ý chủ đề")
        else:
            print(f"\n⚠️  Setup failed: {result['message']}")
    
    def manage_collections(self):
        """Manage collections using CollectionTool - interactive menu"""
        self._ensure_collection_tool_initialized()
        
        while True:
            print("\n" + "="*60)
            print("QUẢN LÝ COLLECTION")
            print("="*60)
            
            # Get all collections
            all_collections = self.collection_tool.list_collections()
            
            # Display available collections
            print(f"\nCó sẵn ({len(all_collections)}):")
            for i, col in enumerate(all_collections, 1):
                status = "✓ ĐANG DÙNG" if col['name'] in self.selected_collections else "  "
                print(f"{i}. [{status}] {col['name']} ({col['num_entities']} docs)")
            
            # Display active collections
            print(f"\nĐang dùng ({len(self.selected_collections)}):")
            for col_name in self.selected_collections:
                print(f"   - {col_name}")
            
            # Menu
            print("\nLệnh:")
            print("  1-9     - Toggle collection")
            print("  all     - Chọn tất cả")
            print("  none    - Bỏ chọn tất cả")
            print("  back    - Quay lại")
            
            choice = input("\nChọn: ").strip().lower()
            
            if choice == 'back':
                break
            elif choice == 'all':
                self.selected_collections = [col['name'] for col in all_collections]
                print(f"✅ Đã chọn tất cả ({len(self.selected_collections)} collections)")
            elif choice == 'none':
                self.selected_collections = []
                print("✅ Đã bỏ chọn tất cả")
            elif choice.isdigit():
                # Toggle collection
                idx = int(choice) - 1
                if 0 <= idx < len(all_collections):
                    col_name = all_collections[idx]['name']
                    if col_name in self.selected_collections:
                        self.selected_collections.remove(col_name)
                        print(f"➖ Đã bỏ: {col_name}")
                    else:
                        self.selected_collections.append(col_name)
                        print(f"➕ Đã thêm: {col_name}")
                else:
                    print("❌ Số không hợp lệ")
            else:
                print("❌ Lệnh không hợp lệ")
    
    def process_message(self, message: str) -> str:
        """Xử lý tin nhắn từ user: phát hiện intent -> trả lời"""
        logger.info(f"User: {message}")
        
        # Add to conversation history (using ConversationHistory)
        self.conversation_history.add_message('user', message)
        
        # Classify: PDF-related or general chat
        pdf_classification = self.intent_classifier.classify(message)
        print(f"\n🔍 Phân loại: {pdf_classification['intent']} (tin cậy: {pdf_classification['confidence']:.2f})")
        print(f"   Lý do: {pdf_classification['reason']}")
        
        # Detect detailed intent (using IntentDetector)
        intent_result = self.intent_detector.detect(message)
        intent = intent_result['intent']
        confidence = intent_result['confidence']
        print(f"   Ý định chi tiết: {intent} (độ tin cậy: {confidence:.2f})")
        
        # Route to appropriate handler
        if intent == 'greeting':
            response = self._handle_greeting()
        elif intent == 'farewell':
            response = self._handle_farewell()
        elif intent == 'thanks':
            response = self._handle_thanks()
        elif intent == 'help':
            response = self._handle_help()
        elif intent == 'command_export':
            response = self._handle_export_command()
        elif intent == 'command_check':
            response = self._handle_check_command()
        elif intent == 'no_idea':
            print("   → Đề xuất các chủ đề từ tài liệu")
            response = self.handle_no_idea_question()
        elif intent == 'question':
            if pdf_classification['intent'] == 'pdf_related':
                print("   → Sử dụng RAG để trả lời từ tài liệu")
                response = self._handle_question(message)
            else:
                print("   → Chat bình thường không cần tìm kiếm tài liệu")
                response = self._handle_general_chat(message)
        else:
            response = "Tôi không hiểu. Vui lòng diễn đạt lại."
        
        # Add response to conversation history
        self.conversation_history.add_message('assistant', response)
        
        return response
    
    def _handle_greeting(self) -> str:
        return f"Hello! I'm {self.name}. I can help you search information from PDF documents. What would you like to know?"
    
    def _handle_farewell(self) -> str:
        return "Goodbye! See you again!"
    
    def _handle_thanks(self) -> str:
        return "You're welcome! Happy to help."
    
    def _handle_help(self) -> str:
        return """I can help you:

1. Search information: Ask any question about the documents
2. Manage collections: Type 'collections' to add/remove collections
3. View history: Type 'history' to see conversation
4. Re-setup: Type 'setup' to select different PDFs/collections
5. Export MD: Ask me to export PDFs to Markdown
6. Check collection: Ask me to check collection status

Example questions:
- "What is ROUGE?"
- "Explain BLEU metric"
- "Export MD files"
- "Check collection status"

Try asking me something!"""
    
    def _handle_export_command(self) -> str:
        """Xử lý lệnh export PDF sang MD (sử dụng ExportTool)"""
        if not self.selected_pdfs:
            return "Chưa chọn PDF nào. Vui lòng chạy setup trước."
        
        try:
            print(f"\nĐang export {len(self.selected_pdfs)} PDF sang MD...")
            
            # Lấy danh sách tên file PDF
            pdf_names = [pdf.name for pdf in self.selected_pdfs]
            
            # Sử dụng ExportTool
            results = self.export_tool.export_multiple_pdfs(pdf_names, output_dir="exports")
            
            # Hiển thị kết quả chi tiết
            for result in results['results']:
                status = "✅" if result['status'] else "❌"
                print(f"{status} {result['pdf_name']}")
            
            # Tạo summary message
            summary = self.export_tool.get_export_summary(results)
            return summary
            
        except Exception as e:
            logger.error(f"Export command failed: {e}", exc_info=True)
            return f"Error during export: {str(e)}"
    
    def _handle_check_command(self) -> str:
        """Kiểm tra trạng thái các collection"""
        if not self.selected_collections:
            return "Chưa chọn collection nào. Vui lòng chạy setup trước."
        
        try:
            from pymilvus import Collection
            
            status_info = []
            total_docs = 0
            
            for col_name in self.selected_collections:
                try:
                    collection = Collection(col_name)
                    collection.load()
                    num_entities = collection.num_entities
                    total_docs += num_entities
                    status_info.append(f"- {col_name}: {num_entities} tài liệu")
                except Exception as e:
                    status_info.append(f"- {col_name}: Lỗi - {str(e)}")
            
            response = f"Trạng thái Collection ({len(self.selected_collections)} collections):\n"
            response += "\n".join(status_info)
            response += f"\n\nTổng số tài liệu: {total_docs}"
            
            return response
        except Exception as e:
            logger.error(f"Check command failed: {e}", exc_info=True)
            return f"Error checking collections: {str(e)}"
    
    def _handle_general_chat(self, message: str) -> str:
        """
        Xử lý chat bình thường không liên quan đến PDF
        Sử dụng LLM để trả lời tự nhiên mà không cần tìm kiếm tài liệu
        """
        self._ensure_llm_initialized()
        
        try:
            # Get recent context from conversation history
            recent_history = self.conversation_history.get_recent(n=3)
            
            # Format context for LLM
            context = ""
            if recent_history:
                for msg in recent_history:
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"
            
            # Prompt for general chat
            prompt = f"""Bạn là một trợ lý AI thân thiện. Hãy trả lời câu hỏi của người dùng một cách tự nhiên và hữu ích.

{context}

User: {message}

Hãy trả lời ngắn gọn, tự nhiên và thân thiện."""

            # Call LLM
            if self.llm_type == 'gemini':
                answer = self.llm_client.generate_content(prompt).strip()
            else:  # ollama
                response = self.llm_client.chat(
                    model=self.ollama_model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                answer = response['message']['content'].strip()
            
            return answer
        
        except Exception as e:
            logger.error(f"Lỗi khi chat: {e}", exc_info=True)
            return "Xin lỗi, tôi gặp lỗi khi xử lý tin nhắn của bạn."
    
    def _handle_question(self, question: str) -> str:
        """Handle question using RagTool - delegate to tool"""
        if not self.initialized:
            return "Agent chưa setup. Chạy setup() trước."
        if not self.selected_collections:
            return "Chưa chọn collection nào."
        
        # Ensure RagTool is initialized
        self._ensure_rag_tool_initialized()
        
        try:
            print(f"\nĐang tìm trong {len(self.selected_collections)} collection...")
            
            # Delegate to RagTool
            result = self.rag_tool.answer_question(
                question=question,
                collection_names=self.selected_collections,
                conversation_history=self.conversation_history.get_all(),
                top_k=20
            )
            
            if not result['success'] or not result['sources']:
                return self._show_no_results_with_suggestions()
            
            # Format response with sources
            answer = result['answer']
            sources = result['sources']
            
            response = f"{answer}\n\n**Nguồn ({len(sources)} tài liệu):**"
            
            from collections import defaultdict
            sources_by_pdf = defaultdict(list)
            for source in sources[:15]:  # Show top 15 sources
                pdf_name = source.get('source', 'Unknown')
                page = source.get('page', 'N/A')
                score = source.get('score', 0)
                sources_by_pdf[pdf_name].append((page, score))
            
            for i, (pdf_name, pages_info) in enumerate(sources_by_pdf.items(), 1):
                response += f"\n  {i}. {pdf_name}"
                for page, score in pages_info[:3]:  # Top 3 pages per PDF
                    response += f"\n     - Trang {page}"
            
            return response
            
        except Exception as e:
            logger.error(f"Lỗi: {e}", exc_info=True)
            return f"Lỗi: {str(e)}"
    
    def _show_no_results_with_suggestions(self) -> str:
        """Hiển thị thông báo không tìm thấy kèm gợi ý"""
        no_result_msg = "❌ Không tìm thấy thông tin liên quan trong tài liệu.\n"
        
        # Kiểm tra xem có topics không
        if self.topic_suggester.has_topics():
            no_result_msg += "\n💡 Bạn có thể hỏi về các chủ đề sau:\n"
            suggestions = self.topic_suggester.get_suggestions(
                self.selected_collections,
                max_suggestions=5
            )
            for i, suggestion in enumerate(suggestions, 1):
                no_result_msg += f"   {i}. {suggestion}\n"
            no_result_msg += "\n📝 Hoặc gõ 'topics' để xem tất cả chủ đề có sẵn"
        else:
            no_result_msg += "💡 Thử diễn đạt lại câu hỏi hoặc gõ 'topics' để xem gợi ý"
        
        return no_result_msg
    
    def get_history(self, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lấy lịch sử hội thoại (tất cả hoặc n cuối cùng)"""
        if last_n is None:
            return self.conversation_history.get_all()
        return self.conversation_history.get_recent(n=last_n)
    
    def clear_history(self):
        """Xóa lịch sử hội thoại và topics cache"""
        self.conversation_history.clear()
        self.topic_suggester.clear_cache()
        logger.info("Đã xóa lịch sử và topics cache")
    
    def show_topics(self) -> str:
        """Hiển thị các chủ đề có sẵn từ tài liệu (sử dụng TopicTool)"""
        if not self.topic_tool.has_topics():
            return "⚠️  Chưa có topics. Vui lòng chạy setup trước."
        
        # Hiển thị topic summary
        summary = self.topic_tool.get_topic_summary()
        
        # Thêm suggestions
        suggestions = self.topic_tool.get_suggestions(
            max_suggestions=8,
            collection_names=self.selected_collections
        )
        
        formatted_suggestions = self.topic_tool.format_suggestions(suggestions)
        
        return summary + "\n\n" + formatted_suggestions
    
    def handle_no_idea_question(self) -> str:
        """
        Xử lý khi user nói 'tôi không biết hỏi gì' hoặc 'đề xuất chủ đề'
        Sử dụng TopicTool
        """
        if not self.topic_tool.has_topics():
            return ("Chưa có thông tin về các chủ đề trong tài liệu. "
                   "Vui lòng chạy setup để phân tích tài liệu.")
        
        # Lấy suggestions
        suggestions = self.topic_tool.get_suggestions(
            max_suggestions=10,
            collection_names=self.selected_collections
        )
        
        formatted = self.topic_tool.format_suggestions(suggestions)
        formatted += "\n\n💬 Hoặc gõ 'topics' để xem tất cả chủ đề có sẵn"
        
        return formatted


def run_cli():
    """Chạy Agent ở chế độ CLI"""
    print("\n" + "="*70)
    print(AGENT_NAME)
    print(AGENT_DESCRIPTION)
    print("="*70)
    
    try:
        agent = Agent()
        agent.setup()
        
        if not agent.initialized:
            print("Thiết lập thất bại")
            return
        
        print("\nBắt đầu chat (gõ exit/quit/bye để thoát)")
        print("-"*70)
        
        while True:
            try:
                user_input = input("\nBạn: ").strip()
                if not user_input:
                    continue
                
                # Xử lý các lệnh đặc biệt
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("Tạm biệt!")
                    break
                elif user_input.lower() == 'history':
                    # Xem lịch sử hội thoại
                    for entry in agent.get_history(last_n=5):
                        role = "Bạn" if entry['role'] == 'user' else "Agent"
                        print(f"\n{role}: {entry['content'][:200]}")
                    continue
                elif user_input.lower() == 'clear':
                    # Xóa lịch sử
                    agent.clear_history()
                    print("Đã xóa lịch sử")
                    continue
                elif user_input.lower() == 'setup':
                    # Thiết lập lại
                    agent.setup()
                    continue
                elif user_input.lower() in ['collections', 'col']:
                    # Quản lý collection
                    agent.manage_collections()
                    continue
                elif user_input.lower() in ['topics', 'topic', 'suggest', 'gợi ý']:
                    # Xem các chủ đề có sẵn
                    topics_info = agent.show_topics()
                    print(f"\n{topics_info}")
                    continue
                
                # Kiểm tra nếu user không biết hỏi gì
                no_idea_keywords = [
                    'không biết hỏi gì', 'không biết hỏi', 'đề xuất', 'gợi ý',
                    'tôi nên hỏi gì', 'có thể hỏi gì', 'chủ đề nào',
                    "don't know what to ask", 'suggest topics', 'what can i ask'
                ]
                
                if any(keyword in user_input.lower() for keyword in no_idea_keywords):
                    response = agent.handle_no_idea_question()
                    print(f"\nAgent: {response}")
                    continue
                
                # Xử lý tin nhắn thông thường
                response = agent.process_message(user_input)
                print(f"\nAgent: {response}")
                
            except KeyboardInterrupt:
                print("\nTạm biệt!")
                break
            except Exception as e:
                print(f"Lỗi: {e}")
                logger.error(f"Lỗi: {e}", exc_info=True)
    
    except Exception as e:
        print(f"Cannot initialize: {e}")
        logger.error(f"Init failed: {e}", exc_info=True)


if __name__ == "__main__":
    run_cli()
