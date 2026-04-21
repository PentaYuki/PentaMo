import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Conversations, ChatMessages
from services.llm_client import llm_client

logger = logging.getLogger(__name__)

class MemoryService:
    """
    3-Tier Memory Management System
    Tier 1: Raw logs (Audit)
    Tier 2: Structured state (Working memory)
    Tier 3: Rolling summary (Long-term context)
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_full_context(self, conversation_id: str, limit: int = 20) -> Dict[str, Any]:
        """Combine all tiers into a single context for the orchestrator"""
        conv = self.db.query(Conversations).filter(Conversations.id == conversation_id).first()
        if not conv:
            return {"state": {}, "summary": "", "history": []}

        # Tier 1: Raw logs (Recent history)
        history = self.db.query(ChatMessages).filter(
            ChatMessages.conversation_id == conversation_id
        ).order_by(ChatMessages.timestamp.desc()).limit(limit).all()
        
        # Reverse to get chronological order
        history_list = [
            {"sender": m.sender_type, "text": m.text, "time": m.timestamp.isoformat()}
            for m in reversed(history)
        ]

        return {
            "state": conv.state or {},
            "summary": conv.memory_summary or "",
            "history": history_list,
            "lead_stage": conv.lead_stage
        }

    def update_structured_state(self, conversation_id: str, new_state: Dict[str, Any]):
        """Update Tier 2 memory (Structured state)"""
        conv = self.db.query(Conversations).filter(Conversations.id == conversation_id).first()
        if conv:
            # Merge state
            current_state = conv.state or {}
            current_state.update(new_state)
            conv.state = current_state
            
            # Sync lead_stage if present
            if "lead_stage" in new_state:
                conv.lead_stage = new_state["lead_stage"]
                
            self.db.commit()
            logger.debug(f"[{conversation_id}] Tier 2 Memory updated.")

    def auto_compact_memory(self, conversation_id: str, history_threshold: int = 15):
        """Check if Tier 3 (Summary) needs update based on turn count"""
        conv = self.db.query(Conversations).filter(Conversations.id == conversation_id).first()
        if not conv: return

        # Count turns
        turn_count = self.db.query(ChatMessages).filter(
            ChatMessages.conversation_id == conversation_id
        ).count()

        if turn_count > 0 and turn_count % history_threshold == 0:
            logger.info(f"[{conversation_id}] Triggering Tier 3 Memory compaction...")
            self.generate_rolling_summary(conversation_id)

    def get_rolling_summary(self, conversation_id: str) -> str:
        """Retrieve current memory summary for the conversation"""
        conv = self.db.query(Conversations).filter(Conversations.id == conversation_id).first()
        return conv.memory_summary if conv and conv.memory_summary else ""

    def generate_rolling_summary(self, conversation_id: str) -> str:
        """Use LLM to update Tier 3 Memory (Rolling Summary)"""
        conv = self.db.query(Conversations).filter(Conversations.id == conversation_id).first()
        history = self.db.query(ChatMessages).filter(
            ChatMessages.conversation_id == conversation_id
        ).order_by(ChatMessages.timestamp.asc()).all()

        text_to_summarize = "\n".join([f"{m.sender_type}: {m.text}" for m in history])
        
        current_summary = conv.memory_summary or "Chưa có tóm tắt."
        
        prompt = f"""
Bạn là chuyên gia quản lý dữ liệu tại PentaMo. 
Hãy cập nhật tóm tắt cuộc hội thoại dưới đây. 

Tóm tắt hiện tại: {current_summary}

Nội dung mới:
{text_to_summarize}

Yêu cầu tóm tắt mới:
1. Ngắn gọn (dưới 100 từ).
2. Lưu lại các thực thể quan trọng: Loại xe khách tìm, Ngân sách, Địa điểm, Rủi ro đã phát hiện.
3. Giữ lại trạng thái chốt đơn hiện tại.

Tóm tắt mới:"""

        try:
            new_summary = llm_client.generate(prompt, temperature=0.3)
            conv.memory_summary = new_summary
            self.db.commit()
            logger.info(f"[{conversation_id}] Tier 3 Memory updated: {new_summary[:50]}...")
            return new_summary
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return current_summary
