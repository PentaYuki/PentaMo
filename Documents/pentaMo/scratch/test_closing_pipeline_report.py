import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from db.models import SellerListings, Users, Conversations, Transactions
import uuid
from datetime import datetime

def test_and_report_closing():
    print("\n" + "="*60)
    print("📋 BÁO CÁO KIỂM TRA PIPELINE CHỐT ĐƠN & ADMIN")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    
    try:
        # 1. Tìm xe và khách
        listing = db.query(SellerListings).first()
        buyer = db.query(Users).filter(Users.role == "buyer").first() or db.query(Users).first()
        
        if not listing:
            print("❌ THẤT BẠI: Không có xe trong kho.")
            return

        # 2. Tạo một Conversation giả lập trong DB để có ID thật
        conv_id = str(uuid.uuid4())
        new_conv = Conversations(
            id=conv_id,
            buyer_id=buyer.id,
            seller_id=listing.seller_id,
            listing_id=listing.id,
            state={"mode": "trader", "listing_id": listing.id},
            created_at=datetime.utcnow()
        )
        db.add(new_conv)
        db.commit()
        print(f"🔹 Khởi tạo hội thoại mới: {conv_id}")
        
        # 3. Khách nhắn tin "Chốt"
        user_msg = "Xe ngon quá, chốt luôn em ơi!"
        print(f"👉 Khách nhắn: \"{user_msg}\"")
        
        # 4. AI Xử lý
        result = orchestrator.process_message(conv_id, user_msg, new_conv.state, db=db)
        print(f"🤖 AI trả lời: \"{result['message']}\"")
        
        # 5. KIỂM TRA DATABASE (Bên Admin nhận được gì?)
        print("\n🔍 ĐANG KIỂM TRA DỮ LIỆU ADMIN...")
        
        # Kiểm tra Transactions
        tx = db.query(Transactions).filter(Transactions.conversation_id == conv_id).first()
        
        # Kiểm tra trạng thái LeadStage của hội thoại
        db.refresh(new_conv)
        
        print("-" * 40)
        if tx:
            print(f"✅ PASS: Hệ thống đã tạo Transaction (ID: {tx.id})")
            print(f"✅ PASS: Số tiền ghi nhận: {tx.amount:,.0f} VNĐ")
            print(f"✅ PASS: Trạng thái: {tx.status}")
        else:
            print("❌ FAIL: Không tìm thấy Transaction trong database.")
            
        if new_conv.lead_stage == "COMPLETED":
             print(f"✅ PASS: Trạng thái Lead của hội thoại đã chuyển sang 'COMPLETED'")
        else:
             print(f"❌ FAIL: Trạng thái Lead là '{new_conv.lead_stage}', mong muốn 'COMPLETED'")
             
        print("-" * 40)
        
        if tx and new_conv.lead_stage == "COMPLETED":
            print("\n🏆 KẾT LUẬN: PIPELINE CHỐT ĐƠN HOẠT ĐỘNG HOÀN HẢO!")
        else:
            print("\n⚠️ KẾT LUẬN: PIPELINE CÓ VẤN ĐỀ, CẦN KIỂM TRA LẠI LOGIC.")

    except Exception as e:
        print(f"💥 LỖI HỆ THỐNG: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_and_report_closing()
