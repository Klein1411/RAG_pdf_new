import sys
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer
import os
import re

# Thêm thư mục gốc project vào sys.path để import src module
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import các thành phần cần thiết từ các file khác
from src.milvus import get_or_create_collection
from src.config import PDF_PATH, EMBEDDING_MODEL_NAME, EMBEDDING_DIM, COLLECTION_NAME, OUTPUT_DIR
from src.export_md import convert_to_markdown
from src.logging_config import get_logger

import nltk

logger = get_logger(__name__)

def get_embedding_model():
    """
    Khởi tạo và trả về model embedding, ưu tiên sử dụng GPU nếu có.
    """
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Tải model embedding '{EMBEDDING_MODEL_NAME}' lên device '{device}'")
    print(f"🤖 Đang tải model embedding '{EMBEDDING_MODEL_NAME}' lên '{device}'...")
    
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        logger.info("Model embedding đã tải thành công")
        print("   -> ✅ Model đã tải thành công!")
        return model
    except Exception as e:
        logger.error(f"Lỗi khi tải model embedding: {e}")
        print(f"   -> ❌ Lỗi khi tải model: {e}")
        return None

def download_nltk_punkt():
    """
    Kiểm tra và tải về các gói tokenizer cần thiết của NLTK.
    """
    try:
        # Phải kiểm tra cả hai tài nguyên, nếu một trong hai thiếu, sẽ gây ra LookupError
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('tokenizers/punkt_tab')
        logger.info("NLTK tokenizer đã có sẵn")
    except LookupError:
        logger.info("Tải các gói tokenizer NLTK (punkt, punkt_tab)")
        print("   -> 📖 Đang tải các gói tokenizer cần thiết cho NLTK ('punkt', 'punkt_tab')...")
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
        logger.info("Tải tokenizer hoàn tất")
        print("   -> ✅ Tải tokenizer hoàn tất.")

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap_sentences: int = 2):
    """
    Chia văn bản thành các chunk một cách thông minh, dựa trên ranh giới câu.
    Sử dụng NLTK để tách câu và nhóm chúng lại, với sự gối đầu giữa các chunk.
    
    Args:
        text (str): Đoạn văn bản cần chia.
        chunk_size (int): Kích thước tối đa (số ký tự) của mỗi chunk.
        chunk_overlap_sentences (int): Số câu gối đầu giữa các chunk liên tiếp.
    """
    if not text:
        return []

    # 1. Tách văn bản thành các câu
    sentences = nltk.sent_tokenize(text)
    
    # 2. Nhóm các câu thành các chunk
    chunks = []
    current_chunk_sentences = []
    current_length = 0
    
    for i, sentence in enumerate(sentences):
        sentence_length = len(sentence)
        
        # Nếu thêm câu này vào sẽ quá dài, hãy hoàn thành chunk hiện tại
        if current_length + sentence_length > chunk_size and current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))
            
            # Bắt đầu chunk mới với sự gối đầu
            # Lấy N câu cuối từ chunk vừa hoàn thành để làm phần gối đầu
            overlap_start_index = max(0, len(current_chunk_sentences) - chunk_overlap_sentences)
            current_chunk_sentences = current_chunk_sentences[overlap_start_index:]
            # Cần tính lại độ dài của chunk mới sau khi có overlap
            current_length = len(" ".join(current_chunk_sentences))

        # Thêm câu vào chunk hiện tại (dù là chunk mới hay cũ)
        current_chunk_sentences.append(sentence)
        current_length += sentence_length

    # Đừng quên chunk cuối cùng
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))
        
    return chunks

