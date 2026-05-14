"""
BABSHARQII v37.0 — Improvement Engine (محرك التحسين العميق)
7 حراس ضد التحديث الشكلي — يضمن كل تحسين حقيقي وليس شكلياً

Architecture:
  ┌──────────────────────────────────────────────────────────────┐
  │                  IMPROVEMENT ENGINE                           │
  │                                                               │
  │  Guard 1: Impact Classification — L0❌ L1⚠️ L2✅ L3🔐       │
  │  Guard 2: Quantitative Metrics Gate — prove with numbers      │
  │  Guard 3: Dependency Analysis — check ripple effect           │
  │  Guard 4: Test Gate — generate test that proves improvement   │
  │  Guard 5: Delta Analysis — compare before/after in sandbox    │
  │  Guard 6: Stagnation Detection — detect empty loops           │
  │  Guard 7: Historical Quality Model — learn from past          │
  │                                                               │
  │  L0 (cosmetic) → AUTO-REJECT, no exceptions                  │
  │  L1 (optimization) → needs metric_proof (≥5% improvement)    │
  │  L2 (structural) → needs dependency_analysis + metric_proof   │
  │  L3 (capability) → needs HUMAN_APPROVAL + new_tests           │
  └──────────────────────────────────────────────────────────────┘
"""

import asyncio
import json
import logging
import re
import time
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.improvement_engine")


# ═══════════════════════════════════════════════════════════════════════════════
#  Impact Classification
# ═══════════════════════════════════════════════════════════════════════════════

class ImpactLevel(str, Enum):
    L0_COSMETIC = "L0"       # formatting, comments, renames — AUTO-REJECT
    L1_OPTIMIZATION = "L1"   # algorithm, performance — needs metric_proof
    L2_STRUCTURAL = "L2"     # architecture, coupling — needs dependency_analysis
    L3_CAPABILITY = "L3"     # new features, integrations — needs human_approval


@dataclass
class ImprovementRecord:
    """سجل تحسين واحد"""
    id: str = ""
    impact_level: str = ""
    diff_summary: str = ""
    files_changed: list = field(default_factory=list)
    before_metrics: dict = field(default_factory=dict)
    after_metrics: dict = field(default_factory=dict)
    delta: dict = field(default_factory=dict)
    verified: bool = False
    rejected: bool = False
    rejection_reason: str = ""
    timestamp: float = 0.0
    elapsed_seconds: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.id:
            self.id = f"imp_{int(self.timestamp)}_{hash(self.diff_summary) % 10000:04d}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Improvement Engine — The 7 Guards
# ═══════════════════════════════════════════════════════════════════════════════

