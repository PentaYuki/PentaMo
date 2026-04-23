#!/usr/bin/env python3
"""
Seed Data Script - Khởi tạo SQLite Database từ listings.json
Chạy: python scripts/seed_database.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Thêm parent directory vào path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, SellerListings, Users, UserRole
from config.settings import settings
import uuid

def load_listings_data():
    """Đọc dữ liệu từ listings.json"""
    data_path = Path(__file__).parent.parent / 'data' / 'listings.json'
    
    if not data_path.exists():
        print(f"❌ File not found: {data_path}")
        print("Tạo file listings.json mẫu...")
        create_sample_listings(data_path)
        
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_sample_listings(path):
    """Tạo file listings.json mẫu"""
    sample_data = [
        {
            "id": "lst-001",
            "brand": "Honda",
            "model_line": "Winner X",
            "model_year": 2022,
            "color": "Trắng",
            "condition": "Mới",
            "price": 34500000,
            "province": "Hồ Chí Minh",
            "address_detail": "Quận 1, TP.HCM",
            "seller_id": "seller-001",
            "seller_name": "Nguyễn Văn A"
        },
        {
            "id": "lst-002",
            "brand": "Yamaha",
            "model_line": "NVX 155",
            "model_year": 2023,
            "color": "Đền",
            "condition": "Nhẽ",
            "price": 33000000,
            "province": "Hồ Chí Minh",
            "address_detail": "Quận 7, TP.HCM",
            "seller_id": "seller-002",
            "seller_name": "Trần Thị B"
        },
        {
            "id": "lst-003",
            "brand": "Honda",
            "model_line": "SH 125i",
            "model_year": 2021,
            "color": "Xanh",
            "condition": "Tốt",
            "price": 45000000,
            "province": "Hà Nội",
            "address_detail": "Ba Đình, Hà Nội",
            "seller_id": "seller-003",
            "seller_name": "Lê Văn C"
        },
        {
            "id": "lst-004",
            "brand": "Suzuki",
            "model_line": "Burgman 200",
            "model_year": 2020,
            "color": "Đen",
            "condition": "Tốt",
            "price": 48000000,
            "province": "Đà Nẵng",
            "address_detail": "Hải Châu, Đà Nẵng",
            "seller_id": "seller-004",
            "seller_name": "Phạm Minh D"
        },
        {
            "id": "lst-005",
            "brand": "Yamaha",
            "model_line": "Exciter 155",
            "model_year": 2024,
            "color": "Trắng",
            "condition": "Mới",
            "price": 32000000,
            "province": "Hồ Chí Minh",
            "address_detail": "Tân Bình, TP.HCM",
            "seller_id": "seller-005",
            "seller_name": "Võ Thị E"
        }
    ]
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Tạo sample listings: {path}")

def seed_database():
    """Khởi tạo database với dữ liệu từ listings.json"""
    
    # Kết nối database
    engine = create_engine(settings.database_url)
    
    # Tạo tables
    print("🔄 Creating database tables...")
    Base.metadata.create_all(engine)
    print("✅ Database tables created")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 1. Tạo sample users (sellers)
        print("\n🔄 Seeding sellers...")
        sellers = [
            Users(
                id="admin-seller-id",
                full_name="PentaMo Official Admin",
                phone="0000000000",
                role=UserRole.ADMIN,
                location_province="Hồ Chí Minh"
            ),
            Users(
                id=str(uuid.uuid4()),
                full_name="Nguyễn Văn A",
                phone="0912345678",
                role=UserRole.SELLER,
                location_province="Hồ Chí Minh"
            ),
            Users(
                id=str(uuid.uuid4()),
                full_name="Trần Thị B",
                phone="0912345679",
                role=UserRole.SELLER,
                location_province="Hồ Chí Minh"
            ),
            Users(
                id=str(uuid.uuid4()),
                full_name="Lê Văn C",
                phone="0987654321",
                role=UserRole.SELLER,
                location_province="Hà Nội"
            ),
            Users(
                id=str(uuid.uuid4()),
                full_name="Phạm Minh D",
                phone="0987654322",
                role=UserRole.SELLER,
                location_province="Đà Nẵng"
            ),
            Users(
                id=str(uuid.uuid4()),
                full_name="Võ Thị E",
                phone="0987654323",
                role=UserRole.SELLER,
                location_province="Hồ Chí Minh"
            )
        ]
        
        # Lưu sellers
        for seller in sellers:
            existing_by_phone = session.query(Users).filter(Users.phone == seller.phone).first()
            existing_by_id = session.query(Users).filter(Users.id == seller.id).first()
            if not existing_by_phone and not existing_by_id:
                session.add(seller)
        
        session.commit()
        existing_sellers = session.query(Users).filter(Users.role == UserRole.SELLER).all()
        print(f"✅ {len(existing_sellers)} sellers in database")
        
        # 2. Tải listings từ JSON
        listings_data = load_listings_data()
        print(f"\n🔄 Seeding {len(listings_data)} listings...")
        
        seller_map = {seller.full_name: seller.id for seller in existing_sellers}
        
        # 3. Thêm listings vào database
        for listing_data in listings_data:
            # Tìm seller_id từ seller_name hoặc lấy seller đầu tiên
            seller_name = listing_data.get('seller_name', '')
            seller_id = seller_map.get(seller_name) or existing_sellers[0].id
            
            # Kiểm tra xem listing đã tồn tại
            existing = session.query(SellerListings).filter(
                SellerListings.brand == listing_data['brand'],
                SellerListings.model_line == listing_data['model_line'],
                SellerListings.seller_id == seller_id
            ).first()
            
            if not existing:
                listing = SellerListings(
                    id=listing_data.get('id', str(uuid.uuid4())),
                    seller_id=seller_id,
                    brand=listing_data['brand'],
                    model_line=listing_data['model_line'],
                    model_year=listing_data['model_year'],
                    color=listing_data['color'],
                    condition=listing_data['condition'],
                    price=listing_data['price'],
                    province=listing_data['province'],
                    address_detail=listing_data.get('address_detail', ''),
                    verification_status='VERIFIED',
                    created_at=datetime.utcnow()
                )
                session.add(listing)
        
        session.commit()
        total_listings = session.query(SellerListings).count()
        print(f"✅ {total_listings} listings in database")
        
        # 4. Print summary
        print("\n" + "="*60)
        print("✅ Database seeding completed!")
        print("="*60)
        print(f"Database: {settings.database_url}")
        print(f"Total Sellers: {len(existing_sellers)}")
        print(f"Total Listings: {total_listings}")
        print("="*60)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
