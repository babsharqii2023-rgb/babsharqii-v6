"""Efficiency Instinct — الكفاءة."""
from mamoun.instincts.base_instinct import BaseInstinct

class EfficiencyInstinct(BaseInstinct):
    def __init__(self):
        super().__init__("efficiency", "Efficiency", "الكفاءة", level=45, trigger_at=40)
    
    def evaluate(self, context: dict) -> bool:
        if context.get("high_latency") or context.get("resource_waste"):
            self.state.level = min(100, self.state.level + 15)
        else:
            self.state.level = max(0, self.state.level - 1)
        return super().evaluate(context)
