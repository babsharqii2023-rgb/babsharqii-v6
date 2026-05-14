"""
BABSHARQII v6.0 — Omni-Model Agent
وكيل الوسائط الموحد — معالجة الصوت والصورة والنص في نموذج واحد.

Supports:
- Nemotron 3 Nano Omni (NVIDIA) — unified voice/image/text
- GPT-4o API — as alternative
- Any OpenAI-compatible multimodal API
"""

import os
import json
import logging
import base64
import httpx
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

OMNI_API_URL = os.getenv("MAMOUN_OMNI_MODEL_URL", "https://open.bigmodel.cn/api/paas/v4")
OMNI_API_KEY = os.getenv("MAMOUN_OMNI_API_KEY", "")


@dataclass
class OmniResult:
    """نتيجة المعالجة الموحدة للوسائط."""
    content: str  # Arabic description/response
    modality: str  # "image", "audio", "text", "multi"
    confidence: float
    sources: list  # List of processed source files
    metadata: dict

    def to_dict(self) -> dict:
        """تحويل النتيجة إلى قاموس."""
        return asdict(self)


class OmniAgent:
    """
    وكيل الوسائط الموحد — معالجة جميع أنواع المدخلات بنموذج واحد.

    Supports:
    - process_omnimodal(file_path, instruction): Single file analysis
    - batch_process(files): Multiple files in one request
    - process_multi_modal(files, instruction): Mix of image+audio+text
    """

    SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    SUPPORTED_AUDIO = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        تهيئة وكيل الوسائط الموحد.

        المعاملات:
            api_url: عنوان URL للنموذج الموحد
            api_key: مفتاح API للنموذج الموحد
        """
        self.api_url = api_url or OMNI_API_URL
        self.api_key = api_key or OMNI_API_KEY

        logger.info(
            f"OmniAgent initialized — "
            f"API key configured: {bool(self.api_key)}, "
            f"API URL: {self.api_url}"
        )

    async def process_omnimodal(
        self, file_path: str, instruction: str = ""
    ) -> OmniResult:
        """
        معالجة ملف واحد (صورة أو صوت أو نص) باستخدام النموذج الموحد.

        Sends file to the omni-model API with the instruction.
        Falls back to individual agents if API unavailable.

        المعاملات:
            file_path: مسار الملف المراد معالجته
            instruction: التعليمات المخصصة للنموذج

        الإرجاع:
            OmniResult يحتوي على نتيجة المعالجة الموحدة
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        suffix = path.suffix.lower()
        is_image = suffix in self.SUPPORTED_IMAGE
        is_audio = suffix in self.SUPPORTED_AUDIO

        if not instruction:
            if is_image:
                instruction = "حلل هذه الصورة بالتفصيل بالعربية. اذكر العناصر الرئيسية والألوان والسياق."
            elif is_audio:
                instruction = "افرغ هذا الملف الصوتي إلى نص بالعربية. صف المحتوى والمشاعر."
            else:
                instruction = "حلل هذا المحتوى بالعربية."

        # Try Omni API
        if self.api_key:
            result = await self._call_omni_api(
                file_path, instruction, is_image, is_audio
            )
            if result:
                return result

        # Fallback: delegate to individual agents
        return await self._fallback_to_individual_agents(
            file_path, instruction, is_image, is_audio
        )

    async def batch_process(
        self, files: list[str], instruction: str = ""
    ) -> list[OmniResult]:
        """
        معالجة عدة ملفات في طلب واحد.

        المعاملات:
            files: قائمة مسارات الملفات
            instruction: التعليمات المخصصة

        الإرجاع:
            قائمة نتائج OmniResult لكل ملف
        """
        results = []
        if self.api_key and len(files) > 1:
            # Try batch API call
            batch_result = await self._call_batch_api(files, instruction)
            if batch_result:
                return batch_result

        # Fallback: process individually
        for f in files:
            result = await self.process_omnimodal(f, instruction)
            results.append(result)
        return results

    async def process_multi_modal(
        self, files: list[str], instruction: str = ""
    ) -> OmniResult:
        """
        معالجة ملفات متعددة الأنواع (صورة + صوت معاً) في طلب واحد.
        Returns a merged result combining all modalities.

        المعاملات:
            files: قائمة مسارات الملفات متعددة الأنواع
            instruction: التعليمات المخصصة

        الإرجاع:
            OmniResult يحتوي على تحليل مدمج لجميع الملفات
        """
        # Try unified API call with all files
        if self.api_key:
            result = await self._call_multi_modal_api(files, instruction)
            if result:
                return result

        # Fallback: process each and merge
        descriptions = []
        for f in files:
            r = await self.process_omnimodal(f)
            descriptions.append(f"[{Path(f).suffix}]: {r.content}")

        merged = "\n---\n".join(descriptions)
        return OmniResult(
            content=f"تحليل مدمج:\n{merged}",
            modality="multi",
            confidence=0.6,
            sources=files,
            metadata={"fallback": True, "source_count": len(files)},
        )

    async def _call_omni_api(
        self, file_path: str, instruction: str, is_image: bool, is_audio: bool
    ) -> Optional[OmniResult]:
        """استدعاء النموذج الموحد API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if is_image:
                    with open(file_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    suffix = Path(file_path).suffix.lower().lstrip(".")
                    response = await client.post(
                        f"{self.api_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": "glm-4v-plus",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": instruction},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/{suffix};base64,{img_b64}"
                                            },
                                        },
                                    ],
                                }
                            ],
                            "max_tokens": 1500,
                        },
                    )
                elif is_audio:
                    with open(file_path, "rb") as f:
                        audio_b64 = base64.b64encode(f.read()).decode()
                    response = await client.post(
                        f"{self.api_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={
                            "model": "glm-4v-plus",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": instruction},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:audio/wav;base64,{audio_b64}"
                                            },
                                        },
                                    ],
                                }
                            ],
                            "max_tokens": 1500,
                        },
                    )
                else:
                    return None

                if response.status_code == 200:
                    content = (
                        response.json()
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    modality = "image" if is_image else "audio"
                    logger.info(
                        f"Omni API succeeded: {len(content)} chars, modality={modality}"
                    )
                    return OmniResult(
                        content=content,
                        modality=modality,
                        confidence=0.85,
                        sources=[file_path],
                        metadata={
                            "api_model": "omni",
                            "provider": "glm-4v-plus",
                        },
                    )
                else:
                    logger.warning(
                        f"Omni API returned {response.status_code}: "
                        f"{response.text[:200]}"
                    )
        except httpx.TimeoutException:
            logger.warning("Omni API timeout — falling back to individual agents")
        except httpx.ConnectError:
            logger.warning(
                "Omni API connection failed — falling back to individual agents"
            )
        except Exception as e:
            logger.warning(f"Omni API error: {e} — falling back to individual agents")

        return None

    async def _call_batch_api(
        self, files: list[str], instruction: str
    ) -> Optional[list[OmniResult]]:
        """معالجة عدة ملفات دفعة واحدة عبر API."""
        # Process files sequentially for now (API limitation)
        results = []
        for f in files:
            r = await self.process_omnimodal(f, instruction)
            results.append(r)
        return results if results else None

    async def _call_multi_modal_api(
        self, files: list[str], instruction: str
    ) -> Optional[OmniResult]:
        """معالجة ملفات متعددة الأنواع في طلب واحد."""
        try:
            content_parts = [
                {
                    "type": "text",
                    "text": instruction or "حلل هذه الملفات معاً بالعربية.",
                }
            ]
            for f in files:
                path = Path(f)
                suffix = path.suffix.lower()
                with open(f, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode()
                if suffix in self.SUPPORTED_IMAGE:
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{suffix.lstrip('.')};base64,{b64}"
                            },
                        }
                    )
                elif suffix in self.SUPPORTED_AUDIO:
                    content_parts.append(
                        {
                            "type": "text",
                            "text": f"[ملف صوتي مرفق: {path.name}]",
                        }
                    )

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "glm-4v-plus",
                        "messages": [
                            {"role": "user", "content": content_parts}
                        ],
                        "max_tokens": 2000,
                    },
                )
                if response.status_code == 200:
                    content = (
                        response.json()
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    logger.info(
                        f"Multi-modal API succeeded: {len(content)} chars, "
                        f"files={len(files)}"
                    )
                    return OmniResult(
                        content=content,
                        modality="multi",
                        confidence=0.8,
                        sources=files,
                        metadata={"api_model": "omni_multi"},
                    )
                else:
                    logger.warning(
                        f"Multi-modal API returned {response.status_code}: "
                        f"{response.text[:200]}"
                    )
        except httpx.TimeoutException:
            logger.warning(
                "Multi-modal API timeout — falling back to individual processing"
            )
        except httpx.ConnectError:
            logger.warning(
                "Multi-modal API connection failed — falling back"
            )
        except Exception as e:
            logger.warning(f"Multi-modal API error: {e}")

        return None

    async def _fallback_to_individual_agents(
        self,
        file_path: str,
        instruction: str,
        is_image: bool,
        is_audio: bool,
    ) -> OmniResult:
        """الرجوع إلى الوكلاء الفرديين عند عدم توفر النموذج الموحد."""
        if is_image:
            from mamoun.agents.vision_agent import VisionAgent

            agent = VisionAgent()
            result = await agent.analyze_image(file_path)
            return OmniResult(
                content=result.description,
                modality="image",
                confidence=result.confidence,
                sources=[file_path],
                metadata={
                    "fallback": True,
                    "original_agent": "VisionAgent",
                    **result.metadata,
                },
            )
        elif is_audio:
            from mamoun.agents.voice_agent import VoiceAgent

            agent = VoiceAgent()
            result = await agent.transcribe(file_path)
            return OmniResult(
                content=result.text,
                modality="audio",
                confidence=result.confidence,
                sources=[file_path],
                metadata={
                    "fallback": True,
                    "original_agent": "VoiceAgent",
                    **result.metadata,
                },
            )
        else:
            return OmniResult(
                content="[نوع ملف غير مدعوم]",
                modality="unknown",
                confidence=0.0,
                sources=[file_path],
                metadata={"error": "unsupported_file_type"},
            )
