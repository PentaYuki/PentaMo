import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator_v3 import AgentOrchestrator
from backend.database import SessionLocal
from db.models import SellerListings, Users, Conversations, Appointments
import uuid
from datetime import datetime

def test_and_report_booking():
    print("\n" + "="*60)
    print("📋 BÁO CÁO KIỂM TRA PIPELINE ĐẶT LỊCH HẸN & ADMIN")
    print("="*60 + "\n")
    
    db = SessionLocal()
    orchestrator = AgentOrchestrator()
    
    try:
        # 1. Tìm xe và khách
        listing = db.query(SellerListings).first()
        buyer = db.query(Users).filter(Users.role == "buyer").first() or db.query(Users).first()
        
        # 2. Tạo một Conversation giả lập
        conv_id = str(uuid.uuid4())
        new_conv = Conversations(
            id=conv_id,
            buyer_id=buyer.id,
            seller_id=listing.seller_id,
            listing_id=listing.id,
            state={"mode": "consultant", "listing_id": listing.id},
            created_at=datetime.utcnow()
        )
        db.add(new_conv)
        db.commit()
        print(f"🔹 Khởi tạo hội thoại mới: {conv_id}")
        
        # 3. Khách nhắn tin "Đặt lịch"
        user_msg = "Mai mình rảnh, cho mình đặt lịch xem xe lúc 9h sáng nhé"
        print(f"👉 Khách nhắn: \"{user_msg}\"")
        
        # 4. AI Xử lý
        result = orchestrator.process_message(conv_id, user_msg, new_conv.state, db=db)
        print(f"🤖 AI trả lời: \"{result['message']}\"")
        
        # 5. KIỂM TRA DATABASE
        print("\n🔍 ĐANG KIỂM TRA DỮ LIỆU LỊCH HẸN...")
        
        # Tìm Appointment mới nhất của buyer cho listing này
        apt = db.query(Appointments).filter(
            Appointments.buyer_id == buyer.id,
            Appointments.listing_id == listing.id
        ).order_by(Appointments.created_at.desc()).first()
        
        print("-" * 40)
        if apt:
            print(f"✅ PASS: Hệ thống đã tạo Lịch hẹn (ID: {apt.id})")
            print(f"✅ PASS: Thời gian: {apt.appointment_date}")
            print(f"✅ PASS: Trạng thái: {apt.status}")
        else:
            print("❌ FAIL: Không tìm thấy Lịch hẹn trong database.")
            
        print("-" * 40)
        
        if apt:
            print("\n🏆 KẾT LUẬN: PIPELINE ĐẶT LỊCH HOẠT ĐỘNG HOÀN HẢO!")
        else:
            print("\n⚠️ KẾT LUẬN: PIPELINE CÓ VẤN ĐỀ.")

    except Exception as e:
        print(f"💥 LỖI HỆ THỐNG: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_and_report_booking()
