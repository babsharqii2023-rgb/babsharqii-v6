"""
Digital Immune System — المناعة الذاتية الرقمية
v16.0 — Novel contribution

The human body has an immune system that detects and fights foreign invaders.
Mamoun needs the same: automatic anomaly detection and response for:
1. Performance anomalies (sudden drops, unusual patterns)
2. Behavioral anomalies (unexpected code changes, strange routing)
3. Security anomalies (unauthorized access attempts, unusual API calls)
4. Stability anomalies (memory leaks, resource exhaustion, cascading failures)

Key principle: "Safety by construction, not detection" — but detection
is the safety net when construction isn't enough.
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.awareness.immune")


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImmuneResponse:
    """An immune system response to a detected anomaly."""
    
    def __init__(
        self,
        threat_type: str,
        threat_level: ThreatLevel,
        description: str,
        auto_response: str,
        requires_human: bool = False,
    ):
        self.id = f"ir_{int(time.time())}_{threat_type[:4]}"
        self.threat_type = threat_type
        self.threat_level = threat_level
        self.description = description
        self.auto_response = auto_response
        self.requires_human = requires_human
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.resolved = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "threat_type": self.threat_type,
            "threat_level": self.threat_level.value if isinstance(self.threat_level, ThreatLevel) else self.threat_level,
            "description": self.description,
            "auto_response": self.auto_response,
            "requires_human": self.requires_human,
            "created_at": self.created_at,
            "resolved": self.resolved,
        }


class DigitalImmuneSystem:
    """
    Mamoun's immune system for automatic anomaly detection and response.
    """
    
    # Baseline metrics (will be calibrated over time)
    BASELINE = {
        "response_time_ms": {"mean": 500, "std": 200},
        "error_rate": {"mean": 0.05, "std": 0.03},
        "memory_usage_pct": {"mean": 60, "std": 15},
        "cpu_usage_pct": {"mean": 40, "std": 20},
        "mutation_success_rate": {"mean": 0.3, "std": 0.15},
        "api_call_frequency_per_min": {"mean": 30, "std": 15},
    }
    
    def __init__(self, data_dir: str = "backend/data/awareness"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.responses_path = self.data_dir / "immune_responses.jsonl"
        self.baseline_path = self.data_dir / "baseline_metrics.json"
        
        self.responses: list[ImmuneResponse] = []
        self.metrics_history: list[dict] = []
        self.baseline = self._load_baseline()
    
    def _load_baseline(self) -> dict:
        if self.baseline_path.exists():
            try:
                with open(self.baseline_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return dict(self.BASELINE)
    
    def _save_response(self, response: ImmuneResponse):
        with open(self.responses_path, "a") as f:
            f.write(json.dumps(response.to_dict(), ensure_ascii=False) + "\n")
    
    def scan(self, current_metrics: dict) -> list[ImmuneResponse]:
        """
        Scan current metrics for anomalies. The immune system's main loop.
        """
        self.metrics_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **current_metrics,
        })
        
        # Keep only last 1000 metric snapshots
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        responses = []
        
        # 1. Performance anomalies
        perf_responses = self._check_performance_anomalies(current_metrics)
        responses.extend(perf_responses)
        
        # 2. Resource anomalies
        resource_responses = self._check_resource_anomalies(current_metrics)
        responses.extend(resource_responses)
        
        # 3. Behavioral anomalies
        behavior_responses = self._check_behavioral_anomalies(current_metrics)
        responses.extend(behavior_responses)
        
        # 4. Stability anomalies
        stability_responses = self._check_stability_anomalies()
        responses.extend(stability_responses)
        
        # Save all responses
        for response in responses:
            self._save_response(response)
            self.responses.append(response)
        
        if responses:
            logger.warning("Immune system detected %d anomalies", len(responses))
        
        return responses
    
    def _is_anomalous(self, metric_name: str, value: float, sigma_threshold: float = 2.5) -> bool:
        """Check if a metric value is statistically anomalous."""
        baseline = self.baseline.get(metric_name)
        if not baseline:
            return False
        mean = baseline["mean"]
        std = baseline["std"]
        if std == 0:
            return False
        z_score = abs(value - mean) / std
        return z_score > sigma_threshold
    
    def _check_performance_anomalies(self, metrics: dict) -> list[ImmuneResponse]:
        """Check for performance anomalies."""
        responses = []
        
        response_time = metrics.get("response_time_ms", 0)
        if self._is_anomalous("response_time_ms", response_time):
            level = ThreatLevel.HIGH if response_time > self.baseline["response_time_ms"]["mean"] * 5 else ThreatLevel.MEDIUM
            responses.append(ImmuneResponse(
                threat_type="performance_slowdown",
                threat_level=level,
                description=f"بطء غير عادي في الاستجابة: {response_time}ms (المتوقع: {self.baseline['response_time_ms']['mean']}ms)",
                auto_response="تفعيل وضع التوفير — تقليل العمليات غير الضرورية والتركيز على المهام الحرجة",
            ))
        
        error_rate = metrics.get("error_rate", 0)
        if self._is_anomalous("error_rate", error_rate):
            level = ThreatLevel.HIGH if error_rate > 0.3 else ThreatLevel.MEDIUM
            responses.append(ImmuneResponse(
                threat_type="error_spike",
                threat_level=level,
                description=f"ارتفاع مفاجئ في معدل الأخطاء: {error_rate:.1%} (المتوقع: {self.baseline['error_rate']['mean']:.1%})",
                auto_response="تفعيل وضع التشخيص — تحليل الأخطاء وتحديد المصدر وتقليل حركة المرور",
            ))
        
        return responses
    
    def _check_resource_anomalies(self, metrics: dict) -> list[ImmuneResponse]:
        """Check for resource anomalies."""
        responses = []
        
        memory = metrics.get("memory_usage_pct", 0)
        if memory > 85:
            level = ThreatLevel.CRITICAL if memory > 95 else ThreatLevel.HIGH
            responses.append(ImmuneResponse(
                threat_type="memory_pressure",
                threat_level=level,
                description=f"ضغط على الذاكرة: {memory}% — خطر نفاد الذاكرة",
                auto_response="تفعيل النسيان الاستراتيجي — تنظيف الذاكرة المؤقتة وإغلاق العمليات غير الضرورية",
                requires_human=memory > 95,
            ))
        
        cpu = metrics.get("cpu_usage_pct", 0)
        if cpu > 90:
            level = ThreatLevel.HIGH if cpu > 95 else ThreatLevel.MEDIUM
            responses.append(ImmuneResponse(
                threat_type="cpu_overload",
                threat_level=level,
                description=f"تحميل معالج مرتفع: {cpu}% — قد يؤثر على الاستجابة",
                auto_response="تأجيل المهام غير العاجلة وتقليل وتيرة التطور",
            ))
        
        return responses
    
    def _check_behavioral_anomalies(self, metrics: dict) -> list[ImmuneResponse]:
        """Check for behavioral anomalies."""
        responses = []
        
        # Check for unusual API call frequency
        api_freq = metrics.get("api_call_frequency_per_min", 0)
        if self._is_anomalous("api_call_frequency_per_min", api_freq) and api_freq > 100:
            responses.append(ImmuneResponse(
                threat_type="api_abuse",
                threat_level=ThreatLevel.HIGH,
                description=f"معدل استدعاءات API غير عادي: {api_freq}/دقيقة — قد يشير إلى حلقة مفرطة أو هجوماً",
                auto_response="تقييد معدل الاستدعاءات مؤقتاً وتحليل المصدر",
                requires_human=True,
            ))
        
        return responses
    
    def _check_stability_anomalies(self) -> list[ImmuneResponse]:
        """Check for cascading failure patterns."""
        responses = []
        
        # Look for consecutive errors in recent metrics
        if len(self.metrics_history) >= 5:
            recent = self.metrics_history[-5:]
            consecutive_errors = all(m.get("error_rate", 0) > 0.1 for m in recent)
            if consecutive_errors:
                responses.append(ImmuneResponse(
                    threat_type="cascading_failure",
                    threat_level=ThreatLevel.CRITICAL,
                    description="أخطاء متتالية في آخر 5 قياسات — قد يكون هناك فشل متسلسل",
                    auto_response="تنشيط وضع الطوارئ — إيقاف جميع عمليات التطور والعودة لآخر حالة مستقرة",
                    requires_human=True,
                ))
        
        return responses
    
    def update_baseline(self, metrics: dict):
        """Gradually update baseline metrics based on recent observations."""
        for key, value in metrics.items():
            if key in self.baseline and isinstance(value, (int, float)):
                current = self.baseline[key]
                # Exponential moving average (slow adaptation)
                alpha = 0.05  # 5% new data weight
                current["mean"] = current["mean"] * (1 - alpha) + value * alpha
                # Update std with Welford's algorithm (simplified)
                diff = value - current["mean"]
                current["std"] = max(
                    (current["std"] * (1 - alpha) + abs(diff) * alpha) * 0.9,
                    current["std"] * 0.5,  # Never shrink too fast
                )
    
    def get_status(self) -> dict:
        recent_responses = self.responses[-20:] if self.responses else []
        active_threats = [r for r in recent_responses if not r.resolved]
        
        return {
            "total_responses": len(self.responses),
            "active_threats": len(active_threats),
            "threat_levels": {
                level.value: sum(1 for r in active_threats if r.threat_level == level)
                for level in ThreatLevel
            },
            "baseline_metrics": {
                k: {"mean": round(v["mean"], 2), "std": round(v["std"], 2)}
                for k, v in self.baseline.items()
            },
            "metrics_history_size": len(self.metrics_history),
        }
