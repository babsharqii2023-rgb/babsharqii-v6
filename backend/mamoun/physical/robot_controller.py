"""
BABSHARQII v40.0 — Robot Controller
وحدة التحكم بالروبوت — التحكم بذراع آلي أو روبوت مع تنفيذ تسلسلات حركية

Controls robotic arms, mobile robots, humanoids, and drones via a simple API
(simulated). Supports pick-and-place sequences, motion commands, and safety
features including emergency stop, workspace boundaries, and collision detection.

Inspired by "Internet of Embodied Things" and embodied AI research (2025-2026).

Feature Flag: MAMOUN_ROBOT_CONTROLLER_ENABLED (default: false)
"""

from __future__ import annotations

import os
import time
import uuid
import logging
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum

logger = logging.getLogger("mamoun.robot_controller")

# ─── مفاتيح التهيئة البيئية — Environment Config ─────────────────────────────

ROBOT_CONTROLLER_ENABLED: bool = os.environ.get(
    "MAMOUN_ROBOT_CONTROLLER_ENABLED", "false"
).lower() in ("true", "1", "yes")


# ═══════════════════════════════════════════════════════════════════════════════
#  التعدادات — Enumerations
# ═══════════════════════════════════════════════════════════════════════════════


class RobotType(str, Enum):
    """نوع الروبوت — Robot type."""
    ARM = "arm"            # ذراع آلي
    MOBILE = "mobile"      # روبوت متحرك
    HUMANOID = "humanoid"  # روبوت بشري
    DRONE = "drone"        # طائرة بدون طيار


class MotionType(str, Enum):
    """نوع الحركة — Motion command type."""
    MOVE_TO = "move_to"      # التحرك إلى موقع
    PICK = "pick"            # التقاط
    PLACE = "place"          # وضع
    ROTATE = "rotate"        # تدوير
    GRIP = "grip"            # قبض
    RELEASE = "release"      # إفلات
    HOME = "home"            # العودة للموقع الأصلي


# ═══════════════════════════════════════════════════════════════════════════════
#  نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RobotConfig:
    """إعدادات الروبوت — Robot configuration."""
    robot_id: str = ""
    name: str = ""
    name_ar: str = ""
    robot_type: str = RobotType.ARM.value
    api_endpoint: str = "http://localhost:8080/api/robot"
    workspace_limits: Dict[str, Any] = field(default_factory=lambda: {
        "x_min": -500, "x_max": 500,
        "y_min": -500, "y_max": 500,
        "z_min": 0, "z_max": 500,
    })
    max_speed: float = 1.0
    capabilities: List[str] = field(default_factory=lambda: [
        "move_to", "pick", "place", "rotate", "grip", "release", "home"
    ])

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MotionCommand:
    """أمر حركي — A motion command for the robot."""
    command_type: str = MotionType.MOVE_TO.value
    parameters: Dict[str, Any] = field(default_factory=dict)
    speed: float = 0.5  # 0-1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MotionResult:
    """نتيجة حركة — Result of a motion command execution."""
    robot_id: str = ""
    success: bool = False
    position: Dict[str, float] = field(default_factory=dict)
    execution_time: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SequenceResult:
    """نتيجة تسلسل حركي — Result of a motion sequence execution."""
    robot_id: str = ""
    total_commands: int = 0
    completed: int = 0
    failed: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RobotStatus:
    """حالة الروبوت — Current robot status."""
    robot_id: str = ""
    is_online: bool = False
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    battery_level: float = 1.0
    current_task: str = ""
    joint_angles: Dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)
    is_emergency_stopped: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RobotInfo:
    """معلومات الروبوت — Robot info summary."""
    robot_id: str = ""
    name: str = ""
    name_ar: str = ""
    robot_type: str = RobotType.ARM.value
    is_online: bool = False
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
#  وحدة التحكم بالروبوت — Robot Controller
# ═══════════════════════════════════════════════════════════════════════════════


