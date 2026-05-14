"""
BABSHARQII v20.0 — Dashboard Builder Engine (محرك بناء الداشبورد)
المحرك الذي ينقل مأمون من 20% إلى 95%+ في قدرة تعديل الداشبورد

هذا المحرك يمكّن النظام من:
  1. إنشاء تخطيطات داشبورد ديناميكياً
  2. إضافة/إزالة/تحديث الودجات
  3. توليد كود React تلقائياً
  4. تطبيق تخطيطات مسبقة (presets)
  5. تصدير/استيراد التخطيطات كـ JSON
  6. جلب بيانات الودجات من محركات API

الودجات المدعومة:
  CHART              — رسوم بيانية (خطي، شريطي، دائري)
  STAT_CARD          — بطاقة إحصائية (رقم + عنوان + اتجاه)
  TIMELINE           — خط زمني للأحداث
  TABLE              — جدول بيانات
  NOTIFICATION_PANEL — لوحة إشعارات
  CUSTOM             — ودجة مخصصة

التخطيطات المسبقة:
  overview     — داشبورد رئيسي بإحصائيات + نشاط + إشعارات
  developer    — مركزي حول الكود (طرفية + ملفات + حالة git)
  consciousness — عرض محركات v19
  analytics    — رسوم بيانية + تنبؤات + مقاييس دقة
"""

import time
import json
import uuid
import logging
import sqlite3
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger("mamoun.core.dashboard_builder")


# ═══════════════════════════════════════════════════════════════════════════════
# أنواع الودجات — Widget Types
# ═══════════════════════════════════════════════════════════════════════════════

class WidgetType(str, Enum):
    """أنواع الودجات المدعومة"""
    CHART = "chart"
    STAT_CARD = "stat_card"
    TIMELINE = "timeline"
    TABLE = "table"
    NOTIFICATION_PANEL = "notification_panel"
    CUSTOM = "custom"


# ═══════════════════════════════════════════════════════════════════════════════
# نماذج البيانات — Data Models
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WidgetConfig:
    """إعدادات الودجة — موقع، نوع، بيانات"""
    id: str = ""
    type: WidgetType = WidgetType.STAT_CARD
    title: str = ""
    title_ar: str = ""
    position: dict = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 3})
    data_source: str = ""
    refresh_interval: int = 30       # ثانية
    props: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "title_ar": self.title_ar,
            "position": self.position,
            "data_source": self.data_source,
            "refresh_interval": self.refresh_interval,
            "props": self.props,
        }

    def validate(self) -> List[str]:
        """التحقق من صحة إعدادات الودجة — يُرجع قائمة الأخطاء"""
        errors = []
        if not self.id:
            errors.append("معرف الودجة مطلوب")
        if not self.title and not self.title_ar:
            errors.append("عنوان الودجة مطلوب (عربي أو إنجليزي)")
        pos = self.position
        if not isinstance(pos, dict):
            errors.append("الموقع يجب أن يكون قاموساً")
        else:
            for key in ("x", "y", "w", "h"):
                if key not in pos:
                    errors.append(f"المفتاح '{key}' مطلوب في الموقع")
                elif not isinstance(pos[key], (int, float)):
                    errors.append(f"قيمة '{key}' يجب أن تكون رقماً")
            if "w" in pos and pos["w"] < 1:
                errors.append("عرض الودجة يجب أن يكون ≥ 1")
            if "h" in pos and pos["h"] < 1:
                errors.append("ارتفاع الودجة يجب أن يكون ≥ 1")
        if self.refresh_interval < 0:
            errors.append("فترة التحديث يجب أن تكون ≥ 0")
        return errors


@dataclass
class DashboardLayout:
    """تخطيط الداشبورد — مجموعة ودجات مع معلومات"""
    id: str = ""
    name: str = ""
    description: str = ""
    widgets: List[WidgetConfig] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "widget_count": len(self.widgets),
            "widgets": [w.to_dict() for w in self.widgets],
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat() if self.created_at else "",
            "updated_at": self.updated_at,
            "updated_at_iso": datetime.fromtimestamp(self.updated_at).isoformat() if self.updated_at else "",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# التخطيطات المسبقة — Preset Layouts
# ═══════════════════════════════════════════════════════════════════════════════

