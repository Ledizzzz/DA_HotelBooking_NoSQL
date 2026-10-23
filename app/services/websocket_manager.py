"""
Dịch vụ Quản lý Kết nối WebSocket Thời Gian Thực (Real-time WebSocket Manager)
Phát sóng (Broadcast) sự kiện thay đổi trạng thái phòng và đơn đặt phòng mới tức thời.
"""

import json
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Gửi thông điệp chào mừng khi kết nối thành công
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "WebSocket đã sẵn sàng — Cập nhật phòng và đơn đặt phòng thời gian thực"
        }))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        """Phát sóng sự kiện tới tất cả các trình duyệt đang mở"""
        message_str = json.dumps(data, ensure_ascii=False)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception:
                disconnected.append(connection)
        for dead_conn in disconnected:
            self.disconnect(dead_conn)

ws_manager = ConnectionManager()
