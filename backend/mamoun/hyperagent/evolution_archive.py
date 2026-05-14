"""
Evolution Archive — Genetic Memory with Cross-Domain Transfer
v16.0

Based on: Hyperagents finding that "skills and improvement capabilities
transfer across domains and accumulate across consecutive cycles."

The Evolution Archive stores:
1. Every genome/variant ever tested (success or failure)
2. Performance scores per domain
3. Cross-domain transferability scores
4. Lineage relationships (parent → child mutations)

This enables:
- Reusing successful patterns from one domain in another
- Avoiding repeated failed experiments
- "Breeding" successful variants together
- Tracking the family tree of improvements
"""

import json
import hashlib
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.hyperagent.evolution_archive")


class ArchiveEntryStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    SUPERSEDED = "superseded"  # Replaced by a better variant


class ArchiveEntry:
    """A single entry in the evolution archive."""
    
    def __init__(
        self,
        variant_id: str,
        parent_id: Optional[str],
        genome_snapshot: dict,
        mutation_description: str,
        domain: str,
        mutation_type: str,
    ):
        self.variant_id = variant_id
        self.parent_id = parent_id
        self.genome_snapshot = genome_snapshot
        self.mutation_description = mutation_description
        self.domain = domain
        self.mutation_type = mutation_type
        self.status = ArchiveEntryStatus.PROPOSED
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.tested_at: Optional[str] = None
        self.accepted_at: Optional[str] = None
        
        # Performance scores
        self.fitness_score: float = 0.0
        self.improvement_pct: float = 0.0
        self.forgetting_pct: float = 0.0
        self.risk_level: str = "low"
        
        # Cross-domain transfer
        self.transfer_scores: dict[str, float] = {}  # {domain: performance}
        self.transferable_patterns: list[str] = []  # Extracted reusable patterns
    
    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "parent_id": self.parent_id,
            "genome_snapshot": self.genome_snapshot,
            "mutation_description": self.mutation_description,
            "domain": self.domain,
            "mutation_type": self.mutation_type,
            "status": self.status.value if isinstance(self.status, ArchiveEntryStatus) else self.status,
            "created_at": self.created_at,
            "tested_at": self.tested_at,
            "accepted_at": self.accepted_at,
            "fitness_score": self.fitness_score,
            "improvement_pct": self.improvement_pct,
            "forgetting_pct": self.forgetting_pct,
            "risk_level": self.risk_level,
            "transfer_scores": self.transfer_scores,
            "transferable_patterns": self.transferable_patterns,
        }


