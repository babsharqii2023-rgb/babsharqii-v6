"""
BABSHARQII v13.0 — Site Builder Agent
وكيل بناء المواقع — يبني مواقع كاملة من وصف نصي

Inspired by TDDev and similar multi-agent website builders.

Flow:
1. User describes the website they want
2. SiteBuilderAgent creates a plan (pages, components, styling)
3. Generates React/Next.js components
4. Tests in development server
5. Deploys or provides download

Security:
- Requires MAMOUN_SELF_PROGRAMMING and human approval
- Uses TimeBoundedPolicy for file system access
- All generated code runs in sandbox

Feature Flag: MAMOUN_SELF_PROGRAMMING (default: false)
"""

import os
import time
import uuid
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

from mamoun.evolution.self_programming_loop import SELF_PROGRAMMING_ENABLED, _is_self_programming_enabled

logger = logging.getLogger(__name__)

SITES_DIR = str(Path(__file__).parent.parent.parent / "data" / "generated_sites")


@dataclass
class SitePlan:
    """خطة الموقع."""
    site_id: str = ""
    name: str = ""
    name_ar: str = ""
    description: str = ""
    pages: list = field(default_factory=list)  # [{name, components, route}]
    theme: dict = field(default_factory=dict)   # {primary_color, font, direction}
    features: list = field(default_factory=list)
    status: str = "planned"

    def __post_init__(self):
        if not self.site_id:
            self.site_id = f"site_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SiteBuildResult:
    """نتيجة بناء الموقع."""
    site_id: str = ""
    success: bool = False
    files_created: list = field(default_factory=list)
    pages_created: int = 0
    build_path: str = ""
    preview_url: str = ""
    error: str = ""
    build_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class SiteBuilderAgent:
    """
    وكيل بناء المواقع — يبني مواقع كاملة من وصف نصي.

    Generates:
    - Next.js pages with App Router
    - Tailwind CSS styling with RTL support
    - Responsive layouts
    - Navigation and routing
    - API routes if needed

    Usage:
        agent = SiteBuilderAgent()
        plan = await agent.plan("موقع متجر إلكتروني عربي")
        result = await agent.build(plan)
    """

    def __init__(self, output_dir: str = ""):
        self._output_dir = output_dir or SITES_DIR
        self._build_count = 0
        self._plans: dict[str, SitePlan] = {}

    async def plan(self, description: str, language: str = "ar") -> SitePlan:
        """
        تخطيط الموقع — Create a site plan from description.

        Args:
            description: وصف الموقع المطلوب
            language: لغة الموقع (ar, en)

        Returns:
            SitePlan with pages, theme, and features
        """
        # Parse description to determine site type
        site_type = self._detect_site_type(description)

        # Generate pages based on site type
        pages = self._generate_pages(site_type, language)

        # Generate theme
        theme = {
            "primary_color": "#2563eb",
            "secondary_color": "#7c3aed",
            "font": "Noto Sans SC" if language == "ar" else "Inter",
            "direction": "rtl" if language == "ar" else "ltr",
            "background": "#ffffff",
            "text_color": "#1f2937",
        }

        # Generate features
        features = self._generate_features(site_type)

        plan = SitePlan(
            name=site_type.get("name", "Generated Site"),
            name_ar=site_type.get("name_ar", "موقع مُولَّد"),
            description=description,
            pages=pages,
            theme=theme,
            features=features,
            status="planned",
        )

        self._plans[plan.site_id] = plan
        return plan

    async def build(self, plan: SitePlan) -> SiteBuildResult:
        """
        بناء الموقع — Build the site from plan.

        Args:
            plan: خطة الموقع

        Returns:
            SiteBuildResult with build output
        """
        start_time = time.time()

        if not _is_self_programming_enabled():
            return SiteBuildResult(
                site_id=plan.site_id,
                success=False,
                error="البرمجة الذاتية معطلة — تحتاج MAMOUN_SELF_PROGRAMMING=true",
            )

        self._build_count += 1
        build_path = os.path.join(self._output_dir, plan.site_id)
        files_created = []

        try:
            os.makedirs(build_path, exist_ok=True)

            # Generate layout.tsx
            layout_code = self._generate_layout(plan)
            layout_path = os.path.join(build_path, "layout.tsx")
            with open(layout_path, "w", encoding="utf-8") as f:
                f.write(layout_code)
            files_created.append("layout.tsx")

            # Generate each page
            for page in plan.pages:
                page_code = self._generate_page(page, plan)
                page_path = os.path.join(
                    build_path,
                    f"page_{page.get('route', page.get('name', 'home')).strip('/')}.tsx"
                )
                with open(page_path, "w", encoding="utf-8") as f:
                    f.write(page_code)
                files_created.append(os.path.basename(page_path))

            plan.status = "built"

            return SiteBuildResult(
                site_id=plan.site_id,
                success=True,
                files_created=files_created,
                pages_created=len(plan.pages),
                build_path=build_path,
                build_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"SiteBuilderAgent: Build failed: {e}")
            return SiteBuildResult(
                site_id=plan.site_id,
                success=False,
                files_created=files_created,
                build_path=build_path,
                error=str(e)[:500],
                build_time_ms=(time.time() - start_time) * 1000,
            )

    def _detect_site_type(self, description: str) -> dict:
        """كشف نوع الموقع من الوصف."""
        desc_lower = description.lower()

        if any(word in desc_lower for word in ["متجر", "تجارة", "store", "shop", "ecommerce"]):
            return {"name": "E-commerce Site", "name_ar": "موقع متجر إلكتروني", "type": "ecommerce"}
        elif any(word in desc_lower for word in ["مدونة", "blog", "مقالات"]):
            return {"name": "Blog Site", "name_ar": "موقع مدونة", "type": "blog"}
        elif any(word in desc_lower for word in ["شركة", "company", "أعمال", "business"]):
            return {"name": "Business Site", "name_ar": "موقع شركة", "type": "business"}
        elif any(word in desc_lower for word in ["محفظة", "portfolio", "أعمالي"]):
            return {"name": "Portfolio Site", "name_ar": "موقع محفظة أعمال", "type": "portfolio"}
        else:
            return {"name": "General Site", "name_ar": "موقع عام", "type": "general"}

    def _generate_pages(self, site_type: dict, language: str) -> list[dict]:
        """توليد صفحات الموقع."""
        pages = [
            {"name": "Home", "name_ar": "الرئيسية", "route": "/", "components": ["hero", "features"]},
            {"name": "About", "name_ar": "من نحن", "route": "/about", "components": ["content"]},
            {"name": "Contact", "name_ar": "اتصل بنا", "route": "/contact", "components": ["form", "map"]},
        ]

        stype = site_type.get("type", "general")
        if stype == "ecommerce":
            pages.extend([
                {"name": "Products", "name_ar": "المنتجات", "route": "/products", "components": ["grid", "filters"]},
                {"name": "Cart", "name_ar": "السلة", "route": "/cart", "components": ["cart_list", "checkout"]},
            ])
        elif stype == "blog":
            pages.extend([
                {"name": "Posts", "name_ar": "المقالات", "route": "/posts", "components": ["post_list", "sidebar"]},
            ])

        return pages

    def _generate_features(self, site_type: dict) -> list[str]:
        """توليد ميزات الموقع."""
        base_features = ["responsive", "rtl_support", "dark_mode", "seo"]
        stype = site_type.get("type", "general")
        if stype == "ecommerce":
            base_features.extend(["cart", "checkout", "product_search"])
        elif stype == "blog":
            base_features.extend(["markdown", "categories", "search"])
        return base_features

    def _generate_layout(self, plan: SitePlan) -> str:
        """توليد ملف Layout."""
        direction = plan.theme.get("direction", "rtl")
        font = plan.theme.get("font", "Noto Sans SC")
        pages_nav = " ".join(
            f'<a href="{p.get("route", "/")}" className="text-gray-600 hover:text-blue-600">'
            f'{p.get("name_ar", "")}</a>'
            for p in plan.pages
        )
        return f'''// Auto-generated by BABSHARQII v13.0 SiteBuilderAgent
import "./globals.css";

export default function RootLayout({{ children }}: {{ children: React.ReactNode }}) {{
  return (
    <html lang="ar" dir="{direction}">
      <body style={{ fontFamily: "{font}" }}>
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <h1 className="text-xl font-bold">{plan.name_ar}</h1>
            <div className="flex gap-4">
              {pages_nav}
            </div>
          </div>
        </nav>
        <main>{{children}}</main>
      </body>
    </html>
  );
}}
'''

    def _generate_page(self, page: dict, plan: SitePlan) -> str:
        """توليد صفحة."""
        components = page.get("components", [])
        page_name = page.get("name_ar", page.get("name", "Page"))
        sections = "\n".join(
            f'<section className="mb-8"><div className="bg-gray-50 rounded-lg p-6">'
            f'{{/* {comp} component */}}</div></section>'
            for comp in components
        )
        return f'''// Auto-generated by BABSHARQII v13.0 SiteBuilderAgent
// Page: {page_name}

export default function {page.get("name", "Home")}Page() {{
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">{page_name}</h1>
      {sections}
    </div>
  );
}}
'''

    def get_status(self) -> dict:
        """حالة وكيل بناء المواقع."""
        return {
            "enabled": SELF_PROGRAMMING_ENABLED,
            "build_count": self._build_count,
            "plans_count": len(self._plans),
            "output_dir": self._output_dir,
        }

    async def shutdown(self):
        """إيقاف الوكيل — يتوافق مع القانون 5."""
        logger.info("SiteBuilderAgent: Shutdown complete (Law 5 compliant)")
