# qa_app.py

import sys
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer
import os

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- 1. CẤU HÌNH & IMPORT ---
from src.config import EMBEDDING_MODEL_NAME, COLLECTION_NAME
from src.milvus import get_or_create_collection
# Import các hàm xử lý LLM từ file mới
from src.llm_handler import initialize_and_select_llm, generate_answer_with_fallback
from src.logging_config import get_logger

logger = get_logger(__name__)

# --- 2. CÁC HÀM TIỆN ÍCH ---

def get_embedding_model():
    """
    Khởi tạo và trả về model embedding, ưu tiên sử dụng GPU nếu có.
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"🤖 Đang tải model embedding '{EMBEDDING_MODEL_NAME}' lên '{device}'...")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        logger.info("✅ Model embedding đã tải thành công!")
        return model
    except Exception as e:
        logger.error(f"❌ Lỗi khi tải model embedding: {e}")
        return None

def search_in_milvus(collection, query_vector, top_k=30):
    """
    Tìm kiếm các vector tương tự trong Milvus. 
    Hàm này giả định collection đã được load sẵn.
    """
    logger.info(f"🔍 Đang tìm kiếm {top_k} kết quả liên quan trong Milvus...")
    try:
        search_params = {"metric_type": "L2", "params": {"nprobe": 64}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["text", "page", "pdf_source"]
        )
        logger.info("✅ Tìm kiếm hoàn tất")
        return results
    except Exception as e:
        logger.error(f"❌ Lỗi khi tìm kiếm trên Milvus: {e}")
        return None

# --- 3. HÀM MAIN CHÍNH ---

def main():
    """
    Hàm chính của ứng dụng Hỏi-Đáp.
    """
    logger.info("=== Khởi động ứng dụng HỎI-ĐÁP RAG ===")
    print("--- CHÀO MỪNG ĐẾN VỚI ỨNG DỤNG HỎI-ĐÁP RAG （*＾3＾)/~☆---")
    
    # --- Bước 1: Khởi tạo và lựa chọn LLM ---
    # Toàn bộ logic phức tạp đã được chuyển sang llm_handler.py
    model_choice, gemini_model, ollama_model_name = initialize_and_select_llm()

    # --- Bước 2: Khởi tạo các thành phần khác ---
    embedding_model = get_embedding_model()
    if not embedding_model:
        logger.error("Ứng dụng không thể khởi động do lỗi model embedding")
        print("\n--- Ứng dụng không thể khởi động do lỗi model embedding. ---")
        return

    logger.info(f"Kết nối tới Milvus collection '{COLLECTION_NAME}'")
    print("\n--- Bước 3: Kết nối tới Milvus collection ---")
    collection = get_or_create_collection(COLLECTION_NAME, recreate=False)
    if not collection:
        logger.error("Không thể kết nối tới collection")
        print("   -> (T_T) Không thể kết nối tới collection. Đã chạy file populate_milvus.py chưa?")
        return

    if not collection.has_index() or collection.num_entities == 0:
        logger.warning("Collection đang trống hoặc chưa được đánh chỉ mục")
        print("   -> ⚠️ Collection hiện đang trống hoặc chưa được đánh chỉ mục.")
        run_populate = input("   -> Bạn có muốn chạy script để đồng bộ dữ liệu? (y/n): ").strip()
        if run_populate.lower() == 'y':
            logger.info("Bắt đầu đồng bộ dữ liệu từ populate_database")
            from src.populate_milvus import populate_database
            populate_database()
            logger.info("Tải lại collection sau khi đồng bộ")
            print("\n   -> Đang tải lại collection sau khi đồng bộ...")
            collection = get_or_create_collection(COLLECTION_NAME, recreate=False)
        else:
            logger.error("Người dùng bỏ qua đồng bộ, ứng dụng không thể tiếp tục")
            print("   -> Bỏ qua bước đồng bộ. Ứng dụng không thể tiếp tục nếu không có dữ liệu.")
            return

    logger.info(f"Tải collection '{COLLECTION_NAME}' vào bộ nhớ")
    print(f"\n--- Bước 4: Tải collection '{COLLECTION_NAME}' vào bộ nhớ ---")
    collection.load()
    logger.info(f"Collection đã sẵn sàng với {collection.num_entities} thực thể")
    print(f"   -> (°o°) Collection đã sẵn sàng! Hiện có {collection.num_entities} thực thể.")

    # --- Vòng lặp hỏi-đáp ---
    logger.info("Bắt đầu phiên hỏi-đáp")
    print("\n--- Bắt đầu phiên hỏi-đáp (gõ 'exit' để thoát :3) ---")
    try:
        while True:
            query = input("\n❓ Đặt câu hỏi của bạn: ")
            if query.lower() == 'exit':
                logger.info("Người dùng kết thúc phiên hỏi-đáp")
                break
                
            logger.info(f"Xử lý câu hỏi: {query[:50]}...")
            print(f"🧠 Đang tạo embedding cho câu hỏi...")
            query_embedding = embedding_model.encode(query)

            search_results = search_in_milvus(collection, query_embedding, top_k=15)

            if not search_results or not search_results[0]:
                logger.warning("Không tìm thấy thông tin liên quan trong tài liệu")
                print("   -> ⚠️ Không tìm thấy thông tin liên quan trong tài liệu.")
                continue

            # --- LOGIC MỚI: MỞ RỘNG NGỮ CẢNH ---
            logger.info(f"Tìm thấy {len(search_results[0])} đoạn liên quan, bắt đầu mở rộng ngữ cảnh")
            print("🎯 Đã tìm thấy các đoạn liên quan, đang mở rộng ngữ cảnh...")
            
            # 1. Lấy số trang từ kết quả ban đầu
            hit_pages = sorted(list(set([hit.entity.get('page') for hit in search_results[0]]))) 
            logger.debug(f"Các trang liên quan ban đầu: {hit_pages}")
            print(f"   -> Các trang liên quan ban đầu: {hit_pages}")

            # 2. Xác định vùng trang để lấy thêm ngữ cảnh
            context_pages = []
            if hit_pages:
                min_page = min(hit_pages)
                max_page = max(hit_pages)
                # Lấy thêm 1 trang trước và 2 trang sau để có ngữ cảnh rộng hơn
                context_min_page = max(1, min_page - 1)
                context_max_page = max_page + 2
                context_pages = list(range(context_min_page, context_max_page + 1))
                logger.info(f"Mở rộng ngữ cảnh từ trang {context_min_page} đến {context_max_page}")
                print(f"   -> Mở rộng ngữ cảnh ra các trang từ {context_min_page} đến {context_max_page}.")

            # 3. Lấy tất cả các chunk từ vùng trang đã mở rộng
            expanded_results = []
            if context_pages:
                expr = f"page in {context_pages}"
                try:
                    expanded_results = collection.query(expr=expr, output_fields=["text", "page"])
                    logger.info(f"Lấy được {len(expanded_results)} chunk từ vùng mở rộng")
                except Exception as e:
                    logger.error(f"Lỗi khi mở rộng ngữ cảnh từ Milvus: {e}")
                    print(f"   -> ❌ Lỗi khi mở rộng ngữ cảnh từ Milvus: {e}")

            # 4. Xây dựng ngữ cảnh cuối cùng từ kết quả mở rộng
            logger.info("Xây dựng prompt với ngữ cảnh đầy đủ")
            print("📝 Đang xây dựng lại prompt với ngữ cảnh đầy đủ hơn...")
            context_map = {} 
            for hit in expanded_results:
                page_num = hit.get('page')
                text = hit.get('text')
                if page_num not in context_map:
                    context_map[page_num] = []
                context_map[page_num].append(text)

            # Ghép các chunk trong cùng một trang và sau đó ghép các trang lại
            final_context = ""
            sorted_pages = sorted(context_map.keys())
            for page_num in sorted_pages:
                final_context += f"--- Nội dung từ Trang {page_num} ---\n"
                final_context += "\n".join(context_map[page_num]) + "\n\n"
            
            # Nếu không có ngữ cảnh mở rộng, quay về dùng ngữ cảnh ban đầu
            if not final_context:
                logger.warning("Không thể mở rộng ngữ cảnh, sử dụng ngữ cảnh gốc")
                print("   -> ⚠️ Không thể mở rộng ngữ cảnh, quay về dùng ngữ cảnh gốc.")
                final_context = "\n".join([hit.entity.get('text') for hit in search_results[0]])

            unique_sources = sorted(list(set([f"{search_results[0][0].entity.get('pdf_source')} (Trang {p})" for p in sorted_pages])))
            # ------------------------------------------

            prompt = f'''Dựa vào các thông tin được cung cấp dưới đây từ một tài liệu PDF:\n\n{final_context}\n\nHãy trả lời câu hỏi sau một cách chi tiết và chính xác. Chỉ sử dụng thông tin được cung cấp, không bịa đặt. Nếu thông tin không đủ để trả lời, hãy nói rằng "Thông tin không có trong tài liệu".\n\nCâu hỏi: {query}\n'''
            
            # --- Gọi model với logic retry và fallback ---
            logger.info("Gọi LLM để tạo câu trả lời")
            answer = generate_answer_with_fallback(prompt, model_choice, gemini_model, ollama_model_name)
            logger.info("Đã nhận được câu trả lời từ LLM")

            print("\n✅ Câu trả lời:")
            print(answer)
            
            if not "[LỖI HỆ THỐNG]" in answer and unique_sources:
                print(f"\nNguồn tham khảo: {', '.join(unique_sources)}")
    finally:
        # Đảm bảo collection được giải phóng khi kết thúc
        logger.info(f"Giải phóng collection '{COLLECTION_NAME}' khỏi bộ nhớ")
        print(f"\n--- Giải phóng collection '{COLLECTION_NAME}' khỏi bộ nhớ ---")
        collection.release()

    logger.info("Kết thúc ứng dụng QA")
    print("\n--- Cảm ơn bạn đã sử dụng! ---")


if __name__ == "__main__":
    main()