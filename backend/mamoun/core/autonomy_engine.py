"""
BABSHARQII v20.0 — Autonomy Engine (محرك الاستقلالية)
المحرك الذي ينقل مأمون من "يحتاج موافقة بشرية لكل شيء" إلى 95%+ استقلالية

هذا المحرك هو المفتاح للانتقال من الاعتماد الكامل على الموافقة البشرية
إلى التشغيل المستقل الآمن مع تصنيف ذكي للعمليات.

المستويات:
  SAFE     → موافقة تلقائية (تنسيق، تعليقات، توثيق)
  MODERATE → موافقة تلقائية بثقة >80% (إصلاح أعطال، إعادة هيكلة)
  RISKY    → تتطلب موافقة بشرية (ميزات جديدة، تغييرات API)
  CRITICAL → تتطلب موافقة بشرية + تحقق ثنائي (ترحيل قاعدة بيانات، أمان)

التعلم من RLHF:
  - كل قرار بشري (موافقة/رفض) يحدّث درجة الثقة لكل نوع عملية
  - العمليات الناجحة تزيد الثقة → موافقة تلقائية مستقبلية
  - العمليات المرفوضة تقلل الثقة → تصعيد للمستقبل
"""

import time
import json
import uuid
import logging
import sqlite3
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger("mamoun.core.autonomy_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# مستويات الأمان — Safety Tiers
# ═══════════════════════════════════════════════════════════════════════════════

class SafetyTier(str, Enum):
    """مستويات أمان العمليات — كل مستوى يحدد سياسة الموافقة"""
    SAFE = "safe"             # آمن — موافقة تلقائية دائماً
    MODERATE = "moderate"     # متوسط — موافقة تلقائية مع تسجيل
    RISKY = "risky"           # محفوف بالمخاطر — يتطلب موافقة بشرية
    CRITICAL = "critical"     # حرج — موافقة بشرية + تحقق ثنائي


# ═══════════════════════════════════════════════════════════════════════════════
# نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OperationClassification:
    """تصنيف العملية — يحدد مستوى الأمان والثقة"""
    operation_type: str = ""
    target: str = ""
    scope: str = "single_file"      # single_file, multi_file, system_level
    reversibility: str = "easy"     # easy, moderate, hard, impossible
    safety_tier: SafetyTier = SafetyTier.MODERATE
    confidence: float = 0.5
    reasoning: str = ""
    file_type: str = ""

    def to_dict(self) -> dict:
        return {
            "operation_type": self.operation_type,
            "target": self.target,
            "scope": self.scope,
            "reversibility": self.reversibility,
            "safety_tier": self.safety_tier.value,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning[:500],
            "file_type": self.file_type,
        }


@dataclass
class AutonomyDecision:
    """قرار الاستقلالية — نتيجة تقييم الموافقة التلقائية"""
    operation_id: str = ""
    operation_type: str = ""
    safety_tier: SafetyTier = SafetyTier.MODERATE
    auto_approved: bool = False
    confidence: float = 0.0
    reason: str = ""
    requires_2fa: bool = False
    timestamp: float = field(default_factory=time.time)
    human_decision: str = ""        # approved, rejected, pending
    human_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type,
            "safety_tier": self.safety_tier.value,
            "auto_approved": self.auto_approved,
            "confidence": round(self.confidence, 4),
            "reason": self.reason[:500],
            "requires_2fa": self.requires_2fa,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat() if self.timestamp else "",
            "human_decision": self.human_decision,
        }


@dataclass
class AutonomyState:
    """حالة الاستقلالية — تتبع المستوى الحالي والإحصائيات"""
    autonomy_level: float = 0.0     # 0-100%
    total_decisions: int = 0
    auto_approved_count: int = 0
    human_approved_count: int = 0
    human_rejected_count: int = 0
    human_override_count: int = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "autonomy_level": round(self.autonomy_level, 2),
            "total_decisions": self.total_decisions,
            "auto_approved_count": self.auto_approved_count,
            "human_approved_count": self.human_approved_count,
            "human_rejected_count": self.human_rejected_count,
            "human_override_count": self.human_override_count,
            "auto_approval_rate": round(
                self.auto_approved_count / max(1, self.total_decisions), 4
            ),
            "last_updated": self.last_updated,
            "last_updated_iso": datetime.fromtimestamp(self.last_updated).isoformat() if self.last_updated else "",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# قواعد التصنيف — Classification Rules
# ═══════════════════════════════════════════════════════════════════════════════

# أنواع العمليات ومستوياتها الافتراضية
OPERATION_TIER_DEFAULTS: Dict[str, SafetyTier] = {
    # ─── SAFE — آمن ────────────────────────────────────────────────
    "format_code": SafetyTier.SAFE,
    "add_comments": SafetyTier.SAFE,
    "add_documentation": SafetyTier.SAFE,
    "fix_typo": SafetyTier.SAFE,
    "update_readme": SafetyTier.SAFE,
    "style_change": SafetyTier.SAFE,
    "whitespace_fix": SafetyTier.SAFE,
    "add_logging": SafetyTier.SAFE,
    "rename_variable": SafetyTier.SAFE,

    # ─── MODERATE — متوسط ──────────────────────────────────────────
    "bug_fix": SafetyTier.MODERATE,
    "refactoring": SafetyTier.MODERATE,
    "performance_improvement": SafetyTier.MODERATE,
    "dependency_update": SafetyTier.MODERATE,
    "test_addition": SafetyTier.MODERATE,
    "config_change": SafetyTier.MODERATE,
    "error_handling": SafetyTier.MODERATE,

    # ─── RISKY — محفوف بالمخاطر ────────────────────────────────────
    "new_feature": SafetyTier.RISKY,
    "api_change": SafetyTier.RISKY,
    "architecture_change": SafetyTier.RISKY,
    "new_dependency": SafetyTier.RISKY,
    "file_restructure": SafetyTier.RISKY,
    "data_model_change": SafetyTier.RISKY,

    # ─── CRITICAL — حرج ────────────────────────────────────────────
    "database_migration": SafetyTier.CRITICAL,
    "security_change": SafetyTier.CRITICAL,
    "auth_change": SafetyTier.CRITICAL,
    "env_variable_change": SafetyTier.CRITICAL,
    "production_deploy": SafetyTier.CRITICAL,
    "safety_rule_change": SafetyTier.CRITICAL,
    "law_modification": SafetyTier.CRITICAL,
}

# أنواع الملفات ومستويات الأمان
FILE_TYPE_TIERS: Dict[str, SafetyTier] = {
    ".md": SafetyTier.SAFE,
    ".txt": SafetyTier.SAFE,
    ".json": SafetyTier.MODERATE,
    ".yaml": SafetyTier.MODERATE,
    ".yml": SafetyTier.MODERATE,
    ".toml": SafetyTier.MODERATE,
    ".py": SafetyTier.MODERATE,
    ".tsx": SafetyTier.MODERATE,
    ".ts": SafetyTier.MODERATE,
    ".js": SafetyTier.MODERATE,
    ".css": SafetyTier.SAFE,
    ".html": SafetyTier.SAFE,
    ".sql": SafetyTier.RISKY,
    ".env": SafetyTier.CRITICAL,
    ".key": SafetyTier.CRITICAL,
    ".pem": SafetyTier.CRITICAL,
}

# نطاق التغيير ومستوى الأمان (لا يُستخدم كحد أعلى بل كمؤشر فقط)
# ملاحظة: single_file لا يرفع المستوى — نوع العملية ونوع الملف هما الأساس
SCOPE_TIERS: Dict[str, SafetyTier] = {
    "single_file": SafetyTier.SAFE,
    "multi_file": SafetyTier.RISKY,
    "system_level": SafetyTier.CRITICAL,
}

# قابلية العكس ومستوى الأمان
REVERSIBILITY_TIERS: Dict[str, SafetyTier] = {
    "easy": SafetyTier.SAFE,
    "moderate": SafetyTier.MODERATE,
    "hard": SafetyTier.RISKY,
    "impossible": SafetyTier.CRITICAL,
}

# عتبة الثقة للموافقة التلقائية على العمليات المتوسطة
MODERATE_AUTO_APPROVE_THRESHOLD = 0.80


# ═══════════════════════════════════════════════════════════════════════════════
# محرك تتبع الثقة — ConfidenceTracker
# ═══════════════════════════════════════════════════════════════════════════════

