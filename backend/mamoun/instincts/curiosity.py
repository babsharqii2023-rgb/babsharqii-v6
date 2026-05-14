"""Curiosity Instinct — الفضول."""
from mamoun.instincts.base_instinct import BaseInstinct

class CuriosityInstinct(BaseInstinct):
    def __init__(self):
        super().__init__("curiosity", "Curiosity", "الفضول", level=65, trigger_at=30)
    
    def evaluate(self, context: dict) -> bool:
        if context.get("knowledge_gap") or context.get("novel_input"):
            self.state.level = min(100, self.state.level + 15)
        else:
            self.state.level = max(0, self.state.level - 1)
        return super().evaluate(context)
