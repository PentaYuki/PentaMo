import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from db.models import Conversations, ChatMessages, Users, SellerListings, Appointments
from auth.jwt_handler import get_current_user, TokenPayload
from backend.orchestrator_v3 import orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.get("/conversations")
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lấy danh sách các cuộc hội thoại của người dùng (cả mua và bán)"""
    uid = current_user.user_id
    convs = db.query(Conversations).filter(
        (Conversations.buyer_id == uid) | (Conversations.seller_id == uid)
    ).order_by(Conversations.updated_at.desc()).all()
    
    results = []
    for c in convs:
        # Determine the "other" person
        other_id = c.seller_id if c.buyer_id == uid else c.buyer_id
        other_name = "Anonymous"
        if other_id:
            other_user = db.query(Users).filter(Users.id == other_id).first()
            other_name = other_user.full_name if other_user else "Unknown User"
        
        listing = db.query(SellerListings).filter(SellerListings.id == c.listing_id).first()
        if c.seller_id is None:
            listing_title = "🛡️ Hỗ trợ PentaMo (AI)"
            other_name = "An (AI Assistant)"
        else:
            listing_title = f"{listing.brand} {listing.model_line}" if listing else "Hỗ trợ PentaMo"
        
        # Get last message
        last_msg = db.query(ChatMessages).filter(ChatMessages.conversation_id == c.id).order_by(ChatMessages.timestamp.desc()).first()
        
        results.append({
            "id": c.id,
            "other_name": other_name,
            "listing_title": listing_title,
            "last_message": last_msg.text if last_msg else "Chưa có tin nhắn",
            "updated_at": c.updated_at.isoformat()
        })
    return {"success": True, "conversations": results}

@router.post("/send")
async def send_message(
    conversation_id: str,
    text: str,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Gửi tin nhắn trong một cuộc hội thoại"""
    conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Check if user is part of the conversation
    if current_user.user_id not in [conv.buyer_id, conv.seller_id]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    new_msg = ChatMessages(
        conversation_id=conversation_id,
        sender_id=current_user.user_id,
        sender_type="user",
        text=text
    )
    db.add(new_msg)
    conv.updated_at = datetime.utcnow()
    
    ai_response_text = None
    # IF AI CONVERSATION (seller_id is None)
    if conv.seller_id is None:
        # Generate AI Response
        state = conv.state if conv.state else {}
        result = orchestrator.process_message(conversation_id, text, state, db=db)
        ai_response_text = result.get("message")
        
        # Save AI message to DB
        ai_msg = ChatMessages(
            conversation_id=conversation_id,
            sender_id="penta_ai", # Generic AI ID
            sender_type="assistant",
            text=ai_response_text
        )
        db.add(ai_msg)
        
    db.commit()
    
    return {
        "success": True, 
        "message": "Tin nhắn đã được gửi",
        "response": ai_response_text
    }

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lấy lịch sử tin nhắn của một cuộc hội thoại"""
    conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if current_user.user_id not in [conv.buyer_id, conv.seller_id]:
        raise HTTPException(status_code=403, detail="Access denied")
        
    msgs = db.query(ChatMessages).filter(ChatMessages.conversation_id == conversation_id).order_by(ChatMessages.timestamp.asc()).all()
    
    return {
        "success": True,
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "sender_id": m.sender_id,
                "timestamp": m.timestamp.isoformat(),
                "is_mine": m.sender_id == current_user.user_id
            } for m in msgs
        ]
    }

@router.get("/appointments")
async def get_all_appointments(
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lấy tất cả lịch hẹn (cả vai trò mua và bán)"""
    uid = current_user.user_id
    
    # Buyer appointments
    buyer_apts = db.query(Appointments).filter(Appointments.buyer_id == uid).all()
    # Seller appointments
    seller_apts = db.query(Appointments).filter(Appointments.seller_id == uid).all()
    
    results = []
    
    # Format buyer appointments
    for a in buyer_apts:
        listing = db.query(SellerListings).filter(SellerListings.id == a.listing_id).first()
        results.append({
            "id": a.id,
            "role": "buyer",
            "listing_title": f"{listing.brand} {listing.model_line}" if listing else "Unknown",
            "date": a.appointment_date.isoformat(),
            "location": a.location,
            "status": a.status,
            "other_party": "Người bán"
        })
        
    # Format seller appointments
    for a in seller_apts:
        listing = db.query(SellerListings).filter(SellerListings.id == a.listing_id).first()
        buyer = db.query(Users).filter(Users.id == a.buyer_id).first()
        results.append({
            "id": a.id,
            "role": "seller",
            "listing_title": f"{listing.brand} {listing.model_line}" if listing else "Unknown",
            "date": a.appointment_date.isoformat(),
            "location": a.location,
            "status": a.status,
            "other_party": buyer.full_name if buyer else "Người mua ẩn danh"
        })
        
    # Sort by date
    results.sort(key=lambda x: x['date'], reverse=True)
    
    return {"success": True, "appointments": results}
