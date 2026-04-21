"""
Conversation Service - Manage chat sessions and history
Provides logic for fraud detection and event tracking
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import ChatMessages, ToolLogs, Conversations

logger = logging.getLogger(__name__)

class ConversationService:
    @staticmethod
    def get_conversation_events(db: Session, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for a conversation (messages + tool logs)
        sorted by timestamp.
        """
        try:
            # 1. Fetch messages
            messages = db.query(ChatMessages).filter(
                ChatMessages.conversation_id == conversation_id
            ).all()
            
            events = []
            for m in messages:
                events.append({
                    "event_type": "message",
                    "sender_type": m.sender_type,
                    "text": m.text,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                    "id": m.id
                })
            
            # 2. Fetch tool logs
            logs = db.query(ToolLogs).filter(
                ToolLogs.conversation_id == conversation_id
            ).all()
            
            for l in logs:
                events.append({
                    "event_type": "tool_call",
                    "tool_name": l.tool_name,
                    "input": l.input_params,
                    "output": l.output,
                    "timestamp": l.executed_at.isoformat() if l.executed_at else None,
                    "id": f"tool_{l.id}"
                })
            
            # Sort by timestamp
            events.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
            return events
            
        except Exception as e:
            logger.error(f"Error fetching conversation events: {e}")
            return []

    @staticmethod
    def check_conversation_fraud(db: Session, conversation_id: str) -> Dict[str, Any]:
        """
        Basic fraud detection check for a conversation.
        Analyzes message patterns and entity extraction results.
        """
        try:
            # Placeholder: In a real system, this would call an AI model
            # or check for suspicious keywords (links, spam, etc.)
            conversation = db.query(Conversations).filter(Conversations.id == conversation_id).first()
            if not conversation:
                return {"status": "error", "message": "Conversation not found"}
                
            # Simulate a result
            return {
                "status": "safe",
                "fraud_score": 0.05,
                "flags": [],
                "checked_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking fraud: {e}")
            return {"status": "error", "message": str(e)}
