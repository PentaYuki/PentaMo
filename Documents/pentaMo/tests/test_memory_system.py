import pytest
from unittest.mock import MagicMock
from services.memory_service import MemoryService
from db.models import Conversations, ChatMessages

@pytest.fixture
def mock_db():
    return MagicMock()

def test_memory_tier_1_retrieval(mock_db):
    service = MemoryService(mock_db)
    conv_id = "c1"
    
    # Mock Conversation
    mock_conv = Conversations(id=conv_id, state={"budget": 20000000}, memory_summary="Tóm tắt cũ.")
    mock_db.query().filter().first.return_value = mock_conv
    
    # Mock Messages
    mock_msg = ChatMessages(sender_type="buyer", text="Chào shop", timestamp=MagicMock())
    mock_db.query().filter().order_by().limit().all.return_value = [mock_msg]
    
    context = service.get_full_context(conv_id)
    
    assert context["state"]["budget"] == 20000000
    assert "buyer" in context["history"][0]["sender"]

def test_memory_tier_2_update(mock_db):
    service = MemoryService(mock_db)
    conv_id = "c1"
    
    mock_conv = Conversations(id=conv_id, state={})
    mock_db.query().filter().first.return_value = mock_conv
    
    new_data = {"location": "HCM", "lead_stage": "MATCHING"}
    service.update_structured_state(conv_id, new_data)
    
    assert mock_conv.state["location"] == "HCM"
    assert mock_conv.lead_stage == "MATCHING"
    mock_db.commit.assert_called()

def test_rolling_summary_retrieval(mock_db):
    service = MemoryService(mock_db)
    conv_id = "c1"
    
    mock_conv = Conversations(id=conv_id, memory_summary="Bản tóm tắt bí mật.")
    mock_db.query().filter().first.return_value = mock_conv
    
    summary = service.get_rolling_summary(conv_id)
    assert summary == "Bản tóm tắt bí mật."
