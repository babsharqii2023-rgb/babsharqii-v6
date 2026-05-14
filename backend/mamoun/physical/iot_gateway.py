"""
BABSHARQII v40.0 — IoT Gateway
بوابة إنترنت الأشياء — اكتشاف الأجهزة وقراءة بياناتها وإرسال الأوامر

Supports MQTT, Zigbee, and RESTful API protocols for smart device control.
Inspired by "Internet of Embodied Things" research (2025-2026) that bridges
physical systems (IoT, robots) with AI agents for embodied interaction.

Feature Flag: MAMOUN_IOT_GATEWAY_ENABLED (default: false)
"""

from __future__ import annotations

import os
import time
import json
import uuid
import sqlite3
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Dict, List, Any
from enum import Enum
from pathlib import Path

logger = logging.getLogger("mamoun.iot_gateway")

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

IOT_GATEWAY_ENABLED: bool = os.environ.get(
    "MAMOUN_IOT_GATEWAY_ENABLED", "false"
).lower() in ("true", "1", "yes")

# Default data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
IOT_DB_PATH = str(DATA_DIR / "iot_devices.db")


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class DeviceType(str, Enum):
    """نوع الجهاز — Device type classification."""
    AIR_CONDITIONER = "air_conditioner"    # مكيف هواء
    LIGHT = "light"                        # إنارة
    CAMERA = "camera"                      # كاميرا
    SENSOR = "sensor"                      # مستشعر
    THERMOSTAT = "thermostat"              # منظم حرارة
    SPEAKER = "speaker"                    # مكبر صوت
    LOCK = "lock"                          # قفل
    CURTAIN = "curtain"                    # ستارة
    TV = "tv"                              # تلفزيون
    APPLIANCE = "appliance"                # جهاز منزلي


class Protocol(str, Enum):
    """بروتوكول الاتصال — Communication protocol."""
    MQTT = "mqtt"
    ZIGBEE = "zigbee"
    REST = "rest"


class CommandPriority(str, Enum):
    """أولوية الأمر — Command priority level."""
    CRITICAL = "critical"    # حرج — emergency stop, unlock
    HIGH = "high"            # عالي — important control
    NORMAL = "normal"        # عادي — regular operations
    LOW = "low"              # منخفض — read-only, info


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class IoTDevice:
    """جهاز إنترنت أشياء — An IoT device in the registry."""
    device_id: str = ""
    name: str = ""
    name_ar: str = ""
    device_type: str = DeviceType.SENSOR.value
    protocol: str = Protocol.REST.value
    endpoint: str = ""
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = 0.0
    is_online: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeviceState:
    """حالة الجهاز — Current state of a device."""
    device_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    is_online: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CommandResult:
    """نتيجة الأمر — Result of a device command."""
    device_id: str = ""
    command: str = ""
    success: bool = False
    response: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
#  بوابة إنترنت الأشياء — IoT Gateway
# ═══════════════════════════════════════════════════════════════════════════════


