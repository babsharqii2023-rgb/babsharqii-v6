"""
BABSHARQII v13.0 — Notification Engine
محرك الإشعارات — إرسال إشعارات فورية وتقارير دورية عبر قنوات متعددة

Channels:
- SMTP (Email)
- WhatsApp Business API
- Telegram Bot
- Discord Webhook

Scheduling:
- Periodic reports via NightCycle (every 3 hours, daily)
- Event-driven instant notifications

Feature Flag: MAMOUN_NOTIFICATIONS_ENABLED (default: false)
"""

import os
import time
import json
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum
from pathlib import Path

from mamoun.notifications import NOTIFICATIONS_ENABLED

logger = logging.getLogger(__name__)

# Channel Configuration
SMTP_HOST = os.getenv("MAMOUN_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("MAMOUN_SMTP_PORT", "587"))
SMTP_USER = os.getenv("MAMOUN_SMTP_USER", "")
SMTP_PASS = os.getenv("MAMOUN_SMTP_PASS", "")
SMTP_FROM = os.getenv("MAMOUN_SMTP_FROM", "mamoun@babsharqii.ai")

WHATSAPP_API_URL = os.getenv("MAMOUN_WHATSAPP_API_URL", "")
WHATSAPP_TOKEN = os.getenv("MAMOUN_WHATSAPP_TOKEN", "")
WHATSAPP_PHONE = os.getenv("MAMOUN_WHATSAPP_PHONE", "")

TELEGRAM_BOT_TOKEN = os.getenv("MAMOUN_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("MAMOUN_TELEGRAM_CHAT_ID", "")

DISCORD_WEBHOOK_URL = os.getenv("MAMOUN_DISCORD_WEBHOOK_URL", "")


class NotificationChannel(str, Enum):
    """قنوات الإشعارات."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    IN_APP = "in_app"  # Internal notification (shown in dashboard)


class NotificationPriority(str, Enum):
    """أولوية الإشعار."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """حالة الإشعار."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"


@dataclass
class Notification:
    """إشعار."""
    notification_id: str = ""
    title: str = ""
    title_ar: str = ""
    body: str = ""
    body_ar: str = ""
    channel: str = NotificationChannel.IN_APP.value
    priority: str = NotificationPriority.NORMAL.value
    status: str = NotificationStatus.PENDING.value
    recipient: str = ""
    data: dict = field(default_factory=dict)
    created_at: float = 0.0
    sent_at: float = 0.0
    delivered_at: float = 0.0
    error: str = ""
    retry_count: int = 0

    def __post_init__(self):
        if not self.notification_id:
            self.notification_id = f"notif_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReportConfig:
    """إعدادات التقرير الدوري."""
    report_id: str = ""
    name: str = ""
    name_ar: str = ""
    interval_hours: float = 3.0
    channels: list = field(default_factory=list)  # List of NotificationChannel
    enabled: bool = True
    last_sent_at: float = 0.0
    next_send_at: float = 0.0
    template: str = ""  # Report template

    def to_dict(self) -> dict:
        return asdict(self)


class Notifier:
    """
    محرك الإشعارات — يرسل إشعارات عبر قنوات متعددة.

    Features:
    - Multi-channel notifications (Email, WhatsApp, Telegram, Discord)
    - In-app notifications for dashboard
    - Periodic report scheduling
    - Priority-based routing (urgent → all channels, low → in-app only)
    - Retry logic for failed deliveries
    - Integration with NightCycle for periodic reports

    Usage:
        notifier = Notifier()
        await notifier.send(
            title="Task Complete",
            title_ar="اكتملت المهمة",
            body="The evolution cycle completed successfully",
            body_ar="اكتملت دورة التطور بنجاح",
            channel=NotificationChannel.TELEGRAM,
            priority=NotificationPriority.HIGH,
        )
    """

    def __init__(self):
        self._notifications: dict[str, Notification] = {}
        self._reports: dict[str, ReportConfig] = {}
        self._channel_status: dict[str, dict] = {}
        self._sent_count = 0
        self._failed_count = 0
        self._in_app_queue: list[dict] = []  # For dashboard notifications

        # Initialize channel availability
        self._channel_status = {
            NotificationChannel.EMAIL.value: {
                "available": bool(SMTP_HOST and SMTP_USER),
                "config": "SMTP" if SMTP_HOST else "Not configured",
            },
            NotificationChannel.WHATSAPP.value: {
                "available": bool(WHATSAPP_API_URL and WHATSAPP_TOKEN),
                "config": "WhatsApp Business API" if WHATSAPP_API_URL else "Not configured",
            },
            NotificationChannel.TELEGRAM.value: {
                "available": bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
                "config": "Telegram Bot" if TELEGRAM_BOT_TOKEN else "Not configured",
            },
            NotificationChannel.DISCORD.value: {
                "available": bool(DISCORD_WEBHOOK_URL),
                "config": "Discord Webhook" if DISCORD_WEBHOOK_URL else "Not configured",
            },
            NotificationChannel.IN_APP.value: {
                "available": True,
                "config": "Always available",
            },
        }

        # Default periodic reports
        self._setup_default_reports()

    def _setup_default_reports(self):
        """إعداد التقارير الدورية الافتراضية."""
        self._reports["status_3h"] = ReportConfig(
            report_id="status_3h",
            name="Status Report (3h)",
            name_ar="تقرير الحالة (كل 3 ساعات)",
            interval_hours=3.0,
            channels=[NotificationChannel.IN_APP.value],
            next_send_at=time.time() + 3 * 3600,
            template="status_report",
        )
        self._reports["daily_summary"] = ReportConfig(
            report_id="daily_summary",
            name="Daily Summary",
            name_ar="ملخص يومي",
            interval_hours=24.0,
            channels=[NotificationChannel.IN_APP.value],
            next_send_at=time.time() + 24 * 3600,
            template="daily_summary",
        )

    async def send(
        self,
        title: str = "",
        title_ar: str = "",
        body: str = "",
        body_ar: str = "",
        channel: str = NotificationChannel.IN_APP.value,
        priority: str = NotificationPriority.NORMAL.value,
        recipient: str = "",
        data: dict = None,
    ) -> dict:
        """
        إرسال إشعار — Send a notification.

        Args:
            title: عنوان الإشعار (English)
            title_ar: عنوان الإشعار (Arabic)
            body: محتوى الإشعار (English)
            body_ar: محتوى الإشعار (Arabic)
            channel: قناة الإرسال
            priority: أولوية الإشعار
            recipient: المستلم
            data: بيانات إضافية

        Returns:
            dict with notification_id and status
        """
        if not NOTIFICATIONS_ENABLED:
            return {
                "notification_id": "",
                "status": "disabled",
                "message": "الإشعارات غير مفعّلة. قم بتعيين MAMOUN_NOTIFICATIONS_ENABLED=true",
            }

        notification = Notification(
            title=title,
            title_ar=title_ar,
            body=body,
            body_ar=body_ar,
            channel=channel,
            priority=priority,
            recipient=recipient,
            data=data or {},
        )

        self._notifications[notification.notification_id] = notification

        # Priority-based routing
        channels_to_use = self._resolve_channels(channel, priority)

        for ch in channels_to_use:
            try:
                result = await self._send_to_channel(notification, ch)
                if result.get("success"):
                    notification.status = NotificationStatus.SENT.value
                    notification.sent_at = time.time()
                    self._sent_count += 1
                else:
                    notification.error = result.get("error", "Unknown error")
                    self._failed_count += 1
            except Exception as e:
                notification.error = str(e)[:200]
                self._failed_count += 1

        # Always store in-app notification
        self._in_app_queue.append(notification.to_dict())
        if len(self._in_app_queue) > 100:
            self._in_app_queue = self._in_app_queue[-50:]

        return {
            "notification_id": notification.notification_id,
            "status": notification.status,
            "channels_used": channels_to_use,
        }

    def _resolve_channels(self, requested_channel: str, priority: str) -> list[str]:
        """تحديد القنوات بناءً على الأولوية."""
        channels = [requested_channel]

        # Urgent: send to all available channels
        if priority == NotificationPriority.URGENT.value:
            channels = [
                ch for ch, status in self._channel_status.items()
                if status["available"]
            ]

        # High: send to requested + in-app
        elif priority == NotificationPriority.HIGH.value:
            if NotificationChannel.IN_APP.value not in channels:
                channels.append(NotificationChannel.IN_APP.value)

        return channels

    async def _send_to_channel(self, notification: Notification, channel: str) -> dict:
        """إرسال عبر قناة محددة."""
        if channel == NotificationChannel.EMAIL.value:
            return await self._send_email(notification)
        elif channel == NotificationChannel.WHATSAPP.value:
            return await self._send_whatsapp(notification)
        elif channel == NotificationChannel.TELEGRAM.value:
            return await self._send_telegram(notification)
        elif channel == NotificationChannel.DISCORD.value:
            return await self._send_discord(notification)
        elif channel == NotificationChannel.IN_APP.value:
            return {"success": True, "channel": "in_app"}
        else:
            return {"success": False, "error": f"Unknown channel: {channel}"}

    async def _send_email(self, notification: Notification) -> dict:
        """إرسال بريد إلكتروني."""
        if not SMTP_HOST:
            return {"success": False, "error": "SMTP not configured"}

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.title_ar or notification.title
            msg["From"] = SMTP_FROM
            msg["To"] = notification.recipient or SMTP_USER

            text = notification.body_ar or notification.body
            msg.attach(MIMEText(text, "plain", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASS,
                use_tls=True,
            )
            return {"success": True, "channel": "email"}
        except ImportError:
            return {"success": False, "error": "aiosmtplib not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    async def _send_whatsapp(self, notification: Notification) -> dict:
        """إرسال عبر واتساب."""
        if not WHATSAPP_API_URL or not WHATSAPP_TOKEN:
            return {"success": False, "error": "WhatsApp not configured"}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{WHATSAPP_API_URL}/messages",
                    headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": notification.recipient or WHATSAPP_PHONE,
                        "type": "text",
                        "text": {"body": notification.body_ar or notification.body},
                    },
                )
                if resp.status_code == 200:
                    return {"success": True, "channel": "whatsapp"}
                return {"success": False, "error": f"WhatsApp API: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    async def _send_telegram(self, notification: Notification) -> dict:
        """إرسال عبر تلجرام."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return {"success": False, "error": "Telegram not configured"}

        try:
            import httpx
            text = f"*{notification.title_ar or notification.title}*\n\n{notification.body_ar or notification.body}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHAT_ID,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
                if resp.status_code == 200:
                    return {"success": True, "channel": "telegram"}
                return {"success": False, "error": f"Telegram API: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    async def _send_discord(self, notification: Notification) -> dict:
        """إرسال عبر ديسكورد."""
        if not DISCORD_WEBHOOK_URL:
            return {"success": False, "error": "Discord not configured"}

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    DISCORD_WEBHOOK_URL,
                    json={
                        "content": f"**{notification.title or notification.title_ar}**\n{notification.body or notification.body_ar}",
                    },
                )
                if resp.status_code == 204:
                    return {"success": True, "channel": "discord"}
                return {"success": False, "error": f"Discord API: {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}

    def get_in_app_notifications(self, limit: int = 20) -> list[dict]:
        """الحصول على الإشعارات الداخلية (للوحة التحكم)."""
        return list(reversed(self._in_app_queue[-limit:]))

    def get_channel_status(self) -> dict:
        """حالة القنوات."""
        return self._channel_status

    def get_status(self) -> dict:
        """حالة محرك الإشعارات."""
        return {
            "enabled": NOTIFICATIONS_ENABLED,
            "channels": self._channel_status,
            "sent_count": self._sent_count,
            "failed_count": self._failed_count,
            "in_app_count": len(self._in_app_queue),
            "reports_configured": len(self._reports),
            "notifications_tracked": len(self._notifications),
        }

    async def send_periodic_report(self, report_id: str, report_data: dict) -> dict:
        """إرسال تقرير دوري."""
        config = self._reports.get(report_id)
        if not config or not config.enabled:
            return {"status": "disabled", "report_id": report_id}

        return await self.send(
            title=f"Report: {config.name}",
            title_ar=config.name_ar,
            body=json.dumps(report_data, ensure_ascii=False, indent=2),
            body_ar=f"تقرير: {config.name_ar}",
            channel=config.channels[0] if config.channels else NotificationChannel.IN_APP.value,
            priority=NotificationPriority.LOW.value,
            data={"report_id": report_id, "report_data": report_data},
        )

    async def shutdown(self):
        """إيقاف المحرك — يتوافق مع القانون 5."""
        logger.info("Notifier: Shutdown complete (Law 5 compliant)")
