from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    BUYER = "USER"
    SELLER = "USER"
    ADMIN = "ADMIN"
    USER = "USER"

class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class LeadStage(str, enum.Enum):
    DISCOVERY = "DISCOVERY"
    MATCHING = "MATCHING"
    NEGOTIATION = "NEGOTIATION"
    APPOINTMENT = "APPOINTMENT"
    CLOSING = "CLOSING"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"
    CANCELLED = "CANCELLED"

class Users(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    google_id = Column(String, nullable=True, unique=True)
    phone = Column(String, nullable=True)
    full_name = Column(String)
    password_hash = Column(String, nullable=True) # Hashed password
    role = Column(String, default="user")
    location_province = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SellerListings(Base):
    __tablename__ = "seller_listings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Vehicle Info
    brand = Column(String)
    model_year = Column(Integer)
    model_line = Column(String)
    color = Column(String)
    condition = Column(String)
    
    # Location
    address_detail = Column(String, nullable=True)
    province = Column(String)
    
    # Price
    price = Column(Float)
    
    # Paperwork
    reg_cert_front = Column(String, nullable=True)
    reg_cert_back = Column(String, nullable=True)
    insurance_front = Column(String, nullable=True)
    id_card_front = Column(String, nullable=True)
    id_card_back = Column(String, nullable=True)
    ocr_data = Column(JSON, nullable=True)
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.PENDING)
    
    # Sales Info
    sale_method = Column(String, default="NORMAL") # "NORMAL" or "AUCTION"
    
    # Images
    image_front = Column(String, nullable=True)
    image_back = Column(String, nullable=True)
    image_left = Column(String, nullable=True)
    image_right = Column(String, nullable=True)
    image_fake_score = Column(Float, default=0.0)
    
    # Seller Description & Notes
    description = Column(String, nullable=True)  # Mô tả chi tiết từ người bán
    seller_notes = Column(String, nullable=True)  # Ghi chú thêm (tình trạng, lý do bán...)

class FAISSPendingReview(Base):
    """Queue for FAISS entries pending admin review (when Gemini gate is unavailable)"""
    __tablename__ = "faiss_pending_reviews"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question = Column(String, nullable=False)
    answer_original = Column(String, nullable=False)  # Original LLM answer
    answer_refined = Column(String, nullable=True)    # Gemini-refined answer (if available)
    mode = Column(String, default="consultant")
    status = Column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    reason = Column(String, nullable=True)      # Why it's pending (e.g., "gemini_unavailable")
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class BuyerRequests(Base):
    __tablename__ = "buyer_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    desired_price_min = Column(Float, nullable=True)
    desired_price_max = Column(Float, nullable=True)
    preferred_brands = Column(JSON, default=[])
    preferred_province = Column(String, nullable=True)
    preferred_years = Column(JSON, default=[])

class Conversations(Base):
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String(36))
    seller_id = Column(String(36), nullable=True)
    listing_id = Column(String(36), nullable=True)
    channel_id = Column(String, nullable=True)
    
    # State as JSONB
    state = Column(JSON, default={})
    memory_summary = Column(String, nullable=True)
    lead_stage = Column(SQLEnum(LeadStage), default=LeadStage.DISCOVERY)
    outcome = Column(String, nullable=True) # "CLOSED_WON", "CLOSED_LOST", "DROPPED", "PENDING"
    closed_at = Column(DateTime, nullable=True)
    feedback_score = Column(Integer, nullable=True)
    
    # Evaluation Metrics
    slot_coverage = Column(JSON, default={}) # e.g. {"brand": true, "budget": true}
    hallucination_rate = Column(Float, default=0.0) 
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatMessages(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36))
    sender_type = Column(String)  # buyer, seller, agent
    sender_id = Column(String(36))
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    positive_feedback_count = Column(Integer, default=0)
    negative_feedback_count = Column(Integer, default=0)

class ToolLogs(Base):
    __tablename__ = "tool_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36))
    tool_name = Column(String)
    input_params = Column(JSON)
    output = Column(JSON)
    executed_at = Column(DateTime, default=datetime.utcnow)

class SavedListings(Base):
    __tablename__ = "saved_listings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36))
    listing_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.utcnow)

class Appointments(Base):
    __tablename__ = "appointments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String(36))
    buyer_id = Column(String(36))
    seller_id = Column(String(36))
    
    appointment_date = Column(DateTime)
    location = Column(String)
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, REJECTED, COMPLETED
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transactions(Base):
    __tablename__ = "transactions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String(36))
    buyer_id = Column(String(36))
    seller_id = Column(String(36))
    amount = Column(Float)
    currency = Column(String, default="VND")
    status = Column(String, default="COMPLETED") # PENDING, COMPLETED, CANCELLED
    
    conversation_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
