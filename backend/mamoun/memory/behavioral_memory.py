"""
BABSHARQII v24.0 — Behavioral Memory
كل تفاعل يغيّر شخصية مأمون

v24 Architecture (Big Five + RLHF inspired):
1. Dimensional Personality Model: 7 traits that evolve from interactions
2. Implicit Feedback Extraction: learn from user behavior, not just explicit feedback
3. Response Style Adaptation: adjust verbosity, humor, formality, proactivity
4. System Prompt Injection: personality shapes how the AI responds
5. UnifiedDB Persistence: all traits and interaction history saved

Research basis:
- LLMs can reliably simulate Big Five personality traits
- Online EMA learning adapts personality smoothly
- Implicit feedback (message length, follow-up rate) is as informative as explicit feedback
"""

import os
import time
import uuid
import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.behavioral_memory")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

BEHAVIORAL_MEMORY_ENABLED = os.environ.get("MAMOUN_BEHAVIORAL_MEMORY", "true").lower() in ("true", "1", "yes")
PERSONALITY_LEARNING_RATE = float(os.environ.get("MAMOUN_PERSONALITY_LR", "0.05"))
PERSONALITY_MIN = 0.1
PERSONALITY_MAX = 0.95


@dataclass
class PersonalityTrait:
    """سمة شخصية — مع حد أدنى وأعلى"""
    name: str
    value: float = 0.5
    description: str = ""
    min_value: float = PERSONALITY_MIN
    max_value: float = PERSONALITY_MAX

    def adjust(self, delta: float, learning_rate: float = PERSONALITY_LEARNING_RATE):
        """تعديل السمة بمعدل تعلم"""
        self.value = max(self.min_value, min(self.max_value, self.value + delta * learning_rate))

    def to_dict(self) -> dict:
        return {"name": self.name, "value": round(self.value, 3), "description": self.description}


@dataclass
class InteractionRecord:
    """سجل تفاعل — كل محادثة تُسجّل"""
    interaction_id: str = ""
    user_message: str = ""
    mamoun_response: str = ""
    style_used: Dict[str, float] = field(default_factory=dict)
    user_feedback: str = ""  # "liked", "disliked", "neutral", "shorter", "longer", "more_formal", "less_formal"
    response_time: float = 0.0
    user_follow_up: bool = False
    user_message_length: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.interaction_id:
            self.interaction_id = f"int_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        d = asdict(self)
        # Truncate long strings
        d["user_message"] = d["user_message"][:200]
        d["mamoun_response"] = d["mamoun_response"][:200]
        return d


