import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.database import SessionLocal
from tools.handlers_v2 import parse_user_intent_for_search, search_listings

msg = "Tìm cho tôi chiếc Honda SH 150i ABS"
params = parse_user_intent_for_search(msg)
print(f"Params: {params}")

db = SessionLocal()
res = search_listings(
    brands=params.get("brands"),
    price_min=params.get("price_min"),
    price_max=params.get("price_max"),
    province=params.get("province"),
    year_min=params.get("year_min"),
    condition=params.get("condition"),
    query_str=params.get("query_str"),
    limit=5
)
print(f"Results: {res}")
