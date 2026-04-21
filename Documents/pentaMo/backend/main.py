import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Thêm thư mục gốc vào sys.path để nhận diện các module 'config', 'db', 'auth'...
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
import os
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import json
from typing import Dict, Optional

from config.settings import settings
from db.models import Base, ChatMessages, Conversations, Users, LeadStage
from backend.schemas import ChatMessage, ChatMessageResponse, AgentResponse, ConversationResponse, ConversationCreate
from backend.orchestrator_v3 import orchestrator
from backend.websocket_manager import get_manager
from auth.routes import router as auth_router
from admin.routes import router as admin_router
from backend.routes.seller import router as seller_router
from backend.routes.buyer import router as buyer_router
from backend.routes.chat import router as chat_router
from auth.jwt_handler import get_current_user, TokenPayload

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

from backend.database import engine, SessionLocal, get_db, create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 PentaMo Agent starting...")
    create_tables()
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"Ollama: {settings.ollama_base_url}")
    
    # Check upload directory permissions
    upload_dir = Path("data/uploads/listings")
    upload_dir.mkdir(parents=True, exist_ok=True)
    test_file = upload_dir / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
        logger.info(f"✓ Upload directory writable: {upload_dir}")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Cannot write to upload directory: {upload_dir} - {e}")
        
    yield
    logger.info("🛑 PentaMo Agent shutting down...")

app = FastAPI(
    title="pentaMO Agent",
    description="Sàn giao dịch xe máy thông minh - Powered by AI Agents",
    version="3.0.0",
    lifespan=lifespan
)