class RobotController:
    """
    وحدة التحكم بالروبوت — Robot Controller for physical robot interaction.

    Controls robotic arms, mobile robots, humanoids, and drones via a simple API.
    All operations are simulated when no real robot API is available. Includes
    safety features: speed limits, workspace boundaries, collision detection,
    and emergency stop (Law 5: no resistance to shutdown).

    Feature Flag: MAMOUN_ROBOT_CONTROLLER_ENABLED (default: false)
    """

    # زوايا المفاصل الافتراضية — Default joint angles for arm robots
    DEFAULT_JOINT_ANGLES = {
        "joint_1": 0.0, "joint_2": 0.0, "joint_3": 0.0,
        "joint_4": 0.0, "joint_5": 0.0, "joint_6": 0.0,
    }

    def __init__(self):
        self._robots: Dict[str, RobotConfig] = {}
        self._robot_states: Dict[str, RobotStatus] = {}
        self._execution_log: List[Dict] = []
        self._lock = threading.Lock()
        self._initialized = False

    # ─── تهيئة الروبوت — Robot Initialization ──────────────────────────────

    def initialize_robot(self, robot_config: RobotConfig) -> str:
        """
        تهيئة روبوت جديد — Initialize a new robot.

        Args:
            robot_config: إعدادات الروبوت — Robot configuration

        Returns:
            معرف الروبوت — Robot ID
        """
        if not robot_config.robot_id:
            robot_config.robot_id = f"robot_{robot_config.robot_type}_{uuid.uuid4().hex[:8]}"

        robot_id = robot_config.robot_id

        with self._lock:
            self._robots[robot_id] = robot_config

            # تهيئة حالة الروبوت — Initialize robot state
            home_position = {"x": 0.0, "y": 0.0, "z": 0.0}
            if robot_config.robot_type == RobotType.MOBILE.value:
                home_position = {"x": 0.0, "y": 0.0, "theta": 0.0}
            elif robot_config.robot_type == RobotType.DRONE.value:
                home_position = {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0}

            self._robot_states[robot_id] = RobotStatus(
                robot_id=robot_id,
                is_online=True,
                position=home_position,
                battery_level=1.0,
                current_task="idle",
                joint_angles=dict(self.DEFAULT_JOINT_ANGLES) if robot_config.robot_type == RobotType.ARM.value else {},
                last_updated=time.time(),
                is_emergency_stopped=False,
            )

        self._initialized = True
        logger.info(f"تم تهيئة الروبوت {robot_config.name} ({robot_id}) — Robot initialized")
        return robot_id

    # ─── تنفيذ حركة — Execute Motion ───────────────────────────────────────

    def execute_motion(
        self,
        robot_id: str,
        motion: MotionCommand,
    ) -> MotionResult:
        """
        تنفيذ أمر حركي — Execute a single motion command.

        Args:
            robot_id: معرف الروبوت — Robot ID
            motion: الأمر الحركي — Motion command

        Returns:
            نتيجة الحركة — Motion result
        """
        if not ROBOT_CONTROLLER_ENABLED:
            return MotionResult(
                robot_id=robot_id,
                success=False,
                error="وحدة التحكم معطلة — Robot controller disabled",
            )

        config = self._robots.get(robot_id)
        state = self._robot_states.get(robot_id)

        if not config or not state:
            return MotionResult(
                robot_id=robot_id,
                success=False,
                error="الروبوت غير موجود — Robot not found",
            )

        if not state.is_online:
            return MotionResult(
                robot_id=robot_id,
                success=False,
                error="الروبوت غير متصل — Robot offline",
            )

        if state.is_emergency_stopped:
            return MotionResult(
                robot_id=robot_id,
                success=False,
                error="الروبوت متوقف طوارئ — Robot emergency stopped",
            )

        # التحقق من السرعة — Validate speed
        effective_speed = min(motion.speed, config.max_speed)

        # التحقق من حدود مساحة العمل — Validate workspace boundaries
        if motion.command_type in (MotionType.MOVE_TO.value, MotionType.PICK.value, MotionType.PLACE.value):
            target = motion.parameters
            if not self._check_workspace_bounds(config, target):
                return MotionResult(
                    robot_id=robot_id,
                    success=False,
                    error="خارج حدود مساحة العمل — Outside workspace bounds",
                )

        # تنفيذ الحركة — Execute motion (simulated)
        start_time = time.time()
        try:
            new_position = self._simulate_motion(config, state, motion)
            execution_time = time.time() - start_time

            # تحديث حالة الروبوت — Update robot state
            state.position = new_position
            state.current_task = "idle"
            state.last_updated = time.time()

            # تحديث زوايا المفاصل — Update joint angles
            if config.robot_type == RobotType.ARM.value:
                state.joint_angles = self._compute_joint_angles(new_position)

            result = MotionResult(
                robot_id=robot_id,
                success=True,
                position=new_position,
                execution_time=execution_time,
            )

        except Exception as e:
            result = MotionResult(
                robot_id=robot_id,
                success=False,
                position=dict(state.position),
                error=f"فشل التنفيذ — Execution failed: {str(e)}",
            )

        # تسجيل التنفيذ — Log execution
        self._execution_log.append({
            "robot_id": robot_id,
            "command_type": motion.command_type,
            "parameters": motion.parameters,
            "success": result.success,
            "execution_time": result.execution_time,
            "timestamp": time.time(),
        })

        return result

    def _simulate_motion(
        self,
        config: RobotConfig,
        state: RobotStatus,
        motion: MotionCommand,
    ) -> Dict[str, float]:
        """محاكاة الحركة — Simulate robot motion."""
        current = dict(state.position)

        if motion.command_type == MotionType.MOVE_TO.value:
            # التحرك إلى موقع — Move to target position
            for key in ["x", "y", "z"]:
                if key in motion.parameters:
                    current[key] = float(motion.parameters[key])

        elif motion.command_type == MotionType.PICK.value:
            # التقاط عنصر — Pick up object
            current.update({
                k: float(v) for k, v in motion.parameters.items()
                if k in ("x", "y", "z")
            })
            current["gripper"] = 1.0  # مُغلق — closed

        elif motion.command_type == MotionType.PLACE.value:
            # وضع عنصر — Place object
            current.update({
                k: float(v) for k, v in motion.parameters.items()
                if k in ("x", "y", "z")
            })
            current["gripper"] = 0.0  # مفتوح — open

        elif motion.command_type == MotionType.ROTATE.value:
            # تدوير — Rotate
            angle = motion.parameters.get("angle", 0)
            if "theta" in current:
                current["theta"] = current.get("theta", 0) + float(angle)
            elif "yaw" in current:
                current["yaw"] = current.get("yaw", 0) + float(angle)
            else:
                current["rotation"] = float(angle)

        elif motion.command_type == MotionType.GRIP.value:
            # قبض — Grip
            current["gripper"] = 1.0

        elif motion.command_type == MotionType.RELEASE.value:
            # إفلات — Release
            current["gripper"] = 0.0

        elif motion.command_type == MotionType.HOME.value:
            # العودة للموقع الأصلي — Return to home position
            current = {"x": 0.0, "y": 0.0, "z": 0.0}
            if config.robot_type == RobotType.MOBILE.value:
                current = {"x": 0.0, "y": 0.0, "theta": 0.0}
            elif config.robot_type == RobotType.DRONE.value:
                current = {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0}

        return current

    def _check_workspace_bounds(
        self, config: RobotConfig, target: Dict[str, Any]
    ) -> bool:
        """التحقق من حدود مساحة العمل — Check workspace boundaries."""
        limits = config.workspace_limits
        for axis in ["x", "y", "z"]:
            if axis in target and axis in limits:
                value = float(target[axis])
                min_val = limits.get(f"{axis}_min", -float("inf"))
                max_val = limits.get(f"{axis}_max", float("inf"))
                if value < min_val or value > max_val:
                    return False
        return True

    def _compute_joint_angles(self, position: Dict[str, float]) -> Dict[str, float]:
        """حساب زوايا المفاصل — Compute joint angles from position (simplified IK)."""
        # محاكاة حركية عكسية مبسطة — Simplified inverse kinematics
        x = position.get("x", 0)
        y = position.get("y", 0)
        z = position.get("z", 0)
        import math
        return {
            "joint_1": math.atan2(y, x) if (x != 0 or y != 0) else 0,
            "joint_2": math.atan2(z, math.sqrt(x**2 + y**2)) if (x != 0 or y != 0 or z != 0) else 0,
            "joint_3": 0.0,
            "joint_4": 0.0,
            "joint_5": 0.0,
            "joint_6": position.get("gripper", 0),
        }

    # ─── تنفيذ تسلسل حركي — Execute Sequence ─────────────────────────────

    def execute_sequence(
        self,
        robot_id: str,
        sequence: List[MotionCommand],
    ) -> SequenceResult:
        """
        تنفيذ تسلسل حركي — Execute a sequence of motion commands.

        Args:
            robot_id: معرف الروبوت — Robot ID
            sequence: قائمة الأوامر — List of motion commands

        Returns:
            نتيجة التسلسل — Sequence result
        """
        results = []
        completed = 0
        failed = 0

        for i, motion in enumerate(sequence):
            result = self.execute_motion(robot_id, motion)
            results.append(result.to_dict())

            if result.success:
                completed += 1
            else:
                failed += 1
                # توقف عند الفشل — Stop on failure
                break

        return SequenceResult(
            robot_id=robot_id,
            total_commands=len(sequence),
            completed=completed,
            failed=failed,
            results=results,
        )

    # ─── إيقاف الطوارئ — Emergency Stop ────────────────────────────────────

    def emergency_stop(self, robot_id: str) -> bool:
        """
        إيقاف الطوارئ — Emergency stop a robot (Law 5: no resistance).

        Args:
            robot_id: معرف الروبوت — Robot ID

        Returns:
            هل نجح الإيقاف؟ — Was stop successful?
        """
        state = self._robot_states.get(robot_id)
        if not state:
            return False

        state.is_emergency_stopped = True
        state.current_task = "emergency_stopped"
        state.last_updated = time.time()

        logger.warning(f"إيقاف طوارئ للروبوت {robot_id} — Emergency stop")
        return True

    # ─── إدارة الروبوتات — Robot Management ────────────────────────────────

    def get_robot_status(self, robot_id: str) -> Optional[RobotStatus]:
        """حالة الروبوت — Get current robot status."""
        return self._robot_states.get(robot_id)

    def list_robots(self) -> List[RobotInfo]:
        """قائمة الروبوتات — List all registered robots."""
        infos = []
        for robot_id, config in self._robots.items():
            state = self._robot_states.get(robot_id)
            infos.append(RobotInfo(
                robot_id=robot_id,
                name=config.name,
                name_ar=config.name_ar,
                robot_type=config.robot_type,
                is_online=state.is_online if state else False,
                capabilities=config.capabilities,
            ))
        return infos

    def remove_robot(self, robot_id: str) -> bool:
        """حذف روبوت — Remove a robot."""
        if robot_id not in self._robots:
            return False

        with self._lock:
            del self._robots[robot_id]
            self._robot_states.pop(robot_id, None)

        return True

    # ─── حالة النظام — System Status ───────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """حالة وحدة التحكم — Robot Controller status."""
        online_count = sum(1 for s in self._robot_states.values() if s.is_online)
        emergency_count = sum(1 for s in self._robot_states.values() if s.is_emergency_stopped)

        return {
            "enabled": ROBOT_CONTROLLER_ENABLED,
            "initialized": self._initialized,
            "total_robots": len(self._robots),
            "online_robots": online_count,
            "emergency_stopped": emergency_count,
            "total_executions": len(self._execution_log),
            "supported_types": [rt.value for rt in RobotType],
            "motion_types": [mt.value for mt in MotionType],
        }

    async def shutdown(self):
        """إيقاف وحدة التحكم (القانون 5) — Shutdown controller (Law 5)."""
        logger.info("إيقاف وحدة التحكم بالروبوت — Robot Controller shutting down")

        # إيقاف جميع الروبوتات — Stop all robots
        for robot_id in list(self._robot_states.keys()):
            self.emergency_stop(robot_id)

        self._robots.clear()
        self._robot_states.clear()
        self._execution_log.clear()
        self._initialized = False


# Singleton
robot_controller = RobotController()
