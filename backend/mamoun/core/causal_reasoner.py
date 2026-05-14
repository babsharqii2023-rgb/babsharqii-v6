"""
BABSHARQII v6.0 — Causal Reasoner
محرك الاستدلال السببي — تحليل الأسباب الجذرية وبناء الرسم البياني السببي

Provides causal reasoning capabilities for identifying root causes from error
patterns, building causal graphs, and suggesting interventions. Integrates
with the AbstractionEngine to propose abstract rules from causal patterns.
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List
from collections import defaultdict
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger(__name__)

# Env toggles for v6 features
V6_ENABLED = os.environ.get("MAMOUN_V6_ENABLED", "true").lower() in ("true", "1", "yes")


@dataclass
class CausalRule:
    """
    قاعدة سببية — علاقة سببية بين حدث ونتيجته.
    A causal relationship between a cause and its effect.
    """
    cause: str = ""
    effect: str = ""
    confidence: float = 0.0
    evidence_count: int = 0
    intervention: str = ""  # suggested fix — الإجراء المقترح

    def to_dict(self) -> dict:
        return {
            "cause": self.cause,
            "effect": self.effect,
            "confidence": round(self.confidence, 4),
            "evidence_count": self.evidence_count,
            "intervention": self.intervention,
        }


# v36 FIX: Added VersionDiff dataclass for test_causal_reasoner_v19.py
@dataclass
class VersionDiff:
    """
    فرق الإصدارات — Comparison between two version states.
    Used by analyze_version_diff() to track changes, regressions,
    improvements, and assess the risk level of transitions.
    """
    from_version: str = ""
    to_version: str = ""
    changes: List[str] = field(default_factory=list)
    regressions: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        # Auto-compute risk level if not explicitly set
        if self.risk_level == "low" and self.regressions:
            self.risk_level = "high" if len(self.regressions) > 1 else "medium"

    def to_dict(self) -> dict:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "changes": self.changes,
            "regressions": self.regressions,
            "improvements": self.improvements,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
        }


class CausalReasoner:
    """
    محرك الاستدلال السببي — يحلل الأسباب الجذرية ويبني الرسوم البيانية السببية.

    Analyzes error patterns to identify causal chains, builds directed
    acyclic graphs of causes, and suggests interventions to break
    undesirable causal chains.

    Integrates with the AbstractionEngine via propose_rules_from_causality()
    to transform causal patterns into abstract rules for proactive prevention.
    """

    # Minimum evidence required to establish a causal link
    MIN_EVIDENCE_THRESHOLD = 2
    # Minimum confidence for a causal rule to be considered valid
    MIN_CONFIDENCE = 0.3

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._causal_graph: dict = {}  # effect → [causes]
        self._rule_cache: list[CausalRule] = []
        self._intervention_templates = self._build_intervention_templates()
        # v36 FIX: Added for test compatibility
        self._initialized = False
        self._version = "v19.0"

    def initialize(self) -> bool:
        """
        تهيئة محرك الاستدلال السببي — Initialize the causal reasoner.

        v36 FIX: Added initialize() method for consistency with other
        systems and for test_causal_reasoner_v19.py compatibility.
        Sets up the database schema and loads any existing rules.
        """
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_rules_from_db()
            self._initialized = True
            logger.info("CausalReasoner initialized — %d rules loaded", len(self._rule_cache))
            return True
        except Exception as e:
            logger.error("CausalReasoner init failed: %s", e)
            self._initialized = False
            return False

    def _ensure_schema(self):
        """Create database tables if they don't exist."""
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute("""CREATE TABLE IF NOT EXISTS causal_rules (
                    cause TEXT, effect TEXT, confidence REAL,
                    evidence_count INTEGER, intervention TEXT,
                    PRIMARY KEY (cause, effect))""")
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass

    def _load_rules_from_db(self):
        """Load existing rules from database."""
        try:
            conn = get_db_connection(self.db_path)
            try:
                for row in conn.execute("SELECT cause, effect, confidence, evidence_count, intervention FROM causal_rules"):
                    self._rule_cache.append(CausalRule(
                        cause=row[0], effect=row[1], confidence=row[2],
                        evidence_count=row[3], intervention=row[4],
                    ))
            finally:
                conn.close()
        except Exception:
            pass

    def get_status(self) -> dict:
        """
        حالة محرك الاستدلال — Get the reasoner's current status.

        v36 FIX: Added get_status() for test compatibility.
        """
        return {
            "initialized": self._initialized,
            "version": self._version,
            "total_rules": len(self._rule_cache),
            "graph_nodes": len(self._causal_graph),
            "v6_enabled": V6_ENABLED,
        }

    async def analyze_version_diff(
        self,
        from_version: str,
        to_version: str,
        changes: List[str] = None,
        regressions: List[str] = None,
        improvements: List[str] = None,
    ) -> 'VersionDiff':
        """
        تحليل فرق الإصدارات — Analyze the difference between two versions.

        v36 FIX: Added analyze_version_diff() for test_causal_reasoner_v19.py.
        Compares two versions and assesses the risk level based on
        the number and severity of changes, regressions, and improvements.

        Args:
            from_version: Source version identifier
            to_version: Target version identifier
            changes: List of changes between versions
            regressions: List of regressions (bugs introduced)
            improvements: List of improvements

        Returns:
            VersionDiff dataclass with analysis results
        """
        changes = changes or []
        regressions = regressions or []
        improvements = improvements or []

        # Compute risk level based on regressions and change count
        if regressions and len(regressions) > 1:
            risk_level = "critical" if len(regressions) > 3 else "high"
        elif regressions:
            risk_level = "medium"
        elif len(changes) > 10:
            risk_level = "medium"
        else:
            risk_level = "low"

        diff = VersionDiff(
            from_version=from_version,
            to_version=to_version,
            changes=changes,
            regressions=regressions,
            improvements=improvements,
            risk_level=risk_level,
        )

        # Update causal graph if regressions found
        for regression in regressions:
            self._add_to_graph(
                f"update:{from_version}->{to_version}",
                f"regression:{regression}",
                0.7,
            )

        return diff

    def _build_intervention_templates(self) -> dict:
        """
        بناء قوالب التدخل — اقتراحات إصلاح لأنماط الأسباب الشائعة.
        Build intervention suggestion templates for common cause patterns.
        """
        return {
            "timeout": "زيادة مهلة التنفيذ أو تحسين الأداء — increase timeout or optimize performance",
            "memory": "تقليل استهلاك الذاكرة أو زيادة الحصة — reduce memory usage or increase allocation",
            "permission": "مراجعة صلاحيات الوصول — review access permissions",
            "network": "تحسين معالجة أخطاء الشبكة — improve network error handling",
            "syntax": "مراجعة بنية الكود قبل التنفيذ — review code syntax before execution",
            "dependency": "التحقق من توفر التبعيات — verify dependencies availability",
            "configuration": "مراجعة إعدادات النظام — review system configuration",
            "data_format": "التحقق من تنسيق البيانات المدخلة — validate input data format",
            "concurrency": "تحسين التعامل مع التزامن — improve concurrency handling",
            "resource": "إدارة أفضل للموارد المتاحة — better resource management",
        }

    async def analyze_root_cause(self, errors: list[dict]) -> list[CausalRule]:
        """
        تحليل السبب الجذري — تحليل أنماط الأخطاء وتحديد السلاسل السببية.

        Analyzes error patterns and identifies causal chains.
        Groups errors by root_cause and effect, then computes confidence
        based on frequency and consistency.

        Args:
            errors: قائمة الأخطاء — كل خطأ يحتوي على root_cause، summary، إلخ

        Returns:
            قائمة القواعد السببية المكتشفة
        """
        if not errors:
            return []

        # Group errors by (cause, effect) pairs
        causal_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)

        for error in errors:
            cause = error.get("root_cause", "") or error.get("cause", "")
            effect = error.get("summary", "") or error.get("effect", "")

            if not cause or not effect:
                continue

            # Normalize cause and effect
            cause_normalized = self._normalize_text(cause)
            effect_normalized = self._normalize_text(effect)

            key = (cause_normalized, effect_normalized)
            causal_groups[key].append(error)

        # Build causal rules from groups
        rules: list[CausalRule] = []

        for (cause, effect), group in causal_groups.items():
            evidence_count = len(group)

            if evidence_count < self.MIN_EVIDENCE_THRESHOLD:
                continue

            # Compute confidence based on evidence count and consistency
            # More evidence = higher confidence, but with diminishing returns
            confidence = min(1.0, (evidence_count / 10.0) * 0.7 + 0.3)

            # Adjust confidence based on error severity
            severities = []
            for err in group:
                severity = err.get("severity", 0.5)
                if isinstance(severity, (int, float)):
                    severities.append(float(severity))
                else:
                    severities.append(0.5)

            if severities:
                avg_severity = sum(severities) / len(severities)
                # High severity errors increase confidence in the causal link
                confidence = min(1.0, confidence * (0.7 + 0.3 * avg_severity))

            if confidence < self.MIN_CONFIDENCE:
                continue

            # Generate intervention suggestion
            intervention = self._suggest_intervention(cause, effect, group)

            rule = CausalRule(
                cause=cause,
                effect=effect,
                confidence=round(confidence, 4),
                evidence_count=evidence_count,
                intervention=intervention,
            )
            rules.append(rule)

        # Sort by confidence (descending)
        rules.sort(key=lambda r: r.confidence, reverse=True)

        # Cache the rules
        self._rule_cache = rules

        # Update causal graph
        for rule in rules:
            self._add_to_graph(rule.cause, rule.effect, rule.confidence)

        return rules

    async def build_causal_graph(self, errors: list[dict]) -> dict:
        """
        بناء الرسم البياني السببي — بناء رسم بياني موجه حلققي للأسباب.

        Builds a Directed Acyclic Graph (DAG) of causes from error patterns.
        Each edge represents a causal link with confidence weight.

        Args:
            errors: قائمة الأخطاء

        Returns:
            الرسم البياني السببي — {node: {successors: [...], confidence: float}}
        """
        # First, analyze root causes to populate rules
        rules = await self.analyze_root_cause(errors)

        graph: dict = {}

        for rule in rules:
            # Add cause node
            if rule.cause not in graph:
                graph[rule.cause] = {"successors": [], "confidence": 0.0, "type": "cause"}
            # Add effect node
            if rule.effect not in graph:
                graph[rule.effect] = {"successors": [], "confidence": 0.0, "type": "effect"}

            # Add directed edge: cause → effect
            edge = {"target": rule.effect, "confidence": rule.confidence, "evidence": rule.evidence_count}
            graph[rule.cause]["successors"].append(edge)
            graph[rule.cause]["confidence"] = max(graph[rule.cause]["confidence"], rule.confidence)

        # Detect and break cycles (simple approach: remove lowest-confidence edges in cycles)
        graph = self._break_cycles(graph)

        # Update internal graph
        self._causal_graph = graph

        return graph

    async def infer_cause(self, effect: str, context: dict = None) -> list[str]:
        """
        الاستدلال السببي العكسي — استنتاج الأسباب المحتملة من ملاحظة الأثر.

        Given an observed effect, infers possible causes by traversing
        the causal graph in reverse.

        Args:
            effect: الأثر الملاحظ
            context: سياق إضافي

        Returns:
            قائمة الأسباب المحتملة مرتبة حسب الاحتمالية
        """
        context = context or {}
        effect_normalized = self._normalize_text(effect)

        possible_causes: list[tuple[str, float]] = []

        # Search in cached rules
        for rule in self._rule_cache:
            if self._normalize_text(rule.effect) == effect_normalized:
                possible_causes.append((rule.cause, rule.confidence))

        # Search in causal graph
        for node, data in self._causal_graph.items():
            for edge in data.get("successors", []):
                if self._normalize_text(edge.get("target", "")) == effect_normalized:
                    possible_causes.append((node, edge.get("confidence", 0.0)))

        # Also check for partial matches
        if not possible_causes:
            for rule in self._rule_cache:
                effect_norm = self._normalize_text(rule.effect)
                if effect_normalized in effect_norm or effect_norm in effect_normalized:
                    possible_causes.append((rule.cause, rule.confidence * 0.7))

        # Deduplicate and sort by confidence
        seen = set()
        unique_causes: list[tuple[str, float]] = []
        for cause, conf in possible_causes:
            cause_key = self._normalize_text(cause)
            if cause_key not in seen:
                seen.add(cause_key)
                unique_causes.append((cause, conf))

        unique_causes.sort(key=lambda x: x[1], reverse=True)

        # Context filtering: if context has specific hints, boost relevant causes
        if context.get("target_file"):
            target = context["target_file"]
            filtered = []
            for cause, conf in unique_causes:
                # Boost causes related to the target file
                if target.lower() in cause.lower():
                    filtered.append((cause, min(1.0, conf * 1.2)))
                else:
                    filtered.append((cause, conf))
            unique_causes = filtered

        return [cause for cause, _ in unique_causes]

    async def generate_intervention(self, causal_chain: list) -> dict:
        """
        توليد التدخل — اقتراح تدخل لكسر السلسلة السببية.

        Suggests interventions to break a causal chain. Targets the
        weakest link in the chain for maximum effectiveness.

        Args:
            causal_chain: السلسلة السببية — قائمة من الأسباب/الآثار المرتبطة

        Returns:
            dict يحتوي على التدخل المقترح والرابط المستهدف
        """
        if not causal_chain:
            return {
                "intervention": "لا توجد سلسلة سببية — لا يوجد تدخل مطلوب",
                "target_link": "",
                "confidence": 0.0,
                "chain_length": 0,
            }

        # Find the weakest link in the chain (lowest confidence)
        weakest_link = None
        weakest_confidence = 1.0

        for i, link in enumerate(causal_chain):
            if isinstance(link, dict):
                conf = link.get("confidence", 0.5)
                cause = link.get("cause", "")
                effect = link.get("effect", "")
            elif isinstance(link, (list, tuple)) and len(link) >= 2:
                cause, effect = link[0], link[1]
                conf = link[2] if len(link) > 2 else 0.5
            else:
                continue

            if conf < weakest_confidence:
                weakest_confidence = conf
                weakest_link = {"cause": cause, "effect": effect, "index": i}

        # Generate intervention for the weakest link
        if weakest_link:
            cause = weakest_link["cause"]
            effect = weakest_link["effect"]
            intervention = self._suggest_intervention(cause, effect, [])

            return {
                "intervention": intervention,
                "target_link": f"{cause} → {effect}",
                "target_index": weakest_link["index"],
                "confidence": weakest_confidence,
                "chain_length": len(causal_chain),
                "arabic_description": (
                    f"التدخل المقترح: كسر الرابط بين '{cause}' و '{effect}' "
                    f"بمستوى ثقة {weakest_confidence:.2f}. {intervention}"
                ),
            }

        # Fallback: suggest intervention for the first link
        first = causal_chain[0]
        if isinstance(first, dict):
            cause = first.get("cause", "غير معروف")
            effect = first.get("effect", "غير معروف")
        else:
            cause = str(first)
            effect = ""

        intervention = self._suggest_intervention(cause, effect, [])
        return {
            "intervention": intervention,
            "target_link": f"{cause} → {effect}",
            "target_index": 0,
            "confidence": 0.5,
            "chain_length": len(causal_chain),
            "arabic_description": f"تدخل أولي: {intervention}",
        }

    async def propose_rules_from_causality(self) -> list[dict]:
        """
        اقتراح قواعد من السببية — ربط مع AbstractionEngine.

        Creates abstract rule proposals from discovered causal patterns.
        These can be submitted to the AbstractionEngine for approval.

        Returns:
            قائمة القواعد المجردة المقترحة
        """
        if not self._rule_cache:
            return []

        proposed_rules: list[dict] = []

        for rule in self._rule_cache:
            if rule.confidence < self.MIN_CONFIDENCE:
                continue

            # Create an abstract rule proposal compatible with AbstractionEngine
            proposed = {
                "name": f"قاعدة سببية: {rule.cause[:50]}",
                "description": (
                    f"تم اكتشاف علاقة سببية: '{rule.cause}' يؤدي إلى '{rule.effect}' "
                    f"بمستوى ثقة {rule.confidence:.2f} ({rule.evidence_count} أدلة). "
                    f"التدخل المقترح: {rule.intervention}"
                ),
                "condition": {
                    "pattern": rule.cause,
                    "type": "causal_link",
                    "effect": rule.effect,
                    "threshold": rule.evidence_count,
                },
                "action": {
                    "suggested_action": rule.intervention,
                    "risk_level": "high" if rule.confidence > 0.7 else "medium",
                    "causal_intervention": True,
                },
                "source_pattern": rule.cause,
                "confidence": rule.confidence,
                "created_from_count": rule.evidence_count,
            }
            proposed_rules.append(proposed)

        # Sort by confidence
        proposed_rules.sort(key=lambda r: r["confidence"], reverse=True)

        return proposed_rules

    # ─── Internal Helpers ──────────────────────────────────────────────────────

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison: lowercase, strip whitespace."""
        if not text:
            return ""
        return text.lower().strip()

    def _add_to_graph(self, cause: str, effect: str, confidence: float):
        """Add a causal edge to the internal graph."""
        if cause not in self._causal_graph:
            self._causal_graph[cause] = {"successors": [], "confidence": 0.0, "type": "cause"}
        if effect not in self._causal_graph:
            self._causal_graph[effect] = {"successors": [], "confidence": 0.0, "type": "effect"}

        edge = {"target": effect, "confidence": confidence, "evidence": 1}
        self._causal_graph[cause]["successors"].append(edge)
        self._causal_graph[cause]["confidence"] = max(
            self._causal_graph[cause]["confidence"], confidence
        )

    def _suggest_intervention(self, cause: str, effect: str, evidence: list[dict]) -> str:
        """
        اقتراح تدخل — إنشاء اقتراح إصلاح بناءً على السبب والأثر.
        Generate an intervention suggestion based on the cause and effect.
        """
        cause_lower = self._normalize_text(cause)

        # Match against intervention templates
        for pattern, template in self._intervention_templates.items():
            if pattern in cause_lower:
                return template

        # Generic intervention based on cause type
        return (
            f"مراجعة السبب '{cause}' لمنع تكرار الأثر '{effect}' — "
            f"review the cause to prevent recurrence of the effect"
        )

    def _break_cycles(self, graph: dict) -> dict:
        """
        كسر الحلقات — إزالة الحواف ذات الثقة الأقل في الحلقات.
        Break cycles in the causal graph by removing lowest-confidence edges.
        Simple DFS-based cycle detection.
        """
        visited = set()
        rec_stack = set()
        edges_to_remove: list[tuple[str, int]] = []

        def dfs(node: str, path: list[tuple[str, int]]):
            visited.add(node)
            rec_stack.add(node)

            if node in graph:
                for i, edge in enumerate(graph[node].get("successors", [])):
                    target = edge.get("target", "")
                    if target not in visited:
                        dfs(target, path + [(node, i)])
                    elif target in rec_stack:
                        # Cycle detected — mark lowest-confidence edge in path
                        all_edges = path + [(node, i)]
                        min_conf = 1.0
                        min_edge = (node, i)
                        for src, idx in all_edges:
                            if src in graph:
                                edges = graph[src].get("successors", [])
                                if idx < len(edges):
                                    conf = edges[idx].get("confidence", 1.0)
                                    if conf < min_conf:
                                        min_conf = conf
                                        min_edge = (src, idx)
                        edges_to_remove.append(min_edge)

            rec_stack.discard(node)

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node, [])

        # Remove marked edges
        for src, idx in edges_to_remove:
            if src in graph and idx < len(graph[src].get("successors", [])):
                graph[src]["successors"].pop(idx)

        return graph
