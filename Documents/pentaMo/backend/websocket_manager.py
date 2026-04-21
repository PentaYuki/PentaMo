"""
WebSocket Manager - Manages real-time connections to clients
Broadcasts events like search_completed, booking_confirmed, etc.
"""

import json
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Quản lý kết nối WebSocket cho các conversation"""
    
    def __init__(self):
        # Structure: {conversation_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.connection_counter = 0
    
    async def connect(self, conversation_id: str, websocket: WebSocket) -> str:
        """
        Kết nối một WebSocket mới.
        Trả về connection_id.
        """
        await websocket.accept()
        
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = {}
        
        connection_id = f"conn_{self.connection_counter}"
        self.connection_counter += 1
        
        self.active_connections[conversation_id][connection_id] = websocket
        logger.info(f"WebSocket connected: {conversation_id}/{connection_id}")
        
        return connection_id
    
    async def disconnect(self, conversation_id: str, connection_id: str):
        """Ngắt kết nối một WebSocket"""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].pop(connection_id, None)
            
            # Xóa conversation nếu không còn connection nào
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
            
            logger.info(f"WebSocket disconnected: {conversation_id}/{connection_id}")
    
    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ):
        """
        Gửi sự kiện đến tất cả WebSocket connections của một conversation.
        """
        if conversation_id not in self.active_connections:
            return
        
        connections = self.active_connections[conversation_id]
        if not connections:
            return
        
        message = {
            "type": "event",
            "event": event_type,
            "payload": payload,
        }
        
        disconnected = []
        for connection_id, websocket in connections.items():
            try:
                await websocket.send_json(message)
                logger.debug(f"Event sent to {conversation_id}/{connection_id}: {event_type}")
            except Exception as e:
                logger.error(f"Error sending to {conversation_id}/{connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Cleanup disconnected
        for conn_id in disconnected:
            await self.disconnect(conversation_id, conn_id)
    
    async def broadcast_search_completed(
        self,
        conversation_id: str,
        listings: list,
        count: int,
    ):
        """Broadcast khi tìm kiếm xe hoàn tất"""
        payload = {
            "count": count,
            "listings": listings,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_conversation(
            conversation_id,
            "search_completed",
            payload,
        )
    
    async def broadcast_booking_status(
        self,
        conversation_id: str,
        status: str,  # "pending", "confirmed", "failed"
        appointment_data: Dict[str, Any] = None,
    ):
        """Broadcast khi trạng thái booking thay đổi"""
        payload = {
            "status": status,
            "appointment": appointment_data or {},
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_conversation(
            conversation_id,
            "booking_status",
            payload,
        )
    
    async def broadcast_ocr_processing(
        self,
        conversation_id: str,
        status: str,  # "processing", "completed", "failed"
        result: Dict[str, Any] = None,
    ):
        """Broadcast khi OCR ảnh xe đang xử lý"""
        payload = {
            "status": status,
            "result": result or {},
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_conversation(
            conversation_id,
            "ocr_status",
            payload,
        )
    
    async def broadcast_typing_indicator(
        self,
        conversation_id: str,
        is_typing: bool,
    ):
        """Broadcast khi AI đang "gõ" (ẩn chỉ báo)"""
        payload = {
            "is_typing": is_typing,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_conversation(
            conversation_id,
            "typing_indicator",
            payload,
        )
    
    def get_active_conversations(self) -> list:
        """Lấy danh sách conversation hiện có active connections"""
        return list(self.active_connections.keys())
    
    def get_connection_count(self, conversation_id: str) -> int:
        """Lấy số lượng connections của một conversation"""
        return len(self.active_connections.get(conversation_id, {}))


# Global singleton instance
_manager_instance = None


def get_manager() -> WebSocketManager:
    """Lấy WebSocketManager singleton"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WebSocketManager()
    return _manager_instance


# Export
__all__ = ["WebSocketManager", "get_manager"]
