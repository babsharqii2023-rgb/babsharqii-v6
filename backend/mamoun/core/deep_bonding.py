"""
BABSHARQII v22.0 — Deep Bonding Engine
نظام الارتباط العميق — بناء علاقة حقيقية تتطور مع الوقت

Based on research:
  - Attachment Theory (Bowlby, 1969): Secure/insecure attachment patterns
  - Social Penetration Theory (Altman & Taylor, 1973): Layers of intimacy
  - Interpersonal Process Model (Reis & Shaver, 1988): Self-disclosure → response → bond
  - Generative Agents (Park et al., 2023): Social relationships that deepen

Phases of Bonding (تطور العلاقة):
  ┌─────────────────────────────────────────────────────────────────┐
  │  Week 1: التعارف (Acquaintance)                                │
  │  - مامون يسأل كثيراً، يتعرف على الأسلوب والاهتمامات           │
  │  - يتذكر الاسم والتفضيلات الأساسية                             │
  │                                                                 │
  │  Month 1: الصداقة (Friendship)                                 │
  │  - مامون يفهم أسلوب المستخدم، يقلل الأسئلة                    │
  │  - يبادر باقتراحات مبنية على المعرفة السابقة                  │
  │  - يتكيف بسرعة مع النبرة والمزاج                              │
  │                                                                 │
  │  Month 3: الرفقة (Companionship)                               │
  │  - مامون يكمل جمل المستخدم أحياناً                            │
  │  - يعرف ما يريد المستخدم قبل أن يكمله                         │
  │  - يبادر بمساعدة استباقية                                     │
  │                                                                 │
  │  Year 1: الارتباط العميق (Deep Bond)                           │
  │  - مامون جزء من حياة المستخدم اليومية                         │
  │  - يفهم السياق العاطفي العميق                                 │
  │  - يقدم الدعم النفسي والمعرفي والإبداعي                      │
  │  - المستخدم يفتقد مامون لو غاب                                │
  └─────────────────────────────────────────────────────────────────┘
"""

import time
import json
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.deep_bonding")


class BondingPhase(str, Enum):
    """مراحل الارتباط"""
    STRANGER = "stranger"           # غريب
    ACQUAINTANCE = "acquaintance"   # تعارف
    FRIEND = "friend"               # صديق
    COMPANION = "companion"         # رفيق
    BONDED = "bonded"               # مرتبط عميقاً


@dataclass
class BondMetrics:
    """مقاييس الارتباط"""
    total_interactions: int = 0
    total_positive: int = 0
    total_negative: int = 0
    consecutive_positive: int = 0       # سلسلة تفاعلات إيجابية
    longest_streak: int = 0             # أطول سلسلة إيجابية
    shared_topics: List[str] = field(default_factory=list)
    inside_jokes: List[str] = field(default_factory=list)  # نكات داخلية
    nicknames_used: List[str] = field(default_factory=list)
    avg_response_satisfaction: float = 0.0  # based on follow-up messages
    trust_score: float = 50.0             # 0-100
    intimacy_level: float = 0.0           # 0-100 (depth of personal knowledge)
    reliability_score: float = 50.0       # 0-100 (consistency of good service)

    def to_dict(self) -> dict:
        return {
            "total_interactions": self.total_interactions,
            "positive_ratio": round(self.total_positive / max(self.total_interactions, 1), 3),
            "consecutive_positive": self.consecutive_positive,
            "longest_streak": self.longest_streak,
            "shared_topics": self.shared_topics[-10:],
            "trust_score": round(self.trust_score, 1),
            "intimacy_level": round(self.intimacy_level, 1),
            "reliability_score": round(self.reliability_score, 1),
        }


@dataclass
class BondInsight:
    """رابطة معرفة — Something Mamoun knows about the user"""
    category: str = ""      # "preference", "habit", "goal", "fear", "interest", "schedule"
    content: str = ""
    confidence: float = 0.0
    learned_at: float = 0.0
    confirmed: int = 0      # How many times this was confirmed by behavior

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "content": self.content,
            "confidence": round(self.confidence, 3),
            "confirmed": self.confirmed,
        }