# ==================== Middleware ====================

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication middleware for protected pages
class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Check authentication for protected pages"""
    
    async def dispatch(self, request: Request, call_next):
        # List of protected paths
        protected_paths = ['/pages/admin', '/pages/seller', '/pages/buyer']
        
        # List of public paths (exempt from auth check)
        public_paths = ['/login.html', '/auth/', '/health', '/api/auth/']
        
        # Check if path is public (allow without auth)
        is_public = any(request.url.path.startswith(path) for path in public_paths)
        
        # Check if path is protected
        is_protected = any(request.url.path.startswith(path) for path in protected_paths)
        
        if is_protected and not is_public:
            # Get token from cookie or Authorization header
            token = request.cookies.get('pentamo_token')
            if not token and request.headers.get('Authorization'):
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
            
            # If no token, redirect to home page (which now handles login)
            if not token:
                return RedirectResponse(url="/")
        
        response = await call_next(request)
        return response


app.add_middleware(AuthenticationMiddleware)

# Serve static files
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.exists("pages"):
    app.mount("/pages", StaticFiles(directory="pages", html=True), name="pages")

# Thêm vào sau khi khởi tạo app, TRƯỚC các router
DATA_DIR = Path(__file__).parent.parent / "data" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# /uploads/listings/... → data/uploads/listings/...
app.mount("/uploads", StaticFiles(directory=str(DATA_DIR)), name="uploads")



# Include routers
app.include_router(auth_router)  # Authentication endpoints
app.include_router(admin_router)  # Admin dashboard endpoints
app.include_router(seller_router) # Seller endpoints
app.include_router(buyer_router)  # Buyer endpoints
app.include_router(chat_router)   # Chat endpoints

# ==================== Routes ====================

@app.get("/")
async def read_index():
    """Phục vụ trang chủ pentaMO"""
    return FileResponse("index.html")

@app.get("/login.html")
async def read_login():
    """Phục vụ trang đăng nhập"""
    return FileResponse("login.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "service": "pentaMO Agent",
        "version": "3.0.0"
    }

@app.get("/health/redis")
async def health_check_redis():
    """Check Redis connection status"""
    from backend.redis_client import redis_client
    is_connected = redis_client.is_connected()
    return {
        "status": "OK" if is_connected else "ERROR",
        "redis_connected": is_connected
    }

@app.get("/api/memory/stats")
async def memory_stats():
    """Get FAISS memory statistics"""
    try:
        stats = orchestrator.get_memory_stats()
        return {
            "success": True,
            "memory": stats
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/admin/analytics")
async def admin_analytics(db: Session = Depends(get_db), current_user: TokenPayload = Depends(get_current_user)):
    """Get AI performance metrics for admin dashboard - Protected by Admin Role"""
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    from services.evaluation_service import evaluation_service
    return evaluation_service.get_stats(db)

# ==================== WebSocket Endpoint ====================

@app.websocket("/ws/{conversation_id}")
async def websocket_endpoint(conversation_id: str, websocket: WebSocket):
    """
    WebSocket endpoint cho real-time updates
    Frontend kết nối tại ws://server/ws/{conversation_id}
    
    Sự kiện nhận được:
    - search_completed: Khi tìm kiếm xe hoàn tất
    - booking_status: Khi trạng thái booking thay đổi
    - ocr_status: Khi OCR ảnh hoàn tất
    - typing_indicator: Khi AI "gõ" (chỉ báo ẩu)
    """
    manager = get_manager()
    connection_id = await manager.connect(conversation_id, websocket)
    
    try:
        # Gửi welcome message
        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "connection_id": connection_id,
            "message": "Connected to WebSocket"
        })
        
        # Keep connection alive
        while True:
            # Lắng nghe incoming messages từ client (nếu có)
            data = await websocket.receive_text()
            # Có thể dùng để gửi heartbeat hoặc client signals
            logger.debug(f"WebSocket message from {conversation_id}: {data}")
            
    except WebSocketDisconnect:
        await manager.disconnect(conversation_id, connection_id)
        logger.info(f"WebSocket disconnected: {conversation_id}/{connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(conversation_id, connection_id)

@app.post("/api/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    message: ChatMessage,
    db: Session = Depends(get_db)
):
    """
    Gửi tin nhắn và nhận phản hồi từ Agent
    Sử dụng simplified orchestrator v3 với FAISS memory
    """
    
    try:
        # Get conversation
        conversation = db.query(Conversations).filter(
            Conversations.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Save user message
        user_msg = ChatMessages(
            conversation_id=conversation_id,
            sender_type=message.sender_type,
            sender_id=message.sender_id,
            text=message.text
        )
        db.add(user_msg)
        db.commit()
        
        # Get current state
        current_state = conversation.state or {}
        
        # Process through new simplified orchestrator
        agent_response = orchestrator.process_message(
            conversation_id,
            message.text,
            current_state,
            db=db
        )
        
        # Save agent message
        ai_message_text = agent_response.get("message", "")
        agent_msg = ChatMessages(
            conversation_id=conversation_id,
            sender_type="agent",
            sender_id="system",
            text=ai_message_text
        )
        db.add(agent_msg)
        
        # Update conversation state
        new_state = agent_response.get("state", current_state)
        conversation.state = new_state
        conversation.lead_stage = new_state.get("lead_stage", "DISCOVERY")
        
        db.commit()
        
        logger.info(
            f"[{conversation_id}] Mode: {agent_response.get('mode')}, "
            f"Source: {agent_response.get('source')}"
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "agent_response": {
                "mode": agent_response.get("mode", "consultant"),
                "message": ai_message_text,
                "source": agent_response.get("source", "llm"),
            },
            "state": new_state
        }
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conversations")
async def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    Tạo conversation mới
    """
    
    conversation = Conversations(
        buyer_id=request.buyer_id,
        seller_id=request.seller_id,
        listing_id=request.listing_id,
        lead_stage=LeadStage.DISCOVERY,
        state={
            "participants": {"buyer_id": request.buyer_id, "seller_id": request.seller_id},
            "lead_stage": "DISCOVERY",
            "constraints": {},
            "listing_context": {},
            "open_questions": [],
            "risks": {"level": "low", "flags": []},
            "tool_history": []
        }
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    logger.info(f"Created conversation {conversation.id}")
    
    return {
        "success": True,
        "conversation_id": conversation.id
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin conversation
    """
    
    conversation = db.query(Conversations).filter(
        Conversations.id == conversation_id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ChatMessages).filter(
        ChatMessages.conversation_id == conversation_id
    ).all()
    
    return {
        "success": True,
        "conversation": {
            "id": conversation.id,
            "buyer_id": conversation.buyer_id,
            "lead_stage": conversation.lead_stage,
            "state": conversation.state,
            "created_at": conversation.created_at.isoformat()
        },
        "messages": [
            {
                "id": msg.id,
                "sender_type": msg.sender_type,
                "text": msg.text,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]
    }

@app.post("/api/conversations/{conversation_id}/mode")
async def set_conversation_mode(
    conversation_id: str,
    mode: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Chuyển đổi chế độ tương tác: 'explore' (tư vấn) hoặc 'transact' (mua bán)
    """
    try:
        if mode not in ["explore", "transact"]:
            raise HTTPException(status_code=400, detail="Mode must be 'explore' or 'transact'")
        
        conversation = db.query(Conversations).filter(
            Conversations.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update mode in state
        if conversation.state is None:
            conversation.state = {}
        
        conversation.state["mode"] = mode
        conversation.state["mode_selected_at"] = datetime.utcnow().isoformat()
        db.commit()
        
        logger.info(f"Conversation {conversation_id} mode set to {mode}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "mode": mode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting mode for conversation {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/tools/provinces")
async def get_provinces():
    """
    Lấy danh sách 34 tỉnh/thành
    """
    from tools.handlers_v2 import get_provinces
    return get_provinces()

@app.get("/api/tools/search")
async def search_listings(
    q: Optional[str] = None,
    brands: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    province: Optional[str] = None,
    year_min: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Search listings từ database (Hỗ trợ từ khóa tổng quát q)
    """
    from tools.handlers_v2 import search_listings as search_handler
    
    brands_list = brands.split(",") if brands else None
    
    return search_handler(
        db=db,
        brands=brands_list,
        price_min=price_min,
        price_max=price_max,
        province=province,
        year_min=year_min,
        query_str=q
    )

# ==================== Feedback Loop (Phase 5) ====================

@app.post("/api/messages/{message_id}/feedback")
async def message_feedback(
    message_id: int,
    is_positive: bool = Body(..., embed=True),
    current_user: TokenPayload = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record user feedback for a specific AI message
    """
    from backend.security import check_feedback_rate_limit
    
    user_id = current_user.user_id
    
    # Check rate limit
    allowed, remaining = check_feedback_rate_limit(user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many feedback submissions")
        
    msg = db.query(ChatMessages).filter(ChatMessages.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    if is_positive:
        msg.positive_feedback_count += 1
    else:
        msg.negative_feedback_count += 1
        
    db.commit()
    
    return {
        "success": True,
        "message_id": message_id,
        "positive_count": msg.positive_feedback_count,
        "negative_count": msg.negative_feedback_count
    }

# ==================== Error Handlers ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )

# ==================== Startup ====================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )
