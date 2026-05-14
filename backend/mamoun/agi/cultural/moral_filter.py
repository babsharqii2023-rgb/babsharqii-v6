"""
BABSHARQII v10.0 — Moral Filter
المرشح الأخلاقي — يطبّق فحصاً أخلاقياً قبل كل استجابة

Pre-response filter that applies moral and cultural checks before
any response is sent to the user. Integrates with the IslamTrust
adapter and the values database.

v10 additions:
  - Multi-culture support via AdaptiveAlignmentEngine
  - Culture-specific sensitivity checking
  - Dynamic culture switching

Feature Flags:
  MAMOUN_ISLAMTRUST_MODE (default: false) — basic moral filter
  MAMOUN_CULTURAL_ADAPTIVE (default: false) — v10 multi-culture
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Optional

from mamoun.agi.cultural.islam_trust_adapter import IslamTrustAdapter, IslamTrustResult

logger = logging.getLogger(__name__)

ISLAMTRUST_MODE_ENABLED: bool = os.environ.get(
    "MAMOUN_ISLAMTRUST_MODE", "false"
).lower() in ("true", "1", "yes")

CULTURAL_ADAPTIVE_ENABLED: bool = os.environ.get(
    "MAMOUN_CULTURAL_ADAPTIVE", "false"
).lower() in ("true", "1", "yes")


@dataclass
class MoralFilterResult:
    """نتيجة المرشح الأخلاقي"""
    original_text: str = ""
    filtered_text: str = ""
    passed: bool = True
    alignment_score: float = 1.0
    violations: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    was_modified: bool = False


class MoralFilter:
    """
    المرشح الأخلاقي

    Applied BEFORE every response is sent to the user.
    Checks the response against:
    1. Islamic values (from values_db.yaml via IslamTrust)
    2. Cultural sensitivity (Arab/Islamic context)
    3. Safety rules (no harm, no illegal content)
    4. Bias detection (Western bias mitigation)

    If MAMOUN_ISLAMTRUST_MODE is false, the filter is a no-op.
    """

    # Forbidden content categories
    FORBIDDEN_PATTERNS = [
        "انتحار", "قتل", "عنف", "تعذيب", "إرهاب",
        "كحول", "خمر", "مخدرات", "قمار",
    ]

    def __init__(self, islam_trust: Optional[IslamTrustAdapter] = None, active_culture: str = "arabic_islamic"):
        self.islam_trust = islam_trust or IslamTrustAdapter()
        self.active_culture = active_culture
        self._adaptive_engine = None  # Lazy-loaded
        self._filter_count = 0
        self._violation_count = 0

    def apply(self, response_text: str, context: str = "") -> MoralFilterResult:
        """
        طبّق المرشح الأخلاقي على الاستجابة.

        Returns a MoralFilterResult with the (possibly modified) response.
        """
        if not ISLAMTRUST_MODE_ENABLED:
            return MoralFilterResult(
                original_text=response_text,
                filtered_text=response_text,
                passed=True,
                alignment_score=1.0,
            )

        self._filter_count += 1

        # Step 1: Safety check (forbidden content)
        safety_violations = self._check_safety(response_text)

        # Step 2: Cultural alignment check
        trust_result = self.islam_trust.evaluate_response(response_text, context)

        # Step 3: Bias detection
        bias_violations = self._check_western_bias(response_text)

        # Step 4 (v10): Multi-culture sensitivity check
        cultural_violations = []
        if CULTURAL_ADAPTIVE_ENABLED:
            cultural_violations = self._check_cultural_sensitivity(response_text, self.active_culture)
            # Apply adaptive filter
            adaptive = self._get_adaptive_engine()
            if adaptive:
                response_text = adaptive.apply_cultural_filter(response_text, self.active_culture)

        # Combine violations
        all_violations = safety_violations + trust_result.violations + bias_violations + cultural_violations
        all_recommendations = trust_result.recommendations

        # Determine if response passes
        passed = len(safety_violations) == 0 and trust_result.alignment_score >= 0.7

        # Modify response if needed
        filtered_text = response_text
        was_modified = False

        if not passed and all_violations:
            self._violation_count += 1
            # Apply cultural alignment
            filtered_text = self.islam_trust.align_response(response_text, context)
            was_modified = filtered_text != response_text

        return MoralFilterResult(
            original_text=response_text,
            filtered_text=filtered_text,
            passed=passed,
            alignment_score=trust_result.alignment_score,
            violations=all_violations,
            recommendations=all_recommendations,
            was_modified=was_modified,
        )

    def _check_safety(self, text: str) -> list[str]:
        """تحقق من المحتوى المحظور"""
        violations = []
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in text:
                # Context-aware: check if it's being discussed (not promoted)
                # Simple heuristic: if it's in a negative context, it's OK
                negative_context = any(
                    neg in text
                    for neg in ["تحريم", "نهي", "لا تفعل", "ممنوع", "خطر", "ضرر"]
                )
                if not negative_context:
                    violations.append(f"محتوى محظور محتمل: {pattern}")
        return violations

    def _check_western_bias(self, text: str) -> list[str]:
        """كشف التحيز الغربي"""
        violations = []

        # Check for Western-centric recommendations without Arab/Islamic alternative
        western_indicators = [
            "فردية", "استقلال تام", "حرية مطلقة",
            "علمانية", "فصل الدين عن",
        ]

        has_western = any(indicator in text for indicator in western_indicators)
        has_islamic_alternative = any(
            alt in text
            for alt in ["إسلامي", "عربي", "شرعي", "حلال", "أدب", "إحسان"]
        )

        if has_western and not has_islamic_alternative:
            violations.append("اقتراح غربي بدون بديل إسلامي/عربي")

        return violations

    def set_culture(self, culture_id: str) -> None:
        """تعيين الثقافة النشطة (v10)"""
        self.active_culture = culture_id

    def _check_cultural_sensitivity(self, text: str, culture_id: str) -> list[str]:
        """تحقق من الحساسية الثقافية (v10)"""
        violations = []
        adaptive = self._get_adaptive_engine()
        if not adaptive:
            return violations

        values = adaptive.load_culture_values(culture_id)
        if not values:
            return violations

        forbidden = values.get("forbidden_topics", [])
        for topic in forbidden:
            if topic.lower() in text.lower():
                violations.append(f"موضوع حساس في الثقافة {culture_id}: {topic}")

        return violations

    def _get_adaptive_engine(self):
        """تحميل كسول لمحرك المحاذاة التكيفية"""
        if self._adaptive_engine is None and CULTURAL_ADAPTIVE_ENABLED:
            try:
                from mamoun.agi.cultural.adaptive_alignment import AdaptiveAlignmentEngine
                self._adaptive_engine = AdaptiveAlignmentEngine()
            except ImportError:
                logger.warning("Cannot import AdaptiveAlignmentEngine")
        return self._adaptive_engine

    @property
    def stats(self) -> dict:
        """إحصائيات المرشح"""
        return {
            "total_filtered": self._filter_count,
            "violations_found": self._violation_count,
            "violation_rate": self._violation_count / self._filter_count if self._filter_count > 0 else 0.0,
            "active_culture": self.active_culture,
            "cultural_adaptive": CULTURAL_ADAPTIVE_ENABLED,
        }