class ConfidenceTracker:
    """
    متتبع الثقة — يتابع درجة الثقة لكل نوع عملية
    ويحدّثها بناءً على قرارات المستخدم (RLHF)

    القاعدة: الثقة تبدأ من 0.5 وتتحرك ببطء نحو الأعلى أو الأسفل
    - موافقة بشرية → +0.03
    - رفض بشري → -0.08
    - موافقة تلقائية ناجحة → +0.01
    - موافقة تلقائية فاشلة → -0.15
    """

    def __init__(self):
        self._confidence: Dict[str, float] = {}
        self._sample_counts: Dict[str, int] = {}

    def get_confidence(self, operation_type: str) -> float:
        """الحصول على درجة الثقة لنوع عملية"""
        return self._confidence.get(operation_type, 0.5)

    def update_from_human_approval(self, operation_type: str):
        """تحديث الثقة بعد موافقة بشرية"""
        current = self.get_confidence(operation_type)
        count = self._sample_counts.get(operation_type, 0)
        # تحديث أسي مرجح — يتباطأ مع زيادة العينات
        alpha = max(0.01, 0.1 / (1 + count * 0.05))
        new_confidence = current + alpha * (1.0 - current)
        self._confidence[operation_type] = min(1.0, new_confidence)
        self._sample_counts[operation_type] = count + 1

    def update_from_human_rejection(self, operation_type: str):
        """تحديث الثقة بعد رفض بشري"""
        current = self.get_confidence(operation_type)
        count = self._sample_counts.get(operation_type, 0)
        alpha = max(0.02, 0.15 / (1 + count * 0.05))
        new_confidence = current - alpha * current
        self._confidence[operation_type] = max(0.0, new_confidence)
        self._sample_counts[operation_type] = count + 1

    def update_from_auto_success(self, operation_type: str):
        """تحديث الثقة بعد موافقة تلقائية ناجحة"""
        current = self.get_confidence(operation_type)
        # زيادة بطيئة جداً للموافقات التلقائية الناجحة
        self._confidence[operation_type] = min(1.0, current + 0.01)

    def update_from_auto_failure(self, operation_type: str):
        """تحديث الثقة بعد موافقة تلقائية فاشلة"""
        current = self.get_confidence(operation_type)
        # عقوبة كبيرة — سلامة أولاً
        self._confidence[operation_type] = max(0.0, current - 0.15)

    def to_dict(self) -> dict:
        """تحويل إلى قاموس"""
        return {
            "confidences": {k: round(v, 4) for k, v in self._confidence.items()},
            "sample_counts": dict(self._sample_counts),
        }

    def load_from_dict(self, data: dict):
        """تحميل من قاموس"""
        self._confidence = {k: float(v) for k, v in data.get("confidences", {}).items()}
        self._sample_counts = {k: int(v) for k, v in data.get("sample_counts", {}).items()}


# ═══════════════════════════════════════════════════════════════════════════════
# محرك الموافقة التلقائية — AutoApprovalEngine
# ═══════════════════════════════════════════════════════════════════════════════