PRESET_LAYOUTS: Dict[str, dict] = {
    "overview": {
        "name": "نظرة عامة",
        "description": "الداشبورد الرئيسي — إحصائيات، نشاط حديث، إشعارات",
        "widgets": [
            {"type": "stat_card", "title": "System Health", "title_ar": "صحة النظام",
             "position": {"x": 0, "y": 0, "w": 3, "h": 2},
             "data_source": "/api/health", "refresh_interval": 10,
             "props": {"icon": "activity", "color": "#4A6FA5"}},
            {"type": "stat_card", "title": "Active Brains", "title_ar": "الأدمغة النشطة",
             "position": {"x": 3, "y": 0, "w": 3, "h": 2},
             "data_source": "/api/brains/status", "refresh_interval": 15,
             "props": {"icon": "brain", "color": "#C0C0C0"}},
            {"type": "stat_card", "title": "Confidence", "title_ar": "مستوى الثقة",
             "position": {"x": 6, "y": 0, "w": 3, "h": 2},
             "data_source": "/api/health", "refresh_interval": 15,
             "props": {"icon": "gauge", "color": "#8A8A8A"}},
            {"type": "stat_card", "title": "Response Time", "title_ar": "زمن الاستجابة",
             "position": {"x": 9, "y": 0, "w": 3, "h": 2},
             "data_source": "/api/health", "refresh_interval": 10,
             "props": {"icon": "clock", "color": "#4A6FA5"}},
            {"type": "chart", "title": "Activity Trend", "title_ar": "اتجاه النشاط",
             "position": {"x": 0, "y": 2, "w": 6, "h": 4},
             "data_source": "/api/activity/trend", "refresh_interval": 30,
             "props": {"chart_type": "line", "color": "#4A6FA5"}},
            {"type": "notification_panel", "title": "Recent Notifications", "title_ar": "الإشعارات الحديثة",
             "position": {"x": 6, "y": 2, "w": 6, "h": 4},
             "data_source": "/api/notifications", "refresh_interval": 15,
             "props": {"max_items": 10}},
            {"type": "timeline", "title": "Recent Activity", "title_ar": "النشاط الحديث",
             "position": {"x": 0, "y": 6, "w": 12, "h": 3},
             "data_source": "/api/activity/recent", "refresh_interval": 30,
             "props": {"max_items": 20}},
        ],
    },
    "developer": {
        "name": "المطور",
        "description": "مركزي حول الكود — طرفية، ملفات، حالة git",
        "widgets": [
            {"type": "custom", "title": "Terminal", "title_ar": "الطرفية",
             "position": {"x": 0, "y": 0, "w": 8, "h": 6},
             "data_source": "/api/terminal", "refresh_interval": 0,
             "props": {"component": "LiveTerminal", "theme": "mamoun-dark"}},
            {"type": "table", "title": "Files", "title_ar": "الملفات",
             "position": {"x": 8, "y": 0, "w": 4, "h": 6},
             "data_source": "/api/files/list", "refresh_interval": 30,
             "props": {"columns": ["name", "size", "modified"], "sortable": True}},
            {"type": "stat_card", "title": "Git Status", "title_ar": "حالة Git",
             "position": {"x": 0, "y": 6, "w": 4, "h": 2},
             "data_source": "/api/git/status", "refresh_interval": 30,
             "props": {"icon": "git-branch", "color": "#C0C0C0"}},
            {"type": "stat_card", "title": "Build Status", "title_ar": "حالة البناء",
             "position": {"x": 4, "y": 6, "w": 4, "h": 2},
             "data_source": "/api/build/status", "refresh_interval": 60,
             "props": {"icon": "package", "color": "#4A6FA5"}},
            {"type": "notification_panel", "title": "Build Output", "title_ar": "مخرجات البناء",
             "position": {"x": 8, "y": 6, "w": 4, "h": 2},
             "data_source": "/api/build/output", "refresh_interval": 10,
             "props": {"max_items": 50}},
        ],
    },
    "consciousness": {
        "name": "الوعي",
        "description": "عرض محركات v19 — الأدمغة، الذاكرة، التأمل الذاتي",
        "widgets": [
            {"type": "custom", "title": "Brain Orbs", "title_ar": "كرات الأدمغة",
             "position": {"x": 0, "y": 0, "w": 6, "h": 5},
             "data_source": "/api/brains/status", "refresh_interval": 5,
             "props": {"component": "BrainOrbs", "animated": True}},
            {"type": "chart", "title": "Memory Usage", "title_ar": "استخدام الذاكرة",
             "position": {"x": 6, "y": 0, "w": 6, "h": 3},
             "data_source": "/api/memory/stats", "refresh_interval": 30,
             "props": {"chart_type": "area", "color": "#4A6FA5"}},
            {"type": "chart", "title": "Confidence Over Time", "title_ar": "الثقة عبر الزمن",
             "position": {"x": 6, "y": 3, "w": 6, "h": 2},
             "data_source": "/api/confidence/trend", "refresh_interval": 30,
             "props": {"chart_type": "line", "color": "#C0C0C0"}},
            {"type": "timeline", "title": "Self-Reflection Log", "title_ar": "سجل التأمل الذاتي",
             "position": {"x": 0, "y": 5, "w": 6, "h": 3},
             "data_source": "/api/reflection/log", "refresh_interval": 60,
             "props": {"max_items": 30}},
            {"type": "stat_card", "title": "Autonomy Level", "title_ar": "مستوى الاستقلالية",
             "position": {"x": 6, "y": 5, "w": 3, "h": 2},
             "data_source": "/api/autonomy/status", "refresh_interval": 30,
             "props": {"icon": "zap", "color": "#8A8A8A"}},
            {"type": "stat_card", "title": "Learning Rate", "title_ar": "معدل التعلم",
             "position": {"x": 9, "y": 5, "w": 3, "h": 2},
             "data_source": "/api/learning/status", "refresh_interval": 60,
             "props": {"icon": "trending-up", "color": "#4A6FA5"}},
        ],
    },
    "analytics": {
        "name": "التحليلات",
        "description": "رسوم بيانية، تنبؤات، مقاييس دقة",
        "widgets": [
            {"type": "chart", "title": "Prediction Accuracy", "title_ar": "دقة التنبؤ",
             "position": {"x": 0, "y": 0, "w": 6, "h": 4},
             "data_source": "/api/analytics/accuracy", "refresh_interval": 60,
             "props": {"chart_type": "line", "color": "#4A6FA5", "show_target": True}},
            {"type": "chart", "title": "Response Distribution", "title_ar": "توزيع الاستجابات",
             "position": {"x": 6, "y": 0, "w": 6, "h": 4},
             "data_source": "/api/analytics/distribution", "refresh_interval": 60,
             "props": {"chart_type": "bar", "color": "#C0C0C0"}},
            {"type": "stat_card", "title": "Avg Accuracy", "title_ar": "متوسط الدقة",
             "position": {"x": 0, "y": 4, "w": 3, "h": 2},
             "data_source": "/api/analytics/accuracy", "refresh_interval": 60,
             "props": {"icon": "target", "color": "#4A6FA5", "format": "percentage"}},
            {"type": "stat_card", "title": "Total Predictions", "title_ar": "إجمالي التنبؤات",
             "position": {"x": 3, "y": 4, "w": 3, "h": 2},
             "data_source": "/api/analytics/count", "refresh_interval": 60,
             "props": {"icon": "hash", "color": "#8A8A8A"}},
            {"type": "stat_card", "title": "RLHF Score", "title_ar": "درجة RLHF",
             "position": {"x": 6, "y": 4, "w": 3, "h": 2},
             "data_source": "/api/rlhf/status", "refresh_interval": 60,
             "props": {"icon": "star", "color": "#C0C0C0"}},
            {"type": "stat_card", "title": "Error Rate", "title_ar": "معدل الأخطاء",
             "position": {"x": 9, "y": 4, "w": 3, "h": 2},
             "data_source": "/api/analytics/errors", "refresh_interval": 60,
             "props": {"icon": "alert-triangle", "color": "#8A8A8A"}},
            {"type": "table", "title": "Model Comparison", "title_ar": "مقارنة النماذج",
             "position": {"x": 0, "y": 6, "w": 12, "h": 4},
             "data_source": "/api/brains/comparison", "refresh_interval": 120,
             "props": {"columns": ["model", "accuracy", "latency", "confidence"],
                       "sortable": True, "filterable": True}},
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# محرك بناء الداشبورد — DashboardBuilderEngine
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardBuilderEngine:
    """
    محرك بناء الداشبورد — إنشاء وتعديل وتوليد الداشبوردات

    المسؤوليات:
    1. إدارة تخطيطات الداشبورد (إنشاء، قراءة، تحديث، حذف)
    2. توليد كود React للمكونات ديناميكياً
    3. التحقق من صحة إعدادات الودجات
    4. تطبيق تخطيطات مسبقة
    5. تصدير/استيراد التخطيطات
    6. جلب بيانات الودجات

    الاستخدام:
        engine = DashboardBuilderEngine()
        engine.initialize()
        layout = engine.create_layout("لوحتي", "وصف مخصص")
        widget = engine.add_widget(layout["id"], "stat_card", "Health", "صحة النظام",
                                    {"x": 0, "y": 0, "w": 4, "h": 2})
        react_code = engine.generate_react_code(layout["id"])
    """

    # عدد الأعمدة في الشبكة
    GRID_COLUMNS = 12

    def __init__(self, db_path: str = None):
        self._db_path = db_path or str(UNIFIED_DB_PATH)
        self._layouts: Dict[str, DashboardLayout] = {}
        self._initialized = False
        self._counter = 0

    def initialize(self) -> bool:
        """تهيئة المحرك — إنشاء الجداول وتحميل التخطيطات"""
        try:
            self._ensure_schema()
            self._load_layouts()
            self._initialized = True
            logger.info(
                "DashboardBuilderEngine initialized — %d layouts loaded",
                len(self._layouts),
            )
            return True
        except Exception as e:
            logger.error("DashboardBuilderEngine init failed: %s", e)
            return False

    def _ensure_schema(self):
        """إنشاء جداول قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dbd_layouts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at REAL DEFAULT 0.0,
                    updated_at REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dbd_widgets (
                    id TEXT PRIMARY KEY,
                    layout_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    title_ar TEXT DEFAULT '',
                    position TEXT DEFAULT '{}',
                    data_source TEXT DEFAULT '',
                    refresh_interval INTEGER DEFAULT 30,
                    props TEXT DEFAULT '{}',
                    FOREIGN KEY (layout_id) REFERENCES dbd_layouts(id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_widgets_layout ON dbd_widgets(layout_id)"
            )
            conn.commit()
        finally:
            conn.close()

    def _load_layouts(self):
        """تحميل التخطيطات من قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            cur = conn.execute("SELECT * FROM dbd_layouts ORDER BY updated_at DESC")
            for row in cur.fetchall():
                layout = DashboardLayout(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                # تحميل الودجات
                wcur = conn.execute(
                    "SELECT * FROM dbd_widgets WHERE layout_id = ? ORDER BY position",
                    (layout.id,),
                )
                for wrow in wcur.fetchall():
                    widget = WidgetConfig(
                        id=wrow["id"],
                        type=WidgetType(wrow["type"]),
                        title=wrow["title"],
                        title_ar=wrow["title_ar"],
                        position=json.loads(wrow["position"]) if wrow["position"] else {},
                        data_source=wrow["data_source"],
                        refresh_interval=wrow["refresh_interval"],
                        props=json.loads(wrow["props"]) if wrow["props"] else {},
                    )
                    layout.widgets.append(widget)

                self._layouts[layout.id] = layout
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════════════════
    # إدارة التخطيطات — Layout CRUD
    # ═══════════════════════════════════════════════════════════════════════

    def create_layout(self, name: str, description: str = "") -> dict:
        """
        إنشاء تخطيط جديد

        Args:
            name: اسم التخطيط
            description: وصف التخطيط

        Returns:
            قاموس التخطيط الجديد
        """
        if not self._initialized:
            self.initialize()

        self._counter += 1
        layout_id = f"layout_{int(time.time())}_{self._counter}_{uuid.uuid4().hex[:6]}"
        now = time.time()

        layout = DashboardLayout(
            id=layout_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )

        # حفظ في قاعدة البيانات
        self._persist_layout(layout)
        self._layouts[layout_id] = layout

        logger.info("Created layout '%s' (%s)", name, layout_id)
        return layout.to_dict()

    def add_widget(
        self,
        layout_id: str,
        widget_type: str,
        title: str,
        title_ar: str,
        position: dict,
        data_source: str = "",
        props: dict = None,
    ) -> dict:
        """
        إضافة ودجة إلى تخطيط

        Args:
            layout_id: معرف التخطيط
            widget_type: نوع الودجة (chart, stat_card, timeline, table, notification_panel, custom)
            title: عنوان الودجة بالإنجليزية
            title_ar: عنوان الودجة بالعربية
            position: الموقع والحجم {x, y, w, h}
            data_source: مصدر البيانات (URL أو معرف)
            props: خصائص إضافية

        Returns:
            قاموس الودجة المضافة
        """
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return {"error": f"التخطيط غير موجود: {layout_id}"}

        # التحقق من نوع الودجة
        try:
            wtype = WidgetType(widget_type)
        except ValueError:
            return {"error": f"نوع ودجة غير صالح: {widget_type}. الأنواع المدعومة: {[t.value for t in WidgetType]}"}

        self._counter += 1
        widget_id = f"widget_{int(time.time())}_{self._counter}_{uuid.uuid4().hex[:6]}"

        widget = WidgetConfig(
            id=widget_id,
            type=wtype,
            title=title,
            title_ar=title_ar,
            position=position,
            data_source=data_source,
            refresh_interval=props.get("refresh_interval", 30) if props else 30,
            props=props or {},
        )

        # التحقق من الصحة
        errors = widget.validate()
        if errors:
            return {"error": "أخطاء في إعدادات الودجة", "details": errors}

        # التحقق من تداخل المواقع
        overlap = self._check_overlap(layout, widget)
        if overlap:
            return {"warning": f"تداخل مع ودجة '{overlap}'", "widget": widget.to_dict()}

        # إضافة الودجة
        layout.widgets.append(widget)
        layout.updated_at = time.time()

        # حفظ
        self._persist_widget(widget, layout_id)
        self._persist_layout_update(layout)

        logger.info(
            "Added widget '%s' (%s) to layout '%s'",
            title, widget_id, layout_id,
        )
        return widget.to_dict()

    def remove_widget(self, layout_id: str, widget_id: str) -> bool:
        """إزالة ودجة من تخطيط"""
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return False

        widget_index = None
        for i, w in enumerate(layout.widgets):
            if w.id == widget_id:
                widget_index = i
                break

        if widget_index is None:
            return False

        # إزالة من الذاكرة
        layout.widgets.pop(widget_index)
        layout.updated_at = time.time()

        # إزالة من قاعدة البيانات
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("DELETE FROM dbd_widgets WHERE id = ?", (widget_id,))
            conn.commit()
        finally:
            conn.close()

        self._persist_layout_update(layout)
        logger.info("Removed widget %s from layout %s", widget_id, layout_id)
        return True

    def update_widget(self, layout_id: str, widget_id: str, updates: dict) -> dict:
        """تحديث إعدادات ودجة"""
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return {"error": f"التخطيط غير موجود: {layout_id}"}

        widget = None
        for w in layout.widgets:
            if w.id == widget_id:
                widget = w
                break

        if not widget:
            return {"error": f"الودجة غير موجودة: {widget_id}"}

        # تحديث الحقول المسموحة
        if "title" in updates:
            widget.title = updates["title"]
        if "title_ar" in updates:
            widget.title_ar = updates["title_ar"]
        if "position" in updates:
            widget.position = updates["position"]
        if "data_source" in updates:
            widget.data_source = updates["data_source"]
        if "refresh_interval" in updates:
            widget.refresh_interval = int(updates["refresh_interval"])
        if "props" in updates:
            widget.props = updates["props"]
        if "type" in updates:
            try:
                widget.type = WidgetType(updates["type"])
            except ValueError:
                return {"error": f"نوع ودجة غير صالح: {updates['type']}"}

        layout.updated_at = time.time()

        # حفظ
        self._persist_widget(widget, layout_id)
        self._persist_layout_update(layout)

        logger.info("Updated widget %s in layout %s", widget_id, layout_id)
        return widget.to_dict()

    def get_layout(self, layout_id: str) -> dict:
        """الحصول على تخطيط كامل"""
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return {"error": f"التخطيط غير موجود: {layout_id}"}
        return layout.to_dict()

    def list_layouts(self) -> list:
        """قائمة جميع التخطيطات"""
        if not self._initialized:
            self.initialize()

        return [
            {
                "id": l.id,
                "name": l.name,
                "description": l.description,
                "widget_count": len(l.widgets),
                "created_at": l.created_at,
                "updated_at": l.updated_at,
            }
            for l in sorted(self._layouts.values(), key=lambda x: x.updated_at, reverse=True)
        ]

    # ═══════════════════════════════════════════════════════════════════════
    # توليد كود React — React Code Generation
    # ═══════════════════════════════════════════════════════════════════════

    def generate_react_code(self, layout_id: str) -> str:
        """
        توليد كود React كامل لصفحة داشبورد

        يولّد ملف page.tsx يحتوي على:
        - استيرادات المكونات
        - شبكة الودجات مع المواقع والأحجام
        - جلب البيانات من مصادر API
        - تحديث تلقائي حسب فترة التحديث

        Args:
            layout_id: معرف التخطيط

        Returns:
            كود React كامل كنص
        """
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return f"// Error: Layout '{layout_id}' not found"

        # بناء الاستيرادات
        imports = self._generate_imports(layout)
        # بناء الودجات
        widget_components = self._generate_widget_components(layout)
        # بناء تأثيرات جلب البيانات
        data_effects = self._generate_data_effects(layout)

        code = f"""\"use client";
// ═══════════════════════════════════════════════════════════════════════
// {layout.name} — {layout.description}
// Generated by DashboardBuilderEngine v20.0
// Generated at: {datetime.now().isoformat()}
// ═══════════════════════════════════════════════════════════════════════

import React, {{ useState, useEffect, useCallback }} from 'react';
{imports}

// ─── أنواع البيانات ─────────────────────────────────────────────────
interface WidgetData {{
  [key: string]: any;
}}

// ─── المكون الرئيسي ─────────────────────────────────────────────────
export default function {self._to_component_name(layout.name)}() {{
  const [widgetData, setWidgetData] = useState<Record<string, WidgetData>>({{}});
  const [loading, setLoading] = useState<Record<string, boolean>>({{}});
  const [error, setError] = useState<Record<string, string>>({{}});

{data_effects}

  return (
    <div className="dashboard-grid grid grid-cols-12 gap-4 p-6">
{widget_components}
    </div>
  );
}}
"""
        return code

    def _generate_imports(self, layout: DashboardLayout) -> str:
        """توليد استيرادات المكونات"""
        needed_imports = set()
        for widget in layout.widgets:
            if widget.type == WidgetType.CHART:
                needed_imports.add("import { LineChart, BarChart, PieChart, AreaChart } from 'recharts';")
            elif widget.type == WidgetType.CUSTOM:
                comp = widget.props.get("component", "")
                if comp:
                    needed_imports.add(f"import {comp} from '@/components/mamoun/{comp}';")

        return "\n".join(sorted(needed_imports))

    def _generate_widget_components(self, layout: DashboardLayout) -> str:
        """توليد كود الودجات"""
        components = []
        for widget in layout.widgets:
            pos = widget.position
            col_start = pos.get("x", 0) + 1
            col_span = pos.get("w", 4)
            row_start = pos.get("y", 0) + 1
            row_span = pos.get("h", 2)

            style_class = f"col-start-{col_start} col-span-{col_span} row-start-{row_start} row-span-{row_span}"

            title = widget.title_ar or widget.title
            data_key = widget.id.replace("-", "_")

            if widget.type == WidgetType.STAT_CARD:
                components.append(self._gen_stat_card(widget, style_class, title, data_key))
            elif widget.type == WidgetType.CHART:
                components.append(self._gen_chart(widget, style_class, title, data_key))
            elif widget.type == WidgetType.TIMELINE:
                components.append(self._gen_timeline(widget, style_class, title, data_key))
            elif widget.type == WidgetType.TABLE:
                components.append(self._gen_table(widget, style_class, title, data_key))
            elif widget.type == WidgetType.NOTIFICATION_PANEL:
                components.append(self._gen_notification_panel(widget, style_class, title, data_key))
            elif widget.type == WidgetType.CUSTOM:
                components.append(self._gen_custom(widget, style_class, title, data_key))

        return "\n\n".join(components)

    def _gen_stat_card(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        icon = w.props.get("icon", "activity")
        color = w.props.get("color", "#4A6FA5")
        tpl = (
            "      {{/* __TITLE__ — بطاقة إحصائية */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            '        <div className="flex items-center gap-3 mb-2">\n'
            '          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{{{ backgroundColor: \'__COLOR__20\' }}}}>\n'
            '            <span className="text-lg" style={{{{ color: \'__COLOR__\' }}}}>{{__ICON__}}</span>\n'
            "          </div>\n"
            "          <div>\n"
            '            <p className="text-sm text-gray-400">{{__TITLE__}}</p>\n'
            '            <p className="text-2xl font-bold" style={{{{ color: \'__COLOR__\' }}}}>\n'
            "              {{widgetData.__DK__?.value ?? '—'}}\n"
            "            </p>\n"
            "          </div>\n"
            "        </div>\n"
            "        {{widgetData.__DK__?.trend && (\n"
            '          <p className={{`text-xs ${{widgetData.__DK__?.trend > 0 ? \'text-green-400\' : \'text-red-400\'}}`}}>\n'
            "            {{{{widgetData.__DK__?.trend > 0 ? '↑' : '↓'}}}} {{{{Math.abs(widgetData.__DK__?.trend ?? 0)}}}}%\n"
            "          </p>\n"
            "        )}}\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk).replace("__ICON__", icon).replace("__COLOR__", color)

    def _gen_chart(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        chart_type = w.props.get("chart_type", "line")
        color = w.props.get("color", "#4A6FA5")
        chart_comp = {"line": "LineChart", "bar": "BarChart", "pie": "PieChart", "area": "AreaChart"}.get(chart_type, "LineChart")
        tpl = (
            "      {{/* __TITLE__ — رسم بياني */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            '        <h3 className="text-sm font-medium text-gray-300 mb-3">{{__TITLE__}}</h3>\n'
            "        {{loading.__DK__ ? (\n"
            '          <div className="h-48 flex items-center justify-center text-gray-500">جاري التحميل...</div>\n'
            "        ) : (\n"
            "          <__CHART_COMP__ data={{widgetData.__DK__?.data ?? []}} width={{undefined}} height={{180}}>\n"
            "            {{chart_type === 'pie' ? (\n"
            '              <Pie dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={{80}} fill="__COLOR__" />\n'
            "            ) : (\n"
            "              <>\n"
            '                <XAxis dataKey="name" stroke="#666" fontSize={{12}} />\n'
            '                <YAxis stroke="#666" fontSize={{12}} />\n'
            "                <Tooltip />\n"
            "                {{chart_type === 'area' ? (\n"
            '                  <Area type="monotone" dataKey="value" stroke="__COLOR__" fill="__COLOR__20" />\n'
            "                ) : chart_type === 'bar' ? (\n"
            '                  <Bar dataKey="value" fill="__COLOR__" />\n'
            "                ) : (\n"
            '                  <Line type="monotone" dataKey="value" stroke="__COLOR__" strokeWidth={{2}} dot={{{{r: 3}}}} />\n'
            "                )}}\n"
            "              </>\n"
            "            )}}\n"
            "          </__CHART_COMP__>\n"
            "        )}}\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk).replace("__COLOR__", color).replace("__CHART_COMP__", chart_comp)

    def _gen_timeline(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        tpl = (
            "      {{/* __TITLE__ — خط زمني */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            '        <h3 className="text-sm font-medium text-gray-300 mb-3">{{__TITLE__}}</h3>\n'
            '        <div className="space-y-2 max-h-64 overflow-y-auto">\n'
            "          {{(widgetData.__DK__?.events ?? []).map((event: any, i: number) => (\n"
            '            <div key={{i}} className="flex gap-3 items-start">\n'
            '              <div className="w-2 h-2 rounded-full bg-blue-400 mt-2 shrink-0" />\n'
            "              <div>\n"
            '                <p className="text-sm text-gray-300">{{{{event.title}}}}</p>\n'
            '                <p className="text-xs text-gray-500">{{{{event.time}}}}</p>\n'
            "              </div>\n"
            "            </div>\n"
            "          ))}}\n"
            "        </div>\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk)

    def _gen_table(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        tpl = (
            "      {{/* __TITLE__ — جدول */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            '        <h3 className="text-sm font-medium text-gray-300 mb-3">{{__TITLE__}}</h3>\n'
            '        <div className="overflow-x-auto">\n'
            '          <table className="w-full text-sm">\n'
            "            <thead>\n"
            '              <tr className="border-b border-white/10">\n'
            "                {{(widgetData.__DK__?.columns ?? []).map((col: string) => (\n"
            '                  <th key={{col}} className="text-left py-2 px-3 text-gray-400 font-medium">{{{{col}}}}</th>\n'
            "                ))}}\n"
            "              </tr>\n"
            "            </thead>\n"
            "            <tbody>\n"
            "              {{(widgetData.__DK__?.rows ?? []).map((row: any, i: number) => (\n"
            '                <tr key={{i}} className="border-b border-white/5 hover:bg-white/5">\n'
            "                  {{(widgetData.__DK__?.columns ?? []).map((col: string) => (\n"
            '                    <td key={{col}} className="py-2 px-3 text-gray-300">{{{{row[col]}}}}</td>\n'
            "                  ))}}\n"
            "                </tr>\n"
            "              ))}}\n"
            "            </tbody>\n"
            "          </table>\n"
            "        </div>\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk)

    def _gen_notification_panel(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        max_items = w.props.get("max_items", 10)
        tpl = (
            "      {{/* __TITLE__ — لوحة إشعارات */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            '        <h3 className="text-sm font-medium text-gray-300 mb-3">{{__TITLE__}}</h3>\n'
            '        <div className="space-y-2 max-h-64 overflow-y-auto">\n'
            "          {{(widgetData.__DK__?.notifications ?? []).slice(0, __MAX__).map((n: any, i: number) => (\n"
            '            <div key={{i}} className={{`p-2 rounded-lg ${{n.type === \'error\' ? \'bg-red-500/10 border-l-2 border-red-500\' : n.type === \'warning\' ? \'bg-yellow-500/10 border-l-2 border-yellow-500\' : \'bg-blue-500/10 border-l-2 border-blue-500\'}}`}}>\n'
            '              <p className="text-sm text-gray-300">{{{{n.message}}}}</p>\n'
            '              <p className="text-xs text-gray-500 mt-1">{{{{n.time}}}}</p>\n'
            "            </div>\n"
            "          ))}}\n"
            "        </div>\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk).replace("__MAX__", str(max_items))

    def _gen_custom(self, w: WidgetConfig, cls: str, title: str, dk: str) -> str:
        comp = w.props.get("component", "div")
        tpl = (
            "      {{/* __TITLE__ — مكون مخصص */}}\n"
            '      <div className="__CLS__ glass-card p-4 rounded-xl border border-white/10">\n'
            "        <__COMP__ data={{widgetData.__DK__}} />\n"
            "      </div>"
        )
        return tpl.replace("__CLS__", cls).replace("__TITLE__", title).replace("__DK__", dk).replace("__COMP__", comp)

    def _generate_data_effects(self, layout: DashboardLayout) -> str:
        """توليد تأثيرات جلب البيانات"""
        effects = []
        for widget in layout.widgets:
            if not widget.data_source:
                continue
            dk = widget.id.replace("-", "_")
            interval = widget.refresh_interval if widget.refresh_interval > 0 else 30
            effects.append(f"""  // جلب بيانات {widget.title_ar or widget.title} كل {interval} ثانية
  useEffect(() => {{
    const fetchData = async () => {{
      setLoading(prev => ({{ ...prev, {dk}: true }}));
      try {{
        const res = await fetch('{widget.data_source}');
        const data = await res.json();
        setWidgetData(prev => ({{ ...prev, {dk}: data }}));
      }} catch (err) {{
        setError(prev => ({{ ...prev, {dk}: String(err) }}));
      }} finally {{
        setLoading(prev => ({{ ...prev, {dk}: false }}));
      }}
    }};
    fetchData();
    const interval = setInterval(fetchData, {interval * 1000});
    return () => clearInterval(interval);
  }}, []);""")

        return "\n\n".join(effects)

    def _to_component_name(self, name: str) -> str:
        """تحويل اسم إلى اسم مكون React صالح"""
        # إزالة الأحرف غير الإنجليزية وتحويل إلى PascalCase
        parts = name.replace("-", " ").replace("_", " ").split()
        result = "".join(p.capitalize() for p in parts if p.isascii())
        if not result:
            result = "CustomDashboard"
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # التخطيطات المسبقة — Presets
    # ═══════════════════════════════════════════════════════════════════════

    def apply_preset(self, preset_name: str) -> dict:
        """
        تطبيق تخطيط مسبق — إنشاء تخطيط من قالب جاهز

        Args:
            preset_name: اسم التخطيط المسبق (overview, developer, consciousness, analytics)

        Returns:
            قاموس التخطيط المُنشأ
        """
        if not self._initialized:
            self.initialize()

        preset = PRESET_LAYOUTS.get(preset_name)
        if not preset:
            return {
                "error": f"تخطيط مسبق غير موجود: {preset_name}",
                "available": list(PRESET_LAYOUTS.keys()),
            }

        # إنشاء التخطيط
        layout = self.create_layout(
            name=preset["name"],
            description=preset["description"],
        )

        # إضافة الودجات
        for w_config in preset.get("widgets", []):
            self.add_widget(
                layout_id=layout["id"],
                widget_type=w_config.get("type", "stat_card"),
                title=w_config.get("title", ""),
                title_ar=w_config.get("title_ar", ""),
                position=w_config.get("position", {"x": 0, "y": 0, "w": 4, "h": 2}),
                data_source=w_config.get("data_source", ""),
                props=w_config.get("props", {}),
            )

        # إعادة تحميل التخطيط المحدث
        result = self.get_layout(layout["id"])
        logger.info("Applied preset '%s' → layout %s", preset_name, layout["id"])
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # تصدير/استيراد — Export/Import
    # ═══════════════════════════════════════════════════════════════════════

    def export_layout(self, layout_id: str) -> str:
        """
        تصدير تخطيط كـ JSON — يمكن استيراده لاحقاً

        Args:
            layout_id: معرف التخطيط

        Returns:
            نص JSON يحتوي على التخطيط الكامل
        """
        if not self._initialized:
            self.initialize()

        layout = self._layouts.get(layout_id)
        if not layout:
            return json.dumps({"error": f"التخطيط غير موجود: {layout_id}"})

        export_data = {
            "version": "20.0",
            "exported_at": time.time(),
            "layout": layout.to_dict(),
        }
        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def import_layout(self, json_str: str) -> dict:
        """
        استيراد تخطيط من JSON

        Args:
            json_str: نص JSON يحتوي على التخطيط

        Returns:
            قاموس التخطيط المُستورد
        """
        if not self._initialized:
            self.initialize()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"JSON غير صالح: {e}"}

        layout_data = data.get("layout", data)

        # التحقق من الحقول المطلوبة
        if not layout_data.get("name"):
            return {"error": "اسم التخطيط مطلوب"}

        # إنشاء تخطيط جديد
        layout = self.create_layout(
            name=layout_data.get("name", "مستورد"),
            description=layout_data.get("description", ""),
        )

        # إضافة الودجات
        for w_data in layout_data.get("widgets", []):
            self.add_widget(
                layout_id=layout["id"],
                widget_type=w_data.get("type", "stat_card"),
                title=w_data.get("title", ""),
                title_ar=w_data.get("title_ar", ""),
                position=w_data.get("position", {"x": 0, "y": 0, "w": 4, "h": 2}),
                data_source=w_data.get("data_source", ""),
                props=w_data.get("props", {}),
            )

        result = self.get_layout(layout["id"])
        logger.info("Imported layout '%s' → %s", layout_data.get("name"), layout["id"])
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # جلب بيانات الودجات — Widget Data
    # ═══════════════════════════════════════════════════════════════════════

    def get_widget_data(self, widget_id: str, data_source: str) -> dict:
        """
        جلب بيانات ودجة — يُرجع بيانات تجريبية

        في الإنتاج، يتصل بمصدر البيانات الفعلي.
        حالياً يُرجع بيانات تجريبية لكل نوع ودجة.

        Args:
            widget_id: معرف الودجة
            data_source: مصدر البيانات

        Returns:
            قاموس البيانات
        """
        now = time.time()
        # بيانات تجريبية حسب نوع الودجة
        sample_data = {
            "stat_card": {
                "value": "98.5%",
                "trend": 2.3,
                "label": "صحة النظام",
            },
            "chart": {
                "data": [
                    {"name": "السبت", "value": 85},
                    {"name": "الأحد", "value": 92},
                    {"name": "الاثنين", "value": 88},
                    {"name": "الثلاثاء", "value": 95},
                    {"name": "الأربعاء", "value": 91},
                    {"name": "الخميس", "value": 97},
                ],
            },
            "timeline": {
                "events": [
                    {"title": "تحديث النظام", "time": "منذ 5 دقائق"},
                    {"title": "تم إصلاح خطأ", "time": "منذ 15 دقيقة"},
                    {"title": "دورة تطور جديدة", "time": "منذ ساعة"},
                ],
            },
            "table": {
                "columns": ["النموذج", "الدقة", "الزمن", "الثقة"],
                "rows": [
                    {"النموذج": "GLM-5.1", "الدقة": "95%", "الزمن": "1.2s", "الثقة": "0.92"},
                    {"النموذج": "DeepSeek", "الدقة": "93%", "الزمن": "1.8s", "الثقة": "0.88"},
                    {"النموذج": "Gemini", "الدقة": "94%", "الزمن": "1.5s", "الثقة": "0.90"},
                ],
            },
            "notification_panel": {
                "notifications": [
                    {"message": "تم تحديث النظام بنجاح", "type": "success", "time": "منذ 2 دقيقة"},
                    {"message": "تحذير: استخدام الذاكرة مرتفع", "type": "warning", "time": "منذ 10 دقائق"},
                ],
            },
        }

        # البحث عن نوع الودجة
        for layout in self._layouts.values():
            for widget in layout.widgets:
                if widget.id == widget_id:
                    data = sample_data.get(widget.type.value, {"value": "—"})
                    data["_meta"] = {
                        "widget_id": widget_id,
                        "data_source": data_source,
                        "fetched_at": now,
                    }
                    return data

        # بيانات افتراضية
        return {
            "value": "—",
            "_meta": {
                "widget_id": widget_id,
                "data_source": data_source,
                "fetched_at": now,
                "note": "ودجة غير موجودة — بيانات تجريبية",
            },
        }

    # ═══════════════════════════════════════════════════════════════════════
    # الحالة — Status
    # ═══════════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """الحصول على حالة المحرك الكاملة"""
        if not self._initialized:
            self.initialize()

        total_widgets = sum(len(l.widgets) for l in self._layouts.values())
        widget_types = {}
        for layout in self._layouts.values():
            for widget in layout.widgets:
                t = widget.type.value
                widget_types[t] = widget_types.get(t, 0) + 1

        return {
            "initialized": self._initialized,
            "layout_count": len(self._layouts),
            "total_widgets": total_widgets,
            "widget_type_distribution": widget_types,
            "available_presets": list(PRESET_LAYOUTS.keys()),
            "supported_widget_types": [t.value for t in WidgetType],
            "grid_columns": self.GRID_COLUMNS,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # دوال داخلية — Internal Methods
    # ═══════════════════════════════════════════════════════════════════════

    def _check_overlap(self, layout: DashboardLayout, new_widget: WidgetConfig) -> Optional[str]:
        """التحقق من تداخل الودجات — يُرجع اسم الودجة المتداخلة أو None"""
        np = new_widget.position
        nx1, ny1 = np.get("x", 0), np.get("y", 0)
        nx2, ny2 = nx1 + np.get("w", 1), ny1 + np.get("h", 1)

        for widget in layout.widgets:
            if widget.id == new_widget.id:
                continue
            wp = widget.position
            wx1, wy1 = wp.get("x", 0), wp.get("y", 0)
            wx2, wy2 = wx1 + wp.get("w", 1), wy1 + wp.get("h", 1)

            # فحص التداخل
            if not (nx2 <= wx1 or nx1 >= wx2 or ny2 <= wy1 or ny1 >= wy2):
                return widget.title or widget.id

        return None

    def _persist_layout(self, layout: DashboardLayout):
        """حفظ تخطيط في قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO dbd_layouts
                (id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                layout.id,
                layout.name,
                layout.description,
                layout.created_at,
                layout.updated_at,
            ))
            conn.commit()
        finally:
            conn.close()

    def _persist_layout_update(self, layout: DashboardLayout):
        """تحديث تخطيط في قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                UPDATE dbd_layouts
                SET name = ?, description = ?, updated_at = ?
                WHERE id = ?
            """, (layout.name, layout.description, layout.updated_at, layout.id))
            conn.commit()
        finally:
            conn.close()

    def _persist_widget(self, widget: WidgetConfig, layout_id: str):
        """حفظ ودجة في قاعدة البيانات"""
        conn = get_db_connection(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO dbd_widgets
                (id, layout_id, type, title, title_ar, position,
                 data_source, refresh_interval, props)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                widget.id,
                layout_id,
                widget.type.value,
                widget.title,
                widget.title_ar,
                json.dumps(widget.position),
                widget.data_source,
                widget.refresh_interval,
                json.dumps(widget.props),
            ))
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton — النسخة الوحيدة من المحرك
# ═══════════════════════════════════════════════════════════════════════════════

dashboard_builder = DashboardBuilderEngine()