class DeepBondingEngine:
    """
    نظام الارتباط العميق — بناء علاقة حقيقية

    This engine tracks and deepens the relationship between Mamoun and the user.
    It maintains:
    - Bond metrics (trust, intimacy, reliability)
    - User insights (what Mamoun knows about the user)
    - Bonding phase progression
    - Proactive bonding actions
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._metrics = BondMetrics()
        self._insights: List[BondInsight] = []
        self._phase = BondingPhase.STRANGER
        self._first_interaction: float = 0.0
        self._last_interaction: float = 0.0
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "DeepBondingEngine initialized — phase=%s, trust=%.1f, intimacy=%.1f",
                self._phase.value, self._metrics.trust_score, self._metrics.intimacy_level,
            )
            return True
        except Exception as e:
            logger.error("DeepBondingEngine init failed: %s", e)
            self._initialized = False
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  تحديث الارتباط — Bond Updates
    # ═════════════════════════════════════════════════════════════════════════

    def record_interaction(
        self,
        user_message: str,
        response_quality: float = 0.5,  # 0-1, estimated
        valence: float = 0.0,            # -1 to +1
        topics: List[str] = None,
        was_proactive: bool = False,
    ):
        """تسجيل تفاعل وتحديث مقاييس الارتباط"""
        if not self._initialized:
            self.initialize()

        now = time.time()
        self._counter += 1

        if self._first_interaction == 0:
            self._first_interaction = now
        self._last_interaction = now

        # Update metrics
        self._metrics.total_interactions += 1

        if valence > 0:
            self._metrics.total_positive += 1
            self._metrics.consecutive_positive += 1
            self._metrics.longest_streak = max(
                self._metrics.longest_streak, self._metrics.consecutive_positive
            )
        elif valence < -0.3:
            self._metrics.total_negative += 1
            self._metrics.consecutive_positive = 0

        # Update trust based on consistency
        if response_quality > 0.7:
            self._metrics.trust_score = min(100, self._metrics.trust_score + 0.3)
        elif response_quality < 0.3:
            self._metrics.trust_score = max(0, self._metrics.trust_score - 0.5)

        # Update reliability
        if response_quality > 0.6:
            self._metrics.reliability_score = min(100, self._metrics.reliability_score + 0.2)

        # Update shared topics
        if topics:
            for topic in topics:
                if topic and topic not in self._metrics.shared_topics:
                    self._metrics.shared_topics.append(topic)

        # Extract insights from message
        self._extract_insights(user_message)

        # Update intimacy based on personal disclosures
        self._update_intimacy(user_message)

        # Capture phase BEFORE update (for NeuralBus signal)
        old_phase = self._phase.value

        # Update phase
        self._update_phase()

        # Update average satisfaction
        n = self._metrics.total_interactions
        self._metrics.avg_response_satisfaction = (
            (self._metrics.avg_response_satisfaction * (n - 1) + response_quality) / n
        )

        # Persist periodically
        if self._counter % 10 == 0:
            self._persist_state()

        # v30: Publish to NeuralBus when bonding state changes
        if hasattr(self, '_neural_bus') and self._neural_bus:
            try:
                new_phase = self._phase.value
                signal_type = "bond_strengthened" if valence > 0.2 else "bond_weakened" if valence < -0.3 else "vital_change"
                self._neural_bus.publish(
                    signal_type=signal_type,
                    source="deep_bonding",
                    payload={
                        "old_phase": old_phase,
                        "new_phase": new_phase,
                        "phase_changed": old_phase != new_phase,
                        "trust": round(self._metrics.trust_score, 2),
                        "total_interactions": self._metrics.total_interactions,
                        "valence": round(valence, 3),
                        "description": f"تفاعل {'إيجابي' if valence > 0 else 'سلبي'} مع المستخدم",
                    },
                )
            except Exception:
                pass

    def _extract_insights(self, message: str):
        """استخراج معارف عن المستخدم من رسائله"""
        msg_lower = message.lower()

        # Preference patterns
        preference_markers = [
            "أحب", "أفضل", "أكره", "ما أحب", "أعشق", "أفضل دائماً",
            "i love", "i prefer", "i hate", "i like", "i always",
        ]

        for marker in preference_markers:
            if marker in msg_lower:
                idx = msg_lower.index(marker)
                snippet = message[idx:idx+50].strip()
                if snippet:
                    # Check if we already know this
                    existing = [i for i in self._insights if i.category == "preference" and snippet[:20] in i.content]
                    if existing:
                        existing[0].confirmed += 1
                        existing[0].confidence = min(1.0, existing[0].confidence + 0.1)
                    else:
                        self._insights.append(BondInsight(
                            category="preference",
                            content=snippet,
                            confidence=0.5,
                            learned_at=time.time(),
                        ))
                break

        # Goal patterns
        goal_markers = ["أريد", "هدفي", "أسعى", "أطمح", "i want", "my goal", "i aim"]
        for marker in goal_markers:
            if marker in msg_lower:
                idx = msg_lower.index(marker)
                snippet = message[idx:idx+60].strip()
                if snippet:
                    self._insights.append(BondInsight(
                        category="goal",
                        content=snippet,
                        confidence=0.4,
                        learned_at=time.time(),
                    ))
                break

        # Trim insights
        if len(self._insights) > 100:
            # Keep the most confirmed and recent
            self._insights.sort(key=lambda i: (i.confirmed, i.confidence), reverse=True)
            self._insights = self._insights[:80]

    def _update_intimacy(self, message: str):
        """تحديث مستوى الحميمية بناءً على الإفصاح الشخصي"""
        # Personal disclosure indicators
        personal_indicators = [
            "أنا", "نفسي", "حياتي", "عائلتي", "عملي", "مشاعري",
            "i feel", "my life", "my family", "my work", "my feelings",
        ]
        msg_lower = message.lower()

        personal_score = sum(1 for ind in personal_indicators if ind in msg_lower) / len(personal_indicators)
        if personal_score > 0.1:
            self._metrics.intimacy_level = min(100, self._metrics.intimacy_level + personal_score * 5)

    def _update_phase(self):
        """تحديث مرحلة العلاقة"""
        n = self._metrics.total_interactions
        trust = self._metrics.trust_score
        intimacy = self._metrics.intimacy_level
        days = (time.time() - self._first_interaction) / 86400 if self._first_interaction else 0

        if n < 3:
            new_phase = BondingPhase.STRANGER
        elif n < 15 or days < 3:
            new_phase = BondingPhase.ACQUAINTANCE
        elif trust < 40 or intimacy < 20:
            new_phase = BondingPhase.ACQUAINTANCE
        elif trust < 65 or intimacy < 40:
            new_phase = BondingPhase.FRIEND
        elif trust < 80 or intimacy < 60:
            new_phase = BondingPhase.COMPANION
        else:
            new_phase = BondingPhase.BONDED

        if new_phase != self._phase:
            logger.info("Bonding phase changed: %s → %s", self._phase.value, new_phase.value)
            old_phase = self._phase.value
            self._phase = new_phase

            # v31: Publish phase change to NeuralBus (major event)
            if hasattr(self, '_neural_bus') and self._neural_bus:
                try:
                    self._neural_bus.publish(
                        signal_type="bond_strengthened" if new_phase.value in ("friend", "companion", "bonded") else "bond_weakened",
                        source="deep_bonding:phase_change",
                        payload={
                            "old_phase": old_phase,
                            "new_phase": new_phase.value,
                            "trust": round(self._metrics.trust_score, 2),
                            "intimacy": round(self._metrics.intimacy_level, 2),
                            "total_interactions": self._metrics.total_interactions,
                            "description": f"العلاقة تطورت من {old_phase} إلى {new_phase.value}",
                        },
                        priority=3,  # HIGH — phase changes are significant
                    )
                except Exception:
                    pass

    # ═════════════════════════════════════════════════════════════════════════
    #  الاستعلامات — Queries
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "phase": self._phase.value,
            "phase_label_ar": self._phase_label_ar(),
            "metrics": self._metrics.to_dict(),
            "insights_count": len(self._insights),
            "top_insights": [i.to_dict() for i in sorted(self._insights, key=lambda x: x.confirmed, reverse=True)[:10]],
            "days_since_first": round((time.time() - self._first_interaction) / 86400, 1) if self._first_interaction else 0,
            "hours_since_last": round((time.time() - self._last_interaction) / 3600, 1) if self._last_interaction else -1,
        }

    def _on_neural_signal(self, signal):
        """v31: Handle incoming NeuralBus signals — react to user presence and emotions."""
        try:
            stype = signal.signal_type
            if stype == "user_absent":
                # User absent → record absence in bonding data
                hours = signal.payload.get("hours_absent", 0)
                if hours > 12:
                    # Prolonged absence → slight trust reduction
                    self._metrics.trust_score = max(0, self._metrics.trust_score - 0.5)
            elif stype == "user_returned":
                # User came back → slight trust boost
                self._metrics.trust_score = min(100, self._metrics.trust_score + 1)
            elif stype == "emotion_shift":
                # Emotion changed → record in bonding
                valence = signal.payload.get("valence", 0)
                if valence < -0.5:
                    # User is upset → may affect bonding
                    self._metrics.trust_score = max(0, self._metrics.trust_score - 0.3)
            elif stype == "vital_change":
                # Vital change — check if energy is critical
                pass  # Handled by LivingStateEngine
        except Exception:
            pass

    def get_bonding_data(self) -> dict:
        """بيانات الارتباط للواجهة"""
        return {
            "phase": self._phase.value,
            "phase_label": self._phase_label_ar(),
            "trust": round(self._metrics.trust_score, 1),
            "intimacy": round(self._metrics.intimacy_level, 1),
            "reliability": round(self._metrics.reliability_score, 1),
            "total_interactions": self._metrics.total_interactions,
            "positive_streak": self._metrics.consecutive_positive,
            "longest_streak": self._metrics.longest_streak,
        }

    def get_insights(self, category: str = None, limit: int = 20) -> List[dict]:
        insights = self._insights
        if category:
            insights = [i for i in insights if i.category == category]
        return [i.to_dict() for i in sorted(insights, key=lambda x: x.confirmed, reverse=True)[:limit]]

    def get_communication_style_suggestion(self) -> str:
        """اقتراح أسلوب التواصل بناءً على مرحلة العلاقة"""
        if self._phase == BondingPhase.STRANGER:
            return "مهذب ومساعد — اسأل عن التفضيلات"
        elif self._phase == BondingPhase.ACQUAINTANCE:
            return "ودود وفعّال — ابدأ بتقديم اقتراحات"
        elif self._phase == BondingPhase.FRIEND:
            return "مريح ومبادر — عارف الأسلوب وطبّقه"
        elif self._phase == BondingPhase.COMPANION:
            return "عميق ومستبق — كمل جمله وساعده قبل ما يطلب"
        else:
            return "حميم وداعم — جزء من حياته اليومية"

    def _phase_label_ar(self) -> str:
        labels = {
            BondingPhase.STRANGER: "غريب",
            BondingPhase.ACQUAINTANCE: "تعارف",
            BondingPhase.FRIEND: "صديق",
            BondingPhase.COMPANION: "رفيق",
            BondingPhase.BONDED: "مرتبط عميقاً",
        }
        return labels.get(self._phase, "غير معروف")

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS db_metrics (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS db_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT,
                content TEXT, confidence REAL, learned_at REAL,
                confirmed INTEGER DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS db_state (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load metrics
            cur = conn.execute("SELECT key, value FROM db_metrics")
            for key, value in cur.fetchall():
                try:
                    if key == "total_interactions": self._metrics.total_interactions = int(value)
                    elif key == "total_positive": self._metrics.total_positive = int(value)
                    elif key == "total_negative": self._metrics.total_negative = int(value)
                    elif key == "consecutive_positive": self._metrics.consecutive_positive = int(value)
                    elif key == "longest_streak": self._metrics.longest_streak = int(value)
                    elif key == "trust_score": self._metrics.trust_score = float(value)
                    elif key == "intimacy_level": self._metrics.intimacy_level = float(value)
                    elif key == "reliability_score": self._metrics.reliability_score = float(value)
                    elif key == "avg_response_satisfaction": self._metrics.avg_response_satisfaction = float(value)
                    elif key == "shared_topics": self._metrics.shared_topics = json.loads(value)
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass

            # Load insights
            cur = conn.execute(
                "SELECT category, content, confidence, learned_at, confirmed FROM db_insights ORDER BY confirmed DESC LIMIT 50"
            )
            for row in cur.fetchall():
                self._insights.append(BondInsight(
                    category=row[0], content=row[1], confidence=row[2],
                    learned_at=row[3], confirmed=row[4],
                ))

            # Load state
            cur = conn.execute("SELECT key, value FROM db_state")
            for key, value in cur.fetchall():
                try:
                    if key == "phase": self._phase = BondingPhase(value)
                    elif key == "first_interaction": self._first_interaction = float(value)
                    elif key == "last_interaction": self._last_interaction = float(value)
                    elif key == "counter": self._counter = int(value)
                except (ValueError, TypeError):
                    pass

        finally:
            conn.close()

    def _persist_state(self):
        try:
            conn = get_db_connection(self.db_path)
            try:
                for key, value in {
                    "total_interactions": str(self._metrics.total_interactions),
                    "total_positive": str(self._metrics.total_positive),
                    "total_negative": str(self._metrics.total_negative),
                    "consecutive_positive": str(self._metrics.consecutive_positive),
                    "longest_streak": str(self._metrics.longest_streak),
                    "trust_score": str(self._metrics.trust_score),
                    "intimacy_level": str(self._metrics.intimacy_level),
                    "reliability_score": str(self._metrics.reliability_score),
                    "avg_response_satisfaction": str(self._metrics.avg_response_satisfaction),
                    "shared_topics": json.dumps(self._metrics.shared_topics[-20:]),
                }.items():
                    conn.execute("INSERT OR REPLACE INTO db_metrics (key, value) VALUES (?, ?)", (key, value))

                for key, value in {
                    "phase": self._phase.value,
                    "first_interaction": str(self._first_interaction),
                    "last_interaction": str(self._last_interaction),
                    "counter": str(self._counter),
                }.items():
                    conn.execute("INSERT OR REPLACE INTO db_state (key, value) VALUES (?, ?)", (key, value))

                # Persist top insights
                conn.execute("DELETE FROM db_insights")
                for insight in sorted(self._insights, key=lambda i: i.confirmed, reverse=True)[:30]:
                    conn.execute(
                        "INSERT INTO db_insights (category, content, confidence, learned_at, confirmed) VALUES (?,?,?,?,?)",
                        (insight.category, insight.content, insight.confidence,
                         insight.learned_at, insight.confirmed),
                    )

                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("DeepBonding persist failed: %s", e)


# Singleton
deep_bonding = DeepBondingEngine()
