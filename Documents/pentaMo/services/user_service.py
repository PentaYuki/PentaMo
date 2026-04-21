"""
User Service - Manage user operations
Handles user retrieval, verification, and suspension
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Import database models
try:
    from db.models import Users, UserRole
    # Try new location first
except ImportError:
    try:
        # Fallback to old location
        from db.models import Users
    except ImportError:
        logger.error("Cannot import Users model")
        Users = None


class UserService:
    """Service for user management operations"""
    
    @staticmethod
    def get_users(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        role: Optional[str] = None,
        verified: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Get list of users with optional filters
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            role: Filter by user role (buyer, seller, admin)
            verified: Filter by verification status
        
        Returns:
            Dictionary with users list and metadata
        """
        try:
            if Users is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            query = db.query(Users)
            
            # Apply filters
            if role:
                query = query.filter(Users.role == role)
            
            # Note: Users model doesn't have verified column yet
            # This can be extended when user verification is added
            
            total = query.count()
            users = query.offset(skip).limit(limit).all()
            
            users_list = [
                {
                    "id": user.id,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "role": (user.role or "USER").upper(),
                    "location_province": user.location_province,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "google_id": user.google_id
                }
                for user in users
            ]
            
            return {
                "success": True,
                "total": total,
                "returned": len(users_list),
                "skip": skip,
                "limit": limit,
                "users": users_list
            }
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_user_detail(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific user
        
        Args:
            db: Database session
            user_id: ID of the user to retrieve
        
        Returns:
            Dictionary with user details
        """
        try:
            if Users is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            user = db.query(Users).filter(Users.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "error": f"User {user_id} not found"
                }
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "email": getattr(user, "email", None),
                    "role": (user.role or "USER").upper(),
                    "location_province": user.location_province,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "google_id": user.google_id
                }
            }
        except Exception as e:
            logger.error(f"Error getting user detail: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def authenticate_user(db: Session, username_or_phone: str, password: str) -> Dict[str, Any]:
        """Verify user credentials against the database with logging"""
        try:
            if Users is None: return {"success": False, "error": "Database model not available"}
            
            # Normalize input
            uid = username_or_phone.strip()
            
            # Check by phone (most common) or full_name/email
            user = db.query(Users).filter(
                (Users.phone == uid) | 
                (Users.full_name == uid)
            ).first()
            
            if not user:
                logger.warning(f"Auth failed: User not found for '{uid}'")
                return {"success": False, "error": "Invalid credentials"}
                
            if not user.password_hash:
                logger.warning(f"Auth failed: User '{uid}' has no password set (Guest)")
                return {"success": False, "error": "Invalid credentials"}
                
            if not pwd_context.verify(password, user.password_hash):
                logger.warning(f"Auth failed: Incorrect password for user '{uid}'")
                return {"success": False, "error": "Invalid credentials"}
                
            logger.info(f"Auth success: User '{uid}' logged in")
            return {"success": True, "user": user}
        except Exception as e:
            logger.error(f"Authentication error for {username_or_phone}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def upsert_user_by_phone(db: Session, phone: str, full_name: Optional[str] = None, role: str = "user", password: Optional[str] = None) -> Dict[str, Any]:
        """Get or create user by phone and synchronize password/role with uniqueness check"""
        try:
            if Users is None: return {"success": False, "error": "Database model not available"}
            
            # Normalize phone and role
            phone_norm = phone.strip()
            role_norm = role.strip().upper() if role else "USER"
            
            user = db.query(Users).filter(Users.phone == phone_norm).first()
            
            # Uniqueness check: If registering (pw provided) and user has a password already
            if user and password and user.password_hash:
                logger.warning(f"Registration failed: Phone {phone_norm} is already registered.")
                return {"success": False, "error": "Số điện thoại đã được đăng ký"}

            if not user:
                logger.info(f"Creating new user for phone: {phone_norm}")
                # Set role with validation
                role_val = UserRole.USER.value
                try:
                    role_val = UserRole[role_norm].value
                except (KeyError, AttributeError):
                    role_val = UserRole.USER.value

                user = Users(
                    phone=phone_norm, 
                    full_name=full_name or f"User_{phone_norm[-4:]}", 
                    role=role_val
                )
                db.add(user)
            else:
                logger.debug(f"Updating existing user profile (Guest -> Member) for phone: {phone_norm}")
                if full_name and user.full_name.startswith("User_"):
                    user.full_name = full_name
                if role:
                    try:
                        user.role = UserRole[role_norm].value
                    except (KeyError, AttributeError):
                        pass # Keep existing role if new one is invalid

            # Always update password if provided and user doesn't have one (or we are in 'upgrade' mode)
            if password:
                user.password_hash = pwd_context.hash(password)
                logger.info(f"Password saved for user: {phone_norm}")
            
            db.commit()
            db.refresh(user)
            return {"success": True, "user": user}
        except Exception as e:
            db.rollback()
            logger.error(f"Error in upsert_user_by_phone: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def upsert_user_by_google(db: Session, google_id: str, email: str, full_name: str) -> Dict[str, Any]:
        """Get or create user by Google ID"""
        try:
            if Users is None: return {"success": False, "error": "Database model not available"}
            user = db.query(Users).filter(Users.google_id == google_id).first()
            if not user:
                logger.info(f"Creating new Google user: {email}")
                user = Users(google_id=google_id, full_name=full_name, role="buyer")
                db.add(user)
                db.commit()
                db.refresh(user)
            return {"success": True, "user": user}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def verify_user(db: Session, user_id: str) -> Dict[str, Any]:
        """
        Manually verify a user's identity
        
        Args:
            db: Database session
            user_id: ID of the user to verify
        
        Returns:
            Dictionary with operation result
        """
        try:
            if Users is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            user = db.query(Users).filter(Users.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "error": f"User {user_id} not found"
                }
            
            # Add verified field if it doesn't exist
            if not hasattr(user, "is_verified"):
                # Field doesn't exist in schema yet
                logger.warning(f"User model doesn't have is_verified field. Skipping verification for {user_id}")
            else:
                user.is_verified = True
                user.verified_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": f"User {user_id} verified successfully",
                "user_id": user_id,
                "verified_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error verifying user: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def suspend_user(db: Session, user_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Suspend a user account
        
        Args:
            db: Database session
            user_id: ID of the user to suspend
            reason: Reason for suspension
        
        Returns:
            Dictionary with operation result
        """
        try:
            if Users is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            user = db.query(Users).filter(Users.id == user_id).first()
            
            if not user:
                return {
                    "success": False,
                    "error": f"User {user_id} not found"
                }
            
            # Add suspension tracking if fields exist
            if hasattr(user, "is_suspended"):
                user.is_suspended = True
                user.suspension_reason = reason
                user.suspended_at = datetime.utcnow()
            else:
                logger.warning(f"User model doesn't have suspension fields. Skipping suspension for {user_id}")
            
            db.commit()
            
            logger.warning(f"User {user_id} suspended. Reason: {reason}")
            
            return {
                "success": True,
                "message": f"User {user_id} suspended successfully",
                "user_id": user_id,
                "reason": reason,
                "suspended_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error suspending user: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
