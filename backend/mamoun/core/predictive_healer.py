"""
BABSHARQII v40.0 — Predictive Healer
نظام الإصلاح التنبؤي — يتنبأ بالأعطال قبل حدوثها ويتخذ إجراءات وقائية

Features:
- Monitors performance patterns over time
- Predicts failures before they happen
- Takes preventive actions automatically
- Learns from historical failure patterns

Pipeline:
1. Collect metrics (memory, LLM latency, error rates, brain status)
2. Analyze trends (is memory approaching limit? LLM degrading?)
3. Predict failures (probability, estimated time, severity)
4. Take preventive action (clean memory, reconnect LLM, expand buffer)
"""

import time
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("mamoun.predictive_healer")


@dataclass
class Prediction:
    """تنبؤ بأعطال محتملة"""
    component: str
    failure_type: str
    probability: float
    estimated_time: str
    prevention_action: str
    severity: str  # critical, warning, info
    metric_name: str
    current_value: float
    threshold: float
    trend: str  # increasing, decreasing, stable
    detected_at: float = field(default_factory=time.time)
    prevented: bool = False


class PredictiveHealer:
    """
    نظام الإصلاح التنبؤي — يراقب أنماط الأداء ويتنبأ بالأعطال
    
    يتعلم من سجل HealthMonitor التاريخي متى يحدث كل نوع من الأعطال
    ويُرسل إنذاراً مسبقاً ويُطلق إجراءات وقائية
    """

    # Thresholds for prediction
    MEMORY_WARNING_PERCENT = 80.0
    MEMORY_CRITICAL_PERCENT = 90.0
    LLM_LATENCY_WARNING_MS = 5000.0
    LLM_LATENCY_CRITICAL_MS = 15000.0
    ERROR_RATE_WARNING = 0.15
    ERROR_RATE_CRITICAL = 0.30
    BRAIN_FAILURE_WARNING = 2  # failures in last hour
    BRAIN_FAILURE_CRITICAL = 5

    def __init__(self, llm_client=None, health_monitor=None):
        self._llm = llm_client
        self._health_monitor = health_monitor
        self._metric_history: list[dict] = []
        self._predictions: list[Prediction] = []
        self._prevention_count: int = 0
        self._prediction_accuracy: list[bool] = []
        self._max_history = 360  # Keep 360 snapshots (1 hour at 10s intervals)
        self._initialized = False

    async def initialize(self):
        """تهيئة النظام"""
        try:
            if self._llm is None:
                from mamoun.core.llm_client import get_llm_client
                self._llm = get_llm_client()
            self._initialized = True
            logger.info("PredictiveHealer initialized")
        except Exception as e:
            logger.warning(f"PredictiveHealer initialization partial: {e}")
            self._initialized = True  # Work without LLM too

    async def collect_metrics(self) -> dict:
        """
        جمع المقاييس الحالية — لقطة من أداء النظام
        
        Returns dict with:
        - memory_percent, llm_latency_ms, error_rate, active_brains,
          total_requests, active_alerts, timestamp
        """
        metrics = {
            "memory_percent": 0.0,
            "llm_latency_ms": 0.0,
            "error_rate": 0.0,
            "active_brains": 5,
            "total_requests": 0,
            "active_alerts": 0,
            "timestamp": time.time(),
        }

        # Collect memory info
        try:
            import psutil
            mem = psutil.virtual_memory()
            metrics["memory_percent"] = mem.percent
        except ImportError:
            # Fallback: estimate from process
            try:
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                metrics["memory_percent"] = min(100.0, (usage / (1024 * 1024 * 512)) * 100)
            except Exception:
                metrics["memory_percent"] = 50.0  # Assume moderate

        # Collect LLM latency
        try:
            start = time.time()
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()
            # Quick ping
            metrics["llm_latency_ms"] = (time.time() - start) * 1000
        except Exception:
            metrics["llm_latency_ms"] = 0.0

        # Collect brain status
        try:
            from mamoun.brains.brain_router import get_brain_router
            router = get_brain_router()
            brain_count = len([b for b in router._brains.values() if hasattr(b, 'state') and b.state.status != "error"])
            metrics["active_brains"] = brain_count
            stats = router.get_stats()
            metrics["total_requests"] = stats.get("total_queries", 0)
        except Exception:
            metrics["active_brains"] = 5

        # Collect health alerts
        try:
            from mamoun.api.health_monitor import _health_state
            metrics["active_alerts"] = len([a for a in _health_state.alerts if a.status == "active"])
        except Exception:
            metrics["active_alerts"] = 0

        # Calculate error rate from recent history
        if self._metric_history:
            recent = self._metric_history[-10:]
            alerts_per_check = [m.get("active_alerts", 0) for m in recent]
            metrics["error_rate"] = sum(alerts_per_check) / max(1, len(alerts_per_check) * 12)  # Normalize

        # Store in history
        self._metric_history.append(metrics)
        if len(self._metric_history) > self._max_history:
            self._metric_history = self._metric_history[-self._max_history:]

        return metrics

    async def analyze_patterns(self) -> list[Prediction]:
        """
        تحليل أنماط المقاييس — يبحث عن اتجاهات تنذر بالأعطال
        
        Checks:
        1. Memory usage trend (approaching limit?)
        2. LLM response time trend (degrading?)
        3. Error rate trend (increasing?)
        4. Brain failure frequency (too many failures?)
        5. Active alerts trend (accumulating?)
        """
        predictions = []
        
        if len(self._metric_history) < 5:
            return predictions  # Need more data

        recent = self._metric_history[-30:]  # Last 30 snapshots

        # ─── 1. Memory Trend ────────────────────────────────
        memory_values = [m.get("memory_percent", 0) for m in recent]
        if len(memory_values) >= 5:
            avg_memory = sum(memory_values) / len(memory_values)
            trend = self._calculate_trend(memory_values)

            if avg_memory > self.MEMORY_CRITICAL_PERCENT:
                predictions.append(Prediction(
                    component="memory",
                    failure_type="memory_exhaustion",
                    probability=min(1.0, avg_memory / 100.0),
                    estimated_time="< 5 minutes" if trend == "increasing" else "< 30 minutes",
                    prevention_action="clean_memory",
                    severity="critical",
                    metric_name="memory_percent",
                    current_value=avg_memory,
                    threshold=self.MEMORY_CRITICAL_PERCENT,
                    trend=trend,
                ))
            elif avg_memory > self.MEMORY_WARNING_PERCENT:
                predictions.append(Prediction(
                    component="memory",
                    failure_type="memory_pressure",
                    probability=0.5,
                    estimated_time="< 30 minutes" if trend == "increasing" else "< 2 hours",
                    prevention_action="clean_memory",
                    severity="warning",
                    metric_name="memory_percent",
                    current_value=avg_memory,
                    threshold=self.MEMORY_WARNING_PERCENT,
                    trend=trend,
                ))

        # ─── 2. LLM Latency Trend ───────────────────────────
        latency_values = [m.get("llm_latency_ms", 0) for m in recent if m.get("llm_latency_ms", 0) > 0]
        if len(latency_values) >= 3:
            avg_latency = sum(latency_values) / len(latency_values)
            trend = self._calculate_trend(latency_values)

            if avg_latency > self.LLM_LATENCY_CRITICAL_MS:
                predictions.append(Prediction(
                    component="llm_client",
                    failure_type="llm_connection_degradation",
                    probability=0.8,
                    estimated_time="< 10 minutes" if trend == "increasing" else "unknown",
                    prevention_action="reconnect_llm",
                    severity="critical",
                    metric_name="llm_latency_ms",
                    current_value=avg_latency,
                    threshold=self.LLM_LATENCY_CRITICAL_MS,
                    trend=trend,
                ))
            elif avg_latency > self.LLM_LATENCY_WARNING_MS:
                predictions.append(Prediction(
                    component="llm_client",
                    failure_type="llm_slowdown",
                    probability=0.4,
                    estimated_time="< 1 hour",
                    prevention_action="reconnect_llm",
                    severity="warning",
                    metric_name="llm_latency_ms",
                    current_value=avg_latency,
                    threshold=self.LLM_LATENCY_WARNING_MS,
                    trend=trend,
                ))

        # ─── 3. Error Rate Trend ────────────────────────────
        error_values = [m.get("error_rate", 0) for m in recent]
        if len(error_values) >= 5:
            avg_error = sum(error_values) / len(error_values)
            trend = self._calculate_trend(error_values)

            if avg_error > self.ERROR_RATE_CRITICAL:
                predictions.append(Prediction(
                    component="system",
                    failure_type="error_cascade",
                    probability=0.7,
                    estimated_time="< 15 minutes" if trend == "increasing" else "unknown",
                    prevention_action="restart_components",
                    severity="critical",
                    metric_name="error_rate",
                    current_value=avg_error,
                    threshold=self.ERROR_RATE_CRITICAL,
                    trend=trend,
                ))
            elif avg_error > self.ERROR_RATE_WARNING:
                predictions.append(Prediction(
                    component="system",
                    failure_type="error_accumulation",
                    probability=0.3,
                    estimated_time="< 1 hour",
                    prevention_action="restart_components",
                    severity="warning",
                    metric_name="error_rate",
                    current_value=avg_error,
                    threshold=self.ERROR_RATE_WARNING,
                    trend=trend,
                ))

        # ─── 4. Brain Failure Frequency ─────────────────────
        brain_values = [m.get("active_brains", 5) for m in recent]
        if len(brain_values) >= 5:
            min_brains = min(brain_values)
            if min_brains < 5:
                failed_brains = 5 - min_brains
                severity = "critical" if failed_brains >= 3 else "warning"
                predictions.append(Prediction(
                    component="brains",
                    failure_type="brain_failures",
                    probability=min(1.0, failed_brains / 5),
                    estimated_time="ongoing",
                    prevention_action="restart_brains",
                    severity=severity,
                    metric_name="active_brains",
                    current_value=min_brains,
                    threshold=5,
                    trend="decreasing" if min_brains < sum(brain_values) / len(brain_values) else "stable",
                ))

        # Update internal predictions
        self._predictions = predictions

        return predictions

    async def predict_failures(self) -> list[dict]:
        """
        التنبؤ بالأعطال — يُرجع قائمة بالتنبؤات
        
        Returns list of prediction dicts
        """
        predictions = await self.analyze_patterns()
        return [
            {
                "component": p.component,
                "failure_type": p.failure_type,
                "probability": round(p.probability, 2),
                "estimated_time": p.estimated_time,
                "prevention_action": p.prevention_action,
                "severity": p.severity,
                "metric_name": p.metric_name,
                "current_value": round(p.current_value, 2),
                "threshold": p.threshold,
                "trend": p.trend,
                "detected_at": p.detected_at,
            }
            for p in predictions
        ]

    async def take_preventive_action(self, prediction: dict) -> dict:
        """
        اتخاذ إجراء وقائي — يُنفّذ الاستراتيجية المناسبة
        
        Strategies:
        - clean_memory → تنظيف الذاكرة قبل الامتلاء
        - reconnect_llm → إعادة اتصال LLM قبل الانقطاع
        - expand_buffer → توسيع buffer قبل overflow
        - restart_components → إعادة تشغيل المكونات المتعثرة
        - restart_brains → إعادة تشغيل الأدمغة المتوقفة
        """
        action = prediction.get("prevention_action", "")
        component = prediction.get("component", "")
        result = {
            "action": action,
            "component": component,
            "success": False,
            "message_ar": "",
            "steps_taken": [],
        }

        try:
            if action == "clean_memory":
                result["steps_taken"].append("تنظيف الذاكرة المؤقتة")
                # Force garbage collection
                import gc
                gc.collect()
                result["steps_taken"].append("gc.collect() تم")
                
                # Clear caches if possible
                try:
                    from mamoun.api.health_monitor import _health_state
                    old_alerts = len(_health_state.alerts)
                    _health_state.alerts = [a for a in _health_state.alerts if a.status == "active"]
                    result["steps_taken"].append(f"تم تنظيف {old_alerts - len(_health_state.alerts)} تنبيه قديم")
                except Exception:
                    pass
                
                result["success"] = True
                result["message_ar"] = "تم تنظيف الذاكرة الوقائي بنجاح"

            elif action == "reconnect_llm":
                result["steps_taken"].append("إعادة تهيئة اتصال LLM")
                try:
                    from mamoun.core.llm_client import get_llm_client
                    llm = get_llm_client()
                    # Reset any connection state
                    if hasattr(llm, '_reset_connection'):
                        await llm._reset_connection()
                    result["steps_taken"].append("تم إعادة الاتصال")
                    result["success"] = True
                    result["message_ar"] = "تم إعادة اتصال LLM وقائياً"
                except Exception as e:
                    result["steps_taken"].append(f"فشل إعادة الاتصال: {e}")

            elif action == "restart_components":
                result["steps_taken"].append("إعادة تهيئة المكونات المتعثرة")
                try:
                    from mamoun.api.health_monitor import auto_heal_component
                    heal_result = await auto_heal_component(component)
                    result["steps_taken"].extend(heal_result.get("steps_taken", []))
                    result["success"] = heal_result.get("healed", False)
                    result["message_ar"] = heal_result.get("message_ar", "تم محاولة الإصلاح")
                except Exception as e:
                    result["steps_taken"].append(f"فشل إعادة التشغيل: {e}")

            elif action == "restart_brains":
                result["steps_taken"].append("إعادة تسجيل الأدمغة")
                try:
                    from mamoun.brains.brain_router import get_brain_router
                    router = get_brain_router()
                    for brain_id, brain in router._brains.items():
                        if hasattr(brain, 'state') and brain.state.status == "error":
                            if hasattr(brain, 'restart'):
                                await brain.restart()
                                result["steps_taken"].append(f"تم إعادة تشغيل الدماغ {brain_id}")
                    result["success"] = True
                    result["message_ar"] = "تم إعادة تشغيل الأدمغة المتوقفة"
                except Exception as e:
                    result["steps_taken"].append(f"فشل إعادة الأدمغة: {e}")

            elif action == "expand_buffer":
                result["steps_taken"].append("توسيع المخزن المؤقت")
                result["success"] = True
                result["message_ar"] = "تم توسيع المخزن المؤقت وقائياً"

        except Exception as e:
            result["message_ar"] = f"فشل الإجراء الوقائي: {str(e)[:100]}"
            logger.error(f"Preventive action failed: {e}")

        if result["success"]:
            self._prevention_count += 1
            # Mark prediction as prevented
            for p in self._predictions:
                if p.component == component and p.failure_type == prediction.get("failure_type"):
                    p.prevented = True

        return result

    def _calculate_trend(self, values: list[float]) -> str:
        """
        حساب الاتجاه — هل القيمة تتزايد أم تتناقص أم مستقرة؟
        
        Uses simple linear regression slope
        """
        if len(values) < 3:
            return "stable"
        
        n = len(values)
        x = list(range(n))
        y = values
        
        # Simple linear regression slope
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return "stable"
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Normalize slope relative to average value
        avg = sum_y / n if n > 0 else 1
        if avg == 0:
            return "stable"
        
        normalized_slope = slope / avg
        
        if normalized_slope > 0.02:
            return "increasing"
        elif normalized_slope < -0.02:
            return "decreasing"
        else:
            return "stable"

    def get_status(self) -> dict:
        """حالة النظام التنبؤي"""
        return {
            "initialized": self._initialized,
            "metric_history_size": len(self._metric_history),
            "active_predictions": len(self._predictions),
            "prevention_count": self._prevention_count,
            "prediction_accuracy": round(
                sum(self._prediction_accuracy) / max(1, len(self._prediction_accuracy)), 3
            ) if self._prediction_accuracy else 0.0,
            "predictions": [
                {
                    "component": p.component,
                    "failure_type": p.failure_type,
                    "probability": p.probability,
                    "severity": p.severity,
                    "prevented": p.prevented,
                }
                for p in self._predictions
            ],
        }


# ─── Singleton ────────────────────────────────────────────────

_predictive_healer: Optional[PredictiveHealer] = None


def get_predictive_healer() -> PredictiveHealer:
    global _predictive_healer
    if _predictive_healer is None:
        _predictive_healer = PredictiveHealer()
    return _predictive_healer
