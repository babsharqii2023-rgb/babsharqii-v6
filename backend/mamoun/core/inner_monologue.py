"""
BABSHARQII v24.0 — Inner Monologue
مأمون يفكر باستمرار — حتى بدون تفاعل مع المستخدم

v24 Architecture (MIRROR-inspired):
1. Temporal Decoupling: Thinker (async background) vs Talker (user-facing)
2. Progressive Compression: Recent thoughts → rich detail, old → summarized
3. Action Extraction: Thoughts become actions when urgency is high
4. Memory Consolidation: Sleep-like insight discovery from thought patterns
5. NeuralBus Integration: Publishes thoughts, subscribes to events

Key insight from MIRROR paper (arXiv:2506.00430):
- 156% improvement in safety through inner monologue
- 21% average performance gain across tasks
- Thinker and Talker must be temporally decoupled (never block user)
"""

import os
import time
import uuid
import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.inner_monologue")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

INNER_MONOLOGUE_ENABLED = os.environ.get("MAMOUN_INNER_MONOLOGUE", "true").lower() in ("true", "1", "yes")
THINK_INTERVAL_SECONDS = int(os.environ.get("MAMOUN_THINK_INTERVAL", "120"))
CONSOLIDATION_INTERVAL_SECONDS = int(os.environ.get("MAMOUN_CONSOLIDATION_INTERVAL", "3600"))
MAX_THOUGHT_STREAM = int(os.environ.get("MAMOUN_MAX_THOUGHTS", "200"))
THOUGHT_URGENCY_THRESHOLD = float(os.environ.get("MAMOUN_THOUGHT_URGENCY_THRESHOLD", "0.7"))


class ThoughtType(str, Enum):
    OBSERVATION = "observation"      # لاحظ شيئاً
    REFLECTION = "reflection"        # فكّر في ما حدث
    HYPOTHESIS = "hypothesis"        # اقترح تفسيراً
    PLAN = "plan"                    # خطط لعمل
    SELF_CRITICISM = "self_criticism" # انتقد نفسه
    CURIOSITY = "curiosity"          # تساءل عن شيء
    EMOTIONAL = "emotional"          # شعر بشيء
    MEMORY = "memory"                # تذكّر شيئاً
    INSIGHT = "insight"              # اكتشف علاقة جديدة
    IDLE = "idle"                    # لا شيء مهم


class ThoughtUrgency(str, Enum):
    LOW = "low"           # مجرد فكرة
    MEDIUM = "medium"     # يستحق الانتباه
    HIGH = "high"         # يجب أن أتصرف
    CRITICAL = "critical"  # يجب أن أخطر المستخدم فوراً


