"""
BABSHARQII v40.0 — Upload API
واجهة رفع الملفات متعددة الوسائط.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from typing import Optional
import shutil
import os
import uuid
import logging
from pathlib import Path

from mamoun.core.multimodal_processor import MultimodalProcessor
from mamoun.api.deps import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Initialize processor
processor = MultimodalProcessor()


@router.post("/", dependencies=[Depends(require_auth)])
async def upload_file(
    file: UploadFile = File(...),
    modality: Optional[str] = Form(""),
    analyze: bool = Form(True),
):
    """
    رفع ملف وتحليله.
    
    المعاملات:
        file: الملف المرفوع
        modality: تلميح عن نوع الوسائط (اختياري: "audio", "image", "text")
        analyze: هل يتم تحليل الملف بعد الرفع
    
    الإرجاع:
        نتيجة المعالجة إذا analyze=True، أو معلومات الملف المحفوظ فقط
    """
    # Validate file was provided
    if not file.filename:
        raise HTTPException(status_code=400, detail="اسم الملف مفقود")
    
    # Validate file size
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    # Create unique filename to avoid conflicts
    file_ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    save_path = processor.upload_dir / unique_name
    
    # Save file and measure size
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > processor.MAX_FILE_SIZE:
                    # Clean up partial file
                    save_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"حجم الملف يتجاوز الحد الأقصى ({processor.MAX_FILE_SIZE / (1024*1024):.0f}MB)",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        save_path.unlink(missing_ok=True)
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"فشل في حفظ الملف: {str(e)}")
    
    logger.info(f"File uploaded: {file.filename} -> {save_path} ({file_size} bytes)")
    
    # If no analysis requested, just return file info
    if not analyze:
        return {
            "success": True,
            "filename": file.filename,
            "saved_as": unique_name,
            "file_path": str(save_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "content_type": file.content_type,
            "analyzed": False,
        }
    
    # Process the file with MultimodalProcessor
    try:
        result = await processor.process_file(str(save_path), modality_hint=modality)
        return {
            "success": True,
            "filename": file.filename,
            "saved_as": unique_name,
            "file_path": str(save_path),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "content_type": file.content_type,
            "analyzed": True,
            "result": result.to_dict(),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"فشل في تحليل الملف: {str(e)}")


@router.post("/analyze", dependencies=[Depends(require_auth)])
async def analyze_existing_file(
    file_path: str = Form(...),
    modality: str = Form(""),
):
    """
    تحليل ملف موجود مسبقاً.
    
    المعاملات:
        file_path: مسار الملف المراد تحليله
        modality: تلميح عن نوع الوسائط (اختياري)
    
    الإرجاع:
        نتيجة المعالجة
    """
    # Validate file path exists
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"الملف غير موجود: {file_path}")
    
    # Security: ensure file is within allowed directories
    resolved = path.resolve()
    allowed_dirs = [
        processor.upload_dir.resolve(),
        Path("/tmp").resolve(),
    ]
    
    # Check if file is in allowed directory (prevent path traversal)
    is_allowed = any(
        str(resolved).startswith(str(allowed_dir))
        for allowed_dir in allowed_dirs
    )
    if not is_allowed:
        raise HTTPException(
            status_code=403,
            detail="الملف خارج المسارات المسموح بها",
        )
    
    try:
        result = await processor.process_file(file_path, modality_hint=modality)
        return {
            "success": True,
            "file_path": file_path,
            "analyzed": True,
            "result": result.to_dict(),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=f"فشل في تحليل الملف: {str(e)}")


@router.post("/decor", dependencies=[Depends(require_auth)])
async def analyze_decor(
    file: UploadFile = File(...),
):
    """
    تحليل أسلوب الديكور في صورة.
    
    المعاملات:
        file: ملف الصورة المرفوع
    
    الإرجاع:
        تحليل الديكور مع الألوان والأنماط والعناصر
    """
    # Validate file was provided
    if not file.filename:
        raise HTTPException(status_code=400, detail="اسم الملف مفقود")
    
    file_ext = Path(file.filename).suffix.lower()
    
    # Validate image format
    if file_ext not in processor.SUPPORTED_IMAGE:
        raise HTTPException(
            status_code=400,
            detail=f"صيغة ملف غير مدعومة للتحليل. الصيغ المدعومة: {processor.SUPPORTED_IMAGE}",
        )
    
    # Save the file
    unique_name = f"{uuid.uuid4().hex}{file_ext}"
    save_path = processor.upload_dir / unique_name
    
    file_size = 0
    try:
        with open(save_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > processor.MAX_FILE_SIZE:
                    save_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"حجم الملف يتجاوز الحد الأقصى ({processor.MAX_FILE_SIZE / (1024*1024):.0f}MB)",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        save_path.unlink(missing_ok=True)
        logger.error(f"Error saving decor image: {e}")
        raise HTTPException(status_code=500, detail=f"فشل في حفظ الملف: {str(e)}")
    
    # Perform decor analysis
    try:
        result = await processor.analyze_decor_style(str(save_path))
        return {
            "success": True,
            "filename": file.filename,
            "saved_as": unique_name,
            "file_path": str(save_path),
            "size_bytes": file_size,
            "analyzed": True,
            "analysis_type": "decor_style",
            "result": result.to_dict(),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing decor: {e}")
        raise HTTPException(status_code=500, detail=f"فشل في تحليل الديكور: {str(e)}")
