# coding: utf-8
"""
Main Agent - Agent RAG nâng cao với spell checking và hỗ trợ nhiều PDF
Tính năng:
- Chọn PDF và collection linh hoạt
- Export MD hàng loạt (batch)
- Kiểm tra chính tả tự động
- Phát hiện ý định (intent detection)
- Tìm kiếm đa collection (sử dụng SearchTool)
- Gợi ý topics (sử dụng TopicTool)
- Export to MD (sử dụng ExportTool)
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
from agent.text_processor import get_text_processor
from agent.pdf_manager import get_pdf_manager
from agent.collection_manager import get_collection_manager
from agent.intent_classifier import get_intent_classifier
from agent.topic_suggester import get_topic_suggester

# Import tools
from agent.tools.search_tool import get_search_tool
from agent.tools.topic_tool import get_topic_tool
from agent.tools.export_tool import get_export_tool

# Import export function
from src.export_md import convert_to_markdown

from src.logging_config import get_logger

logger = get_logger(__name__)


class Agent:
    """Agent chính hỗ trợ nhiều PDF và nhiều collection"""
    
    def __init__(self, name: str = "Agent"):
        """Khởi tạo Agent với các thành phần cần thiết"""
        self.name = name
        self.pdf_manager = get_pdf_manager()  # Quản lý file PDF
        self.text_processor = get_text_processor()  # Xử lý text (spell check, intent)
        self.collection_manager = get_collection_manager()  # Quản lý collection trong Milvus
        self.intent_classifier = get_intent_classifier()  # Phân loại câu hỏi (PDF hay chat)
        self.topic_suggester = get_topic_suggester()  # Đề xuất chủ đề từ tài liệu
        
        # Initialize tools
        self.search_tool = None  # SearchTool - sẽ được khởi tạo khi cần embedding
        self.topic_tool = get_topic_tool(self.topic_suggester)  # TopicTool
        self.export_tool = get_export_tool()  # ExportTool
        
        self.conversation_history = []  # Lịch sử hội thoại
        self.embedder = None  # Model embedding (deprecated, dùng search_tool)
        self.llm_client = None  # Client LLM (Gemini/Ollama)
        self.llm_type = None  # Loại LLM đang dùng
        self.ollama_model = None  # Tên model Ollama nếu dùng Ollama
        self.initialized = False  # Trạng thái khởi tạo
        
        self.selected_pdfs = []  # Danh sách PDF đã chọn
        self.selected_collections = []  # Danh sách collection đã chọn
    
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
    
    def _search_multi_collections(self, question: str, top_k: int = 15) -> Dict[str, Any]:
        """
        Tìm kiếm trong nhiều collections (sử dụng SearchTool)
        
        Args:
            question: Câu hỏi
            top_k: Số kết quả tối đa
            
        Returns:
            Dict chứa answer, sources, metadata
        """
        from src.llm_handler import generate_answer_with_fallback
        
        logger.info(f"Searching {len(self.selected_collections)} collections")
        
        # Khởi tạo SearchTool nếu chưa có
        self._ensure_search_tool_initialized()
        
        # Sử dụng SearchTool với threshold thấp hơn (0.1 thay vì 0.15)
        all_results = self.search_tool.search_multi_collections(
            query=question,
            collection_names=self.selected_collections,
            top_k=top_k,
            similarity_threshold=0.10  # Hạ xuống 0.10 để dễ match hơn
        )
        
        if not all_results:
            return {
                'success': True,
                'answer': "Sorry, no relevant information found.",
                'sources': [],
                'total_searched': len(self.selected_collections)
            }
        
        # Format context cho LLM
        context = self.search_tool.format_results_for_context(all_results, max_results=top_k)
        
        prompt = f"""Based on the following information, answer the question accurately.

Question: {question}

Reference:
{context}

