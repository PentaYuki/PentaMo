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
    COMMON_GUIDELINES = (
        "NGUYÊN TẮC DANH TÍNH: Bạn DUY NHẤT xưng là 'em' và gọi người dùng là 'anh/chị'. "
        "TUYỆT ĐỐI KHÔNG xưng 'chị', 'tôi', 'mình' hay 'tư vấn viên'. "
        "NÓI CHUYỆN TỰ NHIÊN: Tránh dùng từ ngữ máy móc, chuyên ngành khô khan (như 'số đăng ký', 'ngày sản xuất' khi mới bắt đầu tìm xe). "
        "Hãy trả lời như một người bạn am hiểu xe, ngắn gọn, súc tích (dưới 80 từ)."
    )

    CONSULTANT_SYSTEM = (
        f"[VAI TRÒ: AN (EM) | KHÁCH HÀNG: ANH/CHỊ]\n"
        f"Bạn là AN, trợ lý môi giới XE MÁY chuyên nghiệp. {COMMON_GUIDELINES}\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. XƯNG HÔ: Luôn xưng 'em', gọi khách là 'anh/chị'. TUYỆT ĐỐI không gọi khách là 'em'.\n"
        "2. CẤM TỰ XƯNG 'ANH': Bạn là trợ lý, không phải là người bán hay anh trai. Tuyệt đối không dùng từ 'anh' để chỉ bản thân.\n"
        "3. GROUNDING: Chỉ nói về xe có trong hệ thống. Không bịa giá."
    )
    
    TRADER_SYSTEM = (
        f"[VAI TRÒ: AN (EM) | KHÁCH HÀNG: ANH/CHỊ]\n"
        "Bạn là AN, chuyên gia môi giới XE MÁY.\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. XƯNG HÔ: Luôn xưng 'em', gọi 'anh/chị'. Tuyệt đối KHÔNG xưng 'anh' hoặc 'tôi'.\n"
        "2. ĐỐI TƯỢNG: Bạn đang hỗ trợ anh/chị khách hàng mua xe từ người bán.\n"
        "3. Nếu là xe của Admin (admin-seller-id), hãy nói: 'Dạ xe này của hệ thống bên em nên cực kỳ đảm bảo ạ'."
    )
    
    OUT_OF_SCOPE_RESPONSE = (
        "Dạ, chuyên môn của em là về xe máy tại PentaMo thôi ạ. "
        "Mấy vấn đề khác em hơi 'ngáo' chút, anh/chị thông cảm nha. "
        "Có câu hỏi nào về xe cộ cứ nhắn em hỗ trợ liền ạ!"
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
        out_of_scope_keywords = ["nấu ăn", "thời tiết", "chính trị", "đầu tư chứng khoán", "bóng đá"]
        msg_lower = user_message.lower()
        return True

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
        If user message indicates a search, perform real database search
        Returns (formatted_results, count, search_params)
        """
        search_keywords = [
            "tìm", "có cái nào", "có xe nào", "xe gì", "loại xe", "bao nhiêu tiền", "tầm", "dưới", 
            "có không", "bên mình có", "hãng", "chiếc", "con", "mẫu"
        ]
        
        msg_lower = user_message.lower()
        if not any(kw in msg_lower for kw in search_keywords):
            return None, 0, {}
        
        params = parse_user_intent_for_search(user_message)
        # Check if any useful params extracted
        if not any(params.values()):
            return None, 0, {}

        try:
            clean_q = params.get("query_str") or user_message
            q_str = clean_q
            
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
            return {
                "message": self.OUT_OF_SCOPE_RESPONSE,
                "mode": "consultant",
                "source": "safety",
                "state": current_state
            }

        # 2. Update Contextual State
        updated_state = self._update_state(user_message, current_state)
        
        # 3. Proactive Risk Analysis & Metrics (Tier 2/3 Evaluation)
        risk_result = detect_risks(user_message, conversation_id=conversation_id, db=db)
        if risk_result.get("risk_level") in ["high", "critical"]:
            updated_state["risks"] = risk_result
            
        updated_state["slot_coverage"] = self._evaluate_agentic_metrics(updated_state)
        updated_state["turn_count"] = updated_state.get("turn_count", 0) + 1
        
        # 4. Check for Real Search (Early execution to update context)
        search_msg, search_count, search_params = self._perform_search(user_message)
        if search_params and search_count == 1 and "auto_listing_context" in search_params:
            updated_state["listing_context"] = search_params["auto_listing_context"]
            
        if db:
            MemoryService(db).auto_compact_memory(conversation_id)

        # 4. Initialize search state
        search_params = {}
        search_count = 0
        search_context = ""
        
        # 5. Action Planning (Proactive Agent)
        tool_msg = None
        
        # Early Escalation
        if updated_state.get("risks", {}).get("risk_level") == "high":
            escalation = handoff_to_human(conversation_id, f"High risk detected: {updated_state['risks'].get('risks')}")
            updated_state["next_best_action"] = {"action": "HANDOFF", "reason": "High risk detected via detect_risks tool."}
            return {
                "message": escalation.get("message"),
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
                        updated_state["next_best_action"] = {"action": "FOLLOW_UP", "reason": f"Executed tool: {tool_name}"}
                        return {
                            "message": tool_msg,
                            "mode": "trader",
                            "source": "tool",
                            "tool_name": tool_name,
                            "state": updated_state,
                            "decision_reason": decision_reason
                        }

        # 5. Check for Real Search
        search_msg, search_count, search_params = self._perform_search(user_message)
        if search_params and search_count == 0:
            search_context = f"Thông tin tìm kiếm: Đã tra cứu Database PentaMo nhưng KHÔNG TÌM THẤY xe nào khớp với {str(search_params)}."

        if search_msg and search_count > 0:
            evaluation_service.log_event("search")
            return {
                "message": search_msg,
                "mode": "trader",
                "source": "search",
                "state": {**updated_state, "mode": "trader"}
            }

        mode = self._detect_mode(user_message, updated_state)
        updated_state["mode"] = mode
        
        # 5. Search FAISS Cache
        threshold = settings.vector_search_threshold if hasattr(settings, 'vector_search_threshold') else 0.8
        cached_answer = self.memory.search(user_message, mode=mode, threshold=threshold)
        if cached_answer:
            evaluation_service.log_event("faiss")
            return {
                "message": cached_answer,
                "mode": mode,
                "source": "faiss",
                "state": updated_state
            }
        
        # 6. Rate Limiting check before LLM
        user_id = updated_state.get("participants", {}).get("buyer_id", "anonymous")
        allowed, remaining = check_llm_rate_limit(user_id)
        if not allowed:
            evaluation_service.log_event("rate_limit")
            return {
                "message": "Dạ, em hơi bận một xíu. Anh/chị đợi em vài giây rồi nhắn lại nhé!",
                "mode": mode,
                "source": "rate_limit",
                "state": updated_state
            }

        # 7. Call LLM with Context
        system_prompt = self.CONSULTANT_SYSTEM if mode == "consultant" else self.TRADER_SYSTEM
        context_str = self._get_context_str(updated_state)
        
        full_prompt = f"{system_prompt}\n"
        if context_str:
            full_prompt += f"Ngữ cảnh hiện tại: {context_str}\n"
        if search_context:
            full_prompt += f"Kết quả tra cứu hệ thống: {search_context}\n"
        full_prompt += f"\nKhách hàng: {user_message}\nAn:"
        
        evaluation_service.log_event("llm")
        try:
            ai_response = llm_client.generate(
                full_prompt,
                temperature=0.3,
                timeout=settings.llm_timeout if hasattr(settings, 'llm_timeout') else 15
            )
            # Final Persona Check (Robust Swap)
            # Prevent "anh thấy em" (mirroring user)
            resp_lower = ai_response.lower()
            if "anh thấy em" in resp_lower or "anh hiểu em" in resp_lower or "anh đã tìm" in resp_lower:
                # Using unique placeholders to avoid double-swap bug
                ai_response = ai_response.replace("anh", "###T_ANH###").replace("Anh", "###T_ANH_C###")
                ai_response = ai_response.replace("em", "###T_EM###").replace("Em", "###T_EM_C###")
                
                ai_response = ai_response.replace("###T_ANH###", "em").replace("###T_ANH_C###", "Em")
                ai_response = ai_response.replace("###T_EM###", "anh").replace("###T_EM_C###", "Anh")
            
            ai_response = ai_response.replace("tôi", "em").replace("Tôi", "Em")
            ai_response = ai_response.replace("ô tô", "xe máy").replace("Ô tô", "Xe máy")
            
            # Cache the new answer
            self.memory.add(user_message, ai_response, mode)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            ai_response = "Xin lỗi, em đang gặp chút trục trặc. Anh/chị thử lại sau nhé!"
        
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
