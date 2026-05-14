"""
BABSHARQII v40.0 — Data Management Module (GDPR Compliance)
Handles data export, deletion, and retention policies.
"""

import json
import time
import hashlib
import shutil
import aiosqlite
from pathlib import Path
from typing import Optional
from datetime import datetime


class DataManager:
    """Manages user data lifecycle — export, deletion, retention."""
    
    DELETED_REGISTRY_FILE = "deleted_users_registry.json"
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.deleted_registry_path = self.data_dir / self.DELETED_REGISTRY_FILE
        self._db_path = str(self.data_dir / "mamoun.db")
        self._ensure_registry()
    
    def _ensure_registry(self):
        """Ensure the deleted users registry exists."""
        if not self.deleted_registry_path.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.deleted_registry_path.write_text("[]", encoding="utf-8")
    
    # ── Database Helper ──────────────────────────────────────────
    
    async def _get_db(self):
        """Get an aiosqlite connection to the main database."""
        db = await aiosqlite.connect(self._db_path)
        db.row_factory = aiosqlite.Row
        return db
    
    # ── Export Methods ───────────────────────────────────────────
    
    async def _export_conversations(self, user_id: str) -> list:
        """Export conversation data from SQLite for a user."""
        try:
            db = await self._get_db()
            try:
                # Try to query interaction_records table (used by ProceduralMemory)
                cursor = await db.execute("""
                    SELECT id, timestamp, input_type, input_pattern, 
                           response_strategy, brain_used, success, 
                           user_feedback, latency_ms, context
                    FROM interaction_records
                    ORDER BY timestamp DESC
                """)
                rows = await cursor.fetchall()
                conversations = []
                for row in rows:
                    record = {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "datetime": datetime.fromtimestamp(row["timestamp"]).isoformat() if row["timestamp"] else None,
                        "input_type": row["input_type"],
                        "input_pattern": row["input_pattern"],
                        "response_strategy": row["response_strategy"],
                        "brain_used": row["brain_used"],
                        "success": bool(row["success"]),
                        "user_feedback": row["user_feedback"],
                        "latency_ms": row["latency_ms"],
                        "context": json.loads(row["context"]) if row["context"] else {},
                    }
                    conversations.append(record)
                return conversations
            finally:
                await db.close()
        except Exception:
            # Table might not exist yet
            return []
    
    async def _export_settings(self, user_id: str) -> dict:
        """Export user settings from the settings.yaml and environment."""
        settings = {}
        try:
            settings_path = Path(__file__).parent.parent.parent / "settings.yaml"
            if settings_path.exists():
                import yaml
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = yaml.safe_load(f) or {}
            # Remove sensitive data from export
            settings.pop("api_keys", None)
            settings.pop("secrets", None)
        except Exception:
            pass
        return settings
    
    async def _export_journal(self, user_id: str) -> list:
        """Export reflective journal entries from SQLite."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("""
                    SELECT id, timestamp, entry_type, summary, details,
                           emotional_valence, confidence, root_cause,
                           lesson_learned, related_brain_ids, skill_gained, metadata
                    FROM reflective_journal
                    ORDER BY timestamp DESC
                """)
                rows = await cursor.fetchall()
                entries = []
                for row in rows:
                    entry = {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "datetime": datetime.fromtimestamp(row["timestamp"]).isoformat() if row["timestamp"] else None,
                        "entry_type": row["entry_type"],
                        "summary": row["summary"],
                        "details": row["details"],
                        "emotional_valence": row["emotional_valence"],
                        "confidence": row["confidence"],
                        "root_cause": row["root_cause"],
                        "lesson_learned": row["lesson_learned"],
                        "related_brain_ids": json.loads(row["related_brain_ids"]) if row["related_brain_ids"] else [],
                        "skill_gained": row["skill_gained"],
                        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    }
                    entries.append(entry)
                return entries
            finally:
                await db.close()
        except Exception:
            return []
    
    async def _export_skills(self, user_id: str) -> list:
        """Export procedural memory skills from SQLite."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("""
                    SELECT id, name, name_ar, description, category,
                           trigger_condition, action_template, success_count,
                           failure_count, success_rate, last_used, created_at,
                           auto_extracted, source_interactions, related_brain_ids
                    FROM procedural_skills
                    ORDER BY success_rate DESC
                """)
                rows = await cursor.fetchall()
                skills = []
                for row in rows:
                    skill = {
                        "id": row["id"],
                        "name": row["name"],
                        "name_ar": row["name_ar"],
                        "description": row["description"],
                        "category": row["category"],
                        "trigger_condition": row["trigger_condition"],
                        "action_template": row["action_template"],
                        "success_count": row["success_count"],
                        "failure_count": row["failure_count"],
                        "success_rate": row["success_rate"],
                        "last_used": row["last_used"],
                        "created_at": row["created_at"],
                        "auto_extracted": bool(row["auto_extracted"]),
                        "source_interactions": row["source_interactions"],
                        "related_brain_ids": json.loads(row["related_brain_ids"]) if row["related_brain_ids"] else [],
                    }
                    skills.append(skill)
                return skills
            finally:
                await db.close()
        except Exception:
            return []
    
    # ── Delete Methods ───────────────────────────────────────────
    
    async def _delete_conversations(self, user_id: str) -> int:
        """Delete conversation data from SQLite interaction_records."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM interaction_records")
                row = await cursor.fetchone()
                count = row[0] if row else 0
                
                await db.execute("DELETE FROM interaction_records")
                await db.commit()
                return count
            finally:
                await db.close()
        except Exception:
            return 0
    
    async def _delete_settings(self, user_id: str) -> bool:
        """Delete user settings."""
        try:
            # Reset settings.yaml to defaults
            settings_path = Path(__file__).parent.parent.parent / "settings.yaml"
            if settings_path.exists():
                import yaml
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = yaml.safe_load(f) or {}
                # Clear user-specific settings but keep system defaults
                for key in ["user_preferences", "custom_settings", "user_id"]:
                    settings.pop(key, None)
                with open(settings_path, "w", encoding="utf-8") as f:
                    yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception:
            return False
    
    async def _delete_journal(self, user_id: str) -> int:
        """Delete reflective journal entries from SQLite."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM reflective_journal")
                row = await cursor.fetchone()
                count = row[0] if row else 0
                
                await db.execute("DELETE FROM reflective_journal")
                await db.commit()
                return count
            finally:
                await db.close()
        except Exception:
            return 0
    
    async def _delete_skills(self, user_id: str) -> int:
        """Delete procedural memory skills from SQLite."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM procedural_skills")
                row = await cursor.fetchone()
                count = row[0] if row else 0
                
                await db.execute("DELETE FROM procedural_skills")
                await db.commit()
                return count
            finally:
                await db.close()
        except Exception:
            return 0
    
    # ── Count Methods ────────────────────────────────────────────
    
    async def _count_conversations(self, user_id: str) -> int:
        """Count conversation records."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM interaction_records")
                row = await cursor.fetchone()
                return row[0] if row else 0
            finally:
                await db.close()
        except Exception:
            return 0
    
    async def _count_journal(self, user_id: str) -> int:
        """Count journal entries."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM reflective_journal")
                row = await cursor.fetchone()
                return row[0] if row else 0
            finally:
                await db.close()
        except Exception:
            return 0
    
    async def _count_skills(self, user_id: str) -> int:
        """Count procedural skills."""
        try:
            db = await self._get_db()
            try:
                cursor = await db.execute("SELECT COUNT(*) FROM procedural_skills")
                row = await cursor.fetchone()
                return row[0] if row else 0
            finally:
                await db.close()
        except Exception:
            return 0
    
    async def _has_settings(self, user_id: str) -> bool:
        """Check if user settings exist."""
        try:
            settings_path = Path(__file__).parent.parent.parent / "settings.yaml"
            if settings_path.exists():
                import yaml
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = yaml.safe_load(f) or {}
                return len(settings) > 0
        except Exception:
            pass
        return False
    
    # ── Public API ───────────────────────────────────────────────
    
    async def export_user_data(self, user_id: str) -> dict:
        """Export all data associated with a user (GDPR Art. 20)."""
        exported = {
            "user_id": user_id,
            "export_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data_types": {},
        }
        
        # 1. Export conversations from SQLite
        conversations = await self._export_conversations(user_id)
        if conversations:
            exported["data_types"]["conversations"] = conversations
        
        # 2. Export settings/preferences
        settings = await self._export_settings(user_id)
        if settings:
            exported["data_types"]["settings"] = settings
        
        # 3. Export journal entries related to user
        journal = await self._export_journal(user_id)
        if journal:
            exported["data_types"]["journal"] = journal
        
        # 4. Export procedural memory skills
        skills = await self._export_skills(user_id)
        if skills:
            exported["data_types"]["skills"] = skills
        
        return exported
    
    async def delete_user_data(self, user_id: str, confirm: bool = False) -> dict:
        """Delete all data for a user (GDPR Art. 17 - Right to Erasure).
        
        Args:
            user_id: The user identifier to delete
            confirm: Must be True to actually perform deletion
            
        Returns:
            Summary of what was deleted
        """
        if not confirm:
            return {"status": "confirmation_required", "message": "يجب تأكيد الحذف"}
        
        deleted_items = {}
        
        # 1. Delete conversations
        conv_count = await self._delete_conversations(user_id)
        deleted_items["conversations"] = conv_count
        
        # 2. Delete settings
        settings_deleted = await self._delete_settings(user_id)
        deleted_items["settings"] = settings_deleted
        
        # 3. Delete journal entries
        journal_count = await self._delete_journal(user_id)
        deleted_items["journal"] = journal_count
        
        # 4. Delete from procedural memory
        skills_count = await self._delete_skills(user_id)
        deleted_items["skills"] = skills_count
        
        # 5. Register in deleted users registry
        self._register_deleted_user(user_id)
        
        return {
            "status": "deleted",
            "user_id": user_id,
            "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "items_deleted": deleted_items,
            "note": "تم تسجيل الحذف في سجل المستخدمين المحذوفين لمنع الاستعادة من النسخ الاحتياطية",
        }
    
    async def get_data_summary(self, user_id: str) -> dict:
        """Get a summary of data stored for a user (GDPR Art. 15)."""
        return {
            "user_id": user_id,
            "data_categories": {
                "conversations": {"count": await self._count_conversations(user_id), "purpose": "سجل المحادثات"},
                "settings": {"exists": await self._has_settings(user_id), "purpose": "تفضيلات المستخدم"},
                "journal": {"count": await self._count_journal(user_id), "purpose": "يوميات التفاعل"},
                "skills": {"count": await self._count_skills(user_id), "purpose": "مهارات مستخرجة"},
            },
            "retention_policy": {
                "conversations_days": 90,
                "personality_days": 365,
                "anonymous_stats": "indefinite",
            },
        }
    
    def is_user_deleted(self, user_id: str) -> bool:
        """Check if a user ID is in the deleted registry."""
        registry = self._load_registry()
        user_hash = self._hash_user_id(user_id)
        return user_hash in registry
    
    def _register_deleted_user(self, user_id: str):
        """Register a deleted user to prevent restoration from backups."""
        registry = self._load_registry()
        user_hash = self._hash_user_id(user_id)
        registry.append({
            "hash": user_hash,
            "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        self._save_registry(registry)
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash a user ID for pseudonymization."""
        return hashlib.sha256(f"babsharqii_{user_id}".encode()).hexdigest()[:16]
    
    def _load_registry(self) -> list:
        """Load the deleted users registry."""
        try:
            return json.loads(self.deleted_registry_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _save_registry(self, registry: list):
        """Save the deleted users registry."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.deleted_registry_path.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


# Singleton
data_manager = DataManager()