class AutoApprovalEngine:
    """
    محرك الموافقة التلقائية — يقرر ما إذا كانت العملية تُموافق تلقائياً

    القواعد:
    1. SAFE → موافقة تلقائية دائماً (تنسيق، تعليقات، توثيق)
    2. MODERATE → موافقة تلقائية إذا كانت الثقة > 80%
    3. RISKY → تصعيد بشري دائماً
    4. CRITICAL → تصعيد بشري + تحقق ثنائي
    """

    def __init__(self, confidence_tracker: ConfidenceTracker):
        self._tracker = confidence_tracker

    def evaluate(self, classification: OperationClassification) -> AutonomyDecision:
        """
        تقييم العملية — هل تُموافق تلقائياً؟

        يُرجع قرار الاستقلالية مع السبب
        """
        decision = AutonomyDecision(
            operation_id=f"auto_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            operation_type=classification.operation_type,
            safety_tier=classification.safety_tier,
            confidence=classification.confidence,
        )

        tier = classification.safety_tier

        if tier == SafetyTier.SAFE:
            # ─── آمن → موافقة تلقائية ────────────────────────────────
            decision.auto_approved = True
            decision.reason = f"عملية آمنة ({classification.operation_type}) — موافقة تلقائية"
            decision.confidence = max(classification.confidence, 0.95)

        elif tier == SafetyTier.MODERATE:
            # ─── متوسط → موافقة تلقائية إذا الثقة > 80% ─────────────
            type_confidence = self._tracker.get_confidence(classification.operation_type)
            effective_confidence = (classification.confidence + type_confidence) / 2.0
            decision.confidence = effective_confidence

            if effective_confidence >= MODERATE_AUTO_APPROVE_THRESHOLD:
                decision.auto_approved = True
                decision.reason = (
                    f"عملية متوسطة ({classification.operation_type}) — "
                    f"ثقة عالية {effective_confidence:.2f} ≥ {MODERATE_AUTO_APPROVE_THRESHOLD}"
                )
            else:
                decision.auto_approved = False
                decision.reason = (
                    f"عملية متوسطة ({classification.operation_type}) — "
                    f"ثقة منخفضة {effective_confidence:.2f} < {MODERATE_AUTO_APPROVE_THRESHOLD}"
                )

        elif tier == SafetyTier.RISKY:
            # ─── محفوف بالمخاطر → تصعيد بشري ──────────────────────────
            decision.auto_approved = False
            decision.reason = (
                f"عملية محفوفة بالمخاطر ({classification.operation_type}) — "
                f"تتطلب موافقة بشرية"
            )

        elif tier == SafetyTier.CRITICAL:
            # ─── حرج → تصعيد بشري + تحقق ثنائي ────────────────────────
            decision.auto_approved = False
            decision.requires_2fa = True
            decision.reason = (
                f"عملية حرجة ({classification.operation_type}) — "
                f"تتطلب موافقة بشرية + تحقق ثنائي"
            )

        return decision


