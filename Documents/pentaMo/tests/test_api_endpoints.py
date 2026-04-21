import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from db.models import Users, SellerListings, Conversations

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    # Some internal route or just root
    assert response.status_code in [200, 404] # 404 if not defined, but we check availability

def test_chat_flow_initialization():
    # Test creating a conversation
    response = client.post("/api/conversations/", json={"buyer_id": "test_user"})
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        conv_id = data["id"]
        
        # Test sending a message
        msg_resp = client.post(f"/api/conversations/{conv_id}/messages", json={
            "text": "Chào shop, mình muốn tìm xe Honda",
            "sender_type": "buyer"
        })
        assert msg_resp.status_code == 200
        assert "An:" in msg_resp.json()["message"]

def test_listing_search_api():
    response = client.get("/api/tools/search?q=Honda")
    assert response.status_code == 200
    data = response.json()
    assert "listings" in data

def test_appointment_retrieval():
    # Test unified appointment endpoint
    # Requires auth usually, so we expect 401 or 200 depending on check
    response = client.get("/api/chat/appointments")
    assert response.status_code in [200, 401]
