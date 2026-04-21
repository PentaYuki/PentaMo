"""Authentication endpoints"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from auth.jwt_handler import (
    JWTHandler, UserRole, TokenResponse, TokenRefreshRequest,
    get_current_user, get_jwt_handler
)
from sqlalchemy.orm import Session
from backend.database import get_db
from services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response schemas
class LoginRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    """Admin login request"""
    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    """Login response"""
    success: bool
    access_token: str
    refresh_token: Optional[str] = None
    user: dict


# Demo accounts for Phase 3/4
DEMO_USERS = {
    "admin": {
        "password": "PentaMo@Admin123",
        "role": UserRole.SUPER_ADMIN,
        "user_id": "admin_001"
    },
    "moderator": {
        "password": "PentaMo@Mod456",
        "role": UserRole.MODERATOR,
        "user_id": "mod_001"
    },
    "buyer": {
        "password": "PentaMo@Buyer789",
        "role": UserRole.BUYER,
        "user_id": "buyer_001"
    },
    "seller": {
        "password": "PentaMo@Seller321",
        "role": UserRole.SELLER,
        "user_id": "seller_001"
    }
}


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Admin/User login endpoint"""
    
    # 1. Check Demo Users first (Dev convenience)
    clean_username = request.username.strip()
    user_data = DEMO_USERS.get(clean_username)
    user_id = None
    username = clean_username
    role_str = None

    if user_data and user_data["password"] == request.password:
        user_id = user_data["user_id"]
        role_str = user_data["role"].value.upper()
        logger.info(f"✓ Demo User logged in: {request.username}")
    else:
        # 2. Fallback to Database
        auth_result = UserService.authenticate_user(db, request.username, request.password)
        if auth_result["success"]:
            user = auth_result["user"]
            user_id = user.id
            username = user.full_name
            role_str = (user.role or "USER").upper()
            logger.info(f"✓ DB User logged in: {username} ({user.phone})")
        else:
            logger.warning(f"Failed login attempt for user: {request.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
    
    jwt_handler = get_jwt_handler()
    tokens = jwt_handler.create_token_pair(
        user_id=user_id,
        username=username,
        role=UserRole(role_str)
    )
    
    # Create response with tokens
    response_data = {
        "success": True,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "user": {
            "username": username,
            "user_id": user_id,
            "id": user_id,
            "role": role_str
        }
    }
    
    # Create response with JSON data
    response = JSONResponse(content=response_data)
    
    # Set authentication cookie (httpOnly for security, accessible to server only)
    response.set_cookie(
        key="pentamo_token",
        value=tokens.access_token,
        httponly=False,  # Allow JavaScript to read it for Authorization header
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=86400  # 24 hours
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key="pentamo_refresh",
        value=tokens.refresh_token,
        httponly=True,  # Don't expose refresh token to JavaScript
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=604800  # 7 days
    )
    
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest):
    """Refresh access token"""
    
    jwt_handler = get_jwt_handler()
    
    # Verify refresh token
    payload = jwt_handler.verify_refresh_token(request.refresh_token)
    user_id = payload["user_id"]
    
    # Find user to get their role and username
    username = None
    role = UserRole.VIEWER
    
    for uname, udata in DEMO_USERS.items():
        if udata["user_id"] == user_id:
            username = uname
            role = udata["role"]
            break
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    tokens = jwt_handler.create_access_token(user_id, username, role)
    
    logger.info(f"✓ Token refreshed for user: {username}")
    
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in
    )


@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user"""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role.value,
        "token_expires": current_user.exp.isoformat()
    }


@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout endpoint (token should be invalidated on client side)"""
    logger.info(f"✓ User logged out: {current_user.username}")
    return {"status": "logged_out", "message": "Please remove token from client"}


# --- Phase 2: MOCK Google Auth & Phone OTP Auth ---
class GoogleAuthRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    google_id: str
    email: str
    full_name: str

class OTPAuthRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    phone: str
    otp: str
    role: str  # "buyer" or "seller"

class FastPhoneLoginRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    phone: str
    password: Optional[str] = None
    role: str = "user"

@router.post("/phone-login-test")
async def phone_login_test(req: FastPhoneLoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint đăng nhập nhanh chỉ bằng SĐT (Bỏ qua OTP - dùng cho Dev/Test)
    Tự động tạo user nếu chưa có trong DB.
    """
    logger.info(f"Fast Phone Login cho: {req.phone}")
    
    # Persist to DB
    result = UserService.upsert_user_by_phone(db, phone=req.phone.strip(), role=req.role, password=req.password)
    if not result["success"]:
        # Handle specific "Already registered" case with 400 instead of 500
        status_code = 400 if "đã được đăng ký" in result["error"] else 500
        raise HTTPException(status_code=status_code, detail=result["error"])
    
    user = result["user"]
    jwt_handler = get_jwt_handler()
    tokens = jwt_handler.create_token_pair(
        user_id=user.id,
        username=user.full_name,
        role=UserRole.USER
    )
    
    response_data = {
        "success": True,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "user": {
            "id": user.id,
            "user_id": user.id,
            "full_name": user.full_name,
            "role": user.role.upper()
        }
    }
    
    response = JSONResponse(content=response_data)
    
    # Set authentication cookie (Sync with login route)
    response.set_cookie(
        key="pentamo_token",
        value=tokens.access_token,
        httponly=False,
        secure=False,
        samesite="lax",
        max_age=86400
    )
    
    return response

@router.post("/mock-google-login")
async def mock_google_login(google_req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Mock endpoint giả lập Google OAuth Flow
    Thực tế frontend sẽ gửi mã code (idToken), api này verify với google và generate JWT token
    """
    logger.info(f"Mock Google Login cho user: {google_req.email}")
    
    # Persist to DB
    result = UserService.upsert_user_by_google(
        db, 
        google_id=google_req.google_id,
        email=google_req.email,
        full_name=google_req.full_name
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
        
    user = result["user"]
    jwt_handler = get_jwt_handler()
    tokens = jwt_handler.create_token_pair(
        user_id=user.id,
        username=user.full_name,
        role=UserRole.BUYER # Google users are buyers by default
    )
    
    return {
        "success": True,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role.upper()
        },
        "message": "Đăng nhập Google thành công."
    }

@router.post("/mock-otp-verify")
async def mock_otp_verify(otp_req: OTPAuthRequest, db: Session = Depends(get_db)):
    """
    Mock endpoint kiểm tra OTP
    Sau khi check OTP hợp lệ, sẽ cập nhật Role cho User theo tuỳ chọn
    """
    if otp_req.otp != "123456": # Giả lập OTP luôn là 123456
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ, hãy nhập 123456"
        )
    
    try:
        new_role_val = otp_req.role.lower()
        new_role = UserRole(new_role_val)
    except ValueError:
        new_role = UserRole.BUYER
        
    # Persist to DB
    result = UserService.upsert_user_by_phone(db, phone=otp_req.phone, role=UserRole.USER.value)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
        
    user = result["user"]
    jwt_handler = get_jwt_handler()
    
    # Render lại token với role mới
    tokens = jwt_handler.create_token_pair(
        user_id=user.id,
        username=user.full_name,
        role=UserRole.USER
    )
    
    return {
        "success": True,
        "access_token": tokens.access_token,
        "role": user.role,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "role": user.role.upper()
        },
        "message": "Xác minh SĐT thành công."
    }

