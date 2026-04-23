import os
import json
import logging
from typing import Dict, Any, List
from backend.orchestrator_v3 import AgentOrchestrator
from backend.action_planner import ActionPlanner

# Setup minimal logging to console
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("AssignmentDemo")

def run_demo():
    print("="*60)
    print("🚀 PENTAMO AI AGENT - ASSIGNMENT DEMO")
    print("Processing chat_history.jsonl from assignment prompt")
    print("="*60 + "\n")

    orchestrator = AgentOrchestrator()
    data_path = "data/assignment_prompt_data.jsonl"
    
    if not os.path.exists(data_path):
        print(f"❌ Error: Data file not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            conv = json.loads(line)
            conv_id = conv["conversation_id"]
            messages = conv["messages"]
            
            print(f"--- CONVERSATION: {conv_id} ---")
            
            # Initial state for each conversation
            state = {
                "conversation_id": conv_id,
                "participants": {"buyer_id": "buyer_1", "agent_id": "an"},
                "lead_stage": "DISCOVERY",
                "brands": [],
                "constraints": {}
            }
            
            for msg in messages:
                sender = msg["sender"]
                text = msg["text"]
                
                print(f"[{sender.upper()}]: {text}")
                
                # We only process non-agent messages to see how the agent REacts
                if sender != "agent":
                    # Step 1: Update state and detect signals
                    # In a real system, orchestrator handles this in process_message
                    # Here we simulate the pipeline to show what's happening internally
                    
                    # Call orchestrator's processing logic (simplified for demo)
                    # Note: We pass None for DB as we just want to see the logic flow
                    result = orchestrator.process_message(conv_id, text, state, db=None)
                    
                    state = result.get("state", state)
                    tool_name = result.get("tool_name")
                    decision_reason = result.get("decision_reason")
                    agent_response = result.get("message")
                    
                    # Print extracted signals (simulated from state updates)
                    if state.get("budget"):
                        print(f"  ✨ SIGNAL [Budget]: {state.get('budget')}")
                    if state.get("brands"):
                        print(f"  ✨ SIGNAL [Brands]: {state.get('brands')}")
                    if state.get("risks"):
                        print(f"  ⚠️ RISK DETECTED: {state.get('risks')}")
                    
                    if tool_name:
                        print(f"  🛠️ TOOL CALL: {tool_name}")
                        print(f"  📝 REASON: {decision_reason}")
                    
                    print(f"[AGENT RESPONSE]: {agent_response}\n")
            
            print("-" * 40 + "\n")

if __name__ == "__main__":
    run_demo()
