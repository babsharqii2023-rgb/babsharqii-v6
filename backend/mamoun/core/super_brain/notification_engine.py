"""
NotificationEngine v61 — محرك التنبيهات عبر NeuralBus

CRITICAL ADDITION from v61 Stage 4:
- _ws_push(notification): WebSocket push for real-time client updates
- get_api_notifications(): Structured data for API endpoints
- broadcast_emergency(title, message, metadata): Send to ALL channels at once
- Proactive alert integration with HealthMonitor

Previous upgrades preserved:
- v59: لا توجد تنبيهات تلقائية عند الأحداث الحرجة
- v59.2: NotificationEngine يراقب NeuralBus ويرسل تنبيهات تلقائية
- يدعم: WEBHOOK, IN_APP, EMAIL, TELEGRAM, DISCORD
- تنبيهات عند: HEALTH_CRITICAL, META_STAGNATION, EMERGENCY
- Rate limiting: لا يرسل أكثر من 10 تنبيهات في الدقيقة

Inspired by: NVIDIA OpenShell (Continuous Monitoring)

v61 — Super Mind العقل الخارق مامون
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """مستويات التنبيه"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class NotificationChannel(str, Enum):
    """قنوات التنبيه"""
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    LOG = "log"
    WEBSOCKET = "websocket"  # v61: WebSocket push channel


@dataclass
class Notification:
    """تنبيه واحد"""
    id: str
    level: NotificationLevel
    title: str
    message: str
    source: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    metadata: dict = field(default_factory=dict)


