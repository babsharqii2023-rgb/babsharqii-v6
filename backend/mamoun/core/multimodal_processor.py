"""
BABSHARQII v40.0 — Multimodal Processor
يعالج المدخلات متعددة الوسائط (صوت، صورة، نص) ويوجهها للنموذج المناسب.
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
class ProcessingResult:
    """نتيجة معالجة ملف متعدد الوسائط."""
    modality: str  # "audio", "image", "text"
    content: str  # Extracted text or description
    confidence: float
    metadata: dict  # Extra info (language, dimensions, duration, etc.)
    source_file: str

    def to_dict(self) -> dict:
        """تحويل النتيجة إلى قاموس."""
        return asdict(self)


class MultimodalProcessor:
    """
    معالج متعدد الوسائط لمأمون.
    
    يدعم:
    - صوت: تفريغ عبر Whisper API أو محلي
    - صورة: وصف وتحليل عبر Vision API أو BLIP
    - تحليل ديكور: استخلاص أنماط وألوان وعناصر
    """
    
    SUPPORTED_AUDIO = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}
    SUPPORTED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(
        self,
        upload_dir: Optional[str] = None,
        llm_api_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        vision_api_key: Optional[str] = None,
    ):
        """
        تهيئة المعالج متعدد الوسائط.
        
        المعاملات:
            upload_dir: مجلد حفظ الملفات المرفوعة
            llm_api_url: عنوان URL للـ API
            llm_api_key: مفتاح API العام
            vision_api_key: مفتاح API للرؤية
        """
        # Read API config from env vars or use provided values
        self.llm_api_url = llm_api_url or os.getenv("MAMOUN_LLM_API_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.llm_api_key = llm_api_key or os.getenv("MAMOUN_GLM_API_KEY", "")
        self.vision_api_key = vision_api_key or os.getenv("MAMOUN_VISION_API_KEY", self.llm_api_key)
        
        # Setup upload directory
        if upload_dir:
            self.upload_dir = Path(upload_dir)
        else:
            self.upload_dir = Path(os.getenv("MAMOUN_UPLOAD_DIR", "/tmp/mamoun_uploads"))
        
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"MultimodalProcessor initialized — "
            f"LLM URL: {self.llm_api_url}, "
            f"API key configured: {bool(self.llm_api_key)}, "
            f"Vision key configured: {bool(self.vision_api_key)}, "
            f"Upload dir: {self.upload_dir}"
        )

    async def process_file(self, file_path: str, modality_hint: str = "") -> ProcessingResult:
        """
        معالجة ملف وتحديد نوعه تلقائياً إذا لم يُحدد.
        
        المعاملات:
            file_path: مسار الملف المراد معالجته
            modality_hint: تلميح عن نوع الوسائط (اختياري)
        
        الإرجاع:
            ProcessingResult نتيجة المعالجة
        
        الاستثناءات:
            FileNotFoundError: إذا لم يكن الملف موجوداً
            ValueError: إذا كان الملف كبيراً جداً أو غير مدعوم
        """
        path = Path(file_path)
        
        # Validate file exists
        if not path.exists():
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")
        
        # Validate file size
        file_size = path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"حجم الملف ({file_size / (1024*1024):.1f}MB) يتجاوز الحد الأقصى "
                f"({self.MAX_FILE_SIZE / (1024*1024):.0f}MB)"
            )
        
        # Detect modality
        modality = modality_hint if modality_hint else self._detect_modality(file_path)
        
        logger.info(f"Processing file: {file_path} as {modality} ({file_size} bytes)")
        
        if modality == "audio":
            return await self.transcribe_audio(file_path)
        elif modality == "image":
            return await self.analyze_image(file_path)
        elif modality == "text":
            return await self._process_text_file(file_path)
        else:
            raise ValueError(
                f"نوع الملف غير مدعوم: {path.suffix}. "
                f"الأنواع المدعومة: صوت {self.SUPPORTED_AUDIO}, صور {self.SUPPORTED_IMAGE}"
            )

    async def transcribe_audio(self, file_path: str) -> ProcessingResult:
        """
        تفريغ صوتي عبر Whisper API أو معالجة محلية.
        
        يحاول الاتصال بـ Whisper API أولاً. إذا لم يكن متاحاً،
        يُرجع نتيجة مؤقتة تشير إلى ضرورة الإعداد.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"الملف الصوتي غير موجود: {file_path}")
        
        # Validate audio format
        if path.suffix.lower() not in self.SUPPORTED_AUDIO:
            raise ValueError(
                f"صيغة صوتية غير مدعومة: {path.suffix}. "
                f"الصيغ المدعومة: {self.SUPPORTED_AUDIO}"
            )
        
        file_size = path.stat().st_size
        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
        }
        
        # Try Whisper API
        whisper_url = f"{self.llm_api_url}/audio/transcriptions"
        
        if self.llm_api_key:
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    with open(file_path, "rb") as audio_file:
                        response = await client.post(
                            whisper_url,
                            headers={
                                "Authorization": f"Bearer {self.llm_api_key}",
                            },
                            files={
                                "file": (path.name, audio_file, f"audio/{metadata['format']}"),
                            },
                            data={
                                "model": "whisper-1",
                                "language": "ar",
                                "response_format": "verbose_json",
                            },
                        )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("text", "")
                        metadata.update({
                            "language": result.get("language", "ar"),
                            "duration": result.get("duration", 0),
                            "segments": len(result.get("segments", [])),
                        })
                        
                        logger.info(f"Audio transcribed successfully: {len(content)} chars")
                        return ProcessingResult(
                            modality="audio",
                            content=content,
                            confidence=0.9,
                            metadata=metadata,
                            source_file=str(path),
                        )
                    else:
                        logger.warning(
                            f"Whisper API returned {response.status_code}: {response.text[:200]}"
                        )
            except httpx.TimeoutException:
                logger.warning("Whisper API timeout — falling back to placeholder")
            except httpx.ConnectError:
                logger.warning("Whisper API connection failed — falling back to placeholder")
            except Exception as e:
                logger.warning(f"Whisper API error: {e} — falling back to placeholder")
        
        # Fallback: placeholder result
        logger.info(f"Returning placeholder for audio file: {file_path}")
        metadata.update({
            "status": "placeholder",
            "message": "يجب إعداد MAMOUN_GLM_API_KEY لتفعيل التفريغ الصوتي عبر Whisper API",
            "setup_instructions": {
                "env_var": "MAMOUN_GLM_API_KEY",
                "api_url": whisper_url,
                "model": "whisper-1",
            },
        })
        
        return ProcessingResult(
            modality="audio",
            content="[تفريغ صوتي غير متاح — يجب إعداد مفتاح API]",
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def analyze_image(self, file_path: str) -> ProcessingResult:
        """
        تحليل صورة واستخلاص وصف نصي.
        
        يحاول الاتصال بـ Vision API أولاً. إذا لم يكن متاحاً،
        يُرجع نتيجة مؤقتة تحتوي على معلومات الملف الأساسية.
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"ملف الصورة غير موجود: {file_path}")
        
        # Validate image format
        if path.suffix.lower() not in self.SUPPORTED_IMAGE:
            raise ValueError(
                f"صيغة صورة غير مدعومة: {path.suffix}. "
                f"الصيغ المدعومة: {self.SUPPORTED_IMAGE}"
            )
        
        file_size = path.stat().st_size
        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "file_name": path.name,
        }
        
        # Try to get image dimensions
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["mode"] = img.mode
        except ImportError:
            logger.debug("PIL not available — skipping dimension extraction")
        except Exception as e:
            logger.debug(f"Could not read image dimensions: {e}")
        
        # Try Vision API with base64 encoding
        if self.vision_api_key:
            try:
                import base64
                
                with open(file_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                vision_url = f"{self.llm_api_url}/chat/completions"
                
                prompt = "صف هذه الصورة بالتفصيل باللغة العربية. اذكر العناصر الرئيسية والألوان والسياق."
                
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
                                                "url": f"data:image/{metadata['format']};base64,{img_data}"
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
                        
                        metadata.update({
                            "api_model": "glm-4v-plus",
                            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        })
                        
                        logger.info(f"Image analyzed successfully: {len(content)} chars")
                        return ProcessingResult(
                            modality="image",
                            content=content,
                            confidence=0.85,
                            metadata=metadata,
                            source_file=str(path),
                        )
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
        
        # Fallback: placeholder result
        logger.info(f"Returning placeholder for image file: {file_path}")
        dimensions = ""
        if "width" in metadata and "height" in metadata:
            dimensions = f" ({metadata['width']}x{metadata['height']})"
        
        metadata.update({
            "status": "placeholder",
            "message": "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل تحليل الصور عبر Vision API",
            "setup_instructions": {
                "env_var": "MAMOUN_VISION_API_KEY",
                "api_model": "glm-4v-plus",
            },
        })
        
        return ProcessingResult(
            modality="image",
            content=f"[صورة{dimensions} — تحليل الصور غير متاح، يجب إعداد مفتاح API]",
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    async def analyze_decor_style(self, file_path: str) -> ProcessingResult:
        """
        تحليل أسلوب الديكور في صورة — ألوان، أنماط، عناصر.
        
        تحليل متخصص للصور يركز على:
        - لوحة الألوان السائدة
        - أنماط الأثاث والتصميم
        - أسلوب الإضاءة
        - المواد والخامات المستخدمة
        - عناصر الديكور البارزة
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"ملف الصورة غير موجود: {file_path}")
        
        # Validate image format
        if path.suffix.lower() not in self.SUPPORTED_IMAGE:
            raise ValueError(
                f"صيغة صورة غير مدعومة: {path.suffix}. "
                f"الصيغ المدعومة: {self.SUPPORTED_IMAGE}"
            )
        
        file_size = path.stat().st_size
        metadata = {
            "format": path.suffix.lower().lstrip("."),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "analysis_type": "decor_style",
        }
        
        # Try to extract color palette from the image
        color_palette = []
        try:
            from PIL import Image
            import collections
            
            with Image.open(file_path) as img:
                img_small = img.resize((100, 100))
                pixels = list(img_small.getdata())
                
                # Simple color quantization
                color_counts = collections.Counter(pixels)
                top_colors = color_counts.most_common(8)
                
                for color, count in top_colors:
                    if isinstance(color, tuple) and len(color) >= 3:
                        hex_color = "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])
                        color_palette.append({
                            "hex": hex_color,
                            "rgb": list(color[:3]),
                            "frequency": round(count / len(pixels), 3),
                        })
        except ImportError:
            logger.debug("PIL not available — skipping color extraction")
        except Exception as e:
            logger.debug(f"Could not extract color palette: {e}")
        
        if color_palette:
            metadata["extracted_colors"] = color_palette
        
        # Try Vision API with specialized decor analysis prompt
        if self.vision_api_key:
            try:
                import base64
                
                with open(file_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode("utf-8")
                
                vision_url = f"{self.llm_api_url}/chat/completions"
                
                decor_prompt = """حلل أسلوب الديكور في هذه الصورة بالتفصيل. أجب بصيغة JSON بالشكل التالي:
{
  "style": "أسلوب الديكور الرئيسي (مثلاً: حديث، كلاسيكي، بوهيمي، إسكندنافي، عربي تقليدي، إلخ)",
  "color_palette": ["اللون1", "اللون2", "اللون3"],
  "patterns": ["النمط1", "النمط2"],
  "furniture_style": "وصف أسلوب الأثاث",
  "lighting": "وصف نوع الإضاءة وطبيعتها",
  "materials": ["المادة1", "المادة2"],
  "decorative_elements": ["العنصر1", "العنصر2"],
  "overall_mood": "المزاج العام للفراغ",
  "cultural_influences": "التأثيرات الثقافية إن وجدت",
  "detailed_description": "وصف تفصيلي كامل باللغة العربية"
}

أجب فقط بـ JSON صالح بدون أي نص إضافي."""
                
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
                                        {"type": "text", "text": decor_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/{metadata['format']};base64,{img_data}"
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
                        
                        # Try to parse JSON from the response
                        decor_analysis = {}
                        try:
                            # Extract JSON from potential markdown code blocks
                            json_text = content
                            if "```json" in content:
                                json_text = content.split("```json")[1].split("```")[0].strip()
                            elif "```" in content:
                                json_text = content.split("```")[1].split("```")[0].strip()
                            
                            decor_analysis = json.loads(json_text)
                            metadata["decor_analysis"] = decor_analysis
                            
                            # Use the detailed description as the main content
                            if "detailed_description" in decor_analysis:
                                content = decor_analysis["detailed_description"]
                        except json.JSONDecodeError:
                            logger.warning("Could not parse decor analysis as JSON — using raw text")
                            metadata["decor_analysis_raw"] = content
                        
                        metadata.update({
                            "api_model": "glm-4v-plus",
                            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        })
                        
                        logger.info(f"Decor analysis completed: {len(content)} chars")
                        return ProcessingResult(
                            modality="image",
                            content=content,
                            confidence=0.8,
                            metadata=metadata,
                            source_file=str(path),
                        )
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
        
        # Fallback: placeholder result with extracted colors if available
        logger.info(f"Returning placeholder decor analysis for: {file_path}")
        
        color_info = ""
        if color_palette:
            top_3 = [c["hex"] for c in color_palette[:3]]
            color_info = f" — ألوان مستخلصة: {', '.join(top_3)}"
        
        metadata.update({
            "status": "placeholder",
            "message": "يجب إعداد MAMOUN_VISION_API_KEY لتفعيل تحليل الديكور عبر Vision API",
            "setup_instructions": {
                "env_var": "MAMOUN_VISION_API_KEY",
                "api_model": "glm-4v-plus",
                "analysis_type": "decor_style",
            },
        })
        
        return ProcessingResult(
            modality="image",
            content=f"[تحليل ديكور غير متافر{color_info} — يجب إعداد مفتاح API]",
            confidence=0.0,
            metadata=metadata,
            source_file=str(path),
        )

    def _detect_modality(self, file_path: str) -> str:
        """
        كشف نوع الملف تلقائياً بناءً على الامتداد.
        
        الإرجاع:
            "audio" أو "image" أو "text" أو "unknown"
        """
        ext = Path(file_path).suffix.lower()
        
        if ext in self.SUPPORTED_AUDIO:
            return "audio"
        elif ext in self.SUPPORTED_IMAGE:
            return "image"
        elif ext in {".txt", ".md", ".json", ".csv", ".xml", ".yaml", ".yml"}:
            return "text"
        else:
            return "unknown"

    async def _process_text_file(self, file_path: str) -> ProcessingResult:
        """معالجة ملف نصي عادي."""
        path = Path(file_path)
        
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
        
        file_size = path.stat().st_size
        
        return ProcessingResult(
            modality="text",
            content=content,
            confidence=1.0,
            metadata={
                "format": path.suffix.lower().lstrip("."),
                "size_bytes": file_size,
                "line_count": content.count("\n") + 1,
                "char_count": len(content),
            },
            source_file=str(path),
        )
