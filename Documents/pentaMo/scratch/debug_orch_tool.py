import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.orchestrator_v3 import AgentOrchestrator

orch = AgentOrchestrator()
state = {
    "participants": {"buyer_id": "user_1"},
    "lead_stage": "DISCOVERY",
    "listing_context": {"id": "listing_123", "seller_id": "seller_456"}
}

msg = "Ok, đặt cho mình chiều nay"
resp = orch.process_message("test_conv", msg, state)

print(f"Source: {resp.get('source')}")
print(f"Tool Name: {resp.get('tool_name')}")
print(f"Lead Stage: {resp.get('state', {}).get('lead_stage')}")
print(f"Message: {resp.get('message')}")
print(f"Decision: {resp.get('decision_reason')}")
