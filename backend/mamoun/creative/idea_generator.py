"""
BABSHARQII v24.0 — Idea Generator
مأمون يربط أفكار غير مترابطة — يبتكر

v24 Architecture (4-stage creativity pipeline):
1. DIVERGE: 5 brains explore from different perspectives
2. COMBINE: Synthesize perspectives into novel combinations
3. SCORE: Novelty + Utility + Surprise evaluation
4. TRANSFORM: Refine high-scoring ideas into actionable proposals

Research basis:
- Decomposition achieves 4.17/5 vs 2.33/5 for reflection
- Multi-perspective > single-perspective by 1.8x for creativity
- Novelty-utility tradeoff: ideas must be both new AND useful
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

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.idea_generator")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

IDEA_GENERATOR_ENABLED = os.environ.get("MAMOUN_IDEA_GENERATOR", "true").lower() in ("true", "1", "yes")
CREATIVE_SESSION_INTERVAL_HOURS = int(os.environ.get("MAMOUN_CREATIVE_INTERVAL", "6"))
NOVELTY_THRESHOLD = float(os.environ.get("MAMOUN_NOVELTY_THRESHOLD", "0.7"))


class IdeaStage:
    """مراحل الإبداع"""
    DIVERGE = "diverge"
    COMBINE = "combine"
    SCORE = "score"
    TRANSFORM = "transform"


class IdeaStatus:
    DRAFT = "draft"
    EVALUATED = "evaluated"
    NOTIFIED = "notified"
    ARCHIVED = "archived"


@dataclass
class CreativePerspective:
    """منظور دماغي واحد"""
    brain_id: str = ""
    brain_name: str = ""
    perspective: str = ""
    keywords: List[str] = field(default_factory=list)
    novelty: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Idea:
    """فكرة إبداعية"""
    idea_id: str = ""
    title: str = ""
    description: str = ""
    stage: str = IdeaStage.DIVERGE
    status: str = IdeaStatus.DRAFT

    # Scoring
    novelty_score: float = 0.0
    utility_score: float = 0.0
    surprise_score: float = 0.0
    overall_score: float = 0.0

    # Perspectives from 5 brains
    perspectives: List[Dict[str, Any]] = field(default_factory=list)

    # Actionable items
    action_plan: str = ""
    estimated_impact: str = ""

    # Metadata
    source_memories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = 0.0
    evaluated_at: float = 0.0

    def __post_init__(self):
        if not self.idea_id:
            self.idea_id = f"idea_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class IdeaGenerator:
    """
    مأمون يربط أفكار غير مترابطة — يبتكر

    Pipeline:
    ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌────────────┐
    │ DIVERGE   │──→│ COMBINE   │──→│ SCORE     │──→│ TRANSFORM  │
    │ 5 brains  │   │ Synthesize│   │ Novel+Util│   │ Actionable │
    └───────────┘   └───────────┘   └───────────┘   └────────────┘
         │                                              │
         ▼                                              ▼
    ┌───────────┐                                ┌────────────┐
    │ Memory    │                                │ Notify     │
    │ Retrieval │                                │ User       │
    └───────────┘                                └────────────┘
    """

    def __init__(
        self,
        llm_client=None,
        brains_router=None,
        notifier=None,
        novelty_scorer=None,
        db_path: Optional[Path] = None,
    ):
        self._llm = llm_client
        self._brains = brains_router
        self._notifier = notifier
        self._novelty_scorer = novelty_scorer
        self.db_path = db_path or UNIFIED_DB_PATH

        self._ideas: List[Idea] = []
        self._is_running = False
        self._creative_task: Optional[asyncio.Task] = None
        self._idea_count = 0
        self._high_novelty_count = 0
        self._initialized = False

    def set_llm_client(self, llm_client):
        """تعيين عميل LLM — يُستدعى من main.py عند التشغيل"""
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("IdeaGenerator initialized — ideas=%d, high_novelty=%d",
                       len(self._ideas), self._high_novelty_count)
            return True
        except Exception as e:
            logger.error("IdeaGenerator init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ig_ideas (
                    idea_id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    stage TEXT DEFAULT 'diverge',
                    status TEXT DEFAULT 'draft',
                    novelty_score REAL DEFAULT 0,
                    utility_score REAL DEFAULT 0,
                    surprise_score REAL DEFAULT 0,
                    overall_score REAL DEFAULT 0,
                    perspectives TEXT DEFAULT '[]',
                    action_plan TEXT DEFAULT '',
                    estimated_impact TEXT DEFAULT '',
                    source_memories TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    created_at REAL DEFAULT 0,
                    evaluated_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ig_state (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            cur = conn.execute("SELECT key, value FROM ig_state")
            for key, value in cur.fetchall():
                try:
                    if key == "idea_count": self._idea_count = int(value)
                    elif key == "high_novelty_count": self._high_novelty_count = int(value)
                except (ValueError, TypeError):
                    pass
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Stage 1: DIVERGE — 5 Brains Explore
    # ═══════════════════════════════════════════════════════════════

    async def _diverge(self, topic: str = "") -> List[CreativePerspective]:
        """كل دماغ يستكشف من منظور مختلف"""
        perspectives = []

        brain_prompts = {
            "neural": "ما الأنماط المخفية؟ ما العلاقات العميقة بين الأشياء؟",
            "causal": "ما العلاقات السببية؟ ما الذي يسبب ماذا؟",
            "symbolic": "ما القواعد والمنطق؟ ما البنية الرياضية؟",
            "bayesian": "ما الاحتمالات؟ ما أكثر السيناريوهات احتمالاً؟",
            "world_model": "ماذا لو...؟ ما السيناريوهات المستقبلية؟",
        }

        if self._llm:
            # Use LLM for each brain's perspective
            for brain_id, prompt in brain_prompts.items():
                try:
                    full_prompt = f"""أنا مأمون. أحاول الإبداع حول: {topic or 'تحسين ذاتي'}
