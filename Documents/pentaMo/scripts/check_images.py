import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from sqlalchemy.orm import Session
    from backend.database import SessionLocal
    from db.models import SellerListings
    
    def check_missing_images():
        db = SessionLocal()
        try:
            listings = db.query(SellerListings).all()
            missing_count = 0
            total_checked = 0
            
            print(f"--- Checking images for {len(listings)} listings ---\n")
            
            for l in listings:
                for field in ['image_front', 'image_back', 'image_left', 'image_right']:
                    path_str = getattr(l, field)
                    if path_str:
                        total_checked += 1
                        path = Path(path_str)
                        if not path.exists():
                            print(f"❌ Missing: Listing {l.id} | {field} | Path: {path_str}")
                            missing_count += 1
                        elif path.stat().st_size == 0:
                            print(f"⚠️ Empty: Listing {l.id} | {field} | Path: {path_str}")
                            missing_count += 1
            
            print(f"\n--- Scan Complete ---")
            print(f"Total images checked: {total_checked}")
            print(f"Total issues found:   {missing_count}")
            
            if missing_count == 0:
                print("✅ All image paths in database point to valid files on disk.")
            else:
                print("❌ Some images are missing or empty. Users will see placeholders.")
                
        finally:
            db.close()

    if __name__ == "__main__":
        check_missing_images()

except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
