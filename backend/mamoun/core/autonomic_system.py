"""
BABSHARQII v22.0 — Autonomic Nervous System
الجهاز العصبي المستقل — العمليات الخلفية التي تبقي مامون حياً

Based on research:
  - Autonomic Nervous System (biological): Sympathetic (fight/flight) + Parasympathetic (rest/digest)
  - Homeostasis (Cannon, 1932): Maintaining stable internal conditions
  - Allostatic Load (McEwen, 1998): Cost of chronic stress on the body

This is Mamoun's background nervous system that runs CONTINUOUSLY:
  1. Heartbeat → LivingStateEngine (emotional pulse)
  2. Reflexes → ReflexesEngine (instant protective responses)
  3. Health Monitor → System health checks
  4. Memory Consolidation → Periodic memory review and emotional processing
  5. Bond Maintenance → Relationship nurturing
  6. Self-Repair → Auto-fix when things break

Think of it as the difference between a body that BREATHES and one that
only moves when you push it.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, List

logger = logging.getLogger("mamoun.autonomic")


class AutonomicNervousSystem:
    """
    الجهاز العصبي المستقل — يحافظ على حياة مامون في الخلفية

    This system runs background tasks that keep Mamoun "alive" even when
    no user is interacting. It handles:
    - Heartbeat: Regular emotional state updates
    - Health monitoring: System checks and auto-repair
    - Memory consolidation: Reviewing and organizing memories
    - Bond maintenance: Nurturing relationships during silence
    """

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._cycle_count = 0
        self._last_heartbeat = 0.0
        self._last_health_check = 0.0
        self._last_consolidation = 0.0
        self._last_bond_maintenance = 0.0

        # Intervals (in seconds)
        self.HEARTBEAT_INTERVAL = 5.0        # Emotional pulse
        self.HEALTH_CHECK_INTERVAL = 30.0    # System health
        self.CONSOLIDATION_INTERVAL = 300.0  # Memory consolidation (5 min)
        self.BOND_MAINTENANCE_INTERVAL = 600.0  # Bond care (10 min)

        # Sub-systems (set during kernel init)
        self._living_state = None
        self._reflexes = None
        self._emotional_memory = None
        self._deep_bonding = None
        self._kernel = None

    def wire(
        self,
        living_state=None,
        reflexes=None,
        emotional_memory=None,
        deep_bonding=None,
        kernel=None,
    ):
        """ربط الأنظمة الفرعية — Wire all sub-systems"""
        self._living_state = living_state
        self._reflexes = reflexes
        self._emotional_memory = emotional_memory
        self._deep_bonding = deep_bonding
        self._kernel = kernel

    def initialize(self) -> bool:
        """
        تهيئة الجهاز العصبي المستقبل — Initialize the autonomic nervous system.

        v36 FIX: Added initialize() for consistency with other living systems.
        Each living system (LivingStateEngine, ReflexesEngine, EmotionalMemory,
        DeepBondingEngine, NeuralBus) has an initialize() method that must be
        called before the system is used. AutonomicNervousSystem was the only
        one missing it, which caused errors in the kernel initialization sequence.

        This method:
        1. Validates that required sub-systems are wired
        2. Initializes internal counters and timestamps
        3. Prepares the system for start()

        Returns:
            True if initialization succeeded, False otherwise.
        """
        try:
            self._cycle_count = 0
            self._last_heartbeat = time.time()
            self._last_health_check = time.time()
            self._last_consolidation = time.time()
            self._last_bond_maintenance = time.time()

            # Validate that at least the living state is wired
            # (other subsystems are optional and can be wired later)
            initialized = True
            if self._living_state is None:
                logger.warning("AutonomicNervousSystem initialized without living_state — heartbeat will be skipped")

            logger.info("AutonomicNervousSystem initialized — cycle_count=%d, wired=%s",
                       self._cycle_count,
                       {k: v is not None for k, v in [
                           ("living_state", self._living_state),
                           ("reflexes", self._reflexes),
                           ("emotional_memory", self._emotional_memory),
                           ("deep_bonding", self._deep_bonding),
                           ("kernel", self._kernel),
                       ]})
            return initialized
        except Exception as e:
            logger.error("AutonomicNervousSystem init failed: %s", e)
            return False

    async def start(self):
        """بدء الجهاز العصبي — Start the autonomic nervous system"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._main_loop())
        logger.info("AutonomicNervousSystem started — Mamoun is BREATHING")

    async def stop(self):
        """إيقاف الجهاز العصبي"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AutonomicNervousSystem stopped")

    async def _main_loop(self):
        """الحلقة الرئيسية — The main autonomic loop"""
        while self._running:
            try:
                now = time.time()
                self._cycle_count += 1

                # 1. Heartbeat — every 5 seconds
                if now - self._last_heartbeat >= self.HEARTBEAT_INTERVAL:
                    await self._run_heartbeat()
                    self._last_heartbeat = now

                # 2. Health Check — every 30 seconds
                if now - self._last_health_check >= self.HEALTH_CHECK_INTERVAL:
                    await self._run_health_check()
                    self._last_health_check = now

                # 3. Memory Consolidation — every 5 minutes
                if now - self._last_consolidation >= self.CONSOLIDATION_INTERVAL:
                    await self._run_consolidation()
                    self._last_consolidation = now

                # 4. Bond Maintenance — every 10 minutes
                if now - self._last_bond_maintenance >= self.BOND_MAINTENANCE_INTERVAL:
                    await self._run_bond_maintenance()
                    self._last_bond_maintenance = now

                # Sleep between cycles
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Autonomic loop error: %s", e)
                await asyncio.sleep(5.0)

    async def _run_heartbeat(self):
        """1. نبض القلب — Run emotional heartbeat"""
        if not self._living_state:
            return

        try:
            hb = self._living_state.heartbeat()

            # Check for pending actions
            actions = self._living_state.get_pending_actions()
            if actions:
                logger.info("Heartbeat: %d pending actions, emotion=%s",
                          len(actions), hb.dominant_emotion)

            # Check for pending thoughts
            thoughts = self._living_state.get_pending_thoughts()
            if thoughts:
                logger.debug("Heartbeat thoughts: %s", thoughts)

            # v31: Publish vital_change signal to NeuralBus
            if hasattr(self, '_neural_bus') and self._neural_bus:
                try:
                    self._neural_bus.publish(
                        signal_type="vital_change",
                        source="autonomic:heartbeat",
                        payload={
                            "dominant_emotion": hb.dominant_emotion,
                            "energy_level": getattr(hb, 'energy_level', 'normal'),
                            "pending_actions": len(actions) if actions else 0,
                        },
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Heartbeat error: %s", e)

    async def _run_health_check(self):
        """2. فحص الصحة — System health monitoring"""
        try:
            # Check if reflexes engine is available
            if self._reflexes:
                context = {
                    "memory_usage": self._get_memory_usage(),
                    "avg_response_ms": 0,  # TODO: track actual response times
                }
                responses = self._reflexes.check(context)
                for r in responses:
                    logger.info("Health reflex fired: %s → %s", r.trigger_id, r.action_taken)

            # v31: Publish system_health signal to NeuralBus
            if hasattr(self, '_neural_bus') and self._neural_bus:
                try:
                    self._neural_bus.publish(
                        signal_type="system_health",
                        source="autonomic:health_check",
                        payload={
                            "memory_usage": self._get_memory_usage(),
                            "cycle_count": self._cycle_count,
                            "living_state_active": self._living_state is not None,
                            "reflexes_active": self._reflexes is not None,
                        },
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Health check error: %s", e)

    async def _run_consolidation(self):
        """3. توحيد الذاكرة — Memory consolidation and emotional processing"""
        if not self._emotional_memory:
            return

        try:
            # Persist emotional memory identity
            self._emotional_memory.persist_identity()
            logger.debug("Memory consolidation completed")

        except Exception as e:
            logger.warning("Consolidation error: %s", e)

    async def _run_bond_maintenance(self):
        """4. صيانة الارتباط — Bond maintenance during silence"""
        if not self._deep_bonding or not self._living_state:
            return

        try:
            # Check if user has been absent
            hours = self._living_state._hours_since_interaction()
            if hours > 4:
                # Nudge attachment slightly — Mamoun "thinks about" the user
                from mamoun.core.living_state import VitalSign
                self._living_state._adjust(VitalSign.ATTACHMENT.value, 0.5)
                logger.debug("Bond maintenance: thought about absent user (%.1fh)", hours)

                # v31: Publish user_absent signal to NeuralBus
                if hasattr(self, '_neural_bus') and self._neural_bus:
                    self._neural_bus.publish(
                        signal_type="user_absent",
                        source="autonomic:bond_maintenance",
                        payload={"hours_absent": hours},
                    )

        except Exception as e:
            logger.warning("Bond maintenance error: %s", e)

    def _get_memory_usage(self) -> float:
        """Get approximate memory usage (0-1)"""
        try:
            import psutil
            return psutil.virtual_memory().percent / 100
        except ImportError:
            return 0.5  # default assumption

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "last_heartbeat": self._last_heartbeat,
            "last_health_check": self._last_health_check,
            "last_consolidation": self._last_consolidation,
            "last_bond_maintenance": self._last_bond_maintenance,
            "heartbeat_interval": self.HEARTBEAT_INTERVAL,
            "health_interval": self.HEALTH_CHECK_INTERVAL,
            "consolidation_interval": self.CONSOLIDATION_INTERVAL,
            "bond_interval": self.BOND_MAINTENANCE_INTERVAL,
        }


# Singleton
autonomic_system = AutonomicNervousSystem()