منظوري كدماغ {brain_id}: {prompt}

أعطني منظوراً فريداً ومبتكراً. أجب بـ JSON:
{{
    "perspective": "منظوري",
    "keywords": ["كلمة1", "كلمة2", "كلمة3"],
    "novelty": 0.0_to_1.0
}}"""
                    result = await self._llm.think_json(full_prompt, model="glm-5.1", temperature=0.8)
                    if result:
                        perspectives.append(CreativePerspective(
                            brain_id=brain_id,
                            brain_name=brain_id.replace("_", " ").title(),
                            perspective=result.get("perspective", ""),
                            keywords=result.get("keywords", []),
                            novelty=result.get("novelty", 0.5),
                        ))
                except Exception as e:
                    logger.warning("Diverge failed for brain %s: %s", brain_id, e)
                    # Heuristic fallback
                    perspectives.append(CreativePerspective(
                        brain_id=brain_id,
                        brain_name=brain_id.replace("_", " ").title(),
                        perspective=prompt,
                        novelty=0.3,
                    ))
        else:
            # No LLM — use heuristic perspectives
            for brain_id, prompt in brain_prompts.items():
                perspectives.append(CreativePerspective(
                    brain_id=brain_id,
                    brain_name=brain_id.replace("_", " ").title(),
                    perspective=prompt,
                    novelty=0.3,
                ))

        return perspectives

    # ═══════════════════════════════════════════════════════════════
    # Stage 2: COMBINE — Synthesize Perspectives
    # ═══════════════════════════════════════════════════════════════

    async def _combine(self, perspectives: List[CreativePerspective], topic: str = "") -> Idea:
        """دمج المنظورات الخمسة في فكرة واحدة جديدة"""
        idea = Idea(
            stage=IdeaStage.COMBINE,
            perspectives=[p.to_dict() for p in perspectives],
        )

        if self._llm and perspectives:
            persp_text = "\n".join(
                f"- {p.brain_name}: {p.perspective} (كلمات: {', '.join(p.keywords[:3])})"
                for p in perspectives
            )

            combine_prompt = f"""أنا مأمون. هذه 5 منظورات مختلفة عن: {topic or 'تحسين ذاتي'}

{persp_text}

اربط هذه المنظورات الخمسة في فكرة واحدة جديدة لم تخطر على بال أحد.
يجب أن تكون الفكرة مبتكرة AND مفيدة (ليس فقط مبتكرة).

