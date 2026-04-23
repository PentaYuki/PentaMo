import sys
import os
import uuid
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestrator_v3 import orchestrator
from backend.database import SessionLocal
from db.models import Conversations, SellerListings, VerificationStatus, Users

def setup_mock_data(db):
    # Ensure we have an admin user
    admin = db.query(Users).filter(Users.role == "admin").first()
    if not admin:
        admin = Users(id="admin_user_id", full_name="Admin", role="admin")
        db.add(admin)
    
    # Ensure we have a listing
    listing = db.query(SellerListings).first()
    if not listing:
        listing = SellerListings(
            id=str(uuid.uuid4()),
            brand="Honda",
            model_line="SH",
            model_year=2024,
            price=150000000,
            province="Hà Nội",
            seller_id="admin-seller-id",
            verification_status=VerificationStatus.VERIFIED
        )
        db.add(listing)
    
    # Create a conversation
    conv_id = f"test_action_{str(uuid.uuid4())[:8]}"
    conv = Conversations(
        id=conv_id,
        buyer_id="test_buyer_id",
        seller_id=None, # AI conversation
        listing_id=listing.id,
        state={}
    )
    db.add(conv)
    db.commit()
    return conv_id, listing.id

def test_trigger(description, user_message, conv_id):
    print(f"\n--- Testing Trigger: {description} ---")
    print(f"User: {user_message}")
    
    db = SessionLocal()
    try:
        # Load conversation state
        conv = db.query(Conversations).filter(Conversations.id == conv_id).first()
        state = conv.state if conv.state else {}
        
        result = orchestrator.process_message(conv_id, user_message, state, db=db)
        
        print(f"AI: {result.get('message')}")
        print(f"Tool Triggered: {result.get('tool_name')}")
        print(f"Decision Reason: {result.get('decision_reason')}")
        
        # Check if state was updated
        db.refresh(conv)
        print(f"Updated State Action: {conv.state.get('next_best_action')}")
        
    finally:
        db.close()

if __name__ == "__main__":
    db = SessionLocal()
    conv_id, listing_id = setup_mock_data(db)
    db.close()
    
    # Test 1: Purchase Trigger
    test_trigger("Purchase/Closing", "Cho anh chốt đơn con này luôn, lập hóa đơn đi em", conv_id)
    
    # Test 2: Appointment Trigger
    test_trigger("Appointment", "Mai anh qua xem con này được không?", conv_id)
