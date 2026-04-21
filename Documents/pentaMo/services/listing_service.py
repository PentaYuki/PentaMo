"""
Listing Service - Manage seller listing operations
Handles listing verification, fraud detection, and risk analysis
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Import database models
try:
    from db.models import SellerListings
except ImportError:
    logger.error("Cannot import SellerListings model")
    SellerListings = None


class ListingService:
    """Service for listing management and fraud detection"""
    
    @staticmethod
    def get_pending_listings(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        risk_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get listings pending verification with optional risk filtering
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            risk_level: Filter by risk level (low, medium, high)
        
        Returns:
            Dictionary with pending listings
        """
        try:
            if SellerListings is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            from db.models import VerificationStatus
            
            query = db.query(SellerListings).filter(
                SellerListings.verification_status == VerificationStatus.PENDING
            )
            
            # Note: Risk level filtering can be enhanced with ML-based risk scoring
            # For now, we filter by image_fake_score as a proxy for risk
            if risk_level == "high":
                query = query.filter(SellerListings.image_fake_score >= 0.7)
            elif risk_level == "medium":
                query = query.filter(
                    (SellerListings.image_fake_score >= 0.4) &
                    (SellerListings.image_fake_score < 0.7)
                )
            elif risk_level == "low":
                query = query.filter(SellerListings.image_fake_score < 0.4)
            
            total = query.count()
            listings = query.order_by(SellerListings.created_at.desc()).offset(skip).limit(limit).all()
            
            listings_list = [
                {
                    "id": listing.id,
                    "seller_id": listing.seller_id,
                    "brand": listing.brand,
                    "model_year": listing.model_year,
                    "model_line": listing.model_line,
                    "color": listing.color,
                    "price": listing.price,
                    "province": listing.province,
                    "risk_score": listing.image_fake_score,
                    "created_at": listing.created_at.isoformat() if listing.created_at else None
                }
                for listing in listings
            ]
            
            return {
                "success": True,
                "total": total,
                "returned": len(listings_list),
                "skip": skip,
                "limit": limit,
                "listings": listings_list
            }
        except Exception as e:
            logger.error(f"Error getting pending listings: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def analyze_listing_risk(db: Session, listing_id: str) -> Dict[str, Any]:
        """
        Analyze risk factors for a specific listing
        
        Args:
            db: Database session
            listing_id: ID of the listing to analyze
        
        Returns:
            Dictionary with risk analysis details
        """
        try:
            if SellerListings is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
            
            if not listing:
                return {
                    "success": False,
                    "error": f"Listing {listing_id} not found"
                }
            
            # Analyze various risk factors
            risk_factors = {
                "image_authenticity": {
                    "score": listing.image_fake_score,
                    "risk": "high" if listing.image_fake_score >= 0.7 else "medium" if listing.image_fake_score >= 0.4 else "low",
                    "description": f"Image fake detection score: {listing.image_fake_score:.2%}"
                }
            }
            
            # Check for missing paperwork
            paperwork_issues = []
            if not listing.reg_cert_front or not listing.reg_cert_back:
                paperwork_issues.append("Registration certificate incomplete")
            if not listing.id_card_front or not listing.id_card_back:
                paperwork_issues.append("ID card incomplete")
            if not listing.insurance_front:
                paperwork_issues.append("Insurance document missing")
            
            if paperwork_issues:
                risk_factors["paperwork"] = {
                    "score": 0.5,
                    "risk": "medium",
                    "issues": paperwork_issues
                }
            
            # Check OCR data consistency
            ocr_issues = []
            if listing.ocr_data:
                ocr_data = listing.ocr_data if isinstance(listing.ocr_data, dict) else {}
                # Validation logic can be enhanced based on OCR requirements
                if not ocr_data.get("plate_number"):
                    ocr_issues.append("License plate number not found in OCR")
            
            if ocr_issues:
                risk_factors["ocr_validation"] = {
                    "score": 0.3,
                    "risk": "low",
                    "issues": ocr_issues
                }
            
            # Calculate overall risk score
            overall_risk_score = listing.image_fake_score
            overall_risk_level = (
                "high" if overall_risk_score >= 0.7
                else "medium" if overall_risk_score >= 0.4
                else "low"
            )
            
            return {
                "success": True,
                "listing_id": listing_id,
                "overall_risk": {
                    "score": overall_risk_score,
                    "level": overall_risk_level
                },
                "risk_factors": risk_factors,
                "recommendation": (
                    "REJECT" if overall_risk_level == "high"
                    else "REVIEW" if overall_risk_level == "medium"
                    else "APPROVE"
                ),
                "analyzed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing listing risk: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def verify_listing(
        db: Session,
        listing_id: str,
        approved: bool,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Manually verify/reject a listing
        
        Args:
            db: Database session
            listing_id: ID of the listing to verify
            approved: Whether to approve the listing
            notes: Admin notes for the verification decision
        
        Returns:
            Dictionary with verification result
        """
        try:
            if SellerListings is None:
                return {
                    "success": False,
                    "error": "Database model not available"
                }
            
            from db.models import VerificationStatus
            
            listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
            
            if not listing:
                return {
                    "success": False,
                    "error": f"Listing {listing_id} not found"
                }
            
            # Update verification status
            listing.verification_status = (
                VerificationStatus.VERIFIED if approved
                else VerificationStatus.REJECTED
            )
            
            # Store verification notes if field exists
            if hasattr(listing, "verification_notes"):
                listing.verification_notes = notes
            
            if hasattr(listing, "verified_at"):
                listing.verified_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Listing {listing_id} {'approved' if approved else 'rejected'} by admin. Notes: {notes}")
            
            return {
                "success": True,
                "message": f"Listing {listing_id} {'approved' if approved else 'rejected'} successfully",
                "listing_id": listing_id,
                "status": "VERIFIED" if approved else "REJECTED",
                "notes": notes,
                "verified_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error verifying listing: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
