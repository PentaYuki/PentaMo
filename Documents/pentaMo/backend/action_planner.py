import logging
import re
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

class ActionPlanner:
    """
    Decides the next best action/tool for the agent to take
    based on the current conversation state and user message.
    """
    
    def __init__(self):
        # Keywords for intent detection
        self.appointment_keywords = ["đặt lịch", "xem xe", "hẹn", "chiều nay", "mai", "thứ", "xem con này", "qua xem"]
        self.chat_keywords = ["liên hệ", "gọi điện", "zalo", "số điện thoại", "inbox", "nhắn chủ xe"]
        self.risk_keywords = ["chuyển tiền", "đặt cọc", "stk", "tài khoản", "bank"]
        self.doc_risk_keywords = ["giấy tờ", "hồ sơ", "chưa sang tên", "cầm cố", "chính chủ", "rút hồ sơ"]
        self.intermediary_keywords = ["trung gian", "môi giới", "bên thứ ba", "trực tiếp", "không cần bên thứ ba", "đứng giữa"]
        self.purchase_keywords = ["chốt", "mua luôn", "lấy con này", "quyết định mua", "cọc", "chốt đơn", "lấy xe này", "thanh toán luôn", "lập hóa đơn", "chốt giá"]
        # NOTE: "mua xe", "mua", "thanh toán", "giao dịch" are INTENTIONALLY excluded.
        # They are too broad and conflict with search intent ("mua xe giá 15 triệu" = search, not purchase).

    def decide_next_action(
        self, 
        user_message: str, 
        state: Dict[str, Any]
    ) -> Tuple[Optional[str], Dict[str, Any], str]:
        """
        Main decision logic.
        Returns: (tool_name, params, reason)
        """
        msg_lower = user_message.lower()
        
        # 0. Purchase / Closing Intent (Priority)
        # GUARD: Only trigger purchase if NO price/search signals are present
        # "mua xe giá 15 triệu" → search intent, NOT purchase intent
        import re
        has_price = bool(re.search(r'\d+\s*(?:triệu|tr)', msg_lower))
        has_search_signal = any(kw in msg_lower for kw in ["tìm", "có không", "có xe nào", "giá bao nhiêu", "tầm"])
        
        if any(kw in msg_lower for kw in self.purchase_keywords) and not has_price and not has_search_signal:
            listing_id = state.get("listing_context", {}).get("id")
            buyer_id = state.get("participants", {}).get("buyer_id")
            if listing_id and buyer_id:
                params = {"listing_id": listing_id, "buyer_id": buyer_id}
                return "create_purchase_order_and_handoff", params, "Khách hàng quyết định chốt đơn mua xe."
        
        # 1. CASE C2: Document Risk Detection
        if any(kw in msg_lower for kw in self.doc_risk_keywords):
            if any(term in msg_lower for term in ["chưa sang tên", "chờ rút hồ sơ", "chờ hồ sơ"]):
                return "detect_risks", {"type": "DOCUMENT_RISK", "level": "HIGH"}, "Phát hiện rủi ro pháp lý về giấy tờ xe (chưa sang tên/đang chờ hồ sơ)."

        # 2. CASE C3: Intermediary Resistance
        if any(kw in msg_lower for kw in self.intermediary_keywords):
            if any(term in msg_lower for term in ["không muốn qua trung gian", "không cần bên thứ ba", "trực tiếp", "số điện thoại người mua"]):
                return "handoff_to_human", {"reason": "SELLER_RESISTANCE"}, "Người bán từ chối làm việc qua bên thứ ba hoặc yêu cầu kết nối trực tiếp."

        # 3. CASE C1: Price Tension / Negotiation
        budget_obj = state.get("budget")
        asking_price = state.get("listing_context", {}).get("price")
        if budget_obj and asking_price:
            # Handle budget if it's a dictionary (from orchestrator_v3)
            budget_val = budget_obj.get("max") if isinstance(budget_obj, dict) else budget_obj
            if budget_val:
                gap = abs(asking_price - budget_val) / asking_price
                if gap > 0.15: # Over 15% gap
                    return "detect_risks", {"type": "PRICE_MISMATCH", "gap": gap}, f"Khoảng cách giá quá lớn ({gap*100:.1f}%). Cần đàm phán hoặc tìm xe khác."

        # 4. Standard Appointment Intent
        if any(kw in msg_lower for kw in self.appointment_keywords):
            listing_id = state.get("listing_context", {}).get("id")
            if listing_id:
                params = {
                    "listing_id": listing_id,
                    "preferred_date": self._extract_date(msg_lower)
                }
                return "book_appointment", params, "Khách hàng muốn xem xe trực tiếp."
        
        # 5. Connect Buyer & Seller
        if any(kw in msg_lower for kw in self.chat_keywords):
            listing_id = state.get("listing_context", {}).get("id")
            seller_id = state.get("listing_context", {}).get("seller_id")
            buyer_id = state.get("participants", {}).get("buyer_id")
            
            if listing_id and seller_id and buyer_id:
                params = {"listing_id": listing_id, "buyer_id": buyer_id, "seller_id": seller_id}
                return "create_chat_channel", params, "Khách hàng muốn kết nối trực tiếp với người bán."

        return None, {}, "Tiếp tục tư vấn thông thường."

    def _extract_date(self, text: str) -> Optional[str]:
        """Simple date extraction logic"""
        from datetime import datetime, timedelta
        if "chiều nay" in text:
            return (datetime.now() + timedelta(hours=4)).isoformat()
        if "mai" in text:
            return (datetime.now() + timedelta(days=1)).isoformat()
        
        date_match = re.search(r'(\d{1,2}/\d{1,2})', text)
        if date_match:
            try:
                day, month = map(int, date_match.group(1).split('/'))
                return datetime(datetime.now().year, month, day).isoformat()
            except: pass
            
        return None
