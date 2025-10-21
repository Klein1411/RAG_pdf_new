# 🔄 MIGRATION PLAN: Custom → LangChain

## 📋 MIGRATION ORDER (Từ cốt lõi → peripheral)

### **PHASE 1: LLM Integration** ⭐⭐⭐⭐⭐ (PRIORITY 1)
**Files:** `src/llm_handler.py`, `src/gemini_client.py`

**Current:** Custom Gemini + Ollama handling
**Target:** LangChain LLM abstraction

**Benefits:**
- ✅ Unified LLM interface
- ✅ Easy provider switching
- ✅ Built-in retry logic
- ✅ Streaming support

**Implementation:**
```python
# Before: src/llm_handler.py
def call_gemini(prompt, gemini_client):
    return gemini_client.generate_content(prompt)

def call_ollama(prompt, model_name):
    # Manual HTTP calls
    
# After: src/llm_langchain.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.llms import Ollama

gemini_llm = ChatGoogleGenerativeAI(model="gemini-pro")
ollama_llm = Ollama(model="llama2")

response = llm.invoke(prompt)
```

**Migration Steps:**
1. Install dependencies: `langchain`, `langchain-google-genai`, `langchain-ollama`
2. Create `src/llm_langchain.py` wrapper
3. Update `agent/agent.py` to use LangChain LLM
4. Test both Gemini & Ollama
5. Deprecate old llm_handler.py

---

### **PHASE 2: Vector Store** ⭐⭐⭐⭐ (PRIORITY 2)
**Files:** `src/milvus.py`, `src/populate_milvus.py`, `agent/tools/search_tool.py`

**Current:** Direct pymilvus calls
**Target:** LangChain Milvus vectorstore

**Benefits:**
- ✅ Unified vectorstore API
- ✅ Easy DB switching (Milvus → Pinecone → ChromaDB)
- ✅ Built-in similarity search
- ✅ Document management

**Implementation:**
```python
# Before: agent/tools/search_tool.py
from pymilvus import Collection
query_vector = embedding_model.encode(query)
results = collection.search(data=[query_vector], limit=top_k)

# After: agent/tools/search_tool_langchain.py
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Milvus(
    embedding_function=embeddings,
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="my_collection"
)

results = vectorstore.similarity_search_with_score(query, k=top_k)
```

**Migration Steps:**
1. Install: `langchain-milvus`, `langchain-huggingface`
2. Create `src/vectorstore_langchain.py`
3. Wrap Milvus with LangChain interface
4. Update SearchTool to use LangChain
5. Test search functionality
6. Keep pymilvus for collection management (admin operations)

---

### **PHASE 3: RAG Chain** ⭐⭐⭐⭐⭐ (PRIORITY 3)
**Files:** `agent/tools/rag_tool.py`

**Current:** Manual RAG workflow
**Target:** LangChain RAG chains

**Benefits:**
- ✅ Built-in retrieval + generation
- ✅ Source tracking
- ✅ Chain composition
- ✅ Memory integration

**Implementation:**
```python
# Before: agent/tools/rag_tool.py
results = search_tool.search(query)
context = format_context(results)
answer = llm.generate_content(prompt_with_context)

# After: agent/tools/rag_tool_langchain.py
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 20}),
    return_source_documents=True
)

result = qa_chain({"query": question})
```

**Migration Steps:**
1. Create custom prompt templates
2. Build RetrievalQA chain
3. Test with conversation history
4. Handle multi-collection search (custom)
5. Integrate with Agent

---

### **PHASE 4: Memory** ⭐⭐⭐⭐ (PRIORITY 4)
**Files:** `agent/conversation_history.py`

**Current:** Simple list-based history
**Target:** LangChain memory

**Benefits:**
- ✅ Multiple memory types
- ✅ Automatic token management
- ✅ Persistence
- ✅ Summary generation

**Implementation:**
```python
# Before: agent/conversation_history.py
class ConversationHistory:
    def __init__(self):
        self.history = []

# After: agent/memory_langchain.py
from langchain.memory import ConversationBufferWindowMemory

memory = ConversationBufferWindowMemory(
    k=10,
    return_messages=True,
    memory_key="chat_history"
)
```

