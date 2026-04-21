"""Authentication module"""

from .jwt_handler import (
    JWTHandler,
    UserRole,
    TokenPayload,
    TokenResponse,
    get_current_user,
    require_role,
    get_jwt_handler
)
from .routes import router as auth_router

__all__ = [
    "JWTHandler",
    "UserRole",
    "TokenPayload",
    "TokenResponse",
    "get_current_user",
    "require_role",
    "get_jwt_handler",
    "auth_router"
]
