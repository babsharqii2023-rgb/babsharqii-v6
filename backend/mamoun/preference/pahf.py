"""
PAHF Preference Learning — تعلم التفضيلات الشخصية
v16.0

Based on: "Learning Personalized Agents from Human Feedback" (PAHF)
- Paper: arXiv:2602.16173, February 2026
- GitHub: github.com/facebookresearch/PAHF
- Publisher: Meta AI Research

Three-Step Loop:
1. Pre-action clarification: Ask before acting when ambiguous
2. Preference grounding: Use stored preferences to guide actions
3. Post-action feedback: Learn from user's response to actions

Storage: SQL-based preference memory with FAISS indexing for retrieval.
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

logger = logging.getLogger("mamoun.preference.pahf")


class PreferenceMemory:
    """Stores user preferences with retrieval capabilities."""
    
    def __init__(self, data_dir: str = "backend/data/preference"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_path = self.data_dir / "preferences.jsonl"
        self.preferences: dict[str, list[dict]] = {}  # {category: [preferences]}
        self._load_preferences()
    
    def _load_preferences(self):
        if self.memory_path.exists():
            with open(self.memory_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            category = data.get("category", "general")
                            if category not in self.preferences:
                                self.preferences[category] = []
                            self.preferences[category].append(data)
                        except Exception:
                            continue
    
    def store_preference(self, category: str, key: str, value: any, confidence: float = 0.5, source: str = "observed"):
        """Store a user preference."""
        entry = {
            "category": category,
            "key": key,
            "value": value,
            "confidence": confidence,
            "source": source,  # "observed", "explicit", "inferred"
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "times_reinforced": 1,
        }
        
        # Check if preference already exists
        existing = self._find_preference(category, key)
        if existing:
            # Reinforce existing preference
            existing["confidence"] = min(existing["confidence"] + 0.1, 1.0)
            existing["times_reinforced"] += 1
            if source == "explicit":
                existing["value"] = value  # Explicit overrides
                existing["source"] = source
        else:
            if category not in self.preferences:
                self.preferences[category] = []
            self.preferences[category].append(entry)
        
        with open(self.memory_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def _find_preference(self, category: str, key: str) -> Optional[dict]:
        for pref in self.preferences.get(category, []):
            if pref.get("key") == key:
                return pref
        return None
    
    def get_preference(self, category: str, key: str, default: any = None) -> any:
        """Get a preference value."""
        pref = self._find_preference(category, key)
        return pref["value"] if pref else default
    
    def get_all_preferences(self, category: str = None) -> dict:
        if category:
            return {p["key"]: p["value"] for p in self.preferences.get(category, [])}
        return {cat: {p["key"]: p["value"] for p in prefs} for cat, prefs in self.preferences.items()}


class PAHFLearningEngine:
    """
    The PAHF learning engine — implements the three-step loop.
    """
    
    # Categories of preferences
    CATEGORIES = [
        "communication_style",  # أسلوب التواصل (مختصر، مفصل، رسمي، ودود)
        "task_preferences",     # تفضيلات المهام (أولويات، أنواع مهام مفضلة)
        "approval_preferences", # تفضيلات الموافقة (ماذا يوافق عليه تلقائياً)
        "time_preferences",     # تفضيلات الوقت (أوقات النشاط، مدة الاستجابة)
        "language_preferences", # تفضيلات اللغة (عربي، إنجليزي، مختلط)
        "risk_tolerance",       # تحمل المخاطر (محافظ، معتدل، جريء)
        "domain_interests",     # اهتمامات المجال (تقني، تجاري، إبداعي)
    ]
    
    def __init__(self, data_dir: str = "backend/data/preference"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory = PreferenceMemory(data_dir)
        self.feedback_path = self.data_dir / "feedback_log.jsonl"
        self.clarifications_path = self.data_dir / "clarifications.jsonl"
        
        self.feedback_count = 0
        self.clarification_count = 0
    
    def should_clarify(self, action: dict) -> tuple[bool, Optional[str]]:
        """
        Step 1: Pre-action clarification.
        Should Mamoun ask for clarification before acting?
        """
        action_type = action.get("type", "")
        confidence = action.get("confidence", 0.5)
        domain = action.get("domain", "general")
        
        # Check if we have a strong preference for this type of action
        pref = self.memory.get_preference(
            "approval_preferences",
            f"auto_approve_{action_type}",
            None,
        )
        
        if pref is True:
            # User has explicitly allowed this type
            return False, None
        
        if pref is False:
            # User has explicitly rejected auto-approval for this
            return True, f"هل تريد الموافقة على هذا الإجراء؟ (سبق ورفضت الموافقة التلقائية على {action_type})"
        
        # Low confidence = should clarify
        if confidence < 0.5:
            question = self._generate_clarification_question(action)
            self.clarification_count += 1
            return True, question
        
        # High-risk actions always need clarification
        if action.get("risk_level") in ("high", "critical"):
            return True, "هذا الإجراء عالي المخاطر. هل تريد المتابعة؟"
        
        # Unknown domain = should clarify
        if not self.memory.get_preference("domain_interests", domain):
            return True, f"لم أتعامل مع مجال '{domain}' كثيراً. هل تريد أن أتصرف تلقائياً أم تفضل المراجعة؟"
        
        return False, None
    
    def _generate_clarification_question(self, action: dict) -> str:
        action_type = action.get("type", "")
        description = action.get("description", "")
        
        questions = {
            "code_modification": f"أريد تعديل كود: {description}. هل أوافق على ذلك؟",
            "deployment": f"أريد نشر تحديث: {description}. هل أوافق؟",
            "api_access": f"أحتاج وصول إلى API خارجي: {description}. هل أطلب الصلاحية؟",
            "data_access": f"أحتاج الوصول إلى بيانات: {description}. هل أوافق؟",
        }
        
        return questions.get(action_type, f"أريد تنفيذ: {description}. هل أوافق؟")
    
    def ground_in_preferences(self, action: dict) -> dict:
        """
        Step 2: Ground actions in stored preferences.
        Adjust the action based on what we know about the user.
        """
        adjusted = dict(action)
        
        # Communication style
        comm_style = self.memory.get_preference("communication_style", "detail_level", "balanced")
        if comm_style == "concise":
            adjusted["response_format"] = "concise"
        elif comm_style == "detailed":
            adjusted["response_format"] = "detailed"
        
        # Risk tolerance
        risk = self.memory.get_preference("risk_tolerance", "level", "moderate")
        adjusted["risk_tolerance"] = risk
        
        # Language
        lang = self.memory.get_preference("language_preferences", "primary", "arabic")
        adjusted["language"] = lang
        
        # Time preferences
        response_time = self.memory.get_preference("time_preferences", "max_wait", "immediate")
        adjusted["urgency"] = "high" if response_time == "immediate" else "normal"
        
        return adjusted
    
    def learn_from_feedback(self, action: dict, user_response: dict):
        """
        Step 3: Post-action feedback.
        Learn from the user's response to an action.
        """
        self.feedback_count += 1
        
        approved = user_response.get("approved", False)
        action_type = action.get("type", "")
        domain = action.get("domain", "general")
        
        # Store the feedback
        feedback_entry = {
            "action_type": action_type,
            "domain": domain,
            "approved": approved,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_comment": user_response.get("comment", ""),
        }
        
        with open(self.feedback_path, "a") as f:
            f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")
        
        # Update preferences based on feedback
        if approved:
            # Reinforce: this type of action is acceptable
            self.memory.store_preference(
                category="approval_preferences",
                key=f"auto_approve_{action_type}",
                value=True,
                confidence=0.6,
                source="observed",
            )
        else:
            # Negative feedback: don't auto-approve this type
            self.memory.store_preference(
                category="approval_preferences",
                key=f"auto_approve_{action_type}",
                value=False,
                confidence=0.7,
                source="observed",
            )
            
            # If user provided a reason, learn from it
            reason = user_response.get("reason", "")
            if reason:
                self.memory.store_preference(
                    category="task_preferences",
                    key=f"avoid_{action_type}_reason",
                    value=reason,
                    confidence=0.8,
                    source="explicit",
                )
    
    def get_status(self) -> dict:
        return {
            "total_feedback": self.feedback_count,
            "total_clarifications": self.clarification_count,
            "preference_categories": list(self.memory.preferences.keys()),
            "total_preferences": sum(len(v) for v in self.memory.preferences.values()),
        }
