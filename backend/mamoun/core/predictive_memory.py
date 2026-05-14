"""
BABSHARQII v19.0 — Predictive Memory Engine
الذاكرة التنبؤية — Markov Chain + time-weighted recency + pattern extraction

Predicts what the user will ask/need next based on:
1. Markov Chain: transition probabilities between topics/actions
2. Time-weighted recency: recent patterns matter more
3. Pattern extraction: detect recurring sequences

Example output:
  "بناءً على آخر 5 أسئلة، أنت تخطط لفتح شركة ديكور"
  "بناءً على أنماطك، ستسأل عن التسعير بعد 3 رسائل"
"""

import time
import json
import math
import logging
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

from mamoun.config import DB_PATH

logger = logging.getLogger("mamoun.core.predictive_memory")


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class TopicTransition:
    """انتقال بين موضوعين — عقدة في سلسلة ماركوف"""
    from_topic: str = ""
    to_topic: str = ""
    count: int = 0
    last_seen: float = 0.0
    confidence: float = 0.0  # computed probability

    def to_dict(self) -> dict:
        return {
            "from": self.from_topic,
            "to": self.to_topic,
            "count": self.count,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class Prediction:
    """تنبؤ — ما يتوقعه مأمون أن يفعله المستخدم بعد ذلك"""
    id: str = ""
    predicted_topic: str = ""
    predicted_action: str = ""
    confidence: float = 0.0
    reasoning: str = ""  # شرح بالعربي لماذا هذا التنبؤ
    evidence: List[str] = field(default_factory=list)  # الأدلة
    created_at: float = field(default_factory=time.time)
    verified: Optional[bool] = None  # None=pending, True=correct, False=wrong

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "predicted_topic": self.predicted_topic,
            "predicted_action": self.predicted_action,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "evidence": self.evidence[:5],
            "verified": self.verified,
            "created_at": self.created_at,
        }


@dataclass
class PatternSequence:
    """نمط متكرر — تسلسل يحدث أكثر من مرة"""
    sequence: List[str] = field(default_factory=list)
    frequency: int = 0
    last_seen: float = 0.0
    next_predicted: str = ""

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "frequency": self.frequency,
            "next_predicted": self.next_predicted,
        }


# =============================================================================
# Predictive Memory Engine
# =============================================================================

