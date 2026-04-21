# 🏍️ PentaMo V3 - Hệ Thống Trợ Lý AI Chuyên Gia Xe Máy

Hệ thống tư vấn và giao dịch xe máy thông minh, tích hợp đa mô hình ngôn ngữ (Llama 3.2, Gemini) và tìm kiếm ngữ nghĩa FAISS.

## 🏗️ Kiến Trúc Hệ Thống (Architecture)

PentaMo V3 được xây dựng theo kiến trúc phân lớp (Layered Architecture) đảm bảo tính ổn định và khả năng mở rộng:

### 1. Entry Points (Cổng vào)
*   **`run.sh`**: Script khởi động chuẩn, cấu hình sẵn môi trường Offline AI và tối ưu hóa CPU.
*   **`backend/main.py`**: Điểm đầu của API FastAPI, quản lý các endpoint `/chat`, `/admin`, `/auth`.

### 2. Core Logic (Bộ não)
*   **`backend/orchestrator_v3.py`**: Điều phối luồng xử lý 7 bước (Safety -> Intent -> Search -> Cache -> LLM -> History -> Feedback).
*   **`services/llm_client.py`**: Quản lý kết nối LLM với cơ chế **Ollama Primary -> Gemini Fallback**.
*   **`services/faiss_memory.py`**: Semantic Cache giúp phản hồi tức thì các câu hỏi quen thuộc.

### 3. Services & Tools (Công cụ)
*   **`tools/handlers_v2.py`**: Xử lý truy vấn database thực tế (tìm xe theo giá, hãng, khu vực).
*   **`services/conversation_service.py`**: Tổng hợp dữ liệu hội thoại cho Dashboard Admin.
*   **`services/user_service.py`**: Quản lý định danh và quyền hạn người dùng.

### 4. AI Agent System (Hệ thống AI)
*   **Kiến trúc thực tế**: [V3_ARCHITECTURE.md](file:///Users/gooleseswsq1gmail.com/Documents/pentaMo/documentation/ARCHITECTURE/V3_ARCHITECTURE.md) - Hướng dẫn chi tiết luồng xử lý Agentic V3.
*   **Báo cáo Đánh giá**: [AI_EVALUATION_REPORT.md](file:///Users/gooleseswsq1gmail.com/Documents/pentaMo/documentation/REPORTS/AI_EVALUATION_REPORT.md) - Phân tích hiệu quả và rủi ro.
*   **Hướng dẫn & Tham khảo**: Xem thêm trong thư mục `documentation/GUIDES/`.

### 4. Configuration (Cấu hình)
*   **`.env`**: Nơi lưu trữ Key API, Model Name và các ngưỡng Threshold.
*   **`config/settings.py`**: Load và validate cấu hình từ môi trường.

## 📊 Quản lý Dữ liệu & Luồng thông tin

Hệ thống xử lý dữ liệu theo chu kỳ khép kín để đảm bảo AI luôn "hiểu" khách hàng:

### 1. Trích xuất Thực thể (Extraction)
*   **Cơ chế**: Sử dụng Regex và Keyword Matching trong `orchestrator_v3.py`.
*   **Dữ liệu bóc tách**: Ngân sách (Budget), Hãng xe (Brands), Khu vực (Location).

### 2. Lưu trữ (Persistence)
*   **Cơ sở dữ liệu**: SQLAlchemy (SQLite/Postgres).
*   **Trạng thái phiên (Session State)**: Lưu tại bảng `Conversations` (cột `state` kiểu JSON), cho phép AI nhớ khách hàng đang cần gì mà không cần hỏi lại.
*   **Lịch sử**: Bảng `ChatMessages` lưu trữ toàn bộ văn bản hội thoại.

### 3. Truy xuất & Phản hồi (Retrieval)
*   AI dùng dữ liệu đã trích xuất để truy vấn bảng `SellerListings`.
*   Kết quả được đưa vào Prompt làm ngữ cảnh (Context) để AI trả lời cá nhân hóa.

### 4. Quản lý Tin đăng & Xe (Listing Management)
*   **Module nghiệp vụ**: `services/listing_service.py` chịu trách nhiệm xử lý luồng đăng tin của người bán (Sellers).
*   **Lưu trữ**: Bảng `SellerListings` trong cơ sở dữ liệu lưu giữ toàn bộ thông tin xe, bao gồm cả dữ liệu OCR từ giấy tờ xe và hình ảnh 4 chiều.
*   **Xác thực**: Tích hợp các module hỗ trợ kiểm tra giấy tờ tự động và chấm điểm tin cậy của hình ảnh.

## 🔗 Liên Kết Giữa Các File

1.  **Luồng Chat**: `User Request` -> `main.py` -> `orchestrator_v3.py` -> `llm_client.py` -> `Response`.
2.  **Luồng Tìm Xe**: `orchestrator_v3.py` nhận diện ý định -> `handlers_v2.py` gọi Database -> Trả kết quả về cho LLM tóm tắt.
3.  **Luồng Học Tập**: `Feedback` từ người dùng -> `db` -> `sync_feedback_to_faiss.py` -> `faiss_memory` (AI tự khôn lên).

## 🚀 Khởi Chạy Nhanh

1.  **Cài đặt**: `./setup.sh`
2.  **Tải Model**: `ollama pull llama3.2`
3.  **Chạy Server**: `./run.sh`

## 🛠 Bảo Trì
*   Đồng bộ bộ nhớ: `python scripts/sync_feedback_to_faiss.py`
*   Kiểm tra AI: `python scripts/verify_llm_priority.py`

---
*Phát triển bởi Đội ngũ PentaMo - V3 Advanced Intelligence.*
