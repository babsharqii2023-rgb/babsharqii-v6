"""Consistency Instinct — الاتساق."""
from mamoun.instincts.base_instinct import BaseInstinct

class ConsistencyInstinct(BaseInstinct):
    def __init__(self):
        super().__init__("consistency", "Consistency", "الاتساق", level=50, trigger_at=50)
    
    def evaluate(self, context: dict) -> bool:
        if context.get("belief_conflict") or context.get("contradiction"):
            self.state.level = min(100, self.state.level + 20)
        else:
            self.state.level = max(0, self.state.level - 1)
        return super().evaluate(context)
