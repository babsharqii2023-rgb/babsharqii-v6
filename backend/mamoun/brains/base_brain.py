"""
BABSHARQII v40.0 — Base Brain
Abstract base class for all 5 brains.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class BrainState:
    """Current state of a brain."""
    id: str = ""
    name: str = ""
    name_ar: str = ""
    status: str = "idle"  # idle, active, thinking, error
    confidence: float = 0.5
    latency_ms: float = 0.0
    weight: float = 0.2
    model: str = "glm-4-plus"
    temperature: float = 0.5
    total_interactions: int = 0
    successful_interactions: int = 0
    error_count: int = 0

    @property
    def arabic_name(self) -> str:
        """v36 FIX: Alias for name_ar for backward compatibility."""
        return self.name_ar

    @arabic_name.setter
    def arabic_name(self, value: str):
        self.name_ar = value
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_ar": self.name_ar,
            "status": self.status,
            "confidence": self.confidence,
            "latency_ms": round(self.latency_ms, 1),
            "weight": self.weight,
            "model": self.model,
            "temperature": self.temperature,
            "total_interactions": self.total_interactions,
            "successful_interactions": self.successful_interactions,
            "error_count": self.error_count,
        }


class BaseBrain(ABC):
    """Abstract base class for all brains in BABSHARQII."""
    
    def __init__(self, brain_id: str, name: str, name_ar: str, weight: float = 0.2):
        self.state = BrainState(
            id=brain_id, name=name, name_ar=name_ar, weight=weight
        )
        self._system_prompt = ""
    
    @abstractmethod
    async def think(self, input_text: str, context: dict = None) -> dict:
        """Process input and return a response."""
        pass
    
    @abstractmethod
    def get_specialty(self) -> str:
        """Return this brain's specialty description."""
        pass
    
    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt
    
    def activate(self):
        self.state.status = "active"
    
    def deactivate(self):
        self.state.status = "idle"
    
    def record_success(self, latency_ms: float = 0):
        self.state.total_interactions += 1
        self.state.successful_interactions += 1
        self.state.latency_ms = latency_ms
        # Update confidence using EMA
        self.state.confidence = 0.9 * self.state.confidence + 0.1 * 1.0
    
    def record_error(self, latency_ms: float = 0):
        self.state.total_interactions += 1
        self.state.error_count += 1
        self.state.latency_ms = latency_ms
        self.state.confidence = 0.9 * self.state.confidence + 0.1 * 0.0
