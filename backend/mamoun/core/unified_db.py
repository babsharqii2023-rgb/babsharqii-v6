"""
BABSHARQII v23.0 — Unified Database Module
قاعدة بيانات موحدة لكل محركات مامون

Replaces 8+ separate SQLite database files with a SINGLE unified database.
All engine tables are prefixed to avoid collisions:
  ls_  = Living State
  em_  = Emotional Memory
  db_  = Deep Bonding
  rf_  = Reflexes
  ae_  = Absolute Executor
  sh_  = Self-Healing
  nb_  = Neural Bus
  rj_  = Reflective Journal
  pm_  = Predictive Memory
  cl_  = Consciousness Loop
  ms_  = Memory Store

Benefits:
  - Single WAL file = better write concurrency
  - Cross-engine transactions (e.g. store episode + update bond atomically)
  - Simpler backup and migration
  - Reduced file handle pressure
  - Consistent schema versioning
"""

from pathlib import Path
import sqlite3
import json
import logging
import time
import shutil
from typing import Optional, Dict, List, Any

logger = logging.getLogger("mamoun.unified_db")

# ═══════════════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════════════

# Resolve relative to this file's location so the path works regardless of CWD.
# This file lives at: backend/mamoun/core/unified_db.py
# DB should be at:     backend/data/mamoun_unified.db
UNIFIED_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "mamoun_unified.db"

# Old separate DB files that may exist and need migration
OLD_DB_FILES: Dict[str, str] = {
    "living_state":       "living_state.db",
    "emotional_memory":   "emotional_memory.db",
    "deep_bonding":       "deep_bonding.db",
    "reflexes":           "reflexes.db",
    "absolute_executor":  "absolute_executor.db",
    "self_healing":       "self_healing.db",
    "neural_bus":         "neural_bus.db",
    "reflective_journal": "mamoun.db",
    "predictive_memory":  "predictive_memory.db",
    "autonomy":           "autonomy.db",
    "dashboard_builder":  "dashboard_builder.db",
    "iot_devices":        "iot_devices.db",
}

