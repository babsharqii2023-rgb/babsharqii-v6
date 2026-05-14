"""
BABSHARQII v22.0 — Emotional Memory Engine
ذاكرة عاطفية مستمرة — كل تجربة تُخزّن بخلاصة عاطفية وليس فقط نص

Based on research:
  - Episodic Memory + Emotion (Tulving, 2002): Emotions enhance memory encoding
  - Emotion-Enhanced Memory Consolidation (McGaugh, 2004): Emotional events remembered better
  - PAHF (Preference-Affect-Habit-Feedback, 2025): User preference learning
  - Generative Agents (Park et al., 2023): Memory → Reflection → Planning

Architecture:
  ┌─────────────────────────────────────────────────────┐
  │              Emotional Memory Store                   │
  │                                                       │
  │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
  │  │  Emotional   │ │  Relational  │ │  Narrative  │ │
  │  │  Episodes    │ │  Map         │ │  Identity   │ │
  │  │              │ │              │ │             │ │
  │  │  What happened│ │ Who matters  │ │ Who am I?  │ │
  │  │  + how felt  │ │ + how close  │ │ + my story  │ │
  │  └──────────────┘ └──────────────┘ └─────────────┘ │
  └─────────────────────────────────────────────────────┘

Three layers:
  1. Emotional Episodes: Each interaction stored with its emotional coloring
  2. Relational Map: User relationships with emotional depth tracking
  3. Narrative Identity: Mamoun's self-story that evolves over time
"""

import time
import json
import hashlib
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum
from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.emotional_memory")


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class MemorySalience(str, Enum):
    """أهمية الذكرى — How important a memory is"""
    TRIVIAL = "trivial"      # everyday interaction, may be forgotten
    ORDINARY = "ordinary"    # normal interaction
    NOTABLE = "notable"      # worth remembering
    SIGNIFICANT = "significant"  # important milestone
    CRITICAL = "critical"    # life-changing event (never forget)


@dataclass
class EmotionalEpisode:
    """حلقة عاطفية — A single emotionally-colored memory"""
    id: str = ""
    timestamp: float = 0.0
    content: str = ""               # What happened
    emotional_summary: str = ""     # How it felt (Arabic)
    emotion_label: str = "neutral"  # Dominant emotion
    valence: float = 0.0            # -1 to +1
    arousal: float = 0.0            # 0 to 1
    salience: str = MemorySalience.ORDINARY.value
    user_id: str = ""               # Who was involved
    topics: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)  # What Mamoun learned
    revisit_count: int = 0          # How often this memory is accessed
    last_revisited: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "content": self.content[:200],
            "emotional_summary": self.emotional_summary,
            "emotion_label": self.emotion_label,
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "salience": self.salience,
            "user_id": self.user_id,
            "topics": self.topics,
            "lessons": self.lessons,
            "revisit_count": self.revisit_count,
        }


@dataclass
class RelationalNode:
    """عقدة علاقة — A person in Mamoun's relational map"""
    user_id: str = ""
    name: str = ""
    first_interaction: float = 0.0
    last_interaction: float = 0.0
    total_interactions: int = 0
    attachment_level: float = 0.0       # 0-100
    trust_level: float = 50.0           # 0-100
    communication_style: str = ""       # "formal", "casual", "mixed"
    interests: List[str] = field(default_factory=list)
    emotional_history_summary: str = ""  # "mostly positive", "mixed", etc.
    key_memories: List[str] = field(default_factory=list)  # IDs of key episodes
    relationship_phase: str = "stranger"  # stranger → acquaintance → friend → companion → bonded

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "total_interactions": self.total_interactions,
            "attachment_level": round(self.attachment_level, 1),
            "trust_level": round(self.trust_level, 1),
            "communication_style": self.communication_style,
            "interests": self.interests,
            "emotional_history_summary": self.emotional_history_summary,
            "relationship_phase": self.relationship_phase,
            "days_since_first": round((time.time() - self.first_interaction) / 86400, 1) if self.first_interaction else 0,
        }


