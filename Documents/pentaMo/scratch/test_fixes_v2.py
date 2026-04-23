import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from unittest.mock import MagicMock

def test_fixes_v2():
    print("\n" + "="*60)
    print("🚀 TEST CÁC LỖI VỪA FIX (PROVINCE & SEARCH INTENT)")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    # Bypass FAISS to see real logic
    orchestrator.memory.search = MagicMock(return_value=None)
    
    scenarios = [
        {
            "name": "Kịch bản 1: Chỉ hỏi tỉnh thành (Lỗi cũ: Trả lời vòng vo)",
            "message": "xe ở thành phố hồ chí minh"
        },
        {
            "name": "Kịch bản 2: Hỏi giá (Đảm bảo lọc đúng 15tr)",
            "message": "xe tầm 15 triệu"
        }
    ]
    
    try:
        for i, sc in enumerate(scenarios, 1):
            print(f"🔹 {sc['name']}")
            print(f"👉 Khách nhắn: \"{sc['message']}\"")
            
            result = orchestrator.process_message(f"fix_test_{i}", sc['message'], {}, db=db)
            
            print(f"🤖 AI trả lời:\n{result['message']}")
            print(f"📊 Nguồn xử lý: {result['source']}")
            
            # Check if UI commands contain the correct params
            ui_cmds = result.get("ui_commands", [])
            for cmd in ui_cmds:
                if cmd['action'] == 'AUTO_SEARCH':
                    print(f"✅ UI Command AUTO_SEARCH: {cmd['params']}")

            print("-" * 40 + "\n")

        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_fixes_v2()
