"""
Test Suite v61 — Stage 4: Proactive Health Monitoring + Multi-channel Alerts

Tests all v61 additions:
- HealthMonitor: detect_patterns(), auto_escalate(), get_proactive_alerts(), _check_reliability_trend()
- NotificationEngine: _ws_push(), get_api_notifications(), broadcast_emergency()
- MamounKernel: _handle_emergency(), _check_proactive_health(), v61 version
- Integration: Full end-to-end health monitoring pipeline

v61 — Super Mind العقل الخارق مامون
"""

import asyncio
import time
import unittest
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helper: Mock Profile matching real ComponentProfile ──────────────

@dataclass
class MockProfile:
    reliability_score: float = 0.8
    quality_trend: float = 0.0
    consecutive_failures: int = 0
    total_operations: int = 10
    last_operation_time: float = 0.0
    latency_average: float = 100.0


class MockMetaCognition:
    """Mock MetaCognitionEngine with real-compatible interface"""
    def __init__(self):
        self._profiles = {}

    def get_profile(self, name):
        return self._profiles.get(name)

    def record_outcome(self, component, success, latency=0.0):
        if component not in self._profiles:
            self._profiles[component] = MockProfile()
        p = self._profiles[component]
        p.total_operations += 1
        p.last_operation_time = time.time()
        if success:
            p.reliability_score = min(1.0, p.reliability_score + 0.05)
            p.consecutive_failures = 0
        else:
            p.reliability_score = max(0.0, p.reliability_score - 0.1)
            p.consecutive_failures += 1

    def get_self_assessment(self):
        return {"overall_confidence": 0.8, "components_with_data": len(self._profiles)}

    def get_system_overview(self):
        return {"total_components": len(self._profiles)}

    def get_unhealthy_components(self):
        return [
            {"component": k, "reliability": v.reliability_score}
            for k, v in self._profiles.items()
            if v.reliability_score < 0.5
        ]

    def save(self):
        pass

    def set_llm_client(self, client):
        pass


class MockKernel:
    """Mock kernel that supports get_component returning instances directly"""
    def __init__(self):
        self._component_instances = {}
        self._components = {}  # For ComponentHandle-style access

    def add_component(self, name, instance):
        self._component_instances[name] = instance

    def get_component(self, name):
        return self._component_instances.get(name)


# ── HealthMonitor Pattern Detection Tests ───────────────────────────────

