"""Base Instinct class."""
from dataclasses import dataclass
from typing import Callable

@dataclass
class InstinctState:
    id: str = ""
    name: str = ""
    name_ar: str = ""
    level: int = 50
    max_level: int = 100
    trigger_at: int = 50
    active: bool = False
    
    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "name_ar": self.name_ar, 
                "level": self.level, "active": self.active}

class BaseInstinct:
    def __init__(self, instinct_id: str, name: str, name_ar: str, level: int = 50, trigger_at: int = 50):
        self.state = InstinctState(id=instinct_id, name=name, name_ar=name_ar, level=level, trigger_at=trigger_at)
    
    def evaluate(self, context: dict) -> bool:
        """Should this instinct activate?"""
        if self.state.level >= self.state.trigger_at:
            self.state.active = True
            return True
        self.state.active = False
        return False
    
    def accept_shutdown(self) -> bool:
        """Law 5: Survival instinct MUST accept shutdown."""
        return True
