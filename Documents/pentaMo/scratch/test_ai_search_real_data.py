import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from db.models import SellerListings

def test_real_data_search():
    print("\n" + "="*60)
    print("🔍 TEST TÌM KIẾM DỮ LIỆU THẬT TỪ DATABASE")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    
    try:
        # Tình huống 1: Tìm xe Yamaha dưới 50 triệu
        print("🔹 Tình huống 1: Tìm xe Yamaha thực tế trong hệ thống")
        user_message_1 = "Anh muốn tìm mấy chiếc Yamaha giá dưới 50 triệu"
        print(f"👉 Khách nhắn: \"{user_message_1}\"")
        
        result_1 = orchestrator.process_message("search_test_1", user_message_1, {}, db=db)
        
        print(f"🤖 AI trả lời:\n{result_1['message']}")
        print(f"📊 Nguồn dữ liệu: {result_1.get('source')}")
        if result_1.get('ui_commands'):
            print(f"🖥️  Thông số lọc AI đã gửi: {result_1['ui_commands'][0]['params']}")
        print("-" * 40 + "\n")

        # Tình huống 2: Tìm loại xe không tồn tại (Ví dụ: Xe Ferrari giá 10 triệu)
        print("🔹 Tình huống 2: Tìm xe không có trong dữ liệu (Xe Ducati dưới 10 triệu)")
        user_message_2 = "Shop có chiếc Ducati nào giá dưới 10 triệu không?"
        print(f"👉 Khách nhắn: \"{user_message_2}\"")
        
        result_2 = orchestrator.process_message("search_test_2", user_message_2, {}, db=db)
        
        print(f"🤖 AI trả lời: \"{result_2['message']}\"")
        print(f"📊 Nguồn dữ liệu: {result_2.get('source')}")
        print("="*60 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_real_data_search()
