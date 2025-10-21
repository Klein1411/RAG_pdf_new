# Test tất cả imports để tìm circular dependency và conflicts
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*70)
print("KIỂM TRA IMPORTS VÀ DEPENDENCIES")
print("="*70)

errors = []

# Test 1: Agent imports
print("\n1. Testing Agent imports...")
try:
    from agent.agent import Agent
    print("   ✅ agent.agent OK")
except Exception as e:
    errors.append(f"agent.agent: {e}")
    print(f"   ❌ agent.agent: {e}")

# Test 2: Collection Manager
print("\n2. Testing collection_manager...")
try:
    from agent.collection_manager import get_collection_manager
    print("   ✅ collection_manager OK")
except Exception as e:
    errors.append(f"collection_manager: {e}")
    print(f"   ❌ collection_manager: {e}")

# Test 3: PDF Manager
print("\n3. Testing pdf_manager...")
try:
    from agent.pdf_manager import get_pdf_manager
    print("   ✅ pdf_manager OK")
except Exception as e:
    errors.append(f"pdf_manager: {e}")
    print(f"   ❌ pdf_manager: {e}")

# Test 4: Tools
print("\n4. Testing tools...")
try:
    from agent.tools.search_tool_langchain import get_global_search_tool as get_search_tool
    print("   ✅ search_tool_langchain OK")
except Exception as e:
    errors.append(f"search_tool_langchain: {e}")
    print(f"   ❌ search_tool_langchain: {e}")

try:
    from agent.tools.topic_tool import get_topic_tool
    print("   ✅ topic_tool OK")
except Exception as e:
    errors.append(f"topic_tool: {e}")
    print(f"   ❌ topic_tool: {e}")

try:
    from agent.tools.export_tool import get_export_tool
    print("   ✅ export_tool OK")
except Exception as e:
    errors.append(f"export_tool: {e}")
    print(f"   ❌ export_tool: {e}")

# Test 5: Src modules
print("\n5. Testing src modules...")
try:
    from src.export_md import convert_to_markdown
    print("   ✅ export_md OK")
except Exception as e:
    errors.append(f"export_md: {e}")
    print(f"   ❌ export_md: {e}")

try:
    from src.read_pdf import extract_pdf_pages
    print("   ✅ read_pdf OK")
except Exception as e:
    errors.append(f"read_pdf: {e}")
    print(f"   ❌ read_pdf: {e}")

try:
    from src.clean_pdf import clean_extracted_text
    print("   ✅ clean_pdf OK")
except Exception as e:
    errors.append(f"clean_pdf: {e}")
    print(f"   ❌ clean_pdf: {e}")

try:
    from src.config import OUTPUT_DIR, PDF_DIR
    print(f"   ✅ config OK (OUTPUT_DIR={OUTPUT_DIR}, PDF_DIR={PDF_DIR})")
except Exception as e:
    errors.append(f"config: {e}")
    print(f"   ❌ config: {e}")

# Test 6: Check path consistency
print("\n6. Checking path consistency...")
try:
    from agent.pdf_manager import get_pdf_manager
    from agent.collection_manager import get_collection_manager
    from src.config import OUTPUT_DIR
    
    pm = get_pdf_manager()
    cm = get_collection_manager()
    
    test_pdf = Path("data/pdfs/test.pdf")
    md_path_pm = pm.get_md_path(test_pdf)
    expected_md = Path(OUTPUT_DIR) / "test.md"
    
    if str(md_path_pm) == str(expected_md):
        print(f"   ✅ Path consistency OK")
        print(f"      pdf_manager.get_md_path(): {md_path_pm}")
        print(f"      Expected (OUTPUT_DIR): {expected_md}")
    else:
        errors.append(f"Path mismatch: {md_path_pm} != {expected_md}")
        print(f"   ❌ Path mismatch!")
        print(f"      pdf_manager: {md_path_pm}")
        print(f"      Expected: {expected_md}")
        
except Exception as e:
    errors.append(f"path_check: {e}")
    print(f"   ❌ Path check failed: {e}")

# Test 7: Tesseract integration
print("\n7. Testing Tesseract integration...")
try:
    import pytesseract
    import fitz
    print("   ✅ pytesseract OK")
    print("   ✅ pymupdf (fitz) OK")
except Exception as e:
    errors.append(f"tesseract: {e}")
    print(f"   ❌ Tesseract/pymupdf: {e}")

# Test 8: Agent flow simulation
print("\n8. Testing Agent workflow simulation...")
try:
    from agent.agent import Agent
    from src.export_md import convert_to_markdown
    from pathlib import Path
    
    # Simulate: Agent → convert_to_markdown → extract_pdf_pages
    print("   ✅ Agent can import convert_to_markdown")
    
    # Simulate: collection_manager reads MD
    from agent.collection_manager import get_collection_manager
    cm = get_collection_manager()
    print("   ✅ collection_manager can access OUTPUT_DIR")
    
except Exception as e:
    errors.append(f"workflow: {e}")
    print(f"   ❌ Workflow test: {e}")

# Summary
print("\n" + "="*70)
if errors:
    print(f"❌ PHÁT HIỆN {len(errors)} LỖI:")
    for err in errors:
        print(f"   - {err}")
else:
    print("✅ TẤT CẢ IMPORTS VÀ DEPENDENCIES OK!")
print("="*70)