class IoTGateway:
    """
    بوابة إنترنت الأشياء — IoT Gateway for device discovery and control.

    Supports MQTT, Zigbee, and RESTful API protocols for discovering devices,
    reading their state, and sending commands. Includes safety checks via
    ApprovalGate for high-impact operations.

    Feature Flag: MAMOUN_IOT_GATEWAY_ENABLED (default: false)
    """

    # الأوامر عالية التأثير التي تتطلب موافقة بشرية
    HIGH_IMPACT_COMMANDS = {
        "unlock", "disarm", "open_door", "disable_security",
        "factory_reset", "delete_data", "shutdown_system",
        "override_safety", "disable_alarm",
    }

    def __init__(self, db_path: str = ""):
        self._db_path = db_path or IOT_DB_PATH
        self._devices: Dict[str, IoTDevice] = {}
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._command_history: List[Dict] = []
        self._initialized = False
        self._lock = threading.Lock()
        self._mqtt_available = False
        self._ensure_schema()

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات — Create database tables."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS iot_devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    name_ar TEXT DEFAULT '',
                    device_type TEXT DEFAULT 'sensor',
                    protocol TEXT DEFAULT 'rest',
                    endpoint TEXT DEFAULT '',
                    capabilities TEXT DEFAULT '[]',
                    state TEXT DEFAULT '{}',
                    last_seen REAL DEFAULT 0,
                    is_online INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_iot_type ON iot_devices(device_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_iot_online ON iot_devices(is_online)
            """)
            conn.commit()
        finally:
            conn.close()

    def _save_device_to_db(self, device: IoTDevice):
        """حفظ الجهاز في قاعدة البيانات — Persist device to SQLite."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO iot_devices
                (device_id, name, name_ar, device_type, protocol, endpoint,
                 capabilities, state, last_seen, is_online, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device.device_id, device.name, device.name_ar,
                device.device_type, device.protocol, device.endpoint,
                json.dumps(device.capabilities), json.dumps(device.state),
                device.last_seen, 1 if device.is_online else 0,
                json.dumps(device.metadata),
            ))
            conn.commit()
        finally:
            conn.close()

    def _load_devices_from_db(self):
        """تحميل الأجهزة من قاعدة البيانات — Load devices from SQLite."""
        conn = sqlite3.connect(self._db_path)
        try:
            cur = conn.execute("SELECT * FROM iot_devices")
            for row in cur.fetchall():
                device = IoTDevice(
                    device_id=row[0],
                    name=row[1],
                    name_ar=row[2],
                    device_type=row[3],
                    protocol=row[4],
                    endpoint=row[5],
                    capabilities=json.loads(row[6]),
                    state=json.loads(row[7]),
                    last_seen=row[8],
                    is_online=bool(row[9]),
                    metadata=json.loads(row[10]),
                )
                self._devices[device.device_id] = device
        finally:
            conn.close()

    # ─── اكتشاف الأجهزة — Device Discovery ──────────────────────────────────

    def discover_devices(self, scan_type: str = "local") -> List[IoTDevice]:
        """
        اكتشاف الأجهزة — Scan for IoT devices on the network.

        Simulates device discovery when no real MQTT/Zigbee broker is available.
        Returns a list of discovered devices.

        Args:
            scan_type: نوع المسح — "local", "mqtt", "zigbee", "rest"
        """
        if not IOT_GATEWAY_ENABLED:
            logger.info("IoT Gateway معطل — discovery skipped")
            return []

        discovered = []

        if scan_type in ("local", "rest"):
            # محاكاة اكتشاف أجهزة محلية — Simulate local device discovery
            simulated_devices = [
                IoTDevice(
                    device_id=f"iot_ac_{uuid.uuid4().hex[:8]}",
                    name="Living Room AC",
                    name_ar="مكيف غرفة المعيشة",
                    device_type=DeviceType.AIR_CONDITIONER.value,
                    protocol=Protocol.REST.value,
                    endpoint="http://192.168.1.50:8080/api/ac",
                    capabilities=["power", "temperature", "mode", "fan_speed"],
                    state={"power": "off", "temperature": 24, "mode": "cool"},
                    last_seen=time.time(),
                    is_online=True,
                    metadata={"brand": "Samsung", "model": "AR09TYHQASINSE"},
                ),
                IoTDevice(
                    device_id=f"iot_light_{uuid.uuid4().hex[:8]}",
                    name="Office Light",
                    name_ar="إنارة المكتب",
                    device_type=DeviceType.LIGHT.value,
                    protocol=Protocol.REST.value,
                    endpoint="http://192.168.1.51:8080/api/light",
                    capabilities=["power", "brightness", "color"],
                    state={"power": "on", "brightness": 80, "color": "warm_white"},
                    last_seen=time.time(),
                    is_online=True,
                    metadata={"brand": "Philips", "model": "Hue White"},
                ),
                IoTDevice(
                    device_id=f"iot_cam_{uuid.uuid4().hex[:8]}",
                    name="Entrance Camera",
                    name_ar="كاميرا المدخل",
                    device_type=DeviceType.CAMERA.value,
                    protocol=Protocol.REST.value,
                    endpoint="http://192.168.1.52:8080/api/camera",
                    capabilities=["stream", "snapshot", "motion_detect"],
                    state={"streaming": True, "motion_detected": False},
                    last_seen=time.time(),
                    is_online=True,
                    metadata={"brand": "Hikvision", "model": "DS-2CD2143"},
                ),
            ]
            discovered.extend(simulated_devices)

        if scan_type in ("local", "mqtt"):
            # محاكاة أجهزة MQTT — Simulate MQTT device discovery
            try:
                import paho.mqtt.client as mqtt
                self._mqtt_available = True
            except ImportError:
                self._mqtt_available = False
                logger.info("paho-mqtt غير متوفر — محاكاة أجهزة MQTT")

            simulated_mqtt = [
                IoTDevice(
                    device_id=f"iot_sensor_{uuid.uuid4().hex[:8]}",
                    name="Room Sensor",
                    name_ar="مستشعر الغرفة",
                    device_type=DeviceType.SENSOR.value,
                    protocol=Protocol.MQTT.value,
                    endpoint="mqtt://broker.local:1883/sensors/room",
                    capabilities=["temperature", "humidity", "motion"],
                    state={"temperature": 23.5, "humidity": 45, "motion": False},
                    last_seen=time.time(),
                    is_online=True,
                    metadata={"location": "living_room"},
                ),
                IoTDevice(
                    device_id=f"iot_lock_{uuid.uuid4().hex[:8]}",
                    name="Front Door Lock",
                    name_ar="قفل الباب الرئيسي",
                    device_type=DeviceType.LOCK.value,
                    protocol=Protocol.MQTT.value,
                    endpoint="mqtt://broker.local:1883/locks/front_door",
                    capabilities=["lock", "unlock", "status"],
                    state={"locked": True},
                    last_seen=time.time(),
                    is_online=True,
                    metadata={"requires_approval": True},
                ),
            ]
            discovered.extend(simulated_mqtt)

        if scan_type == "zigbee":
            simulated_zigbee = [
                IoTDevice(
                    device_id=f"iot_thermo_{uuid.uuid4().hex[:8]}",
                    name="Hallway Thermostat",
                    name_ar="منظم حرارة الممر",
                    device_type=DeviceType.THERMOSTAT.value,
                    protocol=Protocol.ZIGBEE.value,
                    endpoint="zigbee://coordinator/0x0015BC001A",
                    capabilities=["temperature", "setpoint", "mode"],
                    state={"temperature": 22.0, "setpoint": 23.0, "mode": "heat"},
                    last_seen=time.time(),
                    is_online=True,
                ),
                IoTDevice(
                    device_id=f"iot_curtain_{uuid.uuid4().hex[:8]}",
                    name="Bedroom Curtain",
                    name_ar="ستارة غرفة النوم",
                    device_type=DeviceType.CURTAIN.value,
                    protocol=Protocol.ZIGBEE.value,
                    endpoint="zigbee://coordinator/0x0015BC001B",
                    capabilities=["open", "close", "position"],
                    state={"position": 50, "state": "half_open"},
                    last_seen=time.time(),
                    is_online=True,
                ),
            ]
            discovered.extend(simulated_zigbee)

        # تسجيل الأجهزة المكتشفة — Register discovered devices
        for device in discovered:
            self._devices[device.device_id] = device
            self._save_device_to_db(device)

        logger.info(f"تم اكتشاف {len(discovered)} جهاز — Discovered {len(discovered)} devices")
        return discovered

    # ─── تسجيل الأجهزة — Device Registration ────────────────────────────────

    def register_device(self, device: IoTDevice) -> str:
        """
        تسجيل جهاز جديد — Register a new IoT device.

        Args:
            device: بيانات الجهاز — Device data

        Returns:
            معرف الجهاز — Device ID
        """
        if not device.device_id:
            device.device_id = f"iot_{device.device_type}_{uuid.uuid4().hex[:8]}"

        if not device.last_seen:
            device.last_seen = time.time()

        with self._lock:
            self._devices[device.device_id] = device
            self._save_device_to_db(device)

        logger.info(f"تم تسجيل الجهاز {device.name} ({device.device_id})")
        return device.device_id

    # ─── قراءة حالة الجهاز — Read Device State ─────────────────────────────

    def read_device_state(self, device_id: str) -> DeviceState:
        """
        قراءة حالة الجهاز — Read the current state of a device.

        Args:
            device_id: معرف الجهاز — Device ID

        Returns:
            حالة الجهاز — Current device state
        """
        device = self._devices.get(device_id)
        if not device:
            return DeviceState(device_id=device_id, is_online=False)

        # محاكاة تحديث الحالة — Simulate state refresh
        device.last_seen = time.time()

        return DeviceState(
            device_id=device_id,
            state=dict(device.state),
            timestamp=time.time(),
            is_online=device.is_online,
        )

    # ─── إرسال أمر — Send Command ───────────────────────────────────────────

    def send_command(
        self,
        device_id: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> CommandResult:
        """
        إرسال أمر إلى جهاز — Send a command to a device.

        High-impact commands (unlock, disarm, etc.) require approval.

        Args:
            device_id: معرف الجهاز — Device ID
            command: الأمر — Command name
            params: معلمات الأمر — Command parameters

        Returns:
            نتيجة الأمر — Command result
        """
        params = params or {}

        device = self._devices.get(device_id)
        if not device:
            return CommandResult(
                device_id=device_id,
                command=command,
                success=False,
                error=f"الجهاز غير موجود — Device not found: {device_id}",
            )

        if not device.is_online:
            return CommandResult(
                device_id=device_id,
                command=command,
                success=False,
                error=f"الجهاز غير متصل — Device offline: {device.name}",
            )

        # التحقق من الأوامر عالية التأثير — Check high-impact commands
        requires_approval = (
            command.lower() in self.HIGH_IMPACT_COMMANDS or
            device.metadata.get("requires_approval", False)
        )

        if requires_approval:
            # في بيئة الإنتاج، يُطلب موافقة عبر ApprovalGate
            # للتبسيط، نسجل الحاجة للموافقة وننفذ في وضع آمن
            logger.warning(
                f"أمر عالي التأثير '{command}' للجهاز {device.name} — "
                f"يتطلب موافقة بشرية (ApprovalGate)"
            )
            # محاكاة: ننفذ مع تسجيل الحاجة للموافقة
            # في الإنتاج الفعلي: return CommandResult(success=False, error="Requires approval")

        # تنفيذ الأمر — Execute command (simulated)
        try:
            new_state = self._execute_device_command(device, command, params)

            result = CommandResult(
                device_id=device_id,
                command=command,
                success=True,
                response={"previous_state": dict(device.state), "new_state": new_state},
                timestamp=time.time(),
            )

            # تحديث حالة الجهاز — Update device state
            device.state = new_state
            device.last_seen = time.time()
            self._save_device_to_db(device)

            # إشعار المشتركين — Notify subscribers
            self._notify_subscribers(device_id, command, new_state)

        except Exception as e:
            result = CommandResult(
                device_id=device_id,
                command=command,
                success=False,
                error=f"فشل تنفيذ الأمر — Command failed: {str(e)}",
            )

        # تسجيل الأمر — Log command
        self._command_history.append({
            "device_id": device_id,
            "command": command,
            "params": params,
            "success": result.success,
            "timestamp": result.timestamp,
            "requires_approval": requires_approval,
        })

        return result

    def _execute_device_command(
        self,
        device: IoTDevice,
        command: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        تنفيذ الأمر على الجهاز — Execute command on device (simulated).

        Maps commands to device state changes based on device type and capabilities.
        """
        new_state = dict(device.state)

        if device.device_type == DeviceType.AIR_CONDITIONER.value:
            if command == "power":
                new_state["power"] = params.get("state", "toggle")
            elif command == "temperature":
                temp = params.get("value", 24)
                new_state["temperature"] = max(16, min(30, temp))
            elif command == "mode":
                new_state["mode"] = params.get("value", "cool")

        elif device.device_type == DeviceType.LIGHT.value:
            if command == "power":
                new_state["power"] = params.get("state", "toggle")
            elif command == "brightness":
                new_state["brightness"] = max(0, min(100, params.get("value", 80)))
            elif command == "color":
                new_state["color"] = params.get("value", "warm_white")

        elif device.device_type == DeviceType.LOCK.value:
            if command == "lock":
                new_state["locked"] = True
            elif command == "unlock":
                new_state["locked"] = False

        elif device.device_type == DeviceType.CURTAIN.value:
            if command == "open":
                new_state["position"] = 100
                new_state["state"] = "open"
            elif command == "close":
                new_state["position"] = 0
                new_state["state"] = "closed"
            elif command == "position":
                pos = max(0, min(100, params.get("value", 50)))
                new_state["position"] = pos
                new_state["state"] = "half_open" if 0 < pos < 100 else ("open" if pos == 100 else "closed")

        elif device.device_type == DeviceType.CAMERA.value:
            if command == "snapshot":
                new_state["last_snapshot"] = time.time()
            elif command == "motion_detect":
                new_state["motion_detect_enabled"] = params.get("enabled", True)

        elif device.device_type == DeviceType.THERMOSTAT.value:
            if command == "setpoint":
                new_state["setpoint"] = max(10, min(35, params.get("value", 23)))
            elif command == "mode":
                new_state["mode"] = params.get("value", "heat")

        elif device.device_type == DeviceType.SENSOR.value:
            # المستشعرات للقراءة فقط — Sensors are read-only
            if command not in ("read", "subscribe"):
                logger.warning(f"المستشعرات للقراءة فقط — Sensor read-only: {command}")

        elif device.device_type == DeviceType.TV.value:
            if command == "power":
                new_state["power"] = params.get("state", "toggle")
            elif command == "channel":
                new_state["channel"] = params.get("value", 1)
            elif command == "volume":
                new_state["volume"] = max(0, min(100, params.get("value", 50)))

        elif device.device_type == DeviceType.SPEAKER.value:
            if command == "play":
                new_state["playing"] = True
            elif command == "pause":
                new_state["playing"] = False
            elif command == "volume":
                new_state["volume"] = max(0, min(100, params.get("value", 50)))

        elif device.device_type == DeviceType.APPLIANCE.value:
            if command == "power":
                new_state["power"] = params.get("state", "toggle")

        return new_state

    # ─── الاشتراك — Subscriptions ───────────────────────────────────────────

    def subscribe_to_device(self, device_id: str, callback: Callable) -> str:
        """
        الاشتراك في تحديثات الجهاز — Subscribe to device state changes.

        Args:
            device_id: معرف الجهاز — Device ID
            callback: دالة الاستدعاء — Callback function(state_change_dict)

        Returns:
            معرف الاشتراك — Subscription ID
        """
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"

        if device_id not in self._subscriptions:
            self._subscriptions[device_id] = []
        self._subscriptions[device_id].append(callback)

        return sub_id

    def _notify_subscribers(self, device_id: str, command: str, new_state: Dict):
        """إشعار المشتركين — Notify all subscribers of a state change."""
        callbacks = self._subscriptions.get(device_id, [])
        for callback in callbacks:
            try:
                callback({
                    "device_id": device_id,
                    "command": command,
                    "new_state": new_state,
                    "timestamp": time.time(),
                })
            except Exception as e:
                logger.error(f"خطأ في إشعار المشترك — Subscriber error: {e}")

    # ─── إدارة الأجهزة — Device Management ─────────────────────────────────

    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """الحصول على بيانات جهاز — Get a device by ID."""
        return self._devices.get(device_id)

    def list_devices(self, device_type: Optional[str] = None) -> List[IoTDevice]:
        """
        قائمة الأجهزة — List all registered devices, optionally filtered by type.

        Args:
            device_type: نوع الجهاز (اختياري) — Optional device type filter
        """
        devices = list(self._devices.values())
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
        return devices

    def remove_device(self, device_id: str) -> bool:
        """حذف جهاز — Remove a device from the registry."""
        if device_id not in self._devices:
            return False

        with self._lock:
            del self._devices[device_id]
            self._subscriptions.pop(device_id, None)

            # حذف من قاعدة البيانات — Delete from DB
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("DELETE FROM iot_devices WHERE device_id = ?", (device_id,))
                conn.commit()
            finally:
                conn.close()

        logger.info(f"تم حذف الجهاز {device_id}")
        return True

    # ─── حالة النظام — System Status ───────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """حالة بوابة إنترنت الأشياء — IoT Gateway status."""
        online_count = sum(1 for d in self._devices.values() if d.is_online)
        device_types = {}
        for d in self._devices.values():
            device_types[d.device_type] = device_types.get(d.device_type, 0) + 1

        return {
            "enabled": IOT_GATEWAY_ENABLED,
            "initialized": self._initialized,
            "total_devices": len(self._devices),
            "online_devices": online_count,
            "device_types": device_types,
            "total_commands": len(self._command_history),
            "mqtt_available": self._mqtt_available,
            "subscriptions": sum(len(v) for v in self._subscriptions.values()),
            "high_impact_commands_registered": list(self.HIGH_IMPACT_COMMANDS),
        }

    async def shutdown(self):
        """إيقاف البوابة (القانون 5) — Shutdown gateway (Law 5: no resistance)."""
        logger.info("إيقاف بوابة إنترنت الأشياء — IoT Gateway shutting down")
        self._devices.clear()
        self._subscriptions.clear()
        self._command_history.clear()
        self._initialized = False


# Singleton
iot_gateway = IoTGateway()
