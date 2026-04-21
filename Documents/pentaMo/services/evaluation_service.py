"""
Evaluation Service - v3 Lightweight
Tracks AI performance metrics: Cache HIT rate, Feedback scores, Response times.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.models import ChatMessages

logger = logging.getLogger(__name__)

class EvaluationService:
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "llm_calls": 0,
            "safety_blocks": 0,
            "feedback_positive": 0,
            "feedback_negative": 0
        }
    
    def log_event(self, source: str):
        """Log a processing event"""
        self.metrics["total_requests"] += 1
        if source == "faiss":
            self.metrics["cache_hits"] += 1
        elif source == "llm":
            self.metrics["llm_calls"] += 1
        elif source == "safety":
            self.metrics["safety_blocks"] += 1
            
    def get_stats(self, db: Session) -> Dict[str, Any]:
        """Combine live metrics with database feedback stats"""
        # Get feedback counts from DB
        try:
            pos = db.query(ChatMessages).filter(ChatMessages.positive_feedback_count > 0).count()
            neg = db.query(ChatMessages).filter(ChatMessages.negative_feedback_count > 0).count()
        except:
            pos, neg = 0, 0
            
        hit_rate = (self.metrics["cache_hits"] / self.metrics["total_requests"] * 100) if self.metrics["total_requests"] > 0 else 0
        
        return {
            "success": True,
            "metrics": {
                **self.metrics,
                "db_positive_feedbacks": pos,
                "db_negative_feedbacks": neg,
                "cache_hit_rate": f"{hit_rate:.1f}%"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

# Singleton
evaluation_service = EvaluationService()
