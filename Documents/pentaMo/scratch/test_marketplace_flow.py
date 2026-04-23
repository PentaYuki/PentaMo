import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.orchestrator_v3 import get_orchestrator
from backend.database import SessionLocal
from db.models import Conversations, Appointments, SellerListings
import uuid
import json

def run_test():
    db = SessionLocal()
    orchestrator = get_orchestrator()
    
    print("--- 🚀 STARTING MARKETPLACE TEST ---")
    
    # 1. Test Admin-owned bike (SH 150i ABS)
    print("\n[TEST 1] Admin-owned Bike (SH 150i ABS)")
    conv_id_admin = str(uuid.uuid4())
    db.add(Conversations(id=conv_id_admin, buyer_id="test-buyer-1", state={}))
    db.commit()
    
    state_admin = {}
    
    # Step 1: Search
    msg1 = "Tìm cho tôi chiếc Honda SH 150i ABS"
    print(f"User: {msg1}")
    res1 = orchestrator.process_message(conv_id_admin, msg1, state_admin, db)
    state_admin = res1["state"]
    print(f"AI: {res1['message']}")
    
    # Check if context caught the seller
    seller_id = state_admin.get("participants", {}).get("seller_id")
    listing_id = state_admin.get("listing_context", {}).get("id")
    print(f"-> State after search: Listing ID={listing_id}, Seller ID={seller_id}")
    
    # Step 2: Intent to book
    msg2 = "Tôi muốn xem xe SH này"
    print(f"User: {msg2}")
    res2 = orchestrator.process_message(conv_id_admin, msg2, state_admin, db)
    state_admin = res2["state"]
    print(f"AI: {res2['message']}")
    
    # Step 3: Book appointment
    msg3 = "Đặt lịch chiều nay nhé"
    print(f"User: {msg3}")
    res3 = orchestrator.process_message(conv_id_admin, msg3, state_admin, db)
    state_admin = res3["state"]
    print(f"AI: {res3['message']}")
    
    # Verify DB for appointment
    apt1 = db.query(Appointments).filter(Appointments.listing_id == listing_id).order_by(Appointments.created_at.desc()).first()
    if apt1:
        print(f"✅ Appointment created for Admin listing! Seller ID: {apt1.seller_id}")
    else:
        print("❌ Failed to create appointment for Admin listing.")


    # 2. Test User-owned bike (Winner X)
    print("\n[TEST 2] User-owned Bike (Winner X)")
    conv_id_user = str(uuid.uuid4())
    db.add(Conversations(id=conv_id_user, buyer_id="test-buyer-2", state={}))
    db.commit()
    
    state_user = {}
    
    # Step 1: Search
    msg4 = "Tìm chiếc Honda Winner X"
    print(f"User: {msg4}")
    res4 = orchestrator.process_message(conv_id_user, msg4, state_user, db)
    state_user = res4["state"]
    print(f"AI: {res4['message']}")
    
    listing_id_user = state_user.get("listing_context", {}).get("id")
    
    # Step 2: Intent to book
    msg5 = "Tôi chốt mua chiếc Winner này"
    print(f"User: {msg5}")
    res5 = orchestrator.process_message(conv_id_user, msg5, state_user, db)
    state_user = res5["state"]
    print(f"AI: {res5['message']}")
    
    print("\n--- 🏁 TEST COMPLETE ---")
    
if __name__ == "__main__":
    run_test()
