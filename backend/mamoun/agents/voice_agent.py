"""
BABSHARQII v40.0 — Voice Agent
وكيل الصوت — تفريغ صوتي وكشف اللغة وتحليل أنماط الكلام.
"""

import os
import json
import logging
import httpx
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VoiceResult:
    """نتيجة معالجة الصوت."""
    text: str  # النص المفرّغ أو الوصف بالعربية
    language: str  # رمز اللغة المكتشفة
    confidence: float
    metadata: dict
    source_file: str

    def to_dict(self) -> dict:
        """تحويل النتيجة إلى قاموس."""
        return asdict(self)


class VoiceAgent:
    """
    وكيل الصوت لمأمون.

    يتخصص في:
    - تفريغ الصوت إلى نص (Transcription)
    - كشف اللغة المنطوقة
    - تحليل أنماط الكلام (النبرة، السرعة، المشاعر)
    """

    SUPPORTED_AUDIO = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}

    def __init__(
        self,
        glm_api_key: Optional[str] = None,
        llm_api_url: Optional[str] = None,
    ):
        """
        تهيئة وكيل الصوت.

        المعاملات:
            glm_api_key: مفتاح API العام
            llm_api_url: عنوان URL للـ API
        """
        self.glm_api_key = glm_api_key or os.getenv("MAMOUN_GLM_API_KEY", "")
        self.llm_api_url = llm_api_url or os.getenv(
            "MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4"
        )

        logger.info(
            f"VoiceAgent initialized — "
            f"API key configured: {bool(self.glm_api_key)}, "
            f"LLM URL: {self.llm_api_url}"
        )

    def _validate_audio(self, audio_path: str) -> Path:
        """التحقق من صلاحية مسار الملف الصوتي."""
        path = Path(audio_path)

        if not path.exists():
            raise FileNotFoundError(f"الملف الصوتي غير موجود: {audio_path}")

        if path.suffix.lower() not in self.SUPPORTED_AUDIO:
            raise ValueError(
                f"صيغة صوتية غير مدعومة: {path.suffix}. "
                f"الصيغ المدعومة: {self.SUPPORTED_AUDIO}"
            )

        return path

    async def transcribe(self, audio_path: str, language: str = "ar", use_omni: bool = False) -> VoiceResult:
        """
        تفريغ صوتي — تحويل الكلام إلى نص.

        المعاملات:
            audio_path: مسار الملف الصوتي
            language: رمز اللغة المتوقعة (افتراضي: العربية)
            use_omni: استخدام النموذج الموحد (v6.0)

        الإرجاع:
            VoiceResult يحتوي على النص المفرّغ
        """
        path = self._validate_audio(audio_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "requested_language": language,
            "analysis_type": "transcription",
        }

        # v6.0: Omni-Model integration
        if use_omni or os.getenv("MAMOUN_USE_OMNI", "false").lower() == "true":
            from mamoun.agents.omni_agent import OmniAgent
            omni = OmniAgent()
            omni_result = await omni.process_omnimodal(audio_path, "افرغ هذا الملف الصوتي إلى نص بالعربية")
            return VoiceResult(
                text=omni_result.content,
                language=language,
                confidence=omni_result.confidence,
                metadata={**metadata, "omni_mode": True},
                source_file=str(path),
            )

        # Try Whisper API
        whisper_url = f"{self.llm_api_url}/audio/transcriptions"

        if self.glm_api_key:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(audio_path, "rb") as audio_file:
                        response = await client.post(
                            whisper_url,
                            headers={
                                "Authorization": f"Bearer {self.glm_api_key}",
                            },
                            files={
                                "file": (
                                    path.name,
                                    audio_file,
                                    f"audio/{metadata['format']}",
                                ),
                            },
                            data={
                                "model": "whisper-1",
                                "language": language,
                                "response_format": "verbose_json",
                            },
                        )

                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("text", "")
                        metadata.update(
                            {
                                "language": result.get("language", language),
                                "duration": result.get("duration", 0),
                                "segments": len(result.get("segments", [])),
                            }
                        )

                        logger.info(
                            f"Audio transcribed successfully: {len(content)} chars"
                        )
                        return VoiceResult(
                            text=content,
                            language=result.get("language", language),
                            confidence=0.9,
                            metadata=metadata,
                            source_file=str(path),
                        )
                    else:
                        logger.warning(
                            f"Whisper API returned {response.status_code}: "
                            f"{response.text[:200]}"
                        )
            except httpx.TimeoutException:
                logger.warning("Whisper API timeout — falling back to placeholder")
            except httpx.ConnectError:
                logger.warning(
                    "Whisper API connection failed — falling back to placeholder"
                )
            except Exception as e:
                logger.warning(
                    f"Whisper API error: {e} — falling back to placeholder"
                )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = (
            "يجب إعداد MAMOUN_GLM_API_KEY لتفعيل التفريغ الصوتي عبر Whisper API"
        )
        metadata["setup_instructions"] = {
            "env_var": "MAMOUN_GLM_API_KEY",
            "api_url": whisper_url,
            "model": "whisper-1",
        }

        return VoiceResult(
            text="[تفريغ صوتي غير متاح — يجب إعداد مفتاح API]",
            language=language,
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def detect_language(self, audio_path: str) -> VoiceResult:
        """
        كشف اللغة المنطوقة في الملف الصوتي.

        المعاملات:
            audio_path: مسار الملف الصوتي

        الإرجاع:
            VoiceResult يحتوي على اللغة المكتشفة
        """
        path = self._validate_audio(audio_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "language_detection",
        }

        # Try Whisper API with language detection
        whisper_url = f"{self.llm_api_url}/audio/transcriptions"

        if self.glm_api_key:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(audio_path, "rb") as audio_file:
                        response = await client.post(
                            whisper_url,
                            headers={
                                "Authorization": f"Bearer {self.glm_api_key}",
                            },
                            files={
                                "file": (
                                    path.name,
                                    audio_file,
                                    f"audio/{metadata['format']}",
                                ),
                            },
                            data={
                                "model": "whisper-1",
                                "response_format": "verbose_json",
                            },
                        )

                    if response.status_code == 200:
                        result = response.json()
                        detected_lang = result.get("language", "unknown")
                        content = result.get("text", "")

                        language_names = {
                            "ar": "العربية",
                            "en": "الإنجليزية",
                            "fr": "الفرنسية",
                            "es": "الإسبانية",
                            "de": "الألمانية",
                            "tr": "التركية",
                            "ur": "الأردية",
                            "fa": "الفارسية",
                            "zh": "الصينية",
                            "ja": "اليابانية",
                        }

                        lang_name = language_names.get(detected_lang, detected_lang)

                        metadata["detected_language"] = detected_lang
                        metadata["detected_language_name"] = lang_name
                        metadata["duration"] = result.get("duration", 0)

                        logger.info(
                            f"Language detected: {detected_lang} ({lang_name})"
                        )
                        return VoiceResult(
                            text=f"اللغة المكتشفة: {lang_name} ({detected_lang})",
                            language=detected_lang,
                            confidence=0.85,
                            metadata=metadata,
                            source_file=str(path),
                        )
                    else:
                        logger.warning(
                            f"Whisper API returned {response.status_code}: "
                            f"{response.text[:200]}"
                        )
            except httpx.TimeoutException:
                logger.warning("Whisper API timeout — falling back to placeholder")
            except httpx.ConnectError:
                logger.warning(
                    "Whisper API connection failed — falling back to placeholder"
                )
            except Exception as e:
                logger.warning(
                    f"Whisper API error: {e} — falling back to placeholder"
                )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = (
            "يجب إعداد MAMOUN_GLM_API_KEY لتفعيل كشف اللغة عبر Whisper API"
        )

        return VoiceResult(
            text="[كشف اللغة غير متاح — يجب إعداد مفتاح API]",
            language="unknown",
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def analyze_speech_patterns(self, audio_path: str) -> VoiceResult:
        """
        تحليل أنماط الكلام — النبرة، السرعة، المشاعر.

        المعاملات:
            audio_path: مسار الملف الصوتي

        الإرجاع:
            VoiceResult يحتوي على تحليل أنماط الكلام
        """
        path = self._validate_audio(audio_path)
        file_size = path.stat().st_size

        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
            "analysis_type": "speech_patterns",
        }

        # Try Whisper API for transcription first, then analyze patterns
        whisper_url = f"{self.llm_api_url}/audio/transcriptions"

        if self.glm_api_key:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(audio_path, "rb") as audio_file:
                        response = await client.post(
                            whisper_url,
                            headers={
                                "Authorization": f"Bearer {self.glm_api_key}",
                            },
                            files={
                                "file": (
                                    path.name,
                                    audio_file,
                                    f"audio/{metadata['format']}",
                                ),
                            },
                            data={
                                "model": "whisper-1",
                                "language": "ar",
                                "response_format": "verbose_json",
                            },
                        )

                    if response.status_code == 200:
                        result = response.json()
                        segments = result.get("segments", [])
                        duration = result.get("duration", 0)

                        # Calculate speech patterns from segments
                        word_count = sum(
                            len(seg.get("text", "").split()) for seg in segments
                        )
                        words_per_minute = (
                            (word_count / duration) * 60 if duration > 0 else 0
                        )

                        # Analyze pace
                        if words_per_minute > 160:
                            pace = "سريع"
                            pace_ar = "سريع"
                        elif words_per_minute > 120:
                            pace = "moderate"
                            pace_ar = "معتدل"
                        else:
                            pace = "slow"
                            pace_ar = "بطيء"

                        # Analyze volume variation from segments
                        avg_segment_duration = (
                            sum(
                                seg.get("end", 0) - seg.get("start", 0)
                                for seg in segments
                            )
                            / len(segments)
                            if segments
                            else 0
                        )

                        # Determine tone based on speech patterns
                        if avg_segment_duration > 3:
                            tone = "هادئ ومتأنٍ"
                        elif avg_segment_duration > 1.5:
                            tone = "معتدل"
                        else:
                            tone = "سريع ومتوتر"

                        analysis = (
                            f"تحليل أنماط الكلام:\n"
                            f"- السرعة: {pace_ar} ({words_per_minute:.0f} كلمة/دقيقة)\n"
                            f"- النبرة: {tone}\n"
                            f"- المدة: {duration:.1f} ثانية\n"
                            f"- عدد الكلمات: {word_count}\n"
                            f"- عدد المقاطع: {len(segments)}\n"
                            f"- متوسط مدة المقطع: {avg_segment_duration:.2f} ثانية"
                        )

                        metadata.update(
                            {
                                "words_per_minute": round(words_per_minute, 1),
                                "pace": pace,
                                "tone": tone,
                                "duration": duration,
                                "word_count": word_count,
                                "segment_count": len(segments),
                                "avg_segment_duration": round(
                                    avg_segment_duration, 2
                                ),
                            }
                        )

                        logger.info(
                            f"Speech patterns analyzed: {words_per_minute:.0f} wpm, {pace}"
                        )
                        return VoiceResult(
                            text=analysis,
                            language=result.get("language", "ar"),
                            confidence=0.75,
                            metadata=metadata,
                            source_file=str(path),
                        )
                    else:
                        logger.warning(
                            f"Whisper API returned {response.status_code}: "
                            f"{response.text[:200]}"
                        )
            except httpx.TimeoutException:
                logger.warning("Whisper API timeout — falling back to placeholder")
            except httpx.ConnectError:
                logger.warning(
                    "Whisper API connection failed — falling back to placeholder"
                )
            except Exception as e:
                logger.warning(
                    f"Whisper API error: {e} — falling back to placeholder"
                )

        # Fallback placeholder
        metadata["status"] = "placeholder"
        metadata["message"] = (
            "يجب إعداد MAMOUN_GLM_API_KEY لتفعيل تحليل أنماط الكلام"
        )

        return VoiceResult(
            text="[تحليل أنماط الكلام غير متاح — يجب إعداد مفتاح API]",
            language="unknown",
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )
