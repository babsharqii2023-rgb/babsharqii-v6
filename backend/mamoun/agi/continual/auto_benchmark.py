"""
BABSHARQII v10.0 — Auto Benchmark Runner
مشغّل الاختبارات التلقائي — يشغل اختبارات الأداء بعد كل مهمة ويسجل النتائج

Runs automatic benchmarks after each learning task and records results
to benchmark_history.json. Detects regressions and suggests rollbacks.

Feature Flag: MAMOUN_AUTO_EVOLVE (default: false)
"""

from __future__ import annotations

import os
import json
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

AUTO_EVOLVE_ENABLED: bool = os.environ.get(
    "MAMOUN_AUTO_EVOLVE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class BenchmarkEntry:
    """سجل اختبار أداء"""
    timestamp: float = 0.0
    task_name: str = ""
    benchmark_type: str = ""       # arc_agi, dyn_tom, ccd_bench, ewc_forgetting
    score: float = 0.0
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "task_name": self.task_name,
            "benchmark_type": self.benchmark_type,
            "score": round(self.score, 4),
            "details": self.details,
        }


class AutoBenchmarkRunner:
    """
    مشغّل الاختبارات التلقائي
    
    After each learning task, runs a selected set of benchmarks
    (ARC-AGI, DynToM, forgetting rate) and records results.
    Detects regressions and suggests rollbacks.
    """

    def __init__(self, benchmark_history_path: str = "benchmark_history.json"):
        self._history_path = benchmark_history_path
        self._history: list[BenchmarkEntry] = []
        self._load_history()

    def run_after_task(self, task_name: str) -> list[BenchmarkEntry]:
        """
        شغّل اختبارات الأداء بعد مهمة تعلم.
        """
        if not AUTO_EVOLVE_ENABLED:
            return []

        entries = []

        # Simulate running benchmarks
        # In production, these would call the actual evaluators
        benchmarks = [
            ("arc_agi", self._run_arc_benchmark),
            ("dyn_tom", self._run_tom_benchmark),
            ("ewc_forgetting", self._run_forgetting_benchmark),
        ]

        for bench_type, runner in benchmarks:
            score, details = runner(task_name)
            entry = BenchmarkEntry(
                timestamp=time.time(),
                task_name=task_name,
                benchmark_type=bench_type,
                score=score,
                details=details,
            )
            entries.append(entry)
            self._history.append(entry)

        self._save_history()
        logger.info(f"Auto-benchmark after '{task_name}': {len(entries)} benchmarks run")

        return entries

    def get_history(self) -> list[BenchmarkEntry]:
        """احصل على تاريخ الاختبارات"""
        return self._history

    def detect_regression(self, threshold: float = 0.05) -> list[BenchmarkEntry]:
        """
        كشف التراجع في الأداء.
        
        Returns entries where score dropped more than threshold from previous.
        """
        regressions = []

        # Group by benchmark type
        by_type: dict[str, list[BenchmarkEntry]] = {}
        for entry in self._history:
            if entry.benchmark_type not in by_type:
                by_type[entry.benchmark_type] = []
            by_type[entry.benchmark_type].append(entry)

        for bench_type, entries in by_type.items():
            if len(entries) < 2:
                continue

            # Compare last two entries
            current = entries[-1]
            previous = entries[-2]

            if previous.score > 0 and current.score < previous.score:
                drop = (previous.score - current.score) / previous.score
                if drop > threshold:
                    regressions.append(current)
                    logger.warning(
                        f"Regression detected in {bench_type}: "
                        f"{previous.score:.4f} → {current.score:.4f} "
                        f"(drop: {drop:.2%})"
                    )

        return regressions

    def should_rollback(self, regression_threshold: float = 0.05) -> bool:
        """
        هل يجب التراجع؟ — True إذا كان هناك تراجع كبير في اختبارات حرجة.
        """
        regressions = self.detect_regression(regression_threshold)
        critical_types = {"arc_agi", "dyn_tom", "ewc_forgetting"}

        for r in regressions:
            if r.benchmark_type in critical_types:
                return True

        return False

    def generate_report(self) -> dict:
        """أنشئ تقريراً عن حالة الأداء"""
        if not self._history:
            return {"total_entries": 0, "regressions": 0, "trend": "no_data"}

        # Group by type
        by_type: dict[str, list[float]] = {}
        for entry in self._history:
            if entry.benchmark_type not in by_type:
                by_type[entry.benchmark_type] = []
            by_type[entry.benchmark_type].append(entry.score)

        trends = {}
        for bench_type, scores in by_type.items():
            if len(scores) >= 2:
                recent = scores[-3:] if len(scores) >= 3 else scores
                trend = "improving" if recent[-1] > recent[0] else "declining"
                trends[bench_type] = {
                    "latest": recent[-1],
                    "trend": trend,
                    "count": len(scores),
                }

        regressions = self.detect_regression()

        return {
            "total_entries": len(self._history),
            "regressions": len(regressions),
            "by_type": trends,
            "should_rollback": self.should_rollback(),
        }

    # ═══════════════════════════════════════════════════════════════════════

    def _run_arc_benchmark(self, task_name: str) -> tuple[float, dict]:
        """شغّل اختبار ARC-AGI (محاكاة)"""
        # In production: call arc_agi_3_evaluator.py
        score = 0.15 + (hash(task_name) % 10) * 0.01  # Simulated
        return score, {"simulated": True}

    def _run_tom_benchmark(self, task_name: str) -> tuple[float, dict]:
        """شغّل اختبار DynToM (محاكاة)"""
        score = 0.65 + (hash(task_name) % 10) * 0.01
        return score, {"simulated": True}

    def _run_forgetting_benchmark(self, task_name: str) -> tuple[float, dict]:
        """شغّل اختبار معدل النسيان (محاكاة)"""
        score = 0.92 - (hash(task_name) % 5) * 0.01
        return score, {"simulated": True}

    def _load_history(self) -> None:
        """حمّل تاريخ الاختبارات"""
        path = Path(self._history_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    self._history.append(BenchmarkEntry(
                        timestamp=item.get("timestamp", 0),
                        task_name=item.get("task_name", ""),
                        benchmark_type=item.get("benchmark_type", ""),
                        score=item.get("score", 0),
                        details=item.get("details", {}),
                    ))
            except Exception as e:
                logger.warning(f"Failed to load benchmark history: {e}")

    def _save_history(self) -> None:
        """احفظ تاريخ الاختبارات"""
        path = Path(self._history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._history[-500:]]  # Keep last 500
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
