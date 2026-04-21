import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.jwt_handler import JWTHandler, UserRole, TokenPayload
import jwt
from config.settings import settings

def test_token_validation():
    handler = JWTHandler()
    user_id = "test_id"
    username = "test_user"
    role = UserRole.USER
    
    print(f"Testing role: {role.value}")
    
    # Create token
    tokens = handler.create_access_token(user_id, username, role)
    token = tokens.access_token
    print(f"Token created: {token[:20]}...")
    
    # Simulate decode and Pydantic validation
    try:
        # 1. Decode
        payload = jwt.decode(token, handler.secret_key, algorithms=[handler.algorithm])
        print(f"Decoded payload: {payload}")
        
        # 2. Pydantic Validate
        token_payload = TokenPayload(
            user_id=payload.get("user_id"),
            username=payload.get("username"),
            role=UserRole(payload.get("role")),
            exp=datetime.fromtimestamp(payload.get("exp")),
            iat=datetime.fromtimestamp(payload.get("iat"))
        )
        print("✓ Pydantic validation successful")
        
    except Exception as e:
        print(f"✗ Validation failed: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test_token_validation()
