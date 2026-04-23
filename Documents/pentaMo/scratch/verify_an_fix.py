import sys
import os
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestrator_v3 import orchestrator
from backend.database import SessionLocal

def test_scenario(description, user_message):
    print(f"\n--- Scenario: {description} ---")
    print(f"User: {user_message}")
    
    db = SessionLocal()
    try:
        conversation_id = "test_conv_a82da"
        state = {}
        
        # We need to bypass FAISS cache for testing if possible or just use a fresh conv_id
        result = orchestrator.process_message(conversation_id, user_message, state, db=db)
        
        print(f"AI: {result.get('message')}")
        print(f"Mode: {result.get('mode')}")
        print(f"Source: {result.get('source')}")
    finally:
        db.close()

if __name__ == "__main__":
    # Test cases from user request
    test_scenario("Buying a Honda", "anh mua xe honda")
    test_scenario("15 Million Budget", "anh có 15 triệu mua xe nào")
    test_scenario("Car Inquiry (Implicit)", "có xe innova không")
    test_scenario("Motorbike Inquiry", "có xe máy không")
    test_scenario("Out of Scope", "thời tiết hôm nay thế nào")
