"""
Supra-Meta Agent — Layer 3 of Triple Awareness Loop
v16.0 — Novel contribution beyond Hyperagents paper

The Supra-Meta Agent is the "consciousness" layer that decides:
1. WHETHER to improve at all (cognitive economy — not everything needs improvement)
2. WHERE to direct improvement energy (which domain/brain/component needs it most)
3. WHETHER improvement trajectories are healthy long-term (detecting gradual drift)
4. WHEN to pause improvement and consolidate (learning requires consolidation)

This layer gives Mamoun what the user described as "الوعي" — true self-awareness
that goes beyond just monitoring performance metrics.

Inspired by:
- SOFAI (Fast, Slow, and Metacognitive Thinking in AI) — Nature npj AI, 2025
- "Artificial Metacognition" — Syracuse University, AAAI 2026
- "From Autonomy to Agency: A 10-Level Framework" — Level 7: Self-Extending Systems
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.hyperagent.supra_meta")


class ImprovementDecision(Enum):
    """Decision about whether to improve."""
    IMPROVE = "improve"            # Proceed with improvement
    PAUSE = "pause"               # Pause improvement, consolidate
    REDIRECT = "redirect"          # Change improvement focus
    ROLLBACK = "rollback"          # Rollback recent changes, they're causing drift
    ESCALATE = "escalate"          # Escalate to human — uncertain about trajectory


class SupraMetaAgent:
    """
    Layer 3: The consciousness layer that oversees the Meta Agent.
    
    Key Capabilities:
    - Cognitive Economy: Not everything needs improvement. Sometimes "good enough" is better.
    - Trajectory Analysis: Are we improving in the right direction? Is there gradual drift?
    - Consolidation: After rapid improvement, pause to let changes stabilize.
    - Meta-Cognitive Awareness: "Why am I trying to improve this? Is it worth the cost?"
    """
    
    # Thresholds for cognitive economy
    PERFORMANCE_SATISFIED_THRESHOLD = 0.85  # If performance > 85%, consider it "good enough"
    IMPROVEMENT_VELOCITY_MIN = 0.001  # Minimum improvement velocity to justify continued effort
    CONSOLIDATION_AFTER_CYCLES = 20  # After N cycles, force consolidation
    DRIFT_DETECTION_WINDOW = 10  # Look back N cycles for drift detection
    
    def __init__(self, data_dir: str = "backend/data/hyperagent"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_path = self.data_dir / "supra_meta_state.json"
        self.decisions_path = self.data_dir / "supra_decisions.jsonl"
        
        # Internal state
        self.improvement_trajectory: list[float] = []  # Performance over time
        self.energy_allocation: dict[str, float] = {}  # Where to focus improvement
        self.consolidation_counter = 0  # Cycles since last consolidation
        self.total_decisions = 0
        
        self._load_state()
        logger.info("SupraMetaAgent initialized — trajectory length: %d", len(self.improvement_trajectory))
    
    def _load_state(self):
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                self.improvement_trajectory = data.get("improvement_trajectory", [])
                self.energy_allocation = data.get("energy_allocation", {})
                self.consolidation_counter = data.get("consolidation_counter", 0)
                self.total_decisions = data.get("total_decisions", 0)
            except Exception:
                pass
    
    def _save_state(self):
        with open(self.state_path, "w") as f:
            json.dump({
                "improvement_trajectory": self.improvement_trajectory[-100:],  # Keep last 100
                "energy_allocation": self.energy_allocation,
                "consolidation_counter": self.consolidation_counter,
                "total_decisions": self.total_decisions,
            }, f, indent=2)
    
    def _save_decision(self, decision: ImprovementDecision, reasoning: str, context: dict):
        with open(self.decisions_path, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "decision": decision.value,
                "reasoning": reasoning,
                "context": context,
            }, ensure_ascii=False) + "\n")
    
    def evaluate_improvement_necessity(
        self,
        current_performance: float,
        domain: str,
        recent_improvements: list[dict],
        resource_usage: dict,
    ) -> tuple[ImprovementDecision, str, dict]:
        """
        The core consciousness function: Should we improve? Where? Why?
        
        Returns:
            (decision, reasoning, context)
        """
        self.total_decisions += 1
        self.consolidation_counter += 1
        
        # Track trajectory
        self.improvement_trajectory.append(current_performance)
        
        context = {
            "current_performance": current_performance,
            "domain": domain,
            "recent_improvement_count": len(recent_improvements),
            "consolidation_counter": self.consolidation_counter,
            "trajectory_length": len(self.improvement_trajectory),
        }
        
        # ---- Decision Logic ----
        
        # 1. PERFORMANCE SATISFACTION: Is current performance "good enough"?
        if current_performance >= self.PERFORMANCE_SATISFIED_THRESHOLD:
            reasoning = (
                f"الأداء الحالي ({current_performance:.1%}) يفوق عتبة الرضا "
                f"({self.PERFORMANCE_SATISFIED_THRESHOLD:.0%}). لا حاجة ملحة للتحسين في {domain}. "
                f"من الأفضل توجيه الطاقة لمجالات تحتاج تحسين أكثر."
            )
            decision = ImprovementDecision.REDIRECT
            context["redirect_reason"] = "performance_satisfied"
            self._save_decision(decision, reasoning, context)
            self._save_state()
            return decision, reasoning, context
        
        # 2. CONSOLIDATION: Have we improved too rapidly without stabilizing?
        if self.consolidation_counter >= self.CONSOLIDATION_AFTER_CYCLES:
            reasoning = (
                f"تم تنفيذ {self.consolidation_counter} دورة تحسين متتالية بدون توقف. "
                f"النظام يحتاج فترة تثبيت لضمان استقرار التغييرات. "
                f"التحسين المستمر بدون تثبيت قد يؤدي إلى تراكم عدم الاستقرار."
            )
            decision = ImprovementDecision.PAUSE
            context["pause_duration"] = 5  # Pause for 5 cycles
            self.consolidation_counter = 0
            self._save_decision(decision, reasoning, context)
            self._save_state()
            return decision, reasoning, context
        
        # 3. DRIFT DETECTION: Are improvements getting worse over time?
        drift_detected, drift_info = self._detect_drift()
        if drift_detected:
            reasoning = (
                f"تم كشف انحراف تدريجي في مسار التحسين: {drift_info['description']}. "
                f"التحسينات الأخيرة قد تكون تضر أكثر مما تنفع. "
                f"يُنصح بالتراجع عن آخر التغييرات وإعادة التقييم."
            )
            decision = ImprovementDecision.ROLLBACK
            context["drift_info"] = drift_info
            self._save_decision(decision, reasoning, context)
            self._save_state()
            return decision, reasoning, context
        
        # 4. IMPROVEMENT VELOCITY: Are we making meaningful progress?
        velocity = self._calculate_improvement_velocity()
        if velocity < self.IMPROVEMENT_VELOCITY_MIN and len(self.improvement_trajectory) > 5:
            reasoning = (
                f"سرعة التحسين منخفضة جداً ({velocity:.4f}). "
                f"الجهد المبذول في التحسين لا يبرر النتائج. "
                f"يُنصح بتغيير الاستراتيجية أو توجيه الطاقة لمجال آخر."
            )
            decision = ImprovementDecision.REDIRECT
            context["velocity"] = velocity
            context["redirect_reason"] = "low_velocity"
            self._save_decision(decision, reasoning, context)
            self._save_state()
            return decision, reasoning, context
        
        # 5. RESOURCE AWARENESS: Are we spending too many resources?
        if resource_usage.get("cpu_percent", 0) > 90 or resource_usage.get("memory_percent", 0) > 85:
            reasoning = (
                f"استهلاك الموارد مرتفع (CPU: {resource_usage.get('cpu_percent', 0):.0f}%, "
                f"RAM: {resource_usage.get('memory_percent', 0):.0f}%). "
                f"التحسين الإضافي قد يضر بأداء النظام ككل. يُنصح بالتوقف مؤقتاً."
            )
            decision = ImprovementDecision.PAUSE
            context["pause_duration"] = 3
            self._save_decision(decision, reasoning, context)
            self._save_state()
            return decision, reasoning, context
        
        # 6. DEFAULT: Proceed with improvement
        reasoning = (
            f"الأداء الحالي ({current_performance:.1%}) يحتاج تحسين. "
            f"سرعة التحسين ({velocity:.4f}) مقبولة. "
            f"لا انحراف مكتشف. الموارد كافية. المتابعة بالتحسين في {domain}."
        )
        decision = ImprovementDecision.IMPROVE
        self._save_decision(decision, reasoning, context)
        self._save_state()
        return decision, reasoning, context
    
    def _detect_drift(self) -> tuple[bool, dict]:
        """
        Detect gradual drift in improvement trajectory.
        Drift = performance is slowly decreasing despite "improvements".
        """
        window = self.improvement_trajectory[-self.DRIFT_DETECTION_WINDOW:]
        if len(window) < 5:
            return False, {}
        
        # Calculate trend: compare first half vs second half
        mid = len(window) // 2
        first_half_avg = sum(window[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(window[mid:]) / (len(window) - mid) if len(window) > mid else 0
        
        drift = first_half_avg - second_half_avg
        drift_threshold = 0.03  # 3% performance drop = drift
        
        if drift > drift_threshold:
            return True, {
                "description": f"انخفاض تدريجي قدره {drift:.1%} في آخر {len(window)} قياس",
                "drift_amount": drift,
                "first_half_avg": first_half_avg,
                "second_half_avg": second_half_avg,
            }
        
        return False, {}
    
    def _calculate_improvement_velocity(self) -> float:
        """Calculate the rate of improvement over recent cycles."""
        if len(self.improvement_trajectory) < 3:
            return 0.0
        
        recent = self.improvement_trajectory[-5:]
        if len(recent) < 2:
            return 0.0
        
        # Simple velocity: average improvement per cycle
        total_improvement = recent[-1] - recent[0]
        velocity = total_improvement / len(recent)
        return velocity
    
    def allocate_improvement_energy(self, domains: dict[str, float]) -> dict[str, float]:
        """
        Decide where to focus improvement energy across domains.
        
        Args:
            domains: {domain_name: current_performance} for each domain
        
        Returns:
            {domain_name: energy_allocation} normalized to sum to 1.0
        """
        if not domains:
            return {}
        
        # Allocate more energy to weaker domains
        # Use inverse performance as weight (lower perf = more energy)
        weights = {}
        for domain, perf in domains.items():
            # Inverse performance with minimum weight
            weights[domain] = max(1.0 - perf, 0.1)
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            allocations = {k: round(v / total, 3) for k, v in weights.items()}
        else:
            allocations = {k: round(1.0 / len(weights), 3) for k in weights}
        
        self.energy_allocation = allocations
        self._save_state()
        return allocations
    
    def get_status(self) -> dict:
        return {
            "total_decisions": self.total_decisions,
            "consolidation_counter": self.consolidation_counter,
            "trajectory_length": len(self.improvement_trajectory),
            "latest_performance": self.improvement_trajectory[-1] if self.improvement_trajectory else None,
            "improvement_velocity": self._calculate_improvement_velocity(),
            "energy_allocation": self.energy_allocation,
            "drift_detected": self._detect_drift()[0],
        }
