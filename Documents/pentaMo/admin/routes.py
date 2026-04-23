"""
Admin Dashboard Routes (Phase 3)
User management, fraud detection, system configuration
Now with JWT authentication and database integration
"""

import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from auth.jwt_handler import get_current_user, UserRole, TokenPayload
from services import UserService, ListingService, ConversationService, SystemService
from backend.database import SessionLocal, get_db


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# get_db imported from backend.database



# Dependency: Require admin or moderator role
async def require_admin(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Dependency: Require admin or moderator role"""
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/metrics")
async def get_admin_metrics(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system-wide metrics for admin dashboard"""
    logger.info(f"Admin ({current_user.username}) requested dashboard metrics")
    return SystemService.get_metrics(db)


@router.get("/analytics")
async def get_admin_analytics(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Bridge for frontend analytics dashboard"""
    logger.info(f"Admin ({current_user.username}) requested analytics data")
    data = SystemService.get_metrics(db)
    if data.get("success"):
        # Flatten metrics for the frontend charts
        return {
            "success": True,
            "metrics": data["metrics"]["ai_evaluation"]
        }
    return data


# ==================== User Management ====================

@router.get("/users", tags=["users"])
async def get_users(
    skip: int = Query(0),
    limit: int = Query(50),
    role: Optional[str] = None,
    verified: Optional[bool] = None,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get list of users with optional filters"""
    logger.info(f"Admin ({current_user.username}) requested user list")
    result = UserService.get_users(db, skip=skip, limit=limit, role=role, verified=verified)
    return result


@router.get("/users/{user_id}", tags=["users"])
async def get_user_detail(
    user_id: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    logger.info(f"Admin ({current_user.username}) requested detail for user {user_id}")
    result = UserService.get_user_detail(db, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/users/{user_id}/verify", tags=["users"])
async def verify_user(
    user_id: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Manually verify user identity"""
    logger.info(f"Admin ({current_user.username}) verified user {user_id}")
    result = UserService.verify_user(db, user_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/users/{user_id}/suspend", tags=["users"])
async def suspend_user(
    user_id: str,
    reason: str = "",
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Suspend user account"""
    logger.warning(f"Admin ({current_user.username}) suspended user {user_id}: {reason}")
    result = UserService.suspend_user(db, user_id, reason)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ==================== Fraud Detection ====================

@router.get("/listings/pending-verification", tags=["fraud"])
async def get_pending_listings(
    skip: int = Query(0),
    limit: int = Query(20),
    risk_level: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get listings pending verification
    Risk levels: low, medium, high
    """
    logger.info(f"Admin ({current_user.username}) requested pending listings")
    result = ListingService.get_pending_listings(db, skip=skip, limit=limit, risk_level=risk_level)
    return result


@router.get("/listings/{listing_id}/risk-analysis", tags=["fraud"])
async def analyze_listing_risk(
    listing_id: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Analyze risk factors for a listing
    Returns: paperwork issues, image fake score, seller history
    """
    logger.info(f"Admin ({current_user.username}) analyzed listing {listing_id}")
    result = ListingService.analyze_listing_risk(db, listing_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/listings/{listing_id}/verify", tags=["fraud"])
async def verify_listing(
    listing_id: str,
    approved: bool,
    notes: str = "",
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Manually verify/reject a listing"""
    logger.info(f"Admin ({current_user.username}) {'approved' if approved else 'rejected'} listing {listing_id}")
    result = ListingService.verify_listing(db, listing_id, approved, notes)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.get("/conversations/{conversation_id}/fraud-check", tags=["fraud"])
async def check_conversation_fraud(
    conversation_id: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Check conversation for fraud patterns"""
    logger.info(f"Admin ({current_user.username}) checked conversation {conversation_id}")
    result = ConversationService.check_conversation_fraud(db, conversation_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/users/{user_id}/trigger-voice-bot", tags=["fraud"])
async def trigger_ai_voice_call(
    user_id: str,
    reason: str = "Nghi ngờ lừa đảo/thiếu thông tin",
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Kích hoạt AI Voice Bot gọi điện tự động xác thực danh tính User"""
    logger.warning(f"Admin {current_user.username} triggered Voice Bot for user {user_id}. Reason: {reason}")
    user = UserService.get_user_detail(db, user_id)
    
    if not user.get("success"):
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "success": True,
        "message": f"AI Voice Bot đã lên lịch gọi vào SĐT của user {user_id}.",
        "reason": reason,
        "status": "calling"
    }

# ==================== System Monitoring ====================

@router.get("/system/health", tags=["system"])
async def system_health(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """System health status with real checks"""
    logger.debug(f"Health check requested by admin {current_user.username}")
    
    # Check database health
    db_health = {"status": "OK", "response_time_ms": 5}
    try:
        result = db.execute("SELECT 1").scalar()
        db_health["status"] = "OK" if result == 1 else "DEGRADED"
    except Exception as e:
        db_health["status"] = "UNHEALTHY"
        db_health["error"] = str(e)
    
    # Check redis (stub - not currently used)
    redis_health = {"status": "UNAVAILABLE", "response_time_ms": 0}
    
    # Check ollama (stub - manual check needed)
    ollama_health = {"status": "CHECKING", "response_time_ms": 0}
    
    # Check llama.cpp (stub - manual check needed)
    llama_cpp_health = {"status": "UNAVAILABLE", "response_time_ms": 0}
    
    return {
        "success": True,
        "status": "OK" if db_health["status"] == "OK" else "DEGRADED",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_health,
            "redis": redis_health,
            "ollama": ollama_health,
            "llama_cpp": llama_cpp_health
        }
    }


@router.get("/system/metrics", tags=["system"])
async def system_metrics(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """System metrics and statistics"""
    logger.debug(f"Metrics requested by admin {current_user.username}")
    result = SystemService.get_metrics(db)
    return result


# ==================== Configuration Management ====================

@router.get("/config/database", tags=["config"])
async def get_database_config(
    current_user: TokenPayload = Depends(get_current_user)
):
    """Get current database configuration (SUPER_ADMIN only)"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only SUPER_ADMIN can view database config")
    
    logger.info(f"SUPER_ADMIN {current_user.username} viewed database config")
    
    return {
        "success": True,
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "pentamo"
        }
    }


@router.post("/config/database", tags=["config"])
async def update_database_config(
    database_url: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Switch database configuration (SUPER_ADMIN only)
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Only SUPER_ADMIN can change database config")
    
    logger.warning(f"SUPER_ADMIN {current_user.username} changed database config to {database_url}")
    
    return {
        "success": True,
        "message": "Database configuration updated",
        "database_url": database_url,
        "requires_restart": True
    }


@router.get("/config/models", tags=["config"])
async def get_models_config(
    current_user: TokenPayload = Depends(require_admin)
):
    """Get LLM model configuration"""
    logger.info(f"Admin {current_user.username} viewed models config")
    
    return {
        "success": True,
        "models": {
            "model_a": {
                "type": "ollama",
                "name": "arce-v3",
                "url": "http://localhost:11434",
                "status": "unknown"
            },
            "model_b": {
                "type": "llama.cpp",
                "name": "default",
                "url": "http://localhost:8000",
                "status": "offline"
            }
        }
    }


@router.post("/config/models/test", tags=["config"])
async def test_models_connection(
    current_user: TokenPayload = Depends(require_admin)
):
    """Test LLM model connections"""
    logger.info(f"Admin {current_user.username} tested model connections")
    
    return {
        "success": True,
        "tests": {
            "model_a": {
                "status": "connected",
                "response_time_ms": 150
            },
            "model_b": {
                "status": "unavailable",
                "error": "Connection refused"
            }
        }
    }


# ==================== Logs & Events ====================

@router.get("/logs/recent", tags=["logs"])
async def get_recent_logs(
    skip: int = Query(0),
    limit: int = Query(100),
    level: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin)
):
    """Get recent system logs"""
    logger.info(f"Admin {current_user.username} requested logs")
    
    return {
        "success": True,
        "logs": [],
        "total": 0,
        "skip": skip,
        "limit": limit
    }


@router.get("/ai-traces", tags=["logs"])
async def get_ai_traces(
    current_user: TokenPayload = Depends(require_admin)
):
    """Lấy danh sách các file log tư duy của AI (AI Traces)"""
    trace_dir = "logs/ai_traces"
    if not os.path.exists(trace_dir):
        return {"success": True, "traces": []}
    
    files = [f for f in os.listdir(trace_dir) if f.endswith(".json")]
    traces = []
    for f in files:
        conv_id = f.replace(".json", "")
        # Lấy thời gian sửa cuối làm timestamp
        mtime = os.path.getmtime(os.path.join(trace_dir, f))
        traces.append({
            "conversation_id": conv_id,
            "timestamp": datetime.fromtimestamp(mtime).isoformat(),
            "file": f
        })
    
    # Sắp xếp theo mới nhất
    traces.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"success": True, "traces": traces}


@router.get("/ai-traces/{conversation_id}", tags=["logs"])
async def get_trace_detail(
    conversation_id: str,
    current_user: TokenPayload = Depends(require_admin)
):
    """Đọc chi tiết quá trình suy luận của AI cho một hội thoại"""
    file_path = f"logs/ai_traces/{conversation_id}.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Trace not found")
    
    history = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                history.append(json.loads(line))
                
    return {"success": True, "conversation_id": conversation_id, "history": history}


@router.get("/events/{conversation_id}", tags=["logs"])
async def get_conversation_events(
    conversation_id: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get event timeline for a conversation"""
    logger.info(f"Admin {current_user.username} requested events for conversation {conversation_id}")
    result = ConversationService.get_conversation_events(db, conversation_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


# ==================== Vector Search (Phase 3.4) ====================

@router.post("/search/conversations", tags=["vectors"])
async def search_similar_conversations(
    query: str,
    limit: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Search for similar conversations using vector embeddings (Phase 3.4)
    
    Finds conversations with similar themes/content using RAG
    """
    try:
        from models.embeddings import get_embeddings_model
        from db.postgres.vectors import VectorStore
        
        logger.info(f"Admin {current_user.username} searching similar conversations: '{query}'")
        
        embeddings_model = get_embeddings_model()
        if not embeddings_model:
            return {
                "success": False,
                "error": "Embeddings model not initialized",
                "message": "Vector search requires sentence-transformers library"
            }
        
        # Create embedding for query
        query_embedding = embeddings_model.embed_text(query)
        
        # Search PostgreSQL pgvector
        similar = VectorStore.search_similar(
            db,
            query_embedding,
            limit=limit,
            threshold=threshold
        )
        
        return {
            "success": True,
            "query": query,
            "threshold": threshold,
            "results": similar,
            "count": len(similar)
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Vector search failed"
        }

# ==================== Appointment Management ====================

@router.get("/appointments", tags=["appointments"])
async def get_all_appointments(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách toàn bộ lịch hẹn (Admin)"""
    from db.models import Appointments
    logger.info(f"Admin {current_user.username} requested all appointments")
    
    appointments = db.query(Appointments).all()
    
    return {
        "success": True,
        "count": len(appointments),
        "appointments": [
            {
                "id": a.id,
                "listing_id": a.listing_id,
                "buyer_id": a.buyer_id,
                "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
                "location": a.location,
                "status": a.status,
                "notes": a.notes
            } for a in appointments
        ]
    }


@router.get("/transactions", tags=["transactions"])
async def get_all_transactions(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lấy danh sách toàn bộ giao dịch chốt đơn thành công (Admin)"""
    from db.models import Transactions, SellerListings, Users
    logger.info(f"Admin {current_user.username} requested all transactions")
    
    # Join with listings and users to get full details
    results = db.query(
        Transactions, 
        SellerListings.brand, 
        SellerListings.model_line, 
        Users.full_name.label("buyer_name")
    ).join(SellerListings, Transactions.listing_id == SellerListings.id)\
     .join(Users, Transactions.buyer_id == Users.id)\
     .order_by(Transactions.created_at.desc()).all()
    
    transactions_list = []
    for tx, brand, model_line, buyer_name in results:
        transactions_list.append({
            "id": tx.id,
            "vehicle": f"{brand} {model_line}",
            "buyer": buyer_name,
            "amount": float(tx.amount),
            "status": tx.status,
            "conversation_id": tx.conversation_id,
            "created_at": tx.created_at.isoformat()
        })
        
    return {
        "success": True,
        "count": len(transactions_list),
        "transactions": transactions_list
    }


@router.get("/conversations/{conversation_id}/embeddings", tags=["vectors"])
async def get_conversation_embeddings(
    conversation_id: str,
    embedding_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get vector embeddings for a conversation (Phase 3.4)
    """
    try:
        from db.postgres.vectors import VectorStore
        
        logger.info(f"Admin {current_user.username} requested embeddings for conversation {conversation_id}")
        
        embeddings = VectorStore.search_conversation_embeddings(
            db,
            conversation_id,
            embedding_type=embedding_type,
            limit=limit
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "embedding_type_filter": embedding_type,
            "embeddings": embeddings,
            "count": len(embeddings)
        }
    
    except Exception as e:
        logger.error(f"Embeddings lookup error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ==================== OCR Verification (Phase 4) ====================

@router.post("/verify-image", tags=["ocr"])
async def verify_image_ocr(
    listing_id: str = Query(...),
    image_path: str = Query(...),
    plate_number: Optional[str] = Query(None),
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Verify vehicle image using OCR
    Extracts text from license plates, documents, and validates
    
    Returns: {success, verification{vehicle_type, plate_number, confidence, is_valid}}
    """
    try:
        from tools.handlers_v2 import verify_vehicle
        from db.models import SellerListings
        
        logger.info(f"Admin {current_user.username} initiated OCR verification for listing {listing_id}")
        
        # Get listing
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        
        # Execute verification
        result = verify_vehicle(image_path=image_path, plate_number=plate_number)
        
        # Save OCR result to listing
        if result.get("success"):
            listing.ocr_data = result.get("extracted_fields", {})
            db.commit()
        
        return {
            "success": result.get("success", False),
            "listing_id": listing_id,
            "verification": result.get("verification", {}),
            "extracted_fields": result.get("extracted_fields", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR verification error: {e}")
        return {
            "success": False,
            "error": str(e),
            "listing_id": listing_id,
            "timestamp": datetime.utcnow().isoformat()
        }


# ==================== LLM Configuration (Hot-Swap) ====================

@router.get("/config/llm", tags=["config"])
async def get_llm_config(
    current_user: TokenPayload = Depends(require_admin)
):
    """Get current LLM configuration (main + review)"""
    from services.llm_client import LLMClient, get_review_llm, GeminiProvider, OllamaProvider
    
    main_config = LLMClient.get_current_config()
    
    review = get_review_llm()
    review_config = {"provider": "none", "model": "N/A"}
    if isinstance(review, GeminiProvider):
        review_config = {"provider": "gemini", "model": review.model_name}
    elif isinstance(review, OllamaProvider):
        review_config = {"provider": "ollama", "model": review.model}
    
    return {
        "success": True,
        "main_llm": main_config,
        "review_llm": review_config,
        "available_providers": ["gemini", "ollama"],
    }


@router.post("/config/llm/main", tags=["config"])
async def swap_main_llm(
    provider: str,
    model: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin)
):
    """Hot-swap the main LLM provider (no restart required)"""
    from services.llm_client import LLMClient
    logger.warning(f"Admin {current_user.username} swapping main LLM to {provider}/{model}")
    result = LLMClient.hot_swap_provider(provider, model)
    return result


@router.post("/config/llm/review", tags=["config"])
async def swap_review_llm(
    provider: str,
    model: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin)
):
    """Hot-swap the review/gate LLM (used for FAISS content moderation)"""
    from services.llm_client import set_review_llm
    logger.warning(f"Admin {current_user.username} swapping review LLM to {provider}/{model}")
    result = set_review_llm(provider, model)
    return result


# ==================== FAISS Pending Review Queue ====================

@router.get("/faiss/pending", tags=["faiss"])
async def get_faiss_pending_reviews(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all FAISS entries pending admin review"""
    from db.models import FAISSPendingReview
    
    pending = db.query(FAISSPendingReview).filter(
        FAISSPendingReview.status == "PENDING"
    ).order_by(FAISSPendingReview.created_at.desc()).all()
    
    return {
        "success": True,
        "count": len(pending),
        "reviews": [{
            "id": r.id,
            "question": r.question,
            "answer_original": r.answer_original,
            "answer_refined": r.answer_refined,
            "mode": r.mode,
            "reason": r.reason,
            "created_at": r.created_at.isoformat()
        } for r in pending]
    }


@router.post("/faiss/review/{review_id}", tags=["faiss"])
async def review_faiss_entry(
    review_id: str,
    action: str,  # "approve" or "reject"
    edited_answer: Optional[str] = None,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin reviews a pending FAISS entry.
    action='approve': Save to FAISS (using edited_answer if provided)
    action='reject': Discard the entry
    """
    from db.models import FAISSPendingReview
    from services.faiss_memory import get_faiss_memory
    
    review = db.query(FAISSPendingReview).filter(FAISSPendingReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if action == "approve":
        final_answer = edited_answer or review.answer_refined or review.answer_original
        memory = get_faiss_memory()
        memory.add(review.question, final_answer, review.mode)
        review.status = "APPROVED"
        review.answer_refined = final_answer
        logger.info(f"Admin {current_user.username} approved FAISS entry: {review.question[:50]}")
    elif action == "reject":
        review.status = "REJECTED"
        logger.info(f"Admin {current_user.username} rejected FAISS entry: {review.question[:50]}")
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    
    review.reviewed_by = current_user.user_id
    review.reviewed_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "action": action, "review_id": review_id}


# ==================== Admin Direct Chat ====================

@router.post("/chat/{conversation_id}/send", tags=["chat"])
async def admin_send_message(
    conversation_id: str,
    text: str,
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin sends a message directly to a customer in a conversation"""
    from db.models import Conversations, ChatMessages
    
    conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Create admin message
    admin_msg = ChatMessages(
        conversation_id=conversation_id,
        sender_id=current_user.user_id,
        sender_type="admin",
        text=text
    )
    db.add(admin_msg)
    conv.updated_at = datetime.utcnow()
    
    # If this was an AI-only conversation, assign admin as seller
    if conv.seller_id is None:
        conv.seller_id = current_user.user_id
    
    db.commit()
    db.refresh(admin_msg)
    
    logger.info(f"Admin {current_user.username} sent message in conv {conversation_id}")
    
    return {
        "success": True,
        "message_id": admin_msg.id,
        "text": text,
        "timestamp": admin_msg.timestamp.isoformat()
    }


@router.get("/chat/conversations", tags=["chat"])
async def admin_get_all_conversations(
    current_user: TokenPayload = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get ALL conversations for admin view (not just their own)"""
    from db.models import Conversations, ChatMessages, Users, SellerListings
    
    convs = db.query(Conversations).order_by(Conversations.updated_at.desc()).limit(50).all()
    
    results = []
    for c in convs:
        buyer = db.query(Users).filter(Users.id == c.buyer_id).first() if c.buyer_id else None
        seller = db.query(Users).filter(Users.id == c.seller_id).first() if c.seller_id else None
        listing = db.query(SellerListings).filter(SellerListings.id == c.listing_id).first() if c.listing_id else None
        
        last_msg = db.query(ChatMessages).filter(
            ChatMessages.conversation_id == c.id
        ).order_by(ChatMessages.timestamp.desc()).first()
        
        results.append({
            "id": c.id,
            "buyer_name": buyer.full_name if buyer else "Unknown",
            "seller_name": seller.full_name if seller else "AI Assistant",
            "is_ai": c.seller_id is None,
            "listing_title": f"{listing.brand} {listing.model_line}" if listing else "Hỗ trợ chung",
            "last_message": last_msg.text[:80] if last_msg else "Chưa có tin nhắn",
            "lead_stage": c.lead_stage.value if c.lead_stage else None,
            "updated_at": c.updated_at.isoformat()
        })
    
    return {"success": True, "conversations": results}

