"""
Script kiểm tra Milvus collection
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from pymilvus import Collection
from pymilvus import connections

def check_collection():
    """Kiểm tra collection info"""
    print("\n=== Checking Milvus Collection ===\n")
    
    # Connect to Milvus
    print("1. Connecting to Milvus...")
    connections.connect(host="localhost", port="19530")
    print(f"   ✅ Connected")
    
    # Load collection
    print("\n2. Loading collection 'pdf_rag_collection'...")
    collection = Collection("pdf_rag_collection")
    collection.load()
    print(f"   ✅ Loaded")
    
    # Get stats
    print("\n3. Collection Statistics:")
    num_entities = collection.num_entities
    print(f"   - Number of entities: {num_entities}")
    
    # Get schema info
    print("\n4. Schema Info:")
    for field in collection.schema.fields:
        print(f"   - {field.name}: {field.dtype}")
    
    # Get index info
    print("\n5. Index Info:")
    for index in collection.indexes:
        print(f"   - Field: {index.field_name}")
        print(f"   - Index type: {index.params.get('index_type')}")
        print(f"   - Metric type: {index.params.get('metric_type')}")
        print(f"   - Params: {index.params.get('params')}")
    
    # Try a simple query
    if num_entities > 0:
        print("\n6. Sample Query (first 5 entities):")
        results = collection.query(
            expr="id >= 0",
            output_fields=["text", "page", "pdf_source"],
            limit=5
        )
        for i, result in enumerate(results, 1):
            print(f"\n   Entity {i}:")
            print(f"   - Text: {result['text'][:100]}...")
            print(f"   - Page: {result['page']}")
            print(f"   - Source: {result['pdf_source']}")
    
    print("\n=== Check completed ===")

if __name__ == "__main__":
    check_collection()
