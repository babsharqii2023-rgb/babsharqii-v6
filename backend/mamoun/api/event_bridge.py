"""
BABSHARQII v38.0 — Real-time Event Bridge
جسر الأحداث الحي — يربط NeuralBus + Evolution + SelfHealing بالواجهة

الطبقة 3 من آلية التحكم الشاملة:
- يجمع أحداث كل الأنظمة في مكان واحد
- SSE للبث الفوري
- WebSocket للتواصل ثنائي الاتجاه
- يُغذّي SignalRadar + ThoughtStream + مؤشر الاتصال
"""

import asyncio
import time
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

logger = logging.getLogger("mamoun.api.event_bridge")

router = APIRouter(prefix="/v2/events", tags=["event_bridge"])


# مخزن الأحداث الأخيرة
_event_buffer: list[dict] = []
_subscribers: list[asyncio.Queue] = []
MAX_BUFFER = 200


async def _collect_system_events() -> list[dict]:
    """جمع أحداث من كل الأنظمة"""
    events = []

    # 1. NeuralBus إشارات
    try:
        from mamoun.core.neural_bus import neural_bus
        bus_stats = neural_bus.get_stats()
        recent = neural_bus.get_recent_signals(limit=10) if hasattr(neural_bus, 'get_recent_signals') else []
        events.append({
            "source": "neural_bus",
            "type": "signals",
            "data": {
                "total_published": bus_stats.get("total_published", 0),
                "total_subscriptions": bus_stats.get("total_subscriptions", 0),
                "recent_count": len(recent),
                "recent": recent[:5],
            },
            "timestamp": time.time(),
        })
    except Exception as e:
        events.append({"source": "neural_bus", "type": "error", "data": {"error": str(e)[:100]}, "timestamp": time.time()})

    # 2. Inner Monologue (أفكار حقيقية)
    try:
        from mamoun.core.inner_monologue import inner_monologue
        thoughts = inner_monologue.get_recent_thoughts(limit=5) if hasattr(inner_monologue, 'get_recent_thoughts') else []
        events.append({
            "source": "inner_monologue",
            "type": "thoughts",
            "data": {
                "thoughts": thoughts[:5] if thoughts else [],
                "is_running": inner_monologue._running if hasattr(inner_monologue, '_running') else False,
            },
            "timestamp": time.time(),
        })
    except Exception as e:
        events.append({"source": "inner_monologue", "type": "error", "data": {"error": str(e)[:100]}, "timestamp": time.time()})

    # 3. Living State (مؤشرات حيوية)
    try:
        from mamoun.core.living_state import living_state
        vitals = living_state.get_vitals()
        events.append({
            "source": "living_state",
            "type": "vitals",
            "data": vitals,
            "timestamp": time.time(),
        })
    except Exception as e:
        events.append({"source": "living_state", "type": "error", "data": {"error": str(e)[:100]}, "timestamp": time.time()})

    # 4. Self-Healing
    try:
        from mamoun.core.self_healing import self_healing
        report = self_healing.get_report() if hasattr(self_healing, 'get_report') else {}
        events.append({
            "source": "self_healing",
            "type": "status",
            "data": report,
            "timestamp": time.time(),
        })
    except Exception as e:
        events.append({"source": "self_healing", "type": "error", "data": {"error": str(e)[:100]}, "timestamp": time.time()})

    # 5. Evolution
    try:
        from mamoun.api.deps import evolution_loop
        if evolution_loop:
            events.append({
                "source": "evolution",
                "type": "status",
                "data": {"generation": getattr(evolution_loop, '_generation', 0)},
                "timestamp": time.time(),
            })
    except Exception:
        pass

    # 6. Feature Flags
    try:
        from mamoun.api.feature_flags import feature_flag_manager
        flags = feature_flag_manager.get_all()
        active = sum(1 for f in flags.values() if f["enabled"])
        events.append({
            "source": "feature_flags",
            "type": "status",
            "data": {"total": len(flags), "active": active},
            "timestamp": time.time(),
        })
    except Exception:
        pass

    return events


@router.get("/stream")
async def event_stream(request: Request):
    """
    SSE Stream — أحداث فورية مباشرة
    الواجهة تتصل بهذا ويبقى مفتوحاً ويبث أحداث حقيقية
    """
    async def generate() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        _subscribers.append(queue)

        try:
            # إرسال حالة أولية
            initial_events = await _collect_system_events()
            yield f"data: {json.dumps({'type': 'initial', 'events': initial_events}, ensure_ascii=False)}\n\n"

            while True:
                # تحقق من أن الاتصال لا يزال مفتوحاً
                if await request.is_disconnected():
                    break

                # أرسل تحديث كل 3 ثوان
                await asyncio.sleep(3)

                events = await _collect_system_events()
                yield f"data: {json.dumps({'type': 'update', 'events': events}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/snapshot")
async def events_snapshot():
    """
    لقطة فورية — بيانات حية من كل الأنظمة في طلب واحد
    بديل SSE للواجهات التي لا تدعم streaming
    """
    events = await _collect_system_events()

    # إضافة حالة الاتصال
    connection_status = "connected"
    for e in events:
        if e.get("type") == "error":
            connection_status = "degraded"
            break

    return {
        "status": connection_status,
        "timestamp": time.time(),
        "events": events,
        "subscribers": len(_subscribers),
    }


@router.get("/neural-bus/live")
async def neural_bus_live():
    """
    إشارات الناقل العصبي الحية — يُغذّي SignalRadar
    """
    try:
        from mamoun.core.neural_bus import neural_bus
        stats = neural_bus.get_stats()
        signals = neural_bus.get_recent_signals(limit=30) if hasattr(neural_bus, 'get_recent_signals') else []
        signal_types = {}
        for s in signals:
            sig_type = s.get("type", "unknown") if isinstance(s, dict) else "unknown"
            signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

        return {
            "total_signals": stats.get("total_published", 0),
            "signal_types": signal_types,
            "recent": signals[:15],
            "subscriptions": stats.get("total_subscriptions", 0),
            "status": "live",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "total_signals": 0}


@router.get("/monologue/live")
async def monologue_live():
    """
    أفكار داخلية حية — يُغذّي ThoughtStream
    """
    try:
        from mamoun.core.inner_monologue import inner_monologue
        thoughts = inner_monologue.get_recent_thoughts(limit=20) if hasattr(inner_monologue, 'get_recent_thoughts') else []
        is_running = inner_monologue._running if hasattr(inner_monologue, '_running') else False

        return {
            "thoughts": thoughts[:20],
            "is_running": is_running,
            "status": "live" if is_running else "paused",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:200], "thoughts": []}


@router.get("/connection-status")
async def connection_status():
    """
    حالة الاتصال — يُغذّي مؤشر الاتصال في الواجهة
    """
    try:
        from mamoun.core.mamoun_kernel import get_kernel
        kernel = get_kernel()

        checks = {
            "kernel": kernel._running,
            "brains": len(kernel._brains) > 0,
        }

        # فحص LLM
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            checks["llm"] = True
        except:
            checks["llm"] = False

        # فحص NeuralBus
        try:
            from mamoun.core.neural_bus import neural_bus
            checks["neural_bus"] = True
        except:
            checks["neural_bus"] = False

        # فحص Living Systems
        try:
            from mamoun.core.living_state import living_state
            checks["living"] = True
        except:
            checks["living"] = False

        all_ok = all(checks.values())
        some_ok = any(checks.values())

        return {
            "status": "connected" if all_ok else "degraded" if some_ok else "disconnected",
            "checks": checks,
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e)[:200],
            "checks": {},
            "timestamp": time.time(),
        }