class ImprovementEngine:
    """محرك التحسين العميق — 7 حراس ضد التحديث الشكلي"""

    def __init__(self):
        self._initialized = False
        self._db_initialized = False
        self._history: List[ImprovementRecord] = []

    def initialize(self):
        """Initialize the engine and ensure DB table exists."""
        if self._initialized:
            return
        self._ensure_db()
        self._load_history()
        self._initialized = True
        logger.info("ImprovementEngine initialized — 7 guards ready")

    def _ensure_db(self):
        """Create improvement_history table if not exists."""
        if self._db_initialized:
            return
        try:
            conn = get_db_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS improvement_history (
                    id TEXT PRIMARY KEY,
                    impact_level TEXT NOT NULL,
                    diff_summary TEXT DEFAULT '',
                    files_changed TEXT DEFAULT '[]',
                    before_metrics TEXT DEFAULT '{}',
                    after_metrics TEXT DEFAULT '{}',
                    delta TEXT DEFAULT '{}',
                    verified INTEGER DEFAULT 0,
                    rejected INTEGER DEFAULT 0,
                    rejection_reason TEXT DEFAULT '',
                    timestamp REAL DEFAULT 0,
                    elapsed_seconds REAL DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
            self._db_initialized = True
        except Exception as e:
            logger.error(f"Failed to create improvement_history table: {e}")
            # Fallback: use in-memory only
            self._db_initialized = True

    def _load_history(self):
        """Load recent improvement history from DB."""
        try:
            conn = get_db_connection()
            rows = conn.execute(
                "SELECT * FROM improvement_history ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()
            conn.close()
            for row in rows:
                self._history.append(ImprovementRecord(
                    id=row[0],
                    impact_level=row[1],
                    diff_summary=row[2],
                    files_changed=json.loads(row[3]) if row[3] else [],
                    before_metrics=json.loads(row[4]) if row[4] else {},
                    after_metrics=json.loads(row[5]) if row[5] else {},
                    delta=json.loads(row[6]) if row[6] else {},
                    verified=bool(row[7]),
                    rejected=bool(row[8]),
                    rejection_reason=row[9] or "",
                    timestamp=row[10] or 0,
                    elapsed_seconds=row[11] or 0,
                ))
        except Exception as e:
            logger.warning(f"Could not load improvement history: {e}")

    def _save_record(self, record: ImprovementRecord):
        """Save an improvement record to DB."""
        self._history.append(record)
        try:
            conn = get_db_connection()
            conn.execute(
                """INSERT OR REPLACE INTO improvement_history
                   (id, impact_level, diff_summary, files_changed, before_metrics,
                    after_metrics, delta, verified, rejected, rejection_reason,
                    timestamp, elapsed_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.impact_level,
                    record.diff_summary[:500],
                    json.dumps(record.files_changed),
                    json.dumps(record.before_metrics),
                    json.dumps(record.after_metrics),
                    json.dumps(record.delta),
                    int(record.verified),
                    int(record.rejected),
                    record.rejection_reason,
                    record.timestamp,
                    record.elapsed_seconds,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save improvement record: {e}")

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 1: Impact Classification
    # ───────────────────────────────────────────────────────────────────────

    async def classify_impact(self, diff: str, files_changed: List[str]) -> Dict[str, Any]:
        """
        Guard 1: تصنيف الأثر
        
        Rules:
        - L0 (cosmetic): only whitespace, comments, renames, formatting → AUTO-REJECT
        - L1 (optimization): algorithm changes, performance tweaks → needs metric_proof
        - L2 (structural): changes affecting multiple modules → needs dependency_analysis
        - L3 (capability): new features, new integrations → needs human_approval
        """
        if not diff.strip():
            return {"level": ImpactLevel.L0_COSMETIC, "reason": "فارغ — لا تغييرات", "auto_reject": True}

        lines = diff.split('\n')
        added_lines = [l for l in lines if l.startswith('+') and not l.startswith('+++')]
        removed_lines = [l for l in lines if l.startswith('-') and not l.startswith('---')]

        if not added_lines and not removed_lines:
            return {"level": ImpactLevel.L0_COSMETIC, "reason": "لا إضافات أو حذف فعلي", "auto_reject": True}

        # Count meaningful vs cosmetic changes
        cosmetic_count = 0
        meaningful_count = 0
        new_file_count = 0
        structural_indicators = 0

        for line in added_lines:
            stripped = line[1:].strip()
            if not stripped:
                cosmetic_count += 1
            elif stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('"""') or stripped.startswith("'''"):
                cosmetic_count += 1  # comment
            elif stripped in ('', '\n', '\r\n'):
                cosmetic_count += 1  # whitespace
            else:
                meaningful_count += 1

        for f in files_changed:
            if '/__init__.' in f:
                continue
            if f.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                # Check for genuinely new files (indicated by git diff "new file mode" header)
                if 'new file mode' in diff.lower():
                    new_file_count += 1

        # Check for structural indicators
        structural_keywords = ['class ', 'def ', 'async def ', 'function ', 'export ', 'import ', 'from ']
        for line in added_lines:
            stripped = line[1:].strip()
            for kw in structural_keywords:
                if stripped.startswith(kw):
                    structural_indicators += 1
                    break

        total_changes = cosmetic_count + meaningful_count
        cosmetic_ratio = cosmetic_count / max(total_changes, 1)

        # Decision logic
        if meaningful_count == 0 and cosmetic_count > 0:
            return {
                "level": ImpactLevel.L0_COSMETIC,
                "reason": f"تغيير تجميلي فقط ({cosmetic_count} سطر — تعليقات/فراغات)",
                "auto_reject": True,
                "stats": {"cosmetic": cosmetic_count, "meaningful": 0, "structural": 0},
            }

        if cosmetic_ratio > 0.8 and structural_indicators == 0:
            return {
                "level": ImpactLevel.L0_COSMETIC,
                "reason": f"أغلب التغييرات تجميلية ({cosmetic_ratio:.0%})",
                "auto_reject": True,
                "stats": {"cosmetic": cosmetic_count, "meaningful": meaningful_count, "structural": structural_indicators},
            }

        if new_file_count > 0:
            return {
                "level": ImpactLevel.L3_CAPABILITY,
                "reason": f"ملفات جديدة ({new_file_count}) — ميزة/تكامل جديد",
                "auto_reject": False,
                "requires_approval": True,
                "stats": {"cosmetic": cosmetic_count, "meaningful": meaningful_count, "structural": structural_indicators, "new_files": new_file_count},
            }

        if structural_indicators >= 3 or len(files_changed) >= 3:
            return {
                "level": ImpactLevel.L2_STRUCTURAL,
                "reason": f"تغيير هيكلي ({structural_indicators} مؤشرات بنيوية، {len(files_changed)} ملفات)",
                "auto_reject": False,
                "requires": ["dependency_analysis", "metric_proof"],
                "stats": {"cosmetic": cosmetic_count, "meaningful": meaningful_count, "structural": structural_indicators},
            }

        # Default: L1 optimization
        return {
            "level": ImpactLevel.L1_OPTIMIZATION,
            "reason": f"تحسين محتمل ({meaningful_count} سطر فعلي)",
            "auto_reject": False,
            "requires": ["metric_proof"],
            "stats": {"cosmetic": cosmetic_count, "meaningful": meaningful_count, "structural": structural_indicators},
        }

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 2: Quantitative Metrics Gate
    # ───────────────────────────────────────────────────────────────────────

    async def measure_metrics(self) -> Dict[str, Any]:
        """
        Guard 2: قياس الأداء الحالي
        
        Measures: response_time, error_rate, test_coverage, memory_usage
        """
        metrics = {
            "timestamp": time.time(),
            "response_time_ms": 0,
            "error_rate": 0.0,
            "test_coverage_pct": 0,
            "memory_usage_mb": 0,
            "active_endpoints": 0,
            "neural_bus_subscribers": 0,
            "kernel_brains_active": 0,
        }

        try:
            import subprocess
            # Response time: measure health endpoint
            start = time.time()
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"],
                capture_output=True, text=True, timeout=5,
            )
            elapsed = (time.time() - start) * 1000
            metrics["response_time_ms"] = round(elapsed, 1)
        except Exception:
            metrics["response_time_ms"] = -1  # unreachable

        try:
            # Memory usage
            import os
            import psutil
            process = psutil.Process(os.getpid())
            metrics["memory_usage_mb"] = round(process.memory_info().rss / 1024 / 1024, 1)
        except Exception:
            metrics["memory_usage_mb"] = 0

        try:
            # NeuralBus subscribers count
            from mamoun.core.neural_bus import neural_bus
            if hasattr(neural_bus, '_subscribers'):
                metrics["neural_bus_subscribers"] = len(neural_bus._subscribers)
        except Exception:
            pass

        try:
            # Kernel brains count
            from mamoun.core.mamoun_kernel import get_kernel
            kernel = get_kernel()
            if hasattr(kernel, '_brains'):
                metrics["kernel_brains_active"] = len(kernel._brains)
        except Exception:
            pass

        # Count API endpoints
        try:
            from mamoun.api.routes import api_router
            metrics["active_endpoints"] = len(api_router.routes)
        except Exception:
            pass

        # Error rate from recent history
        recent_errors = sum(1 for r in self._history[-20:] if r.rejected)
        total_recent = max(len(self._history[-20:]), 1)
        metrics["error_rate"] = round(recent_errors / total_recent, 3)

        return metrics

    async def verify_metrics(self, before: Dict, after: Dict, min_improvement_pct: float = 5.0) -> Dict[str, Any]:
        """
        Guard 2: بوابة القياس الكمي
        
        Returns delta analysis with pass/fail for each metric.
        """
        delta = {}
        all_passed = True

        metric_keys = ["response_time_ms", "error_rate", "memory_usage_mb"]
        # Lower is better for these
        lower_is_better = {"response_time_ms", "error_rate", "memory_usage_mb"}

        for key in metric_keys:
            b = before.get(key, 0)
            a = after.get(key, 0)
            if b <= 0:
                delta[key] = {"before": b, "after": a, "change_pct": 0, "improved": True}
                continue

            change_pct = ((a - b) / b) * 100
            improved = change_pct <= -min_improvement_pct if key in lower_is_better else change_pct >= min_improvement_pct
            if not improved and abs(change_pct) > 1:
                all_passed = False

            delta[key] = {
                "before": round(b, 2),
                "after": round(a, 2),
                "change_pct": round(change_pct, 1),
                "improved": improved,
            }

        return {
            "passed": all_passed,
            "delta": delta,
            "min_improvement_pct": min_improvement_pct,
        }

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 3: Dependency Analysis
    # ───────────────────────────────────────────────────────────────────────

    async def analyze_dependencies(self, files_changed: List[str]) -> Dict[str, Any]:
        """
        Guard 3: تحليل الاعتماديات
        
        If only 1 file affected → suspicious (cosmetic)
        If 3+ files affected → likely structural (deep)
        """
        affected_modules = set()
        dependency_chain = []

        module_map = {
            "api": "API Layer",
            "core": "Core Engine",
            "brains": "AI Brains",
            "memory": "Memory System",
            "emotion": "Emotion Engine",
            "instincts": "Instincts",
            "physical": "Physical/IoT",
            "planning": "Planning",
            "learning": "Learning",
            "agi": "AGI Pillars",
            "evolution": "Evolution",
            "terminal": "Terminal",
        }

        for f in files_changed:
            parts = Path(f).parts
            for i, part in enumerate(parts):
                if part in module_map:
                    affected_modules.add(module_map[part])
                    dependency_chain.append(f)

        num_affected = len(affected_modules)
        if num_affected <= 1:
            risk = "suspicious"
            note = "تغيير محلي جداً — غالباً شكلي أو غير مؤثر"
        elif num_affected <= 2:
            risk = "moderate"
            note = "تغيير متوسط — يحتاج مراجعة"
        else:
            risk = "structural"
            note = f"تغيير هيكلي عميق — يؤثر على {num_affected} وحدات"

        return {
            "affected_modules": num_affected,
            "modules": list(affected_modules),
            "dependency_chain": dependency_chain[:20],
            "risk": risk,
            "note": note,
        }

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 4: Test Gate
    # ───────────────────────────────────────────────────────────────────────

    async def generate_test(self, diff: str, files_changed: List[str]) -> Dict[str, Any]:
        """
        Guard 4: بوابة الاختبار — توليد اختبار يثبت التحسن
        
        Uses LLM to generate a pytest test case.
        """
        try:
            from mamoun.core.llm_client import get_llm_client
            llm = get_llm_client()

            truncated_diff = diff[:2000]
            if len(diff) > 2000:
                truncated_diff += f"\n... [truncated, {len(diff)} total chars]"

            response = await llm.think(
                prompt=f"""أنت مهندس اختبارات. اكتب اختبار pytest يثبت أن هذا التغيير حقيقي وليس شكلياً.

التغيير:
```
{truncated_diff}
```

الملفات المتأثرة: {files_changed[:10]}

اكتب اختباراً يفشل قبل التغيير وينجح بعده. الصيغة JSON:
{{"test_code": "import pytest\\n...", "description": "وصف الاختبار", "proves_improvement": true/false}}""",
                system="أنت مهندس اختبارات خبير. أجب فقط بصيغة JSON صالحة.",
                model="glm-5.1",
                temperature=0.3,
                json_mode=True,
            )

            result = response.extract_json()
            if result is None:
                import re
                text = response.text or ""
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    result = json.loads(json_match.group(0))

            if result and isinstance(result, dict):
                return {
                    "success": True,
                    "test_code": result.get("test_code", ""),
                    "description": result.get("description", ""),
                    "proves_improvement": result.get("proves_improvement", False),
                }

            return {"success": False, "test_code": "", "description": "فشل توليد الاختبار", "proves_improvement": False}

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return {"success": False, "test_code": "", "description": f"خطأ: {str(e)}", "proves_improvement": False}

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 5: Delta Analysis
    # ───────────────────────────────────────────────────────────────────────

    async def delta_analysis(self, before_metrics: Dict, after_metrics: Dict) -> Dict[str, Any]:
        """
        Guard 5: تحليل الفرق — مقارنة قبل وبعد
        
        If delta ≈ 0 within noise margin → REJECT (cosmetic)
        If delta negative → ROLLBACK
        If delta positive ≥ threshold → CONFIRM
        """
        result = await self.verify_metrics(before_metrics, after_metrics, min_improvement_pct=3.0)

        noise_margin = 2.0  # 2% noise margin
        any_significant_change = False
        any_regression = False

        for key, d in result.get("delta", {}).items():
            change = abs(d.get("change_pct", 0))
            if change > noise_margin:
                any_significant_change = True
            if not d.get("improved", True) and change > noise_margin:
                any_regression = True

        if any_regression:
            decision = "ROLLBACK"
            reason = "انحدار مكتشف — الأداء تدهور بعد التغيير"
        elif not any_significant_change:
            decision = "REJECT"
            reason = f"تغيير ضمن هامش الضوضاء ({noise_margin}%) — شكلي"
        elif result.get("passed"):
            decision = "CONFIRM"
            reason = "تحسن حقيقي مثبت بالأرقام"
        else:
            decision = "PARTIAL"
            reason = "بعض المقاييس تحسنت وبعضها لم يتغير"

        result["decision"] = decision
        result["reason"] = reason
        result["noise_margin_pct"] = noise_margin

        return result

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 6: Stagnation Detection
    # ───────────────────────────────────────────────────────────────────────

    async def detect_stagnation(self) -> Dict[str, Any]:
        """
        Guard 6: كشف الركود
        
        If last 5 improvements were L0 or rejected → CRITICAL stagnation
        Triggers Deep Scan Mode → forces L2/L3 proposals only
        """
        recent = self._history[-10:]
        if len(recent) < 3:
            return {"stagnation_level": "NONE", "consecutive_shallow": 0, "recommendation": "لا يوجد ركود"}

        consecutive_shallow = 0
        for r in reversed(recent):
            if r.impact_level == ImpactLevel.L0_COSMETIC or r.rejected:
                consecutive_shallow += 1
            else:
                break

        if consecutive_shallow >= 5:
            level = "CRITICAL"
            recommendation = "فحص معمّق مطلوب — 5+ تحسينات شكلية متتالية"
        elif consecutive_shallow >= 3:
            level = "WARNING"
            recommendation = "بداية ركود — التزم بتغييرات L2/L3 فقط"
        else:
            level = "NONE"
            recommendation = "لا يوجد ركود"

        # Area health classification
        area_health = {}
        for r in recent:
            for f in r.files_changed[:3]:
                area = str(Path(f).parent) if '/' in f else "root"
                if area not in area_health:
                    area_health[area] = {"total": 0, "verified": 0}
                area_health[area]["total"] += 1
                if r.verified:
                    area_health[area]["verified"] += 1

        for area, data in area_health.items():
            ratio = data["verified"] / max(data["total"], 1)
            if ratio < 0.3:
                data["status"] = "🔴 High Debt"
            elif ratio < 0.7:
                data["status"] = "🟡 Medium"
            else:
                data["status"] = "🟢 Healthy"

        return {
            "stagnation_level": level,
            "consecutive_shallow": consecutive_shallow,
            "recommendation": recommendation,
            "area_health": area_health,
            "total_improvements": len(self._history),
            "verified_count": sum(1 for r in self._history if r.verified),
            "rejected_count": sum(1 for r in self._history if r.rejected),
        }

    # ───────────────────────────────────────────────────────────────────────
    #  Guard 7: Historical Quality Model
    # ───────────────────────────────────────────────────────────────────────

    async def update_quality_model(self, record: ImprovementRecord):
        """
        Guard 7: نموذج الجودة — التعلم من التحسينات السابقة
        
        Stores the record and updates area health classifications.
        """
        self._save_record(record)
        logger.info(
            f"Quality model updated: {record.id} level={record.impact_level} "
            f"verified={record.verified} rejected={record.rejected}"
        )

    async def get_quality_summary(self) -> Dict[str, Any]:
        """Get a summary of improvement quality."""
        if not self._history:
            return {"total": 0, "message": "لا يوجد سجل تحسينات بعد"}

        by_level = {}
        for level in ImpactLevel:
            records = [r for r in self._history if r.impact_level == level.value]
            verified = sum(1 for r in records if r.verified)
            by_level[level.value] = {
                "total": len(records),
                "verified": verified,
                "rejected": sum(1 for r in records if r.rejected),
                "success_rate": round(verified / max(len(records), 1) * 100, 1),
            }

        return {
            "total": len(self._history),
            "by_level": by_level,
            "last_10": [
                {
                    "id": r.id,
                    "level": r.impact_level,
                    "verified": r.verified,
                    "rejected": r.rejected,
                    "reason": r.rejection_reason[:100] if r.rejection_reason else "",
                    "time": r.timestamp,
                }
                for r in self._history[-10:]
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Singleton
# ═══════════════════════════════════════════════════════════════════════════════

improvement_engine = ImprovementEngine()


def get_improvement_engine() -> ImprovementEngine:
    """Get the global improvement engine singleton."""
    if not improvement_engine._initialized:
        improvement_engine.initialize()
    return improvement_engine
