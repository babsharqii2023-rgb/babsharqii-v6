"""
Outcome Recorder v59 — Decorator/context manager for automatic outcome recording.

CRITICAL ADDITION from v59:
- Provides a reusable decorator and async context manager for recording outcomes
- Every component can use this to automatically track performance in MetaCognition
- Eliminates code duplication and ensures consistent measurement

v59 — Super Mind العقل الخارق مامون
"""

import time
import functools
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OutcomeRecorder:
    """
    Async context manager that automatically records outcomes in MetaCognition.

    Usage:
        async with OutcomeRecorder(meta, "brain_router", "route_query") as rec:
            result = await do_something()
            rec.quality_score = result.confidence
            rec.success = True
        # Outcome is automatically recorded on exit

    If an exception occurs, success=False is recorded automatically.
    """

    def __init__(self, meta_cognition=None, component: str = "", operation: str = "",
                 predicted_quality: float = 0.5):
        self._meta = meta_cognition
        self._component = component
        self._operation = operation
        self._predicted_quality = predicted_quality

        self.success = True
        self.quality_score = 0.5
        self.error: Optional[str] = None
        self.metadata: dict = {}
        self._start_time = 0.0

    async def __aenter__(self):
        self._start_time = time.time()
        # Predict quality before operation
        if self._meta:
            try:
                self._predicted_quality = self._meta.predict_quality(self._component)
            except Exception:
                self._predicted_quality = 0.5
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.time() - self._start_time) * 1000

        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)[:200]
            self.quality_score = 0.0

        if self._meta:
            try:
                from .meta_cognition_engine import OutcomeRecord
                self._meta.record_outcome(OutcomeRecord(
                    component=self._component,
                    operation=self._operation,
                    success=self.success,
                    quality_score=self.quality_score,
                    predicted_quality=self._predicted_quality,
                    latency_ms=latency_ms,
                    error=self.error,
                    metadata=self.metadata,
                ))
            except ImportError:
                logger.warning("Could not import OutcomeRecord — outcome not tracked")
            except Exception as e:
                logger.warning(f"Failed to record outcome: {e}")


def record_outcome(component: str, operation: str):
    """
    Decorator for async methods that automatically records outcomes.

    Usage:
        @record_outcome("brain_router", "route_query")
        async def route_query(self, query, ...):
            ...

    The decorated method must return an object with a `confidence` attribute
    or a dict with a 'confidence' key for quality_score extraction.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Try to get meta_cognition from self
            meta = getattr(self, '_meta_cognition', None)
            if meta is None:
                meta = getattr(self, '_meta', None)

            start = time.time()
            predicted = 0.5
            if meta:
                try:
                    predicted = meta.predict_quality(component)
                except Exception:
                    predicted = 0.5

            try:
                result = await func(self, *args, **kwargs)

                # Extract quality score from result
                quality = 0.5
                if hasattr(result, 'confidence'):
                    quality = result.confidence
                elif hasattr(result, 'final_confidence'):
                    quality = result.final_confidence
                elif isinstance(result, dict):
                    quality = result.get('confidence', result.get('quality_score', 0.5))

                latency = (time.time() - start) * 1000

                if meta:
                    try:
                        from .meta_cognition_engine import OutcomeRecord
                        meta.record_outcome(OutcomeRecord(
                            component=component,
                            operation=operation,
                            success=True,
                            quality_score=quality,
                            predicted_quality=predicted,
                            latency_ms=latency,
                            metadata=getattr(result, 'metadata', {}) if hasattr(result, 'metadata') else {},
                        ))
                    except ImportError:
                        pass
                    except Exception as e:
                        logger.warning(f"Failed to record outcome: {e}")

                return result

            except Exception as e:
                latency = (time.time() - start) * 1000

                if meta:
                    try:
                        from .meta_cognition_engine import OutcomeRecord
                        meta.record_outcome(OutcomeRecord(
                            component=component,
                            operation=operation,
                            success=False,
                            quality_score=0.0,
                            predicted_quality=predicted,
                            latency_ms=latency,
                            error=str(e)[:200],
                        ))
                    except ImportError:
                        pass
                    except Exception as record_err:
                        logger.warning(f"Failed to record outcome: {record_err}")

                raise

        return wrapper
    return decorator
