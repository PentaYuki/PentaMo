import json
import logging
import os
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from db.models import Conversations, ChatMessages, Users
from backend.orchestrator_v3 import get_orchestrator
from services.memory_service import MemoryService
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_and_evaluate():
    db = SessionLocal()
    orchestrator = get_orchestrator()
    file_path = "data/chat_history.jsonl"
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return

    logger.info("Starting ingestion of chat_history.jsonl...")
    
    # Track current states per conversation
    conv_states = {} # conversation_id -> current_state
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            conv_id = data["conversation_id"]
            
            messages = data.get("messages", [])
            
            # Ensure conversation exists in DB
            conv = db.query(Conversations).filter(Conversations.id == conv_id).first()
            if not conv:
                conv = Conversations(id=conv_id, buyer_id="test_buyer", state={})
                db.add(conv)
                db.commit()
                conv_states[conv_id] = {}
            
            if conv_id not in conv_states:
                conv_states[conv_id] = conv.state or {}

            for msg_data in messages:
                sender = msg_data["sender"]
                text = msg_data["text"]

                # Process message through orchestrator pipeline
                result = orchestrator.process_message(
                    conversation_id=conv_id,
                    user_message=text,
                    current_state=conv_states[conv_id],
                    db=db
                )
                
                # Save Raw Log
                msg = ChatMessages(
                    conversation_id=conv_id,
                    sender_type=sender,
                    text=text
                )
                db.add(msg)
                
                # Update Tier 2 Memory (State)
                new_state = result.get("state", {})
                MemoryService(db).update_structured_state(conv_id, new_state)
                conv_states[conv_id] = new_state
                
                logger.info(f"[{conv_id}] {sender}: {text[:30]}... -> Action: {new_state.get('next_best_action', {}).get('action')}")

    db.commit()
    db.close()
    logger.info("Ingestion completed.")

if __name__ == "__main__":
    import_and_evaluate()
