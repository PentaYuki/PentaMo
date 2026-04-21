import pytest
from backend.action_planner import ActionPlanner
from backend.orchestrator_v3 import AgentOrchestrator

def test_action_planner_price_risk():
    planner = ActionPlanner()
    # Case C1: High price gap
    state = {
        "budget": 25000000,
        "listing_context": {"price": 32000000, "id": "bike_123"}
    }
    msg = "Giá 32tr cao quá, mình chỉ mua tối đa 25tr thôi"
    tool, params, reason = planner.decide_next_action(msg, state)
    
    assert tool == "detect_risks"
    assert params["type"] == "PRICE_MISMATCH"
    assert "21.9%" in reason

def test_action_planner_doc_risk():
    planner = ActionPlanner()
    # Case C2: Paperwork risk
    state = {"listing_context": {"id": "bike_123"}}
    msg = "Xe chưa sang tên được ngay, đang chờ rút hồ sơ"
    tool, params, reason = planner.decide_next_action(msg, state)
    
    assert tool == "detect_risks"
    assert params["type"] == "DOCUMENT_RISK"

def test_action_planner_intermediary_resistance():
    planner = ActionPlanner()
    # Case C3: Seller resistance
    state = {"listing_context": {"id": "bike_123", "seller_id": "s1"}}
    msg = "Mình không muốn qua trung gian, chỉ bán trực tiếp thôi"
    tool, params, reason = planner.decide_next_action(msg, state)
    
    assert tool == "handoff_to_human"
    assert params["reason"] == "SELLER_RESISTANCE"

def test_orchestrator_entity_extraction():
    orch = AgentOrchestrator()
    state = {}
    msg = "Mình tìm Vision tầm 25 triệu ở HCM, odo dưới 10k k nhé"
    updated = orch._update_state(msg, state)
    
    assert "Vision" in updated["brands"]
    assert updated["budget"]["max"] == 25000000
    assert updated["location"] == "TP Hồ Chí Minh"
    assert updated["odo_max"] == 10000
