import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from services.faiss_memory import get_faiss_memory
from services.llm_client import set_review_llm

def test_filter():
    print("\n" + "="*50)
    print("🔍 KIỂM TRA BỘ LỌC LLM (GATE LLM)")
    print("="*50 + "\n")
    
    db = SessionLocal()
    memory = get_faiss_memory()
    
    # Đảm bảo đang dùng Gemini để kiểm duyệt
    set_review_llm("gemini")
    
    # Kịch bản 1: Tin nhắn xưng hô chưa chuẩn (Dùng "tôi", "ông")
    print("Kịch bản 1: Chỉnh sửa xưng hô và thái độ")
    question_1 = "Xe này còn bớt không em?"
    answer_1 = "Tôi đã nói rồi, giá này là rẻ nhất thị trường, ông không tìm được chỗ nào rẻ hơn đâu."
    
    print(f"👉 Câu hỏi: {question_1}")
    print(f"👉 Trả lời gốc: {answer_1}")
    print("... Đang qua bộ lọc Gemini ...")
    
    result_1 = memory.gate_and_add(question_1, answer_1, mode="consultant", db_session=db)
    
    print(f"✨ Trạng thái: {result_1['status']}")
    print(f"✨ Câu sau khi lọc: {result_1['answer']}")
    print("-" * 30 + "\n")

    # Kịch bản 2: Tin nhắn quá dài dòng hoặc không chuyên nghiệp
    print("Kịch bản 2: Làm gọn và chuyên nghiệp hóa")
    question_2 = "Địa chỉ shop ở đâu?"
    answer_2 = "Shop mình ở số 123 đường ABC quận 1 nhé bạn ơi, bên mình mở cửa từ 8h sáng tới 10h đêm, bạn cứ qua lúc nào cũng được nha, rất hân hạnh được đón tiếp bạn yêu."
    
    print(f"👉 Câu hỏi: {question_2}")
    print(f"👉 Trả lời gốc: {answer_2}")
    print("... Đang qua bộ lọc Gemini ...")
    
    result_2 = memory.gate_and_add(question_2, answer_2, mode="consultant", db_session=db)
    
    print(f"✨ Trạng thái: {result_2['status']}")
    print(f"✨ Câu sau khi lọc: {result_2['answer']}")
    print("="*50 + "\n")

    db.close()

if __name__ == "__main__":
    test_filter()
