#!/usr/bin/env python
"""
run_booking_scenario.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kịch bản chạy thử: Buyer chốt đơn → Agent gửi xác nhận lịch hẹn
→ Seller nhận và chấp nhận lịch hẹn.

Flow:
  T0  Buyer nhắn hỏi xe (DISCOVERY)
  T1  Agent tìm kiếm, trả kết quả (MATCHING)
  T2  Buyer quan tâm 1 xe cụ thể (selection)
  T3  Buyer đặt lịch xem xe
  T4  Agent tạo booking → gửi xác nhận cho BUYER
  T5  Seller nhận thông báo → chấp nhận lịch
  T6  Agent gửi xác nhận hoàn chỉnh cho cả hai bên

Chạy:
    cd /Users/gooleseswsq1gmail.com/Documents/pentaMo
    python run_booking_scenario.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── project root on PYTHONPATH ────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── minimal logging ───────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)

# ── mock tool stubs (replace with real imports if backend up) ─
MOCK_LISTING = {
    "id":           "lst-air-blade-2021",
    "brand":        "Honda",
    "model_line":   "Air Blade",
    "model_year":   2021,
    "price":        28_500_000,
    "province":     "TP Hồ Chí Minh",
    "odo_km":       19_000,
    "condition":    "Máy móc zin, bảo dưỡng định kỳ",
    "seller_id":    "seller_nguyen_van_a",
    "seller_phone": "0901 234 567",
    "verified":     True,
}

MOCK_BUYER = {
    "id":    "buyer_tran_thi_b",
    "name":  "Trần Thị B",
    "phone": "0912 345 678",
}

CHANNEL_ID = "chan-c1-20260422"


def mock_search_listings(brands, price_max, province):
    """Simulated search_listings() tool."""
    if price_max >= 28_500_000:
        return {"success": True, "count": 1, "listings": [MOCK_LISTING]}
    return {"success": True, "count": 0, "listings": []}


def mock_create_chat_bridge(buyer_id, seller_id, listing_id):
    return {"success": True, "channel_id": CHANNEL_ID}


def mock_book_appointment(channel_id, preferred_time, place):
    """Simulates book_appointment() — returns a pending booking."""
    return {
        "success":    True,
        "booking_id": "bk-20260423-001",
        "status":     "PENDING_SELLER",
        "time":       preferred_time,
        "place":      place,
        "channel_id": channel_id,
    }


def mock_seller_accept_booking(booking_id):
    """Simulates seller pressing ✅ 'Chấp nhận' in their app."""
    return {
        "success":    True,
        "booking_id": booking_id,
        "status":     "CONFIRMED",
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }


def mock_log_event(conversation_id, event):
    pass   # In production: writes to DB / observability platform


# ── Conversation state ────────────────────────────────────────

def make_initial_state(conv_id: str) -> dict:
    return {
        "conversation_id": conv_id,
        "lead_stage":      "DISCOVERY",
        "participants": {
            "buyer_id":  MOCK_BUYER["id"],
            "seller_id": MOCK_LISTING["seller_id"],
        },
        "constraints": {},
        "listing_context": None,
        "open_questions": [],
        "risks": [],
        "next_best_action": None,
        "tool_history": [],
        "summary": "",
    }


# ── Pretty printer ────────────────────────────────────────────

ROLE_COLORS = {
    "BUYER":  "\033[94m",   # blue
    "SELLER": "\033[92m",   # green
    "AGENT":  "\033[93m",   # yellow
    "SYSTEM": "\033[90m",   # grey
    "EVENT":  "\033[95m",   # magenta
}
RESET = "\033[0m"
BOLD  = "\033[1m"


def _print_turn(role: str, text: str, extra: str = ""):
    color = ROLE_COLORS.get(role, "")
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = f"{color}{BOLD}[{ts}] {role}{RESET}{color}"
    print(f"\n{prefix}: {text}{RESET}")
    if extra:
        print(f"         {ROLE_COLORS['SYSTEM']}↳ {extra}{RESET}")


def _print_event(label: str, payload: dict):
    color = ROLE_COLORS["EVENT"]
    print(f"\n{color}  ⚡ {BOLD}{label}{RESET}{color}")
    for k, v in payload.items():
        print(f"     {k}: {v}")
    print(RESET, end="")


def _print_divider(title: str = ""):
    line = "─" * 60
    if title:
        pad = (60 - len(title) - 2) // 2
        print(f"\n{'─'*pad} {BOLD}{title}{RESET} {'─'*pad}")
    else:
        print(f"\n{line}")


# ── Main scenario ─────────────────────────────────────────────

def run():
    conv_id = "demo-booking-c1"
    state   = make_initial_state(conv_id)

    preferred_time  = (
        (datetime.now(timezone.utc) + timedelta(days=1))
        .replace(hour=14, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    preferred_place = "Quận 7, TP Hồ Chí Minh"

    print(f"\n{'═'*60}")
    print(f"  {BOLD}🏍  PENTAMO — BOOKING SCENARIO DEMO{RESET}")
    print(f"  Conversation ID : {conv_id}")
    print(f"  Buyer           : {MOCK_BUYER['name']} ({MOCK_BUYER['phone']})")
    print(f"  Target listing  : {MOCK_LISTING['brand']} {MOCK_LISTING['model_line']} "
          f"{MOCK_LISTING['model_year']}  •  {MOCK_LISTING['price']:,} VNĐ")
    print(f"{'═'*60}")

    # ── T0: Buyer gửi yêu cầu ────────────────────────────────
    _print_divider("T0 — BUYER SENDS REQUEST")
    buyers_message = (
        "Chào bạn, mình tìm Honda Air Blade 2021 giá tầm 28-30 triệu ở HCM, "
        "odo thấp, giấy tờ đầy đủ"
    )
    _print_turn("BUYER", buyers_message)

    # Agent extracts intent
    state["constraints"] = {
        "brand":    "Honda",
        "model":    "Air Blade",
        "year_min": 2021,
        "price":    {"min": 28_000_000, "max": 30_000_000},
        "location": "TP Hồ Chí Minh",
        "odo_max":  25_000,
        "paperwork_required": True,
    }
    state["lead_stage"] = "MATCHING"
    mock_log_event(conv_id, {"type": "USER_MESSAGE", "text": buyers_message})
    mock_log_event(conv_id, {"type": "STATE_UPDATE", "lead_stage": "MATCHING"})

    agent_ack = (
        "Dạ để em tìm ngay ạ — Honda Air Blade 2021, dưới 30 triệu, "
        "HCM, odo thấp, đủ giấy tờ."
    )
    _print_turn("AGENT", agent_ack, extra="intent extracted → searching DB")

    time.sleep(0.3)

    # ── T1: Agent tìm kiếm ───────────────────────────────────
    _print_divider("T1 — TOOL: search_listings()")
    search_result = mock_search_listings(
        brands=["Honda Air Blade"],
        price_max=state["constraints"]["price"]["max"],
        province="TP Hồ Chí Minh",
    )
    mock_log_event(conv_id, {
        "type": "TOOL_CALL",
        "tool": "search_listings",
        "params": state["constraints"],
    })
    mock_log_event(conv_id, {
        "type": "TOOL_RESULT",
        "count": search_result["count"],
    })

    _print_event("TOOL_CALL — search_listings()", {
        "brands":    "Honda Air Blade",
        "price_max": f"{state['constraints']['price']['max']:,} VNĐ",
        "province":  "TP Hồ Chí Minh",
    })

    listing = search_result["listings"][0]
    state["listing_context"] = listing

    search_reply = (
        f"Em tìm thấy 1 xe phù hợp:\n\n"
        f"  🏍  {listing['brand']} {listing['model_line']} {listing['model_year']}\n"
        f"  💰  {listing['price']:,} VNĐ\n"
        f"  📍  {listing['province']}\n"
        f"  🔢  Odo: {listing['odo_km']:,} km\n"
        f"  ✅  Giấy tờ: đầy đủ, đã xác minh\n"
        f"  📋  Tình trạng: {listing['condition']}\n\n"
        f"Anh/chị muốn em kết nối với người bán để xem xe không ạ?"
    )
    _print_turn("AGENT", search_reply, extra=f"source=search  listing_id={listing['id']}")

    time.sleep(0.3)

    # ── T2: Buyer quan tâm ───────────────────────────────────
    _print_divider("T2 — BUYER SHOWS INTEREST")
    _print_turn("BUYER", "Xe này nghe ổn đó, cho mình xem xe được không?")
    state["lead_stage"] = "NEGOTIATION"

    # ── T2b: Tạo kênh chat ───────────────────────────────────
    _print_event("TOOL_CALL — create_chat_bridge()", {
        "buyer_id":  MOCK_BUYER["id"],
        "seller_id": listing["seller_id"],
        "listing_id": listing["id"],
    })
    channel_result = mock_create_chat_bridge(
        buyer_id=MOCK_BUYER["id"],
        seller_id=listing["seller_id"],
        listing_id=listing["id"],
    )
    state["tool_history"].append({"tool": "create_chat_bridge", "result": channel_result})

    channel_reply = (
        f"Dạ em đã kết nối anh/chị với người bán (channel: {channel_result['channel_id']}).\n"
        "Anh/chị muốn đặt lịch hẹn xem xe lúc mấy giờ và ở đâu ạ?"
    )
    _print_turn("AGENT", channel_reply, extra=f"channel_id={CHANNEL_ID}")

    time.sleep(0.3)

    # ── T3: Buyer đặt lịch ──────────────────────────────────
    _print_divider("T3 — BUYER BOOKS APPOINTMENT")
    appointment_msg = "Mình muốn hẹn ngày mai 2 giờ chiều tại Quận 7"
    _print_turn("BUYER", appointment_msg)

    # ── T4: Agent tạo booking ────────────────────────────────
    _print_divider("T4 — TOOL: book_appointment()  →  PENDING_SELLER")
    _print_event("TOOL_CALL — book_appointment()", {
        "channel_id": CHANNEL_ID,
        "time":       preferred_time,
        "place":      preferred_place,
    })

    booking = mock_book_appointment(
        channel_id=CHANNEL_ID,
        preferred_time=preferred_time,
        place=preferred_place,
    )
    state["tool_history"].append({"tool": "book_appointment", "result": booking})
    state["lead_stage"] = "APPOINTMENT"
    mock_log_event(conv_id, {"type": "AGENT_ACTION", "action": "book_appointment", **booking})

    _print_event("BOOKING CREATED", {
        "booking_id": booking["booking_id"],
        "status":     booking["status"],
        "time":       booking["time"],
        "place":      booking["place"],
    })

    # Agent → Buyer: xác nhận chờ duyệt
    agent_buyer_confirm = (
        f"✅ Em đã tạo lịch hẹn:\n\n"
        f"  📅  Thời gian : Ngày mai, 14:00\n"
        f"  📍  Địa điểm : {preferred_place}\n"
        f"  🔖  Mã lịch   : {booking['booking_id']}\n\n"
        f"Đang chờ người bán xác nhận — em sẽ báo anh/chị ngay khi có kết quả nhé!"
    )
    _print_turn("AGENT → BUYER", agent_buyer_confirm, extra="status=PENDING_SELLER")

    time.sleep(0.3)

    # ── T5: Seller nhận & chấp nhận ─────────────────────────
    _print_divider("T5 — SELLER RECEIVES & ACCEPTS")

    # Thông báo đến Seller
    seller_notification = (
        f"[PENTAMO] Bạn có lịch hẹn mới!\n"
        f"  Người mua : {MOCK_BUYER['name']} ({MOCK_BUYER['phone']})\n"
        f"  Xe        : {listing['model_line']} {listing['model_year']}\n"
        f"  Thời gian : Ngày mai, 14:00\n"
        f"  Địa điểm : {preferred_place}\n"
        f"  Mã lịch   : {booking['booking_id']}\n\n"
        f"Nhấn ✅ Chấp nhận hoặc ❌ Từ chối."
    )
    _print_turn("SYSTEM → SELLER", seller_notification)

    _print_turn("SELLER", "✅ Mình chấp nhận lịch này, mai 2 giờ ok nha")
    mock_log_event(conv_id, {"type": "USER_MESSAGE", "sender": "seller", "text": "Chấp nhận lịch hẹn"})

    confirm_result = mock_seller_accept_booking(booking["booking_id"])
    state["tool_history"].append({"tool": "seller_accept_booking", "result": confirm_result})
    mock_log_event(conv_id, {
        "type":       "STATE_UPDATE",
        "lead_stage": "CLOSING",
        "booking":    confirm_result,
    })

    _print_event("BOOKING CONFIRMED", {
        "booking_id":    confirm_result["booking_id"],
        "status":        confirm_result["status"],
        "confirmed_at":  confirm_result["confirmed_at"],
    })

    state["lead_stage"] = "CLOSING"

    # ── T6: Agent gửi xác nhận hoàn chỉnh ───────────────────
    _print_divider("T6 — CONFIRMED NOTIFICATIONS SENT")

    # Agent → Buyer: xác nhận hoàn tất
    final_buyer_msg = (
        f"🎉 Lịch hẹn đã được xác nhận!\n\n"
        f"  📅  Thời gian  : Ngày mai, 14:00\n"
        f"  📍  Địa điểm  : {preferred_place}\n"
        f"  📞  Người bán  : {listing['seller_phone']}\n"
        f"  🔖  Mã lịch    : {booking['booking_id']}\n\n"
        f"Anh/chị nhớ mang CMND/CCCD và đặt cọc thiện chí nếu tiện ạ. "
        f"Em sẽ liên hệ sau buổi hẹn để hỗ trợ bước tiếp theo nhé!"
    )
    _print_turn("AGENT → BUYER", final_buyer_msg)

    # Agent → Seller: nhắc lịch
    final_seller_msg = (
        f"✅ Lịch hẹn với {MOCK_BUYER['name']} đã xác nhận.\n"
        f"  📅  Ngày mai, 14:00  |  📍  {preferred_place}\n"
        f"  📞  Người mua : {MOCK_BUYER['phone']}\n"
        f"Vui lòng chuẩn bị đủ giấy tờ gốc (cavet, đăng ký, CMND). "
        f"Liên hệ em nếu cần hỗ trợ thêm nhé!"
    )
    _print_turn("AGENT → SELLER", final_seller_msg)

    # ── Final state dump ──────────────────────────────────────
    state["next_best_action"] = {
        "action": "FOLLOW_UP_POST_VISIT",
        "reason": "Lịch hẹn đã xác nhận. Sau buổi xem: hỏi phản hồi, hỗ trợ đàm phán / ký hợp đồng.",
    }
    state["summary"] = (
        f"Buyer {MOCK_BUYER['name']} quan tâm Honda Air Blade 2021 giá 28.5 triệu. "
        f"Đã đặt lịch xem xe tại {preferred_place}, ngày mai 14:00. "
        f"Seller đã xác nhận. Bước tiếp: follow-up sau buổi xem."
    )

    _print_divider("FINAL STATE")
    print(json.dumps(state, ensure_ascii=False, indent=2, default=str))

    _print_divider("METRICS SNAPSHOT")
    metrics = {
        "lead_stage":             state["lead_stage"],
        "slot_coverage":          "100% (brand, price, location, odo, paperwork, intent)",
        "time_to_first_match":    "~3 turns",
        "appointment_booked":     True,
        "seller_confirmed":       True,
        "risk_flags":             "None",
        "tools_called":           ["search_listings", "create_chat_bridge", "book_appointment"],
        "faiss_cache_hits":       0,          # new conversation, no prior cache
        "hallucination_detected": False,
    }
    for k, v in metrics.items():
        print(f"  {k:<30} : {v}")
    print()


if __name__ == "__main__":
    run()
