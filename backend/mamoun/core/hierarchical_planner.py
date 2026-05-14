"""
BABSHARQII v24.0 — Hierarchical Planning Engine
محرك التخطيط الهرمي — مأمون يخطط على 3 مستويات

Strategic (months/years) → الأهداف الكبرى
Tactical (weeks/days)   → المهام الفرعية
Operational (minutes)    → الخطوات التنفيذية الفورية

This is NOT text generation. This builds an actual plan tree with:
- Dependencies between tasks
- Resource estimation
- Progress tracking
- Adaptive replanning when things go wrong
"""
import os, time, uuid, json, logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.planner")


class PlanLevel(str, Enum):
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"


class PlanStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPRECATED = "deprecated"


@dataclass
class PlanNode:
    """عقدة خطة — هدف أو مهمة أو خطوة"""
    node_id: str = ""
    title: str = ""
    description: str = ""
    level: str = PlanLevel.OPERATIONAL.value
    status: str = PlanStatus.PROPOSED.value
    parent_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # must complete these first
    estimated_effort: float = 1.0  # hours
    actual_effort: float = 0.0
    progress: float = 0.0  # 0-1
    priority: float = 0.5  # 0-1
    deadline: float = 0.0
    created_at: float = 0.0
    completed_at: float = 0.0

    def __post_init__(self):
        if not self.node_id:
            self.node_id = f"plan_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)


