import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from db.models import SellerListings, Users, Conversations
import uuid

def test_order_pipeline():
    print("\n" + "="*60)
    print("🛒 TEST PIPELINE ĐẶT HÀNG TRỰC TIẾP TỪ AI CHAT")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    
    try:
        # 1. Chuẩn bị dữ liệu mẫu: Một chiếc xe và một khách hàng
        listing = db.query(SellerListings).first()
        if not listing:
            print("❌ Lỗi: Không có xe nào trong DB để test.")
            return
            
        buyer = db.query(Users).filter(Users.role == "buyer").first()
        if not buyer:
            buyer = db.query(Users).first() # Fallback

        print(f"📍 Xe đang xem: {listing.brand} {listing.model_line} - Giá: {listing.price:,.0f} VNĐ")
        print(f"📍 Khách hàng: {buyer.full_name} (ID: {buyer.id})")
        print("-" * 30)

        # 2. Thiết lập State (Ngữ cảnh) cuộc hội thoại
        # Giả lập khách đã chọn xe này rồi
        current_state = {
            "mode": "trader",
            "listing_id": listing.id,
            "listing_context": {
                "id": listing.id,
                "brand": listing.brand,
                "model_line": listing.model_line,
                "price": listing.price
            },
            "participants": {
                "buyer_id": buyer.id,
                "seller_id": listing.seller_id
            }
        }
        
        # 3. Khách nhắn tin chốt đơn
        user_message = "Anh thấy chiếc này ổn quá, chốt mua chiếc này luôn em nhé!"
        print(f"👉 Khách nhắn: \"{user_message}\"")
        print("... AI đang xử lý đơn hàng ...")
        
        # 4. Chạy qua Orchestrator
        # Chúng ta dùng một conversation_id ngẫu nhiên
        conv_id = str(uuid.uuid4())
        result = orchestrator.process_message(conv_id, user_message, current_state, db=db)
        
        # 5. Kiểm tra kết quả
        print(f"\n✅ KẾT QUẢ TỪ AI:")
        print(f"🤖 Tin nhắn AI: \"{result['message']}\"")
        print(f"🛠️  Tool đã dùng: {result.get('tool_name')}")
        print(f"📊 Nguồn xử lý: {result.get('source')}")
        
        if result.get('ui_commands'):
            print(f"🖥️  Lệnh UI: {result['ui_commands']}")

        print("\n" + "="*60)
        
    finally:
        db.close()

if __name__ == "__main__":
    test_order_pipeline()
