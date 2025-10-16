import torch
from sentence_transformers import SentenceTransformer
from read_pdf import extract_pdf_pages
from milvus import get_or_create_collection
from config import PDF_PATH, EMBEDDING_MODEL_NAME, EMBEDDING_DIM, COLLECTION_NAME
import os

def get_embedding_model():
    """
    Khởi tạo và trả về model embedding, ưu tiên sử dụng GPU nếu có.
    """
    # Kiểm tra xem có GPU không
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🤖 Đang tải model embedding '{EMBEDDING_MODEL_NAME}' lên '{device}'...")
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        print("   -> ✅ Model đã tải thành công!")
        return model
    except Exception as e:
        print(f"   -> ❌ Lỗi khi tải model: {e}")
        print("   -> Vui lòng đảm bảo bạn đã cài đặt thư viện: pip install sentence-transformers")
        return None

def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 80):
    """
    Chia một đoạn văn bản dài thành các đoạn nhỏ hơn (chunks) một cách thông minh hơn.
    Nó sẽ cố gắng gộp các đoạn văn lại với nhau cho đến khi đạt chunk_size.
    """
    if not text:
        return []

    # Sử dụng \n\n để tách các đoạn văn lớn, hoặc \n cho các dòng đơn lẻ
    # Điều này giúp giữ các mục trong danh sách hoặc các dòng thơ gần nhau
    paragraphs = text.split('\n')
    
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        p_stripped = p.strip()
        if not p_stripped:
            continue

        # Nếu thêm đoạn này vào sẽ vượt quá kích thước chunk
        if len(current_chunk) + len(p_stripped) + 1 > chunk_size:
            # Nếu current_chunk có nội dung, lưu nó lại
            if current_chunk:
                chunks.append(current_chunk)
            # Bắt đầu một chunk mới với đoạn hiện tại
            current_chunk = p_stripped
        # Nếu không, tiếp tục thêm vào chunk hiện tại
        else:
            if current_chunk: # Thêm dấu cách nếu chunk đã có nội dung
                current_chunk += "\n" + p_stripped
            else: # Nếu là phần đầu tiên của chunk
                current_chunk = p_stripped

    # Đừng quên thêm chunk cuối cùng vào danh sách
    if current_chunk:
        chunks.append(current_chunk)
    
    # Logic cho phần overlap - hiện tại chưa implement để giữ cho nó đơn giản
    # nhưng cấu trúc này sẵn sàng để thêm vào sau.
    return chunks


def populate_database():
    """
    Hàm chính: Đọc PDF, tạo embedding, và lưu vào Milvus.
    """
    print("--- BẮT ĐẦU QUÁ TRÌNH ĐỒNG BỘ DỮ LIỆU VÀO MILVUS ---")
    
    # --- Bước 1: Khởi tạo các thành phần cần thiết ---
    model = get_embedding_model()
    if not model:
        return

    # Lấy hoặc tạo mới collection, xóa cái cũ đi để làm mới
    print("\n--- Bước 2: Chuẩn bị collection trên Milvus ---")
    collection = get_or_create_collection(COLLECTION_NAME, dim=EMBEDDING_DIM, recreate=True)

    # --- Bước 3: Đọc và xử lý file PDF ---
    print(f"\n--- Bước 3: Đọc và xử lý file PDF: {PDF_PATH} ---")
    if not os.path.exists(PDF_PATH):
        print(f"❌ Lỗi: Không tìm thấy file PDF tại '{PDF_PATH}'.")
        return
        
    pages_data = extract_pdf_pages(PDF_PATH)
    if not pages_data:
        print("❌ Không thể trích xuất dữ liệu từ PDF.")
        return

    # --- Bước 4: Chuẩn bị văn bản và bảng để embedding ---
    print("\n--- Bước 4: Chuẩn bị văn bản và bảng (chunking) ---")
    all_chunks = []
    metadata = []
    for page in pages_data:
        page_num = page['page_number']
        
        # Xử lý phần văn bản (text)
        if page.get('text'):
            # Chỉ xử lý các trang có nội dung và không phải là ảnh scan (đã có text)
            if page['source'] in ['gemini', 'manual']:
                page_text = page['text']
                chunks = chunk_text(page_text)
                for chunk in chunks:
                    all_chunks.append(chunk)
                    metadata.append({
                        "pdf_source": os.path.basename(PDF_PATH),
                        "page": page_num
                    })

        # Xử lý phần bảng (tables)
        if page.get('tables'):
            for table_num, table_data in enumerate(page['tables'], 1):
                # Chuyển bảng thành một chuỗi văn bản để embedding
                # Cách đơn giản là nối các hàng và cột lại với nhau
                try:
                    table_string = f"Nội dung của bảng {table_num} trên trang {page_num}:\n"
                    table_string += "\n".join([" | ".join(map(str, row)) for row in table_data])
                    
                    all_chunks.append(table_string)
                    metadata.append({
                        "pdf_source": os.path.basename(PDF_PATH),
                        "page": page_num
                    })
                    print(f"   -> Đã xử lý Bảng {table_num} trên trang {page_num}.")
                except Exception as e:
                    print(f"   -> ⚠️ Lỗi khi xử lý bảng {table_num} trang {page_num}: {e}")

    if not all_chunks:
        print("❌ Không tìm thấy đoạn văn bản hoặc bảng nào để xử lý.")
        return
        
    print(f"   -> Tổng cộng có {len(all_chunks)} đoạn văn bản và bảng cần xử lý.")

    # --- Bước 5: Tạo embedding cho tất cả các chunks ---
    print("\n--- Bước 5: Tạo embeddings cho các đoạn văn bản và bảng ---")
    embeddings = model.encode(all_chunks, show_progress_bar=True)
    print("   -> ✅ Tạo embedding hoàn tất.")

    # --- Bước 6: Chuẩn bị và lưu dữ liệu vào Milvus ---
    print("\n--- Bước 6: Lưu dữ liệu vào Milvus ---")
    entities = [
        embeddings,                                 # Field: embedding
        all_chunks,                                 # Field: text
        [meta['pdf_source'] for meta in metadata],  # Field: pdf_source
        [meta['page'] for meta in metadata]         # Field: page
    ]
    
    try:
        insert_result = collection.insert(entities)
        print(f"   -> ✅ Chèn thành công {insert_result.insert_count} vectors vào Milvus.")
        
        # Flush collection để đảm bảo dữ liệu được ghi xuống đĩa
        print("   -> Đang flush collection...")
        collection.flush()
        print("   -> ✅ Flush hoàn tất.")

    except Exception as e:
        print(f"   -> ❌ Lỗi khi chèn dữ liệu vào Milvus: {e}")

    print("\n--- QUÁ TRÌNH ĐỒNG BỘ HOÀN TẤT ---")


if __name__ == "__main__":
    populate_database()