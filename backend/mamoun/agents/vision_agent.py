"""
BABSHARQII v40.0 — Vision Agent
وكيل الرؤية — تحليل الصور والتصنيف واستخلاص النصوص وتحليل الديكور.
"""

import os
import json
import logging
import base64
import httpx
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from mamoun.core.multimodal_processor import MultimodalProcessor

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    """نتيجة تحليل الصورة."""
    description: str  # وصف نصي بالعربية
    categories: list  # فئات التصنيف
    confidence: float
    metadata: dict
    source_file: str

    def to_dict(self) -> dict:
        """تحويل النتيجة إلى قاموس."""
        return asdict(self)


class VisionAgent:
    """
    وكيل الرؤية لمأمون.

    يتخصص في:
    - تحليل الصور العامة
    - تصنيف الصور
    - استخلاص النصوص من الصور (OCR)
    - تحليل أسلوب الديكور
    """

    SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    def __init__(
        self,
        vision_api_key: Optional[str] = None,
        llm_api_url: Optional[str] = None,
    ):
        """
        تهيئة وكيل الرؤية.

        المعاملات:
            vision_api_key: مفتاح API للرؤية
            llm_api_url: عنوان URL للـ API
        """
        self.vision_api_key = vision_api_key or os.getenv("MAMOUN_VISION_API_KEY", "")
        self.llm_api_url = llm_api_url or os.getenv(
            "MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4"
        )

        # Initialize MultimodalProcessor for decor analysis delegation
        self._processor = MultimodalProcessor(
            llm_api_url=self.llm_api_url,
            vision_api_key=self.vision_api_key,
        )

        logger.info(
            f"VisionAgent initialized — "
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
                        "max_tokens": 1024,
                    },
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    logger.info(f"Vision API succeeded: {len(content)} chars")
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

    async def analyze_image(self, image_path: str, use_omni: bool = False) -> VisionResult:
        """
        تحليل صورة عامة — وصف تفصيلي بالعربية.

        المعاملات:
            image_path: مسار ملف الصورة
            use_omni: استخدام النموذج الموحد (v6.0)

        الإرجاع:
            VisionResult يحتوي على الوصف والبيانات الوصفية
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "general",
        }

        # v6.0: Omni-Model integration
        if use_omni or os.getenv("MAMOUN_USE_OMNI", "false").lower() == "true":
            from mamoun.agents.omni_agent import OmniAgent
            omni = OmniAgent()
            omni_result = await omni.process_omnimodal(image_path, "صف هذه الصورة بالتفصيل باللغة العربية")
            return VisionResult(
                description=omni_result.content,
                categories=[],
                confidence=omni_result.confidence,
                metadata={**metadata, "omni_mode": True},
                source_file=str(path),
            )

        # Try Vision API
        prompt = "صف هذه الصورة بالتفصيل باللغة العربية. اذكر العناصر الرئيسية والألوان والسياق والمشاعر التي تثيرها."
        api_result = await self._call_vision_api(image_path, prompt)

        if api_result:
            metadata["api_model"] = "glm-4v-plus"
            return VisionResult(
                description=api_result,
                categories=[],
                confidence=0.85,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل تحليل الصور"

        return VisionResult(
            description="[تحليل الصور غير متاح — يجب إعداد مفتاح API]",
            categories=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def classify_image(self, image_path: str) -> VisionResult:
        """
        تصنيف الصورة — إرجاع فئات التصنيف.

        المعاملات:
            image_path: مسار ملف الصورة

        الإرجاع:
            VisionResult يحتوي على الفئات والوصف
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "classification",
        }

        # Try Vision API
        prompt = """صنّف هذه الصورة. أجب بصيغة JSON بالشكل التالي:
{
  "categories": ["الفئة1", "الفئة2", "الفئة3"],
  "primary_category": "الفئة الرئيسية",
  "description": "وصف مختصر بالعربية"
}

أجب فقط بـ JSON صالح بدون أي نص إضافي."""

        api_result = await self._call_vision_api(image_path, prompt)

        if api_result:
            categories = []
            description = api_result
            try:
                json_text = api_result
                if "```json" in api_result:
                    json_text = api_result.split("```json")[1].split("```")[0].strip()
                elif "```" in api_result:
                    json_text = api_result.split("```")[1].split("```")[0].strip()

                parsed = json.loads(json_text)
                categories = parsed.get("categories", [])
                description = parsed.get("description", api_result)
                metadata["primary_category"] = parsed.get("primary_category", "")
            except json.JSONDecodeError:
                logger.warning("Could not parse classification as JSON — using raw text")
                metadata["classification_raw"] = api_result

            metadata["api_model"] = "glm-4v-plus"
            return VisionResult(
                description=description,
                categories=categories,
                confidence=0.8,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل تصنيف الصور"

        return VisionResult(
            description="[تصنيف الصور غير متاح — يجب إعداد مفتاح API]",
            categories=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def extract_text_from_image(self, image_path: str) -> VisionResult:
        """
        استخلاص النصوص من الصورة (OCR) — إرجاع النصوص المكتشفة.

        المعاملات:
            image_path: مسار ملف الصورة

        الإرجاع:
            VisionResult يحتوي على النصوص المستخلصة
        """
        path = self._validate_image(image_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "ocr",
        }

        # Try Vision API
        prompt = """استخلص جميع النصوص المكتوبة في هذه الصورة. أجب بصيغة JSON بالشكل التالي:
{
  "text_blocks": ["النص1", "النص2"],
  "full_text": "كل النصوص مجمعة",
  "languages_detected": ["ar", "en"],
  "confidence": 0.9
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
                description = parsed.get("full_text", api_result)
                metadata["text_blocks"] = parsed.get("text_blocks", [])
                metadata["languages_detected"] = parsed.get("languages_detected", [])
                ocr_confidence = parsed.get("confidence", 0.8)
            except json.JSONDecodeError:
                logger.warning("Could not parse OCR result as JSON — using raw text")
                ocr_confidence = 0.7

            metadata["api_model"] = "glm-4v-plus"
            return VisionResult(
                description=description,
                categories=[],
                confidence=ocr_confidence,
                metadata=metadata,
                source_file=str(path),
            )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل استخلاص النصوص"

        return VisionResult(
            description="[استخلاص النصوص غير متاح — يجب إعداد مفتاح API]",
            categories=[],
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def analyze_decor_style(self, image_path: str) -> VisionResult:
        """
        تحليل أسلوب الديكور — يفوّض إلى MultimodalProcessor.

        المعاملات:
            image_path: مسار ملف الصورة

        الإرجاع:
            VisionResult يحتوي على تحليل الديكور
        """
        path = self._validate_image(image_path)

        # Delegate to MultimodalProcessor's analyze_decor_style
        result = await self._processor.analyze_decor_style(image_path)

        metadata = result.metadata.copy()
        metadata["analysis_type"] = "decor_style"
        metadata["delegated_to"] = "MultimodalProcessor"

        return VisionResult(
            description=result.content,
            categories=[],
            confidence=result.confidence,
            metadata=metadata,
            source_file=str(path),
        )
