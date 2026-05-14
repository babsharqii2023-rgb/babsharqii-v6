"""
BABSHARQII v25.0 — Domain Adapter
مُكيّف النطاقات — نقل المعرفة بين نطاقات مختلفة

Transfers learned neural patterns from one domain to another:
1. Weight transfer: Copy relevant weights, freeze important ones
2. Feature alignment: Align representations between domains
3. Progressive fine-tuning: Gradually adapt to new domain
4. Domain bridging: Map concepts across domains

This uses ACTUAL weight matrices, not text rules.
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.domain_adapter")


@dataclass
class DomainProfile:
    """ملف نطاق — خصائص النطاق المعرفي"""
    domain_id: str = ""
    name: str = ""
    description: str = ""
    layer_name: str = ""          # associated neural layer
    weight_mean: float = 0.0
    weight_std: float = 0.0
    weight_sparsity: float = 0.0
    activation_mean: float = 0.0
    sample_count: int = 0
    created_at: float = 0.0
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TransferResult:
    """نتيجة نقل التعلم"""
    transfer_id: str = ""
    source_domain: str = ""
    target_domain: str = ""
    weights_transferred: int = 0
    weights_frozen: int = 0
    weights_plastic: int = 0
    alignment_score: float = 0.0
    estimated_benefit: float = 0.0


class DomainAdapter:
    """
    مُكيّف النطاقات — ينقل المعرفة الفعلية بين نطاقات مختلفة

    Usage:
        adapter = DomainAdapter()
        adapter.initialize()

        # Register domains
        adapter.register_domain("vision", layer_name="vision_layer", weight_matrix=W)
        adapter.register_domain("audio", layer_name="audio_layer", weight_matrix=W2)

        # Transfer knowledge from vision to audio
        result = adapter.transfer("vision", "audio", weight_matrix_target,
                                  freeze_ratio=0.6)

        # Align representations
        alignment = adapter.align_domains("vision", "audio", samples_v, samples_a)
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._domains: Dict[str, DomainProfile] = {}
        self._transfer_history: List[Dict] = []
        self._alignment_matrices: Dict[str, np.ndarray] = {}  # "src→tgt" → alignment matrix
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("DomainAdapter initialized — %d domains", len(self._domains))
            return True
        except Exception as e:
            logger.error("DomainAdapter init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS da_domains (
                    domain_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    layer_name TEXT DEFAULT '',
                    weight_mean REAL DEFAULT 0,
                    weight_std REAL DEFAULT 0,
                    weight_sparsity REAL DEFAULT 0,
                    activation_mean REAL DEFAULT 0,
                    sample_count INTEGER DEFAULT 0,
                    created_at REAL DEFAULT 0,
                    last_updated REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS da_transfers (
                    transfer_id TEXT PRIMARY KEY,
                    source_domain TEXT NOT NULL,
                    target_domain TEXT NOT NULL,
                    weights_transferred INTEGER DEFAULT 0,
                    weights_frozen INTEGER DEFAULT 0,
                    weights_plastic INTEGER DEFAULT 0,
                    alignment_score REAL DEFAULT 0,
                    estimated_benefit REAL DEFAULT 0,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM da_domains"):
                domain = DomainProfile(
                    domain_id=row[0], name=row[1], description=row[2],
                    layer_name=row[3], weight_mean=row[4], weight_std=row[5],
                    weight_sparsity=row[6], activation_mean=row[7],
                    sample_count=row[8], created_at=row[9], last_updated=row[10],
                )
                self._domains[domain.name] = domain
        finally:
            conn.close()

    def _persist_domain(self, domain: DomainProfile):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO da_domains
                (domain_id, name, description, layer_name, weight_mean, weight_std,
                 weight_sparsity, activation_mean, sample_count, created_at, last_updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (domain.domain_id, domain.name, domain.description, domain.layer_name,
                  domain.weight_mean, domain.weight_std, domain.weight_sparsity,
                  domain.activation_mean, domain.sample_count, domain.created_at,
                  domain.last_updated))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API
    # ═══════════════════════════════════════════════════════════

    def register_domain(self, name: str, layer_name: str = "",
                        weight_matrix: np.ndarray = None,
                        description: str = "") -> DomainProfile:
        """تسجيل نطاق جديد"""
        if name in self._domains:
            # Update existing
            domain = self._domains[name]
            if weight_matrix is not None:
                domain.weight_mean = float(np.mean(weight_matrix))
                domain.weight_std = float(np.std(weight_matrix))
                domain.weight_sparsity = float(
                    np.sum(np.abs(weight_matrix) < 0.01) / weight_matrix.size
                )
            domain.last_updated = time.time()
            self._persist_domain(domain)
            return domain

        domain = DomainProfile(
            domain_id=f"domain_{uuid.uuid4().hex[:8]}",
            name=name, description=description, layer_name=layer_name,
            created_at=time.time(), last_updated=time.time(),
        )
        if weight_matrix is not None:
            domain.weight_mean = float(np.mean(weight_matrix))
            domain.weight_std = float(np.std(weight_matrix))
            domain.weight_sparsity = float(
                np.sum(np.abs(weight_matrix) < 0.01) / weight_matrix.size
            )
        self._domains[name] = domain
        self._persist_domain(domain)
        return domain

    def transfer(self, source_domain: str, target_domain: str,
                 target_weight_matrix: np.ndarray,
                 source_weight_matrix: np.ndarray = None,
                 consolidation_matrix: np.ndarray = None,
                 freeze_ratio: float = 0.6) -> TransferResult:
        """
        نقل المعرفة من نطاق مصدر إلى نطاق هدف

        1. نسخ الأوزان من المصدر
        2. تجميد الأوزان المهمة (بناءً على consolidation)
        3. ترك الأوزان غير المهمة قابلة للتعديل

        الهدف: تعلم أسرع في النطاق الجديد مع حماية المعرفة السابقة
        """
        src = self._domains.get(source_domain)
        if not src:
            return TransferResult(source_domain=source_domain, target_domain=target_domain)

        # Get source weights
        if source_weight_matrix is None:
            return TransferResult(source_domain=source_domain, target_domain=target_domain)

        # Check dimensions match
        if source_weight_matrix.shape != target_weight_matrix.shape:
            return TransferResult(source_domain=source_domain, target_domain=target_domain)

        # Copy weights from source to target
        target_weight_matrix[:] = source_weight_matrix.copy()

        # Determine which weights to freeze
        if consolidation_matrix is not None:
            flat = consolidation_matrix.flatten()
            threshold = np.percentile(flat, freeze_ratio * 100)
            freeze_mask = consolidation_matrix >= threshold
        else:
            # Freeze weights with highest absolute value
            flat = np.abs(source_weight_matrix).flatten()
            threshold = np.percentile(flat, freeze_ratio * 100)
            freeze_mask = np.abs(source_weight_matrix) >= threshold

        frozen_count = int(np.sum(freeze_mask))
        plastic_count = target_weight_matrix.size - frozen_count

        # Modify consolidation: frozen weights get high consolidation
        if consolidation_matrix is not None:
            consolidation_matrix[freeze_mask] = 1.0
            consolidation_matrix[~freeze_mask] = 0.01

        # Compute alignment score (cosine similarity of weight distributions)
        src_flat = source_weight_matrix.flatten()
        tgt_flat = target_weight_matrix.flatten()
        alignment = float(np.dot(src_flat, tgt_flat) /
                         (np.linalg.norm(src_flat) * np.linalg.norm(tgt_flat) + 1e-10))

        # Estimate benefit
        benefit = float(freeze_ratio * (1.0 - src.weight_sparsity))

        result = TransferResult(
            transfer_id=f"xfer_{uuid.uuid4().hex[:8]}",
            source_domain=source_domain,
            target_domain=target_domain,
            weights_transferred=target_weight_matrix.size,
            weights_frozen=frozen_count,
            weights_plastic=plastic_count,
            alignment_score=round(alignment, 4),
            estimated_benefit=round(benefit, 4),
        )

        # Persist transfer
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT INTO da_transfers
                (transfer_id, source_domain, target_domain, weights_transferred,
                 weights_frozen, weights_plastic, alignment_score, estimated_benefit, created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (result.transfer_id, result.source_domain, result.target_domain,
                  result.weights_transferred, result.weights_frozen, result.weights_plastic,
                  result.alignment_score, result.estimated_benefit, time.time()))
            conn.commit()
        finally:
            conn.close()

        self._transfer_history.append({
            "from": source_domain, "to": target_domain,
            "frozen": frozen_count, "benefit": benefit,
        })

        return result

    def align_domains(self, source_domain: str, target_domain: str,
                      source_samples: np.ndarray,
                      target_samples: np.ndarray) -> Dict[str, Any]:
        """
        محاذاة النطاقات — إيجاد تحويل خطي بين تمثيلات النطاقين

        Uses least squares to find W such that:
        W @ source_samples ≈ target_samples

        This allows cross-domain activation mapping.
        """
        # Solve: W @ S = T  →  W = T @ S^+  (pseudoinverse)
        S = source_samples.T if source_samples.ndim == 2 else source_samples.reshape(-1, 1).T
        T = target_samples.T if target_samples.ndim == 2 else target_samples.reshape(-1, 1).T

        try:
            W = T @ np.linalg.pinv(S)
        except np.linalg.LinAlgError:
            W = np.eye(T.shape[0], S.shape[0])

        key = f"{source_domain}→{target_domain}"
        self._alignment_matrices[key] = W

        # Compute alignment quality
        reconstructed = W @ S
        error = float(np.mean((reconstructed - T) ** 2))

        return {
            "source": source_domain,
            "target": target_domain,
            "alignment_matrix_shape": list(W.shape),
            "reconstruction_error": round(error, 6),
            "alignment_quality": round(1.0 / (1.0 + error), 4),
        }

    def cross_domain_activate(self, source_domain: str, target_domain: str,
                              source_activation: np.ndarray) -> np.ndarray:
        """تنشيط عبر النطاقات باستخدام مصفوفة المحاذاة"""
        key = f"{source_domain}→{target_domain}"
        W = self._alignment_matrices.get(key)
        if W is None:
            return source_activation  # No alignment, return as-is
        return W @ source_activation

    def get_stats(self) -> Dict:
        return {
            "domains": len(self._domains),
            "transfers": len(self._transfer_history),
            "alignment_matrices": len(self._alignment_matrices),
            "domain_details": {name: d.to_dict() for name, d in self._domains.items()},
        }


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

domain_adapter = DomainAdapter()
