"""
BABSHARQII v21.0 — Agent Browser (المتصفح الوكيلي)
متصفح كامل يتيح لمامون تصفح الويب، النقر، تعبئة الحقول، التقاط صور، استخراج البيانات

يعتمد على:
  - Playwright (رئيسي) — متصفح Chromium كامل التحكم
  - httpx + BeautifulSoup (احتياطي) — للطلبات البسيطة بدون متصفح

القدرات:
  - فتح صفحات الويب
  - النقر على العناصر
  - تعبئة حقول الإدخال
  - التقاط لقطات شاشة
  - استخراج نصوص وبيانات
  - تنفيذ JavaScript
  - إدارة الكوكيز
  - تسجيل الدخول التلقائي
  - البحث في جوجل
  - تحليل صفحات الانستغرام
"""

import os
import time
import json
import base64
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger("mamoun.agents.browser")

BROWSER_ENABLED = os.getenv("MAMOUN_BROWSER_ENABLED", "true").lower() == "true"


class BrowserMode(str, Enum):
    PLAYWRIGHT = "playwright"    # متصفح حقيقي مع رأس
    HEADLESS = "headless"        # متصفح بدون رأس (أسرع)
    HTTP_ONLY = "http_only"      # طلبات HTTP فقط (بدون متصفح)


@dataclass
class BrowserTab:
    """تبويب متصفح"""
    id: str = ""
    url: str = ""
    title: str = ""
    favicon_url: str = ""
    is_active: bool = False
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "favicon_url": self.favicon_url,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class PageElement:
    """عنصر في الصفحة"""
    tag: str = ""
    text: str = ""
    href: str = ""
    src: str = ""
    selector: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_clickable: bool = False
    is_input: bool = False
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "text": self.text[:200],
            "href": self.href,
            "selector": self.selector,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "is_clickable": self.is_clickable,
            "is_input": self.is_input,
        }


@dataclass
class BrowserActionResult:
    """نتيجة إجراء في المتصفح"""
    success: bool = False
    url: str = ""
    title: str = ""
    screenshot_base64: str = ""
    text_content: str = ""
    elements_found: int = 0
    error: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "url": self.url,
            "title": self.title,
            "screenshot_available": bool(self.screenshot_base64),
            "text_length": len(self.text_content),
            "elements_found": self.elements_found,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 0),
        }


