import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from unittest.mock import MagicMock

def test_pronoun_logic():
    print("\n" + "="*60)
    print("🧪 TEST NHẬN DIỆN XƯNG HÔ ĐỘNG (ANH/CHỊ)")
    print("="*60 + "\n")
    
    # Mock LLM và FAISS để test logic xử lý hậu kỳ (Post-processing)
    orchestrator = AgentOrchestrator()
    orchestrator.memory.search = MagicMock(return_value=None) # Không dùng cache
    
    # Giả lập câu trả lời từ LLM (luôn chứa cụm "Anh/Chị" mặc định)
    raw_ai_response = "Dạ chào Anh/Chị, em rất vui được hỗ trợ Anh/Chị tìm xe máy ạ."
    from services.llm_client import llm_client
    llm_client.generate = MagicMock(return_value=raw_ai_response)
    
    test_cases = [
        {
            "name": "Kịch bản 1: Khách tự xưng là ANH",
            "message": "Anh muốn tìm xe Honda Vision đời 2022."
        },
        {
            "name": "Kịch bản 2: Khách tự xưng là CHỊ",
            "message": "Chị cần tư vấn về thủ tục sang tên xe máy."
        },
        {
            "name": "Kịch bản 3: Khách không xưng tên (Chung chung)",
            "message": "Có xe nào giá tầm 20 triệu không shop?"
        }
    ]
    
    for case in test_cases:
        print(f"🔹 {case['name']}")
        print(f"👉 Khách nhắn: \"{case['message']}\"")
        
        # Chạy qua orchestrator
        result = orchestrator.process_message("test_conv", case['message'], {})
        
        print(f"🤖 AI trả lời: \"{result['message']}\"")
        print("-" * 40 + "\n")

if __name__ == "__main__":
    test_pronoun_logic()