Answer:"""
        
        try:
            # Gọi LLM để generate answer
            if self.llm_type == 'gemini':
                # GeminiClient.generate_content() trả về string trực tiếp
                answer = self.llm_client.generate_content(prompt)
            else:  # ollama
                response = self.llm_client.chat(
                    model=self.ollama_model,  # Dùng model được chọn
                    messages=[{'role': 'user', 'content': prompt}]
                )
                answer = response['message']['content']
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            answer = "Sorry, error generating answer."
        
        return {
            'success': True,
            'answer': answer,
            'sources': all_results[:top_k],  # Top results sau khi search
            'total_searched': len(self.selected_collections),
            'total_found': len(all_results)
        }
    
    def setup(self):
        if self.initialized:
            choice = input("\nAgent already setup. Re-run? (y/N): ").strip().lower()
            if choice not in ['y', 'yes']:
                return
            self.initialized = False
        
        print("\n" + "="*70)
        print("SETUP AGENT - Multi-PDF RAG System")
        print("="*70)
        
        # Step 1: Select PDFs
        # === BƯỚC 1: CHỌN PDF ===
        print("\nSTEP 1: Select PDF files")
        print("-" * 70)
        
        pdfs = self.pdf_manager.list_pdfs()
        if not pdfs:
            print(f"\nKhông tìm thấy file PDF trong: {self.pdf_manager.pdf_dir}")
            return
        
        # Hiển thị danh sách PDF với thông tin chi tiết
        print(f"\n{len(pdfs)} file PDF:")
        for i, pdf in enumerate(pdfs, 1):
            info = self.pdf_manager.get_file_info(pdf)
            size_mb = info['pdf_size'] / (1024 * 1024)
            col_name = self.collection_manager.get_collection_name(pdf.name)
            has_collection = self.collection_manager.collection_exists(col_name)
            md_status = "MD" if info['md_exists'] else "No MD"
            col_status = "Col" if has_collection else "No Col"
            print(f"{i}. {pdf.name} ({size_mb:.1f}MB | {md_status} | {col_status})")
        
        print("\nChọn: 'all', số (1,2,3), hoặc tên file")
        choice = input("Chọn PDF: ").strip().lower()
        
        # Xử lý lựa chọn của user
        if not choice or choice == 'all':
            self.selected_pdfs = pdfs
        else:
            items = [item.strip() for item in choice.split(',')]
            self.selected_pdfs = []
            for item in items:
                if item.isdigit():  # Nếu là số
                    idx = int(item) - 1
                    if 0 <= idx < len(pdfs):
                        self.selected_pdfs.append(pdfs[idx])
                else:  # Nếu là tên file
                    for pdf in pdfs:
                        if item in pdf.name.lower():
                            self.selected_pdfs.append(pdf)
                            break
        
        if not self.selected_pdfs:
            print("Chưa chọn PDF nào")
            return
        
        print(f"\nĐã chọn {len(self.selected_pdfs)} PDF")
        
        # === BƯỚC 2: EXPORT MD (chỉ hỏi 1 lần) ===
        print("\nSTEP 2: Export MD files")
        print("-" * 70)
        
        # Tìm PDF chưa có file MD
        pdfs_need_md = []
        for pdf in self.selected_pdfs:
            info = self.pdf_manager.get_file_info(pdf)
            if not info['md_exists']:
                pdfs_need_md.append(pdf)
        
        if pdfs_need_md:
            print(f"\n{len(pdfs_need_md)} PDF cần export sang MD")
            export_choice = input(f"Export MD cho các PDF này? (Y/n): ").strip().lower()
            if export_choice in ['', 'y', 'yes']:
                print(f"\nĐang export {len(pdfs_need_md)} file MD...")
                for i, pdf in enumerate(pdfs_need_md, 1):
                    try:
                        print(f"[{i}/{len(pdfs_need_md)}] {pdf.name}...", end=" ")
                        md_content = convert_to_markdown(str(pdf))
                        md_path = self.pdf_manager.get_md_path(pdf)
                        md_path.write_text(md_content, encoding='utf-8')
                        print("OK")
                    except Exception as e:
                        print(f"Lỗi: {e}")
        else:
            print("\nTất cả PDF đã có file MD")
        
        # === BƯỚC 3: TẠO/CHỌN COLLECTION ===
        print("\nSTEP 3: Create/select collections")
        print("-" * 70)
        
        pdfs_need_collection = []
        existing_collections = []
        pdfs_with_existing_collection = []
        
        # Kiểm tra PDF nào đã có collection
        for pdf in self.selected_pdfs:
            col_name = self.collection_manager.get_collection_name(pdf.name)
            if self.collection_manager.collection_exists(col_name):
                pdfs_with_existing_collection.append((pdf, col_name))
            else:
                pdfs_need_collection.append(pdf)
        
        # Xử lý các collection đã tồn tại
        rebuild_all = None  # None = chưa quyết định, True = rebuild all, False = use all
        
        if pdfs_with_existing_collection:
            print(f"\n✅ {len(pdfs_with_existing_collection)} PDF đã có collection:")
            for pdf, col_name in pdfs_with_existing_collection:
                print(f"   - {pdf.name} → {col_name}")
            
            # Hỏi user có muốn rebuild không (chỉ hỏi 1 lần)
            print("\nTùy chọn cho các collection đã tồn tại:")
            print("  1. Sử dụng lại (nhanh)")
            print("  2. Rebuild tất cả (chậm, nếu PDF đã thay đổi)")
            
            rebuild_choice = input("\nChọn (1/2, mặc định=1): ").strip()
            
            if rebuild_choice == '2':
                # Rebuild all
                print("\n🔄 Sẽ rebuild tất cả collection...")
                rebuild_all = True
                # Chuyển tất cả sang danh sách cần tạo lại
                for pdf, col_name in pdfs_with_existing_collection:
                    # Xóa collection cũ
                    print(f"   Đang xóa {col_name}...")
                    self.collection_manager.delete_collection(col_name)
                    pdfs_need_collection.append(pdf)
            else:
                # Use existing
                print("\n✅ Sử dụng lại collection hiện có")
                rebuild_all = False
                for pdf, col_name in pdfs_with_existing_collection:
                    existing_collections.append(col_name)
        
        # Tạo collection cho PDF chưa có hoặc cần rebuild
        if pdfs_need_collection:
            action = "rebuild" if rebuild_all else "tạo"
            print(f"\n{len(pdfs_need_collection)} PDF cần {action} collection")
            create_choice = input(f"{action.capitalize()} collection cho các PDF này? (Y/n): ").strip().lower()
            if create_choice in ['', 'y', 'yes', 'có']:
                for i, pdf in enumerate(pdfs_need_collection, 1):
                    try:
                        print(f"[{i}/{len(pdfs_need_collection)}] Đang index {pdf.name}...")
                        col_name, success = self.collection_manager.create_and_populate_collection(str(pdf))
                        if success:
                            existing_collections.append(col_name)
                            print(f"   ✅ OK: {col_name}")
                    except Exception as e:
                        print(f"   ❌ Lỗi: {e}")
        
        self.selected_collections = existing_collections
        
        if not self.selected_collections:
            print("\nKhông có collection nào sẵn sàng")
            return
        
        print(f"\nSẽ tìm kiếm trong {len(self.selected_collections)} collection")
        
        # === BƯỚC 4: KHỞI TẠO RAG ===
        print("\nSTEP 4: Initialize RAG")
        self._ensure_llm_initialized()
        
        # === BƯỚC 5: XÂY DỰNG TOPICS (cho đề xuất) ===
        print("\nSTEP 5: Build topic suggestions")
        print("-" * 70)
        try:
            print("Đang phân tích tài liệu để tạo gợi ý chủ đề...")
            # Sử dụng TopicTool
            self.topic_tool.build_topics(
                collection_names=self.selected_collections,
                sample_size=30  # Lấy 30 docs mẫu từ mỗi collection
            )
            print("✅ Đã xây dựng topic suggestions")
        except Exception as e:
            logger.warning(f"Could not build topics: {e}")
            print("⚠️  Không thể tạo topic suggestions (có thể tiếp tục)")
        
        self.initialized = True
        print("\n" + "="*70)
        print(f"SẴN SÀNG! PDFs: {len(self.selected_pdfs)} | Collections: {len(self.selected_collections)}")
        print("="*70)
        print("\nLệnh: collections | history | clear | setup | exit | topics")
        print("💡 Gõ 'topics' hoặc 'suggest' để xem gợi ý chủ đề")
    
    def manage_collections(self):
        """Menu quản lý collection: thêm, xóa, xóa hết, chọn tất cả"""
        while True:
            print("\n" + "="*60)
            print("QUẢN LÝ COLLECTION")
            print("="*60)
            
            all_collections = self.collection_manager.list_collections()
            
            # Hiển thị tất cả collection có sẵn
            print(f"\nCó sẵn ({len(all_collections)}):")
            for i, col in enumerate(all_collections, 1):
                status = "ĐANG DÙNG" if col['name'] in self.selected_collections else "CHƯA DÙNG"
                print(f"{i}. {col['name']} - {status}")
            
            # Hiển thị collection đang active
            print(f"\nĐang dùng ({len(self.selected_collections)}):")
            for col_name in self.selected_collections:
                print(f"   - {col_name}")
            
            print("\nTùy chọn: 1.Thêm | 2.Xóa | 3.Xóa hết | 4.Chọn tất cả | 5.Quay lại")
            choice = input("Chọn: ").strip()
            
            if choice == '1':  # Thêm collection
                inactive = [col for col in all_collections if col['name'] not in self.selected_collections]
                if inactive:
                    for i, col in enumerate(inactive, 1):
                        print(f"{i}. {col['name']}")
                    add_input = input("Thêm (nhập số): ").strip()
                    if add_input.isdigit():
                        idx = int(add_input) - 1
                        if 0 <= idx < len(inactive):
                            self.selected_collections.append(inactive[idx]['name'])
                            print("Đã thêm")
            
            elif choice == '2':  # Xóa collection
                if self.selected_collections:
                    for i, col_name in enumerate(self.selected_collections, 1):
                        print(f"{i}. {col_name}")
                    rm_input = input("Xóa (nhập số): ").strip()
                    if rm_input.isdigit():
                        idx = int(rm_input) - 1
                        if 0 <= idx < len(self.selected_collections):
                            self.selected_collections.pop(idx)
                            print("Đã xóa")
            
            elif choice == '3':  # Xóa tất cả
                self.selected_collections = []
                print("Đã xóa tất cả")
            
            elif choice == '4':  # Chọn tất cả
                self.selected_collections = [col['name'] for col in all_collections]
                print(f"Đã kích hoạt {len(self.selected_collections)} collection")
            
            elif choice == '5':  # Quay lại
                break
    
    def process_message(self, message: str) -> str:
        """Xử lý tin nhắn từ user: kiểm tra lỗi chính tả -> phát hiện intent -> trả lời"""
        logger.info(f"User: {message}")
        
        # Lưu vào lịch sử
        self.conversation_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # BỎ SPELL CHECK - gây hỏng tiếng Việt
        # spelling_check = self.text_processor.check_spelling(message)
        # Spell checker không hoạt động tốt với tiếng Việt nên tắt hoàn toàn
        
        # Bước 1: Phân loại xem có liên quan đến PDF không
        pdf_classification = self.intent_classifier.classify(message)
        print(f"\n🔍 Phân loại: {pdf_classification['intent']} (tin cậy: {pdf_classification['confidence']:.2f})")
        print(f"   Lý do: {pdf_classification['reason']}")
        
        # Bước 2: Phát hiện ý định chi tiết (greeting, question, etc.)
        intent_result = self.text_processor.detect_intent(message)
        intent = intent_result['intent']
        confidence = intent_result['confidence']
        print(f"   Ý định chi tiết: {intent} (độ tin cậy: {confidence:.2f})")
        
        # Xử lý theo intent
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
            # User không biết hỏi gì -> đề xuất topics
            print("   → Đề xuất các chủ đề từ tài liệu")
            response = self.handle_no_idea_question()
        elif intent == 'question':
            # Kiểm tra xem có liên quan đến PDF không
            if pdf_classification['intent'] == 'pdf_related':
                # Câu hỏi về tài liệu -> dùng RAG
                print("   → Sử dụng RAG để trả lời từ tài liệu")
                response = self._handle_question(message)
            else:
                # Chat bình thường -> không cần RAG
                print("   → Chat bình thường không cần tìm kiếm tài liệu")
                response = self._handle_general_chat(message)
        else:
            response = "Tôi không hiểu. Vui lòng diễn đạt lại."
        
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        if len(self.conversation_history) > MAX_CONVERSATION_HISTORY * 2:
            self.conversation_history = self.conversation_history[-(MAX_CONVERSATION_HISTORY * 2):]
        
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
            # Lấy context từ lịch sử hội thoại gần đây
            recent_history = self.get_history(last_n=3)
            context = ""
            if recent_history:
                context = "Lịch sử hội thoại gần đây:\n"
                for entry in recent_history[:-1]:  # Bỏ message hiện tại
                    role = "User" if entry['role'] == 'user' else "Assistant"
                    context += f"{role}: {entry['content']}\n"
            
            # Prompt cho chat bình thường
            prompt = f"""Bạn là một trợ lý AI thân thiện. Hãy trả lời câu hỏi của người dùng một cách tự nhiên và hữu ích.

