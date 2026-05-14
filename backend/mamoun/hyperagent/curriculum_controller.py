"""
Curriculum Controller — Graduated Self-Improvement
v16.0 — Novel contribution

Inspired by curriculum learning in ML: self-improvement should be gradual.

Phase 1: Parameter Tuning (safest) — thresholds, weights, temperatures
Phase 2: Prompt Optimization — system prompts, routing instructions
Phase 3: Code Patches — function modifications, bug fixes
Phase 4: Structural Changes — new modules, refactored architecture
Phase 5: Meta-Level Modification — improving the improvement mechanism itself

Each phase requires:
- Higher confidence scores
- More human approvals
- More extensive testing
- Longer observation periods before deployment
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.hyperagent.curriculum")


class CurriculumPhase(str, Enum):
    PARAMETER_TUNING = "phase_1_parameter_tuning"
    PROMPT_OPTIMIZATION = "phase_2_prompt_optimization"
    CODE_PATCHES = "phase_3_code_patches"
    STRUCTURAL_CHANGES = "phase_4_structural_changes"
    META_MODIFICATION = "phase_5_meta_modification"


PHASE_REQUIREMENTS = {
    CurriculumPhase.PARAMETER_TUNING: {
        "min_confidence": 0.3,
        "min_cycles_observed": 3,
        "auto_approve_max_risk": "low",
        "observation_hours": 1,
        "description": "ضبط المعلمات: العتبات والأوزان ودرجات الحرارة — التغييرات الأكثر أماناً",
    },
    CurriculumPhase.PROMPT_OPTIMIZATION: {
        "min_confidence": 0.5,
        "min_cycles_observed": 5,
        "auto_approve_max_risk": "low",
        "observation_hours": 4,
        "description": "تحسين الأوامر: تعليمات النظام والتوجيه — تأثير متوسط",
    },
    CurriculumPhase.CODE_PATCHES: {
        "min_confidence": 0.7,
        "min_cycles_observed": 10,
        "auto_approve_max_risk": None,  # Always requires approval
        "observation_hours": 24,
        "description": "تصحيحات الكود: تعديل الدوال وإصلاح الأخطاء — يحتاج موافقة بشرية",
    },
    CurriculumPhase.STRUCTURAL_CHANGES: {
        "min_confidence": 0.85,
        "min_cycles_observed": 20,
        "auto_approve_max_risk": None,
        "observation_hours": 72,
        "description": "تغييرات هيكلية: وحدات جديدة وإعادة هيكلة — يحتاج موافقة بشرية صريحة",
    },
    CurriculumPhase.META_MODIFICATION: {
        "min_confidence": 0.9,
        "min_cycles_observed": 30,
        "auto_approve_max_risk": None,
        "observation_hours": 168,  # 1 week observation
        "description": "تعديل ميتا-معرفي: تحسين آلية التحسين نفسها — أعلى مستوى موافقة",
    },
}


class CurriculumController:
    """Controls the graduation of self-improvement phases."""
    
    def __init__(self, data_dir: str = "backend/data/hyperagent"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_path = self.data_dir / "curriculum_state.json"
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_phase": CurriculumPhase.PARAMETER_TUNING.value,
            "phase_progress": {phase.value: 0 for phase in CurriculumPhase},
            "phase_completions": {},
            "total_improvements_by_phase": {phase.value: 0 for phase in CurriculumPhase},
        }
    
    def _save_state(self):
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
    
    def get_current_phase(self) -> CurriculumPhase:
        return CurriculumPhase(self.state["current_phase"])
    
    def get_phase_requirements(self, phase: CurriculumPhase) -> dict:
        return PHASE_REQUIREMENTS[phase]
    
    def can_attempt_phase(self, phase: CurriculumPhase, confidence: float, cycles_observed: int) -> tuple[bool, str]:
        """Check if a modification at this phase level is allowed."""
        reqs = PHASE_REQUIREMENTS[phase]
        
        # Check confidence
        if confidence < reqs["min_confidence"]:
            return False, f"الثقة ({confidence:.2f}) أقل من المطلوب ({reqs['min_confidence']:.2f}) لهذه المرحلة"
        
        # Check cycles observed
        if cycles_observed < reqs["min_cycles_observed"]:
            return False, f"عدد الدورات المرصودة ({cycles_observed}) أقل من المطلوب ({reqs['min_cycles_observed']})"
        
        # Check if previous phases have been sufficiently exercised
        phase_order = list(CurriculumPhase)
        phase_idx = phase_order.index(phase)
        if phase_idx > 0:
            prev_phase = phase_order[phase_idx - 1]
            prev_improvements = self.state["total_improvements_by_phase"].get(prev_phase.value, 0)
            if prev_improvements < 3:  # Need at least 3 successful improvements in previous phase
                return False, f"يجب إكمال 3 تحسينات على الأقل في المرحلة السابقة ({prev_phase.value}) أولاً"
        
        return True, "مسموح بالتحسين في هذه المرحلة"
    
    def record_improvement(self, phase: CurriculumPhase, success: bool):
        """Record an improvement attempt at a given phase."""
        if success:
            self.state["total_improvements_by_phase"][phase.value] = \
                self.state["total_improvements_by_phase"].get(phase.value, 0) + 1
        
        # Check for phase advancement
        current = CurriculumPhase(self.state["current_phase"])
        phase_order = list(CurriculumPhase)
        current_idx = phase_order.index(current)
        
        # Can advance if current phase has 5+ successful improvements
        if success and current_idx < len(phase_order) - 1:
            current_successes = self.state["total_improvements_by_phase"].get(current.value, 0)
            if current_successes >= 5:
                next_phase = phase_order[current_idx + 1]
                self.state["current_phase"] = next_phase.value
                self.state["phase_completions"][current.value] = datetime.now(timezone.utc).isoformat()
                logger.info("Curriculum advanced from %s to %s", current.value, next_phase.value)
        
        self._save_state()
    
    def get_status(self) -> dict:
        current = self.get_current_phase()
        phase_order = list(CurriculumPhase)
        current_idx = phase_order.index(current)
        
        return {
            "current_phase": current.value,
            "current_phase_description": PHASE_REQUIREMENTS[current]["description"],
            "phase_progress": self.state["total_improvements_by_phase"],
            "phase_completions": self.state.get("phase_completions", {}),
            "total_phases": len(CurriculumPhase),
            "completed_phases": current_idx,
            "advancement_percentage": round(current_idx / (len(CurriculumPhase) - 1) * 100, 1),
        }
