"""
BABSHARQII v26.0 — Dynamic Working Memory Engine
محرك الذاكرة العاملة الديناميكية — بدون LLM

Real working memory with:
1. Capacity-limited buffer (Baddeley's model: 7±2 items)
2. Salience-based activation and decay
3. Interference management (proactive/retroactive)
4. Episodic buffer: integrate multimodal info
5. Central executive: attention allocation
6. Rehearsal loop: prevent decay of important items

Based on: Baddeley & Hitch (1974), Cowan (2001)
"""

import time, uuid, json, logging, numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.dynamic_working_memory")


@dataclass
class WMItem:
    """عنصر في الذاكرة العاملة"""
    item_id: str = ""
    content: str = ""
    item_type: str = "info"  # info, goal, context, perception, action
    source: str = ""
    salience: float = 0.5
    activation: float = 1.0
    decay_rate: float = 0.01
    rehearsal_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0

    def __post_init__(self):
        if not self.item_id:
            self.item_id = f"wm_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_accessed:
            self.last_accessed = time.time()

    def age(self) -> float:
        return time.time() - self.created_at

    def effective_salience(self) -> float:
        """الملحوظة الفعلية = salience × activation × (1 / (1 + decay))"""
        return self.salience * self.activation / (1 + self.decay_rate * self.age())


class DynamicWorkingMemory:
    """
    الذاكرة العاملة الديناميكية — محدودة السعة مع إدارة ذكية

    - Capacity: 7±2 items (Baddeley)
    - Salience decay over time
    - Rehearsal prevents decay
    - Interference resolution
    - Central executive allocates attention
    """

    def __init__(self, db_path=None, capacity: int = 7):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._capacity = capacity
        self._items: Dict[str, WMItem] = {}
        self._focus_item: Optional[str] = None
        self._episodic_buffer: List[Dict] = []
        self._rehearsal_loop: List[str] = []  # item_ids being rehearsed
        self._stats = {"added": 0, "evicted": 0, "rehearsed": 0, "retrieved": 0}

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("DynamicWorkingMemory initialized: capacity=%d, loaded=%d",
                        self._capacity, len(self._items))
            return True
        except Exception as e:
            logger.error("DWM init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS dwm_items (
                item_id TEXT PRIMARY KEY, content TEXT, item_type TEXT, source TEXT,
                salience REAL, activation REAL, decay_rate REAL,
                rehearsal_count INTEGER, created_at REAL, last_accessed REAL)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT item_id, content, item_type, source, salience, activation, decay_rate, rehearsal_count, created_at, last_accessed FROM dwm_items ORDER BY salience DESC LIMIT 20"):
                item = WMItem(item_id=row[0], content=row[1], item_type=row[2], source=row[3],
                    salience=row[4], activation=row[5], decay_rate=row[6],
                    rehearsal_count=row[7], created_at=row[8], last_accessed=row[9])
                if len(self._items) < self._capacity:
                    self._items[item.item_id] = item
        finally:
            conn.close()

    def _persist_item(self, item: WMItem):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO dwm_items VALUES (?,?,?,?,?,?,?,?,?,?)",
                (item.item_id, item.content, item.item_type, item.source,
                 item.salience, item.activation, item.decay_rate,
                 item.rehearsal_count, item.created_at, item.last_accessed))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def add(self, content: str, item_type: str = "info", source: str = "",
            salience: float = 0.5, decay_rate: float = 0.01) -> WMItem:
        """إضافة عنصر — مع إدارة السعة"""
        # Evict lowest-salience item if at capacity
        while len(self._items) >= self._capacity:
            self._evict_lowest()

        item = WMItem(content=content, item_type=item_type, source=source,
                      salience=salience, decay_rate=decay_rate)
        self._items[item.item_id] = item
        self._persist_item(item)
        self._stats["added"] += 1
        return item

    def get(self, item_id: str) -> Optional[WMItem]:
        """استرجاع عنصر — ينشّطه"""
        item = self._items.get(item_id)
        if item:
            item.activation = min(1.0, item.activation + 0.2)  # boost
            item.last_accessed = time.time()
            self._stats["retrieved"] += 1
            return item
        return None

    def focus(self, item_id: str) -> Optional[WMItem]:
        """التركيز على عنصر — يصبح محور الانتباه"""
        item = self.get(item_id)
        if item:
            self._focus_item = item_id
            item.salience = min(1.0, item.salience + 0.3)  # focused items are more salient
            item.rehearsal_count += 1
            self._stats["rehearsed"] += 1
        return item

    def get_focus(self) -> Optional[WMItem]:
        """العنصر المركزي الحالي"""
        if self._focus_item:
            return self._items.get(self._focus_item)
        return None

    def decay_all(self):
        """اضمحلال كل العناصر — محاكاة النسيان"""
        to_remove = []
        for item_id, item in self._items.items():
            # Items in rehearsal loop decay slower
            if item_id in self._rehearsal_loop:
                item.activation *= 0.99
            else:
                item.activation *= (1 - item.decay_rate)

            if item.activation < 0.05:
                to_remove.append(item_id)

        for item_id in to_remove:
            del self._items[item_id]

    def rehearse(self, item_id: str):
        """بروفنة — منع اضمحلال عنصر مهم"""
        if item_id in self._items:
            item = self._items[item_id]
            item.activation = 1.0
            item.rehearsal_count += 1
            if item_id not in self._rehearsal_loop:
                self._rehearsal_loop.append(item_id)
            self._stats["rehearsed"] += 1

    def add_to_episodic_buffer(self, content: Dict):
        """إضافة للذاكرة العرضية"""
        self._episodic_buffer.append({**content, "timestamp": time.time()})
        if len(self._episodic_buffer) > 20:
            self._episodic_buffer = self._episodic_buffer[-20:]

    def get_active_items(self, top_k: int = 5) -> List[WMItem]:
        """العناصر النشطة — مرتبة بالملحوظة الفعلية"""
        items = sorted(self._items.values(), key=lambda x: -x.effective_salience())
        return items[:top_k]

    def clear(self):
        """مسح الذاكرة العاملة"""
        self._items.clear()
        self._focus_item = None
        self._episodic_buffer.clear()
        self._rehearsal_loop.clear()

    def _evict_lowest(self):
        """طرد العنصر الأقل ملحوظة"""
        if not self._items:
            return
        lowest_id = min(self._items, key=lambda k: self._items[k].effective_salience())
        del self._items[lowest_id]
        self._stats["evicted"] += 1
        if self._focus_item == lowest_id:
            self._focus_item = None

    def get_stats(self) -> Dict:
        items = list(self._items.values())
        return {
            "capacity": self._capacity,
            "current_load": len(items),
            "load_pct": round(len(items) / self._capacity * 100, 1),
            "focus_item": self._focus_item,
            "avg_salience": round(np.mean([i.effective_salience() for i in items]), 3) if items else 0,
            "avg_activation": round(np.mean([i.activation for i in items]), 3) if items else 0,
            "episodic_buffer_size": len(self._episodic_buffer),
            "rehearsal_loop_size": len(self._rehearsal_loop),
            **self._stats,
        }


_dwm: Optional[DynamicWorkingMemory] = None

def get_dynamic_working_memory() -> DynamicWorkingMemory:
    global _dwm
    if _dwm is None:
        _dwm = DynamicWorkingMemory()
    return _dwm
