import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.handlers_v2 import search_listings, parse_user_intent_for_search
from backend.database import SessionLocal

db = SessionLocal()
msg = "Anh tìm mua Honda Blade tầm 15 triệu."
params = parse_user_intent_for_search(msg)
print(f"Extracted Params: {params}")

# Use the logic from orchestrator_v3.py
clean_q = params.get("query_str") or msg
words = clean_q.split()
if len(words) > 3:
    junk = ["em", "ơi", "anh", "chị", "đang", "tìm", "mua", "một", "chiếc", "mẫu"]
    keywords = [w for w in words if w.lower() not in junk]
    q_str = " ".join(keywords) if len(keywords) <= 3 else " ".join(keywords[-3:])
else:
    q_str = clean_q
print(f"Final q_str used: '{q_str}'")

results = search_listings(
    brands=params.get("brands"),
    price_min=params.get("price_min"),
    price_max=params.get("price_max"),
    query_str=q_str
)

print(f"Results Success: {results.get('success')}")
print(f"Results Count: {results.get('count')}")
if results.get('count', 0) > 0:
    for l in results['listings']:
        print(f" - {l['brand']} {l['model_line']} Price: {l['price']}")

db.close()