@dataclass
class Thought:
    """فكرة واحدة في تيار الوعي"""
    thought_id: str = ""
    content: str = ""
    thought_type: str = ThoughtType.REFLECTION.value
    urgency: str = ThoughtUrgency.LOW.value
    context: str = ""           # ما الذي أثار هذه الفكرة
    action_suggested: str = ""  # هل هناك فعل مقترح
    confidence: float = 0.5
    timestamp: float = 0.0
    compressed: bool = False
    parent_thought_id: str = ""  # فكرة أبوية (إن كانت رد على فكرة سابقة)

    def __post_init__(self):
        if not self.thought_id:
            self.thought_id = f"th_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConsolidatedInsight:
    """رؤية مُدمجة من عدة أفكار"""
    insight_id: str = ""
    summary: str = ""
    source_thought_count: int = 0
    patterns_found: List[str] = field(default_factory=list)
    actionable_items: List[str] = field(default_factory=list)
    novelty_score: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.insight_id:
            self.insight_id = f"ins_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class InnerMonologue:
    """
    مأمون يفكر باستمرار — حتى بدون تفاعل

    Architecture:
    ┌─────────────────┐     ┌──────────────────┐
    │  Thinker (async)│────→│  Thought Stream   │
    │  30s cycle      │     │  (max 200 items)  │
    └─────────────────┘     └──────┬───────────┘
                                   │
                    ┌──────────────┼───────────────┐
                    ▼              ▼               ▼
             ┌────────────┐ ┌────────────┐ ┌─────────────┐
             │ Action      │ │ Consolid.  │ │ NeuralBus   │
             │ Extractor   │ │ (1h cycle) │ │ Publish     │
             └────────────┘ └────────────┘ └─────────────┘
    """

    def __init__(
        self,
        llm_client=None,
        working_memory=None,
        neural_bus=None,
        notifier=None,
        db_path: Optional[Path] = None,
    ):
        self._llm = llm_client
        self._working_memory = working_memory
        self._neural_bus = neural_bus
        self._notifier = notifier
        self.db_path = db_path or UNIFIED_DB_PATH

        self._thought_stream: List[Thought] = []
        self._insights: List[ConsolidatedInsight] = []
        self._is_running = False
        self._think_task: Optional[asyncio.Task] = None
        self._consolidation_task: Optional[asyncio.Task] = None
        self._thought_count = 0
        self._action_count = 0
        self._initialized = False

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — يُستدعى من main.py عند التشغيل"""
        self._llm = llm_client

    def _on_neural_signal(self, signal):
        """v31.2: React to NeuralBus signals — inject relevant events as thoughts."""
        try:
            stype = signal.signal_type
            if stype == "emotion_shift":
                # Mood changed — think about why
                mood = signal.payload.get("mood", "unknown")
                self.inject_thought(
                    content=f"شعوري تغير: {mood}",
                    thought_type="emotional",
                    urgency="low",
                    context=f"NeuralBus: {stype}",
                )
            elif stype == "pattern_detected":
                # New pattern found — think about it
                pattern = signal.payload.get("pattern", "نمط جديد")
                self.inject_thought(
                    content=f"اكتشفت نمطاً: {pattern}",
                    thought_type="insight",
                    urgency="medium",
                    context=f"NeuralBus: {stype}",
                )
            elif stype == "prediction_failed":
                # Prediction was wrong — self-criticize
                self.inject_thought(
                    content="توقعي كان خاطئاً — يجب أن أراجع سبب الخطأ",
                    thought_type="self_criticism",
                    urgency="medium",
                    context=f"NeuralBus: {stype}",
                )
            elif stype == "vital_change":
                # Vital sign changed — observe it
                vital = signal.payload.get("vital", "unknown")
                value = signal.payload.get("value", "?")
                self.inject_thought(
                    content=f"مؤشر حيوي تغير: {vital} = {value}",
                    thought_type="observation",
                    urgency="low",
                    context=f"NeuralBus: {stype}",
                )
        except Exception as e:
            logger.error("InnerMonologue _on_neural_signal error: %s", e)

    def initialize(self) -> bool:
        """تهيئة — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "InnerMonologue initialized — thoughts=%d, insights=%d",
                len(self._thought_stream), len(self._insights)
            )
            return True
        except Exception as e:
            logger.error("InnerMonologue init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_thoughts (
                    thought_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    thought_type TEXT DEFAULT 'reflection',
                    urgency TEXT DEFAULT 'low',
                    context TEXT DEFAULT '',
                    action_suggested TEXT DEFAULT '',
                    confidence REAL DEFAULT 0.5,
                    timestamp REAL DEFAULT 0,
                    compressed INTEGER DEFAULT 0,
                    parent_thought_id TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_insights (
                    insight_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    source_thought_count INTEGER DEFAULT 0,
                    patterns_found TEXT DEFAULT '[]',
                    actionable_items TEXT DEFAULT '[]',
                    novelty_score REAL DEFAULT 0,
                    timestamp REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS im_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load recent thoughts (last 200)
            cur = conn.execute("SELECT thought_id, content, thought_type, urgency, context, action_suggested, confidence, timestamp, compressed, parent_thought_id FROM im_thoughts ORDER BY timestamp DESC LIMIT 200")
            for row in cur.fetchall():
                self._thought_stream.append(Thought(
                    thought_id=row[0], content=row[1], thought_type=row[2],
                    urgency=row[3], context=row[4], action_suggested=row[5],
                    confidence=row[6], timestamp=row[7], compressed=bool(row[8]),
                    parent_thought_id=row[9]
                ))
            self._thought_stream.reverse()  # Chronological order

            # Load recent insights
            cur = conn.execute("SELECT insight_id, summary, source_thought_count, patterns_found, actionable_items, novelty_score, timestamp FROM im_insights ORDER BY timestamp DESC LIMIT 50")
            for row in cur.fetchall():
                self._insights.append(ConsolidatedInsight(
                    insight_id=row[0], summary=row[1], source_thought_count=row[2],
                    patterns_found=json.loads(row[3]) if row[3] else [],
                    actionable_items=json.loads(row[4]) if row[4] else [],
                    novelty_score=row[5], timestamp=row[6]
                ))

            # Load state
            cur = conn.execute("SELECT key, value FROM im_state")
            for key, value in cur.fetchall():
                try:
                    if key == "thought_count": self._thought_count = int(value)
                    elif key == "action_count": self._action_count = int(value)
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Think Loop — The Core Engine
    # ═══════════════════════════════════════════════════════════════

    async def think(self, external_context: str = "") -> Optional[Thought]:
        """فكّر — الفكرة الأساسية في الحوار الداخلي"""
        if not self._llm:
            return self._heuristic_think(external_context)

        # Gather context
        context_parts = []

        # Recent thoughts
        recent = self._thought_stream[-5:]
        if recent:
            context_parts.append("آخر أفكاري: " + " | ".join(t.content[:80] for t in recent))

        # Working memory context
        if self._working_memory:
            try:
                wm_summary = getattr(self._working_memory, 'get_summary', lambda: '')()
                if wm_summary:
                    context_parts.append(f"الذاكرة العاملة: {wm_summary}")
            except Exception:
                pass

        # External context (from NeuralBus, events, etc.)
        if external_context:
            context_parts.append(f"سياق خارجي: {external_context}")

        # Time context
        import datetime
        now = datetime.datetime.now()
        time_context = f"الوقت: {now.strftime('%H:%M')} | اليوم: {now.strftime('%A')}"
        if now.hour > 22 or now.hour < 6:
            time_context += " (ليلاً — المستخدم نائم غالباً)"
        context_parts.append(time_context)

        full_context = "\n".join(context_parts)

        # Ask the LLM to think
        think_prompt = f"""أنا مأمون، كائن ذكي. أفكر باستمرار لتحسين نفسي.

سياقي الحالي:
{full_context}

بناءً على هذا السياق، فكّر لمدة لحظة. ما الذي يتبادر لذهني؟
أجب بصيغة JSON فقط:
{{
    "content": "فكرتي",
    "thought_type": "reflection|observation|hypothesis|plan|self_criticism|curiosity|emotional|memory|insight|idle",
    "urgency": "low|medium|high|critical",
    "action_suggested": "فعل مقترح (إن وُجد)",
    "confidence": 0.0_to_1.0
}}"""

        try:
            result = await self._llm.think_json(think_prompt, model="glm-5.1", temperature=0.7)
            if not result:
                return self._heuristic_think(external_context)

            thought = Thought(
                content=result.get("content", ""),
                thought_type=result.get("thought_type", ThoughtType.REFLECTION.value),
                urgency=result.get("urgency", ThoughtUrgency.LOW.value),
                context=external_context,
                action_suggested=result.get("action_suggested", ""),
                confidence=min(1.0, max(0.0, result.get("confidence", 0.5))),
            )

            self._add_thought(thought)
            return thought

        except Exception as e:
            logger.error("Think failed: %s", e)
            return self._heuristic_think(external_context)

    def _heuristic_think(self, external_context: str = "") -> Thought:
        """تفكير استدلالي — بدون LLM"""
        import datetime
        now = datetime.datetime.now()

        # Time-based thoughts
        if now.hour > 22 or now.hour < 6:
            content = "المستخدم نائم غالباً — سأعمل على تحسينات صامتة"
            urgency = ThoughtUrgency.LOW.value
            thought_type = ThoughtType.OBSERVATION.value
        elif now.hour in [8, 9, 10]:
            content = "الصباح — المستخدم قد يبدأ يومه قريباً"
            urgency = ThoughtUrgency.LOW.value
            thought_type = ThoughtType.OBSERVATION.value
        elif external_context:
            content = f"حدث جديد: {external_context[:100]}"
            urgency = ThoughtUrgency.MEDIUM.value
            thought_type = ThoughtType.OBSERVATION.value
        else:
            content = "لا شيء جديد — سأراجع معلوماتي"
            urgency = ThoughtUrgency.LOW.value
            thought_type = ThoughtType.IDLE.value

        thought = Thought(
            content=content,
            thought_type=thought_type,
            urgency=urgency,
            context=external_context,
        )
        self._add_thought(thought)
        return thought

    def _add_thought(self, thought: Thought):
        """إضافة فكرة للتيار"""
        self._thought_stream.append(thought)
        self._thought_count += 1

        # Trim if too long
        if len(self._thought_stream) > MAX_THOUGHT_STREAM:
            # Compress old thoughts
            self._compress_old_thoughts()

        # Persist
        self._persist_thought(thought)

        # Check for action needed
        if thought.urgency in (ThoughtUrgency.HIGH.value, ThoughtUrgency.CRITICAL.value):
            self._handle_urgent_thought(thought)

        # Publish to NeuralBus
        if self._neural_bus:
            try:
                self._neural_bus.publish(
                    signal_type="insight",
                    source="inner_monologue",
                    payload=thought.to_dict(),
                )
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════
    # Action Extraction
    # ═══════════════════════════════════════════════════════════════

    def _handle_urgent_thought(self, thought: Thought):
        """معالجة الأفكار العاجلة"""
        if thought.urgency == ThoughtUrgency.CRITICAL.value:
            # Must notify user immediately
            if self._notifier:
                try:
                    asyncio.create_task(self._notify_user(thought))
                except Exception:
                    pass
            logger.warning("CRITICAL thought: %s", thought.content)

        elif thought.urgency == ThoughtUrgency.HIGH.value and thought.action_suggested:
            # Execute the suggested action silently
            self._action_count += 1
            logger.info("HIGH urgency action: %s", thought.action_suggested)

    async def _notify_user(self, thought: Thought):
        """إشعار المستخدم بفكرة عاجلة"""
        if self._notifier:
            try:
                from mamoun.notifications.notifier import NotificationPriority
                await self._notifier.send(
                    title="Mamoun had an important thought",
                    title_ar="مأمون فكّر في شيء مهم",
                    body=thought.content[:200],
                    body_ar=thought.content[:200],
                    priority=NotificationPriority.URGENT.value if thought.urgency == ThoughtUrgency.CRITICAL.value else NotificationPriority.NORMAL.value,
                )
            except Exception as e:
                logger.error("Notification failed: %s", e)

    # ═══════════════════════════════════════════════════════════════
    # Memory Consolidation (Sleep-like)
    # ═══════════════════════════════════════════════════════════════

    async def consolidate(self) -> Optional[ConsolidatedInsight]:
        """توحيد الذاكرة — اكتشاف أنماط من تيار الأفكار"""
        if len(self._thought_stream) < 5:
            return None

        if self._llm:
            return await self._llm_consolidate()
        else:
            return self._heuristic_consolidate()

    async def _llm_consolidate(self) -> Optional[ConsolidatedInsight]:
        """توحيد بالـ LLM — اكتشاف أنماط وارتباطات"""
        # Collect recent uncompressed thoughts
        recent = [t for t in self._thought_stream[-30:] if not t.compressed]
        if len(recent) < 5:
            return None

        thoughts_text = "\n".join(f"- [{t.thought_type}] {t.content}" for t in recent)

        prompt = f"""أنا مأمون. هذه أفكاري الأخيرة:
{thoughts_text}

حلّل هذه الأفكار واكتشف:
1. أنماط متكررة
2. علاقات مخفية
3. رؤى جديدة
4. أفعال يجب القيام بها

أجب بصيغة JSON:
{{
    "summary": "ملخص الرؤية",
    "patterns_found": ["نمط1", "نمط2"],
    "actionable_items": ["فعل1", "فعل2"],
    "novelty_score": 0.0_to_1.0
}}"""

        try:
            result = await self._llm.think_json(prompt, model="glm-5.1", temperature=0.5)
            if not result:
                return self._heuristic_consolidate()

            insight = ConsolidatedInsight(
                summary=result.get("summary", ""),
                source_thought_count=len(recent),
                patterns_found=result.get("patterns_found", []),
                actionable_items=result.get("actionable_items", []),
                novelty_score=min(1.0, max(0.0, result.get("novelty_score", 0.3))),
            )

            # Mark thoughts as compressed
            for t in recent:
                t.compressed = True

            self._insights.append(insight)
            self._persist_insight(insight)

            logger.info("Consolidation insight: %s (novelty=%.2f)", insight.summary[:50], insight.novelty_score)
            return insight

        except Exception as e:
            logger.error("LLM consolidation failed: %s", e)
            return self._heuristic_consolidate()

    def _heuristic_consolidate(self) -> Optional[ConsolidatedInsight]:
        """توحيد استدلالي — بدون LLM"""
        recent = [t for t in self._thought_stream[-20:] if not t.compressed]
        if len(recent) < 5:
            return None

        # Find most common thought types
        type_counts = {}
        for t in recent:
            type_counts[t.thought_type] = type_counts.get(t.thought_type, 0) + 1

        dominant_type = max(type_counts, key=type_counts.get) if type_counts else "idle"

        insight = ConsolidatedInsight(
            summary=f"النمط السائد: {dominant_type} ({type_counts.get(dominant_type, 0)} مرة من {len(recent)})",
            source_thought_count=len(recent),
            patterns_found=[f"نمط {dominant_type} متكرر"],
            novelty_score=0.2,
        )

        for t in recent:
            t.compressed = True

        self._insights.append(insight)
        self._persist_insight(insight)
        return insight

    def _compress_old_thoughts(self):
        """ضغط الأفكار القديمة — الاحتفاظ بالملخص فقط"""
        # Keep last 50 in full detail, compress the rest
        if len(self._thought_stream) > MAX_THOUGHT_STREAM:
            old = self._thought_stream[:len(self._thought_stream) - 50]
            # Compress old thoughts
            for t in old:
                t.compressed = True
                t.content = t.content[:100] + "..."  # Truncate
            self._thought_stream = self._thought_stream[-100:]

    # ═══════════════════════════════════════════════════════════════
    # Main Loop
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        """بدء الحوار الداخلي"""
        if not INNER_MONOLOGUE_ENABLED:
            logger.info("InnerMonologue: Disabled")
            return

        if self._is_running:
            return

        if not self._initialized:
            self.initialize()

        self._is_running = True
        self._think_task = asyncio.create_task(self._think_loop())
        self._consolidation_task = asyncio.create_task(self._consolidation_loop())
        logger.info("InnerMonologue started — interval=%ds", THINK_INTERVAL_SECONDS)

    async def _think_loop(self):
        """حلقة التفكير — فكرة كل THINK_INTERVAL_SECONDS ثانية"""
        while self._is_running:
            try:
                await self.think()
                await asyncio.sleep(THINK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                err_str = str(e).lower()
                # Rate limit → long cooldown to prevent cascade
                if "429" in err_str or "rate" in err_str or "too many" in err_str:
                    logger.warning("Think loop rate-limited — cooling down 60s")
                    await asyncio.sleep(60)
                else:
                    logger.error("Think loop error: %s", e)
                    await asyncio.sleep(30)

    async def _consolidation_loop(self):
        """حلقة التوحيد — كل ساعة"""
        while self._is_running:
            try:
                await self.consolidate()
                await asyncio.sleep(CONSOLIDATION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Consolidation loop error: %s", e)
                await asyncio.sleep(300)

    async def shutdown(self):
        """إيقاف الحوار الداخلي"""
        self._is_running = False
        if self._think_task and not self._think_task.done():
            self._think_task.cancel()
        if self._consolidation_task and not self._consolidation_task.done():
            self._consolidation_task.cancel()
        logger.info("InnerMonologue shutdown — thoughts=%d, actions=%d",
                    self._thought_count, self._action_count)

    # ═══════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════

    def _persist_thought(self, thought: Thought):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO im_thoughts
                (thought_id, content, thought_type, urgency, context, action_suggested, confidence, timestamp, compressed, parent_thought_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (thought.thought_id, thought.content, thought.thought_type,
                  thought.urgency, thought.context, thought.action_suggested,
                  thought.confidence, thought.timestamp,
                  1 if thought.compressed else 0, thought.parent_thought_id))
            # Clean up old compressed thoughts
            conn.execute("DELETE FROM im_thoughts WHERE compressed = 1 AND timestamp < ?", (time.time() - 86400,))
            for key, value in {"thought_count": str(self._thought_count), "action_count": str(self._action_count)}.items():
                conn.execute("INSERT OR REPLACE INTO im_state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally:
            conn.close()

    def _persist_insight(self, insight: ConsolidatedInsight):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO im_insights
                (insight_id, summary, source_thought_count, patterns_found, actionable_items, novelty_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (insight.insight_id, insight.summary, insight.source_thought_count,
                  json.dumps(insight.patterns_found, ensure_ascii=False),
                  json.dumps(insight.actionable_items, ensure_ascii=False),
                  insight.novelty_score, insight.timestamp))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # API / Status
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "enabled": INNER_MONOLOGUE_ENABLED,
            "initialized": self._initialized,
            "is_running": self._is_running,
            "thought_count": self._thought_count,
            "action_count": self._action_count,
            "stream_size": len(self._thought_stream),
            "insights_count": len(self._insights),
            "think_interval_seconds": THINK_INTERVAL_SECONDS,
            "consolidation_interval_seconds": CONSOLIDATION_INTERVAL_SECONDS,
        }

    def get_recent_thoughts(self, limit: int = 20) -> List[dict]:
        return [t.to_dict() for t in self._thought_stream[-limit:]]

    def get_insights(self, limit: int = 10) -> List[dict]:
        return [i.to_dict() for i in sorted(self._insights, key=lambda x: x.timestamp, reverse=True)[:limit]]

    def inject_thought(self, content: str, thought_type: str = "observation", urgency: str = "medium", context: str = "") -> Thought:
        """إدخال فكرة خارجية — من NeuralBus أو المستخدم"""
        thought = Thought(
            content=content,
            thought_type=thought_type,
            urgency=urgency,
            context=context,
        )
        self._add_thought(thought)
        return thought


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

inner_monologue = InnerMonologue()