class PredictiveMemoryEngine:
    """
    محرك الذاكرة التنبؤية — يتنبأ بالإجراء/الموضوع التالي

    Architecture:
      - Markov Chain: P(topic_B | topic_A) = count(A→B) / count(A→*)
      - Time-weighted recency: recent transitions get exponential boost
      - Pattern extraction: find recurring sequences of length 2-5
      - Prediction verification: track if predictions were correct

    Storage: SQLite for persistence (same as other memory systems)
    """

    # Markov Chain order (how many previous topics to consider)
    MARKOV_ORDER = 2
    # Minimum transitions before making predictions
    MIN_TRANSITIONS = 3
    # Time decay half-life in seconds (10 minutes)
    RECENCY_HALFLIFE = 600
    # Minimum confidence to surface a prediction
    MIN_PREDICTION_CONFIDENCE = 0.3
    # Maximum predictions to keep active
    MAX_ACTIVE_PREDICTIONS = 10

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH.parent / "predictive_memory.db"
        self._transition_cache: Dict[str, List[TopicTransition]] = defaultdict(list)
        self._topic_counts: Dict[str, int] = defaultdict(int)
        self._recent_topics: List[str] = []  # last N topics
        self._active_predictions: List[Prediction] = []
        self._patterns: List[PatternSequence] = []
        self._prediction_counter = 0
        self._accuracy_history: List[Dict] = []
        self._overall_accuracy = 0.0
        self._initialized = False

    def initialize(self) -> bool:
        """تهيئة المحرك — إنشاء الجداول وتحميل البيانات"""
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("PredictiveMemoryEngine initialized — %d transitions, %d patterns loaded",
                       sum(len(v) for v in self._transition_cache.values()), len(self._patterns))
            return True
        except Exception as e:
            logger.error("PredictiveMemoryEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        """إنشاء جداول SQLite"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_transitions (
                    from_topic TEXT NOT NULL,
                    to_topic TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    last_seen REAL DEFAULT 0,
                    PRIMARY KEY (from_topic, to_topic)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_predictions (
                    id TEXT PRIMARY KEY,
                    predicted_topic TEXT NOT NULL,
                    predicted_action TEXT DEFAULT '',
                    confidence REAL DEFAULT 0,
                    reasoning TEXT DEFAULT '',
                    evidence TEXT DEFAULT '[]',
                    created_at REAL DEFAULT 0,
                    verified TEXT DEFAULT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_patterns (
                    sequence TEXT PRIMARY KEY,
                    frequency INTEGER DEFAULT 1,
                    last_seen REAL DEFAULT 0,
                    next_predicted TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_accuracy (
                    timestamp REAL PRIMARY KEY,
                    correct INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 1
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        """تحميل البيانات من SQLite إلى الذاكرة"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Load transitions
            cur = conn.execute("SELECT from_topic, to_topic, count, last_seen FROM pm_transitions")
            for row in cur.fetchall():
                t = TopicTransition(
                    from_topic=row[0], to_topic=row[1],
                    count=row[2], last_seen=row[3]
                )
                self._transition_cache[row[0]].append(t)
                self._topic_counts[row[0]] += row[2]

            # Load active predictions
            cur = conn.execute(
                "SELECT id, predicted_topic, predicted_action, confidence, reasoning, evidence, created_at, verified FROM pm_predictions WHERE verified IS NULL ORDER BY created_at DESC LIMIT 10"
            )
            for row in cur.fetchall():
                p = Prediction(
                    id=row[0], predicted_topic=row[1], predicted_action=row[2],
                    confidence=row[3], reasoning=row[4],
                    evidence=json.loads(row[5]) if row[5] else [],
                    created_at=row[6],
                    verified=None if row[7] in (None, "None", "") else (row[7] == "True")
                )
                self._active_predictions.append(p)
                try:
                    num = int(row[0].split("_")[-1])
                    self._prediction_counter = max(self._prediction_counter, num)
                except (ValueError, IndexError):
                    pass

            # Load patterns
            cur = conn.execute("SELECT sequence, frequency, last_seen, next_predicted FROM pm_patterns")
            for row in cur.fetchall():
                seq = json.loads(row[0])
                self._patterns.append(PatternSequence(
                    sequence=seq, frequency=row[1],
                    last_seen=row[2], next_predicted=row[3]
                ))

            # Load accuracy
            cur = conn.execute("SELECT timestamp, correct, total FROM pm_accuracy ORDER BY timestamp DESC LIMIT 100")
            for row in cur.fetchall():
                self._accuracy_history.append({
                    "timestamp": row[0], "correct": bool(row[1]), "total": row[2]
                })
            self._compute_overall_accuracy()
        finally:
            conn.close()

    # ─── Core: Record Interaction ──────────────────────────────────────────

    def record_interaction(self, topic: str, action: str = "", metadata: dict = None):
        """
        تسجيل تفاعل جديد — يُحدّث سلسلة ماركوف ويستخرج الأنماط

        Args:
            topic: الموضوع (مثلاً "ديكور"، "برمجة"، "تسعير")
            action: الإجراء (مثلاً "سؤال"، "طلب بناء"، "بحث")
            metadata: بيانات إضافية
        """
        if not self._initialized:
            self.initialize()

        now = time.time()
        topic = topic.strip().lower()
        if not topic:
            return

        # 1. Update Markov Chain transitions
        if self._recent_topics:
            # Record transition from each of last MARKOV_ORDER topics
            for i, prev_topic in enumerate(self._recent_topics[-self.MARKOV_ORDER:]):
                weight = 1.0 + (i * 0.2)  # more recent = higher weight
                self._record_transition(prev_topic, topic, now, weight)

        # 2. Update recent topics list
        self._recent_topics.append(topic)
        if len(self._recent_topics) > 50:
            self._recent_topics = self._recent_topics[-50:]

        # 3. Extract patterns from recent sequence
        self._extract_patterns(self._recent_topics, now)

        # 4. Verify any pending predictions
        self._verify_predictions(topic)

        # 5. Persist to DB
        self._persist_interaction(topic, action, now)

        logger.debug("PredictiveMemory: recorded [%s→%s], recent=%s", 
                     self._recent_topics[-2] if len(self._recent_topics) > 1 else "START",
                     topic, len(self._recent_topics))

    def _record_transition(self, from_topic: str, to_topic: str, timestamp: float, weight: float = 1.0):
        """تسجيل انتقال في سلسلة ماركوف"""
        # Find existing transition
        for t in self._transition_cache[from_topic]:
            if t.to_topic == to_topic:
                t.count += weight
                t.last_seen = timestamp
                self._topic_counts[from_topic] += weight
                return

        # New transition
        t = TopicTransition(
            from_topic=from_topic, to_topic=to_topic,
            count=weight, last_seen=timestamp
        )
        self._transition_cache[from_topic].append(t)
        self._topic_counts[from_topic] += weight

    # ─── Core: Make Predictions ────────────────────────────────────────────

    def predict(self, n: int = 3) -> List[Prediction]:
        """
        التنبؤ بالموضوعات/الإجراءات التالية

        Uses:
        1. Markov Chain probabilities (time-weighted)
        2. Pattern matching (recurring sequences)
        3. Recency boost

        Returns top-N predictions sorted by confidence.
        """
        if not self._initialized:
            self.initialize()

        if not self._recent_topics:
            return []

        predictions: List[Prediction] = []

        # Strategy 1: Markov Chain prediction
        markov_preds = self._markov_predict()
        predictions.extend(markov_preds)

        # Strategy 2: Pattern-based prediction
        pattern_preds = self._pattern_predict()
        predictions.extend(pattern_preds)

        # Deduplicate and merge
        merged = self._merge_predictions(predictions)

        # Sort by confidence and return top-N
        merged.sort(key=lambda p: p.confidence, reverse=True)
        result = merged[:n]

        # Store as active predictions
        for pred in result:
            self._prediction_counter += 1
            pred.id = f"pred_{self._prediction_counter}"
            self._active_predictions.append(pred)
            self._persist_prediction(pred)

        # Prune old predictions
        self._active_predictions = [p for p in self._active_predictions if p.verified is None]
        if len(self._active_predictions) > self.MAX_ACTIVE_PREDICTIONS:
            self._active_predictions = self._active_predictions[-self.MAX_ACTIVE_PREDICTIONS:]

        return result

    def _markov_predict(self) -> List[Prediction]:
        """تنبؤ بناءً على سلسلة ماركوف"""
        predictions = []
        now = time.time()

        # Predict from last topic
        last_topic = self._recent_topics[-1] if self._recent_topics else ""
        if not last_topic:
            return []

        transitions = self._transition_cache.get(last_topic, [])
        if not transitions:
            return []

        # Compute time-weighted probabilities
        total_weight = 0.0
        weighted_transitions = []

        for t in transitions:
            # Time decay: recent transitions matter more
            age = now - t.last_seen
            recency_factor = 0.5 ** (age / self.RECENCY_HALFLIFE)
            weight = t.count * recency_factor
            weighted_transitions.append((t, weight))
            total_weight += weight

        if total_weight == 0:
            return []

        # Generate predictions for top transitions
        for t, weight in sorted(weighted_transitions, key=lambda x: x[1], reverse=True)[:5]:
            probability = weight / total_weight

            if probability < self.MIN_PREDICTION_CONFIDENCE:
                continue

            # Generate Arabic reasoning
            reasoning = self._generate_reasoning(last_topic, t.to_topic, probability)

            pred = Prediction(
                predicted_topic=t.to_topic,
                predicted_action="سؤال أو طلب",
                confidence=probability,
                reasoning=reasoning,
                evidence=[f"transition: {last_topic} → {t.to_topic} (count={int(t.count)})"],
            )
            predictions.append(pred)

        return predictions

    def _pattern_predict(self) -> List[Prediction]:
        """تنبؤ بناءً على الأنماط المتكررة"""
        predictions = []

        if len(self._recent_topics) < 2:
            return []

        # Check if recent sequence matches any known pattern
        for pattern in self._patterns:
            if not pattern.next_predicted:
                continue

            seq_len = len(pattern.sequence)
            if seq_len > len(self._recent_topics):
                continue

            # Compare recent topics with pattern
            recent_slice = self._recent_topics[-seq_len:]
            if recent_slice == pattern.sequence:
                # Match found! Predict the next step
                confidence = min(0.9, pattern.frequency * 0.15)
                reasoning = (
                    f"النمط {pattern.sequence} → {pattern.next_predicted} "
                    f"تكرر {pattern.frequency} مرات"
                )
                pred = Prediction(
                    predicted_topic=pattern.next_predicted,
                    predicted_action="اتباع نمط",
                    confidence=confidence,
                    reasoning=reasoning,
                    evidence=[f"pattern: {' → '.join(pattern.sequence)} → {pattern.next_predicted}"],
                )
                predictions.append(pred)

        return predictions

    def _merge_predictions(self, predictions: List[Prediction]) -> List[Prediction]:
        """دمج التنبؤات المتشابهة"""
        merged: Dict[str, Prediction] = {}

        for pred in predictions:
            key = pred.predicted_topic
            if key in merged:
                # Merge: take higher confidence and combine evidence
                existing = merged[key]
                existing.confidence = max(existing.confidence, pred.confidence)
                existing.evidence.extend(pred.evidence)
                if len(existing.reasoning) < len(pred.reasoning):
                    existing.reasoning = pred.reasoning
            else:
                merged[key] = Prediction(
                    predicted_topic=pred.predicted_topic,
                    predicted_action=pred.predicted_action,
                    confidence=pred.confidence,
                    reasoning=pred.reasoning,
                    evidence=pred.evidence[:],
                )

        return list(merged.values())

    def _generate_reasoning(self, from_topic: str, to_topic: str, confidence: float) -> str:
        """توليد شرح عربي للتنبؤ"""
        if confidence > 0.7:
            return f"بناءً على أنماطك، ستنتقل غالباً من '{from_topic}' إلى '{to_topic}'"
        elif confidence > 0.5:
            return f"يبدو أنك بعد '{from_topic}' تسأل عادة عن '{to_topic}'"
        else:
            return f"قد تسأل عن '{to_topic}' بعد '{from_topic}'"

    # ─── Pattern Extraction ────────────────────────────────────────────────

    def _extract_patterns(self, recent: List[str], now: float):
        """استخراج الأنماط المتكررة من التسلسل الأخير"""
        if len(recent) < 3:
            return

        # Extract sequences of length 2-5
        for length in range(2, min(6, len(recent))):
            for start in range(len(recent) - length):
                seq = recent[start:start + length]
                seq_key = json.dumps(seq, ensure_ascii=False)

                # Check if this pattern already exists
                found = False
                for pattern in self._patterns:
                    if pattern.sequence == seq:
                        pattern.frequency += 1
                        pattern.last_seen = now
                        # Update next_predicted if there's a next element
                        if start + length < len(recent):
                            pattern.next_predicted = recent[start + length]
                        found = True
                        break

                if not found and start + length < len(recent):
                    self._patterns.append(PatternSequence(
                        sequence=seq,
                        frequency=1,
                        last_seen=now,
                        next_predicted=recent[start + length]
                    ))

        # Prune low-frequency patterns (keep top 100)
        self._patterns.sort(key=lambda p: p.frequency, reverse=True)
        if len(self._patterns) > 100:
            self._patterns = self._patterns[:100]

    # ─── Prediction Verification ───────────────────────────────────────────

    def _verify_predictions(self, actual_topic: str):
        """تحقق من التنبؤات النشطة — هل تطابق الموضوع الفعلي؟"""
        for pred in self._active_predictions:
            if pred.verified is not None:
                continue

            # Check if the actual topic matches the prediction
            if actual_topic == pred.predicted_topic:
                pred.verified = True
                self._record_accuracy(True)
                logger.info("Prediction CORRECT: [%s] — %s", pred.id, pred.predicted_topic)
            elif pred.created_at < time.time() - 3600:  # 1 hour timeout
                pred.verified = False
                self._record_accuracy(False)
                logger.info("Prediction WRONG: [%s] — predicted %s, got %s", 
                           pred.id, pred.predicted_topic, actual_topic)

    def _record_accuracy(self, correct: bool):
        """تسجيل دقة التنبؤ"""
        now = time.time()
        record = {"timestamp": now, "correct": correct, "total": 1}
        self._accuracy_history.append(record)

        # Keep only last 100 records
        if len(self._accuracy_history) > 100:
            self._accuracy_history = self._accuracy_history[-100:]

        self._compute_overall_accuracy()

        # Persist
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO pm_accuracy (timestamp, correct, total) VALUES (?, ?, 1)",
                (now, 1 if correct else 0)
            )
            conn.commit()
        finally:
            conn.close()

    def _compute_overall_accuracy(self):
        """حساب الدقة الكلية"""
        if not self._accuracy_history:
            self._overall_accuracy = 0.0
            return

        correct = sum(1 for r in self._accuracy_history if r["correct"])
        total = len(self._accuracy_history)
        self._overall_accuracy = correct / total if total > 0 else 0.0

    # ─── Persistence ───────────────────────────────────────────────────────

    def _persist_interaction(self, topic: str, action: str, timestamp: float):
        """حفظ التفاعل في SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            # Update transitions
            if len(self._recent_topics) >= 2:
                prev = self._recent_topics[-2]
                conn.execute(
                    "INSERT INTO pm_transitions (from_topic, to_topic, count, last_seen) VALUES (?, ?, 1, ?) ON CONFLICT(from_topic, to_topic) DO UPDATE SET count=count+1, last_seen=?",
                    (prev, topic, timestamp, timestamp)
                )

            # Update patterns
            for pattern in self._patterns[:50]:  # persist top 50
                seq_key = json.dumps(pattern.sequence, ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO pm_patterns (sequence, frequency, last_seen, next_predicted) VALUES (?, ?, ?, ?)",
                    (seq_key, pattern.frequency, pattern.last_seen, pattern.next_predicted)
                )

            conn.commit()
        finally:
            conn.close()

    def _persist_prediction(self, pred: Prediction):
        """حفظ التنبؤ في SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO pm_predictions (id, predicted_topic, predicted_action, confidence, reasoning, evidence, created_at, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pred.id, pred.predicted_topic, pred.predicted_action,
                 pred.confidence, pred.reasoning,
                 json.dumps(pred.evidence, ensure_ascii=False),
                 pred.created_at,
                 str(pred.verified) if pred.verified is not None else None)
            )
            conn.commit()
        finally:
            conn.close()

    # ─── Status & API ──────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """حالة محرك الذاكرة التنبؤية"""
        return {
            "initialized": self._initialized,
            "total_transitions": sum(len(v) for v in self._transition_cache.values()),
            "total_topics": len(self._topic_counts),
            "total_patterns": len(self._patterns),
            "active_predictions": len([p for p in self._active_predictions if p.verified is None]),
            "overall_accuracy": round(self._overall_accuracy, 4),
            "accuracy_samples": len(self._accuracy_history),
            "recent_topics": self._recent_topics[-5:],
        }

    def get_predictions(self) -> List[dict]:
        """الحصول على التنبؤات النشطة"""
        return [p.to_dict() for p in self._active_predictions if p.verified is None]

    def get_all_predictions(self, limit: int = 50) -> List[dict]:
        """الحصول على جميع التنبؤات (نشطة + محققة)"""
        all_preds = self._active_predictions[:]
        all_preds.sort(key=lambda p: p.created_at, reverse=True)
        return [p.to_dict() for p in all_preds[:limit]]

    def get_patterns(self, limit: int = 20) -> List[dict]:
        """الحصول على الأنماط المكتشفة"""
        sorted_patterns = sorted(self._patterns, key=lambda p: p.frequency, reverse=True)
        return [p.to_dict() for p in sorted_patterns[:limit]]

    def get_transitions(self, topic: str = "", limit: int = 20) -> List[dict]:
        """الحصول على انتقالات سلسلة ماركوف"""
        now = time.time()
        all_transitions = []

        topics = [topic] if topic else list(self._transition_cache.keys())
        for t in topics:
            for trans in self._transition_cache.get(t, []):
                # Recompute confidence with current time
                total = self._topic_counts.get(t, 1)
                age = now - trans.last_seen
                recency = 0.5 ** (age / self.RECENCY_HALFLIFE)
                trans.confidence = (trans.count / total) * recency
                all_transitions.append(trans)

        all_transitions.sort(key=lambda t: t.confidence, reverse=True)
        return [t.to_dict() for t in all_transitions[:limit]]

    def get_accuracy_trend(self, limit: int = 20) -> List[dict]:
        """الحصول على اتجاه الدقة عبر الزمن"""
        return self._accuracy_history[-limit:]


# =============================================================================
# Singleton
# =============================================================================

predictive_memory = PredictiveMemoryEngine()