class HierarchicalPlanner:
    """
    محرك التخطيط الهرمي
    
    Usage:
        planner = HierarchicalPlanner()
        planner.initialize()
        
        # Create a strategic goal
        goal = planner.create_plan("Build e-commerce store", level="strategic")
        
        # Break it down
        design = planner.add_subplan(goal.node_id, "Design the UI", level="tactical")
        backend = planner.add_subplan(goal.node_id, "Build the backend", level="tactical")
        
        # Add operational steps
        planner.add_subplan(design.node_id, "Create homepage mockup", level="operational")
        planner.add_subplan(design.node_id, "Design product page", level="operational")
        
        # Set dependency: backend needs design first
        planner.add_dependency(backend.node_id, design.node_id)
        
        # Get next actionable step
        next_step = planner.get_next_action()
        
        # Complete a step
        planner.update_progress(step_id, progress=1.0, status="completed")
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._plans: Dict[str, PlanNode] = {}
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("HierarchicalPlanner initialized — %d plans", len(self._plans))
            return True
        except Exception as e:
            logger.error("HierarchicalPlanner init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hp_plans (
                    node_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    level TEXT DEFAULT 'operational',
                    status TEXT DEFAULT 'proposed',
                    parent_id TEXT DEFAULT '',
                    children_ids TEXT DEFAULT '[]',
                    dependencies TEXT DEFAULT '[]',
                    estimated_effort REAL DEFAULT 1.0,
                    actual_effort REAL DEFAULT 0.0,
                    progress REAL DEFAULT 0.0,
                    priority REAL DEFAULT 0.5,
                    deadline REAL DEFAULT 0,
                    created_at REAL DEFAULT 0,
                    completed_at REAL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hp_parent ON hp_plans(parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hp_status ON hp_plans(status)")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM hp_plans"):
                p = PlanNode(
                    node_id=row[0], title=row[1], description=row[2],
                    level=row[3], status=row[4], parent_id=row[5],
                    children_ids=json.loads(row[6]),
                    dependencies=json.loads(row[7]),
                    estimated_effort=row[8], actual_effort=row[9],
                    progress=row[10], priority=row[11],
                    deadline=row[12], created_at=row[13], completed_at=row[14]
                )
                self._plans[p.node_id] = p
        finally:
            conn.close()

    def _persist_plan(self, p: PlanNode):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO hp_plans
                (node_id, title, description, level, status, parent_id, children_ids,
                 dependencies, estimated_effort, actual_effort, progress, priority,
                 deadline, created_at, completed_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (p.node_id, p.title, p.description, p.level, p.status,
                  p.parent_id, json.dumps(p.children_ids), json.dumps(p.dependencies),
                  p.estimated_effort, p.actual_effort, p.progress, p.priority,
                  p.deadline, p.created_at, p.completed_at))
            conn.commit()
        finally:
            conn.close()

    def create_plan(self, title: str, description: str = "",
                    level: str = PlanLevel.STRATEGIC.value,
                    priority: float = 0.5, deadline: float = 0) -> PlanNode:
        plan = PlanNode(
            title=title, description=description,
            level=level, priority=priority, deadline=deadline,
            status=PlanStatus.ACTIVE.value,
        )
        self._plans[plan.node_id] = plan
        self._persist_plan(plan)
        return plan

    def add_subplan(self, parent_id: str, title: str, description: str = "",
                    level: str = PlanLevel.OPERATIONAL.value,
                    priority: float = 0.5) -> Optional[PlanNode]:
        parent = self._plans.get(parent_id)
        if not parent:
            return None

        subplan = PlanNode(
            title=title, description=description,
            level=level, parent_id=parent_id, priority=priority,
            status=PlanStatus.ACTIVE.value,
        )
        self._plans[subplan.node_id] = subplan
        parent.children_ids.append(subplan.node_id)
        self._persist_plan(subplan)
        self._persist_plan(parent)
        return subplan

    def add_dependency(self, node_id: str, depends_on_id: str) -> bool:
        node = self._plans.get(node_id)
        dep = self._plans.get(depends_on_id)
        if not node or not dep:
            return False
        if depends_on_id not in node.dependencies:
            node.dependencies.append(depends_on_id)
            self._persist_plan(node)
        return True

    def update_progress(self, node_id: str, progress: float = None,
                        status: str = None, actual_effort: float = None) -> Optional[PlanNode]:
        node = self._plans.get(node_id)
        if not node:
            return None

        if progress is not None:
            node.progress = min(1.0, max(0.0, progress))
        if status:
            node.status = status
            if status == PlanStatus.COMPLETED.value:
                node.progress = 1.0
                node.completed_at = time.time()
        if actual_effort is not None:
            node.actual_effort = actual_effort

        self._persist_plan(node)

        # Propagate progress to parent
        if node.parent_id:
            parent = self._plans.get(node.parent_id)
            if parent and parent.children_ids:
                children = [self._plans.get(cid) for cid in parent.children_ids]
                children = [c for c in children if c]
                if children:
                    parent.progress = sum(c.progress for c in children) / len(children)
                    if all(c.status == PlanStatus.COMPLETED.value for c in children):
                        parent.status = PlanStatus.COMPLETED.value
                        parent.completed_at = time.time()
                    self._persist_plan(parent)

        return node

    def get_next_action(self) -> Optional[Dict]:
        """الحصول على الخطوة التالية القابلة للتنفيذ"""
        candidates = []
        for p in self._plans.values():
            if p.status not in (PlanStatus.ACTIVE.value, PlanStatus.IN_PROGRESS.value):
                continue
            if p.level != PlanLevel.OPERATIONAL.value:
                continue
            if p.progress >= 1.0:
                continue
            # Check dependencies
            deps_met = all(
                self._plans.get(d, PlanNode()).status == PlanStatus.COMPLETED.value
                for d in p.dependencies
                if d in self._plans
            )
            if not deps_met:
                continue
            candidates.append(p)

        if not candidates:
            return None

        # Sort by priority (desc) then deadline (asc)
        candidates.sort(key=lambda p: (-p.priority, p.deadline or float('inf')))
        best = candidates[0]
        return best.to_dict()

    def get_plan_tree(self, root_id: str = None) -> Dict:
        """الحصول على شجرة الخطة"""
        if root_id:
            roots = [self._plans.get(root_id)]
        else:
            roots = [p for p in self._plans.values() if not p.parent_id]

        def build_tree(node):
            if not node:
                return None
            children = [build_tree(self._plans.get(cid)) for cid in node.children_ids]
            return {
                **node.to_dict(),
                "children": [c for c in children if c],
            }

        trees = [build_tree(r) for r in roots]
        return {"plans": [t for t in trees if t]}

    def get_stats(self) -> Dict:
        plans = list(self._plans.values())
        return {
            "total_plans": len(plans),
            "by_level": {l.value: len([p for p in plans if p.level == l.value]) for l in PlanLevel},
            "by_status": {s.value: len([p for p in plans if p.status == s.value]) for s in PlanStatus},
            "avg_progress": round(sum(p.progress for p in plans) / max(len(plans), 1), 3),
        }


hierarchical_planner = HierarchicalPlanner()
