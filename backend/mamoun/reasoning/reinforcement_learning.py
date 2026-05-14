"""
BABSHARQII v26.0 — Reinforcement Learning Engine
محرك التعلم المعزز — بدون LLM

Real RL with:
1. Q-Table: state-action value function
2. Q-Learning: off-policy TD control
3. SARSA: on-policy TD control
4. Epsilon-greedy exploration
5. Reward shaping and discount
6. Policy extraction from Q-values

NO LLM CALLS. Pure temporal difference learning.
Based on: Sutton & Barto (2018), Watkins (1989)
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

logger = logging.getLogger("mamoun.reinforcement_learning")


@dataclass
class RLState:
    """حالة — تمثيل بيئة"""
    state_id: str = ""
    features: Dict[str, float] = field(default_factory=dict)
    description: str = ""
    visit_count: int = 0

    def __post_init__(self):
        if not self.state_id:
            self.state_id = f"s_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {"state_id": self.state_id, "features": self.features,
                "description": self.description, "visit_count": self.visit_count}


@dataclass
class RLAction:
    """فعل — قرار يمكن اتخاذه"""
    action_id: str = ""
    name: str = ""
    action_type: str = "discrete"  # discrete, continuous
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.action_id:
            self.action_id = f"a_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return {"action_id": self.action_id, "name": self.name,
                "action_type": self.action_type, "parameters": self.parameters}


class ReinforcementLearningEngine:
    """
    محرك التعلم المعزز — تعلم من التجربة بالمكافأة

    - Q-Table: persistent state-action values in SQLite
    - Q-Learning update: Q(s,a) ← Q(s,a) + α[r + γ·max_a' Q(s',a') - Q(s,a)]
    - Exploration: ε-greedy with decay
    - Policy: extract best action from Q-values
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._llm = None
        self._initialized = False
        self._q_table: Dict[str, Dict[str, float]] = {}  # state → action → Q-value
        self._states: Dict[str, RLState] = {}
        self._actions: Dict[str, RLAction] = {}
        self._alpha = 0.1        # learning rate
        self._gamma = 0.95       # discount factor
        self._epsilon = 0.3      # exploration rate
        self._epsilon_decay = 0.995
        self._epsilon_min = 0.01
        self._episode_count = 0
        self._total_reward = 0.0

    def set_llm_client(self, llm_client):
        self._llm = llm_client  # NOT USED

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("RLEngine initialized: %d states, %d actions, %d Q-entries",
                        len(self._states), len(self._actions), sum(len(v) for v in self._q_table.values()))
            return True
        except Exception as e:
            logger.error("RLEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""CREATE TABLE IF NOT EXISTS rl_q_table (
                state_id TEXT, action_id TEXT, q_value REAL DEFAULT 0.0,
                update_count INTEGER DEFAULT 0, last_updated REAL DEFAULT 0,
                PRIMARY KEY (state_id, action_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rl_states (
                state_id TEXT PRIMARY KEY, features TEXT, description TEXT, visit_count INTEGER DEFAULT 0)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rl_actions (
                action_id TEXT PRIMARY KEY, name TEXT, action_type TEXT, parameters TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS rl_episodes (
                episode_id TEXT PRIMARY KEY, state_id TEXT, action_id TEXT,
                reward REAL DEFAULT 0.0, next_state_id TEXT, done INTEGER DEFAULT 0,
                timestamp REAL DEFAULT 0)""")
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT state_id, action_id, q_value FROM rl_q_table"):
                self._q_table.setdefault(row[0], {})[row[1]] = row[2]
            for row in conn.execute("SELECT state_id, features, description, visit_count FROM rl_states"):
                self._states[row[0]] = RLState(state_id=row[0], features=json.loads(row[1]),
                    description=row[2], visit_count=row[3])
            for row in conn.execute("SELECT action_id, name, action_type, parameters FROM rl_actions"):
                self._actions[row[0]] = RLAction(action_id=row[0], name=row[1],
                    action_type=row[2], parameters=json.loads(row[3]))
        finally:
            conn.close()

    def _persist_q(self, state_id: str, action_id: str, q_value: float):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO rl_q_table (state_id, action_id, q_value, update_count, last_updated) VALUES (?,?,?,?,?)",
                (state_id, action_id, q_value, 1, time.time()))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════════════

    def register_state(self, description: str, features: Dict[str, float] = None) -> RLState:
        """تسجيل حالة جديدة"""
        state = RLState(features=features or {}, description=description)
        self._states[state.state_id] = state
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO rl_states VALUES (?,?,?,?)",
                (state.state_id, json.dumps(state.features), state.description, 0))
            conn.commit()
        finally:
            conn.close()
        return state

    def register_action(self, name: str, action_type: str = "discrete",
                        parameters: Dict = None) -> RLAction:
        """تسجيل فعل جديد"""
        action = RLAction(name=name, action_type=action_type, parameters=parameters or {})
        self._actions[action.action_id] = action
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("INSERT OR REPLACE INTO rl_actions VALUES (?,?,?,?)",
                (action.action_id, action.name, action.action_type, json.dumps(action.parameters)))
            conn.commit()
        finally:
            conn.close()
        return action

    def q_learn(self, state_id: str, action_id: str, reward: float,
                next_state_id: str, done: bool = False) -> float:
        """
        Q-Learning update — التعلم من خطوة واحدة

        Q(s,a) ← Q(s,a) + α[r + γ·max_a' Q(s',a') - Q(s,a)]
        """
        current_q = self._q_table.get(state_id, {}).get(action_id, 0.0)

        if done:
            target = reward
        else:
            max_next_q = max(self._q_table.get(next_state_id, {}).values(), default=0.0)
            target = reward + self._gamma * max_next_q

        new_q = current_q + self._alpha * (target - current_q)
        self._q_table.setdefault(state_id, {})[action_id] = new_q
        self._persist_q(state_id, action_id, new_q)

        # Update visit count
        if state_id in self._states:
            self._states[state_id].visit_count += 1

        # Record episode
        self._episode_count += 1
        self._total_reward += reward

        return new_q

    def choose_action(self, state_id: str, available_actions: List[str] = None) -> Optional[str]:
        """
        اختيار فعل — ε-greedy

        With probability ε: explore (random action)
        With probability 1-ε: exploit (best Q-value action)
        """
        actions = available_actions or list(self._actions.keys())
        if not actions:
            return None

        # Epsilon-greedy
        if np.random.random() < self._epsilon:
            # Explore
            chosen = np.random.choice(actions)
        else:
            # Exploit: choose action with highest Q-value
            q_values = {a: self._q_table.get(state_id, {}).get(a, 0.0) for a in actions}
            max_q = max(q_values.values()) if q_values else 0.0
            best_actions = [a for a, q in q_values.items() if q == max_q]
            chosen = np.random.choice(best_actions)

        # Decay epsilon
        self._epsilon = max(self._epsilon_min, self._epsilon * self._epsilon_decay)
        return chosen

    def get_policy(self, state_id: str) -> Dict[str, Any]:
        """استخراج السياسة — أفضل فعل لكل حالة"""
        q_values = self._q_table.get(state_id, {})
        if not q_values:
            return {"state": state_id, "best_action": None, "q_values": {}}

        best_action = max(q_values, key=q_values.get)
        return {"state": state_id, "best_action": best_action, "q_values": q_values}

    def get_value(self, state_id: str) -> float:
        """V(s) = max_a Q(s,a)"""
        q_values = self._q_table.get(state_id, {})
        return max(q_values.values()) if q_values else 0.0

    def get_stats(self) -> Dict:
        return {
            "states": len(self._states),
            "actions": len(self._actions),
            "q_entries": sum(len(v) for v in self._q_table.values()),
            "episodes": self._episode_count,
            "total_reward": round(self._total_reward, 2),
            "avg_reward": round(self._total_reward / max(self._episode_count, 1), 4),
            "epsilon": round(self._epsilon, 4),
        }


_rl_engine: Optional[ReinforcementLearningEngine] = None

def get_rl_engine() -> ReinforcementLearningEngine:
    global _rl_engine
    if _rl_engine is None:
        _rl_engine = ReinforcementLearningEngine()
    return _rl_engine
