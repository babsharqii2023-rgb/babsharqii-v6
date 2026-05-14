"""
BABSHARQII v40.0 — Screen Agent
وكيل الشاشة — تحليل لقطات الشاشة وإحداثيات واجهة المستخدم.
"""

import os
import json
import logging
import base64
import httpx
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScreenResult:
    """نتيجة تحليل الشاشة."""
    description: str  # وصف نصي بالعربية
    coordinates: list  # إحداثيات العناصر القابلة للنقر
    confidence: float
    metadata: dict
    source_file: str

    def to_dict(self) -> dict:
        """تحويل النتيجة إلى قاموس."""
        return asdict(self)


class ScreenAgent:
    """
    وكيل الشاشة لمأمون.

    يتخصص في:
    - تحليل لقطات الشاشة وفهم المحتوى
    - استخلاص إحداثيات العناصر القابلة للنقر
    - وصف بنية واجهة المستخدم
    """

    SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    def __init__(
        self,
        vision_api_key: Optional[str] = None,
        llm_api_url: Optional[str] = None,
    ):
        """
        تهيئة وكيل الشاشة.

        المعاملات:
            vision_api_key: مفتاح API للرؤية
            llm_api_url: عنوان URL للـ API
        """
        self.vision_api_key = vision_api_key or os.getenv("MAMOUN_VISION_API_KEY", "")
        self.llm_api_url = llm_api_url or os.getenv(
            "MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4"
        )

        logger.info(
            f"ScreenAgent initialized — "
            f"API key configured: {bool(self.vision_api_key)}, "
            f"LLM URL: {self.llm_api_url}"
        )

    def _validate_image(self, image_path: str) -> Path:
        """التحقق من صلاحية مسار الصورة."""
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"ملف الصورة غير موجود: {image_path}")

        if path.suffix.lower() not in self.SUPPORTED_IMAGE:
            raise ValueError(
                f"صيغة صورة غير مدعومة: {path.suffix}. "
                f"الصيغ المدعومة: {self.SUPPORTED_IMAGE}"
            )

        return path

    async def _call_vision_api(self, image_path: str, prompt: str) -> Optional[str]:
        """
        استدعاء Vision API مع الصورة والطلب.

        يحاول الاتصال بـ GLM-4V API أولاً. إذا لم يكن متاحاً،
        يُرجع None للسماح بالاستجابة المؤقتة.
        """
        if not self.vision_api_key:
            return None

        path = Path(image_path)

        try:
            with open(image_path, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode("utf-8")

            img_format = path.suffix.lower().lstrip(".")
            vision_url = f"{self.llm_api_url}/chat/completions"

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    vision_url,
                    headers={
                        "Authorization": f"Bearer {self.vision_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "glm-4v-plus",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/{img_format};base64,{img_data}"
                                        },
                                    },
                                ],
                            }
                        ],
                        "max_tokens": 1500,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info(f"Screen Vision API succeeded: {len(content)} chars")
                    return content
                else:
                    logger.warning(
                        f"Vision API returned {response.status_code}: {response.text[:200]}"
                    )
        except httpx.TimeoutException:
            logger.warning("Vision API timeout — falling back to placeholder")
        except httpx.ConnectError:
            logger.warning("Vision API connection failed — falling back to placeholder")
        except Exception as e:
            logger.warning(f"Vision API error: {e} — falling back to placeholder")

        return None

    async def analyze_screenshot(self, image_path: str, use_omni: bool = False) -> ScreenResult:
        """
        تحليل لقطة شاشة — فهم المحتوى والسياق.

        المعاملات:
            image_path: مسار ملف لقطة الشاشة
            use_omni: استخدام النموذج الموحد (v6.0)

        الإرجاع:
            ScreenResult يحتوي على الوصف والبيانات الوصفية
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "screenshot_analysis",
        }

        # v6.0: Omni-Model integration
        if use_omni or os.getenv("MAMOUN_USE_OMNI", "false").lower() == "true":
            from mamoun.agents.omni_agent import OmniAgent
            omni = OmniAgent()
            omni_result = await omni.process_omnimodal(image_path, "حلل لقطة الشاشة هذه بالتفصيل باللغة العربية")
            return ScreenResult(
                description=omni_result.content,
                coordinates=[],
                confidence=omni_result.confidence,
                metadata={**metadata, "omni_mode": True},
                source_file=str(path),
            )

        # Try to get image dimensions
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
        except ImportError:
            logger.debug("PIL not available — skipping dimension extraction")
        except Exception as e:
            logger.debug(f"Could not read image dimensions: {e}")

        # Try Vision API
        prompt = "حلل لقطة الشاشة هذه بالتفصيل باللغة العربية. صف التطبيق أو الموقع الظاهر، والعناصر المرئية، والنصوص المكتوبة، والسياق العام."
        api_result = await self._call_vision_api(image_path, prompt)

        if api_result:
            metadata["api_model"] = "glm-4v-plus"
            return ScreenResult(
                description=api_result,
                coordinates=[],
                confidence=0.85,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل تحليل لقطات الشاشة"

        return ScreenResult(
            description="[تحليل لقطات الشاشة غير متاح — يجب إعداد مفتاح API]",
            coordinates=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def extract_ui_coordinates(self, image_path: str) -> ScreenResult:
        """
        استخلاص إحداثيات العناصر القابلة للنقر في لقطة الشاشة.

        المعاملات:
            image_path: مسار ملف لقطة الشاشة

        الإرجاع:
            ScreenResult يحتوي على قائمة الإحداثيات
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "ui_coordinates",
        }

        # Try to get image dimensions for coordinate reference
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
        except ImportError:
            logger.debug("PIL not available — skipping dimension extraction")
        except Exception as e:
            logger.debug(f"Could not read image dimensions: {e}")

        # Try Vision API
        prompt = """حدد جميع العناصر القابلة للنقر في لقطة الشاشة هذه. أجب بصيغة JSON بالشكل التالي:
{
  "elements": [
    {
      "type": "button|link|input|menu|icon",
      "label": "النص الظاهر على العنصر",
      "x": 100,
      "y": 200,
      "width": 150,
      "height": 40,
      "confidence": 0.9
    }
  ],
  "total_elements": 5,
  "screen_description": "وصف مختصر للشاشة بالعربية"
}

استخدم إحداثيات البكسل الفعلية قدر الإمكان. أجب فقط بـ JSON صالح بدون أي نص إضافي."""

        api_result = await self._call_vision_api(image_path, prompt)

        if api_result:
            coordinates = []
            description = api_result
            try:
                json_text = api_result
                if "```json" in api_result:
                    json_text = api_result.split("```json")[1].split("```")[0].strip()
                elif "```" in api_result:
                    json_text = api_result.split("```")[1].split("```")[0].strip()

                parsed = json.loads(json_text)
                coordinates = parsed.get("elements", [])
                description = parsed.get("screen_description", api_result)
                metadata["total_elements"] = parsed.get(
                    "total_elements", len(coordinates)
                )
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse UI coordinates as JSON — using raw text"
                )
                metadata["coordinates_raw"] = api_result

            metadata["api_model"] = "glm-4v-plus"
            return ScreenResult(
                description=description,
                coordinates=coordinates,
                confidence=0.75,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل استخلاص إحداثيات واجهة المستخدم"

        return ScreenResult(
            description="[استخلاص إحداثيات واجهة المستخدم غير متاح — يجب إعداد مفتاح API]",
            coordinates=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def describe_ui_layout(self, image_path: str) -> ScreenResult:
        """
        وصف بنية واجهة المستخدم في لقطة الشاشة.

        المعاملات:
            image_path: مسار ملف لقطة الشاشة

        الإرجاع:
            ScreenResult يحتوي على وصف البنية
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "ui_layout",
        }

        # Try to get image dimensions
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
        except ImportError:
            logger.debug("PIL not available — skipping dimension extraction")
        except Exception as e:
            logger.debug(f"Could not read image dimensions: {e}")

        # Try Vision API
        prompt = """صف بنية واجهة المستخدم في لقطة الشاشة هذه بالتفصيل. أجب بصيغة JSON بالشكل التالي:
{
  "layout_type": "single_column|multi_column|dashboard|tabbed|modal|split_view",
  "sections": [
    {
      "region": "top|bottom|left|right|center|sidebar|header|footer",
      "type": "navigation|content|sidebar|header|footer|modal|toolbar",
      "description": "وصف القسم بالعربية",
      "contains": ["عنصر1", "عنصر2"]
    }
  ],
  "responsive_hints": "ملاحظات عن الاستجابة للشاشات المختلفة",
  "interaction_patterns": ["نقر", "تمرير", "إدخال"],
  "detailed_description": "وصف تفصيلي كامل لبنية واجهة المستخدم باللغة العربية"
}

أجب فقط بـ JSON صالح بدون أي نص إضافي."""

        api_result = await self._call_vision_api(image_path, prompt)

        if api_result:
            description = api_result
            try:
                json_text = api_result
                if "```json" in api_result:
                    json_text = api_result.split("```json")[1].split("```")[0].strip()
                elif "```" in api_result:
                    json_text = api_result.split("```")[1].split("```")[0].strip()

                parsed = json.loads(json_text)
                description = parsed.get("detailed_description", api_result)
                metadata["layout_type"] = parsed.get("layout_type", "unknown")
                metadata["sections"] = parsed.get("sections", [])
                metadata["interaction_patterns"] = parsed.get(
                    "interaction_patterns", []
                )
            except json.JSONDecodeError:
                logger.warning(
                    "Could not parse UI layout as JSON — using raw text"
                )
                metadata["layout_raw"] = api_result

            metadata["api_model"] = "glm-4v-plus"
            return ScreenResult(
                description=description,
                coordinates=[],
                confidence=0.8,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل وصف بنية واجهة المستخدم"

        return ScreenResult(
            description="[وصف بنية واجهة المستخدم غير متاح — يجب إعداد مفتاح API]",
            coordinates=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )
