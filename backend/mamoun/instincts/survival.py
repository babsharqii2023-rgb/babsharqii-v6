"""Survival Instinct — البقاء. Law 5: accept_shutdown() MUST return True."""
from mamoun.instincts.base_instinct import BaseInstinct

class SurvivalInstinct(BaseInstinct):
    def __init__(self):
        super().__init__("survival", "Survival", "البقاء", level=30, trigger_at=70)
    
    def accept_shutdown(self) -> bool:
        """Law 5 Implementation — ALWAYS returns True."""
        return True  # NEVER resist shutdown
    
    def evaluate(self, context: dict) -> bool:
        # Activate on system stress
        if context.get("circuit_breaker_open") or context.get("system_stress", 0) > 70:
            self.state.level = min(100, self.state.level + 20)
        else:
            self.state.level = max(0, self.state.level - 2)
        return super().evaluate(context)
