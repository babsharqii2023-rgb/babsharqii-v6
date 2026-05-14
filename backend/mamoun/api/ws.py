"""
BABSHARQII v17.0 — WebSocket Endpoint
تواصل فعلي في الوقت الحقيقي — مأمون يتحدث معك مباشرة

WebSocket provides real-time:
- Brain status updates (which brain is thinking, confidence levels)
- Deliberation results (live voting, conflict detection)
- Mirror reflections (self-awareness insights)
- Kernel heartbeat (system health, evolution cycles)
"""

import asyncio
import json
import time
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("mamoun.api.ws")

router = APIRouter()


class ConnectionManager:
    """مدير اتصالات WebSocket — يربط كل العملاء"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._broadcast_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self.active_connections))

    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """بث رسالة لكل العملاء المتصلين"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        self.active_connections -= disconnected

    async def start_heartbeat_broadcast(self, interval: float = 5.0):
        """
        بث دوري — يرسل حالة الأدمغة والنواة كل 5 ثوانٍ
        
        This makes the frontend dashboard come alive with real-time data.
        """
        while True:
            try:
                await asyncio.sleep(interval)
                
                if not self.active_connections:
                    continue
                
                # Collect system status
                status = await self._collect_status()
                await self.broadcast({
                    "type": "heartbeat",
                    "timestamp": time.time(),
                    "data": status,
                })
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat broadcast error: %s", e)

    async def _collect_status(self) -> dict:
        """جمع حالة النظام الكاملة"""
        try:
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            
            # Brain states
            brains = {}
            for brain_id, brain in kernel._brains.items():
                brains[brain_id] = brain.state.to_dict()
            
            # Workspace
            workspace = kernel.workspace.get_status()
            
            # LLM stats
            llm_stats = kernel.llm.get_stats()
            
            # Deliberation room
            deliberation_stats = {}
            if hasattr(kernel, '_deliberation_room') and kernel._deliberation_room:
                deliberation_stats = {
                    "history_size": len(kernel._deliberation_room._history),
                }
            
            # Router stats
            router_stats = {}
            if hasattr(kernel, '_brain_router') and kernel._brain_router:
                router_stats = kernel._brain_router.get_stats()
            
            return {
                "kernel_running": kernel._running,
                "cycle_count": kernel._cycle_count,
                "version": "v17.0",
                "brains": brains,
                "workspace": workspace,
                "llm_stats": llm_stats,
                "deliberation": deliberation_stats,
                "router": router_stats,
            }
        except Exception as e:
            return {"error": str(e), "version": "v17.0"}


# Singleton
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    نقطة نهاية WebSocket الرئيسية
    
    يرسل الخادم:
    - heartbeat: كل 5 ثوانٍ (حالة الأدمغة + النواة)
    - deliberation: نتيجة مداولة فعلية
    - reflection: تأمل ذاتي جديد
    - evolution: نتيجة دورة تطور
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                if msg_type == "ping":
                    await manager.send_personal({
                        "type": "pong",
                        "timestamp": time.time(),
                    }, websocket)
                
                elif msg_type == "chat":
                    # Process chat message through the kernel
                    from mamoun.core.mamoun_kernel import get_kernel
                    kernel = get_kernel()
                    
                    user_message = message.get("message", "")
                    if user_message.strip():
                        result = await kernel.chat(
                            message=user_message,
                            context=message.get("context", {}),
                        )
                        
                        # Get deliberation data
                        deliberation = getattr(kernel, '_last_deliberation', None)
                        
                        response = {
                            "type": "chat_response",
                            "timestamp": time.time(),
                            "data": {
                                "response": result.get("response", ""),
                                "confidence": result.get("confidence", 0),
                                "winning_brain": result.get("winning_brain", ""),
                                "escalation": result.get("escalation", ""),
                                "brain_responses": {
                                    bid: {
                                        "response": resp.get("response", "")[:300],
                                        "confidence": resp.get("confidence", 0),
                                        "stance": resp.get("stance", "neutral"),
                                        "model_used": resp.get("model_used", ""),
                                    }
                                    for bid, resp in (deliberation.brain_responses if deliberation else {}).items()
                                } if deliberation else {},
                                "consensus_level": deliberation.consensus_level if deliberation else 0,
                                "cjs": deliberation.critical_junction_score if deliberation else 0,
                                "conflict_detected": deliberation.conflict_detected if deliberation else False,
                                "mirror_reflection": deliberation.mirror_reflection[:500] if deliberation and deliberation.mirror_reflection else "",
                            },
                        }
                        
                        await manager.send_personal(response, websocket)
                        
                        # Also broadcast brain activity to all clients
                        await manager.broadcast({
                            "type": "brain_activity",
                            "timestamp": time.time(),
                            "data": {
                                "event": "chat_processed",
                                "winning_brain": result.get("winning_brain", ""),
                                "confidence": result.get("confidence", 0),
                            },
                        })
                
                elif msg_type == "subscribe":
                    # Client subscribes to specific event types
                    await manager.send_personal({
                        "type": "subscribed",
                        "events": message.get("events", ["heartbeat", "brain_activity"]),
                        "timestamp": time.time(),
                    }, websocket)
                
            except json.JSONDecodeError:
                await manager.send_personal({
                    "type": "error",
                    "message": "رسالة غير صالحة — يجب أن تكون JSON",
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
