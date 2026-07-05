"""
WebSocket Server for Guardian API — Real-time mission updates and streaming results.
Clients subscribe to mission updates, receive status changes as they occur.
"""

import json
import asyncio
from typing import Set, Dict, Callable
from fastapi import WebSocket, WebSocketDisconnect
from shadowcypher.core.logger import logger
from shadowcypher.core.mission_executor import get_mission_executor


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, mission_id: str, websocket: WebSocket):
        """Register a new WebSocket connection for a mission."""
        await websocket.accept()

        if mission_id not in self.active_connections:
            self.active_connections[mission_id] = set()

        self.active_connections[mission_id].add(websocket)
        logger.info("websocket", f"Client connected to mission {mission_id}")

    async def disconnect(self, mission_id: str, websocket: WebSocket):
        """Unregister a WebSocket connection."""
        if mission_id in self.active_connections:
            self.active_connections[mission_id].discard(websocket)
            if not self.active_connections[mission_id]:
                del self.active_connections[mission_id]

        logger.info("websocket", f"Client disconnected from mission {mission_id}")

    async def broadcast_mission_update(self, mission_id: str, data: Dict):
        """Send mission update to all connected clients."""
        if mission_id not in self.active_connections:
            return

        message = json.dumps({
            "type": "mission_update",
            "mission_id": mission_id,
            "data": data,
        })

        disconnected = set()
        for websocket in self.active_connections[mission_id]:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.debug("websocket", f"Failed to send to client: {e}")
                disconnected.add(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            await self.disconnect(mission_id, websocket)

    async def send_personal_message(self, websocket: WebSocket, message: str):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.debug("websocket", f"Failed to send personal message: {e}")


# Global manager instance
_ws_manager = None


def get_ws_manager() -> WebSocketManager:
    """Get or create WebSocket manager singleton."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


async def subscribe_to_mission(mission_id: str, websocket: WebSocket):
    """Handle WebSocket subscription to a mission."""
    manager = get_ws_manager()
    await manager.connect(mission_id, websocket)

    try:
        # Send current mission status
        executor = get_mission_executor()
        mission = executor.get_mission(mission_id)

        if mission:
            from dataclasses import asdict
            await manager.send_personal_message(
                websocket,
                json.dumps({
                    "type": "initial_state",
                    "mission": asdict(mission),
                })
            )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle ping/pong for keep-alive
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    websocket,
                    json.dumps({"type": "pong"})
                )

            # Handle explicit status queries
            elif message.get("type") == "get_status":
                mission = executor.get_mission(mission_id)
                if mission:
                    from dataclasses import asdict
                    await manager.send_personal_message(
                        websocket,
                        json.dumps({
                            "type": "mission_status",
                            "mission": asdict(mission),
                        })
                    )

    except WebSocketDisconnect:
        await manager.disconnect(mission_id, websocket)
    except Exception as e:
        logger.error("websocket", f"WebSocket error: {e}")
        await manager.disconnect(mission_id, websocket)