# ═══════════════════════════════════════════════════════════════════════════════
# محرك الاستقلالية الرئيسي — AutonomyEngine
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomyEngine:
    """
    محرك الاستقلالية — المفتاح للانتقال إلى 95%+ استقلالية

    المسؤوليات:
    1. تصنيف العمليات حسب مستوى الأمان
    2. تقرير الموافقة التلقائية
    3. تعلم قرارات المستخدم (RLHF)
    4. تتبع حالة الاستقلالية
    5. تصعيد العمليات الخطرة

    الاستخدام:
        engine = AutonomyEngine()
        engine.initialize()
        result = engine.classify_operation("bug_fix", "main.py", "single_file", "easy")
        approval = engine.should_auto_approve(result)
        if approval["auto_approved"]:
            # تنفيذ العملية
            pass
        else:
            # طلب موافقة بشرية
            pass
    """

    # الملفات المحمية — دائماً CRITICAL
    PROTECTED_TARGETS = {
        "laws.yaml", "safety_guard.py", "approval_gate.py",
        ".env", ".key", ".pem", ".secret",
        "safety_gate_client.py", "self_modifier.py",
        "autonomy_engine.py",
    }

    def __init__(self, db_path: str = None):
        self._db_path = db_path or str(UNIFIED_DB_PATH)
        self._confidence_tracker = ConfidenceTracker()
        self._auto_approval = AutoApprovalEngine(self._confidence_tracker)
        self._state = AutonomyState()
        self._recent_decisions: List[AutonomyDecision] = []
        self._initialized = False
        self._counter = 0

    def initialize(self) -> bool:
        """تهيئة المحرك — إنشاء الجداول وتحميل الحالة"""
        try:
            self._ensure_schema()
            self._load_state()
            self._load_confidence()
            self._load_recent_decisions()
            self._initialized = True
            logger.info(
                "AutonomyEngine initialized — autonomy=%.1f%%, decisions=%d",
                self._state.autonomy_level, self._state.total_decisions,
            )
            return True
        except Exception as e:
            logger.error("AutonomyEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS at_decisions (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    safety_tier TEXT NOT NULL,
                    auto_approved INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    reason TEXT DEFAULT '',
                    requires_2fa INTEGER DEFAULT 0,
                    timestamp REAL DEFAULT 0.0,
                    human_decision TEXT DEFAULT 'pending',
                    human_reason TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS at_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS at_confidence (
                    operation_type TEXT PRIMARY KEY,
                    confidence REAL DEFAULT 0.5,
                    sample_count INTEGER DEFAULT 0
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_type ON at_decisions(operation_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_decisions_timestamp ON at_decisions(timestamp DESC)"
            )
            conn.commit()
        finally:
            conn.close()

    def _load_state(self):
        """تحميل حالة الاستقلالية من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute("SELECT key, value FROM at_state")
            state_data = {}
            for key, value in cur.fetchall():
                state_data[key] = value

            if state_data:
                self._state.autonomy_level = float(state_data.get("autonomy_level", 0.0))
                self._state.total_decisions = int(state_data.get("total_decisions", 0))
                self._state.auto_approved_count = int(state_data.get("auto_approved_count", 0))
                self._state.human_approved_count = int(state_data.get("human_approved_count", 0))
                self._state.human_rejected_count = int(state_data.get("human_rejected_count", 0))
                self._state.human_override_count = int(state_data.get("human_override_count", 0))
                self._state.last_updated = float(state_data.get("last_updated", time.time()))
        finally:
            conn.close()

    def _load_confidence(self):
        """تحميل درجات الثقة من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute("SELECT operation_type, confidence, sample_count FROM at_confidence")
            confidences = {}
            counts = {}
            for row in cur.fetchall():
                confidences[row[0]] = row[1]
                counts[row[0]] = row[2]
            self._confidence_tracker.load_from_dict({
                "confidences": confidences,
                "sample_counts": counts,
            })
        finally:
            conn.close()

    def _load_recent_decisions(self):
        """تحميل القرارات الأخيرة من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM at_decisions ORDER BY timestamp DESC LIMIT 50"
            )
            self._recent_decisions = []
            for row in cur.fetchall():
                self._recent_decisions.append(AutonomyDecision(
                    operation_id=row["operation_id"],
                    operation_type=row["operation_type"],
                    safety_tier=SafetyTier(row["safety_tier"]),
                    auto_approved=bool(row["auto_approved"]),
                    confidence=row["confidence"],
                    reason=row["reason"],
                    requires_2fa=bool(row["requires_2fa"]),
                    timestamp=row["timestamp"],
                    human_decision=row["human_decision"],
                    human_reason=row["human_reason"],
                ))
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════════════
    # تصنيف العمليات — Operation Classification
    # ═══════════════════════════════════════════════════════════════════════

    def classify_operation(
        self,
        operation_type: str,
        target: str,
        scope: str,
        reversibility: str,
    ) -> dict:
        """
        تصنيف عملية — يحدد مستوى الأمان والثقة

        المعايير:
        1. نوع العملية (الافتراضي حسب OPERATION_TIER_DEFAULTS)
        2. نوع الملف المُعدَّل
        3. نطاق التغيير (ملف واحد، عدة ملفات، مستوى النظام)
        4. قابلية العكس
        5. نجاح العمليات المشابهة سابقاً (RLHF)
        6. هل الهدف محمي؟

        Args:
            operation_type: نوع العملية (مثلاً bug_fix, new_feature, etc.)
            target: الملف أو المورد المستهدف
            scope: نطاق التغيير (single_file, multi_file, system_level)
            reversibility: قابلية العكس (easy, moderate, hard, impossible)

        Returns:
            قاموس بتصنيف العملية
        """
        if not self._initialized:
            self.initialize()

        classification = OperationClassification(
            operation_type=operation_type,
            target=target,
            scope=scope,
            reversibility=reversibility,
        )

        # 1. تحديد نوع الملف
        file_ext = Path(target).suffix.lower() if target else ""
        classification.file_type = file_ext

        # 2. تحديد المستوى الأساسي من نوع العملية
        base_tier = OPERATION_TIER_DEFAULTS.get(operation_type, SafetyTier.MODERATE)

        # 3. التحقق من الأهداف المحمية — دائماً CRITICAL
        target_name = target.split("/")[-1] if "/" in target else target
        if target_name in self.PROTECTED_TARGETS:
            base_tier = SafetyTier.CRITICAL
            classification.reasoning += "هدف محمي → CRITICAL. "

        # 4. تحديد المستوى من نوع الملف
        file_tier = FILE_TYPE_TIERS.get(file_ext, SafetyTier.MODERATE)

        # 5. تحديد المستوى من النطاق
        scope_tier = SCOPE_TIERS.get(scope, SafetyTier.MODERATE)

        # 6. تحديد المستوى من قابلية العكس
        rev_tier = REVERSIBILITY_TIERS.get(reversibility, SafetyTier.MODERATE)

        # 7. اختيار المستوى الأعلى (الأكثر حذراً)
        tier_order = {
            SafetyTier.SAFE: 0,
            SafetyTier.MODERATE: 1,
            SafetyTier.RISKY: 2,
            SafetyTier.CRITICAL: 3,
        }
        tiers = [
            (base_tier, "نوع العملية"),
            (file_tier, "نوع الملف"),
            (scope_tier, "نطاق التغيير"),
            (rev_tier, "قابلية العكس"),
        ]
        max_tier = max(tiers, key=lambda t: tier_order[t[0]])
        classification.safety_tier = max_tier[0]

        # تسجيل أسباب التصنيف
        for tier, label in tiers:
            classification.reasoning += f"{label}: {tier.value}. "

        # 8. حساب الثقة بناءً على التاريخ
        historical_confidence = self._confidence_tracker.get_confidence(operation_type)
        classification.confidence = historical_confidence

        # 9. تعديل الثقة بناءً على النطاق وقابلية العكس
        if scope == "system_level":
            classification.confidence *= 0.5
        elif scope == "multi_file":
            classification.confidence *= 0.8

        if reversibility == "impossible":
            classification.confidence *= 0.3
        elif reversibility == "hard":
            classification.confidence *= 0.6

        classification.confidence = max(0.0, min(1.0, classification.confidence))

        # 10. تعديل المستوى إذا كانت الثقة التاريخية عالية جداً
        if (
            historical_confidence >= 0.95
            and classification.safety_tier == SafetyTier.RISKY
            and scope != "system_level"
        ):
            classification.safety_tier = SafetyTier.MODERATE
            classification.reasoning += "ثقة تاريخية عالية ≥0.95 → خُفض المستوى إلى MODERATE. "

        logger.info(
            "Classified %s on %s → %s (confidence=%.2f)",
            operation_type, target, classification.safety_tier.value,
            classification.confidence,
        )

        return classification.to_dict()

    # ═══════════════════════════════════════════════════════════════════════
    # تقرير الموافقة التلقائية — Auto-Approval Decision
    # ═══════════════════════════════════════════════════════════════════════

    def should_auto_approve(self, operation: dict) -> dict:
        """
        تقرير الموافقة التلقائية — هل تُنفَّذ العملية بدون موافقة بشرية؟

        Args:
            operation: قاموس تصنيف العملية (من classify_operation)

        Returns:
            قاموس بقرار الموافقة
        """
        if not self._initialized:
            self.initialize()

        # تحويل القاموس إلى كائن تصنيف
        classification = OperationClassification(
            operation_type=operation.get("operation_type", ""),
            target=operation.get("target", ""),
            scope=operation.get("scope", "single_file"),
            reversibility=operation.get("reversibility", "easy"),
            safety_tier=SafetyTier(operation.get("safety_tier", "moderate")),
            confidence=operation.get("confidence", 0.5),
            file_type=operation.get("file_type", ""),
        )

        # تقييم الموافقة التلقائية
        decision = self._auto_approval.evaluate(classification)

        # حفظ القرار في قاعدة البيانات
        self._persist_decision(decision)

        # تحديث الحالة
        self._state.total_decisions += 1
        if decision.auto_approved:
            self._state.auto_approved_count += 1

        # حساب مستوى الاستقلالية
        self._update_autonomy_level()

        # إضافة للقرارات الأخيرة
        self._recent_decisions.insert(0, decision)
        if len(self._recent_decisions) > 100:
            self._recent_decisions = self._recent_decisions[:100]

        # حفظ الحالة
        self._persist_state()

        logger.info(
            "Auto-approve decision for %s: %s (confidence=%.2f)",
            decision.operation_type,
            "YES" if decision.auto_approved else "NO",
            decision.confidence,
        )

        return decision.to_dict()

    # ═══════════════════════════════════════════════════════════════════════
    # تسجيل قرارات المستخدم — RLHF Feedback
    # ═══════════════════════════════════════════════════════════════════════

    def record_human_decision(
        self,
        operation_id: str,
        approved: bool,
        reason: str = "",
    ):
        """
        تسجيل قرار بشري — يحدّث درجات الثقة (RLHF)

        عند موافقة المستخدم:
        - تزداد ثقة نوع العملية
        - تُسجل الموافقة

        عند رفض المستخدم:
        - تقل ثقة نوع العملية
        - تُسجل الرفض
        - يُحسب كتجاوز بشري إذا كانت العملية موافقة تلقائية

        Args:
            operation_id: معرف العملية
            approved: هل وافق المستخدم؟
            reason: سبب القرار (اختياري)
        """
        if not self._initialized:
            self.initialize()

        # البحث عن القرار
        decision = None
        for d in self._recent_decisions:
            if d.operation_id == operation_id:
                decision = d
                break

        if not decision:
            # محاولة البحث في قاعدة البيانات
            decision = self._load_decision_from_db(operation_id)

        if not decision:
            logger.warning("Decision not found: %s", operation_id)
            return

        # تحديث القرار
        decision.human_decision = "approved" if approved else "rejected"
        decision.human_reason = reason

        # تحديث الثقة بناءً على القرار
        op_type = decision.operation_type
        if approved:
            self._confidence_tracker.update_from_human_approval(op_type)
            self._state.human_approved_count += 1

            # إذا كانت موافقة تلقائية سابقة ووافق عليها الإنسان → نجاح
            if decision.auto_approved:
                self._confidence_tracker.update_from_auto_success(op_type)
        else:
            self._confidence_tracker.update_from_human_rejection(op_type)
            self._state.human_rejected_count += 1

            # إذا كانت موافقة تلقائية ورفضها الإنسان → فشل ذريع
            if decision.auto_approved:
                self._confidence_tracker.update_from_auto_failure(op_type)
                self._state.human_override_count += 1
                logger.warning(
                    "Human override! Auto-approved operation %s was rejected: %s",
                    operation_id, reason,
                )

        # حفظ التحديثات
        self._persist_decision_update(decision)
        self._persist_confidence()
        self._update_autonomy_level()
        self._persist_state()

        logger.info(
            "Human decision recorded for %s: %s (reason: %s)",
            operation_id, "approved" if approved else "rejected", reason[:100],
        )

    # ═══════════════════════════════════════════════════════════════════════
    # التصعيد — Escalation
    # ═══════════════════════════════════════════════════════════════════════

    def escalate(self, operation: dict, reason: str) -> dict:
        """
        تصعيد عملية — طلب تدخل بشري عاجل

        يُستخدم عندما يكتشف النظام أن العملية تحتاج مراجعة فورية.
        ينشئ قرار تصعيد ويُسجله.

        Args:
            operation: قاموس العملية
            reason: سبب التصعيد

        Returns:
            قاموس قرار التصعيد
        """
        if not self._initialized:
            self.initialize()

        decision = AutonomyDecision(
            operation_id=f"esc_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            operation_type=operation.get("operation_type", "unknown"),
            safety_tier=SafetyTier(operation.get("safety_tier", "critical")),
            auto_approved=False,
            confidence=0.0,
            reason=f"تصعيد: {reason}",
            requires_2fa=operation.get("safety_tier") == "critical",
        )

        self._persist_decision(decision)
        self._state.total_decisions += 1
        self._persist_state()

        logger.warning(
            "Escalation: %s — %s", decision.operation_id, reason,
        )

        return decision.to_dict()

    # ═══════════════════════════════════════════════════════════════════════
    # الاستعلامات — Queries
    # ═══════════════════════════════════════════════════════════════════════

    def get_autonomy_status(self) -> dict:
        """الحصول على حالة الاستقلالية الكاملة"""
        if not self._initialized:
            self.initialize()
        return self._state.to_dict()

    def get_confidence_for_type(self, operation_type: str) -> float:
        """الحصول على درجة الثقة لنوع عملية"""
        if not self._initialized:
            self.initialize()
        return round(self._confidence_tracker.get_confidence(operation_type), 4)

    def get_recent_decisions(self, limit: int = 20) -> list:
        """الحصول على القرارات الأخيرة"""
        if not self._initialized:
            self.initialize()
        return [d.to_dict() for d in self._recent_decisions[:limit]]

    def get_status(self) -> dict:
        """الحصول على حالة المحرك الكاملة"""
        if not self._initialized:
            self.initialize()
        return {
            "initialized": self._initialized,
            "autonomy": self._state.to_dict(),
            "confidence_tracker": self._confidence_tracker.to_dict(),
            "recent_decisions_count": len(self._recent_decisions),
            "moderate_threshold": MODERATE_AUTO_APPROVE_THRESHOLD,
            "operation_tiers": {k: v.value for k, v in OPERATION_TIER_DEFAULTS.items()},
        }

    # ═══════════════════════════════════════════════════════════════════════
    # دوال داخلية — Internal Methods
    # ═══════════════════════════════════════════════════════════════════════

    def _update_autonomy_level(self):
        """
        تحديث مستوى الاستقلالية — نسبة القرارات الموافق عليها تلقائياً

        الحساب:
        - نسبة الموافقات التلقائية = auto_approved / total
        - تعديل بناءً على التجاوزات البشرية (-5% لكل تجاوز)
        - حد أقصى 95% (دائماً هناك حد أدنى من الإشراف)
        """
        if self._state.total_decisions == 0:
            self._state.autonomy_level = 0.0
            return

        base_rate = self._state.auto_approved_count / self._state.total_decisions
        override_penalty = min(0.3, self._state.human_override_count * 0.05)
        self._state.autonomy_level = max(0.0, min(95.0, (base_rate - override_penalty) * 100))
        self._state.last_updated = time.time()

    def _load_decision_from_db(self, operation_id: str) -> Optional[AutonomyDecision]:
        """تحميل قرار من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute(
                "SELECT * FROM at_decisions WHERE operation_id = ?",
                (operation_id,),
            )
            row = cur.fetchone()
            if row:
                return AutonomyDecision(
                    operation_id=row["operation_id"],
                    operation_type=row["operation_type"],
                    safety_tier=SafetyTier(row["safety_tier"]),
                    auto_approved=bool(row["auto_approved"]),
                    confidence=row["confidence"],
                    reason=row["reason"],
                    requires_2fa=bool(row["requires_2fa"]),
                    timestamp=row["timestamp"],
                    human_decision=row["human_decision"],
                    human_reason=row["human_reason"],
                )
            return None
        finally:
            conn.close()

    def _persist_decision(self, decision: AutonomyDecision):
        """حفظ قرار في قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO at_decisions
                (operation_id, operation_type, safety_tier, auto_approved,
                 confidence, reason, requires_2fa, timestamp,
                 human_decision, human_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.operation_id,
                decision.operation_type,
                decision.safety_tier.value,
                1 if decision.auto_approved else 0,
                decision.confidence,
                decision.reason[:1000],
                1 if decision.requires_2fa else 0,
                decision.timestamp,
                decision.human_decision,
                decision.human_reason[:500],
            ))
            conn.commit()
        finally:
            conn.close()

    def _persist_decision_update(self, decision: AutonomyDecision):
        """تحديث قرار في قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                UPDATE at_decisions
                SET human_decision = ?, human_reason = ?
                WHERE operation_id = ?
            """, (
                decision.human_decision,
                decision.human_reason[:500],
                decision.operation_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def _persist_state(self):
        """حفظ حالة الاستقلالية"""
        conn = get_db_connection(self._db_path)
        try:
            state_items = {
                "autonomy_level": str(self._state.autonomy_level),
                "total_decisions": str(self._state.total_decisions),
                "auto_approved_count": str(self._state.auto_approved_count),
                "human_approved_count": str(self._state.human_approved_count),
                "human_rejected_count": str(self._state.human_rejected_count),
                "human_override_count": str(self._state.human_override_count),
                "last_updated": str(self._state.last_updated),
            }
            for key, value in state_items.items():
                conn.execute(
                    "INSERT OR REPLACE INTO at_state (key, value) VALUES (?, ?)",
                    (key, value),
                )
            conn.commit()
        finally:
            conn.close()

    def _persist_confidence(self):
        """حفظ درجات الثقة"""
        conn = get_db_connection(self._db_path)
        try:
            data = self._confidence_tracker.to_dict()
            for op_type, confidence in data.get("confidences", {}).items():
                sample_count = data.get("sample_counts", {}).get(op_type, 0)
                conn.execute("""
                    INSERT OR REPLACE INTO at_confidence
                    (operation_type, confidence, sample_count)
                    VALUES (?, ?, ?)
                """, (op_type, confidence, sample_count))
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton — النسخة الوحيدة من المحرك
# ═══════════════════════════════════════════════════════════════════════════════

autonomy_engine = AutonomyEngine()
