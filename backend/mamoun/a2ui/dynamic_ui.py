"""
A2UI Dynamic UI System — توليد واجهات ديناميكية
v16.0

Based on: A2UI (Agent-to-User Interface) by Google
- Specification: a2ui.org/specification/v0.8-a2ui
- GitHub: github.com/google/a2ui
- "Generative UI allows AI agents to generate tailored UI widgets in real-time"

How A2UI works:
1. Agent generates A2UI messages describing UI (structure + data) as JSON
2. Messages stream to client application as JSONL
3. Client renders using native components (React, Angular, etc.)
4. No executable code — declarative JSON format (secure by design)

Complementary: AG-UI Protocol (CopilotKit)
- github.com/ag-ui-protocol/ag-ui
- 17 event types for real-time agent-UI interaction
- HTTP + SSE + webhooks for streaming
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.a2ui.dynamic_ui")


class UIComponentType(str, Enum):
    """A2UI component types — the building blocks."""
    TEXT = "text"
    HEADING = "heading"
    BUTTON = "button"
    CARD = "card"
    TABLE = "table"
    FORM = "form"
    INPUT = "input"
    SELECT = "select"
    CHART = "chart"
    LIST = "list"
    NOTIFICATION = "notification"
    MODAL = "modal"
    TABS = "tabs"
    PROGRESS = "progress"
    BADGE = "badge"
    SECTION = "section"  # Container for other components


class A2UIMessage:
    """
    A single A2UI message — follows the A2UI v0.8 specification.
    
    Format: JSONL (JSON Lines) for streaming.
    Each message has: type, component, data, metadata
    """
    
    def __init__(
        self,
        component_type: UIComponentType,
        component_id: str,
        data: dict,
        action: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ):
        self.message_type = "a2ui"
        self.component_type = component_type
        self.component_id = component_id
        self.data = data
        self.action = action  # What happens when user interacts
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_jsonl(self) -> str:
        """Convert to JSONL format for streaming."""
        msg = {
            "type": self.message_type,
            "component": self.component_type.value,
            "id": self.component_id,
            "data": self.data,
            "action": self.action,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
        return json.dumps(msg, ensure_ascii=False)


class DynamicUIGenerator:
    """
    Generates dynamic UI components for the dashboard.
    
    Mamoun can create new sections, cards, buttons, forms, etc.
    without writing React code — just A2UI JSON messages.
    """
    
    def __init__(self, data_dir: str = "backend/data/a2ui"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates_path = self.data_dir / "ui_templates.jsonl"
        self.history_path = self.data_dir / "generated_ui_history.jsonl"
        
        self.registered_templates: dict[str, list[A2UIMessage]] = {}
    
    def generate_task_section(self, section_name: str, section_type: str, fields: list[dict]) -> list[A2UIMessage]:
        """
        Generate a complete task section with A2UI messages.
        
        Args:
            section_name: Display name (Arabic)
            section_type: Category (technical, customer_service, market_analysis, etc.)
            fields: List of field definitions [{name, type, required, options}]
        """
        messages = []
        
        # 1. Section container
        messages.append(A2UIMessage(
            component_type=UIComponentType.SECTION,
            component_id=f"section_{section_type}",
            data={
                "title": section_name,
                "type": section_type,
                "collapsible": True,
                "icon": self._get_section_icon(section_type),
            },
        ))
        
        # 2. Header with stats
        messages.append(A2UIMessage(
            component_type=UIComponentType.CARD,
            component_id=f"section_{section_type}_stats",
            data={
                "title": f"إحصائيات {section_name}",
                "metrics": [
                    {"label": "إجمالي المهام", "value": 0, "color": "slate"},
                    {"label": "قيد التنفيذ", "value": 0, "color": "amber"},
                    {"label": "مكتملة", "value": 0, "color": "blue"},
                ],
            },
        ))
        
        # 3. Add task button
        messages.append(A2UIMessage(
            component_type=UIComponentType.BUTTON,
            component_id=f"section_{section_type}_add",
            data={
                "label": f"إضافة مهمة {section_name}",
                "variant": "outline",
                "icon": "plus",
            },
            action={
                "type": "open_modal",
                "modal_id": f"modal_add_task_{section_type}",
            },
        ))
        
        # 4. Add task form (in modal)
        form_fields = []
        for field in fields:
            if field.get("type") == "select":
                messages.append(A2UIMessage(
                    component_type=UIComponentType.SELECT,
                    component_id=f"form_{section_type}_{field['name']}",
                    data={
                        "label": field.get("label", field["name"]),
                        "options": field.get("options", []),
                        "required": field.get("required", False),
                    },
                ))
            else:
                messages.append(A2UIMessage(
                    component_type=UIComponentType.INPUT,
                    component_id=f"form_{section_type}_{field['name']}",
                    data={
                        "label": field.get("label", field["name"]),
                        "type": field.get("type", "text"),
                        "placeholder": field.get("placeholder", ""),
                        "required": field.get("required", False),
                    },
                ))
        
        # Save template
        self.registered_templates[section_type] = messages
        self._save_template(section_type, messages)
        
        return messages
    
    def generate_permission_request(self, request: dict) -> list[A2UIMessage]:
        """Generate a permission request UI."""
        messages = []
        
        messages.append(A2UIMessage(
            component_type=UIComponentType.NOTIFICATION,
            component_id=f"perm_{request.get('id', int(time.time()))}",
            data={
                "title": "طلب صلاحية جديد",
                "description": request.get("description", ""),
                "risk_level": request.get("risk_level", "low"),
                "requested_by": "مأمون",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            action={
                "type": "dual_buttons",
                "approve": {"label": "موافقة", "variant": "default"},
                "reject": {"label": "رفض", "variant": "destructive"},
            },
        ))
        
        return messages
    
    def generate_evolution_status(self, status: dict) -> list[A2UIMessage]:
        """Generate evolution status UI."""
        messages = []
        
        messages.append(A2UIMessage(
            component_type=UIComponentType.CARD,
            component_id="evolution_status",
            data={
                "title": "حالة التطور الذاتي",
                "phase": status.get("current_phase", ""),
                "cycle": status.get("cycle_count", 0),
                "progress": status.get("advancement_percentage", 0),
                "improvements": status.get("total_improvements", 0),
            },
        ))
        
        messages.append(A2UIMessage(
            component_type=UIComponentType.PROGRESS,
            component_id="evolution_progress",
            data={
                "value": status.get("advancement_percentage", 0),
                "max": 100,
                "label": "تقدم مراحل التطور",
                "variant": "gradient",
            },
        ))
        
        return messages
    
    def _get_section_icon(self, section_type: str) -> str:
        icons = {
            "technical": "cpu",
            "customer_service": "headphones",
            "market_analysis": "trending-up",
            "location": "map-pin",
            "workflow": "git-branch",
            "new_task": "sparkles",
            "research": "book-open",
            "deployment": "rocket",
        }
        return icons.get(section_type, "folder")
    
    def _save_template(self, template_name: str, messages: list[A2UIMessage]):
        with open(self.templates_path, "a") as f:
            for msg in messages:
                f.write(json.dumps({
                    "template": template_name,
                    "message": msg.to_jsonl(),
                }, ensure_ascii=False) + "\n")
    
    def get_status(self) -> dict:
        return {
            "registered_templates": len(self.registered_templates),
            "template_names": list(self.registered_templates.keys()),
        }