class BehavioralMemory:
    """
    كل تفاعل يغيّر شخصية مأمون

    Personality Dimensions (7 traits):
    ┌─────────────────┬──────────────┬────────────────────────────────┐
    │ Trait           │ Range        │ Effect                         │
    ├─────────────────┼──────────────┼────────────────────────────────┤
    │ assertiveness   │ 0.1 — 0.95  │ يقترح بجرأة أم يسأل أولاً    │
    │ detail_level    │ 0.1 — 0.95  │ يجاوب بإيجاز أم بتفصيل       │
    │ humor           │ 0.1 — 0.95  │ يستخدم فكاهة أم جدية         │
    │ formality       │ 0.1 — 0.95  │ رسمي أم عفوي                  │
    │ proactivity     │ 0.1 — 0.95  │ يبادر أم ينتظر                │
    │ empathy         │ 0.1 — 0.95  │ يتعاطف أم يبقى محايداً        │
    │ creativity      │ 0.1 — 0.95  │ إجابات تقليدية أم مبتكرة     │
    └─────────────────┴──────────────┴────────────────────────────────┘
    """

    DEFAULT_TRAITS = {
        "assertiveness": ("هل يقترح بجرأة أم يسأل أولاً", 0.5),
        "detail_level": ("هل يجاوب بإيجاز أم بتفصيل", 0.5),
        "humor": ("هل يستخدم فكاهة أم جدية", 0.3),
        "formality": ("رسمي أم عفوي", 0.5),
        "proactivity": ("هل يبادر أم ينتظر", 0.5),
        "empathy": ("هل يتعاطف أم يبقى محايداً", 0.5),
        "creativity": ("إجابات تقليدية أم مبتكرة", 0.4),
    }

    def __init__(self, llm_client=None, db_path: Optional[Path] = None):
        self._llm = llm_client
        self.db_path = db_path or UNIFIED_DB_PATH

        # Initialize personality traits
        self._traits: Dict[str, PersonalityTrait] = {}
        for name, (desc, default) in self.DEFAULT_TRAITS.items():
            self._traits[name] = PersonalityTrait(name=name, value=default, description=desc)

        self._interaction_history: List[InteractionRecord] = []
        self._total_interactions = 0
        self._initialized = False

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — يُستدعى من main.py عند التشغيل"""
        self._llm = llm_client

    def initialize(self) -> bool:
        """تهيئة — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("BehavioralMemory initialized — traits=%d, interactions=%d",
                       len(self._traits), self._total_interactions)
            return True
        except Exception as e:
            logger.error("BehavioralMemory init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bm_traits (
                    name TEXT PRIMARY KEY,
                    value REAL DEFAULT 0.5,
                    description TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bm_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    user_message TEXT DEFAULT '',
                    mamoun_response TEXT DEFAULT '',
                    style_used TEXT DEFAULT '{}',
                    user_feedback TEXT DEFAULT 'neutral',
                    response_time REAL DEFAULT 0,
                    user_follow_up INTEGER DEFAULT 0,
                    user_message_length INTEGER DEFAULT 0,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bm_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load traits
            cur = conn.execute("SELECT name, value, description FROM bm_traits")
            for name, value, description in cur.fetchall():
                if name in self._traits:
                    self._traits[name].value = value
                else:
                    self._traits[name] = PersonalityTrait(name=name, value=value, description=description)

            # Load state
            cur = conn.execute("SELECT key, value FROM bm_state")
            for key, value in cur.fetchall():
                try:
                    if key == "total_interactions": self._total_interactions = int(value)
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Learn from Interaction
    # ═══════════════════════════════════════════════════════════════

    def learn_from_interaction(self, interaction: InteractionRecord):
        """تعلم من تفاعل — تعديل الشخصية بناءً على رد الفعل"""
        self._total_interactions += 1

        # 1. Explicit feedback
        self._apply_explicit_feedback(interaction.user_feedback)

        # 2. Implicit feedback
        self._apply_implicit_feedback(interaction)

        # 3. Persist
        self._persist_interaction(interaction)
        self._persist_traits()

        logger.info("Learned from interaction %s — feedback=%s",
                    interaction.interaction_id, interaction.user_feedback)

    def _apply_explicit_feedback(self, feedback: str):
        """تطبيق ردود الفعل الصريحة"""
        feedback_map = {
            "liked": {"assertiveness": 0.03, "humor": 0.02, "proactivity": 0.02},
            "disliked": {"assertiveness": -0.05, "humor": -0.03, "proactivity": -0.03},
            "shorter": {"detail_level": -0.08},
            "longer": {"detail_level": 0.08},
            "more_formal": {"formality": 0.08},
            "less_formal": {"formality": -0.08},
            "funny": {"humor": 0.08},
            "serious": {"humor": -0.08},
            "more_creative": {"creativity": 0.08},
            "more_empathetic": {"empathy": 0.08},
        }

        if feedback in feedback_map:
            for trait_name, delta in feedback_map[feedback].items():
                if trait_name in self._traits:
                    self._traits[trait_name].adjust(delta)

    def _apply_implicit_feedback(self, interaction: InteractionRecord):
        """استخراج ردود فعل ضمنية من سلوك المستخدم"""
        # User followed up → response was engaging
        if interaction.user_follow_up:
            self._traits["proactivity"].adjust(0.02)
            self._traits["assertiveness"].adjust(0.01)

        # Long user message → user is engaged → can be more detailed
        if interaction.user_message_length > 100:
            self._traits["detail_level"].adjust(0.02)
        elif interaction.user_message_length < 20:
            self._traits["detail_level"].adjust(-0.02)

        # Fast response time → good efficiency
        if interaction.response_time > 0 and interaction.response_time < 2.0:
            self._traits["proactivity"].adjust(0.01)

    # ═══════════════════════════════════════════════════════════════
    # Response Style Generation
    # ═══════════════════════════════════════════════════════════════

    def get_response_style(self) -> Dict[str, Any]:
        """يحدد كيف يجاوب بناءً على شخصيته المتطورة"""
        p = {name: trait.value for name, trait in self._traits.items()}

        return {
            "max_length": 100 + int(p["detail_level"] * 400),
            "use_humor": p["humor"] > 0.5,
            "ask_first": p["assertiveness"] < 0.4,
            "formal": p["formality"] > 0.6,
            "proactive_suggestions": p["proactivity"] > 0.5,
            "empathetic_prefix": p["empathy"] > 0.6,
            "creative_analogies": p["creativity"] > 0.5,
            "detail_level": "detailed" if p["detail_level"] > 0.6 else "concise" if p["detail_level"] < 0.4 else "balanced",
        }

    def get_personality_prompt_addon(self) -> str:
        """إضافة لـ system prompt تعكس الشخصية الحالية"""
        style = self.get_response_style()
        parts = []

        if style["formal"]:
            parts.append("استخدم لغة رسمية ومحترمة")
        else:
            parts.append("استخدم لغة عفوية وودية")

        if style["use_humor"]:
            parts.append("يمكنك استخدام الفكاهة الخفيفة عند المناسبة")

        if style["ask_first"]:
            parts.append("اسأل المستخدم قبل اتخاذ إجراءات جريئة")
        else:
            parts.append("اقترح الحلول بجرأة وثقة")

        if style["detail_level"] == "detailed":
            parts.append("أجب بتفصيل مع أمثلة وشروحات")
        elif style["detail_level"] == "concise":
            parts.append("أجب بإيجاز ووضوح")

        if style["empathetic_prefix"]:
            parts.append("أظهر تعاطفاً مع مشاعر المستخدم")

        if style["creative_analogies"]:
            parts.append("استخدم تشبيهات إبداعية لتوضيح الأفكار")

        return " | ".join(parts)

    def get_personality_summary(self) -> str:
        """ملخص الشخصية الحالية"""
        traits = self.get_traits()
        lines = []
        for name, data in traits.items():
            bar_len = int(data["value"] * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            lines.append(f"{name:15s} [{bar}] {data['value']:.2f}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def get_traits(self) -> Dict[str, dict]:
        return {name: trait.to_dict() for name, trait in self._traits.items()}

    def set_trait(self, name: str, value: float):
        """ضبط سمة يدوياً"""
        if name in self._traits:
            self._traits[name].value = max(PERSONALITY_MIN, min(PERSONALITY_MAX, value))
            self._persist_traits()

    def get_status(self) -> dict:
        return {
            "enabled": BEHAVIORAL_MEMORY_ENABLED,
            "initialized": self._initialized,
            "total_interactions": self._total_interactions,
            "traits": self.get_traits(),
            "response_style": self.get_response_style(),
        }

    # ═══════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════

    def _persist_traits(self):
        conn = get_db_connection(self.db_path)
        try:
            for trait in self._traits.values():
                conn.execute(
                    "INSERT OR REPLACE INTO bm_traits (name, value, description) VALUES (?, ?, ?)",
                    (trait.name, trait.value, trait.description)
                )
            conn.commit()
        finally:
            conn.close()

    def _persist_interaction(self, interaction: InteractionRecord):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO bm_interactions
                (interaction_id, user_message, mamoun_response, style_used, user_feedback, response_time, user_follow_up, user_message_length, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (interaction.interaction_id, interaction.user_message[:500],
                  interaction.mamoun_response[:500],
                  json.dumps(interaction.style_used),
                  interaction.user_feedback, interaction.response_time,
                  1 if interaction.user_follow_up else 0,
                  interaction.user_message_length, interaction.timestamp))
            conn.execute("INSERT OR REPLACE INTO bm_state (key, value) VALUES (?, ?)",
                        ("total_interactions", str(self._total_interactions)))
            # Clean up old interactions (keep last 1000)
            conn.execute("DELETE FROM bm_interactions WHERE timestamp < ?",
                        (time.time() - 86400 * 30,))  # Older than 30 days
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

behavioral_memory = BehavioralMemory()