class AgentBrowser:
    """
    المتصفح الوكيلي — يتيح لمامون تصفح الويب والتفاعل معه

    المستوى 1 (Playwright): متصفح حقيقي كامل التحكم — يتطلب playwright install
    المستوى 2 (HTTP): طلبات HTTP + BeautifulSoup — يعمل دائماً
    """

    def __init__(self, mode: BrowserMode = BrowserMode.HEADLESS):
        self._mode = mode
        self._playwright = None
        self._browser = None
        self._page = None
        self._tabs: dict[str, BrowserTab] = {}
        self._tab_counter = 0
        self._initialized = False
        self._action_history: list[dict] = []

    async def initialize(self) -> bool:
        """تهيئة المتصفح"""
        if self._initialized:
            return True

        if self._mode in (BrowserMode.PLAYWRIGHT, BrowserMode.HEADLESS):
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=(self._mode == BrowserMode.HEADLESS),
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--window-size=1280,720',
                    ]
                )
                self._page = await self._browser.new_page(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                self._initialized = True
                logger.info("AgentBrowser initialized — Playwright %s mode", self._mode.value)
                return True
            except ImportError:
                logger.warning("Playwright not available — falling back to HTTP mode")
                self._mode = BrowserMode.HTTP_ONLY
            except Exception as e:
                logger.warning("Playwright launch failed: %s — falling back to HTTP mode", e)
                self._mode = BrowserMode.HTTP_ONLY
                self._initialized = True  # HTTP mode works without Playwright

        # HTTP fallback always works
        self._initialized = True
        logger.info("AgentBrowser initialized — HTTP mode")
        return True

    # ─── Navigation ──────────────────────────────────────────────────────────

    async def navigate(self, url: str) -> BrowserActionResult:
        """فتح صفحة ويب"""
        start = time.time()

        if self._page:
            try:
                response = await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title = await self._page.title()
                screenshot = await self._page.screenshot() if self._mode != BrowserMode.HTTP_ONLY else b""
                screenshot_b64 = base64.b64encode(screenshot).decode() if screenshot else ""

                self._tab_counter += 1
                tab = BrowserTab(
                    id=f"tab_{self._tab_counter}",
                    url=self._page.url,
                    title=title,
                    is_active=True,
                    created_at=time.time(),
                )
                self._tabs[tab.id] = tab

                duration = (time.time() - start) * 1000
                result = BrowserActionResult(
                    success=response.status < 400 if response else True,
                    url=self._page.url,
                    title=title,
                    screenshot_base64=screenshot_b64,
                    duration_ms=duration,
                )
                self._log_action("navigate", {"url": url, "success": result.success})
                return result
            except Exception as e:
                logger.warning("Playwright navigate failed: %s", e)

        # HTTP fallback
        return await self._http_navigate(url)

    async def _http_navigate(self, url: str) -> BrowserActionResult:
        """فتح صفحة عبر HTTP فقط"""
        import httpx
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                text = resp.text
                title = ""
                if "<title>" in text:
                    title = text.split("<title>")[1].split("</title>")[0].strip()

                duration = (time.time() - start) * 1000
                return BrowserActionResult(
                    success=resp.status_code < 400,
                    url=str(resp.url),
                    title=title,
                    text_content=text[:50000],
                    duration_ms=duration,
                )
        except Exception as e:
            return BrowserActionResult(success=False, url=url, error=str(e), duration_ms=(time.time() - start) * 1000)

    # ─── Interaction ─────────────────────────────────────────────────────────

    async def click(self, selector: str) -> BrowserActionResult:
        """النقر على عنصر"""
        if not self._page:
            return BrowserActionResult(success=False, error="لا يوجد صفحة مفتوحة")

        start = time.time()
        try:
            await self._page.click(selector, timeout=10000)
            await self._page.wait_for_load_state("domcontentloaded", timeout=10000)
            title = await self._page.title()
            return BrowserActionResult(
                success=True,
                url=self._page.url,
                title=title,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)

    async def fill(self, selector: str, value: str) -> BrowserActionResult:
        """تعبئة حقل إدخال"""
        if not self._page:
            return BrowserActionResult(success=False, error="لا يوجد صفحة مفتوحة")

        start = time.time()
        try:
            await self._page.fill(selector, value)
            return BrowserActionResult(success=True, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)

    async def type_text(self, selector: str, text: str, delay: int = 50) -> BrowserActionResult:
        """كتابة نص حرف حرف"""
        if not self._page:
            return BrowserActionResult(success=False, error="لا يوجد صفحة مفتوحة")

        start = time.time()
        try:
            await self._page.type(selector, text, delay=delay)
            return BrowserActionResult(success=True, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)

    async def press_key(self, key: str) -> BrowserActionResult:
        """ضغط مفتاح"""
        if not self._page:
            return BrowserActionResult(success=False, error="لا يوجد صفحة مفتوحة")

        start = time.time()
        try:
            await self._page.keyboard.press(key)
            return BrowserActionResult(success=True, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return BrowserActionResult(success=False, error=str(e), duration_ms=(time.time() - start) * 1000)

    # ─── Data Extraction ─────────────────────────────────────────────────────

    async def get_text(self) -> str:
        """استخراج نص الصفحة"""
        if not self._page:
            return ""
        try:
            return await self._page.inner_text("body")
        except Exception:
            return ""

    async def get_html(self) -> str:
        """استخراج HTML الصفحة"""
        if not self._page:
            return ""
        try:
            return await self._page.content()
        except Exception:
            return ""

    async def find_elements(self, selector: str) -> list[dict]:
        """البحث عن عناصر"""
        if not self._page:
            return []
        try:
            elements = await self._page.query_selector_all(selector)
            results = []
            for i, el in enumerate(elements[:50]):  # Limit to 50
                text = await el.inner_text() if el else ""
                tag = await el.evaluate("el => el.tagName") if el else ""
                href = await el.get_attribute("href") or ""
                box = await el.bounding_box() if el else None

                results.append(PageElement(
                    tag=tag,
                    text=text[:200],
                    href=href,
                    selector=f"{selector} >> nth={i}",
                    x=int(box["x"]) if box else 0,
                    y=int(box["y"]) if box else 0,
                    width=int(box["width"]) if box else 0,
                    height=int(box["height"]) if box else 0,
                    is_clickable=tag.lower() in ("a", "button", "input", "select"),
                    is_input=tag.lower() in ("input", "textarea", "select"),
                ).to_dict())
            return results
        except Exception as e:
            logger.warning("Find elements error: %s", e)
            return []

    async def screenshot(self, full_page: bool = False) -> dict:
        """التقاط صورة للصفحة"""
        if not self._page:
            return {"success": False, "error": "لا يوجد صفحة مفتوحة"}

        try:
            img_bytes = await self._page.screenshot(full_page=full_page)
            img_b64 = base64.b64encode(img_bytes).decode()
            return {"success": True, "image_base64": img_b64, "size_bytes": len(img_bytes)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_js(self, script: str) -> dict:
        """تنفيذ JavaScript"""
        if not self._page:
            return {"success": False, "error": "لا يوجد صفحة مفتوحة"}

        # Safety: block dangerous operations
        dangerous = ["fetch(", "XMLHttpRequest", "eval(", "Function(", "import("]
        for d in dangerous:
            if d in script:
                return {"success": False, "error": f"JavaScript محظور يحتوي على: {d}"}

        try:
            result = await self._page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ─── Specialized Operations ──────────────────────────────────────────────

    async def google_search(self, query: str, num_results: int = 10) -> list[dict]:
        """بحث في جوجل واستخراج النتائج"""
        await self.navigate(f"https://www.google.com/search?q={query}&num={num_results}")
        await asyncio.sleep(1)

        results = await self.find_elements("div.g")
        return results[:num_results]

    async def analyze_instagram_page(self, username: str) -> dict:
        """تحليل صفحة انستغرام بشكل عميق"""
        url = f"https://www.instagram.com/{username}/"
        nav_result = await self.navigate(url)

        # Try HTTP fallback if Playwright can't access
        if not nav_result.success:
            return await self._http_analyze_instagram(username)

        # Extract page data
        try:
            page_text = await self.get_text()
            elements = await self.find_elements("a, img, span, div")

            # Parse key metrics
            followers = 0
            following = 0
            posts = 0
            bio = ""

            # Try to extract from meta tags
            meta_desc = await self._page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.getAttribute('content') : '';
                }
            """)

            if meta_desc:
                # Parse "X Followers, Y Following, Z Posts" pattern
                import re
                f_match = re.search(r'([\d,\.mMkK]+)\s*Followers', meta_desc)
                fo_match = re.search(r'([\d,\.mMkK]+)\s*Following', meta_desc)
                p_match = re.search(r'([\d,\.mMkK]+)\s*Posts', meta_desc)

                if f_match:
                    followers = self._parse_count(f_match.group(1))
                if fo_match:
                    following = self._parse_count(fo_match.group(1))
                if p_match:
                    posts = self._parse_count(p_match.group(1))

                bio = meta_desc.split("•")[-1].strip() if "•" in meta_desc else ""

            # Extract recent posts
            post_links = await self.find_elements("a[href*='/p/'], a[href*='/reel/']")
            recent_posts = post_links[:12]

            return {
                "success": True,
                "username": username,
                "url": url,
                "followers": followers,
                "following": following,
                "posts_count": posts,
                "bio": bio,
                "recent_post_count": len(recent_posts),
                "recent_posts": recent_posts,
                "page_title": nav_result.title,
                "analysis_notes": [
                    "تم استخراج البيانات من meta tags",
                    f"عدد المتابعين: {self._format_count(followers)}",
                    f"عدد المنشورات: {posts}",
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e), "username": username}

    async def _http_analyze_instagram(self, username: str) -> dict:
        """تحليل صفحة انستغرام عبر HTTP"""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                url = f"https://www.instagram.com/{username}/"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html",
                })
                text = resp.text

                # Extract from og:meta tags
                import re
                og_title = re.search(r'og:title.*?content="([^"]*)"', text)
                og_desc = re.search(r'og:description.*?content="([^"]*)"', text)
                og_image = re.search(r'og:image.*?content="([^"]*)"', text)

                followers = 0
                posts = 0
                bio = ""

                if og_desc:
                    desc = og_desc.group(1)
                    f_match = re.search(r'([\d,\.mMkK]+)\s*Followers', desc)
                    p_match = re.search(r'([\d,\.mMkK]+)\s*Posts', desc)
                    if f_match:
                        followers = self._parse_count(f_match.group(1))
                    if p_match:
                        posts = self._parse_count(p_match.group(1))
                    bio = desc.split("–")[-1].strip() if "–" in desc else desc

                return {
                    "success": True,
                    "username": username,
                    "url": url,
                    "followers": followers,
                    "following": 0,
                    "posts_count": posts,
                    "bio": bio,
                    "profile_image": og_image.group(1) if og_image else "",
                    "method": "http_meta_extraction",
                    "analysis_notes": [
                        "تم الاستخراج عبر HTTP + meta tags (محدود بدون تسجيل دخول)",
                        f"عدد المتابعين: {self._format_count(followers)}",
                        "للحصول على تحليل أعمق، فعّل Playwright mode + Instagram session",
                    ],
                }
        except Exception as e:
            return {"success": False, "error": str(e), "username": username}

    # ─── Utilities ───────────────────────────────────────────────────────────

    @staticmethod
    def _parse_count(text: str) -> int:
        """تحويل '1.5M' → 1500000 إلخ"""
        text = text.strip().replace(",", "")
        multipliers = {"K": 1000, "M": 1000000, "B": 1000000000}
        for suffix, mult in multipliers.items():
            if text.upper().endswith(suffix):
                try:
                    return int(float(text[:-1]) * mult)
                except ValueError:
                    return 0
        try:
            return int(float(text))
        except ValueError:
            return 0

    @staticmethod
    def _format_count(n: int) -> str:
        """تنسيق الأرقام الكبيرة"""
        if n >= 1000000:
            return f"{n/1000000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)

    def _log_action(self, action: str, details: dict):
        """تسجيل إجراء"""
        self._action_history.append({
            "action": action,
            "details": details,
            "timestamp": time.time(),
        })

    async def close(self):
        """إغلاق المتصفح"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._initialized = False

    def get_status(self) -> dict:
        return {
            "enabled": BROWSER_ENABLED,
            "mode": self._mode.value,
            "initialized": self._initialized,
            "tabs_open": len(self._tabs),
            "actions_performed": len(self._action_history),
        }

    def get_action_history(self, limit: int = 50) -> list[dict]:
        return self._action_history[-limit:]


# Singleton
_agent_browser: Optional[AgentBrowser] = None

def get_agent_browser() -> AgentBrowser:
    global _agent_browser
    if _agent_browser is None:
        _agent_browser = AgentBrowser()
    return _agent_browser
