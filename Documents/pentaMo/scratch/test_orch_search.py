import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.orchestrator_v3 import AgentOrchestrator

def test_orchestrator_logic():
    orch = AgentOrchestrator()
    state = {"mode": "consultant", "brands": [], "budget": None}
    
    messages = [
        "anh múa xe honda bên mình có không",
        "bên shop có không xe không",
        "anh cần tìm chiếc sh"
    ]
    
    for msg in messages:
        print(f"\nUser: {msg}")
        # Test search detection
        search_msg, search_count, search_params = orch._perform_search(msg)
        print(f"Search Triggered: {'YES' if search_params else 'NO'}")
        print(f"Results Count: {search_count}")
        print(f"Search Params: {search_params}")
        
        # Test mode detection
        mode = orch._detect_mode(msg, state)
        print(f"Detected Mode: {mode}")
        
        # Test state update
        new_state = orch._update_state(msg, state)
        print(f"Updated State: {new_state}")

if __name__ == "__main__":
    test_orchestrator_logic()