class EvolutionArchive:
    """
    Stores and manages the complete evolutionary history.
    Enables cross-domain transfer and lineage tracking.
    """
    
    def __init__(self, data_dir: str = "backend/data/hyperagent/archive"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.entries_path = self.data_dir / "archive_entries.jsonl"
        self.index_path = self.data_dir / "archive_index.json"
        
        self.entries: list[ArchiveEntry] = self._load_entries()
        self.index: dict = self._load_index()
    
    def _load_entries(self) -> list:
        entries = []
        if self.entries_path.exists():
            with open(self.entries_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            entry = ArchiveEntry(
                                variant_id=data["variant_id"],
                                parent_id=data.get("parent_id"),
                                genome_snapshot=data.get("genome_snapshot", {}),
                                mutation_description=data.get("mutation_description", ""),
                                domain=data.get("domain", "general"),
                                mutation_type=data.get("mutation_type", "unknown"),
                            )
                            entry.status = ArchiveEntryStatus(data.get("status", "proposed"))
                            entry.created_at = data.get("created_at", "")
                            entry.tested_at = data.get("tested_at")
                            entry.accepted_at = data.get("accepted_at")
                            entry.fitness_score = data.get("fitness_score", 0.0)
                            entry.improvement_pct = data.get("improvement_pct", 0.0)
                            entry.forgetting_pct = data.get("forgetting_pct", 0.0)
                            entry.risk_level = data.get("risk_level", "low")
                            entry.transfer_scores = data.get("transfer_scores", {})
                            entry.transferable_patterns = data.get("transferable_patterns", [])
                            entries.append(entry)
                        except Exception:
                            continue
        return entries
    
    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"total_entries": 0, "domains": {}, "lineage_depth": 0}
    
    def _save_entry(self, entry: ArchiveEntry):
        with open(self.entries_path, "a") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
    
    def _save_index(self):
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def add_entry(self, entry: ArchiveEntry) -> str:
        """Add a new entry to the archive."""
        self.entries.append(entry)
        self._save_entry(entry)
        
        # Update index
        self.index["total_entries"] = len(self.entries)
        if entry.domain not in self.index["domains"]:
            self.index["domains"][entry.domain] = 0
        self.index["domains"][entry.domain] += 1
        
        # Track lineage depth
        if entry.parent_id:
            depth = self._get_lineage_depth(entry.variant_id)
            self.index["lineage_depth"] = max(self.index.get("lineage_depth", 0), depth)
        
        self._save_index()
        logger.info("Archive entry added: %s (%s)", entry.variant_id, entry.domain)
        return entry.variant_id
    
    def update_entry(self, variant_id: str, updates: dict):
        """Update an existing entry with test results."""
        for entry in self.entries:
            if entry.variant_id == variant_id:
                for key, value in updates.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                break
        # Note: In production, we'd rewrite the file. For now, append update marker.
        with open(self.entries_path, "a") as f:
            f.write(json.dumps({"_update": variant_id, **updates}, ensure_ascii=False) + "\n")
    
    def get_entry(self, variant_id: str) -> Optional[ArchiveEntry]:
        for entry in self.entries:
            if entry.variant_id == variant_id:
                return entry
        return None
    
    def get_lineage(self, variant_id: str) -> list[ArchiveEntry]:
        """Get the full lineage (ancestor chain) for a variant."""
        lineage = []
        current = self.get_entry(variant_id)
        while current:
            lineage.append(current)
            if current.parent_id:
                current = self.get_entry(current.parent_id)
            else:
                break
        return lineage
    
    def _get_lineage_depth(self, variant_id: str) -> int:
        return len(self.get_lineage(variant_id))
    
    def find_transferable_patterns(self, source_domain: str, target_domain: str, limit: int = 5) -> list[dict]:
        """
        Find patterns from source_domain that might work in target_domain.
        This is the cross-domain transfer mechanism.
        """
        candidates = []
        
        for entry in self.entries:
            if entry.domain == source_domain and entry.status == ArchiveEntryStatus.ACCEPTED:
                # Check if this entry has been tested in the target domain
                target_score = entry.transfer_scores.get(target_domain)
                if target_score and target_score > 0.5:
                    candidates.append({
                        "variant_id": entry.variant_id,
                        "source_domain": source_domain,
                        "target_score": target_score,
                        "patterns": entry.transferable_patterns,
                        "fitness": entry.fitness_score,
                        "improvement": entry.improvement_pct,
                    })
                elif not target_score:
                    # Untested — use similarity heuristic
                    # Higher fitness in source = more likely to transfer
                    candidates.append({
                        "variant_id": entry.variant_id,
                        "source_domain": source_domain,
                        "target_score": None,  # Unknown
                        "patterns": entry.transferable_patterns,
                        "fitness": entry.fitness_score,
                        "improvement": entry.improvement_pct,
                    })
        
        # Sort by fitness and improvement
        candidates.sort(key=lambda c: (c.get("target_score") or 0, c["fitness"], c["improvement"]), reverse=True)
        return candidates[:limit]
    
    def get_successful_variants(self, domain: str = None, limit: int = 20) -> list[ArchiveEntry]:
        """Get the most successful variants, optionally filtered by domain."""
        accepted = [e for e in self.entries if e.status == ArchiveEntryStatus.ACCEPTED]
        if domain:
            accepted = [e for e in accepted if e.domain == domain]
        accepted.sort(key=lambda e: (e.fitness_score, e.improvement_pct), reverse=True)
        return accepted[:limit]
    
    def get_failed_variants(self, domain: str = None, limit: int = 20) -> list[ArchiveEntry]:
        """Get failed variants to avoid repeating mistakes."""
        failed = [e for e in self.entries if e.status == ArchiveEntryStatus.REJECTED]
        if domain:
            failed = [e for e in failed if e.domain == domain]
        failed.sort(key=lambda e: e.forgetting_pct, reverse=True)
        return failed[:limit]
    
    def get_statistics(self) -> dict:
        accepted = sum(1 for e in self.entries if e.status == ArchiveEntryStatus.ACCEPTED)
        rejected = sum(1 for e in self.entries if e.status == ArchiveEntryStatus.REJECTED)
        
        domain_stats = {}
        for entry in self.entries:
            if entry.domain not in domain_stats:
                domain_stats[entry.domain] = {"total": 0, "accepted": 0, "rejected": 0}
            domain_stats[entry.domain]["total"] += 1
            if entry.status == ArchiveEntryStatus.ACCEPTED:
                domain_stats[entry.domain]["accepted"] += 1
            elif entry.status == ArchiveEntryStatus.REJECTEDED:
                domain_stats[entry.domain]["rejected"] += 1
        
        return {
            "total_entries": len(self.entries),
            "accepted": accepted,
            "rejected": rejected,
            "acceptance_rate": accepted / len(self.entries) if self.entries else 0,
            "domains": domain_stats,
            "lineage_depth": self.index.get("lineage_depth", 0),
            "transferable_patterns_count": sum(
                len(e.transferable_patterns) for e in self.entries if e.transferable_patterns
            ),
        }
