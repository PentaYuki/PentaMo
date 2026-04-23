"""
Simplified Tool Handlers with Real Database Integration
Used by the new orchestrator to perform actual searches and operations
"""

import json
import logging
import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db.models import SellerListings, Users, VerificationStatus, Conversations, ChatMessages, Appointments
from backend.database import SessionLocal
from backend.utils import safe_public_url

logger = logging.getLogger(__name__)

def retry(times=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            import time
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    time.sleep(delay)
            logger.error(f"Failed {func.__name__} after {times} retries: {last_err}")
            return {"success": False, "error": str(last_err)}
        return wrapper
    return decorator


@retry(times=2, delay=0.5)
def search_listings(
    db: Optional[Session] = None,
    brands: Optional[List[str]] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    province: Optional[str] = None,
    year_min: Optional[int] = None,
    condition: Optional[str] = None,
    query_str: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Search listings from real database
    Returns verified or pending listings only
    
    Args:
        db: Database session
        brands: List of vehicle brands to filter
        price_min: Minimum price
        price_max: Maximum price
        province: Province to filter
        year_min: Minimum model year
        query_str: General search string (brand, model, color)
        limit: Maximum results to return
    
    Returns:
        Dict with success flag, count, and listings
    """
    if db is None:
        db = SessionLocal()
    
    try:
        # Build query for verified/pending listings
        query = db.query(SellerListings).filter(
            SellerListings.verification_status.in_([
                VerificationStatus.PENDING,
                VerificationStatus.VERIFIED
            ])
        )
        
        # Apply filters
        if brands:
            if isinstance(brands, str):
                brands = [brands]
            query = query.filter(SellerListings.brand.in_(brands))
        
        if price_min is not None:
            query = query.filter(SellerListings.price >= price_min)
        if price_max is not None:
            query = query.filter(SellerListings.price <= price_max)
        
        if province:
            # Fuzzy province matching to handle DB inconsistencies
            # DB may have: "Hồ Chí Minh", "TP. HCM", "TP. Hồ Chí Minh", "TP Hồ Chí Minh"
            province_variants = [f"%{province}%"]
            province_lower = province.lower()
            if "hồ chí minh" in province_lower or "hcm" in province_lower:
                province_variants = [
                    "%Hồ Chí Minh%", "%HCM%", "%Sài Gòn%", "%Saigon%"
                ]
            elif "hà nội" in province_lower:
                province_variants = ["%Hà Nội%", "%Ha Noi%"]
            elif "đà nẵng" in province_lower:
                province_variants = ["%Đà Nẵng%", "%Da Nang%"]
            
            query = query.filter(or_(*[SellerListings.province.ilike(v) for v in province_variants]))
        
        if year_min is not None:
            query = query.filter(SellerListings.model_year >= year_min)
        
        if condition:
            query = query.filter(SellerListings.condition.ilike(f"%{condition}%"))
        
        if query_str:
            # Multi-term split search: Each word must match at least one descriptive column
            terms = [t.strip() for t in query_str.split() if t.strip()]
            for term in terms:
                pattern = f"%{term}%"
                query = query.filter(or_(
                    SellerListings.brand.ilike(pattern),
                    SellerListings.model_line.ilike(pattern),
                    SellerListings.color.ilike(pattern)
                ))
        
        # Execute query and limit results
        results = query.order_by(SellerListings.created_at.desc()).limit(limit).all()
        
        # Format results
        listings = []
        for r in results:
            # Get seller info for contact display
            seller_name = None
            seller_phone = None
            try:
                from db.models import Users
                seller = db.query(Users).filter(Users.id == r.seller_id).first()
                if seller:
                    seller_name = seller.full_name
                    seller_phone = seller.phone
            except Exception:
                pass
            
            listings.append({
                "id": r.id,
                "brand": r.brand,
                "model_line": r.model_line,
                "model_year": r.model_year,
                "color": r.color,
                "condition": r.condition or "Unknown",
                "price": float(r.price),
                "province": r.province,
                "address_detail": r.address_detail or "Contact seller",
                "seller_id": r.seller_id,
                "seller_name": seller_name,
                "seller_phone": seller_phone,
                "description": getattr(r, 'description', None),
                "seller_notes": getattr(r, 'seller_notes', None),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "verification_status": r.verification_status.value if r.verification_status else "pending",
                "image_front": safe_public_url(r.image_front),
                "image_back": safe_public_url(r.image_back),
                "image_left": safe_public_url(r.image_left),
                "image_right": safe_public_url(r.image_right),
            })
        
        logger.info(f"Search found {len(listings)} listings")
        
        return {
            "success": True,
            "count": len(listings),
            "listings": listings,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "listings": []
        }


def get_listing_detail(listing_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get detailed information about a specific listing
    
    Args:
        listing_id: ID of the listing
        db: Database session
    
    Returns:
        Dict with listing details
    """
    if db is None:
        db = SessionLocal()
    
    try:
        listing = db.query(SellerListings).filter(
            SellerListings.id == listing_id
        ).first()
        
        if not listing:
            return {
                "success": False,
                "error": "Listing not found"
            }
        
        # Get seller info if available
        seller_name = f"Seller {listing.seller_id[:8]}" if listing.seller_id else "Unknown"
        try:
            seller = db.query(Users).filter(Users.id == listing.seller_id).first()
            if seller:
                seller_name = seller.full_name or seller_name
        except:
            pass
        
        return {
            "success": True,
            "listing": {
                "id": listing.id,
                "brand": listing.brand,
                "model_line": listing.model_line,
                "model_year": listing.model_year,
                "color": listing.color,
                "condition": listing.condition,
                "price": float(listing.price),
                "province": listing.province,
                "address_detail": listing.address_detail,
                "created_at": listing.created_at.isoformat() if listing.created_at else None,
                "image_front": safe_public_url(listing.image_front),
                "image_back": safe_public_url(listing.image_back),
                "image_left": safe_public_url(listing.image_left),
                "image_right": safe_public_url(listing.image_right)
            },
            "seller": {
                "id": listing.seller_id,
                "name": seller_name,
                "response_time": "Usually replies within 2 hours"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting listing detail: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@retry(times=2, delay=0.5)
def book_appointment(
    listing_id: str,
    preferred_date: Optional[str] = None,
    preferred_location: Optional[str] = None,
    conversation_id: Optional[str] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Create appointment booking request
    
    Args:
        listing_id: ID of the listing to book
        preferred_date: Preferred date for viewing (ISO format)
        preferred_location: Preferred location for viewing
        conversation_id: ID of the conversation
        db: Database session
    
    Returns:
        Dict with appointment details
    """
    if db is None:
        db = SessionLocal()
        
    try:
        # Check if listing exists
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        if not listing:
            return {"success": False, "error": "Listing not found"}
            
        # Create real appointment
        buyer_id = "unknown"
        if conversation_id:
            from db.models import Conversations
            conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
            if conv:
                buyer_id = conv.buyer_id
            else:
                # Fallback to legacy split logic if no conv record found
                buyer_id = conversation_id.split('_')[0] if '_' in conversation_id else conversation_id
        
        new_apt = Appointments(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            appointment_date=datetime.fromisoformat(preferred_date.replace('Z', '')) if preferred_date else datetime.utcnow() + timedelta(days=1),
            location=preferred_location or listing.province,
            status="PENDING",
            notes=f"Requested via AI Assistant"
        )
        db.add(new_apt)
        db.commit()
        db.refresh(new_apt)
        
        return {
            "success": True,
            "appointment_id": new_apt.id,
            "listing_id": listing_id,
            "status": "PENDING",
            "message": (
                "Yêu cầu lịch hẹn đã được gửi đến người bán. "
                "Hệ thống sẽ thông báo cho bạn khi người bán xác nhận."
            ),
            "confirmation_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_provinces() -> Dict[str, Any]:
    """Get list of 63 provinces/cities from JSON file"""
    import json
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "provinces.json")
        with open(json_path, "r", encoding="utf-8") as f:
            provinces = json.load(f)
        return {
            "success": True,
            "provinces": provinces
        }
    except Exception as e:
        logger.error(f"Error reading provinces.json: {e}")
        # Fallback
        return {"success": True, "provinces": ["Hà Nội", "TP Hồ Chí Minh", "Đà Nẵng"]}


# Mapping cho aliases (tên cũ, viết tắt)
PROVINCE_ALIASES = {
    "hcm": "TP Hồ Chí Minh",
    "saigon": "TP Hồ Chí Minh",
    "sài gòn": "TP Hồ Chí Minh",
    "tp hcm": "TP Hồ Chí Minh",
    "hà nội": "Hà Nội",
    "bắc ninh": "Bắc Ninh",
    "hải phòng": "Hải Phòng",
    "đà nẵng": "Đà Nẵng",
    "cần thơ": "Cần Thơ",
}


def normalize_province(province_input: str) -> Optional[str]:
    """
    Normalize tên tỉnh từ input người dùng
    """
    normalized = province_input.lower().strip()
    
    # Check aliases
    if normalized in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[normalized]
    
    # Check exact match trong provinces list
    provinces = get_provinces()["provinces"]
    if normalized in {p.lower() for p in provinces}:
        return next((p for p in provinces if p.lower() == normalized), None)
    
    return None


def verify_vehicle(image_path: str, plate_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Xác minh xe (vehicle verification) sử dụng OCR
    """
    try:
        # Try to use OCR if available
        try:
            from backend.models.ocr import VehicleVerificationTool
            tool = VehicleVerificationTool()
            return tool.execute(image_path=image_path, plate_number=plate_number, check_registration=True)
        except ImportError:
            # Fallback if OCR module is not available
            return {
                "success": True,
                "verification_status": "PENDING",
                "message": "Vehicle verification queued",
                "image_path": image_path
            }
    except Exception as e:
        logger.error(f"Error in verify_vehicle: {e}")
        return {
            "success": False,
            "error": str(e),
            "verification_status": "FAILED"
        }


def parse_user_intent_for_search(user_message: str) -> Dict[str, Any]:
    """
    Simple parser to extract search parameters from user message
    Returns extracted parameters that can be used for search
    
    Args:
        user_message: User's message
    
    Returns:
        Dict with extracted search parameters
    """
    params = {
        "brands": None,
        "price_min": None,
        "price_max": None,
        "province": None,
        "year_min": None,
        "condition": None,
        "query_str": None,
        "car_detected": False
    }
    
    try:
        msg_lower = user_message.lower()
        
        # Extract brand names
        brands_list = ["Honda", "Yamaha", "Suzuki", "SYM", "Piaggio", "Vespa", "Kawasaki", "Ducati"]
        for b in brands_list:
            if b.lower() in msg_lower:
                params["brands"] = [b]
                break
        
        # Model-specific keywords that are strong search signals
        model_keywords = [
            "vision", "lead", "air blade", "exciter", "winner",
            "wave", "sirius", "nvx", "janus", "grande", "nozza", "blade",
            "raider", "satria", "vario", "pcx", "freego", "latte",
            "elizabeth", "attila", "angela", "zip", "liberty", "medley",
            "sprint", "gts", "primavera", "tay ga", "côn tay"
        ]
        # Short model names need word boundary matching (sh, ab, lx, số)
        short_model_keywords = ["sh", "ab", "lx", "số"]
        
        import re as _re
        detected_model = None
        for m in model_keywords:
            if m in msg_lower:
                detected_model = m
                break
        
        if not detected_model:
            for m in short_model_keywords:
                # Use word boundary to prevent 'sh' matching inside 'shop'
                if _re.search(rf'\b{_re.escape(m)}\b', msg_lower):
                    detected_model = m
                    break
        
        # NOTE: Do NOT set query_str to raw user_message anymore.
        # Only set it if meaningful search terms remain after cleaning.
        
        # Extract price range (natural language)
        import re
        
        # Look for numbers with 'triệu' or 'tr'
        found_prices = re.findall(r'(\d+)\s*(?:triệu|tr)', msg_lower)
        if len(found_prices) >= 2:
            params["price_min"] = int(found_prices[0]) * 1_000_000
            params["price_max"] = int(found_prices[1]) * 1_000_000
        elif len(found_prices) == 1:
            params["price_max"] = int(found_prices[0]) * 1_000_000

        # Build query_str ONLY from model-relevant terms
        clean_query = msg_lower
        # 1. Strip punctuation
        import string
        for punct in string.punctuation:
            clean_query = clean_query.replace(punct, " ")
            
        # 2. Strip junk words
        junk = [
            "em ơi", "anh ơi", "chị ơi", "cho anh", "cho em", "anh cần", "em hãy", "cho tôi",
            "tìm mua", "mua xe", "ngân sách", "tầm", "khoảng", "có con nào", "bên mình",
            "cần tìm", "kiếm", "chiếc", "con", "xe", "anh", "em", "tìm", "mua", "cho", "cần",
            "tôi", "cái", "này", "đó", "kia", "chào", "muốn", "giá", "gía", "bạn", "mình",
            "xem", "hỏi", "được", "không", "nhỉ", "nhé", "nha", "ạ", "dạ", "với", "là",
            "chao", "muon", "gia", "ban", "minh", "duoc", "khong", "nhe", "co",
            "ở", "tại", "bên", "có", "nào", "gì", "thế", "thì", "nữa", "hay", "và",
            "học", "về", "tư vấn", "cho biết", "giúp", "hỏi", "thắc mắc",
            "thành phố", "hồ chí minh", "hà nội", "đà nẵng", "cần thơ",
            "sài gòn", "hải phòng", "bình dương", "đồng nai", "hcm",
            # Extra conversational junk
            "đi", "nhà", "nghỉ", "nghĩ", "làm", "sao", "như", "vậy", "lắm",
            "quá", "rất", "cũng", "nhưng", "mà", "rồi", "ơi", "nhá",
            # Shopping/browsing junk — NOT vehicle model names
            "shop", "rẻ", "đắt", "tốt", "đẹp", "chất lượng", "giá rẻ", "giá cả",
            "những", "máy", "loại", "dòng", "nên", "ra sao", "thế nào", "bao nhiêu",
            "bên bạn", "bên shop", "cửa hàng", "liệt kê", "helo", "hello", "hi",
            "xin chào", "hàng", "ngang", "phù hợp"
        ]
        # Sort junk by length descending to avoid partial matches
        junk.sort(key=len, reverse=True)
        
        # Normalize for junk matching
        from unidecode import unidecode
        
        for word in junk:
            # Match both accented and unaccented versions
            norm_word = unidecode(word)
            
            # Pattern for accented
            p1 = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
            clean_query = p1.sub(" ", clean_query)
            
            # Pattern for unaccented
            if norm_word != word:
                p2 = re.compile(rf'\b{re.escape(norm_word)}\b', re.IGNORECASE)
                clean_query = p2.sub(" ", clean_query)

        
        # 3. Strip brand name if already detected to allow focus on model
        if params["brands"]:
            for b in params["brands"]:
                clean_query = clean_query.replace(b.lower(), " ")

        # 4. Strip specific price mentions
        clean_query = re.sub(r'\d+\s*(?:triệu|tr)', '', clean_query)
        
        # Final cleanup: collapse spaces
        cleaned = " ".join(clean_query.split()).strip()
        
        # KEY FIX: Only set query_str if there are actual meaningful terms left
        # (brand names, model names, or at least 2+ chars of meaningful content)
        if cleaned and len(cleaned) >= 2:
            # Check if cleaned string contains any known model keyword
            has_model_term = any(m in cleaned.lower() for m in model_keywords)
            # Also check short model keywords with word boundary
            if not has_model_term:
                has_model_term = any(_re.search(rf'\b{_re.escape(m)}\b', cleaned.lower()) for m in short_model_keywords)
            if has_model_term:
                params["query_str"] = cleaned
            else:
                # Don't use random leftover words as query_str — they cause false matches
                params["query_str"] = None
        else:
            params["query_str"] = None
        
        # If a model keyword was detected, always include it in query_str
        if detected_model and not params["query_str"]:
            params["query_str"] = detected_model
        
        # Extract year (simple pattern)
        year_pattern = r'(201\d|202\d)'
        years = re.findall(year_pattern, msg_lower)
        if years:
            params["year_min"] = int(years[0])

        # Detect car keywords
        car_keywords = ["ô tô", "oto", "car", "suv", "hatchback", "sedan", "innova", "vios", "ranger"]
        if any(kw in msg_lower for kw in car_keywords):
            params["car_detected"] = True
        
        # Extract province keywords — use broad fuzzy patterns to handle
        # DB inconsistencies ("Hồ Chí Minh", "TP. HCM", "TP. Hồ Chí Minh")
        provinces_keywords = {
            "hà nội": "Hà Nội",
            "sài gòn": "Hồ Chí Minh",
            "hcm": "Hồ Chí Minh",
            "hồ chí minh": "Hồ Chí Minh",
            "tp hồ chí minh": "Hồ Chí Minh",
            "thành phố hồ chí minh": "Hồ Chí Minh",
            "hải phòng": "Hải Phòng",
            "đà nẵng": "Đà Nẵng",
            "huế": "Thừa Thiên Huế",
            "cần thơ": "Cần Thơ",
            "bình dương": "Bình Dương",
            "đồng nai": "Đồng Nai",
        }
        # Sort by length descending so "thành phố hồ chí minh" matches before "hcm"
        for keyword in sorted(provinces_keywords.keys(), key=len, reverse=True):
            if keyword in msg_lower:
                params["province"] = provinces_keywords[keyword]
                break
        
        # Extract condition
        if any(kw in msg_lower for kw in ["mới", "đập hộp", "chưa lăn bánh"]):
            params["condition"] = "New"
        elif any(kw in msg_lower for kw in ["cũ", "qua sử dụng", "đã dùng"]):
            params["condition"] = "Used"
        elif any(kw in msg_lower for kw in ["lướt", "như mới", "99%"]):
            params["condition"] = "Like New"
        
    except Exception as e:
        logger.debug(f"Error parsing intent: {e}")
    
    return params
@retry(times=2, delay=0.5)
def create_chat_channel(
    listing_id: str,
    buyer_id: str,
    seller_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Create a secure chat channel between buyer and seller
    """
    if db is None:
        db = SessionLocal()
    
    try:
        # Check if conversation exists
        conv = db.query(Conversations).filter(
            Conversations.listing_id == listing_id,
            Conversations.buyer_id == buyer_id
        ).first()
        
        if not conv:
            conv = Conversations(
                buyer_id=buyer_id,
                seller_id=seller_id,
                listing_id=listing_id,
                state={}
            )
            db.add(conv)
            db.flush()

        channel_id = f"ch_{conv.id[:8]}_{int(datetime.utcnow().timestamp())}"
        conv.channel_id = channel_id
        db.commit()
        
        return {
            "success": True,
            "channel_id": channel_id,
            "message": "Kênh chat đã được tạo công khai. Bạn có thể trao đổi trực tiếp với người bán."
        }
    except Exception as e:
        db.rollback()
        raise e

def detect_risks(
    text: str,
    conversation_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Identify potential risks (fraud, external links, payment requests)
    """
    risks = []
    level = "low"
    
    # Simple rule-based risk detection
    risk_patterns = {
        "external_contact": [r"zalo", r"0\d{9}", r"facebook", r"fb.com"],
        "suspicious_payment": [r"chuyển tiền trước", r"đặt cọc", r"bank", r"stk"],
        "fraud_signal": [r"triệu đô", r"miễn phí", r"trúng thưởng"],
        "missing_papers": [r"không giấy", r"mất đăng ký", r"không chính chủ", r"giấy đi đường", r"mẹ bồng con"],
        "price_anomaly": [r"giá rẻ bất ngờ", r"giá sốc"]
    }
    
    import re
    msg_lower = text.lower()
    for risk_type, patterns in risk_patterns.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                risks.append({"type": risk_type, "pattern": pattern})
                level = "high" if risk_type in ["suspicious_payment", "missing_papers"] else "medium"
    
    # Contextual check: Logic for price vs common sense
    if "sh" in msg_lower and any(p in msg_lower for p in ["5 triệu", "10 triệu", "7tr"]):
        risks.append({"type": "price_anomaly", "detail": "SH price too low"})
        level = "high"

    return {
        "success": True,
        "risk_level": level,
        "risks": risks,
        "detected_at": datetime.utcnow().isoformat()
    }

def handoff_to_human(conversation_id: str, reason: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Escalate conversation to a human administrator or seller
    """
    if db is None:
        db = SessionLocal()
        
    try:
        conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
        if not conv:
            return {"success": False, "error": "Conversation not found"}
        
        # If it was an AI conversation (seller_id is None), assign to Admin
        if conv.seller_id is None:
            admin = db.query(Users).filter(Users.role == "admin").first()
            if admin:
                conv.seller_id = admin.id
        
        # Update state
        state = conv.state or {}
        state["handoff_active"] = True
        state["handoff_time"] = datetime.now().isoformat()
        state["handoff_reason"] = reason
        conv.state = state
        
        db.commit()
        logger.warning(f"!!! ESCALATION !!! Conv: {conversation_id} | Reason: {reason}")
        
        return {
            "success": True, 
            "message": "Em đã chuyển yêu cầu của anh/chị cho bộ phận hỗ trợ kỹ thuật xử lý rồi ạ. Chờ chút sẽ có anh/chị admin vào hỗ trợ mình liền nha!",
            "escalated": True
        }
    except Exception as e:
        logger.error(f"Handoff error: {e}")
        return {"success": False, "error": str(e)}

def create_purchase_order_and_handoff(
    conversation_id: str, 
    listing_id: str, 
    buyer_id: str,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Creates a transaction record and initiates handoff to Admin"""
    if db is None:
        db = SessionLocal()
    
    from db.models import Transactions, LeadStage
    
    try:
        # 1. Get Listing info
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        if not listing:
            return {"success": False, "error": "Listing not found"}
            
        # 2. Create Transaction
        new_tx = Transactions(
            id=str(uuid.uuid4()),
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id or 'admin-seller-id',
            amount=listing.price,
            conversation_id=conversation_id,
            status="COMPLETED"
        )
        db.add(new_tx)
        
        # 3. Update Conversation
        conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
        if conv:
            conv.lead_stage = LeadStage.COMPLETED
            conv.outcome = "CLOSED_WON"
            conv.seller_id = listing.seller_id # Assign to real seller/admin
            
            state = conv.state or {}
            state["purchase_completed"] = True
            state["transaction_id"] = new_tx.id
            state["handoff_active"] = True
            conv.state = state
            
        db.commit()
        logger.info(f"✓ Purchase created: TX {new_tx.id} for Listing {listing_id}")
        
        return {
            "success": True, 
            "message": "CHỐT ĐƠN THÀNH CÔNG! Em đã lập hóa đơn và chuyển cho anh/chị Admin hỗ trợ bàn giao xe ngay cho mình ạ.", 
            "transaction_id": new_tx.id,
            "amount": listing.price,
            "vehicle": f"{listing.brand} {listing.model_line}"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Purchase error: {e}")
        return {"success": False, "error": str(e)}

