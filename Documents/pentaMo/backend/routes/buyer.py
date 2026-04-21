import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.database import get_db
from db.models import SellerListings, VerificationStatus, SavedListings, Appointments
from auth.jwt_handler import get_current_user, TokenPayload
from backend.redis_client import redis_client
from backend.utils import safe_public_url
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/buyer", tags=["buyer"])

@router.get("/spotlight-search")
async def spotlight_smart_search(
    query: str,
    province_priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Tìm kiếm siêu tốc kiểu Spotlight (Mac).
    Trong thực tế, nên dùng ElasticSearch hoặc Redisearch.
    Ở đây dùng DB ILIKE kết hợp Cache Redis để tăng tốc.
    """
    # 1. Trả về từ Cache nếu có
    cache_key = f"spotlight_search:{query}:{province_priority}"
    cached_result = redis_client.get(cache_key)
    
    if cached_result:
        logger.info(f"Spotlight Search: Cache hit for query '{query}'")
        return {"success": True, "source": "cache", "results": json.loads(cached_result)}
    
    # 2. Query từ DB nếu Cache Miss
    search_pattern = f"%{query}%"
    db_query = db.query(SellerListings).filter(
        SellerListings.verification_status.in_([VerificationStatus.VERIFIED, VerificationStatus.PENDING]),
        or_(
            SellerListings.brand.ilike(search_pattern),
            SellerListings.model_line.ilike(search_pattern)
        )
    )
    
    # Ưu tiên theo khu vực (như kế hoạch yêu cầu)
    if province_priority:
        # Lấy các result cùng tỉnh trước
        priority_results = db_query.filter(SellerListings.province == province_priority).limit(5).all()
        other_results = db_query.filter(SellerListings.province != province_priority).limit(5).all()
        results = priority_results + other_results
    else:
        results = db_query.limit(10).all()

    # 3. Chuẩn hoá dữ liệu trả về cho UI
    formatted_results = [
        {
            "id": r.id,
            "title": f"{r.brand} {r.model_line} ({r.model_year})",
            "price": r.price,
            "province": r.province,
            "condition": r.condition
        } for r in results
    ]
    
    # 4. Lưu Cache tốc độ cao trong 60 giây
    redis_client.set(cache_key, formatted_results, ex=60)
    
    return {"success": True, "source": "database", "results": formatted_results}

@router.post("/saved-listings/{listing_id}")
async def toggle_save_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lưu hoặc bỏ lưu tin đăng"""
    existing = db.query(SavedListings).filter(
        SavedListings.user_id == current_user.user_id,
        SavedListings.listing_id == listing_id
    ).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return {"success": True, "saved": False, "message": "Đã bỏ lưu tin đăng"}
    else:
        new_save = SavedListings(user_id=current_user.user_id, listing_id=listing_id)
        db.add(new_save)
        db.commit()
        return {"success": True, "saved": True, "message": "Đã lưu tin đăng"}

@router.get("/saved-listings")
async def get_saved_listings(
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lấy danh sách tin đã lưu của người dùng"""
    saved_ids = db.query(SavedListings.listing_id).filter(
        SavedListings.user_id == current_user.user_id
    ).all()
    saved_ids = [s[0] for s in saved_ids]
    
    listings = db.query(SellerListings).filter(
        SellerListings.id.in_(saved_ids)
    ).all()
    
    return {
        "success": True,
        "count": len(listings),
        "listings": [
            {
                "id": l.id,
                "brand": l.brand,
                "model_line": l.model_line,
                "model_year": l.model_year,
                "price": l.price,
                "province": l.province,
                "image_front": safe_public_url(l.image_front),
                "verification_status": l.verification_status.value if hasattr(l.verification_status, 'value') else l.verification_status
            } for l in listings
        ]
    }

@router.post("/book-appointment")
async def book_appointment_api(
    listing_id: str,
    date: str,
    location: str,
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Gửi yêu cầu đặt lịch hẹn xem xe"""
    listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    try:
        new_apt = Appointments(
            listing_id=listing_id,
            buyer_id=current_user.user_id,
            seller_id=listing.seller_id,
            appointment_date=datetime.fromisoformat(date.replace('Z', '')),
            location=location,
            status="PENDING"
        )
        db.add(new_apt)
        db.commit()
        return {"success": True, "message": "Đã gửi yêu cầu đặt lịch hẹn!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid date format or data: {str(e)}")

@router.get("/appointments")
async def get_buyer_appointments(
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user)
):
    """Lấy danh sách lịch hẹn của người mua"""
    apts = db.query(Appointments).filter(Appointments.buyer_id == current_user.user_id).order_by(Appointments.created_at.desc()).all()
    
    results = []
    for a in apts:
        listing = db.query(SellerListings).filter(SellerListings.id == a.listing_id).first()
        results.append({
            "id": a.id,
            "listing_title": f"{listing.brand} {listing.model_line}" if listing else "Unknown Vehicle",
            "date": a.appointment_date.isoformat(),
            "location": a.location,
            "status": a.status,
            "notes": a.notes
        })
    return {"success": True, "appointments": results}
