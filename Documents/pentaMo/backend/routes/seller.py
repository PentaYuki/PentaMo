import os
import logging
import uuid
import unicodedata
import re
from unidecode import unidecode
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import get_db
from db.models import SellerListings, VerificationStatus, Users, Appointments
from auth.jwt_handler import get_current_user, UserRole, require_role, TokenPayload
from services.faiss_memory import get_faiss_memory
import json
from backend.utils import to_public_url, safe_public_url

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    """Chuyển tên file về ASCII-safe bằng unidecode, không dấu, không khoảng trắng"""
    if not name:
        return "unnamed"
    # 1. Chuyển đổi ký tự có dấu thành không dấu ASCII sạch
    name = unidecode(name)
    # 2. Thay khoảng trắng và ký tự đặc biệt bằng dấu gạch dưới
    name = re.sub(r"[^\w.\-]", "_", name)
    return name.lower()

router = APIRouter(prefix="/api/seller", tags=["seller"])

# ==================== TEST ENDPOINTS (No Auth Required) ====================

@router.post("/listings-test")
async def create_listing_test(
    brand: str = Form(...),
    model_year: int = Form(...),
    model_line: str = Form(...),
    color: str = Form(...),
    condition: str = Form(...),
    price: float = Form(...),
    province: str = Form(...),
    address_detail: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    sale_method: str = Form("NORMAL")
):
    """Test endpoint - Tạo listing KHÔNG cần authentication"""
    try:
        new_listing = SellerListings(
            seller_id="test-seller",
            brand=str(brand),
            model_year=int(model_year),
            model_line=str(model_line),
            color=str(color),
            condition=str(condition),
            price=float(price),
            province=str(province),
            address_detail=str(address_detail) if address_detail else None,
            verification_status=VerificationStatus.PENDING,
            sale_method=str(sale_method) if sale_method else "NORMAL"
        )
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        
        logger.info(f"✓ [TEST] Created listing {new_listing.id}")
        
        return {
            "success": True, 
            "listing_id": new_listing.id, 
            "message": "Vehicle details saved (TEST endpoint).",
            "brand": new_listing.brand,
            "model_line": new_listing.model_line
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating test listing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create listing: {str(e)}")


@router.post("/listings-test/{listing_id}/upload-docs-test")
async def upload_documents_test(
    listing_id: str,
    reg_cert_front: UploadFile = File(None),
    reg_cert_back: UploadFile = File(None),
    insurance_front: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Test endpoint - Upload documents KHÔNG cần authentication"""
    try:
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        # Lưu file vào thư mục (absolute path)
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        doc_dir = project_root / "data" / "uploads" / "documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[TEST] Document directory: {doc_dir}")

        files_saved = {}
        
        if reg_cert_front: 
            try:
                filename = f"{listing_id}_reg_front_test_{int(datetime.now().timestamp())}_{sanitize_filename(reg_cert_front.filename)}"
                path = doc_dir / filename
                content = await reg_cert_front.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                # Kiểm tra file thực sư tồn tại và có dữ liệu
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.reg_cert_front = str(path)
                files_saved['reg_cert_front'] = str(path)
                logger.info(f"✓ [TEST] Saved reg_cert_front: {path}")
            except Exception as e:
                logger.error(f"Error saving reg_cert_front: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to save file: {e}")
        
        if reg_cert_back:
            try:
                filename = f"{listing_id}_reg_back_test_{int(datetime.now().timestamp())}_{sanitize_filename(reg_cert_back.filename)}"
                path = doc_dir / filename
                content = await reg_cert_back.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.reg_cert_back = str(path)
                files_saved['reg_cert_back'] = str(path)
                logger.info(f"✓ [TEST] Saved reg_cert_back: {path}")
            except Exception as e:
                logger.error(f"Error saving reg_cert_back: {e}")

        if insurance_front:
            try:
                filename = f"{listing_id}_ins_test_{int(datetime.now().timestamp())}_{sanitize_filename(insurance_front.filename)}"
                path = doc_dir / filename
                content = await insurance_front.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.insurance_front = str(path)
                files_saved['insurance_front'] = str(path)
                logger.info(f"✓ [TEST] Saved insurance: {path}")
            except Exception as e:
                logger.error(f"Error saving insurance: {e}")

        # Commit to database
        db.commit()
        db.refresh(listing)
        logger.info(f"✓ [TEST] Documents committed for listing {listing_id}")
        
        return {
            "success": True, 
            "message": "Documents uploaded (TEST endpoint)",
            "files_saved": files_saved,
            "listing_id": listing_id
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in upload test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/listings-test/{listing_id}/upload-photos-test")
async def upload_vehicle_photos_test(
    listing_id: str,
    image_front: UploadFile = File(None),
    image_back: UploadFile = File(None),
    image_left: UploadFile = File(None),
    image_right: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Test endpoint - Upload photos KHÔNG cần authentication"""
    try:
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        img_dir = project_root / "data" / "uploads" / "listings"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[TEST] Image directory: {img_dir}")

        files_saved = {}
        for field_name, file_obj in [
            ("image_front", image_front), 
            ("image_back", image_back), 
            ("image_left", image_left), 
            ("image_right", image_right)
        ]:
            if file_obj:
                try:
                    filename = f"{listing_id}_{field_name}_test_{int(datetime.now().timestamp())}_{sanitize_filename(file_obj.filename)}"
                    path = img_dir / filename
                    content = await file_obj.read()
                    with open(str(path), "wb") as f:
                        f.write(content)
                        
                    if not path.exists() or path.stat().st_size == 0:
                        raise IOError(f"Failed to write photo file for {field_name}")
                        
                    setattr(listing, field_name, str(path))
                    files_saved[field_name] = str(path)
                    logger.info(f"✓ [TEST] Saved {field_name}: {path}")
                except Exception as e:
                    logger.error(f"Error saving {field_name}: {e}")
        
        db.commit()
        db.refresh(listing)
        logger.info(f"✓ [TEST] Photos committed for listing {listing_id}")

        return {
            "success": True, 
            "message": "Photos uploaded (TEST endpoint)",
            "files_saved": files_saved,
            "listing_id": listing_id
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in upload photos test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# --- Phase 3.1: OCR Mock Function ---
def mock_ocr_processing(file_name: str, listing_brand: str = "Honda", listing_model: str = "Vision") -> dict:
    """Mô phỏng bóc tách OCR từ giấy tờ thật"""
    logger.info(f"Processing OCR for {file_name}...")
    # Giả lập kết quả OCR khớp với loại xe đã đăng để xác thực chéo
    return {
        "plate_number": f"{10 + hash(file_name)%89}A1-{10000 + hash(file_name)%89999}",
        "brand": listing_brand,
        "model_line": listing_model,
        "color": "Đen",
        "owner_name": "NGUYỄN VĂN A",
        "chassis_number": f"RLH{uuid.uuid4().hex[:12].upper()}",
        "engine_number": f"JF58E-{hash(file_name)%999999}",
        "ocr_confidence": 0.94
    }

# --- Phase 3.2: Fraud Detection Mock Function (Background Task) ---
def mock_anti_fraud_check(listing_id: str, photo_names: List[str]):
    """Giả lập quá trình check Anti-fraud chạy nền"""
    logger.info(f"[Background Task] Running Anti-Fraud Check on Listing {listing_id} with photos {photo_names}")
    from backend.database import SessionLocal
    
    db = SessionLocal()
    try:
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        if listing:
            # Fake logic: nếu tên file chứa từ "internet", cho fake score cao
            has_internet_photo = any("internet" in name.lower() for name in photo_names)
            listing.image_fake_score = 0.85 if has_internet_photo else 0.15
            
            # Cập nhật status
            if listing.image_fake_score > 0.7:
                listing.verification_status = VerificationStatus.REJECTED
            
            db.commit()
            logger.info(f"[Background Task] Finished Anti-Fraud. Score: {listing.image_fake_score}")
    except Exception as e:
        logger.error(f"Error in background anti-fraud check: {e}")
    finally:
        db.close()


# --- Phase 3.4: Dynamic Data Sync to AI Memory ---
def index_listing_to_faiss(listing: SellerListings):
    """Cập nhật dữ liệu xe mới vào bộ nhớ AI (FAISS) ngay lập tức"""
    try:
        faiss_mem = get_faiss_memory("main")
        
        # Tạo mô tả xe thân thiện với chatbot
        car_info = f"Xe {listing.brand} {listing.model_line} năm {listing.model_year}, màu {listing.color}, giá {listing.price:,.0f} VNĐ, khu vực {listing.province}."
        
        # Các câu hỏi mà khách có thể hỏi để dẫn tới xe này
        questions = [
            f"Bên em có xe {listing.brand} nào không?",
            f"Anh tìm xe {listing.brand} {listing.model_line} tầm giá {listing.price:,.0f}",
            f"Có chiếc {listing.brand} nào ở {listing.province} không em?",
            f"Xe máy cũ {listing.brand} {listing.model_line} giá rẻ",
            f"Tư vấn cho anh chiếc {listing.brand} {listing.model_line}"
        ]
        
        # Câu trả lời AI sẽ dùng (có thể tùy chỉnh thêm link hoặc ID)
        answer = (
            f"Dạ có ạ! Bên em vừa mới về chiếc {listing.brand} {listing.model_line} đời {listing.model_year}, màu {listing.color} rất đẹp. "
            f"Xe đang được chào bán với giá {listing.price:,.0f} VNĐ tại {listing.province}. Anh/chị có muốn em hỗ trợ xem chi tiết xe này không ạ?"
        )
        
        # Thêm vào FAISS cho từng "câu hỏi gợi ý"
        for q in questions:
            faiss_mem.add(
                question=q,
                answer=answer,
                mode="consultant",
                metadata_extra={
                    "listing_id": listing.id,
                    "type": "new_inventory",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        logger.info(f"✓ AI Memory updated for Listing {listing.id} ({listing.brand} {listing.model_line})")
    except Exception as e:
        logger.error(f"Failed to index listing to FAISS: {e}")

@router.post("/listings")
async def create_listing(
    brand: str = Form(...),
    model_year: int = Form(...),
    model_line: str = Form(...),
    color: str = Form(...),
    condition: str = Form(...),
    price: float = Form(...),
    province: str = Form(...),
    address_detail: Optional[str] = Form(None),
    sale_method: str = Form("NORMAL"),
    current_user: TokenPayload = Depends(require_role(UserRole.USER, UserRole.SELLER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Tạo mới một listing trắng"""
    try:
        new_listing = SellerListings(
            seller_id=current_user.user_id,
            brand=str(brand),
            model_year=int(model_year),
            model_line=str(model_line),
            color=str(color),
            condition=str(condition),
            price=float(price),
            province=str(province),
            address_detail=str(address_detail) if address_detail else None,
            verification_status=VerificationStatus.VERIFIED,
            sale_method=str(sale_method) if sale_method else "NORMAL"
        )
        db.add(new_listing)
        db.commit()
        db.refresh(new_listing)
        
        logger.info(f"✓ Created listing {new_listing.id} for seller {current_user.user_id}")
        
        # Cập nhật bộ nhớ AI
        index_listing_to_faiss(new_listing)
        
        return {
            "success": True, 
            "listing_id": new_listing.id, 
            "message": "Vehicle details saved.",
            "brand": new_listing.brand,
            "model_line": new_listing.model_line,
            "price": new_listing.price
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating listing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create listing: {str(e)}")


@router.get("/listings")
async def get_my_listings(
    current_user: TokenPayload = Depends(require_role(UserRole.USER, UserRole.SELLER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Lấy danh sách tin đăng của chính người dùng hiện tại"""
    try:
        listings = db.query(SellerListings).filter(
            SellerListings.seller_id == current_user.user_id
        ).order_by(SellerListings.created_at.desc()).all()
        
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
                    "verification_status": l.verification_status.value if hasattr(l.verification_status, 'value') else l.verification_status,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                    "image_front": safe_public_url(l.image_front),
                    "image_back": safe_public_url(l.image_back),
                    "image_left": safe_public_url(l.image_left),
                    "image_right": safe_public_url(l.image_right)
                } for l in listings
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching my listings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch listings")


@router.post("/listings/{listing_id}/upload-docs")
async def upload_documents(
    listing_id: str,
    reg_cert_front: UploadFile = File(None),
    reg_cert_back: UploadFile = File(None),
    insurance_front: UploadFile = File(None),
    id_card_front: UploadFile = File(None),
    id_card_back: UploadFile = File(None),
    current_user: TokenPayload = Depends(require_role(UserRole.USER, UserRole.SELLER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    API Upload giấy tờ và quét OCR.
    Mô phỏng module Vision AI quét mặt trước/sau để trích xuất text.
    Tất cả file đều tùy chọn.
    """
    try:
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        
        if not listing or (listing.seller_id != current_user.user_id and current_user.role != UserRole.ADMIN):
            raise HTTPException(status_code=404, detail="Listing not found or access denied")

        # Lưu file thực tế vào thư mục data/uploads/documents/ (absolute path)
        import os
        from pathlib import Path
        
        # Get absolute path
        project_root = Path(__file__).parent.parent.parent  # Navigate to project root
        doc_dir = project_root / "data" / "uploads" / "documents"
        
        # Create directory if not exists
        doc_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Document directory: {doc_dir}")

        files_saved = {}
        
        if reg_cert_front: 
            try:
                # Lấy extension từ filename
                orig_name = reg_cert_front.filename or "reg_cert_front"
                ext = os.path.splitext(orig_name)[1] or ".pdf"
                filename = f"{listing_id}_reg_front_{int(datetime.now().timestamp())}{ext}"
                path = doc_dir / filename
                content = await reg_cert_front.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.reg_cert_front = str(path)
                files_saved['reg_cert_front'] = str(path)
                logger.info(f"Saved reg_cert_front: {path}")
            except Exception as e:
                logger.error(f"Error saving reg_cert_front: {e}")
                # Không fail vì file khác, chỉ log lại
        
        if reg_cert_back: 
            try:
                orig_name = reg_cert_back.filename or "reg_cert_back"
                ext = os.path.splitext(orig_name)[1] or ".pdf"
                filename = f"{listing_id}_reg_back_{int(datetime.now().timestamp())}{ext}"
                path = doc_dir / filename
                content = await reg_cert_back.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.reg_cert_back = str(path)
                files_saved['reg_cert_back'] = str(path)
                logger.info(f"Saved reg_cert_back: {path}")
            except Exception as e:
                logger.error(f"Error saving reg_cert_back: {e}")

        if insurance_front: 
            try:
                orig_name = insurance_front.filename or "insurance"
                ext = os.path.splitext(orig_name)[1] or ".pdf"
                filename = f"{listing_id}_ins_{int(datetime.now().timestamp())}{ext}"
                path = doc_dir / filename
                content = await insurance_front.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.insurance_front = str(path)
                files_saved['insurance_front'] = str(path)
                logger.info(f"Saved insurance_front: {path}")
            except Exception as e:
                logger.error(f"Error saving insurance_front: {e}")

        if id_card_front:
            try:
                orig_name = id_card_front.filename or "id_card_front"
                ext = os.path.splitext(orig_name)[1] or ".pdf"
                filename = f"{listing_id}_id_front_{int(datetime.now().timestamp())}{ext}"
                path = doc_dir / filename
                content = await id_card_front.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.id_card_front = str(path)
                files_saved['id_card_front'] = str(path)
                logger.info(f"Saved id_card_front: {path}")
            except Exception as e:
                logger.error(f"Error saving id_card_front: {e}")

        if id_card_back:
            try:
                orig_name = id_card_back.filename or "id_card_back"
                ext = os.path.splitext(orig_name)[1] or ".pdf"
                filename = f"{listing_id}_id_back_{int(datetime.now().timestamp())}{ext}"
                path = doc_dir / filename
                content = await id_card_back.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError("Failed to write document file")
                    
                listing.id_card_back = str(path)
                files_saved['id_card_back'] = str(path)
                logger.info(f"Saved id_card_back: {path}")
            except Exception as e:
                logger.error(f"Error saving id_card_back: {e}")

        # Chạy bóc tách OCR thật (mô phỏng dựa trên brand/model của listing)
        ocr_result = mock_ocr_processing(
            reg_cert_front.filename if reg_cert_front else "unknown.jpg", 
            listing.brand, 
            listing.model_line
        )
        listing.ocr_data = ocr_result
        
        # CRITICAL: Ensure commit happens
        db.commit()
        db.refresh(listing)
        logger.info(f"✓ Documents saved and committed for listing {listing_id}")
        
        return {
            "success": True, 
            "message": "Documents uploaded and OCR processed.",
            "files_saved": files_saved,
            "ocr_extracted_data": ocr_result,
            "listing_id": listing_id
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in upload_documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.post("/listings/{listing_id}/upload-photos")
async def upload_vehicle_photos(
    listing_id: str,
    background_tasks: BackgroundTasks,
    image_front: UploadFile = File(...),
    image_back: UploadFile = File(...),
    image_left: UploadFile = File(...),
    image_right: UploadFile = File(...),
    current_user: TokenPayload = Depends(require_role(UserRole.USER, UserRole.SELLER, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """
    API tải lên 4 góc hình xe.
    Sau khi tải lên, Background Task sẽ chạy mock engine phát hiện ảnh giả / mạng.
    """
    try:
        listing = db.query(SellerListings).filter(SellerListings.id == listing_id).first()
        
        if not listing or (listing.seller_id != current_user.user_id and current_user.role != UserRole.ADMIN):
            raise HTTPException(status_code=404, detail="Listing not found or access denied")

        # Lưu file thực tế vào thư mục data/uploads/listings/ (absolute path)
        from pathlib import Path
        
        # Get absolute path
        project_root = Path(__file__).parent.parent.parent
        img_dir = project_root / "data" / "uploads" / "listings"
        
        # Create directory if not exists
        img_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Image directory: {img_dir}")

        # Lưu 4 góc ảnh
        files_saved = {}
        for field_name, file_obj in [
            ("image_front", image_front), 
            ("image_back", image_back), 
            ("image_left", image_left), 
            ("image_right", image_right)
        ]:
            try:
                filename = f"{listing_id}_{field_name}_{int(datetime.now().timestamp())}_{sanitize_filename(file_obj.filename)}"
                path = img_dir / filename
                content = await file_obj.read()
                with open(str(path), "wb") as f:
                    f.write(content)
                    
                if not path.exists() or path.stat().st_size == 0:
                    raise IOError(f"Failed to write photo file for {field_name}")
                    
                setattr(listing, field_name, str(path))
                files_saved[field_name] = str(path)
                logger.info(f"Saved {field_name}: {path}")
            except Exception as e:
                logger.error(f"Error saving {field_name}: {e}")
                raise HTTPException(status_code=400, detail=f"Failed to save {field_name}: {e}")
        
        # CRITICAL: Ensure commit happens before background task
        db.commit()
        db.refresh(listing)
        logger.info(f"✓ Vehicle photos saved and committed for listing {listing_id}")

        # Gửi vào hàng đợi queue xử lý Anti-fraud check để không làm chậm response (Phase 3 yêu cầu Queue Job/Background)
        file_names = [image_front.filename, image_back.filename, image_left.filename, image_right.filename]
        background_tasks.add_task(mock_anti_fraud_check, listing_id, file_names)

        return {
            "success": True, 
            "message": "Vehicle photos uploaded. Anti-fraud check queued in background.",
            "files_saved": {k: safe_public_url(v) for k, v in files_saved.items()},
            "listing_id": listing_id
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in upload_vehicle_photos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/appointments")
async def get_seller_appointments(
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(UserRole.SELLER, UserRole.ADMIN, UserRole.USER))
):
    """Lấy danh sách yêu cầu lịch hẹn gửi đến người bán"""
    apts = db.query(Appointments).filter(Appointments.seller_id == current_user.user_id).order_by(Appointments.created_at.desc()).all()
    
    results = []
    for a in apts:
        listing = db.query(SellerListings).filter(SellerListings.id == a.listing_id).first()
        buyer = db.query(Users).filter(Users.id == a.buyer_id).first()
        results.append({
            "id": a.id,
            "listing_title": f"{listing.brand} {listing.model_line}" if listing else "Unknown Vehicle",
            "buyer_name": buyer.full_name if buyer else "Anonymous Buyer",
            "date": a.appointment_date.isoformat(),
            "location": a.location,
            "status": a.status,
            "notes": a.notes
        })
    return {"success": True, "appointments": results}

@router.patch("/appointments/{apt_id}")
async def update_appointment_status(
    apt_id: str,
    status: str, # ACCEPTED, REJECTED
    db: Session = Depends(get_db),
    current_user: TokenPayload = Depends(require_role(UserRole.SELLER, UserRole.ADMIN, UserRole.USER))
):
    """Chấp nhận hoặc từ chối lịch hẹn"""
    apt = db.query(Appointments).filter(Appointments.id == apt_id, Appointments.seller_id == current_user.user_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    if status not in ["ACCEPTED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    apt.status = status
    db.commit()
    return {"success": True, "message": f"Đã { 'chấp nhận' if status == 'ACCEPTED' else 'từ chối' } lịch hẹn."}