{context}

User: {message}

Hãy trả lời ngắn gọn, tự nhiên và thân thiện."""

            # Gọi LLM
            if self.llm_type == 'gemini':
                # GeminiClient.generate_content() trả về string trực tiếp
                answer = self.llm_client.generate_content(prompt).strip()
            else:  # ollama
                response = self.llm_client.chat(
                    model=self.ollama_model,  # Dùng model được chọn
                    messages=[{'role': 'user', 'content': prompt}]
                )
                answer = response['message']['content'].strip()
            
            return answer
        
        except Exception as e:
            logger.error(f"Lỗi khi chat: {e}", exc_info=True)
            return "Xin lỗi, tôi gặp lỗi khi xử lý tin nhắn của bạn."
    
    def _split_complex_question(self, question: str) -> List[str]:
        """
        Tách câu hỏi phức tạp thành nhiều sub-questions
        
        Args:
            question: Câu hỏi gốc
            
        Returns:
            List các sub-questions
        """
        # Các dấu hiệu câu hỏi phức tạp
        separators = ['?', ';', ',', 'và', 'hoặc', '.']
        
        # Tách theo dấu ? trước
        parts = []
        if '?' in question:
            # Tách theo dấu ?
            questions = question.split('?')
            for q in questions:
                q = q.strip()
                if q and len(q) > 10:  # Bỏ phần quá ngắn
                    parts.append(q + '?')
        
        # Nếu không có dấu ?, tách theo từ nối
        if not parts:
            # Tìm các từ nối
            import re
            # Tách theo "và", "hoặc", ";"
            pattern = r'\s+(và|hoặc)\s+|;'
            segments = re.split(pattern, question, flags=re.IGNORECASE)
            
            for seg in segments:
                seg = seg.strip()
                if seg and seg.lower() not in ['và', 'hoặc'] and len(seg) > 15:
                    # Kiểm tra xem có từ hỏi không
                    question_words = ['gì', 'nào', 'sao', 'thế nào', 'như thế nào', 'là gì', 
                                     'what', 'how', 'why', 'when', 'where', 'who']
                    if any(qw in seg.lower() for qw in question_words):
                        if not seg.endswith('?'):
                            seg += '?'
                        parts.append(seg)
        
        # Nếu vẫn không tách được hoặc chỉ có 1 phần, giữ nguyên
        if len(parts) <= 1:
            return [question]
        
        logger.info(f"Tách câu hỏi thành {len(parts)} phần: {parts}")
        return parts
    
    def _handle_question(self, question: str) -> str:
        """Xử lý câu hỏi từ tài liệu bằng RAG"""
        if not self.initialized:
            return "Agent chưa setup. Chạy setup() trước."
        if not self.selected_collections:
            return "Chưa chọn collection nào."
        
        self._ensure_llm_initialized()
        
        try:
            # Kiểm tra xem câu hỏi có phức tạp không (nhiều phần)
            sub_questions = self._split_complex_question(question)
            
            if len(sub_questions) > 1:
                # Câu hỏi phức tạp -> tìm kiếm từng phần
                print(f"\n📝 Phát hiện {len(sub_questions)} câu hỏi con, đang xử lý...\n")
                
                all_answers = []
                all_sources = []
                all_contexts = []  # Lưu context để gộp
                
                for i, sub_q in enumerate(sub_questions, 1):
                    print(f"[{i}/{len(sub_questions)}] {sub_q}")
                    
                    # Tăng top_k lên 20, hạ threshold xuống 0.1
                    rag_result = self._search_multi_collections(sub_q, top_k=20)
                    
                    if rag_result['success'] and rag_result['sources']:
                        all_answers.append({
                            'question': sub_q,
                            'answer': rag_result['answer'],
                            'has_result': True
                        })
                        all_sources.extend(rag_result['sources'])
                        # Lưu context để tổng hợp
                        all_contexts.append(f"Q: {sub_q}\nA: {rag_result['answer']}")
                    else:
                        all_answers.append({
                            'question': sub_q,
                            'answer': "Không tìm thấy thông tin cụ thể",
                            'has_result': False
                        })
                    
                    print("   ✓ Hoàn thành\n")
                
                # Kiểm tra có kết quả không
                has_any_result = any(a['has_result'] for a in all_answers)
                
                if not has_any_result:
                    # Không có kết quả nào -> đề xuất topics
                    return self._show_no_results_with_suggestions()
                
                # Tổng hợp câu trả lời cuối cùng bằng LLM
                print("🔄 Đang tổng hợp câu trả lời...")
                combined_context = "\n\n".join(all_contexts)
                
                synthesis_prompt = f"""Dựa trên các câu trả lời từng phần dưới đây, hãy tổng hợp thành một câu trả lời hoàn chỉnh và mạch lạc.

