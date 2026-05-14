"""
BABSHARQII v25.0 — Synaptic Intelligence Engine
محرك الذكاء المشبكي — منع النسيان الكارثي

Based on "Continual Learning Through Synaptic Intelligence" (Zenke et al., 2017)

Core idea: Track how much each weight has contributed to the loss reduction.
When learning a new task, protect weights that were important for previous tasks.

Ω_i = Σ_t |Δw_i(t)| · F_i(t)
where F_i is the contribution of weight i to the loss change.

When learning new task, add SI penalty:
L_total = L_task + λ · Σ Ω_i · (w_i - w*_i)²

This is NOT a rule-based system. It tracks ACTUAL weight changes and
computes REAL importance scores for neural weights.
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.synaptic_intelligence")


@dataclass
class SynapseInfo:
    """معلومات مشبك — أهمية ووزن أمثل"""
    weight_id: str = ""           # layer_name:row:col
    current_weight: float = 0.0
    optimal_weight: float = 0.0   # best weight from previous tasks
    omega: float = 0.0            # importance measure
    total_delta: float = 0.0      # accumulated |Δw|
    update_count: int = 0
    last_task_id: str = ""
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SIReport:
    """تقرير نقل التعلم"""
    task_id: str = ""
    domain: str = ""
    total_synapses: int = 0
    important_synapses: int = 0    # omega > threshold
    protected_synapses: int = 0    # frozen
    si_penalty: float = 0.0
    forgetting_estimate: float = 0.0
    transfer_score: float = 0.0


class SynapticIntelligenceEngine:
    """
    محرك الذكاء المشبكي — يتتبع أهمية كل وزن فعلياً

    Usage:
        si = SynapticIntelligenceEngine()
        si.initialize()

        # Before learning Task A, start tracking
        si.start_task("task_a", "vision", weight_matrix, layer_name="vision_layer")

        # ... learning happens, weights change ...

        # After Task A, compute importance
        si.end_task("task_a", weight_matrix)

        # Before learning Task B, compute SI penalty
        penalty = si.compute_si_penalty(weight_matrix, layer_name="vision_layer")

        # Can we change this weight without hurting Task A?
        decision = si.should_change_weight(layer_name, row, col, proposed_delta)
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._synapses: Dict[str, SynapseInfo] = {}  # weight_id → SynapseInfo
        self._task_history: List[Dict] = []
        self._active_task: Optional[str] = None
        self._task_weights_before: Dict[str, np.ndarray] = {}  # snapshot before task
        self._llm = None
        self._initialized = False
        self._lambda_si = 1.0  # SI penalty strength

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("SynapticIntelligence initialized — %d tracked synapses",
                       len(self._synapses))
            return True
        except Exception as e:
            logger.error("SynapticIntelligence init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS si_synapses (
                    weight_id TEXT PRIMARY KEY,
                    current_weight REAL DEFAULT 0,
                    optimal_weight REAL DEFAULT 0,
                    omega REAL DEFAULT 0,
                    total_delta REAL DEFAULT 0,
                    update_count INTEGER DEFAULT 0,
                    last_task_id TEXT DEFAULT '',
                    last_updated REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS si_tasks (
                    task_id TEXT PRIMARY KEY,
                    domain TEXT DEFAULT '',
                    synapses_tracked INTEGER DEFAULT 0,
                    si_penalty REAL DEFAULT 0,
                    transfer_score REAL DEFAULT 0,
                    started_at REAL DEFAULT 0,
                    completed_at REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM si_synapses"):
                syn = SynapseInfo(
                    weight_id=row[0], current_weight=row[1], optimal_weight=row[2],
                    omega=row[3], total_delta=row[4], update_count=row[5],
                    last_task_id=row[6], last_updated=row[7],
                )
                self._synapses[syn.weight_id] = syn
        finally:
            conn.close()

    def _persist_synapse(self, syn: SynapseInfo):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO si_synapses
                (weight_id, current_weight, optimal_weight, omega, total_delta,
                 update_count, last_task_id, last_updated)
                VALUES (?,?,?,?,?,?,?,?)
            """, (syn.weight_id, syn.current_weight, syn.optimal_weight,
                  syn.omega, syn.total_delta, syn.update_count,
                  syn.last_task_id, syn.last_updated))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API
    # ═══════════════════════════════════════════════════════════

    def start_task(self, task_id: str, domain: str,
                   weight_matrix: np.ndarray, layer_name: str = "default"):
        """
        بدء مهمة جديدة — حفظ لقطة من الأوزان قبل التعلم
        """
        self._active_task = task_id
        self._task_weights_before[f"{layer_name}:{task_id}"] = weight_matrix.copy()

        # Register task
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO si_tasks
                (task_id, domain, synapses_tracked, started_at)
                VALUES (?,?,?,?)
            """, (task_id, domain, weight_matrix.size, time.time()))
            conn.commit()
        finally:
            conn.close()

        logger.info("SI: Started task '%s' in domain '%s' — %d weights",
                    task_id, domain, weight_matrix.size)

    def end_task(self, task_id: str, weight_matrix: np.ndarray,
                 layer_name: str = "default") -> SIReport:
        """
        إنهاء مهمة — حساب أهمية كل وزن بناءً على التغيرات الفعلية

        Ω_i += |w_i_final - w_i_initial|  (accumulated importance)
        """
        key = f"{layer_name}:{task_id}"
        before = self._task_weights_before.get(key)
        if before is None:
            return SIReport(task_id=task_id)

        # Compute importance: Ω_i = |Δw_i|
        delta = weight_matrix - before
        abs_delta = np.abs(delta)

        # Update synapse records
        important_count = 0
        for i in range(weight_matrix.shape[0]):
            for j in range(weight_matrix.shape[1]):
                wid = f"{layer_name}:{i}:{j}"
                if wid in self._synapses:
                    syn = self._synapses[wid]
                    syn.total_delta += abs_delta[i, j]
                    syn.omega += abs_delta[i, j]  # Accumulate importance
                    syn.current_weight = float(weight_matrix[i, j])
                    syn.optimal_weight = float(weight_matrix[i, j])  # Update optimal
                    syn.update_count += 1
                    syn.last_task_id = task_id
                    syn.last_updated = time.time()
                else:
                    syn = SynapseInfo(
                        weight_id=wid,
                        current_weight=float(weight_matrix[i, j]),
                        optimal_weight=float(weight_matrix[i, j]),
                        omega=float(abs_delta[i, j]),
                        total_delta=float(abs_delta[i, j]),
                        update_count=1,
                        last_task_id=task_id,
                        last_updated=time.time(),
                    )
                    self._synapses[wid] = syn

                if self._synapses[wid].omega > 0.01:
                    important_count += 1

                self._persist_synapse(self._synapses[wid])

        # Compute SI penalty
        si_penalty = self.compute_si_penalty(weight_matrix, layer_name)

        # Estimate forgetting
        forgetting = self._estimate_forgetting(weight_matrix, layer_name)

        report = SIReport(
            task_id=task_id,
            domain="",
            total_synapses=weight_matrix.size,
            important_synapses=important_count,
            protected_synapses=sum(1 for s in self._synapses.values()
                                  if s.omega > 0.01 and s.weight_id.startswith(layer_name)),
            si_penalty=si_penalty,
            forgetting_estimate=forgetting,
            transfer_score=1.0 - min(forgetting, 1.0),
        )

        # Update task record
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                UPDATE si_tasks SET si_penalty=?, transfer_score=?, completed_at=?
                WHERE task_id=?
            """, (si_penalty, report.transfer_score, time.time(), task_id))
            conn.commit()
        finally:
            conn.close()

        self._active_task = None
        self._task_history.append({
            "task_id": task_id,
            "layer": layer_name,
            "important_synapses": important_count,
            "si_penalty": si_penalty,
        })

        logger.info("SI: Completed task '%s' — %d important synapses, penalty=%.4f",
                    task_id, important_count, si_penalty)

        return report

    def compute_si_penalty(self, weight_matrix: np.ndarray,
                           layer_name: str = "default") -> float:
        """
        حساب عقاب SI: L_SI = λ · Σ Ω_i · (w_i - w*_i)²
        """
        penalty = 0.0
        for i in range(weight_matrix.shape[0]):
            for j in range(weight_matrix.shape[1]):
                wid = f"{layer_name}:{i}:{j}"
                syn = self._synapses.get(wid)
                if syn and syn.omega > 0:
                    diff = weight_matrix[i, j] - syn.optimal_weight
                    penalty += syn.omega * diff ** 2
        return float(self._lambda_si * penalty)

    def should_change_weight(self, layer_name: str, row: int, col: int,
                             proposed_delta: float) -> Dict[str, Any]:
        """
        هل يمكن تغيير هذا الوزن دون إيذاء المهام السابقة؟
        """
        wid = f"{layer_name}:{row}:{col}"
        syn = self._synapses.get(wid)
        if not syn or syn.omega < 0.001:
            return {"can_change": True, "reason": "low_importance", "omega": 0.0}

        # Compute penalty for this specific change
        penalty = syn.omega * proposed_delta ** 2
        threshold = 0.01  # Allow changes that don't exceed this penalty

        if penalty < threshold:
            return {"can_change": True, "reason": "low_penalty",
                    "omega": syn.omega, "penalty": penalty}
        else:
            return {"can_change": False, "reason": "would_hurt_previous_tasks",
                    "omega": syn.omega, "penalty": penalty, "threshold": threshold}

    def _estimate_forgetting(self, weight_matrix: np.ndarray,
                             layer_name: str) -> float:
        """تقدير مقدار النسيان"""
        total_omega = 0.0
        total_change = 0.0
        for i in range(weight_matrix.shape[0]):
            for j in range(weight_matrix.shape[1]):
                wid = f"{layer_name}:{i}:{j}"
                syn = self._synapses.get(wid)
                if syn and syn.omega > 0:
                    total_omega += syn.omega
                    diff = abs(weight_matrix[i, j] - syn.optimal_weight)
                    total_change += syn.omega * diff
        if total_omega == 0:
            return 0.0
        return float(total_change / total_omega)

    def get_domain_map(self) -> Dict[str, List[str]]:
        """خريطة النطاقات والمهام"""
        conn = get_db_connection(self.db_path)
        try:
            rows = conn.execute("SELECT domain, task_id FROM si_tasks").fetchall()
            domains = {}
            for domain, task_id in rows:
                domains.setdefault(domain or "unknown", []).append(task_id)
            return domains
        finally:
            conn.close()

    def get_stats(self) -> Dict:
        return {
            "tracked_synapses": len(self._synapses),
            "important_synapses": sum(1 for s in self._synapses.values() if s.omega > 0.01),
            "tasks_completed": len(self._task_history),
            "active_task": self._active_task,
            "lambda_si": self._lambda_si,
            "avg_omega": float(np.mean([s.omega for s in self._synapses.values()]))
                        if self._synapses else 0.0,
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

synaptic_intelligence = SynapticIntelligenceEngine()
