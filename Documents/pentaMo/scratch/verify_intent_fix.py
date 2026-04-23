"""
Verification Script: Test that AI responses are correct for different message types.
Tests the 5 scenarios from the bug report.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.handlers_v2 import parse_user_intent_for_search

# ─── Test parse_user_intent_for_search ───────────────────────────────────────
print("=" * 70)
print("TEST 1: parse_user_intent_for_search — Intent Classification")
print("=" * 70)

test_messages = [
    ("tôi muốn mua xe", "General intent, should NOT trigger specific search"),
    ("Mua bên bạn có xe nào tầm giá 15 triệu không", "Has price → SHOULD search"),
    ("xe ở thành phố hồ chí minh", "Province only → should NOT search (no price/brand)"),
    ("đi nhà nghỉ không", "Off-topic → should NOT search at all"),
    ("anh muốn học về xe tay ga", "Educational → should NOT search"),
    ("Honda Vision giá bao nhiêu", "Brand + model + search keyword → SHOULD search"),
    ("có xe nào tầm 20 triệu ở HCM không", "Full search: price + province + keyword → SHOULD search"),
    ("tìm xe Yamaha Exciter", "Brand + model + keyword → SHOULD search"),
]

for msg, expected in test_messages:
    params = parse_user_intent_for_search(msg)
    
    # Check which params are populated
    populated = {k: v for k, v in params.items() if v and k != 'car_detected'}
    
    print(f"\n📩 Message: '{msg}'")
    print(f"   Expected: {expected}")
    print(f"   Params: {populated}")
    
    # Check if search would be triggered (same logic as orchestrator v3 fixed)
    search_keywords = [
        "tìm", "có cái nào", "có xe nào", "xe gì", "loại xe", "bao nhiêu tiền",
        "tầm giá", "dưới", "có không", "bên mình có", "hãng", "chiếc", "mẫu",
        "bán xe", "giá xe", "mua xe"
    ]
    has_search_keywords = any(kw in msg.lower() for kw in search_keywords)
    has_structured = any([
        params.get("brands"),
        params.get("price_min"),
        params.get("price_max"),
        params.get("year_min"),
        params.get("condition"),
        params.get("query_str"),
    ])
    
    # Educational check
    educational_keywords = [
        "học về", "tìm hiểu", "so sánh", "khác nhau", "ưu điểm", "nhược điểm",
        "nên mua", "loại nào tốt", "tay ga là gì", "côn tay là gì",
        "xe tay ga", "xe côn tay", "xe số", "bảo dưỡng", "bảo trì",
        "thay nhớt", "kinh nghiệm", "lưu ý", "hướng dẫn",
        "đăng ký xe", "sang tên", "giấy tờ cần", "thủ tục",
        "tiêu hao nhiên liệu", "tiết kiệm xăng"
    ]
    is_educational = any(kw in msg.lower() for kw in educational_keywords)
    
    # New logic: structured params required, search keywords alone NOT enough
    would_search = has_structured and not is_educational
    # Exception: search keywords + province = valid
    if has_search_keywords and params.get("province") and not is_educational:
        would_search = True
    
    status = "🔍 SEARCH" if would_search else "💬 LLM/CHAT"
    print(f"   → Result: {status}")

# ─── Test Province Matching ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("TEST 2: Province Normalization")  
print("=" * 70)

province_tests = [
    "xe ở thành phố hồ chí minh",
    "tìm xe HCM",
    "xe Sài Gòn",
    "ở hà nội",
]

for msg in province_tests:
    params = parse_user_intent_for_search(msg)
    print(f"  '{msg}' → province: {params.get('province', 'None')}")

# ─── Test Out-of-Scope Detection ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("TEST 3: Out-of-Scope Detection")
print("=" * 70)

# Simulate _check_safety
out_of_scope_keywords = [
    "nấu ăn", "thời tiết", "chính trị", "đầu tư chứng khoán", "bóng đá",
    "nhà nghỉ", "khách sạn", "du lịch", "đi chơi", "phim", "nhạc",
    "game", "trò chơi", "yêu đương", "tình yêu", "bói", "tử vi",
    "crypto", "bitcoin", "forex", "bất động sản"
]

oos_tests = [
    "đi nhà nghỉ không",
    "thời tiết hôm nay thế nào",
    "tôi muốn mua xe Honda", 
    "anh muốn học về xe tay ga",
]

for msg in oos_tests:
    is_safe = not any(kw in msg.lower() for kw in out_of_scope_keywords)
    status = "✅ IN-SCOPE" if is_safe else "🚫 OUT-OF-SCOPE"
    print(f"  '{msg}' → {status}")

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
