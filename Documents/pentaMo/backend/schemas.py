from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ConversationState(BaseModel):
    model_config = {"protected_namespaces": ()}
    participants: Dict[str, Optional[str]] = {}
    lead_stage: str = "DISCOVERY"
    mode: str = "explore"  # "explore" or "transact"
    constraints: Dict[str, Any] = {}
    listing_context: Dict[str, Any] = {}
    open_questions: List[str] = []
    risks: Dict[str, Any] = {"level": "low", "flags": []}
    next_best_action: Dict[str, Any] = {}
    tool_history: List[Dict[str, Any]] = []
    summary: Optional[str] = None
    customer_segment: Optional[str] = None
    turn_count: int = 0  # Track conversation turns for response variation

class ChatMessage(BaseModel):
    model_config = {"protected_namespaces": ()}
    conversation_id: str
    sender_type: str  # buyer, seller, agent
    sender_id: str
    text: str

class ChatMessageResponse(ChatMessage):
    model_config = {"protected_namespaces": ()}
    id: Optional[int] = None
    timestamp: datetime
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0

class UserCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    phone: Optional[str] = None
    full_name: str
    role: str = "buyer"
    location_province: Optional[str] = None

class UserResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    phone: Optional[str]
    full_name: str
    role: str
    created_at: datetime

class ConversationCreate(BaseModel):
    model_config = {"protected_namespaces": ()}
    buyer_id: str
    seller_id: Optional[str] = None
    listing_id: Optional[str] = None

class ConversationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str
    buyer_id: str
    seller_id: Optional[str]
    listing_id: Optional[str]
    lead_stage: str
    state: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class AgentResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    intent: str
    entities: Dict[str, Any]
    action: str
    message: str
    next_step: Optional[str] = None
