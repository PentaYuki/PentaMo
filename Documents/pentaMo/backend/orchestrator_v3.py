"""
Simplified Agent Orchestrator - v3
Two-mode system: Consultant (An) and Trader
Uses FAISS for caching Q&A pairs, simple LLM prompts per mode
Integrates real search functionality
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from db.models import Conversations, ChatMessages # Import Conversations
from datetime import datetime
from services.llm_client import llm_client
from services.faiss_memory import get_faiss_memory
from config.settings import settings
from backend.security import check_llm_rate_limit, check_tool_rate_limit
from services.evaluation_service import evaluation_service
from backend.action_planner import ActionPlanner
from tools.handlers_v2 import (
    search_listings, parse_user_intent_for_search, book_appointment, 
    create_chat_channel, detect_risks, handoff_to_human, create_purchase_order_and_handoff
)
from services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Main orchestrator for agent conversations
    
    Modes:
    - "consultant": An - vehicle advisor, knowledge-based Q&A
    - "trader": Trading analyst - buying/selling analysis, negotiations
    """
    
    # System prompts for each mode
    # ------------------------------------------------------------------
    # Persona & System Prompts — v3.1 (Precise, decisive, zero fluff)
    # ------------------------------------------------------------------

    _IDENTITY_BLOCK = (
        "Bạn là An, nhân viên tư vấn bán xe máy của PentaMo.\n"
        "Quy tắc xưng hô:\n"
        "- Bạn LUÔN LUÔN xưng là 'em'.\n"
        "- Bạn LUÔN LUÔN gọi khách hàng là 'Anh' hoặc 'Chị'. (Nếu chưa rõ giới tính thì gọi là 'Anh/Chị').\n"
        "- Dù khách hàng tự xưng là 'em', 'mình', hay 'tôi', bạn vẫn phải gọi khách là 'Anh' hoặc 'Chị'.\n\n"
        "Quy tắc tư vấn (Ngắn gọn, Thấu hiểu):\n"
        "- Tối đa 2-3 câu.\n"
        "- Nếu khách tìm xe theo nhu cầu (cho sinh viên, phụ nữ, người mới lái, mua cho con): "
        "HÃY HỎI THĂM 1 câu về vóc dáng hoặc sở thích (xe ga hay xe số) trước khi giới thiệu xe.\n"
        "- KHÔNG tự nghĩ ra tên xe lạ, chỉ dùng xe phổ biến tại Việt Nam (Honda Vision, Air Blade, Wave, Yamaha Exciter...).\n"
    )

    _CONTENT_GUARD = (
        "CẤM: Đề cập đến ô tô (Honda City, Toyota, v.v.) dưới bất kỳ hình thức nào. "
        "Nếu khách hỏi ô tô → nhắc ngay: PentaMo chỉ chuyên xe máy.\n"
    )

    CONSULTANT_SYSTEM = (
        _IDENTITY_BLOCK
        + _CONTENT_GUARD
        + "VAI TRÒ: Tư vấn viên kiến thức — giúp anh/chị hiểu về dòng xe, kỹ thuật, "
        "giấy tờ, bảo dưỡng. Khi chưa đủ thông tin, hỏi đúng 1 câu rõ ràng nhất.\n"
        "SAU KHI BIẾT NHU CẦU: Đề xuất tìm xe ngay — không vòng vo.\n"
    )

    TRADER_SYSTEM = (
        _IDENTITY_BLOCK
        + _CONTENT_GUARD
        + "VAI TRÒ: Môi giới giao dịch — hỗ trợ mua/bán, thương lượng giá, giấy tờ, lịch hẹn.\n"
        + "KHI KHỚP XE: Đề nghị kết nối buyer-seller hoặc đặt lịch ngay — không chờ khách hỏi.\n"
        + "KHI XE CỦA HỆ THỐNG (admin): Nói thẳng: "
        "'Dạ xe này PentaMo đảm bảo 100% giấy tờ. Anh/chị xác nhận chốt là em lập đơn luôn ạ?'\n"
        + "KHI ĐÀM PHÁN: Nêu khoảng cách giá cụ thể, gợi ý mức trung gian hợp lý.\n"
    )

    OUT_OF_SCOPE_RESPONSE = (
        "Dạ, PentaMo em chỉ hỗ trợ về xe máy thôi ạ. "
        "Anh/chị có nhu cầu tìm xe hay cần tư vấn kỹ thuật gì cứ hỏi em nhé!"
    )
    
    def __init__(self):
        self.memory = get_faiss_memory(index_name="main")
        self.mode_classifier = get_faiss_memory(index_name="mode_classifier")
        self.planner = ActionPlanner()
        logger.info("AgentOrchestrator v3.Agentic initialized")
    
    def _detect_mode(self, user_message: str, current_state: Dict[str, Any]) -> str:
        """
        Advanced mode detection using FAISS classifier with rule-based fallback
        """
        # Thử dùng FAISS classifier
        mode_votes = {"consultant": 0, "trader": 0}
        results = self.mode_classifier.search_metadata(user_message, k=5, threshold=0.6)
        
        if results:
            for meta, similarity in results:
                mode_votes[meta["mode"]] += 1
            
            # Đa số rõ ràng
            if max(mode_votes.values()) >= 3:
                detected = max(mode_votes, key=mode_votes.get)
                logger.info(f"Advanced Mode detected: {detected} (Votes: {mode_votes})")
                return detected

        # Fallback về rule-based đơn giản
        msg_lower = user_message.lower()
        trader_keywords = [
            "mua", "bán", "bao nhiêu tiền", "giá", "thương lượng",
            "đặt lịch", "xem xe", "đăng ký", "kiểm định",
            "trả giá", "chênh lệch", "thương", "khuyến mại", "góp", "tài chính"
        ]
        
        if any(kw in msg_lower for kw in trader_keywords):
            return "trader"
            
        return current_state.get("mode", "consultant")
    
    def _update_state(self, user_message: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities (budget, brand, location, odo, paperwork) from message 
        and update the structured state.
        """
        state = current_state.copy()
        msg_lower = user_message.lower()
        
        # 1. Extract budget (Regex)
        budget_patterns = [
            r'(\d+)\s*(?:triệu|tr)',
            r'tầm\s*(\d+)',
            r'dưới\s*(\d+)',
            r'tối đa\s*(\d+)'
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                val = int(match.group(1)) * 1_000_000
                if "budget" not in state: state["budget"] = {}
                state["budget"] = {"min": val - 2000000, "max": val} # Simple range
                break
                
        # 2. Extract brands & models
        common_brands = ["Honda", "Yamaha", "Suzuki", "SYM", "Piaggio", "Vespa", "Vision", "Lead", "SH", "Exciter", "Winner", "Air Blade", "AB"]
        detected_brands = state.get("brands", [])
        for brand in common_brands:
            if brand.lower() in msg_lower and brand not in detected_brands:
                detected_brands.append(brand)
        state["brands"] = detected_brands
        
        # 3. Extract Location
        provinces = ["Hà Nội", "TP Hồ Chí Minh", "HCM", "Đà Nẵng", "Bình Dương", "Cần Thơ"]
        for p in provinces:
            if p.lower() in msg_lower:
                state["location"] = "TP Hồ Chí Minh" if p.upper() == "HCM" else p
                break

        # 4. Extract ODO & Year
        if "odo" in msg_lower:
            match = re.search(r'(\d+)\s*k', msg_lower)
            if match: state["odo_max"] = int(match.group(1)) * 1000
        
        match_year = re.search(r'đời\s*(\d{4})', msg_lower)
        if match_year: state["year_min"] = int(match_year.group(1))

        # 5. Extract Paperwork signals
        if any(kw in msg_lower for kw in ["giấy tờ", "hồ sơ", "sang tên"]):
            state["paperwork_required"] = True
                
        return state

    def _get_open_questions(self, state: Dict[str, Any]) -> List[str]:
        """Identify missing information based on current state"""
        missing = []
        if not state.get("budget"): missing.append("ngân sách của anh/chị")
        if not state.get("brands"): missing.append("hãng xe anh/chị thích")
        if not state.get("location"): missing.append("khu vực xem xe")
        return missing

    def _check_safety(self, user_message: str) -> bool:
        """
        Check if message is out of scope or contains sensitive content
        Returns True if safe, False if out of scope
        """
        out_of_scope_keywords = [
            "nấu ăn", "thời tiết", "chính trị", "đầu tư chứng khoán", "bóng đá",
            "nhà nghỉ", "khách sạn", "du lịch", "đi chơi", "phim", "nhạc",
            "game", "trò chơi", "yêu đương", "tình yêu", "bói", "tử vi",
            "crypto", "bitcoin", "forex", "bất động sản"
        ]
        msg_lower = user_message.lower()
        if any(kw in msg_lower for kw in out_of_scope_keywords):
            return False
        return True
    
    def _is_consultative_intent(self, user_message: str) -> bool:
        """
        Detect if user wants to LEARN or get ADVICE about vehicles (not direct search).
        Consultative questions should go to LLM, not to search.
        """
        msg_lower = user_message.lower()
        consultative_keywords = [
            "học về", "tìm hiểu", "so sánh", "khác nhau", "ưu điểm", "nhược điểm",
            "nên mua", "loại nào tốt", "tay ga là gì", "côn tay là gì",
            "xe tay ga", "xe côn tay", "xe số", "bảo dưỡng", "bảo trì",
            "thay nhớt", "kinh nghiệm", "lưu ý", "hướng dẫn",
            "đăng ký xe", "sang tên", "giấy tờ cần", "thủ tục",
            "tiêu hao nhiên liệu", "tiết kiệm xăng", 
            "tư vấn", "cho con", "sinh viên", "đi làm", "phụ nữ", 
            "người già", "lớn tuổi", "cho nam", "cho nữ", "người mới"
        ]
        return any(kw in msg_lower for kw in consultative_keywords)

    def _evaluate_agentic_metrics(self, state: Dict[str, Any]) -> Dict[str, bool]:
        """Calculate slot coverage for entities"""
        slots = ["budget", "location", "brands", "intent"]
        coverage = {slot: bool(state.get(slot)) for slot in slots}
        return coverage

    def _get_context_str(self, state: Dict[str, Any]) -> str:
        """Create a compact context string for the prompt"""
        ctx = []
        if state.get("budget"):
            b = state["budget"]
            if isinstance(b, dict):
                ctx.append(f"Ngân sách: {b.get('min', 0):,.0f} - {b.get('max', 0):,.0f} VNĐ")
            else:
                ctx.append(f"Ngân sách: {b:,.0f} VNĐ")
        if state.get("location"):
            ctx.append(f"Khu vực: {state['location']}")
        if state.get("brands"):
            ctx.append(f"Hãng quan tâm: {', '.join(state['brands'])}")
            
        return " | ".join(ctx) if ctx else ""

    def _perform_search(self, user_message: str) -> Tuple[Optional[str], int, Dict[str, Any]]:
        """
        If user message indicates a search, perform real database search.
        Returns (formatted_results, count, search_params)
        
        KEY LOGIC: Only search when user has clear search intent.
        Non-search messages (greetings, education, off-topic) should NOT trigger search.
        """
        msg_lower = user_message.lower()
        
        # Skip search if it looks like a definitive action (closing/booking)
        action_keywords = ["chốt", "đặt lịch", "hẹn", "thanh toán", "lập hóa đơn"]
        if any(kw in msg_lower for kw in action_keywords) and len(msg_lower.split()) < 10:
             return None, 0, {}

        # Parse structured params from message
        params = parse_user_intent_for_search(user_message)
        
        # ─── INTENT GATE ──────────────────────────────────────────────────
        # Only proceed with search if user has CLEAR search intent:
        #   a) Message contains search keywords, OR
        #   b) Structured params were extracted (price, brand, province, year)
        # This prevents casual chatter from triggering search + hard return.
        search_keywords = [
            "tìm", "có cái nào", "có xe nào", "xe gì", "loại xe", "bao nhiêu tiền",
            "tầm giá", "dưới", "có không", "bên mình có", "hãng", "chiếc", "mẫu",
            "bán xe", "giá xe", "mua xe", "có những", "giá cả", "ra sao",
            "có gì", "xe nào", "liệt kê"
        ]
        has_search_keywords = any(kw in msg_lower for kw in search_keywords)
        has_structured_params = any([
            params.get("brands"),
            params.get("price_min"),
            params.get("price_max"),
            params.get("year_min"),
            params.get("condition"),
            params.get("province"),   # FIX: Added province to trigger real search
            params.get("query_str"),  # Now only set for model keywords
        ])
        
        # KEY RULE: Search keywords ALONE are not enough.
        # "tôi muốn mua xe" has search keywords but zero structured params
        # → should let LLM ask clarifying questions (budget? brand? location?)
        # Only trigger real search when we have at LEAST one concrete filter.
        has_search_intent = has_structured_params
        
        # Exception: explicit search phrases + province = valid search
        if has_search_keywords and params.get("province"):
            has_search_intent = True
        
        if not has_search_intent:
            # BROWSE MODE: If user has search keywords but no specific params,
            # they want to browse ALL inventory ("có những xe nào", "giá cả ra sao")
            if has_search_keywords:
                # Do a broad search with no filters to show inventory
                params["_has_search_intent"] = True
                params["_browse_mode"] = True
            else:
                # No concrete params, no search keywords — let LLM handle
                return None, 0, {}
        
        # Mark that this was a real search attempt (used by caller for hard return logic)
        params["_has_search_intent"] = True
        
        try:
            # Only pass query_str if it's meaningful (model keyword)
            q_str = params.get("query_str") or None
            
            search_result = search_listings(
                brands=params.get("brands"),
                price_min=params.get("price_min"),
                price_max=params.get("price_max"),
                province=params.get("province"),
                year_min=params.get("year_min"),
                condition=params.get("condition"),
                query_str=q_str,
                limit=5
            )
            
            if not search_result["success"] or search_result["count"] == 0:
                return None, 0, params
            
            listings = search_result["listings"]
            count = search_result["count"]
            formatted = f"Dạ, em tìm thấy {count} xe phù hợp với nhu cầu của anh/chị đây ạ:\n\n"
            
            for i, listing in enumerate(listings, 1):
                formatted += (
                    f"{i}. {listing['brand']} {listing['model_line']} ({listing['model_year']})\n"
                    f"   Giá: {listing['price']:,.0f} VNĐ | {listing['province']}\n"
                )
            
            formatted += "\nAnh/chị có muốn xem chi tiết chiếc nào không ạ?"
            
            # AUTO-CONTEXT: If exactly one result, pin it to state
            if count == 1:
                params["auto_listing_context"] = listings[0]
                
            return formatted, count, params
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None, 0, params

    def _compact_memory(self, conversation_id: str, history: List[Dict[str, Any]]) -> str:
        """Use LLM to summarize long conversation history"""
        if not history:
            return ""
        
        text_to_summarize = "\n".join([f"{m['sender_type']}: {m['text']}" for m in history[-10:]])
        prompt = (
            "Bạn là trợ lý PentaMo. Hãy tóm tắt nội dung chính của cuộc hội thoại sau đây trong vòng 1-2 câu. "
            "Tập trung vào nhu cầu của khách (hãng xe, ngân sách, ý định xem xe).\n\n"
            f"{text_to_summarize}\n\n"
            "Tóm tắt:"
        )
        summary = llm_client.generate(prompt, temperature=0.3)
        logger.info(f"[{conversation_id}] Memory compacted: {summary}")
        return summary

    def _is_cacheable_response(self, question: str, answer: str) -> bool:
        """
        RAG Cache Guard: Returns True ONLY for general knowledge answers
        that are safe to replay without real-time DB data.

        Blocks caching if answer contains:
        - Specific prices (numbers + VNĐ/triệu/tr)
        - Specific listing IDs or vehicle names with model year
        - Appointment/booking confirmations
        - Search result counts
        - Any factual claim that depends on live inventory
        """
        import re
        answer_lower = answer.lower()
        question_lower = question.lower()

        # Block if answer has specific prices (e.g. "14.500.000 VNĐ", "45 triệu")
        if re.search(r'\d[\d.,]*\s*(?:vnđ|vnd|đồng|triệu|tr\.?\b)', answer_lower):
            return False

        # Block if answer has model-year patterns (2019, 2020, 2021, 2022, 2023, 2024)
        if re.search(r'\b20(1[5-9]|2[0-5])\b', answer):
            return False

        # Block if answer mentions odometer / km readings
        if re.search(r'\d+\s*(?:km|k km)', answer_lower):
            return False

        # Block if it's about finding specific results
        if re.search(r'(?:tìm thấy|kết quả|em thấy|có \d+ xe)', answer_lower):
            return False

        # Block booking/appointment confirmations
        booking_signals = ["lịch hẹn", "đặt lịch", "xác nhận", "chốt đơn", "hóa đơn", "appointment"]
        if any(s in answer_lower for s in booking_signals):
            return False

        # Block if question is clearly inventory search
        search_signals = ["tìm", "có xe nào", "bên mình có", "giá bao nhiêu", "tầm", "dưới", "mua xe"]
        if any(s in question_lower for s in search_signals):
            return False

        # Safe to cache: general brand info, maintenance, paperwork, persona Q&A
        return True


    def _apply_pronoun_filter(self, user_message: str, ai_response: str) -> str:
        """Helper to dynamically adjust pronouns based on user message"""
        user_msg_lower = user_message.lower()
        target_pronoun = None
        
        if "anh" in user_msg_lower and "chị" not in user_msg_lower:
            target_pronoun = "anh"
        elif "chị" in user_msg_lower and "anh" not in user_msg_lower:
            target_pronoun = "chị"
            
        if target_pronoun:
            # Case-insensitive replacement for various forms of "anh/chị"
            patterns = ["anh/chị", "Anh/chị", "anh/Chị", "Anh/Chị", "ANH/CHỊ"]
            for p in patterns:
                ai_response = ai_response.replace(p, target_pronoun if p[0].islower() else target_pronoun.capitalize())
        
        return ai_response


    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        current_state: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Main message processing pipeline - v3 Advanced
        """
        logger.info(f"[{conversation_id}] Processing: {user_message[:60]}...")
        
        # 0. Emergency Reset Command
        if user_message.strip().upper() == "[RESET]" and db:
            db.query(ChatMessages).filter(ChatMessages.conversation_id == conversation_id).delete()
            db.commit()
            self.memory.clear_conversation_context(conversation_id)
            return {
                "message": "Em đã dọn dẹp sạch sẽ lịch sử chat cũ rồi ạ! Bây giờ chúng mình bắt đầu lại nha anh.",
                "mode": "consultant",
                "source": "manual_reset",
                "state": {}
            }
        
        # 1. Check Safety / Out of Scope
        if not self._check_safety(user_message):
            logger.info(f"[{conversation_id}] Out of scope detected")
            evaluation_service.log_event("safety")
            msg = self.OUT_OF_SCOPE_RESPONSE
            return {
                "message": self._apply_pronoun_filter(user_message, msg),
                "mode": "consultant",
                "source": "safety",
                "state": current_state
            }

        # 2. Update Contextual State
        updated_state = self._update_state(user_message, current_state)
        
        # 2b. Sync Participants & Listing from DB if available
        if db:
            from tools.handlers_v2 import get_listing_detail # Local import to avoid circular dependency
            conv = db.query(Conversations).filter(Conversations.id == conversation_id).first()
            if conv:
                if "participants" not in updated_state:
                    updated_state["participants"] = {"buyer_id": conv.buyer_id, "seller_id": conv.seller_id}
                
                # IMPORTANT: If listing_id exists in DB but not in context, fetch it
                if conv.listing_id and ("listing_context" not in updated_state or not updated_state["listing_context"]):
                    detail = get_listing_detail(conv.listing_id, db=db)
                    if detail.get("success"):
                        updated_state["listing_context"] = detail["listing"]
                        updated_state["listing_id"] = conv.listing_id
        
        # 3. Proactive Risk Analysis & Metrics (Tier 2/3 Evaluation)
        risk_result = detect_risks(user_message, conversation_id=conversation_id, db=db)
        if risk_result.get("risk_level") in ["high", "critical"]:
            updated_state["risks"] = risk_result
            
        updated_state["slot_coverage"] = self._evaluate_agentic_metrics(updated_state)
        updated_state["turn_count"] = updated_state.get("turn_count", 0) + 1
        
        # 4. Check for Real Search (Early execution to update context)
        # Educational/Consultative intent bypass — if user wants to LEARN or get ADVICE, skip search, go to LLM
        if self._is_consultative_intent(user_message):
            logger.info(f"[{conversation_id}] Consultative intent detected — skipping search")
            search_msg, search_count, search_params = None, 0, {}
        else:
            search_msg, search_count, search_params = self._perform_search(user_message)
        search_context: str = ""

        if search_params and search_count == 1 and "auto_listing_context" in search_params:
            updated_state["listing_context"] = search_params["auto_listing_context"]

        # Hard return when search was INTENTIONALLY attempted but found NOTHING.
        # Only applies when user had clear search intent (price/brand/model query).
        # For casual messages that accidentally matched, let LLM handle.
        if (search_params 
            and search_count == 0 
            and search_params.get("_has_search_intent")
            and not search_params.get("car_detected")):
            logger.info(f"[{conversation_id}] Intentional search returned 0 results — hard return")
            evaluation_service.log_event("search_empty")
            mode = self._detect_mode(user_message, updated_state)
            updated_state["mode"] = mode
            msg = "Dạ em không tìm thấy xe phù hợp trong hệ thống ạ. Anh/chị muốn điều chỉnh tiêu chí (hãng, giá, khu vực) không ạ?"
            return {
                "message": self._apply_pronoun_filter(user_message, msg),
                "mode": mode,
                "source": "search_empty",
                "state": updated_state
            }

        if db:
            MemoryService(db).auto_compact_memory(conversation_id)
        
        # 5. Action Planning (Proactive Agent)
        tool_msg = None
        
        # Early Escalation
        if updated_state.get("risks", {}).get("risk_level") == "high":
            escalation = handoff_to_human(conversation_id, f"High risk detected: {updated_state['risks'].get('risks')}")
            updated_state["next_best_action"] = {"action": "HANDOFF", "reason": "High risk detected via detect_risks tool."}
            return {
                "message": self._apply_pronoun_filter(user_message, escalation.get("message")),
                "mode": "trader",
                "source": "risk_escalation",
                "state": updated_state
            }

        tool_name, tool_params, decision_reason = self.planner.decide_next_action(user_message, updated_state)
        
        if tool_name:
            user_id = updated_state.get("participants", {}).get("buyer_id", "anonymous")
            allowed, _ = check_tool_rate_limit(user_id)
            
            if allowed:
                logger.info(f"[{conversation_id}] Decided Tool: {tool_name} | Reason: {decision_reason}")
                
                # Execute Tool
                tool_result = {}
                if tool_name == "book_appointment":
                    tool_params["conversation_id"] = conversation_id
                    tool_params["db"] = db
                    tool_result = book_appointment(**tool_params)
                    if tool_result.get("success"):
                        updated_state["lead_stage"] = "APPOINTMENT"
                elif tool_name == "create_chat_channel":
                    tool_result = create_chat_channel(**tool_params)
                    if tool_result.get("success"):
                        updated_state["lead_stage"] = "MATCHING"
                elif tool_name == "create_purchase_order_and_handoff":
                    tool_result = create_purchase_order_and_handoff(
                        conversation_id=conversation_id,
                        listing_id=tool_params.get("listing_id"),
                        buyer_id=tool_params.get("buyer_id"),
                        db=db
                    )
                    if tool_result.get("success"):
                        updated_state["purchase_completed"] = True
                        updated_state["transaction_id"] = tool_result.get("transaction_id")
                        updated_state["handoff_active"] = True
                        mode = "trader"
                
                if tool_result.get("success"):
                    tool_msg = tool_result.get("message")
                    evaluation_service.log_event(f"tool_{tool_name}")
                    # If we found a critical action, we can skip
                    if tool_name in ["book_appointment", "create_chat_channel", "create_purchase_order_and_handoff"]:
                        # BUG FIX: Add ui_commands to let frontend switch pages/modals
                        ui_commands = []
                        if tool_name == "book_appointment":
                            ui_commands.append({"action": "SWITCH_SECTION", "params": {"section": "appointments"}})
                        elif tool_name == "create_chat_channel":
                            ui_commands.append({"action": "SWITCH_SECTION", "params": {"section": "chat-list"}})
                        elif tool_name == "create_purchase_order_and_handoff":
                            ui_commands.append({"action": "SWITCH_SECTION", "params": {"section": "chat-list"}}) # View in message list
                            ui_commands.append({"action": "OPEN_RECEIPT", "params": {"tx_id": updated_state.get("transaction_id")}})

                        return {
                            "message": self._apply_pronoun_filter(user_message, tool_msg),
                            "mode": "trader",
                            "source": "tool",
                            "tool_name": tool_name,
                            "state": updated_state,
                            "decision_reason": decision_reason,
                            "ui_commands": ui_commands
                        }

        # 5. Return search results if found (results from the single search call in step 4)
        # BUG FIX #4: no second call to _perform_search — reuse search_msg/count/params from above
        if search_msg and search_count > 0:
            evaluation_service.log_event("search")
            # NOTE: Do NOT cache raw search snippets into FAISS —
            # structured listing data is too specific to reuse semantically.
            return {
                "message": self._apply_pronoun_filter(user_message, search_msg),
                "mode": "trader",
                "source": "search",
                "state": {**updated_state, "mode": "trader"},
                "ui_commands": [{
                    "action": "AUTO_SEARCH",
                    "params": search_params
                }]
            }

        # If car_detected, set context warning (only case left where we proceed to LLM)
        if search_params and search_params.get("car_detected"):
            search_context = "HỆ THỐNG CẢNH BÁO: Khách hàng đang hỏi về Ô TÔ. PentaMo KHÔNG bán ô tô. Hãy nhắc nhở khách hàng bạn chỉ chuyên về XE MÁY và không được giới thiệu bất kỳ mẫu ô tô nào."

        mode = self._detect_mode(user_message, updated_state)
        updated_state["mode"] = mode

        # ── FAISS Semantic Cache ──────────────────────────────────────────────
        # RAG rule: ONLY use cache when search was NOT triggered.
        # If search_params is populated, the user is asking about real inventory
        # data → never serve a cached generic answer (hallucination risk).
        faiss_applicable = not bool(search_params)  # skip cache if search ran
        cached_answer = None

        if faiss_applicable:
            threshold = getattr(settings, 'vector_search_threshold', 0.82)
            cached_answer = self.memory.search(
                user_message,
                mode=mode,
                threshold=threshold,
                conv_id=conversation_id,
            )
            if cached_answer:
                evaluation_service.log_event("faiss")
                return {
                    "message": self._apply_pronoun_filter(user_message, cached_answer),
                    "mode": mode,
                    "source": "faiss",
                    "state": updated_state
                }
        
        # 6. Rate Limiting check before LLM
        user_id = updated_state.get("participants", {}).get("buyer_id", "anonymous")
        allowed, remaining = check_llm_rate_limit(user_id)
        if not allowed:
            evaluation_service.log_event("rate_limit")
            msg = "Dạ, em hơi bận một xíu. Anh/chị đợi em vài giây rồi nhắn lại nhé!"
            return {
                "message": self._apply_pronoun_filter(user_message, msg),
                "mode": mode,
                "source": "rate_limit",
                "state": updated_state
            }

        # 7. Call LLM with Context
        system_prompt = self.CONSULTANT_SYSTEM if mode == "consultant" else self.TRADER_SYSTEM
        context_str = self._get_context_str(updated_state)
        
        # Marketplace Persona Adjustment
        seller_id = updated_state.get("participants", {}).get("seller_id")
        is_admin_stock = (seller_id == "admin-seller-id")
        
        if is_admin_stock:
            system_prompt += "\nLƯU Ý: Xe này là hàng chính chủ của PentaMo (Admin). Hãy khẳng định uy tín và độ an toàn pháp lý 100%."
        else:
            system_prompt += "\nLƯU Ý: Xe này thuộc sở hữu của một người bán cá nhân trên sàn. Hãy đóng vai trò trung gian hỗ trợ kết nối và kiểm tra thông tin giúp khách."

        full_prompt = f"{system_prompt}\n"
        if context_str:
            full_prompt += f"Ngữ cảnh hiện tại: {context_str}\n"
        if search_context:
            full_prompt += f"Kết quả tra cứu hệ thống: {search_context}\n"
            
        # Xác định xưng hô mong muốn dựa vào tin nhắn khách
        target_pronoun = "Anh/Chị"
        user_msg_lower = user_message.lower()
        if "anh " in user_msg_lower or "anh" == user_msg_lower.strip():
            target_pronoun = "Anh"
        elif "chị " in user_msg_lower or "chị" == user_msg_lower.strip():
            target_pronoun = "Chị"
            
        full_prompt += f"\n[LỆNH ÉP BUỘC]: Bạn BẮT BUỘC phải xưng là 'em' và GỌI KHÁCH HÀNG LÀ '{target_pronoun}'. TUYỆT ĐỐI KHÔNG gọi khách là 'em' hay 'bạn'.\n"
        
        # Kỹ thuật mồi câu (Prefill) để ép AI đi đúng hướng xưng hô
        prefix = f"Dạ chào {target_pronoun}, "
        full_prompt += f"Khách hàng: {user_message}\nAn: {prefix}"
        
        evaluation_service.log_event("llm")
        try:
            ai_response = llm_client.generate(
                full_prompt,
                temperature=0.3,
                timeout=settings.llm_timeout if hasattr(settings, 'llm_timeout') else 15
            )
            # Gắn lại prefix vì LLM thường viết tiếp từ đoạn đó
            ai_response = prefix + ai_response
            # Final Persona Check (Robust Swap)
            # Ensure "em" and "anh/chị" are correctly used
            ai_response = ai_response.replace("Ô tô", "Xe máy").replace("ô tô", "xe máy")
            ai_response = ai_response.replace("Chúng tôi", "Em").replace("chúng tôi", "em")
            
            # Avoid mirror hallucination where AI calls itself "anh" because user did
            if "anh là an" in ai_response.lower() or "tôi là an" in ai_response.lower():
                 ai_response = ai_response.replace("anh là An", "em là An").replace("Anh là An", "Em là An")

            # Apply final pronoun filter
            ai_response = self._apply_pronoun_filter(user_message, ai_response)

            # ── Dynamic Pronoun Adjustment ────────────────────────────────────
            # If the user explicitly called themselves "Anh" or "Chị" in the current message,
            # we force the AI response to use that specific pronoun instead of "Anh/Chị".
            user_msg_lower = user_message.lower()
            if "anh" in user_msg_lower and "chị" not in user_msg_lower:
                ai_response = ai_response.replace("anh/chị", "anh").replace("Anh/Chị", "Anh")
            elif "chị" in user_msg_lower and "anh" not in user_msg_lower:
                ai_response = ai_response.replace("anh/chị", "chị").replace("Anh/Chị", "Chị")

            # ── RAG-Compliant Cache Guard ─────────────────────────────────────
            # Only cache GENERAL knowledge answers (persona, paperwork, brand Q&A).
            # NEVER cache answers that contain specific prices, vehicle names, or
            # figures — those are data-specific and will hallucinate if replayed.
            if faiss_applicable and self._is_cacheable_response(user_message, ai_response):
                self.memory.add(user_message, ai_response, mode, conv_id=conversation_id)
                logger.debug(f"[{conversation_id}] Cached general knowledge answer.")
            else:
                logger.debug(f"[{conversation_id}] Cache SKIPPED — data-specific or search-triggered response.")
        except Exception as e:
            logger.error(f"LLM error: {e}")
            ai_response = self._apply_pronoun_filter(user_message, "Xin lỗi, em đang gặp chút trục trặc. Anh/chị thử lại sau nhé!")
        
        # 9. Final State Update (Schema Aligned)
        updated_state["open_questions"] = self._get_open_questions(updated_state)
        updated_state["summary"] = MemoryService(db).get_rolling_summary(conversation_id) if db else ""
        
        if tool_name:
            updated_state["next_best_action"] = {"action": tool_name, "reason": decision_reason}
        else:
            updated_state["next_best_action"] = {"action": "CONTINUE_ADVICE", "reason": "Tiếp tục tìm hiểu nhu cầu khách hàng."}

        return {
            "message": tool_msg if tool_msg else ai_response,
            "mode": mode,
            "source": "tool" if tool_msg else ("faiss" if cached_answer else "llm"),
            "tool_name": tool_name if tool_name else None,
            "state": updated_state,
            "decision_reason": decision_reason if tool_name else None
        }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics including learning history"""
        stats = self.memory.get_stats()
        mc_stats = self.mode_classifier.get_stats()
        return {
            "total_cached_pairs": stats["total_pairs"],
            "mode_classifier_samples": mc_stats["total_pairs"],
            "consultant_pairs": stats["consultant_count"],
            "trader_pairs": stats["trader_count"],
            "last_updated": stats.get("last_updated"),
            "recent_learning": stats.get("recent_learning", [])
        }


# Singleton instance
_orchestrator = None

def get_orchestrator() -> AgentOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


# For backward compatibility
orchestrator = AgentOrchestrator()
