"""JWT token management and authentication"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from enum import Enum
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from config.settings import settings

logger = logging.getLogger(__name__)

# User roles
class UserRole(str, Enum):
    """Admin role levels"""
    SUPER_ADMIN = "ADMIN"  # Consolidated for simplicity
    ADMIN = "ADMIN"
    MODERATOR = "ADMIN"
    BUYER = "USER"
    SELLER = "USER"
    USER = "USER"
    VIEWER = "VIEWER"



# Token schemas
class TokenPayload(BaseModel):
    model_config = {"protected_namespaces": ()}
    """JWT token payload"""
    user_id: str
    username: str
    role: UserRole
    exp: datetime
    iat: datetime


class TokenResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    """Token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    """Refresh token request"""
    refresh_token: str


# JWT Handler
class JWTHandler:
    """Manages JWT token creation and validation"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = "HS256"
        self.access_token_expire = 2592000  # 30 days (increased for persistent testing session)
        self.refresh_token_expire = 2592000  # 30 days
        
        if not self.secret_key or len(self.secret_key) < 32:
            logger.warning("⚠️ JWT_SECRET_KEY not set or too short (min 32 chars)")
    
    def create_access_token(self,
                          user_id: str,
                          username: str,
                          role: UserRole = UserRole.VIEWER) -> TokenResponse:
        """Create new access token"""
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.access_token_expire)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role.value,
            "exp": exp.timestamp(),
            "iat": now.timestamp(),
            "type": "access"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return TokenResponse(
                access_token=token,
                expires_in=self.access_token_expire
            )
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token"""
        
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self.refresh_token_expire)
        
        payload = {
            "user_id": user_id,
            "exp": exp.timestamp(),
            "iat": now.timestamp(),
            "type": "refresh"
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise
    
    def create_token_pair(self,
                         user_id: str,
                         username: str,
                         role: UserRole = UserRole.VIEWER) -> TokenResponse:
        """Create both access and refresh tokens"""
        
        access_response = self.create_access_token(user_id, username, role)
        refresh_token = self.create_refresh_token(user_id)
        
        access_response.refresh_token = refresh_token
        return access_response
    
    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode token"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return TokenPayload(
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                role=UserRole(payload.get("role", "VIEWER").upper()),
                exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
            )
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify refresh token and return user_id"""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            return {"user_id": payload.get("user_id")}
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )


# FastAPI dependency for token extraction
security = HTTPBearer()
jwt_handler = JWTHandler()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenPayload:
    """Dependency to extract and verify current user from JWT"""
    return jwt_handler.verify_token(credentials.credentials)


def require_role(*allowed_roles: UserRole):
    """Dependency factory for role-based access control"""
    
    async def role_checker(current_user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join([r.value for r in allowed_roles])}"
            )
        return current_user
    
    return role_checker


# Utility functions
def get_jwt_handler() -> JWTHandler:
    """Get the global JWT handler instance"""
    return jwt_handler
