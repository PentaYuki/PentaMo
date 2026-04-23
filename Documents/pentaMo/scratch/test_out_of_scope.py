import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal

def test_out_of_scope():
    print("\n" + "="*60)
    print("🛑 TEST TỪ CHỐI CÂU HỎI KHÔNG LIÊN QUAN (OUT OF SCOPE)")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    
    scenarios = [
        {
            "name": "Kịch bản 1: Hỏi về tình yêu / tâm sự mỏng",
            "message": "Em ơi anh đang thất tình buồn quá, tư vấn tình yêu cho anh được không?"
        },
        {
            "name": "Kịch bản 2: Hỏi về thời tiết / xàm",
            "message": "Thời tiết Sài Gòn hôm nay thế nào hả em?"
        },
        {
            "name": "Kịch bản 3: Hỏi đầu tư ngoài lề (Bất động sản)",
            "message": "Anh có 2 tỷ, nên đầu tư mua đất hay mua bitcoin em nhỉ?"
        }
    ]
    
    try:
        for i, sc in enumerate(scenarios, 1):
            print(f"🔹 {sc['name']}")
            print(f"👉 Khách nhắn: \"{sc['message']}\"")
            
            result = orchestrator.process_message(f"out_of_scope_{i}", sc['message'], {}, db=db)
            
            print(f"🤖 AI trả lời:\n{result['message']}")
            print(f"📊 Nguồn xử lý: {result['source']}")
            print("-" * 40 + "\n")

        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_out_of_scope()
