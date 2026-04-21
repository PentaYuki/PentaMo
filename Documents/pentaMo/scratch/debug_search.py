
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from tools.handlers_v2 import search_listings
from db.models import SellerListings, VerificationStatus

db = SessionLocal()
try:
    print("--- Database check ---")
    listings = db.query(SellerListings).all()
    print(f"Total listings in DB: {len(listings)}")
    for l in listings[:3]:
        print(f"Listing ID: {l.id}, Status: '{l.verification_status}', Status Type: {type(l.verification_status)}")

    print("\n--- Search Handler test ---")
    results = search_listings(db=db)
    print(f"Search results success: {results.get('success')}")
    print(f"Search results count: {results.get('count')}")
    if not results.get('success'):
        print(f"Error: {results.get('error')}")

    print("\n--- Manual query test ---")
    # Simulate the query in search_listings
    query = db.query(SellerListings).filter(
        SellerListings.verification_status.in_([
            VerificationStatus.PENDING,
            VerificationStatus.VERIFIED
        ])
    )
    manual_results = query.all()
    print(f"Manual query results count: {len(manual_results)}")
    
    # Try with raw strings
    query_raw = db.query(SellerListings).filter(
        SellerListings.verification_status.in_(['pending', 'verified'])
    )
    manual_results_raw = query_raw.all()
    print(f"Manual query (raw strings) results count: {len(manual_results_raw)}")

finally:
    db.close()
