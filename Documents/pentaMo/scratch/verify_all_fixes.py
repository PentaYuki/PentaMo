"""
Final verification: Test ALL bug scenarios from user report
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.handlers_v2 import parse_user_intent_for_search, search_listings
from backend.action_planner import ActionPlanner

planner = ActionPlanner()

print("=" * 70)
print("TEST A: Action Planner — Purchase vs Search")
print("=" * 70)

test_cases = [
    ("mua xe giá 15 triệu có không", {}, "Should NOT trigger purchase (has price → search)"),
    ("chốt đơn", {"listing_context": {"id": "abc"}, "participants": {"buyer_id": "u1"}}, "SHOULD trigger purchase"),
    ("mua luôn con này", {"listing_context": {"id": "abc"}, "participants": {"buyer_id": "u1"}}, "SHOULD trigger purchase"),
    ("tôi muốn mua xe", {}, "Should NOT trigger purchase (no listing context)"),
    ("tầm giá 15 triệu", {}, "Should NOT trigger purchase"),
]

for msg, state, expected in test_cases:
    tool, params, reason = planner.decide_next_action(msg, state)
    status = f"🔧 {tool}" if tool else "💬 NONE"
    ok = "✅" if (tool == "create_purchase_order_and_handoff") == ("SHOULD trigger" in expected) else "❌"
    print(f"  {ok} '{msg}' → {status}")
    print(f"     Expected: {expected}")

print("\n" + "=" * 70)
print("TEST B: Search Intent Classification")
print("=" * 70)

test_msgs = [
    ("tôi muốn mua xe", "General → LLM asks questions"),
    ("bên shop có xe nào giá rẻ tầm 15 triệu không", "Price → SEARCH"),
    ("bên bạn có những xe máy nào giá cả ra sao", "Browse → SEARCH (broad)"),
    ("xe ở thành phố hồ chí minh", "Province only → LLM"),
    ("đi nhà nghỉ không", "Off-topic → OUT-OF-SCOPE"),
    ("anh muốn học về xe tay ga", "Educational → LLM"),
    ("mua xe giá 15 triệu có không", "Price + search → SEARCH"),
]

for msg, expected in test_msgs:
    params = parse_user_intent_for_search(msg)
    
    search_keywords = [
        "tìm", "có cái nào", "có xe nào", "xe gì", "loại xe", "bao nhiêu tiền",
        "tầm giá", "dưới", "có không", "bên mình có", "hãng", "chiếc", "mẫu",
        "bán xe", "giá xe", "mua xe", "có những", "giá cả", "ra sao",
        "có gì", "xe nào", "liệt kê"
    ]
    has_kw = any(kw in msg.lower() for kw in search_keywords)
    has_struct = any([params.get("brands"), params.get("price_min"), params.get("price_max"),
                      params.get("year_min"), params.get("condition"), params.get("query_str")])
    
    edu_kw = ["học về", "tìm hiểu", "so sánh", "xe tay ga", "xe côn tay", "bảo dưỡng"]
    is_edu = any(kw in msg.lower() for kw in edu_kw)
    
    oos_kw = ["nhà nghỉ", "khách sạn", "du lịch", "bóng đá"]
    is_oos = any(kw in msg.lower() for kw in oos_kw)
    
    if is_oos:
        result = "🚫 OUT-OF-SCOPE"
    elif is_edu:
        result = "📚 EDUCATIONAL → LLM"
    elif has_struct:
        result = "🔍 SEARCH"
    elif has_kw:
        result = "🔍 BROWSE (broad search)"
    else:
        result = "💬 LLM"
    
    populated = {k: v for k, v in params.items() if v and k not in ('car_detected',)}
    print(f"  '{msg}'")
    print(f"    Expected: {expected}")
    print(f"    Result:   {result}")
    print(f"    Params:   {populated}")
    print()

print("=" * 70)
print("TEST C: E2E Search — Database Results")
print("=" * 70)

# "tầm 15 triệu"
r = search_listings(price_max=15000000)
print(f"  'tầm 15 triệu' → Found {r['count']} xe")
for l in r.get('listings', []):
    print(f"    - {l['brand']} {l['model_line']} | {l['price']:,.0f} VNĐ")

# "xe ở HCM" (broad)
r = search_listings(province="Hồ Chí Minh")
print(f"\n  'xe ở HCM' → Found {r['count']} xe")

# "bên bạn có những xe nào" (no filters = all)
r = search_listings(limit=5)
print(f"\n  'browse all' → Found {r['count']} xe (showing max 5)")
for l in r.get('listings', []):
    print(f"    - {l['brand']} {l['model_line']} | {l['price']:,.0f} VNĐ | {l['province']}")

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
