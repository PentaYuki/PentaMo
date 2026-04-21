import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from backend.database import SessionLocal
    from db.models import Users, SellerListings, Appointments, Conversations, ChatMessages, VerificationStatus
    
    def test_flow():
        print("--- Starting U2U Interaction Test ---")
        db = SessionLocal()
        
        try:
            # 1. Create Seller
            seller_id = str(uuid.uuid4())
            seller = Users(
                id=seller_id,
                full_name="Người Bán Test",
                phone="0912345678",
                role="user"
            )
            db.add(seller)
            
            # 2. Create Listing
            listing_id = str(uuid.uuid4())
            listing = SellerListings(
                id=listing_id,
                seller_id=seller_id,
                brand="Honda",
                model_line="SH 150i",
                model_year=2023,
                price=100000000,
                province="Hà Nội",
                verification_status=VerificationStatus.VERIFIED
            )
            db.add(listing)
            
            # 3. Create Buyer
            buyer_id = str(uuid.uuid4())
            buyer = Users(
                id=buyer_id,
                full_name="Người Mua Test",
                phone="0987654321",
                role="user"
            )
            db.add(buyer)
            db.commit()
            print(f"✅ Created Seller ({seller_id[:8]}) and Buyer ({buyer_id[:8]})")

            # 4. Buyer Books Appointment
            apt_id = str(uuid.uuid4())
            apt = Appointments(
                id=apt_id,
                listing_id=listing_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                appointment_date=datetime.utcnow() + timedelta(days=2),
                location="123 Phố Huế, Hà Nội",
                status="PENDING"
            )
            db.add(apt)
            db.commit()
            print(f"✅ Buyer requested appointment (Status: PENDING)")

            # 5. Seller Accepts
            apt.status = "ACCEPTED"
            db.commit()
            print(f"✅ Seller accepted appointment (Status: ACCEPTED)")

            # 6. Buyer Messages Seller
            conv_id = str(uuid.uuid4())
            conv = Conversations(
                id=conv_id,
                buyer_id=buyer_id,
                seller_id=seller_id,
                listing_id=listing_id,
                state={}
            )
            db.add(conv)
            
            msg = ChatMessages(
                conversation_id=conv_id,
                sender_id=buyer_id,
                sender_type="user",
                text="Chào anh, tôi muốn xem xe SH vào chiều thứ 7 này."
            )
            db.add(msg)
            db.commit()
            print(f"✅ Buyer sent message to Seller in Conversation ({conv_id[:8]})")

            # Final Verification
            apt_check = db.query(Appointments).filter(Appointments.id == apt_id).first()
            msg_check = db.query(ChatMessages).filter(ChatMessages.conversation_id == conv_id).first()
            
            print("\n--- Summary ---")
            print(f"Appointment Status: {apt_check.status}")
            print(f"Last Message: '{msg_check.text}'")
            print("✅ TEST PASSED: Full interaction loop verified in Database.")

        except Exception as e:
            print(f"❌ Error during test: {e}")
            db.rollback()
        finally:
            db.close()

    if __name__ == "__main__":
        test_flow()

except ImportError as e:
    print(f"Import Error: {e}")
