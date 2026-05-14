"""
BABSHARQII v25.0 — Neural Mesh Engine
محرك الشبكة العصبية — أوزان فعلية تُعدّل بالخبرة

This is NOT text generation. This is a REAL neural network where:
- Weight matrices are NumPy arrays (float64)
- Learning happens through Hebbian plasticity (Δw = η·x·y)
- Oja's rule prevents unbounded growth (Δw = η·y·(x - y·w))
- STDP handles temporal sequences
- Synaptic consolidation protects well-learned weights
- All weights persist to SQLite

The mesh can:
1. learn_pattern() — present input, get output, update weights
2. recall() — given partial input, complete the pattern (auto-associative)
3. associate() — link two patterns bidirectionally
4. transfer_knowledge() — copy weights to a new domain with consolidation
5. forget() — controlled decay of unused connections
"""

import time
import uuid
import json
import logging
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from enum import Enum

from mamoun.core.unified_db import get_db_connection, UNIFIED_DB_PATH

logger = logging.getLogger("mamoun.neural_mesh")


# ═══════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════

class ActivationFn(str, Enum):
    SIGMOID = "sigmoid"
    RELU = "relu"
    TANH = "tanh"
    LINEAR = "linear"


@dataclass
class NeuralLayer:
    """طبقة عصبية — مصفوفة أوزان فعلية"""
    layer_id: str = ""
    name: str = ""
    input_size: int = 0
    output_size: int = 0
    activation: str = ActivationFn.SIGMOID.value
    learning_rate: float = 0.01
    oja_beta: float = 0.01       # Oja's normalization constant
    consolidation_rate: float = 0.001  # How fast weights consolidate
    weight_matrix: Optional[Any] = None  # numpy array
    bias_vector: Optional[Any] = None     # numpy array
    trace_matrix: Optional[Any] = None    # eligibility traces
    consolidation_matrix: Optional[Any] = None  # consolidation strength
    update_count: int = 0
    last_update: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.layer_id:
            self.layer_id = f"layer_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_update:
            self.last_update = time.time()
        # Initialize weight matrices if sizes are set
        if self.input_size > 0 and self.output_size > 0:
            if self.weight_matrix is None:
                # Xavier initialization
                scale = np.sqrt(2.0 / (self.input_size + self.output_size))
                self.weight_matrix = np.random.randn(self.output_size, self.input_size) * scale
                self.bias_vector = np.zeros(self.output_size)
                self.trace_matrix = np.zeros((self.output_size, self.input_size))
                self.consolidation_matrix = np.ones((self.output_size, self.input_size)) * 0.01

    def activate(self, x: np.ndarray) -> np.ndarray:
        """Forward pass: compute output from input"""
        z = self.weight_matrix @ x + self.bias_vector
        if self.activation == ActivationFn.SIGMOID.value:
            return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        elif self.activation == ActivationFn.RELU.value:
            return np.maximum(0, z)
        elif self.activation == ActivationFn.TANH.value:
            return np.tanh(z)
        else:  # linear
            return z

    def learn_hebbian(self, x: np.ndarray, y: np.ndarray, learning_rate: float = None):
        """
        تعلم هيبي — الأوزان تتعدل فعلياً
        Δw = η · y · (x - β · y · w)  [Oja's rule]
        Consolidation: stronger weights change slower
        """
        eta = learning_rate or self.learning_rate
        # Oja's rule: Δw = η * (y * x^T - β * y^2 * W)
        # This is equivalent to: η * outer(y, x) - η * β * y^2 * W
        delta = eta * (np.outer(y, x) - self.oja_beta * np.outer(y, y) @ self.weight_matrix)
        # Apply consolidation: well-established weights change slower
        # consolidation_matrix ranges from 0.01 (new) to 1.0 (well-consolidated)
        effective_rate = 1.0 / (1.0 + self.consolidation_matrix * 10.0)
        delta *= effective_rate
        # Clip delta to prevent explosion
        delta = np.clip(delta, -0.5, 0.5)
        self.weight_matrix += delta
        # Update bias with simple gradient
        self.bias_vector += eta * y * 0.1
        # Update eligibility traces (for temporal credit)
        self.trace_matrix = 0.9 * self.trace_matrix + np.abs(delta)
        # Update consolidation (weights with high absolute value get consolidated)
        self.consolidation_matrix += self.consolidation_rate * np.abs(self.weight_matrix)
        self.consolidation_matrix = np.clip(self.consolidation_matrix, 0.01, 1.0)
        self.update_count += 1
        self.last_update = time.time()

    def learn_stdp(self, pre_activation: np.ndarray, post_activation: np.ndarray,
                   time_delta: float = 0.01):
        """
        تعلم STDP — التوقيت مهم
        If pre fires before post → LTP (long-term potentiation)
        If post fires before pre → LTD (long-term depression)
        """
        # STDP window function
        # Positive time_delta = pre before post → potentiation
        # Negative time_delta = post before pre → depression
        A_plus = 0.005   # LTP amplitude
        A_minus = 0.004  # LTD amplitude
        tau_plus = 0.02   # LTP time constant
        tau_minus = 0.02  # LTD time constant

        if time_delta >= 0:
            # LTP: pre before post → strengthen
            stdp_weight = A_plus * np.exp(-time_delta / tau_plus)
        else:
            # LTD: post before pre → weaken
            stdp_weight = -A_minus * np.exp(time_delta / tau_minus)

        # Apply STDP to connections where both pre and post are active
        active_pre = pre_activation > 0.5
        active_post = post_activation > 0.5
        mask = np.outer(active_post.astype(float), active_pre.astype(float))
        delta = stdp_weight * mask * self.consolidation_matrix
        self.weight_matrix += delta
        self.trace_matrix = 0.9 * self.trace_matrix + np.abs(delta)
        self.update_count += 1
        self.last_update = time.time()

    def decay_unused(self, decay_rate: float = 0.0001):
        """اضمحال الاتصالات غير المستخدمة"""
        # Weights with low eligibility traces decay slowly
        low_use_mask = self.trace_matrix < 0.001
        self.weight_matrix[low_use_mask] *= (1.0 - decay_rate)
        self.trace_matrix *= 0.95  # Trace decay

    def get_weight_stats(self) -> Dict:
        """إحصائيات الأوزان الفعلية"""
        if self.weight_matrix is None:
            return {}
        return {
            "layer_id": self.layer_id,
            "shape": f"{self.output_size}x{self.input_size}",
            "total_params": self.output_size * self.input_size,
            "mean_weight": float(np.mean(self.weight_matrix)),
            "std_weight": float(np.std(self.weight_matrix)),
            "max_weight": float(np.max(self.weight_matrix)),
            "min_weight": float(np.min(self.weight_matrix)),
            "mean_trace": float(np.mean(self.trace_matrix)),
            "mean_consolidation": float(np.mean(self.consolidation_matrix)),
            "update_count": self.update_count,
            "sparsity": float(np.sum(np.abs(self.weight_matrix) < 0.01) / self.weight_matrix.size),
        }

    def to_storage(self) -> Dict:
        """Serialize for SQLite storage"""
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "input_size": self.input_size,
            "output_size": self.output_size,
            "activation": self.activation,
            "learning_rate": self.learning_rate,
            "oja_beta": self.oja_beta,
            "consolidation_rate": self.consolidation_rate,
            "weight_matrix": self.weight_matrix.tobytes().hex() if self.weight_matrix is not None else "",
            "bias_vector": self.bias_vector.tobytes().hex() if self.bias_vector is not None else "",
            "trace_matrix": self.trace_matrix.tobytes().hex() if self.trace_matrix is not None else "",
            "consolidation_matrix": self.consolidation_matrix.tobytes().hex() if self.consolidation_matrix is not None else "",
            "update_count": self.update_count,
            "last_update": self.last_update,
            "created_at": self.created_at,
        }

    @classmethod
    def from_storage(cls, data: Dict) -> 'NeuralLayer':
        """Deserialize from SQLite storage"""
        layer = cls(
            layer_id=data["layer_id"],
            name=data["name"],
            input_size=data["input_size"],
            output_size=data["output_size"],
            activation=data["activation"],
            learning_rate=data["learning_rate"],
            oja_beta=data["oja_beta"],
            consolidation_rate=data["consolidation_rate"],
            update_count=data["update_count"],
            last_update=data["last_update"],
            created_at=data["created_at"],
        )
        # Restore numpy arrays
        if data.get("weight_matrix"):
            raw = bytes.fromhex(data["weight_matrix"])
            layer.weight_matrix = np.frombuffer(raw, dtype=np.float64).reshape(
                data["output_size"], data["input_size"]).copy()
        if data.get("bias_vector"):
            raw = bytes.fromhex(data["bias_vector"])
            layer.bias_vector = np.frombuffer(raw, dtype=np.float64).copy()
        if data.get("trace_matrix"):
            raw = bytes.fromhex(data["trace_matrix"])
            layer.trace_matrix = np.frombuffer(raw, dtype=np.float64).reshape(
                data["output_size"], data["input_size"]).copy()
        if data.get("consolidation_matrix"):
            raw = bytes.fromhex(data["consolidation_matrix"])
            layer.consolidation_matrix = np.frombuffer(raw, dtype=np.float64).reshape(
                data["output_size"], data["input_size"]).copy()
        return layer


