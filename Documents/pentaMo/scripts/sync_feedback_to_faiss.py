"""
Sync Feedback to FAISS - v3 Self-Learning
Fetches messages with high positive feedback (>= 3) and adds them to FAISS memory.
"""

import sys
import os
from pathlib import Path

# Add root folder to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from db.models import ChatMessages
from services.faiss_memory import get_faiss_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_high_quality_feedback():
    db = SessionLocal()
    memory = get_faiss_memory(index_name="main")
    
    try:
        # Get AI messages with 3+ likes
        # Message must be from agent and have a previous message from user as 'query'
        high_quality_msgs = db.query(ChatMessages).filter(
            ChatMessages.sender_type == "agent",
            ChatMessages.positive_feedback_count >= 3
        ).all()
        
        logger.info(f"Found {len(high_quality_msgs)} high-quality messages for syncing.")
        
        synced_count = 0
        for msg in high_quality_msgs:
            # Find the user message immediately preceding this agent message
            prev_msg = db.query(ChatMessages).filter(
                ChatMessages.conversation_id == msg.conversation_id,
                ChatMessages.id < msg.id,
                ChatMessages.sender_type == "buyer"
            ).order_by(ChatMessages.id.desc()).first()
            
            if prev_msg:
                # Add to FAISS
                # determine mode (default to consultant if unknown)
                mode = "consultant" # Simple assumption or peek at state if needed
                
                # Check if already in memory (optional, add() has some logic)
                memory.add(prev_msg.text, msg.text, mode=mode)
                synced_count += 1
                
        logger.info(f"Successfully synced {synced_count} pairs to FAISS 'main' index.")
        
    except Exception as e:
        logger.error(f"Sync error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    sync_high_quality_feedback()
