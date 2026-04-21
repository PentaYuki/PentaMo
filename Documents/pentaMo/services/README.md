# 🛠️ Services Layer

Thư mục chứa các dịch vụ logic độc lập được sử dụng bởi Orchestrator.

- **`llm_client.py`**: Cổng kết nối với các mô hình ngôn ngữ (Ollama, Gemini).
- **`memory_service.py`**: Quản lý bộ nhớ 3 tầng (Raw, Structured, Summary).
- **`evaluation_service.py`**: Theo dõi chỉ số và đánh giá hiệu năng của AI.
- **`faiss_memory.py`**: Xử lý lưu trữ và tìm kiếm vector cho bộ nhớ ngữ nghĩa.
