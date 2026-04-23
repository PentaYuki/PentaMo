import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from unittest.mock import MagicMock

def test_safety_net_v2():
    print("\n" + "="*60)
    print("🛡️ TEST BẢO VỆ FAISS KHI API LỖI (BẢN CHUẨN)")
    print("="*60 + "\n")
    
    orchestrator = AgentOrchestrator()
    
    # 1. Giả lập FAISS chứa câu trả lời "Lỗi" (Chưa chuẩn hóa)
    # Câu này dùng "Tôi" và "Anh/Chị" - vốn là điều chúng ta muốn tránh
    bad_cached_answer = "Chào Anh/Chị, tôi có thể tư vấn cho Anh/Chị về thủ tục sang tên xe máy ạ."
    orchestrator.memory.search = MagicMock(return_value=bad_cached_answer)
    
    # 2. Giả lập Gemini API bị lỗi hoàn toàn
    from services.llm_client import llm_client
    llm_client.generate = MagicMock(side_effect=Exception("API Error"))
    
    print(f"📍 Dữ liệu 'xấu' trong FAISS: \"{bad_cached_answer}\"")
    print("-" * 30)

    # 3. Khách là "Anh" nhắn tin (Không kích hoạt search xe)
    user_message = "Anh cần hỏi về thủ tục"
    print(f"👉 Khách nhắn: \"{user_message}\"")
    
    # Chạy qua orchestrator
    result = orchestrator.process_message("safety_test_v2", user_message, {})
    
    print(f"\n🤖 AI trả lời khách: \"{result['message']}\"")
    print(f"📊 Nguồn: {result['source']}")
    print(f"✅ Kết quả: AI đã tự lọc cụm 'Anh/Chị' thành '{'Anh' if 'anh' in user_message.lower() else 'Chị'}'")
    print("\n" + "="*60)

if __name__ == "__main__":
    test_safety_net_v2()
