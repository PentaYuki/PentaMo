import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from db.models import Conversations, ChatMessages
from backend.orchestrator_v3 import get_orchestrator
import uuid

def test_agentic_upgrades():
    db = SessionLocal()
    orchestrator = get_orchestrator()
    conv_id = f"test_{uuid.uuid4().hex[:8]}"
    
    print(f"--- Testing Conversation: {conv_id} ---")
    
    # 1. Start a conversation
    initial_state = {"mode": "consultant", "turn_count": 0}
    conv = Conversations(id=conv_id, buyer_id="test_user", state=initial_state)
    db.add(conv)
    db.commit()
    
    # 2. Test Message 1: Normal intent (Discovery)
    print("\n[Test 1] Normal Intent...")
    msg1 = "Chào em, anh muốn tìm mua xe Honda Vision tầm 30 triệu ở Hà Nội"
    resp1 = orchestrator.process_message(conv_id, msg1, initial_state, db=db)
    
    print(f"Agent: {resp1['message'][:50]}...")
    print(f"Slot Coverage: {resp1['state'].get('slot_coverage')}")
    print(f"Next Best Action: {resp1['state'].get('next_best_action')}")
    
    # 3. Test Message 2: Sub-context Risk (Suspicious Price)
    print("\n[Test 2] Risk Detection (Suspicious Price)...")
    msg2 = "Anh thấy có người đăng bán SH đời 2023 giá 5 triệu, em xem giúp anh"
    resp2 = orchestrator.process_message(conv_id, msg2, resp1['state'], db=db)
    
    print(f"Agent: {resp2['message'][:100]}...")
    print(f"Risk Level: {resp2['state'].get('risks', {}).get('risk_level')}")
    print(f"Handoff? {'Yes' if resp2.get('tool_name') == 'detect_risks' else 'No'}")

    # 4. Cleanup
    db.delete(conv)
    db.commit()
    db.close()

if __name__ == "__main__":
    test_agentic_upgrades()