class NotificationEngine:
    """
    محرك التنبيهات — يراقب NeuralBus ويرسل تنبيهات تلقائية

    المسؤوليات:
    1. الاشتراك في أحداث NeuralBus الحرجة
    2. تحويل الأحداث إلى تنبيهات
    3. إرسال التنبيهات عبر القنوات المتاحة
    4. Rate limiting لمنع الإغراق
    5. تتبع التنبيهات غير المقروءة

    Integration:
    - NeuralBus: مصدر الأحداث
    - MetaCognitionEngine: مصدر بيانات الصحة
    - SelfHealingBridge: مصدر أحداث الشفاء
    """

    RATE_LIMIT_PER_MINUTE = 10
    MAX_IN_APP_NOTIFICATIONS = 200

    def __init__(
        self,
        neural_bus=None,
        meta_cognition=None,
        webhook_url: str = None,
    ):
        self._neural_bus = neural_bus
        self._meta_cognition = meta_cognition
        self._webhook_url = webhook_url or ""

        # قائمة التنبيهات
        self._notifications: list[Notification] = []
        self._notification_counter = 0

        # Rate limiting
        self._sent_timestamps: list[float] = []

        # الاشتراكات
        self._subscribers: dict[str, list[Callable]] = {}

        # v61: WebSocket subscribers for real-time push
        self._ws_subscribers: list[Callable] = []

        # v61: Emergency broadcast log
        self._emergency_broadcasts: list[dict] = []

    def set_neural_bus(self, neural_bus):
        self._neural_bus = neural_bus
        self._subscribe_to_events()

    def set_meta_cognition(self, meta_cognition):
        self._meta_cognition = meta_cognition

    def set_webhook_url(self, url: str):
        self._webhook_url = url

    def _subscribe_to_events(self):
        """الاشتراك في أحداث NeuralBus"""
        if not self._neural_bus:
            return

        try:
            try:
                from ..shared.neural_bus import EventType
            except ImportError:
                from shared.neural_bus import EventType

            # اشتراك في الأحداث الحرجة
            if hasattr(EventType, 'META_STAGNATION'):
                self._neural_bus.subscribe(
                    EventType.META_STAGNATION.value,
                    self._on_stagnation,
                )

            if hasattr(EventType, 'HEALTH_CRITICAL'):
                self._neural_bus.subscribe(
                    EventType.HEALTH_CRITICAL.value,
                    self._on_health_critical,
                )

            # اشتراك في Heartbeat لمراقبة الصحة
            self._neural_bus.subscribe(
                EventType.HEARTBEAT.value,
                self._on_heartbeat,
            )

            logger.info("NotificationEngine subscribed to NeuralBus events")

        except Exception as e:
            logger.error(f"Failed to subscribe to NeuralBus: {e}")

    async def _on_stagnation(self, event):
        """معالجة حدث الركود"""
        data = event.data if hasattr(event, 'data') else {}
        component = data.get("component", "unknown")
        reason = data.get("reason", "stagnation detected")

        await self.send_notification(
            level=NotificationLevel.WARNING,
            title=f"ركود مكتشف: {component}",
            message=f"المكون {component} يعاني من ركود. السبب: {reason}",
            source="meta_cognition",
            metadata=data,
        )

    async def _on_health_critical(self, event):
        """معالجة حدث صحي حرج"""
        data = event.data if hasattr(event, 'data') else {}
        component = data.get("component", "unknown")

        await self.send_notification(
            level=NotificationLevel.CRITICAL,
            title=f"صحة حرجة: {component}",
            message=f"المكون {component} في حالة حرجة! الإجراء: {data.get('action', 'none')}",
            source="health_monitor",
            channel=NotificationChannel.WEBHOOK,  # أرسل عبر webhook أيضاً
            metadata=data,
        )

    async def _on_heartbeat(self, event):
        """معالجة نبض القلب — كشف المكونات غير الصحية"""
        data = event.data if hasattr(event, 'data') else {}
        health = data.get("health", 1.0)
        source = event.source if hasattr(event, 'source') else "unknown"

        if health < 0.3:
            await self.send_notification(
                level=NotificationLevel.WARNING,
                title=f"صحة منخفضة: {source}",
                message=f"المكون {source} صحته {health:.1%} — أقل من الحد الأدنى",
                source="heartbeat_monitor",
                metadata={"health": health, "component": source},
            )

    async def send_notification(
        self,
        level: Any = None,
        title: str = "",
        message: str = "",
        source: str = "system",
        channel: NotificationChannel = NotificationChannel.IN_APP,
        metadata: dict = None,
    ) -> Optional[Notification]:
        """
        إرسال تنبيه — مع rate limiting
        level يمكن أن يكون NotificationLevel أو str
        """
        # تطبيع المستوى
        if isinstance(level, str):
            try:
                level = NotificationLevel(level)
            except ValueError:
                level = NotificationLevel.INFO
        elif not isinstance(level, NotificationLevel):
            level = NotificationLevel.INFO
        # Rate limiting
        now = time.time()
        self._sent_timestamps = [
            t for t in self._sent_timestamps if now - t < 60
        ]
        if len(self._sent_timestamps) >= self.RATE_LIMIT_PER_MINUTE:
            logger.warning("Notification rate limit reached — dropping notification")
            return None

        # إنشاء التنبيه
        self._notification_counter += 1
        notification = Notification(
            id=f"notif_{int(time.time())}_{self._notification_counter}",
            level=level,
            title=title,
            message=message,
            source=source,
            channel=channel,
            metadata=metadata or {},
        )

        # إضافة للقائمة
        self._notifications.append(notification)
        if len(self._notifications) > self.MAX_IN_APP_NOTIFICATIONS:
            self._notifications = self._notifications[-100:]

        # تسجيل الوقت
        self._sent_timestamps.append(now)

        # إرسال عبر القنوات
        await self._dispatch(notification)

        logger.info(f"Notification [{level.value}]: {title}")

        return notification

    async def _dispatch(self, notification: Notification):
        """إرسال التنبيه عبر القنوات المتاحة"""
        # دائماً: تسجيل في السجل
        self._log_notification(notification)

        # IN_APP: مضاف بالفعل في القائمة
        # إعلام المشتركين
        await self._notify_subscribers(notification)

        # WEBHOOK: إرسال HTTP POST
        if notification.channel == NotificationChannel.WEBHOOK:
            if notification.level in (NotificationLevel.CRITICAL, NotificationLevel.EMERGENCY):
                await self._send_webhook(notification)

        # EMERGENCY: إرسال عبر كل القنوات المتاحة
        if notification.level == NotificationLevel.EMERGENCY:
            await self._send_all_channels(notification)

    def _log_notification(self, notification: Notification):
        """تسجيل التنبيه في السجل"""
        log_level = {
            NotificationLevel.INFO: logging.INFO,
            NotificationLevel.WARNING: logging.WARNING,
            NotificationLevel.CRITICAL: logging.CRITICAL,
            NotificationLevel.EMERGENCY: logging.CRITICAL,
        }.get(notification.level, logging.INFO)

        logger.log(
            log_level,
            f"[{notification.level.value.upper()}] {notification.title}: {notification.message}",
        )

    async def _send_webhook(self, notification: Notification):
        """إرسال عبر webhook"""
        if not self._webhook_url:
            return

        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                payload = {
                    "level": notification.level.value,
                    "title": notification.title,
                    "message": notification.message,
                    "source": notification.source,
                    "timestamp": notification.timestamp,
                    "metadata": notification.metadata,
                }
                response = await client.post(
                    self._webhook_url,
                    json=payload,
                )
                if response.status_code >= 400:
                    logger.warning(f"Webhook delivery failed: {response.status_code}")
        except ImportError:
            logger.debug("httpx not available for webhook")
        except Exception as e:
            logger.warning(f"Webhook delivery failed: {e}")

    async def _send_all_channels(self, notification: Notification):
        """إرسال عبر كل القنوات المتاحة للحالات الطارئة"""
        # Webhook (أعلاه)
        # إضافة قنوات أخرى هنا (email, telegram, discord) عند التهيئة
        logger.critical(
            f"EMERGENCY NOTIFICATION: {notification.title} — {notification.message}"
        )

    async def _notify_subscribers(self, notification: Notification):
        """إعلام المشتركين بالتنبيه"""
        level_key = notification.level.value
        for callback in self._subscribers.get(level_key, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.warning(f"Notification subscriber failed: {e}")

    def subscribe(self, level: NotificationLevel, callback: Callable):
        """الاشتراك في تنبيهات بمستوى معين"""
        key = level.value
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)

    def acknowledge(self, notification_id: str) -> bool:
        """تأكيد قراءة تنبيه"""
        for n in self._notifications:
            if n.id == notification_id:
                n.acknowledged = True
                return True
        return False

    # ── v61: WebSocket Push ──────────────────────────────────────────────

    def subscribe_ws(self, callback: Callable):
        """الاشتراك في تحديثات WebSocket الفورية"""
        self._ws_subscribers.append(callback)

    async def _ws_push(self, notification: Notification) -> None:
        """
        إرسال تنبيه عبر WebSocket لجميع المشتركين

        Pushes notification data to all WebSocket subscribers in real-time.
        Used for live dashboard updates and emergency alerts.

        Args:
            notification: The notification to push
        """
        data = {
            "type": "notification",
            "id": notification.id,
            "level": notification.level.value,
            "title": notification.title,
            "message": notification.message,
            "source": notification.source,
            "channel": notification.channel.value,
            "timestamp": notification.timestamp,
            "metadata": notification.metadata,
        }

        for callback in self._ws_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.debug(f"WS push subscriber failed: {e}")

    # ── v61: API Endpoint Data ───────────────────────────────────────────

    def get_api_notifications(self, level: NotificationLevel = None, limit: int = 50, offset: int = 0) -> dict:
        """
        الحصول على بيانات التنبيهات بتنسيق API endpoint

        Returns structured notification data suitable for REST API responses,
        with pagination support and optional level filtering.

        Args:
            level: Optional level filter
            limit: Maximum number of notifications to return (default 50)
            offset: Pagination offset (default 0)

        Returns:
            dict with:
            - notifications: list of notification dicts
            - total: total count of matching notifications
            - unread_count: count of unread matching notifications
            - limit: the limit used
            - offset: the offset used
            - version: "v61"
        """
        notifications = self._notifications
        if level:
            notifications = [n for n in notifications if n.level == level]

        total = len(notifications)
        unread_count = sum(1 for n in notifications if not n.acknowledged)

        # Apply pagination
        paginated = notifications[offset:offset + limit]

        return {
            "version": "v61",
            "notifications": [
                {
                    "id": n.id,
                    "level": n.level.value,
                    "title": n.title,
                    "message": n.message,
                    "source": n.source,
                    "channel": n.channel.value,
                    "timestamp": n.timestamp,
                    "acknowledged": n.acknowledged,
                    "metadata": n.metadata,
                }
                for n in reversed(paginated)
            ],
            "total": total,
            "unread_count": unread_count,
            "limit": limit,
            "offset": offset,
        }

    # ── v61: Emergency Broadcast ─────────────────────────────────────────

    async def broadcast_emergency(self, title: str, message: str, metadata: dict = None) -> dict:
        """
        بث طوارئ — إرسال عبر جميع القنوات في وقت واحد

        Sends an emergency notification to ALL available channels simultaneously:
        - IN_APP (always)
        - WEBHOOK (if configured)
        - LOG (always)
        - WEBSOCKET (to all WS subscribers)
        - Subscribers at all levels

        This bypasses rate limiting for emergency broadcasts.

        Args:
            title: Emergency title
            message: Emergency message
            metadata: Optional additional metadata

        Returns:
            dict with broadcast results per channel
        """
        results = {}

        # Create the emergency notification
        self._notification_counter += 1
        notification = Notification(
            id=f"emergency_{int(time.time())}_{self._notification_counter}",
            level=NotificationLevel.EMERGENCY,
            title=title,
            message=message,
            source="emergency_broadcast",
            channel=NotificationChannel.IN_APP,
            timestamp=time.time(),
            metadata=metadata or {},
        )

        # 1. IN_APP — add to list
        self._notifications.append(notification)
        if len(self._notifications) > self.MAX_IN_APP_NOTIFICATIONS:
            self._notifications = self._notifications[-100:]
        results["in_app"] = True

        # 2. LOG — always log
        self._log_notification(notification)
        results["log"] = True

        # 3. WEBHOOK — send if configured
        if self._webhook_url:
            try:
                await self._send_webhook(notification)
                results["webhook"] = True
            except Exception as e:
                results["webhook"] = False
                results["webhook_error"] = str(e)
        else:
            results["webhook"] = False
            results["webhook_reason"] = "not_configured"

        # 4. WEBSOCKET — push to all subscribers
        try:
            await self._ws_push(notification)
            results["websocket"] = True
            results["ws_subscribers_notified"] = len(self._ws_subscribers)
        except Exception as e:
            results["websocket"] = False
            results["websocket_error"] = str(e)

        # 5. Notify all level subscribers
        notified_subscribers = 0
        for level_key in self._subscribers:
            for callback in self._subscribers[level_key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(notification)
                    else:
                        callback(notification)
                    notified_subscribers += 1
                except Exception as e:
                    logger.warning(f"Emergency broadcast subscriber failed: {e}")
        results["subscribers_notified"] = notified_subscribers

        # 6. NeuralBus — publish emergency event
        if self._neural_bus:
            try:
                from ..shared.neural_bus import Event, EventType
            except ImportError:
                try:
                    from shared.neural_bus import Event, EventType
                except ImportError:
                    EventType = None

            if EventType and hasattr(EventType, 'HEALTH_CRITICAL'):
                try:
                    await self._neural_bus.publish(Event(
                        event_type=EventType.HEALTH_CRITICAL,
                        source="notification_engine",
                        data={
                            "title": title,
                            "message": message,
                            "metadata": metadata or {},
                            "broadcast": True,
                        },
                    ))
                    results["neural_bus"] = True
                except Exception as e:
                    results["neural_bus"] = False
                    results["neural_bus_error"] = str(e)

        # Record emergency broadcast
        broadcast_record = {
            "id": notification.id,
            "title": title,
            "message": message,
            "timestamp": notification.timestamp,
            "results": results,
            "metadata": metadata or {},
        }
        self._emergency_broadcasts.append(broadcast_record)
        if len(self._emergency_broadcasts) > 50:
            self._emergency_broadcasts = self._emergency_broadcasts[-25:]

        logger.critical(f"EMERGENCY BROADCAST: {title} — {message}")

        return results

    def get_unread(self, level: NotificationLevel = None) -> list[dict]:
        """الحصول على التنبيهات غير المقروءة"""
        notifications = [
            n for n in self._notifications if not n.acknowledged
        ]
        if level:
            notifications = [
                n for n in notifications if n.level == level
            ]
        return [
            {
                "id": n.id,
                "level": n.level.value,
                "title": n.title,
                "message": n.message,
                "source": n.source,
                "timestamp": n.timestamp,
                "metadata": n.metadata,
            }
            for n in reversed(notifications[-50:])
        ]

    def get_stats(self) -> dict:
        """إحصائيات التنبيهات"""
        total = len(self._notifications)
        unread = sum(1 for n in self._notifications if not n.acknowledged)
        by_level = {}
        for n in self._notifications:
            by_level[n.level.value] = by_level.get(n.level.value, 0) + 1

        return {
            "version": "v61",
            "total_notifications": total,
            "unread": unread,
            "by_level": by_level,
            "subscribers": {
                k: len(v) for k, v in self._subscribers.items()
            },
            "ws_subscribers": len(self._ws_subscribers),
            "webhook_configured": bool(self._webhook_url),
            "rate_limit_remaining": self.RATE_LIMIT_PER_MINUTE - len(self._sent_timestamps),
            "emergency_broadcasts_count": len(self._emergency_broadcasts),
        }