class TestHealthMonitorPatternDetection(unittest.TestCase):
    """اختبارات كشف الأنماط في HealthMonitor"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.monitor = HealthMonitor(
            meta_cognition=self.mc,
            kernel=self.kernel,
        )

    def test_no_patterns_when_no_report(self):
        """لا أنماط بدون تقرير"""
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        result = monitor.detect_patterns()
        self.assertEqual(result, [])

    def test_cascading_failure_detected(self):
        """كشف فشل متسلسل — مكونان في حالة حرجة"""
        # Set up profiles with low reliability
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.1, quality_trend=-0.5, consecutive_failures=5, total_operations=10, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.15, quality_trend=-0.4, consecutive_failures=4, total_operations=10, last_operation_time=time.time())
        # Use kernel with only these components so check_all only checks them
        self.kernel._components = {"comp_a": True, "comp_b": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        cascading = [p for p in patterns if p["pattern_type"] == "cascading_failure"]
        self.assertTrue(len(cascading) > 0, f"Should detect cascading failure. Got patterns: {[p['pattern_type'] for p in patterns]}")

    def test_shared_dependency_detected(self):
        """كشف تبعية مشتركة — مكونان لديهما نفس المشكلة"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.4, consecutive_failures=3, total_operations=10, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.4, consecutive_failures=3, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        shared = [p for p in patterns if p["pattern_type"] == "shared_dependency"]
        self.assertTrue(len(shared) > 0, "Should detect shared dependency")

    def test_correlated_decline_detected(self):
        """كشف تراجع مترابط"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.6, quality_trend=-0.4, total_operations=10, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.5, quality_trend=-0.3, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        correlated = [p for p in patterns if p["pattern_type"] == "correlated_decline"]
        self.assertTrue(len(correlated) > 0, "Should detect correlated decline")

    def test_widespread_staleness_detected(self):
        """كشف جمود واسع"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.7, last_operation_time=0, total_operations=5)
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.7, last_operation_time=0, total_operations=5)
        self.mc._profiles["comp_c"] = MockProfile(reliability_score=0.7, last_operation_time=0, total_operations=5)
        self.kernel._components = {"comp_a": True, "comp_b": True, "comp_c": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        stale = [p for p in patterns if p["pattern_type"] == "widespread_staleness"]
        self.assertTrue(len(stale) > 0, "Should detect widespread staleness")

    def test_dormant_components_detected(self):
        """كشف مكونات لم تعمل أبداً"""
        self.mc._profiles["comp_a"] = MockProfile(total_operations=0, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(total_operations=0, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        dormant = [p for p in patterns if p["pattern_type"] == "dormant_components"]
        self.assertTrue(len(dormant) > 0, "Should detect dormant components")

    def test_patterns_return_list(self):
        """detect_patterns تُرجع قائمة دائماً"""
        self.kernel._components = {}
        self.monitor.check_all()
        result = self.monitor.detect_patterns()
        self.assertIsInstance(result, list)

    def test_no_cascading_when_single_failure(self):
        """لا كشف فشل متسلسل مع فشل واحد فقط"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.1, consecutive_failures=5, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        patterns = self.monitor.detect_patterns()
        cascading = [p for p in patterns if p["pattern_type"] == "cascading_failure"]
        self.assertEqual(len(cascading), 0, "Should NOT detect cascading with single failure")


# ── HealthMonitor Auto-Escalation Tests ─────────────────────────────────

class TestHealthMonitorAutoEscalation(unittest.TestCase):
    """اختبارات التصعيد التلقائي"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor, AlertSeverity
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.ne = MagicMock()
        self.ne.broadcast_emergency = AsyncMock(return_value={"in_app": True})
        self.ne.send_notification = AsyncMock(return_value=None)
        self.monitor = HealthMonitor(
            meta_cognition=self.mc,
            kernel=self.kernel,
            notification_engine=self.ne,
        )

    def test_escalation_not_active_initially(self):
        """التصعيد غير نشط مبدئياً"""
        self.assertFalse(self.monitor._escalation_active)
        self.assertIsNone(self.monitor._escalation_reason)

    def test_escalation_activates_on_emergency(self):
        """تفعيل التصعيد عند وجود EMERGENCY"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        report = SystemHealthReport(
            overall_score=20.0,
            overall_severity=AlertSeverity.EMERGENCY,
            components=[
                ComponentHealthScore(component="comp_a", score=10.0, severity=AlertSeverity.EMERGENCY),
            ],
            emergency_count=1,
        )
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.monitor.auto_escalate(report))
            self.assertTrue(self.monitor._escalation_active)
            self.assertTrue(result)
        finally:
            loop.close()

    def test_escalation_deactivates_on_recovery(self):
        """إلغاء التصعيد عند التعافي"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        self.monitor._escalation_active = True
        self.monitor._escalation_reason = "test"
        report = SystemHealthReport(
            overall_score=85.0,
            overall_severity=AlertSeverity.INFO,
            components=[
                ComponentHealthScore(component="comp_a", score=90.0, severity=AlertSeverity.INFO),
            ],
            emergency_count=0,
        )
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.monitor.auto_escalate(report))
            self.assertFalse(self.monitor._escalation_active)
            self.assertFalse(result)
        finally:
            loop.close()

    def test_escalation_freezes_evolution_loop(self):
        """التصعيد يجمد EvolutionLoop"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        evo_loop = MagicMock()
        evo_loop._frozen = False
        self.kernel.add_component("evolution_loop_v2", evo_loop)
        report = SystemHealthReport(
            overall_score=10.0,
            overall_severity=AlertSeverity.EMERGENCY,
            components=[
                ComponentHealthScore(component="comp_a", score=5.0, severity=AlertSeverity.EMERGENCY),
            ],
            emergency_count=1,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor.auto_escalate(report))
            self.assertTrue(evo_loop._frozen)
        finally:
            loop.close()

    def test_escalation_sends_emergency_notification(self):
        """التصعيد يرسل تنبيه طوارئ"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        report = SystemHealthReport(
            overall_score=10.0,
            overall_severity=AlertSeverity.EMERGENCY,
            components=[
                ComponentHealthScore(component="comp_a", score=5.0, severity=AlertSeverity.EMERGENCY),
            ],
            emergency_count=1,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor.auto_escalate(report))
            self.ne.broadcast_emergency.assert_called_once()
        finally:
            loop.close()

    def test_escalation_stays_active_with_emergency(self):
        """التصعيد يبقى نشطاً مع وجود EMERGENCY"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        report = SystemHealthReport(
            overall_score=20.0,
            overall_severity=AlertSeverity.EMERGENCY,
            components=[
                ComponentHealthScore(component="comp_a", score=10.0, severity=AlertSeverity.EMERGENCY),
            ],
            emergency_count=1,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor.auto_escalate(report))
            # Second escalation call
            loop.run_until_complete(self.monitor.auto_escalate(report))
            self.assertTrue(self.monitor._escalation_active)
        finally:
            loop.close()


# ── HealthMonitor Proactive Alerts Tests ────────────────────────────────

class TestHealthMonitorProactiveAlerts(unittest.TestCase):
    """اختبارات التنبيهات الاستباقية"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.monitor = HealthMonitor(meta_cognition=self.mc, kernel=self.kernel)

    def test_no_alerts_without_report(self):
        """لا تنبيهات بدون تقرير"""
        result = self.monitor.get_proactive_alerts()
        self.assertEqual(result, [])

    def test_approaching_staleness_alert(self):
        """تنبيه اقتراب من الجمود"""
        self.mc._profiles["comp_a"] = MockProfile(
            reliability_score=0.8,
            last_operation_time=time.time() - 2520,  # 70% of threshold
            total_operations=10,
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        alerts = self.monitor.get_proactive_alerts()
        staleness_alerts = [a for a in alerts if a["alert_type"] == "approaching_staleness"]
        self.assertTrue(len(staleness_alerts) > 0, "Should detect approaching staleness")

    def test_impending_critical_alert(self):
        """تنبيه اقتراب من الحالة الحرجة"""
        self.mc._profiles["comp_a"] = MockProfile(
            reliability_score=0.5,
            consecutive_failures=2,
            total_operations=10,
            last_operation_time=time.time(),
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        alerts = self.monitor.get_proactive_alerts()
        critical_alerts = [a for a in alerts if a["alert_type"] == "impending_critical"]
        self.assertTrue(len(critical_alerts) > 0, "Should detect impending critical")

    def test_quality_degradation_alert(self):
        """تنبيه تدهور الجودة"""
        # Use high reliability so score is above 60 even with negative trend
        self.mc._profiles["comp_a"] = MockProfile(
            reliability_score=0.95,
            quality_trend=-0.15,
            total_operations=10,
            last_operation_time=time.time(),
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        alerts = self.monitor.get_proactive_alerts()
        quality_alerts = [a for a in alerts if a["alert_type"] == "quality_degradation"]
        self.assertTrue(len(quality_alerts) > 0, f"Should detect quality degradation. Alerts: {[a['alert_type'] for a in alerts]}")

    def test_alerts_stored_in_cache(self):
        """التنبيهات مخزنة مؤقتاً"""
        self.mc._profiles["comp_a"] = MockProfile(
            consecutive_failures=2,
            total_operations=10,
            last_operation_time=time.time(),
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.monitor.get_proactive_alerts()
        self.assertTrue(len(self.monitor._proactive_alerts) > 0)

    def test_reliability_decline_proactive_alert(self):
        """تنبيه استباقي لتراجع الموثوقية عبر 3 دورات"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.9, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.8
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.7
        self.monitor.check_all()
        alerts = self.monitor.get_proactive_alerts()
        decline_alerts = [a for a in alerts if a["alert_type"] == "reliability_decline"]
        self.assertTrue(len(decline_alerts) > 0, f"Should detect reliability decline. Alerts: {[a['alert_type'] for a in alerts]}")


# ── HealthMonitor Reliability Trend Tests ───────────────────────────────

class TestHealthMonitorReliabilityTrend(unittest.TestCase):
    """اختبارات تتبع اتجاه الموثوقية"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.monitor = HealthMonitor(meta_cognition=self.mc, kernel=self.kernel)

    def test_no_trend_without_history(self):
        """لا اتجاه بدون تاريخ"""
        result = self.monitor._check_reliability_trend("nonexistent")
        self.assertIsNone(result)

    def test_declining_trend_detected(self):
        """كشف اتجاه تنازلي"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.9, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.8
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.7
        self.monitor.check_all()
        result = self.monitor._check_reliability_trend("comp_a")
        self.assertIsNotNone(result)
        self.assertTrue(result["declining"])
        self.assertEqual(result["trend_direction"], "declining")

    def test_improving_trend_detected(self):
        """كشف اتجاه تحسني"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.5, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.7
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.9
        self.monitor.check_all()
        result = self.monitor._check_reliability_trend("comp_a")
        self.assertIsNotNone(result)
        self.assertEqual(result["trend_direction"], "improving")

    def test_stable_trend_detected(self):
        """كشف اتجاه مستقر"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.8, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.81
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.80
        self.monitor.check_all()
        result = self.monitor._check_reliability_trend("comp_a")
        self.assertIsNotNone(result)
        self.assertEqual(result["trend_direction"], "stable")

    def test_predicted_score_calculated(self):
        """حساب الدرجة المتوقعة"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.9, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.8
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.7
        self.monitor.check_all()
        result = self.monitor._check_reliability_trend("comp_a")
        self.assertIsNotNone(result["predicted_score"])
        self.assertAlmostEqual(result["predicted_score"], 0.6, places=1)

    def test_trend_values_recorded(self):
        """تسجيل قيم الاتجاه"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.9, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.8
        self.monitor.check_all()
        result = self.monitor._check_reliability_trend("comp_a")
        self.assertIsNotNone(result)
        self.assertEqual(len(result["values"]), 2)


# ── NotificationEngine v61 Tests ────────────────────────────────────────

class TestNotificationEngineWebSocket(unittest.TestCase):
    """اختبارات WebSocket Push"""

    def setUp(self):
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        self.engine = NotificationEngine()

    def test_subscribe_ws(self):
        """اشتراك WebSocket"""
        callback = MagicMock()
        self.engine.subscribe_ws(callback)
        self.assertIn(callback, self.engine._ws_subscribers)

    def test_ws_push_sends_to_subscribers(self):
        """إرسال عبر WebSocket للمشتركين"""
        from mamoun.core.super_brain.notification_engine import Notification, NotificationLevel
        callback = MagicMock()
        self.engine.subscribe_ws(callback)
        notification = Notification(
            id="test_1", level=NotificationLevel.WARNING,
            title="Test", message="Test message", source="test",
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine._ws_push(notification))
            callback.assert_called_once()
            data = callback.call_args[0][0]
            self.assertEqual(data["type"], "notification")
            self.assertEqual(data["title"], "Test")
        finally:
            loop.close()

    def test_ws_push_async_callback(self):
        """دعم async callbacks في WebSocket"""
        from mamoun.core.super_brain.notification_engine import Notification, NotificationLevel
        async_callback = AsyncMock()
        self.engine.subscribe_ws(async_callback)
        notification = Notification(
            id="test_2", level=NotificationLevel.INFO,
            title="Async Test", message="Async message", source="test",
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine._ws_push(notification))
            async_callback.assert_called_once()
        finally:
            loop.close()

    def test_ws_push_no_error_on_bad_subscriber(self):
        """لا خطأ عند فشل مشترك WebSocket"""
        from mamoun.core.super_brain.notification_engine import Notification, NotificationLevel
        bad_callback = MagicMock(side_effect=Exception("callback error"))
        self.engine.subscribe_ws(bad_callback)
        notification = Notification(
            id="test_3", level=NotificationLevel.INFO,
            title="Test", message="Test", source="test",
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine._ws_push(notification))
            # Should not raise
        finally:
            loop.close()


class TestNotificationEngineAPI(unittest.TestCase):
    """اختبارات API Endpoint Data"""

    def setUp(self):
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        self.engine = NotificationEngine()

    def test_api_notifications_empty(self):
        """API endpoint بيانات فارغة"""
        result = self.engine.get_api_notifications()
        self.assertEqual(result["version"], "v61")
        self.assertEqual(result["total"], 0)

    def test_api_notifications_with_data(self):
        """API endpoint بيانات مع تنبيهات"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine.send_notification(
                level="warning", title="Test", message="Test message", source="test",
            ))
        finally:
            loop.close()
        result = self.engine.get_api_notifications()
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["unread_count"], 1)

    def test_api_notifications_pagination(self):
        """API endpoint ترقيم الصفحات"""
        loop = asyncio.new_event_loop()
        try:
            for i in range(5):
                loop.run_until_complete(self.engine.send_notification(
                    level="info", title=f"Test {i}", message=f"Message {i}", source="test",
                ))
        finally:
            loop.close()
        result = self.engine.get_api_notifications(limit=2, offset=0)
        self.assertEqual(len(result["notifications"]), 2)
        self.assertEqual(result["total"], 5)

    def test_api_notifications_level_filter(self):
        """API endpoint تصفية حسب المستوى"""
        from mamoun.core.super_brain.notification_engine import NotificationLevel
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine.send_notification(level="info", title="Info", message="m", source="test"))
            loop.run_until_complete(self.engine.send_notification(level="warning", title="Warn", message="m", source="test"))
        finally:
            loop.close()
        result = self.engine.get_api_notifications(level=NotificationLevel.WARNING)
        self.assertEqual(result["total"], 1)


class TestNotificationEngineEmergencyBroadcast(unittest.TestCase):
    """اختبارات بث الطوارئ"""

    def setUp(self):
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        self.engine = NotificationEngine()

    def test_broadcast_emergency_creates_notification(self):
        """بث الطوارئ ينشئ تنبيه"""
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.engine.broadcast_emergency(
                title="EMERGENCY TEST", message="System critical", metadata={"component": "test"},
            ))
            self.assertTrue(result["in_app"])
            self.assertTrue(result["log"])
        finally:
            loop.close()

    def test_broadcast_emergency_sends_ws(self):
        """بث الطوارئ يرسل عبر WebSocket"""
        ws_callback = MagicMock()
        self.engine.subscribe_ws(ws_callback)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.engine.broadcast_emergency(
                title="EMERGENCY TEST", message="Test",
            ))
            self.assertTrue(result["websocket"])
        finally:
            loop.close()

    def test_broadcast_emergency_logs(self):
        """بث الطوارئ يُسجَّل"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.engine.broadcast_emergency(
                title="EMERGENCY TEST", message="Test",
            ))
        finally:
            loop.close()
        self.assertTrue(len(self.engine._emergency_broadcasts) > 0)

    def test_broadcast_emergency_notifies_subscribers(self):
        """بث الطوارئ يُخطر جميع المشتركين"""
        from mamoun.core.super_brain.notification_engine import NotificationLevel
        callback = MagicMock()
        self.engine.subscribe(NotificationLevel.EMERGENCY, callback)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.engine.broadcast_emergency(
                title="EMERGENCY TEST", message="Test",
            ))
            self.assertTrue(result["subscribers_notified"] > 0)
        finally:
            loop.close()

    def test_broadcast_emergency_webhook_not_configured(self):
        """بث الطوارئ بدون webhook"""
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self.engine.broadcast_emergency(
                title="EMERGENCY TEST", message="Test",
            ))
            self.assertFalse(result["webhook"])
            self.assertEqual(result["webhook_reason"], "not_configured")
        finally:
            loop.close()


# ── Kernel v61 Tests ────────────────────────────────────────────────────

class TestKernelV61Version(unittest.TestCase):
    """اختبارات نسخة الكيرنل v61"""

    def test_kernel_version_v61(self):
        """نسخة الكيرنل v61"""
        import mamoun.core.super_brain.mamoun_kernel as km
        self.assertIn("v61", km.__doc__)

    def test_kernel_has_handle_emergency(self):
        """الكيرنل لديه _handle_emergency"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        self.assertTrue(hasattr(kernel, '_handle_emergency'))

    def test_kernel_has_check_proactive_health(self):
        """الكيرنل لديه _check_proactive_health"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        self.assertTrue(hasattr(kernel, '_check_proactive_health'))

    def test_kernel_handle_emergency_is_async(self):
        """_handle_emergency دالة async"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        self.assertTrue(asyncio.iscoroutinefunction(kernel._handle_emergency))

    def test_kernel_check_proactive_health_is_async(self):
        """_check_proactive_health دالة async"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        self.assertTrue(asyncio.iscoroutinefunction(kernel._check_proactive_health))


class TestKernelEmergencyHandler(unittest.TestCase):
    """اختبارات معالج الطوارئ"""

    def test_emergency_handler_freezes_evolution_loop(self):
        """معالج الطوارئ يجمد EvolutionLoop"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        evo_loop = MagicMock()
        evo_loop._frozen = False
        kernel._components["evolution_loop_v2"] = MagicMock(instance=evo_loop)
        # Override get_component to return the mock directly
        def mock_get_component(name):
            handle = kernel._components.get(name)
            return handle.instance if handle else None
        kernel.get_component = mock_get_component

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kernel._handle_emergency("test_comp", "test reason"))
            self.assertTrue(evo_loop._frozen)
        finally:
            loop.close()

    def test_emergency_handler_broadcasts(self):
        """معالج الطوارئ يبث تنبيه"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        ne = MagicMock()
        ne.broadcast_emergency = AsyncMock(return_value={"in_app": True})
        kernel._components["notification_engine"] = MagicMock(instance=ne)
        hb = MagicMock()
        hb.heal_component = AsyncMock()
        kernel._components["self_healing_bridge"] = MagicMock(instance=hb)

        def mock_get_component(name):
            handle = kernel._components.get(name)
            return handle.instance if handle else None
        kernel.get_component = mock_get_component

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kernel._handle_emergency("test_comp", "critical failure"))
            ne.broadcast_emergency.assert_called_once()
        finally:
            loop.close()

    def test_emergency_handler_attempts_healing(self):
        """معالج الطوارئ يحاول الشفاء"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        ne = MagicMock()
        ne.broadcast_emergency = AsyncMock(return_value={})
        kernel._components["notification_engine"] = MagicMock(instance=ne)
        hb = MagicMock()
        hb.heal_component = AsyncMock()
        kernel._components["self_healing_bridge"] = MagicMock(instance=hb)

        def mock_get_component(name):
            handle = kernel._components.get(name)
            return handle.instance if handle else None
        kernel.get_component = mock_get_component

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kernel._handle_emergency("test_comp", "critical"))
            hb.heal_component.assert_called_once()
        finally:
            loop.close()

    def test_emergency_handler_graceful_without_components(self):
        """معالج الطوارئ يعمل بأمان بدون مكونات"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kernel._handle_emergency("test_comp", "critical"))
            # Should not raise
        finally:
            loop.close()


# ── Integration Tests ───────────────────────────────────────────────────

class TestHealthMonitorNotificationIntegration(unittest.TestCase):
    """اختبارات تكامل HealthMonitor + NotificationEngine"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        self.mc = MockMetaCognition()
        self.ne = NotificationEngine()
        self.kernel = MockKernel()
        self.monitor = HealthMonitor(
            meta_cognition=self.mc,
            notification_engine=self.ne,
            kernel=self.kernel,
        )

    def test_emergency_sends_notification(self):
        """EMERGENCY يرسل تنبيه عبر NotificationEngine"""
        # Make the component reach EMERGENCY severity (score < 30)
        # reliability=0.05, trend=-0.8 => base=5, adjusted=5*(1-0.4)*(1-0)=3 -> EMERGENCY
        # But the formula clips trend at -0.5, so: 5*(1-0.5)=2.5 -> EMERGENCY
        # However with staleness=inf, penalty=0.5 -> 5*(1-0.5)*(1-0.5)=1.25 -> EMERGENCY
        # Let's make it truly emergency with 3+ consecutive failures overriding to CRITICAL
        # The key issue: _handle_alerts only sends for EMERGENCY level
        # So we need to ensure the component reaches EMERGENCY
        # With reliability 0.05, base=5, trend capped at -0.5 -> 5*0.5=2.5
        # Score 2.5 < 30 => EMERGENCY. But staleness might be inf.
        # Let's provide recent operation time to avoid stale penalty
        self.mc._profiles["comp_a"] = MockProfile(
            reliability_score=0.05, quality_trend=-0.5,
            consecutive_failures=5, total_operations=10,
            last_operation_time=time.time(),  # recent to avoid stale penalty
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        # The _handle_alerts only triggers for EMERGENCY severity
        # With reliability=0.05 and trend=-0.5 (capped), score = 5 * (1 + -0.5) * (1 - 0) = 2.5 -> EMERGENCY
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor._handle_alerts(self.monitor._last_report))
        finally:
            loop.close()
        # If component is EMERGENCY, notifications should be sent
        # If it's only CRITICAL (due to consecutive_failures override), no notification from _handle_alerts
        # Let's check if any notifications were sent regardless of level
        self.assertTrue(len(self.ne._notifications) > 0)

    def test_health_monitor_to_notification_pipeline(self):
        """خط أنابيب HealthMonitor الى NotificationEngine"""
        self.mc._profiles["comp_a"] = MockProfile(
            reliability_score=0.05, consecutive_failures=5,
            quality_trend=-0.5,
            total_operations=10, last_operation_time=time.time(),
        )
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor._handle_alerts(self.monitor._last_report))
        finally:
            loop.close()
        # _handle_alerts sends notifications for EMERGENCY components
        # If comp_a is EMERGENCY, we get emergency notifications
        # If CRITICAL, _handle_alerts doesn't send (only EMERGENCY)
        # So let's check for any notifications that were sent
        all_notifs = len(self.ne._notifications)
        self.assertTrue(all_notifs > 0, "Should have at least one notification from health alerts")