# ═══════════════════════════════════════════════════════════════
# Neural Mesh — Multi-layer neural network with real weights
# ═══════════════════════════════════════════════════════════════

class NeuralMesh:
    """
    الشبكة العصبية الفعلية — أوزان حقيقية تُعدّل بالخبرة

    Usage:
        mesh = NeuralMesh()
        mesh.initialize()

        # Create a layer (e.g., 64 inputs → 32 outputs)
        layer = mesh.create_layer("vision", input_size=64, output_size=32)

        # Learn a pattern
        x = np.random.rand(64)  # input
        y = layer.activate(x)    # forward pass
        target = np.random.rand(32)  # desired output
        layer.learn_hebbian(x, target)  # weights actually change!

        # Auto-associative recall
        partial = x * 0.5  # partial input
        recalled = mesh.recall("vision", partial)  # pattern completion

        # Transfer knowledge to another domain
        mesh.transfer_knowledge("vision", "audio", freeze_ratio=0.7)
    """

    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else UNIFIED_DB_PATH
        self._layers: Dict[str, NeuralLayer] = {}
        self._associations: Dict[str, Dict] = {}  # bidirectional pattern links
        self._pattern_cache: Dict[str, np.ndarray] = {}  # recent patterns
        self._llm = None
        self._initialized = False

    def set_llm_client(self, llm_client):
        self._llm = llm_client

    def initialize(self) -> bool:
        try:
            self._ensure_schema()
            self._load_from_db()
            self._initialized = True
            logger.info("NeuralMesh initialized — %d layers", len(self._layers))
            return True
        except Exception as e:
            logger.error("NeuralMesh init failed: %s", e)
            return False

    def _ensure_schema(self):
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nm_layers (
                    layer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    input_size INTEGER NOT NULL,
                    output_size INTEGER NOT NULL,
                    activation TEXT DEFAULT 'sigmoid',
                    learning_rate REAL DEFAULT 0.01,
                    oja_beta REAL DEFAULT 0.01,
                    consolidation_rate REAL DEFAULT 0.001,
                    weight_matrix TEXT DEFAULT '',
                    bias_vector TEXT DEFAULT '',
                    trace_matrix TEXT DEFAULT '',
                    consolidation_matrix TEXT DEFAULT '',
                    update_count INTEGER DEFAULT 0,
                    last_update REAL DEFAULT 0,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nm_associations (
                    assoc_id TEXT PRIMARY KEY,
                    source_layer TEXT NOT NULL,
                    target_layer TEXT NOT NULL,
                    forward_weights TEXT DEFAULT '',
                    backward_weights TEXT DEFAULT '',
                    strength REAL DEFAULT 0.5,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nm_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    layer_id TEXT NOT NULL,
                    label TEXT DEFAULT '',
                    vector TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_seen REAL DEFAULT 0,
                    created_at REAL DEFAULT 0
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_from_db(self):
        conn = get_db_connection(self.db_path)
        try:
            for row in conn.execute("SELECT * FROM nm_layers"):
                data = {
                    "layer_id": row[0], "name": row[1], "input_size": row[2],
                    "output_size": row[3], "activation": row[4], "learning_rate": row[5],
                    "oja_beta": row[6], "consolidation_rate": row[7],
                    "weight_matrix": row[8], "bias_vector": row[9],
                    "trace_matrix": row[10], "consolidation_matrix": row[11],
                    "update_count": row[12], "last_update": row[13], "created_at": row[14],
                }
                layer = NeuralLayer.from_storage(data)
                self._layers[layer.layer_id] = layer
        finally:
            conn.close()

    def _persist_layer(self, layer: NeuralLayer):
        conn = get_db_connection(self.db_path)
        try:
            data = layer.to_storage()
            conn.execute("""
                INSERT OR REPLACE INTO nm_layers
                (layer_id, name, input_size, output_size, activation, learning_rate,
                 oja_beta, consolidation_rate, weight_matrix, bias_vector,
                 trace_matrix, consolidation_matrix, update_count, last_update, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, tuple(data.values()))
            conn.commit()
        finally:
            conn.close()

    # ═══════════════════════════════════════════════════════════
    # Core API
    # ═══════════════════════════════════════════════════════════

    def create_layer(self, name: str, input_size: int = 64, output_size: int = 32,
                     activation: str = "sigmoid", learning_rate: float = 0.01) -> NeuralLayer:
        """إنشاء طبقة عصبية جديدة بأوزان حقيقية"""
        # Check if layer with same name exists
        for layer in self._layers.values():
            if layer.name == name:
                return layer

        layer = NeuralLayer(
            name=name, input_size=input_size, output_size=output_size,
            activation=activation, learning_rate=learning_rate,
        )
        self._layers[layer.layer_id] = layer
        self._persist_layer(layer)
        logger.info("Created neural layer '%s': %d→%d", name, input_size, output_size)
        return layer

    def learn_pattern(self, layer_name: str, input_pattern: np.ndarray,
                      target_output: np.ndarray = None,
                      learning_rate: float = None) -> Dict[str, Any]:
        """
        تعلم نمط — الأوزان تتعدل فعلياً

        If target_output is provided: supervised Hebbian learning
        If not: unsupervised Hebbian (self-organizing)
        """
        layer = self._find_layer_by_name(layer_name)
        if not layer:
            return {"error": f"Layer '{layer_name}' not found"}

        # Ensure input dimensions match
        if len(input_pattern) != layer.input_size:
            return {"error": f"Input size mismatch: expected {layer.input_size}, got {len(input_pattern)}"}

        x = np.array(input_pattern, dtype=np.float64)

        # Forward pass
        y = layer.activate(x)

        if target_output is not None:
            # Supervised: learn toward target
            target = np.array(target_output, dtype=np.float64)
            if len(target) != layer.output_size:
                return {"error": f"Output size mismatch: expected {layer.output_size}, got {len(target)}"}
            layer.learn_hebbian(x, target, learning_rate)
        else:
            # Unsupervised: self-organizing (Oja's rule)
            layer.learn_hebbian(x, y, learning_rate)

        # Store pattern in cache
        self._pattern_cache[f"{layer_name}:{hash(x.tobytes())}"] = x

        self._persist_layer(layer)

        return {
            "layer": layer_name,
            "input_norm": float(np.linalg.norm(x)),
            "output_norm": float(np.linalg.norm(y)),
            "weight_change": float(np.mean(np.abs(layer.trace_matrix))),
            "update_count": layer.update_count,
        }

    def recall(self, layer_name: str, partial_input: np.ndarray,
               iterations: int = 5) -> Dict[str, Any]:
        """
        استرجاع ذاتي — إكمال النمط من مدخل جزئي
        Auto-associative recall: pattern completion
        """
        layer = self._find_layer_by_name(layer_name)
        if not layer:
            return {"error": f"Layer '{layer_name}' not found"}

        x = np.array(partial_input, dtype=np.float64)

        # Forward pass
        y = layer.activate(x)

        # Iterative refinement: feed output back as input (if square matrix)
        refined = y
        for _ in range(iterations):
            if layer.input_size == layer.output_size:
                refined = layer.activate(refined)
            else:
                break

        return {
            "layer": layer_name,
            "output": refined.tolist(),
            "output_norm": float(np.linalg.norm(refined)),
            "max_activation": float(np.max(refined)),
            "active_units": int(np.sum(refined > 0.5)),
        }

    def associate(self, source_layer: str, target_layer: str,
                  source_input: np.ndarray, target_input: np.ndarray,
                  strength: float = 0.5) -> Dict[str, Any]:
        """
        ربط نمطين عبر طبقتين — ارتباط ثنائي الاتجاه
        Bidirectional association between patterns in different layers
        """
        src = self._find_layer_by_name(source_layer)
        tgt = self._find_layer_by_name(target_layer)
        if not src or not tgt:
            return {"error": "Layer not found"}

        # Compute activations
        src_out = src.activate(np.array(source_input, dtype=np.float64))
        tgt_out = tgt.activate(np.array(target_input, dtype=np.float64))

        # Store association weights
        assoc_id = f"assoc_{uuid.uuid4().hex[:8]}"
        forward_w = np.outer(tgt_out, src_out) * strength
        backward_w = np.outer(src_out, tgt_out) * strength

        self._associations[assoc_id] = {
            "source_layer": source_layer,
            "target_layer": target_layer,
            "forward_weights": forward_w,
            "backward_weights": backward_w,
            "strength": strength,
        }

        # Persist association
        conn = get_db_connection(self.db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO nm_associations
                (assoc_id, source_layer, target_layer, forward_weights, backward_weights, strength, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (assoc_id, source_layer, target_layer,
                  forward_w.tobytes().hex(), backward_w.tobytes().hex(),
                  strength, time.time()))
            conn.commit()
        finally:
            conn.close()

        return {
            "association_id": assoc_id,
            "source_layer": source_layer,
            "target_layer": target_layer,
            "strength": strength,
        }

    def cross_activate(self, source_layer: str, target_layer: str,
                       source_input: np.ndarray) -> Dict[str, Any]:
        """
        تنشيط متقاطع — تنشيط طبقة هدف عبر ارتباط من طبقة مصدر
        """
        src = self._find_layer_by_name(source_layer)
        tgt = self._find_layer_by_name(target_layer)
        if not src or not tgt:
            return {"error": "Layer not found"}

        src_out = src.activate(np.array(source_input, dtype=np.float64))

        # Find association
        cross_input = None
        for assoc in self._associations.values():
            if assoc["source_layer"] == source_layer and assoc["target_layer"] == target_layer:
                # Use forward weights to map source→target
                fw = assoc["forward_weights"]
                if fw.shape[1] == len(src_out):
                    cross_signal = fw @ src_out
                    cross_input = cross_signal[:tgt.input_size] if len(cross_signal) >= tgt.input_size else None
                    break
            elif assoc["target_layer"] == source_layer and assoc["source_layer"] == target_layer:
                # Use backward weights (reverse direction)
                bw = assoc["backward_weights"]
                if bw.shape[1] == len(src_out):
                    cross_signal = bw @ src_out
                    cross_input = cross_signal[:tgt.input_size] if len(cross_signal) >= tgt.input_size else None
                    break

        if cross_input is None:
            return {"error": "No association found between layers"}

        # Normalize cross input to target layer's input size
        if len(cross_input) > tgt.input_size:
            cross_input = cross_input[:tgt.input_size]
        elif len(cross_input) < tgt.input_size:
            padded = np.zeros(tgt.input_size)
            padded[:len(cross_input)] = cross_input
            cross_input = padded

        tgt_out = tgt.activate(cross_input)

        return {
            "source_activation": src_out.tolist(),
            "cross_input": cross_input.tolist(),
            "target_activation": tgt_out.tolist(),
        }

    def transfer_knowledge(self, source_layer: str, target_layer: str,
                           freeze_ratio: float = 0.7) -> Dict[str, Any]:
        """
        نقل المعرفة — نسخ أوزان من طبقة لأخرى مع تجميد جزئي
        Transfer learning: copy weights, freeze important ones
        """
        src = self._find_layer_by_name(source_layer)
        tgt = self._find_layer_by_name(target_layer)
        if not src or not tgt:
            return {"error": "Layer not found"}
        if src.input_size != tgt.input_size or src.output_size != tgt.output_size:
            return {"error": "Layer dimensions must match for transfer"}

        # Copy weights from source to target
        tgt.weight_matrix = src.weight_matrix.copy()
        tgt.bias_vector = src.bias_vector.copy()

        # Freeze the top freeze_ratio of weights (by consolidation strength)
        flat_consolidation = src.consolidation_matrix.flatten()
        threshold = np.percentile(flat_consolidation, freeze_ratio * 100)
        freeze_mask = src.consolidation_matrix >= threshold

        # Frozen weights get high consolidation (hard to change)
        tgt.consolidation_matrix = np.where(
            freeze_mask,
            1.0,  # frozen
            src.consolidation_matrix.copy() * 0.1  # plastic
        )
        # Reset traces for transferred weights
        tgt.trace_matrix = np.where(freeze_mask, 0.0, src.trace_matrix.copy())
        tgt.update_count = 0

        self._persist_layer(tgt)

        frozen_count = int(np.sum(freeze_mask))
        total = freeze_mask.size
        return {
            "source": source_layer,
            "target": target_layer,
            "frozen_weights": frozen_count,
            "plastic_weights": total - frozen_count,
            "freeze_ratio": freeze_ratio,
            "weight_mean": float(np.mean(tgt.weight_matrix)),
            "weight_std": float(np.std(tgt.weight_matrix)),
        }

    def decay_all(self, decay_rate: float = 0.0001):
        """اضمحال جميع الطبقات غير المستخدمة"""
        for layer in self._layers.values():
            layer.decay_unused(decay_rate)
            self._persist_layer(layer)

    def get_layer(self, layer_name: str) -> Optional[Dict]:
        layer = self._find_layer_by_name(layer_name)
        if not layer:
            return None
        stats = layer.get_weight_stats()
        # Include actual weight matrix sample
        if layer.weight_matrix is not None:
            stats["weight_sample"] = layer.weight_matrix[0, :5].tolist()  # First row, first 5
            stats["weight_matrix_shape"] = list(layer.weight_matrix.shape)
        return stats

    def get_stats(self) -> Dict:
        total_params = sum(
            l.input_size * l.output_size for l in self._layers.values()
            if l.weight_matrix is not None
        )
        return {
            "layers": len(self._layers),
            "associations": len(self._associations),
            "total_parameters": total_params,
            "layer_details": {l.name: l.get_weight_stats() for l in self._layers.values()},
        }

    def _find_layer_by_name(self, name: str) -> Optional[NeuralLayer]:
        for layer in self._layers.values():
            if layer.name == name:
                return layer
        return None

    def save_pattern(self, layer_name: str, label: str, vector: np.ndarray):
        """حفظ نمط في قاعدة البيانات"""
        layer = self._find_layer_by_name(layer_name)
        if not layer:
            return
        conn = get_db_connection(self.db_path)
        try:
            # Check if pattern exists
            existing = conn.execute(
                "SELECT pattern_id, frequency FROM nm_patterns WHERE layer_id=? AND label=?",
                (layer.layer_id, label)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE nm_patterns SET frequency=?, last_seen=? WHERE pattern_id=?",
                    (existing[1] + 1, time.time(), existing[0])
                )
            else:
                conn.execute("""
                    INSERT INTO nm_patterns (pattern_id, layer_id, label, vector, frequency, last_seen, created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (f"pat_{uuid.uuid4().hex[:8]}", layer.layer_id, label,
                      vector.tobytes().hex(), 1, time.time(), time.time()))
            conn.commit()
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

neural_mesh = NeuralMesh()
