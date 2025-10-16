# qa_app.py

import torch
from sentence_transformers import SentenceTransformer
from milvus import get_or_create_collection
from gemini_client import configure_gemini # Import the configuration function
import os

# --- 1. CẤU HÌNH ---
# Import các cấu hình chung từ file config.py
from config import EMBEDDING_MODEL_NAME, COLLECTION_NAME

# --- 2. KHỞI TẠO CÁC MODEL ---

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

# --- 3. HÀM TÌM KIẾM ---

def search_in_milvus(collection, query_vector, top_k=5):
    """
    Tìm kiếm các vector tương tự trong Milvus.
    """
    print(f"🔍 Đang tìm kiếm {top_k} kết quả liên quan trong Milvus...")
    try:
        # Đảm bảo collection đã được load để tìm kiếm
        collection.load() 
        
        search_params = {
            "metric_type": "L2", # Khoảng cách Euclidean
            "params": {"nprobe": 10},
        }
        
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["text", "page", "pdf_source"] # Yêu cầu trả về các field này
        )
        
        collection.release() # Giải phóng collection khỏi bộ nhớ sau khi tìm kiếm
        print("   -> ✅ Tìm kiếm hoàn tất.")
        return results
    except Exception as e:
        print(f"   -> ❌ Lỗi khi tìm kiếm trên Milvus: {e}")
        return None

def main():
    """
    Hàm chính của ứng dụng Hỏi-Đáp.
    """
    print("--- CHÀO MỪNG ĐẾN VỚI ỨNG DỤNG HỎI-ĐÁP RAG ---")
    
    # --- Khởi tạo ---
    embedding_model = get_embedding_model()
    # Khởi tạo model Gemini bằng hàm có sẵn
    generative_model = configure_gemini() 
    
    if not embedding_model or not generative_model:
        print("\n--- Ứng dụng không thể khởi động do lỗi. Vui lòng kiểm tra lại. ---")
        return

    print("\n--- Bước 1: Kết nối tới Milvus collection ---")
    # recreate=False để không tạo lại collection
    collection = get_or_create_collection(COLLECTION_NAME, recreate=False)
    if not collection:
        print("   -> ❌ Không thể kết nối tới collection. Đã chạy file populate_milvus.py chưa?")
        return
    print(f"   -> ✅ Kết nối thành công tới collection '{COLLECTION_NAME}'.")
    print(f"   -> Collection hiện có {collection.num_entities} thực thể.")


    # --- Vòng lặp hỏi-đáp ---
    print("\n--- Bắt đầu phiên hỏi-đáp (gõ 'exit' để thoát) ---")
    while True:
        query = input("\n❓ Đặt câu hỏi của bạn: ")
        if query.lower() == 'exit':
            break
            
        # --- Bước 2: Tạo embedding cho câu hỏi ---
        print(f"🧠 Đang tạo embedding cho câu hỏi...")
        query_embedding = embedding_model.encode(query)
        
        # --- Bước 3: Tìm kiếm thông tin liên quan (Retrieval) ---
        search_results = search_in_milvus(collection, query_embedding, top_k=5)
        
        if not search_results or not search_results[0]:
            print("   -> ⚠️ Không tìm thấy thông tin liên quan trong tài liệu.")
            continue
            
        # --- Bước 4: Xây dựng prompt và gọi Gemini (Generation) ---
        print("📝 Đang xây dựng prompt và gọi Gemini để tạo câu trả lời...")
        
        # Lấy context từ kết quả tìm kiếm
        context = ""
        sources = []
        # search_results[0] là kết quả cho query đầu tiên (và duy nhất)
        for hit in search_results[0]:
            context += f"- {hit.entity.get('text')}\n"
            sources.append(f"{hit.entity.get('pdf_source')} (Trang {hit.entity.get('page')})")

        # Tạo prompt
        prompt = f'''Dựa vào các thông tin được cung cấp dưới đây từ một tài liệu PDF:

{context}

Hãy trả lời câu hỏi sau một cách chi tiết và chính xác. Chỉ sử dụng thông tin được cung cấp, không bịa đặt. Nếu thông tin không đủ để trả lời, hãy nói rằng "Thông tin không có trong tài liệu".

Câu hỏi: {query}
'''
        
        # Gọi Gemini
        try:
            answer = generative_model.generate_content(prompt).text
            print("\n✅ Câu trả lời từ Gemini:")
            print(answer)
            # Dùng set để loại bỏ các nguồn trùng lặp
            unique_sources = sorted(list(set(sources)))
            print(f"\nNguồn tham khảo: {', '.join(unique_sources)}")
        except Exception as e:
            print(f"   -> ❌ Lỗi khi gọi Gemini API: {e}")


    print("\n--- Cảm ơn bạn đã sử dụng! ---")


if __name__ == "__main__":
    main()
