import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from unittest.mock import MagicMock

def test_safety_net():
    print("\n" + "="*60)
    print("🛡️ TEST CƠ CHẾ BẢO VỆ CUỐI CÙNG (SAFETY NET)")
    print("="*60 + "\n")
    
    orchestrator = AgentOrchestrator()
    
    # 1. Giả lập FAISS đang chứa một câu trả lời "Lỗi" (Chưa chuẩn hóa xưng hô)
    bad_cached_answer = "Chào Anh/Chị, tôi là robot, Anh/Chị cần mua xe gì?"
    orchestrator.memory.search = MagicMock(return_value=bad_cached_answer)
    
    # 2. Giả lập tình huống Gemini API bị chết (Hết lượt gọi)
    from services.llm_client import llm_client
    llm_client.generate = MagicMock(side_effect=Exception("API Limit Exceeded"))
    
    print("📍 Tình huống: FAISS chứa câu chưa chuẩn, Gemini API bị lỗi.")
    print(f"📍 Câu trong bộ nhớ: \"{bad_cached_answer}\"")
    print("-" * 30)

    # 3. Khách hàng là "Anh" nhắn tin
    user_message = "Anh muốn mua xe máy"
    print(f"👉 Khách nhắn: \"{user_message}\"")
    
    # Chạy qua orchestrator
    result = orchestrator.process_message("safety_test", user_message, {})
    
    print(f"\n🤖 AI trả lời khách: \"{result['message']}\"")
    print(f"📊 Nguồn: {result['source']}")
    print(f"💡 Ghi chú: Dù API lỗi và bộ nhớ chưa chuẩn, AI vẫn phải gọi đúng là 'Anh'.")
    print("\n" + "="*60)

if __name__ == "__main__":
    test_safety_net()
