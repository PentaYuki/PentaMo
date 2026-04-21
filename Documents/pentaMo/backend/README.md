# 🧠 Backend Core - PentaMo

Thư mục này chứa toàn bộ logic xử lý phía máy chủ (Server-side) của hệ thống PentaMo, được xây dựng trên nền tảng **FastAPI**.

## 📂 Các thành phần chính:

- **`main.py`**: Điểm khởi đầu của ứng dụng. Nơi đăng ký các router và middleware.
- **`orchestrator_v3.py`**: Bộ não điều phối AI. Xử lý luồng đi của tin nhắn từ lúc khách nhắn đến khi AI phản hồi.
- **`database.py`**: Cấu hình SQLAlchemy và quản lý kết nối tới SQLite/PostgreSQL.
- **`security.py`**: Xử lý phân quyền (Rate Limiting) và bảo mật cho các tool của AI.
- **`action_planner.py`**: Module lập kế hoạch hành động. Quyết định khi nào AI nên gọi tool và tại sao.

---

## 🚀 Luồng xử lý tin nhắn (Pipeline):
`Request` -> `main.py` -> `orchestrator_v3.py` -> `action_planner.py` -> `llm_client.py` -> `Response`.