{combined_context}

Hãy tổng hợp và trả lời một cách logic, đầy đủ cho tất cả các câu hỏi trên:"""

                try:
                    if self.llm_type == 'gemini':
                        # GeminiClient.generate_content() trả về string trực tiếp
                        final_answer = self.llm_client.generate_content(synthesis_prompt)
                    else:  # ollama
                        response_obj = self.llm_client.chat(
                            model=self.ollama_model,  # Dùng model được chọn
                            messages=[{'role': 'user', 'content': synthesis_prompt}]
                        )
                        final_answer = response_obj['message']['content']
                except Exception as e:
                    logger.error(f"Synthesis error: {e}")
                    # Fallback: ghép các câu trả lời
                    final_answer = "\n\n".join([
                        f"**{i+1}. {a['question']}**\n{a['answer']}"
                        for i, a in enumerate(all_answers)
                    ])
                
                # Format response
                response = f"📚 **Câu trả lời:**\n\n{final_answer}"
                response += f"\n\n**Nguồn tham khảo ({len(set(s['source'] for s in all_sources))} PDF):**"
                
                from collections import defaultdict
                sources_by_pdf = defaultdict(list)
                for source in all_sources[:20]:  # Tăng lên 20 sources
                    pdf_name = source.get('source', 'Unknown')
                    page = source.get('page', 'N/A')
                    sources_by_pdf[pdf_name].append(page)
                
                for i, (pdf_name, pages) in enumerate(sources_by_pdf.items(), 1):
                    unique_pages = sorted(set(pages))[:8]
                    response += f"\n  {i}. {pdf_name} (trang {', '.join(map(str, unique_pages))})"
                
                return response
            
            else:
                # Câu hỏi đơn giản -> tìm kiếm bình thường
                print(f"\nĐang tìm trong {len(self.selected_collections)} collection...")
                rag_result = self._search_multi_collections(question, top_k=20)  # Tăng lên 20
                
                if not rag_result['success']:
                    return "Lỗi khi tìm kiếm."
                
                answer = rag_result['answer']
                sources = rag_result['sources']
                
                # Nếu không tìm thấy thông tin -> đề xuất topics
                if not sources:
                    return self._show_no_results_with_suggestions()
                
                response = f"{answer}\n\nNguồn ({len(sources)}):"
                
                from collections import defaultdict
                sources_by_pdf = defaultdict(list)
                for source in sources[:10]:
                    pdf_name = source.get('source', 'Unknown')
                    page = source.get('page', 'N/A')
                    score = source.get('score', 0)
                    sources_by_pdf[pdf_name].append((page, score))
                
                for i, (pdf_name, pages_info) in enumerate(sources_by_pdf.items(), 1):
                    response += f"\n  {i}. {pdf_name}"
                    for page, score in pages_info[:3]:
                        response += f"\n     - Trang {page} (score: {score:.3f})"
                
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
            return self.conversation_history
        return self.conversation_history[-last_n*2:] if last_n > 0 else []
    
    def clear_history(self):
        """Xóa lịch sử hội thoại và topics cache"""
        self.conversation_history = []
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
