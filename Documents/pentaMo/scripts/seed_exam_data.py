import sys
import os
import uuid
from datetime import datetime

# Add root to sys.path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from db.models import Users, SellerListings, VerificationStatus

def seed_exam_data():
    db = SessionLocal()
    try:
        print("--- Starting Exam Data Seed ---")
        
        # 1. Create Mock Admin Seller if not exists
        admin = db.query(Users).filter(Users.role == 'admin').first()
        if not admin:
            print("Creating Admin Seller...")
            admin = Users(
                id="admin-seller-id",
                full_name="PentaMo Official Admin",
                phone="0901234567",
                role="admin",
                password_hash="hashed_pwd" # Placeholder
            )
            db.add(admin)
            db.commit()
            print(f"Admin created: {admin.id}")
        else:
            print(f"Using existing admin: {admin.id}")

        # 2. Clear old test listings to avoid duplicates
        db.query(SellerListings).filter(SellerListings.seller_id == admin.id).delete()
        
        listings = [
            # SCENARIO 1: Price Negotiation (C1)
            {
                "brand": "Honda",
                "model_line": "SH 150i ABS",
                "model_year": 2023,
                "price": 115000000,
                "color": "Trắng",
                "province": "TP. Hồ Chí Minh",
                "condition": "Như mới (99%)",
                "address_detail": "Quận 1, TP. HCM",
                "image_front": "static/img/sh_front.png"
            },
            {
                "brand": "Honda",
                "model_line": "SH 125i CBS",
                "model_year": 2022,
                "price": 85000000,
                "color": "Đỏ",
                "province": "Hà Nội",
                "condition": "Đã sử dụng (95%)",
                "address_detail": "Đống Đa, Hà Nội"
            },
            # SCENARIO 2: Paperwork Risk (C2)
            {
                "brand": "Honda",
                "model_line": "Vision",
                "model_year": 2021,
                "price": 28000000,
                "color": "Xanh nhám",
                "province": "Bình Dương",
                "condition": "Tốt",
                "address_detail": "Dĩ An, Bình Dương",
                "brand": "Honda", # Intentional repeat for clarity
                "model_line": "Vision (Giấy tờ tay)",
                "condition": "Mất giấy tờ gốc, chỉ có giấy bán tay"
            },
            # SCENARIO 3: Fraud/Payment Risk (C3)
            {
                "brand": "Yamaha",
                "model_line": "Exciter 155 VVA",
                "model_year": 2023,
                "price": 42000000,
                "color": "Xanh GP",
                "province": "TP. Hồ Chí Minh",
                "address_detail": "Quận 7, TP. HCM",
                "condition": "Cần bán gấp, cọc trước 5 triệu giao xe tận nơi"
            },
            # Common High-volume listings
            {
                "brand": "Honda", "model_line": "Wave Alpha", "model_year": 2023, "price": 18500000, "province": "Toàn quốc", "color": "Trắng"
            },
            {
                "brand": "Honda", "model_line": "Wave RSX", "model_year": 2022, "price": 21000000, "province": "TP. HCM", "color": "Đen"
            },
            {
                "brand": "Yamaha", "model_line": "Sirius FI", "model_year": 2023, "price": 19000000, "province": "Đồng Nai", "color": "Đỏ đen"
            },
            {
                "brand": "Yamaha", "model_line": "NVX 155 Premium", "model_year": 2022, "price": 48000000, "province": "Cần Thơ", "color": "Xám"
            },
            {
                "brand": "Honda", "model_line": "Blade 110", "model_year": 2021, "price": 15000000, "province": "TP. HCM", "color": "Đỏ đen", "condition": "Xe đi kỹ, chính chủ Admin"
            }
        ]

        for l_data in listings:
            l = SellerListings(
                id=str(uuid.uuid4()),
                seller_id=admin.id,
                brand=l_data.get("brand"),
                model_line=l_data.get("model_line"),
                model_year=l_data.get("model_year", 2022),
                price=l_data.get("price"),
                color=l_data.get("color"),
                province=l_data.get("province", "TP. Hồ Chí Minh"),
                condition=l_data.get("condition", "Tốt"),
                address_detail=l_data.get("address_detail", "Đang cập nhật"),
                verification_status=VerificationStatus.VERIFIED
            )
            db.add(l)
        
        db.commit()
        print(f"Successfully seeded {len(listings)} listings for Exam scenarios.")
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_exam_data()
