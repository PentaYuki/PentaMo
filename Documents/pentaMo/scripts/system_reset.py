import sys
import os
import shutil
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from sqlalchemy import text
    from backend.database import SessionLocal
    
    def total_reset():
        print("--- Starting Total System Reset ---")
        
        db = SessionLocal()
        try:
            # 1. Reset Database Tables
            print("Resetting database tables...")
            tables_to_empty = [
                'users',
                'buyer_requests',
                'seller_listings',
                'chat_messages',
                'conversations',
                'saved_listings',
                'tool_logs',
                'appointments'
            ]
            
            # Disable foreign key checks for SQLite/Postgres
            try:
                db.execute(text("PRAGMA foreign_keys = OFF;")) # SQLite
            except:
                db.execute(text("SET session_replication_role = 'replica';")) # Postgres fallback
                
            for table in tables_to_empty:
                try:
                    print(f"  Truncating {table}...")
                    db.execute(text(f"DELETE FROM {table};"))
                    # Reset auto-increment
                    try:
                        db.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}';"))
                    except:
                        pass
                    db.commit()
                    print(f"  ✓ {table} cleared.")
                except Exception as e:
                    print(f"  ! Could not clear {table} (might not exist): {e}")
                    db.rollback()
            
            print("✅ Database reset process completed.")
            
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            db.rollback()
        finally:
            db.close()

        # 2. Cleanup Uploads
        print("\nCleaning up upload directories...")
        upload_paths = [
            PROJECT_ROOT / "data" / "uploads" / "listings",
            PROJECT_ROOT / "data" / "uploads" / "documents"
        ]
        
        for path in upload_paths:
            if path.exists():
                print(f"  Cleaning {path}...")
                for item in path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                print(f"  ✓ {path.name} directory cleared.")
            else:
                print(f"  ! {path} does not exist. Skipping.")

        # 3. Clear FAISS Memory
        print("\nClearing FAISS memory...")
        faiss_dir = PROJECT_ROOT / "data" / "faiss"
        if faiss_dir.exists():
            print(f"  Removing files in {faiss_dir}...")
            for item in faiss_dir.iterdir():
                if item.is_file():
                    item.unlink()
            print("  ✓ FAISS memory cleared.")
        else:
            print("  ! FAISS directory does not exist. Skipping.")

        print("\n--- Reset Complete. System is now clean. ---")

    if __name__ == "__main__":
        confirm = input("ARE YOU SURE? This will delete all listings and chats. (yes/no): ")
        if confirm.lower() == 'yes':
            total_reset()
        else:
            print("Aborted.")

except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