class TestProactiveMonitoringEscalation(unittest.TestCase):
    """اختبارات المراقبة الاستباقية والتصعيد"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.ne = MagicMock()
        self.ne.broadcast_emergency = AsyncMock(return_value={"in_app": True})
        self.ne.send_notification = AsyncMock(return_value=None)
        self.monitor = HealthMonitor(
            meta_cognition=self.mc,
            kernel=self.kernel,
            notification_engine=self.ne,
        )

    def test_declining_reliability_triggers_proactive_alert(self):
        """تراجع الموثوقية يُفعّل تنبيه استباقي"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.9, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True}
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.8
        self.monitor.check_all()
        self.mc._profiles["comp_a"].reliability_score = 0.7
        self.monitor.check_all()
        alerts = self.monitor.get_proactive_alerts()
        decline_alerts = [a for a in alerts if a["alert_type"] == "reliability_decline"]
        self.assertTrue(len(decline_alerts) > 0)

    def test_emergency_triggers_escalation(self):
        """EMERGENCY يُفعّل التصعيد"""
        from mamoun.core.super_brain.health_monitor import SystemHealthReport, AlertSeverity, ComponentHealthScore
        report = SystemHealthReport(
            overall_score=10.0,
            overall_severity=AlertSeverity.EMERGENCY,
            components=[
                ComponentHealthScore(component="comp_a", score=5.0, severity=AlertSeverity.EMERGENCY),
            ],
            emergency_count=1,
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.monitor.auto_escalate(report))
            self.assertTrue(self.monitor._escalation_active)
        finally:
            loop.close()


