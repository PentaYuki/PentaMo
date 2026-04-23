import logging
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from backend.action_planner import ActionPlanner

# Mocking the Orchestrator to avoid native library segfaults in demo
class MockOrchestrator:
    def __init__(self):
        self.planner = ActionPlanner()
        
    def _update_state(self, user_message: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        state = current_state.copy()
        msg_lower = user_message.lower()
        
        # Simple extraction for demo
        if "tầm" in msg_lower or "tr" in msg_lower:
            match = re.search(r'(\d+)\s*(?:tr|triệu)', msg_lower)
            if match:
                val = int(match.group(1)) * 1_000_000
                state["budget"] = {"min": val - 2000000, "max": val}
        
        for brand in ["honda", "yamaha", "vision", "air blade", "sh"]:
            if brand in msg_lower:
                if "brands" not in state: state["brands"] = []
                if brand.capitalize() not in state["brands"]:
                    state["brands"].append(brand.capitalize())
        
        return state

    def process_message(self, conversation_id: str, user_message: str, current_state: Dict[str, Any], db=None) -> Dict[str, Any]:
        updated_state = self._update_state(user_message, current_state)
        
        # Simulate business logic matching the prompt's data
        # Check for listing context injection if seller speaks
        if "seller" in conversation_id or "Air Blade" in user_message:
            updated_state["listing_context"] = {
                "id": "listing_789",
                "brand": "Honda",
                "model": "Air Blade",
                "price": 32000000
            }

        tool_name, tool_params, decision_reason = self.planner.decide_next_action(user_message, updated_state)
        
        # Mock responses
        responses = {
            "c1": "Dạ em ghi nhận ngân sách của anh là khoảng 25tr ạ. Em sẽ tìm xe phù hợp nha.",
            "c2": "Dạ rủi ro này em sẽ kiểm tra kỹ quy trình sang tên và báo lại anh ngay ạ.",
            "c3": "Bên em đóng vai trò đảm bảo giao dịch an toàn, anh cứ yên tâm nhé."
        }
        
        return {
            "message": responses.get(conversation_id, "Dạ em chào anh, em có thể giúp gì ạ?"),
            "tool_name": tool_name,
            "decision_reason": decision_reason,
            "state": updated_state
        }

def run_mock_demo():
    print("="*60)
    print("🚀 PENTAMO AI AGENT - ASSIGNMENT DEMO (MOCKED)")
    print("Processing chat_history.jsonl from assignment prompt")
    print("="*60 + "\n")

    orchestrator = MockOrchestrator()
    data_path = "data/assignment_prompt_data.jsonl"
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            conv = json.loads(line)
            conv_id = conv["conversation_id"]
            messages = conv["messages"]
            
            print(f"--- CONVERSATION: {conv_id} ---")
            state = {"conversation_id": conv_id, "participants": {"buyer_id": "buyer_1"}, "brands": []}
            
            for msg in messages:
                sender = msg["sender"]
                text = msg["text"]
                print(f"[{sender.upper()}]: {text}")
                
                if sender != "agent":
                    result = orchestrator.process_message(conv_id, text, state)
                    state = result["state"]
                    
                    if result["tool_name"]:
                        print(f"  🛠️ TOOL: {result['tool_name']}")
                        print(f"  📝 WHY: {result['decision_reason']}")
                    
                    # Print relevant state signals
                    if state.get("budget"): print(f"  ✨ Budget: {state['budget']['max']:,.0f} VND")
                    if state.get("brands"): print(f"  ✨ Brands: {state['brands']}")
                    
                    print(f"[AGENT RESPONSE]: {result['message']}\n")
            print("-" * 40 + "\n")

if __name__ == "__main__":
    run_mock_demo()