**Migration Steps:**
1. Install LangChain memory
2. Create memory wrapper
3. Integrate with RAG chain
4. Test truncation & persistence
5. Optional: Add ConversationSummaryMemory

---

### **PHASE 5: Agent (Optional)** ⭐⭐⭐ (PRIORITY 5)
**Files:** `agent/agent.py`

**Current:** Manual intent detection + routing
**Target:** LangChain Agent (optional)

**Benefits:**
- ✅ Intelligent tool selection
- ✅ Multi-step reasoning
- ✅ Built-in memory

**Decision:** KEEP CUSTOM (khuyến nghị)
- Deterministic routing tốt hơn
- Performance better
- Easier debugging

**If migrate:**
```python
from langchain.agents import initialize_agent, Tool

tools = [
    Tool(name="RAG", func=rag_chain.invoke, description="..."),
    Tool(name="Topics", func=topic_tool.get_suggestions, description="...")
]

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory
)
```

---

### **PHASE 6: Prompt Templates** ⭐⭐⭐ (PRIORITY 6)
**Files:** Various prompt strings in tools

**Current:** String formatting
**Target:** LangChain PromptTemplate

**Benefits:**
- ✅ Centralized prompts
- ✅ Validation
- ✅ Versioning
- ✅ Partial variables

**Implementation:**
```python
# Before: Scattered strings
prompt = f"Context: {context}\nQuestion: {question}\nAnswer:"

# After: src/prompts_langchain.py
from langchain.prompts import PromptTemplate

RAG_PROMPT = PromptTemplate(
    template="""Context: {context}
History: {history}
Question: {question}

Answer:""",
    input_variables=["context", "history", "question"]
)
```

---

## 📊 TIMELINE

### **Week 1-2: LLM Integration**
- Day 1-2: Install dependencies & setup
- Day 3-4: Create llm_langchain.py wrapper
- Day 5-6: Integrate with Agent
- Day 7: Testing & validation

### **Week 3-4: Vector Store**
- Day 1-3: Wrap Milvus with LangChain
- Day 4-5: Update SearchTool
- Day 6-7: Multi-collection handling & testing

### **Week 5-6: RAG Chain**
- Day 1-2: Build RetrievalQA chain
- Day 3-4: Custom prompt templates
- Day 5-6: Integration & testing
- Day 7: Performance optimization

### **Week 7: Memory**
- Day 1-2: Implement ConversationBufferWindowMemory
- Day 3-4: Integration with RAG
- Day 5: Testing

### **Week 8: Cleanup & Documentation**
- Deprecate old code
- Update documentation
- Performance benchmarking
- Final testing

---

## ⚠️ RISKS & MITIGATION

### **Risk 1: Performance Degradation**
- **Mitigation**: Benchmark before/after each phase
- **Threshold**: <20% performance hit acceptable

### **Risk 2: Breaking Changes**
- **Mitigation**: Keep both old & new code during transition
- **Strategy**: Feature flags for A/B testing

### **Risk 3: Multi-collection Search**
- **Issue**: LangChain doesn't support multi-collection natively
- **Solution**: Custom retriever class extending BaseRetriever

### **Risk 4: Dependency Bloat**
- **Issue**: LangChain adds many dependencies
- **Mitigation**: Use `langchain-core` only, add providers as needed

---

## ✅ SUCCESS CRITERIA

### **Per Phase:**
1. All existing tests pass
2. Performance within 20% of baseline
3. Code coverage maintained
4. Documentation updated

### **Overall:**
1. ✅ Easier LLM provider switching
2. ✅ Better code maintainability
3. ✅ Access to LangChain ecosystem
4. ✅ No regression in functionality

---

## 🎯 RECOMMENDED APPROACH

**START WITH:** Phase 1 (LLM Integration)
- Highest value
- Lowest risk
- Independent from other components
- Immediate benefits (retry logic, streaming)

**THEN:** Phase 2 → Phase 3 → Phase 4

**SKIP:** Phase 5 (Agent) - Keep custom routing

**ALWAYS:** Maintain backward compatibility during transition

---

**Next Steps:**
1. Review & approve plan
2. Install initial dependencies
3. Begin Phase 1: LLM Integration