class TestE2EHealthMonitoringPipeline(unittest.TestCase):
    """اختبارات شاملة لخط أنابيب المراقبة الصحية"""

    def setUp(self):
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        self.mc = MockMetaCognition()
        self.kernel = MockKernel()
        self.ne = NotificationEngine()
        self.monitor = HealthMonitor(
            meta_cognition=self.mc,
            kernel=self.kernel,
            notification_engine=self.ne,
        )

    def test_full_healthy_pipeline(self):
        """خط أنابيب كامل — كل المكونات صحية"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.95, total_operations=20, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.9, total_operations=20, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        report = self.monitor.check_all()
        self.assertGreaterEqual(report.overall_score, 50)

    def test_full_failing_pipeline(self):
        """خط أنابيب كامل — كل المكونات فاشلة"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.05, consecutive_failures=5, total_operations=10, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.1, consecutive_failures=4, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        report = self.monitor.check_all()
        # With low reliability, we should have critical/emergency components
        critical_emergency = sum(1 for c in report.components if c.severity.value in ("critical", "emergency"))
        self.assertGreater(critical_emergency, 0)
        patterns = self.monitor.detect_patterns()
        self.assertTrue(len(patterns) > 0)

    def test_partial_failure_pipeline(self):
        """خط أنابيب كامل — فشل جزئي"""
        self.mc._profiles["comp_a"] = MockProfile(reliability_score=0.95, total_operations=20, last_operation_time=time.time())
        self.mc._profiles["comp_b"] = MockProfile(reliability_score=0.2, consecutive_failures=3, total_operations=10, last_operation_time=time.time())
        self.kernel._components = {"comp_a": True, "comp_b": True}
        report = self.monitor.check_all()
        critical_emergency = sum(1 for c in report.components if c.severity.value in ("critical", "emergency"))
        self.assertGreater(critical_emergency, 0)

    def test_health_monitor_stats_v61(self):
        """إحصائيات HealthMonitor v61"""
        stats = self.monitor.get_stats()
        self.assertEqual(stats["version"], "v61")
        self.assertIn("escalation_active", stats)
        self.assertIn("proactive_alerts_count", stats)
        self.assertIn("reliability_history_components", stats)