أجب بـ JSON:
{{
    "title": "عنوان الفكرة",
    "description": "وصف مفصل",
    "tags": ["tag1", "tag2"],
    "estimated_impact": "التأثير المتوقع"
}}"""

            try:
                result = await self._llm.think_json(combine_prompt, model="glm-5.1", temperature=0.9)
                if result:
                    idea.title = result.get("title", "فكرة بدون عنوان")
                    idea.description = result.get("description", "")
                    idea.tags = result.get("tags", [])
                    idea.estimated_impact = result.get("estimated_impact", "")
            except Exception as e:
                logger.error("Combine failed: %s", e)
                idea.title = "فكرة تجريبية"
                idea.description = "دمج المنظورات: " + " + ".join(p.perspective[:30] for p in perspectives)
        else:
            idea.title = "فكرة تجريبية"
            idea.description = "دمج بسيط للمنظورات"

        return idea

    # ═══════════════════════════════════════════════════════════════
    # Stage 3: SCORE — Evaluate Novelty + Utility + Surprise
    # ═══════════════════════════════════════════════════════════════

    async def _score(self, idea: Idea) -> Idea:
        """تقييم الفكرة — الإبداع والفائدة معاً"""
        idea.stage = IdeaStage.SCORE

        if self._llm and idea.description:
            score_prompt = f"""قيّم هذه الفكرة:
العنوان: {idea.title}
الوصف: {idea.description}

قيّم من 0 إلى 1:
1. novelty: مدى جدتها (0 = معروف جداً، 1 = لم يسمع به أحد)
2. utility: مدى فائدته (0 = غير مفيد, 1 = مفيد جداً)
3. surprise: مدى المفاجأة (0 = متوقع, 1 = مذهل)

أجب بـ JSON:
{{
    "novelty": 0.0_to_1.0,
    "utility": 0.0_to_1.0,
    "surprise": 0.0_to_1.0,
    "feedback": "ملاحظات"
}}"""

            try:
                result = await self._llm.think_json(score_prompt, model="glm-5.1", temperature=0.3)
                if result:
                    idea.novelty_score = min(1.0, max(0.0, result.get("novelty", 0.5)))
                    idea.utility_score = min(1.0, max(0.0, result.get("utility", 0.5)))
                    idea.surprise_score = min(1.0, max(0.0, result.get("surprise", 0.3)))
            except Exception as e:
                logger.error("Scoring failed: %s", e)

        # Calculate overall score (weighted: novelty 35%, utility 40%, surprise 25%)
        idea.overall_score = (
            idea.novelty_score * 0.35 +
            idea.utility_score * 0.40 +
            idea.surprise_score * 0.25
        )
        idea.evaluated_at = time.time()
        idea.status = IdeaStatus.EVALUATED

        return idea

    # ═══════════════════════════════════════════════════════════════
    # Stage 4: TRANSFORM — Make Actionable
    # ═══════════════════════════════════════════════════════════════

    async def _transform(self, idea: Idea) -> Idea:
        """تحويل الفكرة لخطة عمل"""
        idea.stage = IdeaStage.TRANSFORM

        if self._llm and idea.overall_score >= NOVELTY_THRESHOLD:
            transform_prompt = f"""حول هذه الفكرة إلى خطة عمل:
العنوان: {idea.title}
الوصف: {idea.description}
التقييم: novelty={idea.novelty_score:.2f}, utility={idea.utility_score:.2f}

