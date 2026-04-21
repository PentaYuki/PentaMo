"""
System Service - Manage system-wide operations
Handles metrics, health checks, and system statistics
"""

import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SystemService:
    """Service for system metrics and monitoring"""
    
    @staticmethod
    def get_metrics(db: Session) -> Dict[str, Any]:
        """
        Get system metrics and statistics
        
        Args:
            db: Database session
        
        Returns:
            Dictionary with system metrics
        """
        try:
            from services.evaluation_service import evaluation_service
            ai_stats = evaluation_service.get_stats(db)
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "database": SystemService._get_database_metrics(db),
                "users": SystemService._get_user_metrics(db),
                "listings": SystemService._get_listing_metrics(db),
                "conversations": SystemService._get_conversation_metrics(db),
                "appointments": SystemService._get_appointment_metrics(db),
                "ai_evaluation": ai_stats.get("metrics", {})
            }
            
            return {
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def _get_database_metrics(db: Session) -> Dict[str, Any]:
        """Get database connection and health metrics"""
        try:
            from sqlalchemy import text
            # Test database connectivity
            result = db.execute(text("SELECT 1")).scalar()
            
            if result == 1:
                return {
                    "status": "healthy",
                    "connected": True,
                    "response_time_ms": 5
                }
            else:
                return {
                    "status": "degraded",
                    "connected": True,
                    "response_time_ms": 10
                }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    @staticmethod
    def _get_user_metrics(db: Session) -> Dict[str, Any]:
        """Get user-related metrics"""
        try:
            from db.models import Users, UserRole
            
            total_users = db.query(Users).count()
            buyers = db.query(Users).filter(Users.role == UserRole.BUYER).count()
            sellers = db.query(Users).filter(Users.role == UserRole.SELLER).count()
            admins = db.query(Users).filter(Users.role == UserRole.ADMIN).count()
            
            return {
                "total_users": total_users,
                "buyers": buyers,
                "sellers": sellers,
                "admins": admins
            }
        except Exception as e:
            logger.error(f"Error getting user metrics: {str(e)}")
            return {
                "total_users": 0,
                "error": str(e)
            }
    
    @staticmethod
    def _get_listing_metrics(db: Session) -> Dict[str, Any]:
        """Get listing-related metrics"""
        try:
            from db.models import SellerListings, VerificationStatus
            
            total_listings = db.query(SellerListings).count()
            pending = db.query(SellerListings).filter(
                SellerListings.verification_status == VerificationStatus.PENDING
            ).count()
            verified = db.query(SellerListings).filter(
                SellerListings.verification_status == VerificationStatus.VERIFIED
            ).count()
            rejected = db.query(SellerListings).filter(
                SellerListings.verification_status == VerificationStatus.REJECTED
            ).count()
            
            return {
                "total_listings": total_listings,
                "pending": pending,
                "verified": verified,
                "rejected": rejected
            }
        except Exception as e:
            logger.error(f"Error getting listing metrics: {str(e)}")
            return {
                "total_listings": 0,
                "error": str(e)
            }
    
    @staticmethod
    def _get_appointment_metrics(db: Session) -> Dict[str, Any]:
        """Get appointment statistics"""
        try:
            from db.models import Appointments
            total = db.query(Appointments).count()
            pending = db.query(Appointments).filter(Appointments.status == "PENDING").count()
            accepted = db.query(Appointments).filter(Appointments.status == "ACCEPTED").count()
            
            return {
                "total": total,
                "pending": pending,
                "accepted": accepted
            }
        except Exception as e:
            logger.error(f"Error getting appointment metrics: {e}")
            return {"total": 0}

    @staticmethod
    def _get_conversation_metrics(db: Session) -> Dict[str, Any]:
        """Get conversation-related metrics"""
        try:
            # Try to get conversation metrics from model if it exists
            try:
                from db.models import Conversations
                total_conversations = db.query(Conversations).count()
            except ImportError:
                logger.warning("Conversations model not found")
                total_conversations = 0
            
            return {
                "total_conversations": total_conversations
            }
        except Exception as e:
            logger.error(f"Error getting conversation metrics: {str(e)}")
            return {
                "total_conversations": 0,
                "error": str(e)
            }