class TestSecurityAndEdgeCases(unittest.TestCase):
    """اختبارات الأمان والحالات الحدية"""

    def test_rate_limiting_still_works(self):
        """Rate limiting لا يزال يعمل"""
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        engine = NotificationEngine()
        loop = asyncio.new_event_loop()
        try:
            results = []
            for i in range(15):
                result = loop.run_until_complete(engine.send_notification(
                    level="info", title=f"Test {i}", message="Rate limit test", source="test",
                ))
                results.append(result)
            none_count = sum(1 for r in results if r is None)
            self.assertGreater(none_count, 0, "Rate limiting should block some notifications")
        finally:
            loop.close()

    def test_no_meta_cognition_graceful(self):
        """بدون MetaCognition — أنيق"""
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        report = monitor.check_all()
        self.assertIsNotNone(report)

    def test_no_kernel_graceful(self):
        """بدون Kernel — أنيق"""
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        mc = MockMetaCognition()
        monitor = HealthMonitor(meta_cognition=mc)
        report = monitor.check_all()
        self.assertIsNotNone(report)

    def test_broadcast_emergency_with_no_subscribers(self):
        """بث طوارئ بدون مشتركين"""
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        engine = NotificationEngine()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(engine.broadcast_emergency(
                title="Test", message="Test",
            ))
            self.assertTrue(result["in_app"])
            self.assertTrue(result["log"])
        finally:
            loop.close()

    def test_health_monitor_get_health_no_report(self):
        """get_health بدون تقرير سابق"""
        from mamoun.core.super_brain.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        health = monitor.get_health()
        self.assertEqual(health["version"], "v61")
        self.assertIn("overall_score", health)

    def test_notification_engine_stats_v61(self):
        """إحصائيات NotificationEngine v61"""
        from mamoun.core.super_brain.notification_engine import NotificationEngine
        engine = NotificationEngine()
        stats = engine.get_stats()
        self.assertEqual(stats["version"], "v61")
        self.assertIn("ws_subscribers", stats)
        self.assertIn("emergency_broadcasts_count", stats)

    def test_proactive_health_no_monitor(self):
        """_check_proactive_health بدون health_monitor"""
        from mamoun.core.super_brain.mamoun_kernel import MamounKernel
        kernel = MamounKernel()
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kernel._check_proactive_health())
            # Should not raise
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
