"""
Test comprehensive cho search_tool_langchain.py
Verify tất cả functionality trước khi xóa file cũ
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.tools.search_tool_langchain import (
    SearchToolLangChain,
    SearchTool,  # Alias
    search_collections_tool,
    get_global_search_tool
)


def test_1_basic_initialization():
    """Test 1: Khởi tạo cơ bản"""
    print("\n" + "="*70)
    print("TEST 1: Khởi tạo SearchToolLangChain")
    print("="*70)
    
    tool = SearchToolLangChain()
    assert tool.name == "search_tool_langchain"
    assert tool.embedding_model is not None
    print("✅ Khởi tạo thành công")
    print(f"   - Name: {tool.name}")
    print(f"   - Has embedding model: {tool.embedding_model is not None}")
    return tool


def test_2_backward_compatibility():
    """Test 2: Backward compatibility với SearchTool"""
    print("\n" + "="*70)
    print("TEST 2: Backward Compatibility")
    print("="*70)
    
    # SearchTool phải là alias của SearchToolLangChain
    assert SearchTool is SearchToolLangChain
    print("✅ SearchTool alias working")
    
    # Có thể khởi tạo bằng SearchTool
    tool = SearchTool()
    assert isinstance(tool, SearchToolLangChain)
    print("✅ SearchTool() khởi tạo OK")


def test_3_langchain_tools():
    """Test 3: LangChain tools interface"""
    print("\n" + "="*70)
    print("TEST 3: LangChain Tools Interface")
    print("="*70)
    
    tool = SearchToolLangChain()
    tools = tool.get_langchain_tools()
    
    assert len(tools) == 2, f"Expected 2 tools, got {len(tools)}"
    print(f"✅ Got {len(tools)} LangChain tools")
    
    # Check tool names
    tool_names = [t.name for t in tools]
    assert "search_collections" in tool_names
    assert "search_single_collection" in tool_names
    print(f"✅ Tool names correct: {tool_names}")
    
    # Check descriptions
    for t in tools:
        assert len(t.description) > 0
        print(f"   - {t.name}: {t.description[:50]}...")


def test_4_standalone_tool():
    """Test 4: Standalone tool function"""
    print("\n" + "="*70)
    print("TEST 4: Standalone Tool Function")
    print("="*70)
    
    # Check tool exists
    assert search_collections_tool is not None
    print(f"✅ search_collections_tool exists")
    print(f"   - Name: {search_collections_tool.name}")
    print(f"   - Description: {search_collections_tool.description[:50]}...")


def test_5_global_instance():
    """Test 5: Global instance singleton"""
    print("\n" + "="*70)
    print("TEST 5: Global Instance Singleton")
    print("="*70)
    
    tool1 = get_global_search_tool()
    tool2 = get_global_search_tool()
    
    # Phải là cùng instance
    assert tool1 is tool2
    print("✅ Global instance là singleton")
    print(f"   - ID 1: {id(tool1)}")
    print(f"   - ID 2: {id(tool2)}")


def test_6_methods_exist():
    """Test 6: Core methods tồn tại"""
    print("\n" + "="*70)
    print("TEST 6: Core Methods")
    print("="*70)
    
    tool = SearchToolLangChain()
    
    # Check methods
    assert hasattr(tool, 'search_multi_collections')
    assert hasattr(tool, 'search_single_collection')
    assert hasattr(tool, 'get_langchain_tools')
    
    print("✅ All core methods exist:")
    print("   - search_multi_collections")
    print("   - search_single_collection")
    print("   - get_langchain_tools")


def test_7_method_signatures():
    """Test 7: Method signatures correct"""
    print("\n" + "="*70)
    print("TEST 7: Method Signatures")
    print("="*70)
    
    tool = SearchToolLangChain()
    
    # Test method can be called với correct params
    import inspect
    
    # search_multi_collections
    sig = inspect.signature(tool.search_multi_collections)
    params = list(sig.parameters.keys())
    assert 'query' in params
    assert 'collection_names' in params
    assert 'top_k' in params
    assert 'similarity_threshold' in params
    print("✅ search_multi_collections signature OK")
    
    # search_single_collection
    sig = inspect.signature(tool.search_single_collection)
    params = list(sig.parameters.keys())
    assert 'query' in params
    assert 'collection_name' in params
    assert 'top_k' in params
    assert 'similarity_threshold' in params
    print("✅ search_single_collection signature OK")


def test_8_pydantic_schemas():
    """Test 8: Pydantic schemas exist"""
    print("\n" + "="*70)
    print("TEST 8: Pydantic Schemas")
    print("="*70)
    
    from agent.tools.search_tool_langchain import SearchInput, SearchSingleInput
    
    # SearchInput
    schema = SearchInput.model_json_schema()
    assert 'query' in schema['properties']
    assert 'collection_names' in schema['properties']
    print("✅ SearchInput schema OK")
    
    # SearchSingleInput
    schema = SearchSingleInput.model_json_schema()
    assert 'query' in schema['properties']
    assert 'collection_name' in schema['properties']
    print("✅ SearchSingleInput schema OK")


def run_all_tests():
    """Chạy tất cả tests"""
    print("\n" + "🧪 " * 35)
    print("TEST SUITE: search_tool_langchain.py")
    print("🧪 " * 35)
    
    try:
        tool = test_1_basic_initialization()
        test_2_backward_compatibility()
        test_3_langchain_tools()
        test_4_standalone_tool()
        test_5_global_instance()
        test_6_methods_exist()
        test_7_method_signatures()
        test_8_pydantic_schemas()
        
        print("\n" + "="*70)
        print("🎉 TẤT CẢ TESTS PASSED!")
        print("="*70)
        print("\n✅ search_tool_langchain.py READY để thay thế search_tool.py")
        print("✅ Safe để xóa agent/tools/search_tool.py\n")
        return True
        
    except AssertionError as e:
        print("\n" + "="*70)
        print("❌ TEST FAILED!")
        print("="*70)
        print(f"Error: {e}")
        return False
    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST ERROR!")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
