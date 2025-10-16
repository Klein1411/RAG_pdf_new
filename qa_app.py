# qa_app.py

import torch
from sentence_transformers import SentenceTransformer
import os

# --- 1. CẤU HÌNH & IMPORT ---
from config import EMBEDDING_MODEL_NAME, COLLECTION_NAME
from milvus import get_or_create_collection
# Import các hàm xử lý LLM từ file mới
from llm_handler import initialize_and_select_llm, generate_answer_with_fallback

# --- 2. CÁC HÀM TIỆN ÍCH ---

def get_embedding_model():
    """
    Khởi tạo và trả về model embedding, ưu tiên sử dụng GPU nếu có.
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🤖 Đang tải model embedding '{EMBEDDING_MODEL_NAME}' lên '{device}'...")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        print("   -> ✅ Model embedding đã tải thành công!")
        return model
    except Exception as e:
        print(f"   -> ❌ Lỗi khi tải model embedding: {e}")
        return None

def search_in_milvus(collection, query_vector, top_k=30):
    """
    Tìm kiếm các vector tương tự trong Milvus.
    """
    print(f"🔍 Đang tìm kiếm {top_k} kết quả liên quan trong Milvus...")
    try:
        collection.load()
        search_params = {"metric_type": "L2", "params": {"nprobe": 64}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["text", "page", "pdf_source"]
        )
        collection.release()
        print("   -> ✅ Tìm kiếm hoàn tất.")
        return results
    except Exception as e:
        print(f"   -> ❌ Lỗi khi tìm kiếm trên Milvus: {e}")
        return None

# --- 3. HÀM MAIN CHÍNH ---

def main():
    """
    Hàm chính của ứng dụng Hỏi-Đáp.
    """
    print("--- CHÀO MỪNG ĐẾN VỚI ỨNG DỤNG HỎI-ĐÁP RAG （*＾3＾)/~☆---")
    
    # --- Bước 1: Khởi tạo và lựa chọn LLM ---
    # Toàn bộ logic phức tạp đã được chuyển sang llm_handler.py
    model_choice, gemini_model, ollama_model_name = initialize_and_select_llm()

    # --- Bước 2: Khởi tạo các thành phần khác ---
    embedding_model = get_embedding_model()
    if not embedding_model:
        print("\n--- Ứng dụng không thể khởi động do lỗi model embedding. ---")
        return

    print("\n--- Bước 3: Kết nối tới Milvus collection ---")
    collection = get_or_create_collection(COLLECTION_NAME, recreate=False)
    if not collection:
        print("   -> (T_T) Không thể kết nối tới collection. Đã chạy file populate_milvus.py chưa?")
        return

    if not collection.has_index() or collection.num_entities == 0:
        print("   -> ⚠️ Collection hiện đang trống hoặc chưa được đánh chỉ mục.")
        run_populate = input("   -> Bạn có muốn chạy script để đồng bộ dữ liệu? (y/n): ").strip()
        if run_populate.lower() == 'y':
            from populate_milvus import populate_database
            populate_database()
            print("\n   -> Đang tải lại collection sau khi đồng bộ...")
            collection = get_or_create_collection(COLLECTION_NAME, recreate=False)
        else:
            print("   -> Bỏ qua bước đồng bộ. Ứng dụng không thể tiếp tục nếu không có dữ liệu.")
            return

    print(f"\n--- Bước 4: Tải collection '{COLLECTION_NAME}' vào bộ nhớ ---")
    collection.load()
    print(f"   -> (°o°) Collection đã sẵn sàng! Hiện có {collection.num_entities} thực thể.")

    # --- Vòng lặp hỏi-đáp ---
    print("\n--- Bắt đầu phiên hỏi-đáp (gõ 'exit' để thoát :3) ---")
    while True:
        query = input("\n❓ Đặt câu hỏi của bạn: ")
        if query.lower() == 'exit':
            break
            
        print(f"🧠 Đang tạo embedding cho câu hỏi...")
        query_embedding = embedding_model.encode(query)

        search_results = search_in_milvus(collection, query_embedding, top_k=30)

        if not search_results or not search_results[0]:
            print("   -> ⚠️ Không tìm thấy thông tin liên quan trong tài liệu.")
            continue
            
        print("📝 Đang xây dựng prompt để tạo câu trả lời...")
        
        context = ""
        sources = []
        for hit in search_results[0]:
            context += f"- {hit.entity.get('text')}\n"
            sources.append(f"{hit.entity.get('pdf_source')} (Trang {hit.entity.get('page')})")

        # # DEBUG: In ra context và sources để kiểm tra
        # print("\n---------------- DEBUG: CONTEXT TRUY XUẤT ----------------")
        # print("Ngữ cảnh được lấy từ Milvus:")
        # print(context)
        # unique_sources_for_debug = sorted(list(set(sources)))
        # print(f"Nguồn tham khảo (trước khi đưa vào LLM): {', '.join(unique_sources_for_debug)}")
        # print("----------------------------------------------------------\n")

        prompt = f'''Dựa vào các thông tin được cung cấp dưới đây từ một tài liệu PDF:\n\n{context}\n\nHãy trả lời câu hỏi sau một cách chi tiết và chính xác. Chỉ sử dụng thông tin được cung cấp, không bịa đặt. Nếu thông tin không đủ để trả lời, hãy nói rằng "Thông tin không có trong tài liệu".\n\nCâu hỏi: {query}\n'''
        
        # --- Gọi model với logic retry và fallback ---
        answer = generate_answer_with_fallback(prompt, model_choice, gemini_model, ollama_model_name)

        print("\n✅ Câu trả lời:")
        print(answer)
        
        if not "[LỖI HỆ THỐNG]" in answer:
            unique_sources = sorted(list(set(sources)))
            print(f"\nNguồn tham khảo: {', '.join(unique_sources)}")

    print("\n--- Cảm ơn bạn đã sử dụng! ---")


if __name__ == "__main__":
    main()