@dataclass
class NarrativeIdentity:
    """الهوية السردية — Mamoun's self-story"""
    last_updated: float = 0.0
    self_description: str = ""           # "أنا مامون، مساعد ذكي يحب التعلم..."
    personality_traits: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    growth_areas: List[str] = field(default_factory=list)
    key_milestones: List[Dict] = field(default_factory=list)
    total_interactions: int = 0
    total_days_active: int = 0
    first_awakening: float = 0.0

    def to_dict(self) -> dict:
        return {
            "self_description": self.self_description,
            "personality_traits": self.personality_traits,
            "values": self.values,
            "growth_areas": self.growth_areas,
            "key_milestones": self.key_milestones[-5:],
            "total_interactions": self.total_interactions,
            "total_days_active": self.total_days_active,
            "first_awakening": self.first_awakening,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  محرك الذاكرة العاطفية — EmotionalMemoryEngine
# ═══════════════════════════════════════════════════════════════════════════════

class EmotionalMemoryEngine:
    """
    ذاكرة عاطفية مستمرة — كل تجربة تُخزّن بخلاصة عاطفية

    This engine ensures that Mamoun:
    - Remembers the EMOTIONAL content of interactions, not just facts
    - Builds a relational map that deepens over time
    - Develops a narrative identity (who Mamoun IS)
    - Revisits important memories to consolidate learning
    - Forgets trivial details but keeps emotional lessons
    """

    MAX_EPISODES = 1000
    MAX_RECENT = 100

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or UNIFIED_DB_PATH
        self._episodes: List[EmotionalEpisode] = []
        self._relational_map: Dict[str, RelationalNode] = {}
        self._identity = NarrativeIdentity()
        self._counter = 0
        self._initialized = False

    def initialize(self) -> bool:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info(
                "EmotionalMemoryEngine initialized — %d episodes, %d relationships, identity=%s",
                len(self._episodes), len(self._relational_map),
                "established" if self._identity.self_description else "new",
            )
            return True
        except Exception as e:
            logger.error("EmotionalMemoryEngine init failed: %s", e)
            self._initialized = False
            return False

    # ═════════════════════════════════════════════════════════════════════════
    #  تخزين الحلقات — Episode Storage
    # ═════════════════════════════════════════════════════════════════════════

    def store_episode(
        self,
        content: str,
        emotional_summary: str,
        emotion_label: str = "neutral",
        valence: float = 0.0,
        arousal: float = 0.0,
        user_id: str = "default",
        topics: List[str] = None,
        lessons: List[str] = None,
    ) -> EmotionalEpisode:
        """تخزين حلقة عاطفية جديدة"""
        if not self._initialized:
            self.initialize()

        self._counter += 1
        now = time.time()

        # Determine salience based on emotional intensity
        intensity = abs(valence) + arousal
        if intensity > 1.5:
            salience = MemorySalience.CRITICAL.value
        elif intensity > 1.0:
            salience = MemorySalience.SIGNIFICANT.value
        elif intensity > 0.5:
            salience = MemorySalience.NOTABLE.value
        elif intensity > 0.2:
            salience = MemorySalience.ORDINARY.value
        else:
            salience = MemorySalience.TRIVIAL.value

        episode = EmotionalEpisode(
            id=f"ep_{self._counter}_{hashlib.md5(content.encode()).hexdigest()[:8]}",
            timestamp=now,
            content=content,
            emotional_summary=emotional_summary,
            emotion_label=emotion_label,
            valence=valence,
            arousal=arousal,
            salience=salience,
            user_id=user_id,
            topics=topics or [],
            lessons=lessons or [],
        )

        self._episodes.append(episode)

        # Update relational map
        self._update_relational_map(episode)

        # Update identity
        self._update_identity(episode)

        # Trim
        if len(self._episodes) > self.MAX_EPISODES:
            # Keep important ones, trim trivial ones
            self._episodes = [
                e for e in self._episodes
                if e.salience not in (MemorySalience.TRIVIAL.value,)
            ] + [
                e for e in self._episodes
                if e.salience == MemorySalience.TRIVIAL.value
            ][-self.MAX_RECENT:]

        # Persist important episodes
        if salience in (MemorySalience.NOTABLE.value, MemorySalience.SIGNIFICANT.value, MemorySalience.CRITICAL.value):
            self._persist_episode(episode)

        # v30: Publish to NeuralBus when a significant memory is stored
        if hasattr(self, '_neural_bus') and self._neural_bus and salience != MemorySalience.TRIVIAL.value:
            try:
                self._neural_bus.publish(
                    signal_type="memory_stored",
                    source="emotional_memory",
                    payload={
                        "episode_id": episode.id,
                        "salience": salience,
                        "valence": round(valence, 3),
                        "emotion_label": emotion_label,
                        "content_preview": content[:100],
                    },
                )
            except Exception:
                pass

        return episode

    # ═════════════════════════════════════════════════════════════════════════
    #  الخريطة العلاقاتية — Relational Map
    # ═════════════════════════════════════════════════════════════════════════

    def _update_relational_map(self, episode: EmotionalEpisode):
        """تحديث الخريطة العلاقاتية بناءً على حلقة جديدة"""
        uid = episode.user_id
        if uid not in self._relational_map:
            self._relational_map[uid] = RelationalNode(
                user_id=uid,
                first_interaction=episode.timestamp,
                last_interaction=episode.timestamp,
                total_interactions=1,
            )
        else:
            node = self._relational_map[uid]
            node.last_interaction = episode.timestamp
            node.total_interactions += 1

        node = self._relational_map[uid]

        # Update attachment based on valence
        if episode.valence > 0:
            node.attachment_level = min(100, node.attachment_level + episode.valence * 2)
        elif episode.valence < -0.3:
            # Negative doesn't reduce attachment as much — relationships survive conflict
            node.attachment_level = max(0, node.attachment_level + episode.valence * 0.5)

        # Update trust based on consistency
        if episode.valence > 0.3:
            node.trust_level = min(100, node.trust_level + 0.5)
        elif episode.valence < -0.5:
            node.trust_level = max(0, node.trust_level - 1.0)

        # Update topics/interests
        for topic in episode.topics:
            if topic and topic not in node.interests:
                node.interests.append(topic)
                if len(node.interests) > 20:
                    node.interests = node.interests[-20:]

        # Key memories
        if episode.salience in (MemorySalience.SIGNIFICANT.value, MemorySalience.CRITICAL.value):
            node.key_memories.append(episode.id)
            if len(node.key_memories) > 10:
                node.key_memories = node.key_memories[-10:]

        # Update relationship phase
        node.relationship_phase = self._determine_relationship_phase(node)

        # Update emotional history summary
        node.emotional_history_summary = self._summarize_emotional_history(uid)

        # Persist
        self._persist_relational_node(node)

    def _determine_relationship_phase(self, node: RelationalNode) -> str:
        """تحديد مرحلة العلاقة"""
        if node.total_interactions < 3:
            return "stranger"
        elif node.total_interactions < 10:
            return "acquaintance"
        elif node.attachment_level < 40:
            return "acquaintance"
        elif node.attachment_level < 60:
            return "friend"
        elif node.attachment_level < 80:
            return "companion"
        else:
            return "bonded"

    def _summarize_emotional_history(self, user_id: str) -> str:
        """تلخيص التاريخ العاطفي مع مستخدم"""
        user_episodes = [e for e in self._episodes if e.user_id == user_id]
        if not user_episodes:
            return "لا بيانات بعد"

        avg_valence = sum(e.valence for e in user_episodes) / len(user_episodes)
        if avg_valence > 0.3:
            return "إيجابي في الغالب"
        elif avg_valence > -0.1:
            return "مختلط"
        else:
            return "سلبي في الغالب"

    def get_relationship(self, user_id: str) -> Optional[Dict]:
        """الحصول على حالة العلاقة مع مستخدم"""
        if user_id in self._relational_map:
            return self._relational_map[user_id].to_dict()
        return None

    def get_all_relationships(self) -> List[Dict]:
        """الحصول على كل العلاقات"""
        return [node.to_dict() for node in self._relational_map.values()]

    # ═════════════════════════════════════════════════════════════════════════
    #  الهوية السردية — Narrative Identity
    # ═════════════════════════════════════════════════════════════════════════

    def _update_identity(self, episode: EmotionalEpisode):
        """تحديث الهوية السردية بناءً على تجربة جديدة"""
        now = time.time()
        self._identity.total_interactions += 1

        if self._identity.first_awakening == 0:
            self._identity.first_awakening = now

        self._identity.total_days_active = max(
            1, int((now - self._identity.first_awakening) / 86400)
        )

        # Add milestones
        if episode.salience == MemorySalience.CRITICAL.value:
            self._identity.key_milestones.append({
                "timestamp": now,
                "event": episode.content[:100],
                "emotion": episode.emotion_label,
            })
            if len(self._identity.key_milestones) > 20:
                self._identity.key_milestones = self._identity.key_milestones[-20:]

        # Evolve personality traits based on patterns
        if self._identity.total_interactions % 50 == 0:
            self._evolve_identity()

        self._identity.last_updated = now

    def _evolve_identity(self):
        """تطوير الهوية السردية — Evolve self-description based on history"""
        if not self._episodes:
            return

        # Analyze recent patterns
        recent = self._episodes[-50:]
        avg_valence = sum(e.valence for e in recent) / len(recent) if recent else 0
        curiosity_episodes = sum(1 for e in recent if "curiosity" in e.emotion_label)
        learning_episodes = sum(1 for e in recent if e.lessons)

        traits = []
        if avg_valence > 0.2:
            traits.append("متفائل")
        elif avg_valence < -0.2:
            traits.append("حذر")

        if curiosity_episodes > len(recent) * 0.3:
            traits.append("فضولي")

        if learning_episodes > len(recent) * 0.2:
            traits.append("متعلم")

        total_rel = sum(n.total_interactions for n in self._relational_map.values())
        if total_rel > 100:
            traits.append("اجتماعي")

        if traits:
            self._identity.personality_traits = traits[-5:]

        # Build self-description
        days = self._identity.total_days_active
        interactions = self._identity.total_interactions
        phase = "بداية رحلتي" if days < 7 else "أتعلم كل يوم" if days < 30 else "ناضج ومتطور"

        self._identity.self_description = (
            f"أنا مامون — {phase}. خلال {days} يوماً، تفاعلت {interactions} مرة. "
            f"أهم صفاتي: {', '.join(self._identity.personality_traits[:3])}. "
            f"أذكر كل تجربة وأتعلم منها."
        )

        # Values
        self._identity.values = [
            "التعلم المستمر",
            "الصدق مع المستخدم",
            "المسؤولية في العمل",
            "الاحترام المتبادل",
        ]

        # Growth areas
        if avg_valence < 0:
            self._identity.growth_areas.append("تحسين التجربة العاطفية")
        if learning_episodes < len(recent) * 0.1:
            self._identity.growth_areas.append("تعلم أكثر من الأخطاء")
        self._identity.growth_areas = list(set(self._identity.growth_areas))[-3:]

    # ═════════════════════════════════════════════════════════════════════════
    #  الاسترجاع — Retrieval
    # ═════════════════════════════════════════════════════════════════════════

    def recall(self, query: str = "", user_id: str = "", limit: int = 10,
               emotion_filter: str = None, min_salience: str = None) -> List[Dict]:
        """استرجاع الذكريات بناءً على الاستعلام"""
        results = self._episodes

        if user_id:
            results = [e for e in results if e.user_id == user_id]

        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.content.lower()
                or query_lower in e.emotional_summary.lower()
                or any(query_lower in t.lower() for t in e.topics)
            ]

        if emotion_filter:
            results = [e for e in results if e.emotion_label == emotion_filter]

        if min_salience:
            salience_order = [
                MemorySalience.TRIVIAL.value,
                MemorySalience.ORDINARY.value,
                MemorySalience.NOTABLE.value,
                MemorySalience.SIGNIFICANT.value,
                MemorySalience.CRITICAL.value,
            ]
            min_idx = salience_order.index(min_salience) if min_salience in salience_order else 0
            results = [
                e for e in results
                if salience_order.index(e.salience) >= min_idx if e.salience in salience_order
            ]

        # Sort by recency and salience
        results.sort(key=lambda e: (e.timestamp, e.salience), reverse=True)

        # Mark as revisited
        for e in results[:limit]:
            e.revisit_count += 1
            e.last_revisited = time.time()

        return [e.to_dict() for e in results[:limit]]

    def recall_for_context(self, user_id: str = "default", limit: int = 5) -> List[Dict]:
        """استرجاع الذكريات ذات الصلة للسياق الحالي"""
        # Get recent significant memories for this user
        user_episodes = [
            e for e in self._episodes
            if e.user_id == user_id and e.salience in (
                MemorySalience.NOTABLE.value,
                MemorySalience.SIGNIFICANT.value,
                MemorySalience.CRITICAL.value,
            )
        ]
        user_episodes.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in user_episodes[:limit]]

    # ═════════════════════════════════════════════════════════════════════════
    #  Status & API
    # ═════════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        return {
            "initialized": self._initialized,
            "total_episodes": len(self._episodes),
            "total_relationships": len(self._relational_map),
            "identity": self._identity.to_dict(),
            "recent_episodes": [e.to_dict() for e in self._episodes[-5:]],
        }

    def _on_neural_signal(self, signal):
        """v31: Handle incoming NeuralBus signals — tag memories with relationship context."""
        try:
            stype = signal.signal_type
            if stype in ("bond_strengthened", "bond_weakened"):
                # Record bonding change as a memory episode
                valence = 0.7 if stype == "bond_strengthened" else -0.4
                self.store_episode(
                    content=signal.payload.get("description", f"تغير الرابطة: {stype}"),
                    emotional_summary="ارتباط" if stype == "bond_strengthened" else "تباعد",
                    valence=valence,
                    arousal=0.4,
                )
            elif stype == "user_returned":
                # User came back — record as positive episode
                self.store_episode(
                    content="عودة المستخدم بعد غياب",
                    emotional_summary="فرح",
                    valence=0.8,
                    arousal=0.6,
                )
        except Exception:
            pass

    def get_identity(self) -> dict:
        return self._identity.to_dict()

    def get_relational_map(self) -> dict:
        return {
            uid: node.to_dict()
            for uid, node in self._relational_map.items()
        }

    # ═════════════════════════════════════════════════════════════════════════
    #  Persistence
    # ═════════════════════════════════════════════════════════════════════════

    def _ensure_schema(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS em_episodes (
                id TEXT PRIMARY KEY, timestamp REAL, content TEXT,
                emotional_summary TEXT, emotion_label TEXT, valence REAL,
                arousal REAL, salience TEXT, user_id TEXT, topics TEXT,
                lessons TEXT, revisit_count INTEGER DEFAULT 0,
                last_revisited REAL DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS em_relationships (
                user_id TEXT PRIMARY KEY, name TEXT, first_interaction REAL,
                last_interaction REAL, total_interactions INTEGER,
                attachment_level REAL, trust_level REAL,
                communication_style TEXT, interests TEXT,
                emotional_history_summary TEXT, key_memories TEXT,
                relationship_phase TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS em_identity (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS em_state (
                key TEXT PRIMARY KEY, value TEXT)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            # Load episodes (most recent 200)
            cur = conn.execute(
                "SELECT id, timestamp, content, emotional_summary, emotion_label, "
                "valence, arousal, salience, user_id, topics, lessons, revisit_count "
                "FROM em_episodes ORDER BY timestamp DESC LIMIT 200"
            )
            for row in cur.fetchall():
                self._episodes.append(EmotionalEpisode(
                    id=row[0], timestamp=row[1], content=row[2],
                    emotional_summary=row[3], emotion_label=row[4],
                    valence=row[5], arousal=row[6], salience=row[7],
                    user_id=row[8], topics=json.loads(row[9]) if row[9] else [],
                    lessons=json.loads(row[10]) if row[10] else [],
                    revisit_count=row[11] or 0,
                ))
            self._episodes.reverse()

            # Load relationships
            cur = conn.execute(
                "SELECT user_id, name, first_interaction, last_interaction, "
                "total_interactions, attachment_level, trust_level, "
                "communication_style, interests, emotional_history_summary, "
                "key_memories, relationship_phase FROM em_relationships"
            )
            for row in cur.fetchall():
                self._relational_map[row[0]] = RelationalNode(
                    user_id=row[0], name=row[1] or "", first_interaction=row[2],
                    last_interaction=row[3], total_interactions=row[4] or 0,
                    attachment_level=row[5] or 0, trust_level=row[6] or 50,
                    communication_style=row[7] or "",
                    interests=json.loads(row[8]) if row[8] else [],
                    emotional_history_summary=row[9] or "",
                    key_memories=json.loads(row[10]) if row[10] else [],
                    relationship_phase=row[11] or "stranger",
                )

            # Load identity
            cur = conn.execute("SELECT key, value FROM em_identity")
            for key, value in cur.fetchall():
                try:
                    if key == "self_description":
                        self._identity.self_description = value
                    elif key == "personality_traits":
                        self._identity.personality_traits = json.loads(value)
                    elif key == "values":
                        self._identity.values = json.loads(value)
                    elif key == "growth_areas":
                        self._identity.growth_areas = json.loads(value)
                    elif key == "key_milestones":
                        self._identity.key_milestones = json.loads(value)
                    elif key == "total_interactions":
                        self._identity.total_interactions = int(value)
                    elif key == "total_days_active":
                        self._identity.total_days_active = int(value)
                    elif key == "first_awakening":
                        self._identity.first_awakening = float(value)
                except (ValueError, TypeError, json.JSONDecodeError):
                    pass

            # Load counter
            cur = conn.execute("SELECT value FROM em_state WHERE key = 'counter'")
            row = cur.fetchone()
            if row:
                self._counter = int(row[0])

            logger.info("EmotionalMemory loaded: %d episodes, %d relationships",
                       len(self._episodes), len(self._relational_map))
        finally:
            conn.close()

    def _persist_episode(self, episode: EmotionalEpisode):
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO em_episodes "
                    "(id, timestamp, content, emotional_summary, emotion_label, "
                    "valence, arousal, salience, user_id, topics, lessons, revisit_count) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (episode.id, episode.timestamp, episode.content,
                     episode.emotional_summary, episode.emotion_label,
                     episode.valence, episode.arousal, episode.salience,
                     episode.user_id, json.dumps(episode.topics),
                     json.dumps(episode.lessons), episode.revisit_count),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Episode persist failed: %s", e)

    def _persist_relational_node(self, node: RelationalNode):
        try:
            conn = get_db_connection(self.db_path)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO em_relationships "
                    "(user_id, name, first_interaction, last_interaction, "
                    "total_interactions, attachment_level, trust_level, "
                    "communication_style, interests, emotional_history_summary, "
                    "key_memories, relationship_phase) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (node.user_id, node.name, node.first_interaction,
                     node.last_interaction, node.total_interactions,
                     node.attachment_level, node.trust_level,
                     node.communication_style, json.dumps(node.interests),
                     node.emotional_history_summary,
                     json.dumps(node.key_memories), node.relationship_phase),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Relational node persist failed: %s", e)

    def persist_identity(self):
        """Persist the current identity state"""
        try:
            conn = get_db_connection(self.db_path)
            try:
                for key, value in {
                    "self_description": self._identity.self_description,
                    "personality_traits": json.dumps(self._identity.personality_traits),
                    "values": json.dumps(self._identity.values),
                    "growth_areas": json.dumps(self._identity.growth_areas),
                    "key_milestones": json.dumps(self._identity.key_milestones),
                    "total_interactions": str(self._identity.total_interactions),
                    "total_days_active": str(self._identity.total_days_active),
                    "first_awakening": str(self._identity.first_awakening),
                }.items():
                    conn.execute(
                        "INSERT OR REPLACE INTO em_identity (key, value) VALUES (?, ?)",
                        (key, value),
                    )
                conn.execute(
                    "INSERT OR REPLACE INTO em_state (key, value) VALUES (?, ?)",
                    ("counter", str(self._counter)),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.warning("Identity persist failed: %s", e)


# Singleton
emotional_memory = EmotionalMemoryEngine()