# Mapping: (old_db_filename, old_table_name, unified_table_name)
# For modules whose tables are now prefixed in the unified DB.
MODULE_TABLE_MAP: Dict[str, Dict[str, str]] = {
    "autonomy": {
        "autonomy_decisions": "at_decisions",
        "autonomy_state": "at_state",
        "autonomy_confidence": "at_confidence",
    },
    "dashboard_builder": {
        "dashboard_layouts": "dbd_layouts",
        "dashboard_widgets": "dbd_widgets",
    },
    "iot_devices": {
        "iot_devices": "iot_devices",
    },
    "mamoun": {
        "reflective_journal": "rj_entries",
        "approval_requests": "ap_requests",
        "episodic_memory_v14": "ep_memory",
        "procedural_skills": "pm_skills",
        "interaction_records": "ir_records",
        "memory_fallback": "mf_fallback",
        "one_shot_skills": "os_skills",
        "one_shot_applications": "os_applications",
        "skill_generalizations": "os_generalizations",
        "skill_domain_mappings": "os_domain_mappings",
        "skill_merges": "os_merges",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
#  Connection Management
# ═══════════════════════════════════════════════════════════════════════════════

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    الحصول على اتصال بقاعدة البيانات الموحدة — Get a connection to the unified DB.

    Enables WAL mode for better read/write concurrency (readers don't block
    writers and writers don't block readers). Sets foreign keys ON and a
    reasonable busy timeout.

    Args:
        db_path: Override the default UNIFIED_DB_PATH if needed.

    Returns:
        sqlite3.Connection with WAL mode enabled.
    """
    path = db_path or UNIFIED_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


# ═══════════════════════════════════════════════════════════════════════════════
#  Schema Initialization
# ═══════════════════════════════════════════════════════════════════════════════

SCHEMA_VERSION = 3

def init_unified_schema(db_path: Optional[Path] = None) -> bool:
    """
    إنشاء جميع جداول المحركات في قاعدة بيانات واحدة — Create ALL engine
    tables in a single database with proper prefixes.

    Tables created (by engine):
      Living State:       ls_vitals, ls_events, ls_state
      Emotional Memory:   em_episodes, em_relationships, em_identity, em_state
      Deep Bonding:       db_metrics, db_insights, db_state
      Reflexes:           rf_triggers, rf_responses
      Absolute Executor:  ae_plans, ae_steps, ae_stats
      Self-Healing:       sh_issues, sh_repairs, sh_stats
      Neural Bus:         nb_signals, nb_stats
      Reflective Journal: rj_entries
      Predictive Memory:  pm_predictions, pm_stats
      Consciousness Loop: cl_perceptions, cl_expectations, cl_surprises, cl_learnings, cl_actions, cl_state
      Memory Store:       ms_store

    Also creates a _meta table for schema version tracking.

    Args:
        db_path: Override the default UNIFIED_DB_PATH if needed.

    Returns:
        True if schema was created/verified successfully.
    """
    conn = get_db_connection(db_path)
    try:
        # ── Meta table ──────────────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS _meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # Check existing version
        cur = conn.execute("SELECT value FROM _meta WHERE key = 'schema_version'")
        row = cur.fetchone()
        existing_version = int(row["value"]) if row else 0

        if existing_version >= SCHEMA_VERSION:
            logger.debug("Unified DB schema v%d already exists, skipping", existing_version)
            return True

        # ── Living State (ls_) ──────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ls_vitals (
            name TEXT PRIMARY KEY,
            value REAL,
            baseline REAL,
            min_val REAL,
            max_val REAL,
            decay_rate REAL,
            last_updated REAL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ls_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            event_type TEXT,
            intensity REAL,
            valence REAL,
            source TEXT,
            description TEXT,
            effects TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ls_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Emotional Memory (em_) ─────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS em_episodes (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            content TEXT,
            emotional_summary TEXT,
            emotion_label TEXT,
            valence REAL,
            arousal REAL,
            salience TEXT,
            user_id TEXT,
            topics TEXT,
            lessons TEXT,
            revisit_count INTEGER DEFAULT 0,
            last_revisited REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS em_relationships (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            first_interaction REAL,
            last_interaction REAL,
            total_interactions INTEGER,
            attachment_level REAL,
            trust_level REAL,
            communication_style TEXT,
            interests TEXT,
            emotional_history_summary TEXT,
            key_memories TEXT,
            relationship_phase TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS em_identity (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS em_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Deep Bonding (db_) ──────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS db_metrics (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS db_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            content TEXT,
            confidence REAL,
            learned_at REAL,
            confirmed INTEGER DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS db_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Reflexes (rf_) ─────────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS rf_triggers (
            id TEXT PRIMARY KEY,
            reflex_type TEXT,
            condition TEXT,
            priority TEXT,
            action TEXT,
            handler_name TEXT,
            enabled INTEGER DEFAULT 1,
            fire_count INTEGER DEFAULT 0,
            last_fired REAL DEFAULT 0,
            cooldown_seconds REAL DEFAULT 60
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS rf_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_id TEXT,
            reflex_type TEXT,
            action_taken TEXT,
            success INTEGER,
            message_ar TEXT,
            response_time_ms REAL,
            timestamp REAL
        )""")

        # ── Absolute Executor (ae_) ─────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ae_plans (
            id TEXT PRIMARY KEY,
            user_request TEXT,
            intent TEXT,
            intent_category TEXT,
            phase TEXT,
            success INTEGER,
            total_retries INTEGER,
            created_at REAL,
            completed_at REAL,
            result TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ae_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT,
            step_id TEXT,
            description TEXT,
            tool TEXT,
            params TEXT,
            status TEXT DEFAULT 'pending',
            result TEXT,
            error TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            started_at REAL,
            completed_at REAL,
            FOREIGN KEY (plan_id) REFERENCES ae_plans(id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS ae_stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Self-Healing (sh_) ──────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS sh_issues (
            id TEXT PRIMARY KEY,
            component TEXT,
            severity TEXT,
            description TEXT,
            root_cause TEXT,
            repair_action TEXT,
            detected_at REAL,
            resolved_at REAL,
            is_resolved INTEGER,
            auto_repaired INTEGER,
            recurrence_count INTEGER
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sh_repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id TEXT,
            root_cause TEXT,
            repair_action TEXT,
            repair_time_ms REAL,
            success INTEGER,
            timestamp REAL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS sh_stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Neural Bus (nb_) ────────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS nb_signals (
            id TEXT PRIMARY KEY,
            signal_type TEXT,
            priority INTEGER,
            direction TEXT,
            source TEXT,
            target TEXT,
            payload TEXT,
            timestamp REAL,
            cascade_chain TEXT,
            processed_by TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS nb_stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Reflective Journal (rj_) ────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS rj_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            entry_type TEXT NOT NULL,
            summary TEXT,
            details TEXT DEFAULT '',
            emotional_valence REAL DEFAULT 0.0,
            confidence REAL DEFAULT 0.0,
            root_cause TEXT DEFAULT '',
            lesson_learned TEXT DEFAULT '',
            related_brain_ids TEXT DEFAULT '[]',
            skill_gained TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}'
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rj_type ON rj_entries(entry_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rj_timestamp ON rj_entries(timestamp)"
        )

        # ── Predictive Memory (pm_) ─────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_transitions (
            from_topic TEXT NOT NULL,
            to_topic TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            last_seen REAL DEFAULT 0,
            PRIMARY KEY (from_topic, to_topic)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_predictions (
            id TEXT PRIMARY KEY,
            predicted_topic TEXT NOT NULL,
            predicted_action TEXT DEFAULT '',
            confidence REAL DEFAULT 0,
            reasoning TEXT DEFAULT '',
            evidence TEXT DEFAULT '[]',
            created_at REAL DEFAULT 0,
            verified TEXT DEFAULT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_patterns (
            sequence TEXT PRIMARY KEY,
            frequency INTEGER DEFAULT 1,
            last_seen REAL DEFAULT 0,
            next_predicted TEXT DEFAULT ''
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_accuracy (
            timestamp REAL PRIMARY KEY,
            correct INTEGER DEFAULT 0,
            total INTEGER DEFAULT 1
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        # ── Autonomy Engine (at_) ────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS at_decisions (
            operation_id TEXT PRIMARY KEY,
            operation_type TEXT NOT NULL,
            safety_tier TEXT NOT NULL,
            auto_approved INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            reason TEXT DEFAULT '',
            requires_2fa INTEGER DEFAULT 0,
            timestamp REAL DEFAULT 0.0,
            human_decision TEXT DEFAULT 'pending',
            human_reason TEXT DEFAULT ''
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS at_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS at_confidence (
            operation_type TEXT PRIMARY KEY,
            confidence REAL DEFAULT 0.5,
            sample_count INTEGER DEFAULT 0
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_at_decisions_ts ON at_decisions(timestamp)"
        )

        # ── Dashboard Builder (dbd_) ─────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS dbd_layouts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS dbd_widgets (
            id TEXT PRIMARY KEY,
            layout_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT DEFAULT '',
            title_ar TEXT DEFAULT '',
            position TEXT DEFAULT '{}',
            data_source TEXT DEFAULT '',
            refresh_interval INTEGER DEFAULT 30,
            props TEXT DEFAULT '{}',
            FOREIGN KEY (layout_id) REFERENCES dbd_layouts(id)
        )""")

        # ── IoT Gateway (iot_) ───────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS iot_devices (
            device_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            name_ar TEXT DEFAULT '',
            device_type TEXT NOT NULL,
            protocol TEXT DEFAULT 'rest',
            endpoint TEXT DEFAULT '',
            capabilities TEXT DEFAULT '[]',
            state TEXT DEFAULT '{}',
            last_seen REAL DEFAULT 0,
            is_online INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}'
        )""")

        # ── Reflective Journal (rj_) — full table matching mamoun.db schema ──
        # Already created above with v1 schema; ensure compatibility columns
        # The rj_entries table already exists from v1

        # ── Approval Gate (ap_) ──────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ap_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            change_type TEXT NOT NULL,
            target TEXT NOT NULL,
            description TEXT DEFAULT '',
            risk_level TEXT DEFAULT 'medium',
            details TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            requested_at REAL DEFAULT 0,
            decided_at REAL DEFAULT 0,
            decided_by TEXT DEFAULT '',
            rejection_reason TEXT DEFAULT '',
            auto_deploy_enabled INTEGER DEFAULT 0
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ap_requests_status ON ap_requests(status)"
        )

        # ── Episodic Memory (ep_) ────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ep_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_type TEXT DEFAULT '',
            content TEXT NOT NULL,
            participants TEXT DEFAULT '[]',
            emotions TEXT DEFAULT '[]',
            context TEXT DEFAULT '{}',
            timestamp REAL DEFAULT 0,
            importance_score REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed REAL DEFAULT 0,
            tags TEXT DEFAULT '[]',
            embedding BLOB
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ep_memory_ts ON ep_memory(timestamp)"
        )

        # ── One-Shot Learning (os_) ──────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS os_skills (
            skill_id TEXT PRIMARY KEY,
            skill_name TEXT NOT NULL,
            skill_name_ar TEXT DEFAULT '',
            task_type TEXT DEFAULT '',
            abstract_rules TEXT DEFAULT '[]',
            dynamic_variables TEXT DEFAULT '[]',
            constraints TEXT DEFAULT '[]',
            prerequisites TEXT DEFAULT '[]',
            source_example_id TEXT DEFAULT '',
            created_at REAL DEFAULT 0,
            application_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0,
            template TEXT DEFAULT '{}'
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS os_applications (
            application_id TEXT PRIMARY KEY,
            skill_id TEXT NOT NULL,
            instance_id TEXT DEFAULT '',
            success INTEGER DEFAULT 0,
            output_data TEXT DEFAULT '{}',
            confidence REAL DEFAULT 0,
            substitutions TEXT DEFAULT '{}',
            errors TEXT DEFAULT '[]',
            applied_at REAL DEFAULT 0,
            FOREIGN KEY (skill_id) REFERENCES os_skills(skill_id)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS os_generalizations (
            generalized_skill_id TEXT PRIMARY KEY,
            original_skill_id TEXT NOT NULL,
            generalized_rules TEXT DEFAULT '[]',
            applicable_domains TEXT DEFAULT '[]',
            generalization_confidence REAL DEFAULT 0,
            domain_mappings TEXT DEFAULT '{}',
            created_at REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS os_domain_mappings (
            mapping_id TEXT PRIMARY KEY,
            source_domain TEXT NOT NULL,
            target_domain TEXT NOT NULL,
            source_skill_id TEXT NOT NULL,
            rule_mappings TEXT DEFAULT '{}',
            variable_mappings TEXT DEFAULT '{}',
            confidence REAL DEFAULT 0,
            created_at REAL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS os_merges (
            merged_skill_id TEXT PRIMARY KEY,
            source_skill_ids TEXT DEFAULT '[]',
            merged_rules TEXT DEFAULT '[]',
            merged_variables TEXT DEFAULT '[]',
            coverage_score REAL DEFAULT 0,
            created_at REAL DEFAULT 0
        )""")

        # ── Procedural Memory (pm_) — skill storage ──────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS pm_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_ar TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            trigger_condition TEXT DEFAULT '',
            action_template TEXT DEFAULT '',
            context_patterns TEXT DEFAULT '[]',
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0,
            last_used REAL DEFAULT 0,
            created_at REAL DEFAULT 0,
            auto_extracted INTEGER DEFAULT 0,
            source_interactions TEXT DEFAULT '[]',
            related_brain_ids TEXT DEFAULT '[]'
        )""")

        # ── Interaction Records (ir_) ────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ir_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL DEFAULT 0,
            input_type TEXT DEFAULT '',
            input_pattern TEXT DEFAULT '',
            response_strategy TEXT DEFAULT '',
            brain_used TEXT DEFAULT '',
            success INTEGER DEFAULT 0,
            user_feedback TEXT DEFAULT '',
            latency_ms REAL DEFAULT 0,
            context TEXT DEFAULT '{}'
        )""")

        # ── Memory Fallback (mf_) ────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS mf_fallback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_type TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            timestamp REAL DEFAULT 0,
            tags TEXT DEFAULT '[]',
            embedding BLOB
        )""")

        # ── Consciousness Loop (cl_) ──────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_perceptions (
            id TEXT PRIMARY KEY, content TEXT NOT NULL,
            perception_type TEXT DEFAULT 'user_interaction', source TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}', timestamp REAL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_expectations (
            id TEXT PRIMARY KEY, expected_topic TEXT NOT NULL,
            expected_action TEXT DEFAULT '', confidence REAL DEFAULT 0.5,
            source_phase TEXT DEFAULT '', timestamp REAL DEFAULT 0, verified TEXT DEFAULT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_surprises (
            id TEXT PRIMARY KEY, expectation_id TEXT DEFAULT '',
            expected TEXT DEFAULT '', actual TEXT DEFAULT '',
            surprise_level TEXT DEFAULT 'none', surprise_score REAL DEFAULT 0,
            learning_value REAL DEFAULT 0, description TEXT DEFAULT '', timestamp REAL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_learnings (
            id TEXT PRIMARY KEY, what_was_learned TEXT NOT NULL,
            model_updated TEXT DEFAULT '', before_state TEXT DEFAULT '',
            after_state TEXT DEFAULT '', source_surprise_id TEXT DEFAULT '',
            timestamp REAL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_actions (
            id TEXT PRIMARY KEY, action_type TEXT DEFAULT 'notification',
            content TEXT NOT NULL, priority TEXT DEFAULT 'low',
            source_learning_id TEXT DEFAULT '', timestamp REAL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cl_state (
            key TEXT PRIMARY KEY, value TEXT NOT NULL)""")

        # ── Memory Store (ms_) ─────────────────────────────────────────────
        conn.execute("""CREATE TABLE IF NOT EXISTS ms_store (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL DEFAULT 0,
            updated_at REAL DEFAULT 0,
            metadata TEXT DEFAULT '{}'
        )""")

        # ── Indexes for common queries ──────────────────────────────────────
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ls_events_ts ON ls_events(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_em_episodes_ts ON em_episodes(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_em_episodes_uid ON em_episodes(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sh_issues_resolved ON sh_issues(is_resolved)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nb_signals_ts ON nb_signals(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ae_plans_ts ON ae_plans(created_at)"
        )

        # Record schema version
        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
            ("created_at", str(time.time())),
        )

        conn.commit()
        logger.info("Unified DB schema v%d created successfully at %s", SCHEMA_VERSION, db_path or UNIFIED_DB_PATH)
        return True

    except Exception as e:
        logger.error("Failed to init unified schema: %s", e)
        conn.rollback()
        return False
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Migration from Separate DBs
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping: (old_db_filename, old_table_name, unified_table_name)
# These are the tables that exist in the old separate databases.
MIGRATION_MAP: List[tuple] = [
    # Living State
    ("living_state.db",       "ls_vitals",       "ls_vitals"),
    ("living_state.db",       "ls_events",       "ls_events"),
    ("living_state.db",       "ls_state",        "ls_state"),
    # Emotional Memory
    ("emotional_memory.db",   "em_episodes",       "em_episodes"),
    ("emotional_memory.db",   "em_relationships",  "em_relationships"),
    ("emotional_memory.db",   "em_identity",       "em_identity"),
    ("emotional_memory.db",   "em_state",          "em_state"),
    # Deep Bonding
    ("deep_bonding.db",       "db_metrics",      "db_metrics"),
    ("deep_bonding.db",       "db_insights",     "db_insights"),
    ("deep_bonding.db",       "db_state",        "db_state"),
    # Reflexes
    ("reflexes.db",           "rf_triggers",     "rf_triggers"),
    ("reflexes.db",           "rf_responses",    "rf_responses"),
    # Absolute Executor
    ("absolute_executor.db",  "ae_plans",        "ae_plans"),
    ("absolute_executor.db",  "ae_stats",        "ae_stats"),
    # Self-Healing
    ("self_healing.db",       "sh_issues",       "sh_issues"),
    ("self_healing.db",       "sh_repairs",      "sh_repairs"),
    ("self_healing.db",       "sh_stats",        "sh_stats"),
    # Neural Bus
    ("neural_bus.db",         "nb_signals",      "nb_signals"),
    ("neural_bus.db",         "nb_stats",        "nb_stats"),
    # Reflective Journal — old table name is "reflective_journal", new is "rj_entries"
    ("mamoun.db",             "reflective_journal", "rj_entries"),
    # Predictive Memory — all tables migrated 1:1 with matching schemas
    ("predictive_memory.db",  "pm_transitions",  "pm_transitions"),
    ("predictive_memory.db",  "pm_predictions",  "pm_predictions"),
    ("predictive_memory.db",  "pm_patterns",     "pm_patterns"),
    ("predictive_memory.db",  "pm_accuracy",     "pm_accuracy"),
    # Autonomy Engine — table names changed to prefixed
    ("autonomy.db",           "autonomy_decisions",  "at_decisions"),
    ("autonomy.db",           "autonomy_state",      "at_state"),
    ("autonomy.db",           "autonomy_confidence",  "at_confidence"),
    # Dashboard Builder — table names changed to prefixed
    ("dashboard_builder.db",  "dashboard_layouts",   "dbd_layouts"),
    ("dashboard_builder.db",  "dashboard_widgets",   "dbd_widgets"),
    # IoT Devices — table name stays the same in unified DB
    ("iot_devices.db",        "iot_devices",         "iot_devices"),
    # Mamoun main DB — remaining tables with new prefixed names
    ("mamoun.db",             "approval_requests",   "ap_requests"),
    ("mamoun.db",             "episodic_memory_v14", "ep_memory"),
    ("mamoun.db",             "procedural_skills",   "pm_skills"),
    ("mamoun.db",             "interaction_records",  "ir_records"),
    ("mamoun.db",             "memory_fallback",     "mf_fallback"),
    ("mamoun.db",             "one_shot_skills",     "os_skills"),
    ("mamoun.db",             "one_shot_applications", "os_applications"),
    ("mamoun.db",             "skill_generalizations", "os_generalizations"),
    ("mamoun.db",             "skill_domain_mappings", "os_domain_mappings"),
    ("mamoun.db",             "skill_merges",        "os_merges"),
    # Consciousness Loop (cl_) — new tables in v3, no migration needed
    # Memory Store (ms_) — new table in v3, no migration needed
]


def _get_data_dirs() -> List[Path]:
    """Get all possible data directories where old DB files might live."""
    candidates = [
        Path("backend/data"),
        Path("backend/backend/data"),
        Path(__file__).parent.parent.parent / "data",
        Path(__file__).parent.parent.parent / "backend" / "data",
    ]
    return [d for d in candidates if d.is_dir()]


def migrate_from_separate_dbs(
    db_path: Optional[Path] = None,
    data_dirs: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    ترحيل البيانات من قواعد البيانات المنفصلة إلى الموحدة — Migrate data
    from each old separate DB file into the unified one.

    For each old DB file:
      1. Open it and check if it has data
      2. Copy all rows from each table into the corresponding unified table
      3. Rename the old file with a .migrated.bak suffix

    Args:
        db_path: Override the default UNIFIED_DB_PATH if needed.
        data_dirs: Override the search directories for old DB files.

    Returns:
        Dict with migration statistics:
          - migrated_tables: list of table names that were migrated
          - migrated_rows: dict of table_name → row_count
          - skipped: list of old DB files that were not found
          - errors: list of (source, error_message)
          - backed_up: list of old files renamed to .migrated.bak
    """
    result: Dict[str, Any] = {
        "migrated_tables": [],
        "migrated_rows": {},
        "skipped": [],
        "errors": [],
        "backed_up": [],
    }

    unified_path = db_path or UNIFIED_DB_PATH

    # Ensure schema exists before migration
    init_unified_schema(unified_path)

    # Find data directories
    dirs = data_dirs or _get_data_dirs()
    if not dirs:
        logger.warning("No data directories found for migration")
        result["skipped"] = list(OLD_DB_FILES.keys())
        return result

    # Track which old DB files we've already processed (avoid double-migration)
    processed_files: Dict[str, Path] = {}

    for old_filename, old_table, unified_table in MIGRATION_MAP:
        # Find the old DB file
        old_db_path = None
        for d in dirs:
            candidate = d / old_filename
            if candidate.exists() and candidate.is_file():
                old_db_path = candidate
                break

        if old_db_path is None:
            if old_filename not in [s for s in result["skipped"]]:
                result["skipped"].append(old_filename)
            continue

        # Skip if already migrated (file has .migrated.bak suffix)
        if old_db_path.suffix == ".bak" or ".migrated" in old_db_path.name:
            continue

        try:
            # Connect to the old separate DB
            old_conn = sqlite3.connect(str(old_db_path))
            old_conn.row_factory = sqlite3.Row

            # Check if the table exists in the old DB
            cur = old_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (old_table,),
            )
            if not cur.fetchone():
                old_conn.close()
                continue

            # Count rows
            count_cur = old_conn.execute(f"SELECT COUNT(*) as cnt FROM [{old_table}]")
            row_count = count_cur.fetchone()["cnt"]

            if row_count == 0:
                old_conn.close()
                continue

            # Connect to unified DB
            uni_conn = get_db_connection(unified_path)

            # Fetch column names from the old table
            sample_cur = old_conn.execute(f"SELECT * FROM [{old_table}] LIMIT 1")
            col_names = [desc[0] for desc in sample_cur.description] if sample_cur.description else []

            # Fetch all rows
            rows_cur = old_conn.execute(f"SELECT * FROM [{old_table}]")
            rows = rows_cur.fetchall()

            migrated = 0
            for row in rows:
                # Convert Row to dict
                row_dict = dict(row)
                # Only keep columns that exist in the unified table
                # Build INSERT statement dynamically
                values = [row_dict.get(col) for col in col_names]
                placeholders = ", ".join(["?"] * len(col_names))
                col_str = ", ".join(f"[{c}]" for c in col_names)

                try:
                    uni_conn.execute(
                        f"INSERT OR IGNORE INTO [{unified_table}] ({col_str}) VALUES ({placeholders})",
                        values,
                    )
                    migrated += 1
                except Exception as insert_err:
                    # Column mismatch — try inserting with only matching columns
                    try:
                        # Get columns from the unified table (BUG-004 FIX: use f-string since PRAGMA doesn't support params)
                        # Table name is from MIGRATION_MAP (hardcoded), safe from injection
                        uni_cur = uni_conn.execute(
                            f"SELECT name FROM pragma_table_info([{unified_table}])"
                        )
                        uni_cols = {r[0] for r in uni_cur.fetchall()}
                        matching_cols = [c for c in col_names if c in uni_cols]
                        if matching_cols:
                            m_values = [row_dict.get(c) for c in matching_cols]
                            m_placeholders = ", ".join(["?"] * len(matching_cols))
                            m_col_str = ", ".join(f"[{c}]" for c in matching_cols)
                            uni_conn.execute(
                                f"INSERT OR IGNORE INTO [{unified_table}] ({m_col_str}) VALUES ({m_placeholders})",
                                m_values,
                            )
                            migrated += 1
                        else:
                            result["errors"].append(
                                (f"{old_filename}:{old_table}", str(insert_err))
                            )
                    except Exception as fallback_err:
                        result["errors"].append(
                            (f"{old_filename}:{old_table}", str(fallback_err))
                        )

            uni_conn.commit()
            # Connections closed in finally block (BUG-005 fix)

            result["migrated_tables"].append(f"{old_table}→{unified_table}")
            result["migrated_rows"][unified_table] = result["migrated_rows"].get(unified_table, 0) + migrated

            logger.info(
                "Migrated %d rows from %s:%s → %s",
                migrated, old_filename, old_table, unified_table,
            )

            # Mark file for backup (we'll rename after all tables from this file are done)
            processed_files[old_filename] = old_db_path

        except Exception as e:
            result["errors"].append((f"{old_filename}:{old_table}", str(e)))
            logger.error("Migration error for %s:%s: %s", old_filename, old_table, e)
        finally:
            # BUG-005 FIX: Ensure connections are always closed
            try:
                if 'uni_conn' in dir():
                    uni_conn.close()
            except Exception:
                pass
            try:
                old_conn.close()
            except Exception:
                pass

    # Rename old DB files with .migrated.bak suffix
    for old_filename, old_path in processed_files.items():
        backup_path = old_path.with_suffix(old_path.suffix + ".migrated.bak")
        # Don't overwrite existing backups
        if backup_path.exists():
            logger.info("Backup already exists: %s, skipping rename", backup_path)
            continue
        try:
            shutil.move(str(old_path), str(backup_path))
            result["backed_up"].append(str(backup_path))
            logger.info("Renamed %s → %s", old_path, backup_path)
        except Exception as e:
            result["errors"].append((f"backup:{old_filename}", str(e)))
            logger.error("Failed to rename %s: %s", old_path, e)

    logger.info(
        "Migration complete: %d tables migrated, %d rows total, %d errors, %d files backed up",
        len(result["migrated_tables"]),
        sum(result["migrated_rows"].values()),
        len(result["errors"]),
        len(result["backed_up"]),
    )

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_schema_info(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    الحصول على معلومات مخطط قاعدة البيانات — Get info about all tables
    in the unified database (row counts, column names).
    """
    conn = get_db_connection(db_path)
    try:
        tables = {}
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        for row in cur.fetchall():
            table_name = row["name"]
            count_cur = conn.execute(f"SELECT COUNT(*) as cnt FROM [{table_name}]")
            cnt = count_cur.fetchone()["cnt"]

            cols_cur = conn.execute(f"PRAGMA table_info([{table_name}])")
            columns = [{"name": r["name"], "type": r["type"], "pk": r["pk"]} for r in cols_cur.fetchall()]

            tables[table_name] = {
                "row_count": cnt,
                "columns": columns,
            }

        # Meta info
        meta = {}
        meta_cur = conn.execute("SELECT key, value FROM _meta")
        for row in meta_cur.fetchall():
            meta[row["key"]] = row["value"]

        return {"tables": tables, "meta": meta}
    finally:
        conn.close()


def vacuum(db_path: Optional[Path] = None) -> bool:
    """تفريغ قاعدة البيانات — Vacuum the unified DB to reclaim space."""
    try:
        conn = get_db_connection(db_path)
        conn.execute("VACUUM")
        conn.close()
        logger.info("Unified DB vacuumed successfully")
        return True
    except Exception as e:
        logger.error("Vacuum failed: %s", e)
        return False


def check_integrity(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """فحص سلامة قاعدة البيانات — Check database integrity."""
    conn = get_db_connection(db_path)
    try:
        cur = conn.execute("PRAGMA integrity_check")
        result = cur.fetchone()
        is_ok = result["integrity_check"] == "ok" if result else False

        # Also check WAL mode
        wal_cur = conn.execute("PRAGMA journal_mode")
        wal_mode = wal_cur.fetchone()
        journal_mode = wal_cur.fetchone() if wal_mode else None
        # Re-query because row_factory already consumed it
        wal_cur2 = conn.execute("PRAGMA journal_mode")
        jm_row = wal_cur2.fetchone()
        jmode = dict(jm_row).get("journal_mode", "unknown") if jm_row else "unknown"

        return {
            "integrity_ok": is_ok,
            "journal_mode": jmode,
            "db_path": str(db_path or UNIFIED_DB_PATH),
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Auto-initialize on import
# ═══════════════════════════════════════════════════════════════════════════════

try:
    _init_ok = init_unified_schema()
    if _init_ok:
        logger.debug("Unified DB auto-initialized on import")
    else:
        logger.warning("Unified DB auto-init returned False (schema may be incomplete)")
except Exception as _init_err:
    logger.warning("Unified DB auto-init failed on import: %s", _init_err)