أجب بـ JSON:
{{
    "action_plan": "خطوات التنفيذ",
    "estimated_impact": "التأثير المتوقع"
}}"""

            try:
                result = await self._llm.think_json(transform_prompt, model="glm-5.1", temperature=0.5)
                if result:
                    idea.action_plan = result.get("action_plan", "")
                    idea.estimated_impact = result.get("estimated_impact", idea.estimated_impact)
            except Exception:
                pass

        return idea

    # ═══════════════════════════════════════════════════════════════
    # Full Creative Pipeline
    # ═══════════════════════════════════════════════════════════════

    async def creative_session(self, topic: str = "") -> Optional[Idea]:
        """جلسة إبداعية كاملة — 4 مراحل"""
        logger.info("Creative session started — topic: %s", topic or "auto")

        # Stage 1: Diverge
        perspectives = await self._diverge(topic)
        if not perspectives:
            return None

        # Stage 2: Combine
        idea = await self._combine(perspectives, topic)

        # Stage 3: Score
        idea = await self._score(idea)

        # Stage 4: Transform (only if score is high enough)
        if idea.overall_score >= NOVELTY_THRESHOLD:
            idea = await self._transform(idea)
            self._high_novelty_count += 1

            # Notify user about high-novelty idea
            if self._notifier:
                try:
                    from mamoun.notifications.notifier import NotificationPriority
                    await self._notifier.send(
                        title=f"New Idea: {idea.title[:50]}",
                        title_ar=f"فكرة جديدة: {idea.title[:50]}",
                        body=idea.description[:200],
                        body_ar=idea.description[:200],
                        priority=NotificationPriority.NORMAL.value,
                    )
                    idea.status = IdeaStatus.NOTIFIED
                except Exception:
                    pass

        # Save
        self._ideas.append(idea)
        self._idea_count += 1
        self._persist_idea(idea)

        logger.info("Creative session complete — idea=%s, score=%.2f, novelty=%.2f",
                    idea.idea_id, idea.overall_score, idea.novelty_score)
        return idea

    # ═══════════════════════════════════════════════════════════════
    # Main Loop
    # ═══════════════════════════════════════════════════════════════

    async def start(self):
        if not IDEA_GENERATOR_ENABLED:
            logger.info("IdeaGenerator: Disabled")
            return
        if self._is_running:
            return
        if not self._initialized:
            self.initialize()

        self._is_running = True
        self._creative_task = asyncio.create_task(self._creative_loop())
        logger.info("IdeaGenerator started — interval=%d hours", CREATIVE_SESSION_INTERVAL_HOURS)

    async def _creative_loop(self):
        while self._is_running:
            try:
                await self.creative_session()
                await asyncio.sleep(CREATIVE_SESSION_INTERVAL_HOURS * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Creative loop error: %s", e)
                await asyncio.sleep(600)

    async def shutdown(self):
        self._is_running = False
        if self._creative_task and not self._creative_task.done():
            self._creative_task.cancel()
        logger.info("IdeaGenerator shutdown — ideas=%d, high_novelty=%d",
                    self._idea_count, self._high_novelty_count)

    # ═══════════════════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════════════════

    def _persist_idea(self, idea: Idea):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO ig_ideas
                (idea_id, title, description, stage, status, novelty_score, utility_score, surprise_score,
                 overall_score, perspectives, action_plan, estimated_impact, source_memories, tags, created_at, evaluated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (idea.idea_id, idea.title, idea.description, idea.stage, idea.status,
                  idea.novelty_score, idea.utility_score, idea.surprise_score, idea.overall_score,
                  json.dumps(idea.perspectives, ensure_ascii=False),
                  idea.action_plan, idea.estimated_impact,
                  json.dumps(idea.source_memories), json.dumps(idea.tags, ensure_ascii=False),
                  idea.created_at, idea.evaluated_at))
            for key, value in {"idea_count": str(self._idea_count),
                              "high_novelty_count": str(self._high_novelty_count)}.items():
                conn.execute("INSERT OR REPLACE INTO ig_state (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # API
    # ═══════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "enabled": IDEA_GENERATOR_ENABLED,
            "initialized": self._initialized,
            "is_running": self._is_running,
            "idea_count": self._idea_count,
            "high_novelty_count": self._high_novelty_count,
            "novelty_threshold": NOVELTY_THRESHOLD,
            "interval_hours": CREATIVE_SESSION_INTERVAL_HOURS,
        }

    def get_ideas(self, limit: int = 20, min_score: float = 0.0) -> List[dict]:
        ideas = [i for i in self._ideas if i.overall_score >= min_score]
        return [i.to_dict() for i in sorted(ideas, key=lambda x: x.overall_score, reverse=True)[:limit]]

    def get_top_ideas(self, limit: int = 5) -> List[dict]:
        return self.get_ideas(limit=limit, min_score=NOVELTY_THRESHOLD)


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

idea_generator = IdeaGenerator()