def populate_database():
    """
    Hàm chính: Tự động tạo file Markdown nếu cần, đọc nội dung,
    tạo embedding, và lưu vào Milvus.
    """
    download_nltk_punkt() # Đảm bảo NLTK đã sẵn sàng
    logger.info("=== BẮT ĐẦU QUÁ TRÌNH ĐỒNG BỘ DỮ LIỆU VÀO MILVUS ===")
    print("--- BẮT ĐẦU QUÁ TRÌNH ĐỒNG BỘ DỮ LIỆU VÀO MILVUS ---")

    # --- Bước 1: Đảm bảo file Markdown tồn tại ---
    logger.info("Bước 1: Chuẩn bị file Markdown nguồn")
    print("\n--- Bước 1: Chuẩn bị file Markdown nguồn ---")
    md_filename = os.path.splitext(os.path.basename(PDF_PATH))[0] + ".md"
    md_filepath = os.path.join(OUTPUT_DIR, md_filename)

    if not os.path.exists(md_filepath):
        logger.warning(f"File '{md_filename}' không tồn tại trong {OUTPUT_DIR}, tạo mới từ PDF")
        print(f"   -> ⚠️ File '{md_filename}' không tồn tại trong {OUTPUT_DIR}. Tự động tạo mới từ PDF...")
        
        # Tạo thư mục output nếu chưa tồn tại
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        markdown_content = convert_to_markdown(PDF_PATH)
        try:
            with open(md_filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info(f"Đã tạo và lưu file '{md_filename}' vào {OUTPUT_DIR}")
            print(f"   -> ✅ Đã tạo và lưu file '{md_filename}' vào {OUTPUT_DIR}.")
        except Exception as e:
            logger.error(f"Lỗi khi lưu file Markdown: {e}")
            print(f"   -> ❌ Lỗi khi lưu file Markdown: {e}")
            return
    else:
        logger.info(f"Đã tìm thấy file '{md_filename}' trong {OUTPUT_DIR}")
        print(f"   -> ✅ Đã tìm thấy file '{md_filename}' trong {OUTPUT_DIR}.")

    # --- Bước 2: Đọc và xử lý file Markdown ---
    logger.info(f"Bước 2: Đọc file {md_filename}")
    print(f"\n--- Bước 2: Đọc và xử lý file: {md_filename} ---")
    try:
        with open(md_filepath, "r", encoding="utf-8") as f:
            full_content = f.read()
        logger.info(f"Đọc file thành công ({len(full_content)} ký tự)")
    except Exception as e:
        logger.error(f"Lỗi khi đọc file Markdown: {e}")
        print(f"   -> ❌ Lỗi khi đọc file Markdown: {e}")
        return

    # --- Bước 3: Khởi tạo các thành phần cần thiết ---
    model = get_embedding_model()
    if not model:
        logger.error("Không thể tải model embedding")
        return

    logger.info(f"Bước 3: Chuẩn bị collection '{COLLECTION_NAME}' trên Milvus")
    print("\n--- Bước 3: Chuẩn bị collection trên Milvus ---")
    collection = get_or_create_collection(COLLECTION_NAME, dim=EMBEDDING_DIM, recreate=True)

    # --- Bước 4: Phân tách nội dung và tạo chunks ---
    logger.info("Bước 4: Phân tách nội dung và tạo chunks")
    print("\n--- Bước 4: Phân tách nội dung và tạo chunks ---")
    all_chunks = []
    metadata = []

    # Tách file MD thành các trang dựa trên marker
    # Regex để tìm "--- Trang X (Nguồn: Y) ---"
    page_splits = re.split(r'--- Trang (\d+) \(Nguồn: [^)]+\) ---', full_content)

    # Bỏ phần đầu tiên (thường là rỗng hoặc là tiêu đề chính)
    content_parts = page_splits[1:]
    
    if not content_parts:
        logger.warning("Không tìm thấy marker trang trong MD, coi toàn bộ file là 1 trang")
        print("   -> ⚠️ Không tìm thấy marker trang nào trong file MD. Coi toàn bộ file là một trang.")
        page_chunks = chunk_text(full_content)
        all_chunks.extend(page_chunks)
        for _ in page_chunks:
            metadata.append({"pdf_source": os.path.basename(PDF_PATH), "page": 1})
    else:
        # Ghép cặp [số trang, nội dung]
        for i in range(0, len(content_parts), 2):
            page_num = int(content_parts[i])
            page_content = content_parts[i+1].strip()
            
            if not page_content:
                continue

            page_chunks = chunk_text(page_content)
            all_chunks.extend(page_chunks)
            
            # Gán cùng một số trang cho tất cả các chunk của trang đó
            for _ in page_chunks:
                metadata.append({
                    "pdf_source": os.path.basename(PDF_PATH),
                    "page": page_num
                })
        logger.info(f"Xử lý được {len(set(m['page'] for m in metadata))} trang")
        print(f"   -> Đã xử lý và phân tách được {len(set(m['page'] for m in metadata))} trang.")

    if not all_chunks:
        logger.error("Không tìm thấy đoạn văn bản nào để xử lý")
        print("❌ Không tìm thấy đoạn văn bản nào để xử lý.")
        return
    
    logger.info(f"Tổng cộng có {len(all_chunks)} chunks cần xử lý")
    print(f"   -> Tổng cộng có {len(all_chunks)} đoạn văn bản cần xử lý.")

    # --- Bước 5: Tạo embedding cho tất cả các chunks ---
    logger.info("Bước 5: Tạo embeddings cho các đoạn văn bản")
    print("\n--- Bước 5: Tạo embeddings cho các đoạn văn bản ---")
    embeddings = model.encode(all_chunks, show_progress_bar=True)
    logger.info("Tạo embedding hoàn tất")
    print("   -> ✅ Tạo embedding hoàn tất.")

    # --- Bước 6: Chuẩn bị và lưu dữ liệu vào Milvus ---
    logger.info("Bước 6: Lưu dữ liệu vào Milvus")
    print("\n--- Bước 6: Lưu dữ liệu vào Milvus ---")
    entities = [
        embeddings,
        all_chunks,
        [meta['pdf_source'] for meta in metadata],
        [meta['page'] for meta in metadata]
    ]
    
    try:
        insert_result = collection.insert(entities)
        logger.info(f"Chèn thành công {insert_result.insert_count} vectors vào Milvus")
        print(f"   -> ✅ Chèn thành công {insert_result.insert_count} vectors vào Milvus.")
        
        logger.info("Đang flush collection")
        print("   -> Đang flush collection...")
        collection.flush()
        logger.info("Flush hoàn tất")
        print("   -> ✅ Flush hoàn tất.")

    except Exception as e:
        logger.error(f"Lỗi khi chèn dữ liệu vào Milvus: {e}")
        print(f"   -> ❌ Lỗi khi chèn dữ liệu vào Milvus: {e}")

    logger.info("=== QUÁ TRÌNH ĐỒNG BỘ HOÀN TẤT ===")
    print("\n--- QUÁ TRÌNH ĐỒNG BỘ HOÀN TẤT ---")


if __name__ == "__main__":
    populate_database()
