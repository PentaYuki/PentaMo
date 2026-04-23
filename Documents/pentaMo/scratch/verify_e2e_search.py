"""E2E test: Verify DB search with province fix works"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.handlers_v2 import search_listings

print("TEST: Search xe tầm 15 triệu")
r = search_listings(price_max=15000000)
print(f"  Found: {r['count']} xe")
for l in r.get('listings', []):
    print(f"  - {l['brand']} {l['model_line']} | {l['price']:,.0f} | {l['province']}")

print("\nTEST: Search xe ở HCM (fuzzy province)")
r = search_listings(province="Hồ Chí Minh")
print(f"  Found: {r['count']} xe")
for l in r.get('listings', []):
    print(f"  - {l['brand']} {l['model_line']} | {l['price']:,.0f} | {l['province']}")

print("\nTEST: Search xe tầm 20 triệu ở HCM")
r = search_listings(price_max=20000000, province="Hồ Chí Minh")
print(f"  Found: {r['count']} xe")
for l in r.get('listings', []):
    print(f"  - {l['brand']} {l['model_line']} | {l['price']:,.0f} | {l['province']}")

print("\nTEST: Search Honda Vision (model query)")
r = search_listings(brands=["Honda"], query_str="Vision")
print(f"  Found: {r['count']} xe")
for l in r.get('listings', []):
    print(f"  - {l['brand']} {l['model_line']} | {l['price']:,.0f} | {l['province']}")

print("\n✅ E2E Search tests done!")
