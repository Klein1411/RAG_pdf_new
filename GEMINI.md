# Gemini Project Instructions

This file (GEMINI.md) provides specific instructions and context for the Gemini large language model to understand and interact with this project.

## Project Overview

*   **Project Name:** [RAG PDF reader]
*   **Description:** [This is a rag can read a lot of type of pdf, and maybe can update into an agent, can read language english and vietnamese]
*   **Goals:** [The goals of project is can be a good rag read pdf, can use with docker compose using milvus.]

## Instructions for Gemini

*   **Dos:**
    *   ["Always use the `black` formatter for Python code."]
    *   ["Follow the existing coding style."]
    *   ["Using milvus for vector database, using transformer local for model embeddings (must can vector the picture)"]
    *   ["use gemini api for call llm"]
    *   ["almost use is langchain/langgraph framework"]  
*   **Don'ts:**
    *   ["Do not commit directly to the `main` branch."]

## Key Files

*   `read_pdf.py`: [this file is for read pdf input using gemini model to read, and have case to use the normal read pdf as contingency plan]
*   `milvus_connect.ipynb`: [this file is for the milvus database, import pdf from read_pdf.py then vector it.]
*   `metric.pdf`: [the example pdf, change later]
*   `export_md`: [this file to export the pdf into markdown file]
*   `config`: [where to place the path for other file use]
*   `gemini_client`: [the file to load api key from .env file, setup model and call api all in here]
---

### Giải thích bằng tiếng Việt

Tệp này (GEMINI.md) cung cấp các hướng dẫn và ngữ cảnh cụ thể để mô hình ngôn ngữ lớn Gemini có thể hiểu và tương tác với dự án này. Bạn có thể chỉnh sửa tệp này để đưa ra các chỉ dẫn, mô tả tổng quan về dự án, và xác định các tệp quan trọng, giúp Gemini hỗ trợ bạn một cách hiệu quả và chính xác hơn.
