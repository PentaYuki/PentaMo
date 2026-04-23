import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from unittest.mock import MagicMock

def test_ai_scenarios():
    print("\n" + "="*60)
    print("🚀 TEST CÁC KỊCH BẢN PHẢN HỒI THỰC TẾ (Bypass Cache)")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    orchestrator.memory.search = MagicMock(return_value=None)

    
    scenarios = [
        {
            "name": "Kịch bản 1: Hỏi mua xe với mức giá cụ thể (15 triệu)",
            "message": "Hôm nay anh muốn mua xe giá tầm 15 triệu"
        },
        {
            "name": "Kịch bản 2: Mua xe cho con (Đã được nâng cấp để tâm lý hơn)",
            "message": "Anh muốn mua xe cho con anh, em tư vấn giúp anh"
        },
        {
            "name": "Kịch bản 3: Sinh viên mới ra trường",
            "message": "Em mới ra trường, muốn tìm chiếc xe nào đi làm cho bền, tài chính cũng eo hẹp. Tư vấn giúp em."
        },
        {
            "name": "Kịch bản 4: Phụ nữ chân yếu tay mềm",
            "message": "Chị là phụ nữ, tay lái yếu, muốn tìm chiếc nào dắt nhẹ nhẹ thôi."
        }
    ]
    
    try:
        for i, sc in enumerate(scenarios, 1):
            print(f"🔹 {sc['name']}")
            print(f"👉 Khách nhắn: \"{sc['message']}\"")
            
            result = orchestrator.process_message(f"scenario_test_{i}", sc['message'], {}, db=db)
            
            print(f"🤖 AI trả lời:\n{result['message']}")
            print("-" * 40 + "\n")

        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_ai_scenarios()
