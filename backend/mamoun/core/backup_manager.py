"""
BABSHARQII v40.0 — Backup Manager
Programmatic backup management for API integration.
"""

import os
import json
import time
import shutil
import subprocess
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BackupInfo:
    """Information about a backup."""
    name: str = ""
    timestamp: str = ""
    size_bytes: int = 0
    size_human: str = ""
    encrypted: bool = False
    verified: bool = False
    sha256: str = ""
    components: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "encrypted": self.encrypted,
            "verified": self.verified,
            "sha256": self.sha256,
            "components": self.components,
        }


class BackupManager:
    """
    Manages backup operations for BABSHARQII.
    
    Features:
    - Create backups (SQLite, PostgreSQL, Neo4j, ChromaDB)
    - List available backups
    - Restore from backup
    - Verify backup integrity
    - Backup rotation (7 daily, 4 weekly, 3 monthly)
    - S3 upload support
    """
    
    KEEP_DAILY = 7
    KEEP_WEEKLY = 4
    KEEP_MONTHLY = 3
    
    def __init__(self, backend_dir: str = ""):
        if not backend_dir:
            backend_dir = str(Path(__file__).parent.parent.parent)
        self.backend_dir = Path(backend_dir)
        self.data_dir = self.backend_dir / "data"
        self.backup_dir = self.backend_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_backup(
        self,
        include_postgres: bool = True,
        include_neo4j: bool = True,
        include_chromadb: bool = True,
        encrypt: bool = False,
        upload_s3: bool = False,
    ) -> BackupInfo:
        """Create a complete backup of all data."""
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        backup_name = f"mamoun_backup_{timestamp}"
        components = []
        
        # 1. Create compressed archive of data directory
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        if self.data_dir.exists():
            result = subprocess.run(
                ["tar", "-czf", str(archive_path), "-C", str(self.data_dir), "."],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                components.append("data_archive")
        
        # 2. Backup SQLite specifically
        db_path = self.data_dir / "mamoun.db"
        if db_path.exists():
            dest = self.backup_dir / f"mamoun_{timestamp}.db"
            shutil.copy2(db_path, dest)
            components.append("sqlite")
        
        # 3. Backup PostgreSQL if connected
        if include_postgres:
            try:
                pg_host = os.getenv("MAMOUN_POSTGRES_HOST", "")
                pg_pass = os.getenv("MAMOUN_POSTGRES_PASSWORD", "")
                if pg_host and pg_pass:
                    pg_user = os.getenv("MAMOUN_POSTGRES_USER", "mamoun")
                    pg_db = os.getenv("MAMOUN_POSTGRES_DB", "mamoun")
                    pg_port = os.getenv("MAMOUN_POSTGRES_PORT", "5432")
                    
                    pg_dump_path = self.backup_dir / f"postgres_{timestamp}.sql"
                    env = {**os.environ, "PGPASSWORD": pg_pass}
                    result = subprocess.run(
                        ["pg_dump", "-h", pg_host, "-p", pg_port, "-U", pg_user, pg_db],
                        capture_output=True, text=True, timeout=300, env=env
                    )
                    if result.returncode == 0:
                        pg_dump_path.write_text(result.stdout, encoding="utf-8")
                        components.append("postgresql")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # 4. Backup Neo4j if connected
        if include_neo4j:
            try:
                neo4j_uri = os.getenv("MAMOUN_NEO4J_URI", "")
                neo4j_pass = os.getenv("MAMOUN_NEO4J_PASSWORD", "")
                if neo4j_uri and neo4j_pass:
                    neo4j_dump_path = self.backup_dir / f"neo4j_{timestamp}.dump"
                    result = subprocess.run(
                        ["neo4j-admin", "database", "dump", "neo4j",
                         "--to-path", str(self.backup_dir),
                         "--to-file", f"neo4j_{timestamp}.dump"],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        components.append("neo4j")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        
        # 5. Backup configuration files
        for config_file in ["laws.yaml", "settings.yaml"]:
            src = self.backend_dir / config_file
            if src.exists():
                dest = self.backup_dir / f"{config_file.replace('.yaml', '')}_{timestamp}.yaml"
                shutil.copy2(src, dest)
                components.append(config_file.replace('.yaml', ''))
        
        # 6. Calculate SHA-256 checksum
        sha256 = ""
        if archive_path.exists():
            sha256 = self._calculate_sha256(archive_path)
            sha_path = self.backup_dir / f"{backup_name}.sha256"
            sha_path.write_text(f"{sha256}  {backup_name}.tar.gz", encoding="utf-8")
            components.append("sha256")
        
        # 7. Encrypt if requested
        if encrypt and shutil.which("gpg"):
            result = subprocess.run(
                ["gpg", "--symmetric", "--cipher-algo", "AES256", "--batch", "--passphrase", "", str(archive_path)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                archive_path.unlink(missing_ok=True)
                components.append("encrypted")
        
        # 8. S3 upload if requested
        if upload_s3:
            s3_bucket = os.getenv("MAMOUN_BACKUP_S3_BUCKET", "")
            if s3_bucket and shutil.which("aws"):
                upload_file = archive_path
                if not upload_file.exists():
                    gpg_path = self.backup_dir / f"{backup_name}.tar.gz.gpg"
                    if gpg_path.exists():
                        upload_file = gpg_path
                
                if upload_file.exists():
                    result = subprocess.run(
                        ["aws", "s3", "cp", str(upload_file), f"s3://{s3_bucket}/backups/{upload_file.name}"],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        components.append("s3_upload")
        
        # 9. Apply rotation policy
        self._apply_rotation()
        
        # Build result
        size_bytes = 0
        size_human = "0B"
        final_path = self.backup_dir / f"{backup_name}.tar.gz"
        if not final_path.exists():
            final_path = self.backup_dir / f"{backup_name}.tar.gz.gpg"
        
        if final_path.exists():
            size_bytes = final_path.stat().st_size
            size_human = self._human_size(size_bytes)
        
        return BackupInfo(
            name=backup_name,
            timestamp=timestamp,
            size_bytes=size_bytes,
            size_human=size_human,
            encrypted=(backup_name + ".tar.gz.gpg") in [f.name for f in self.backup_dir.iterdir()],
            verified=False,
            sha256=sha256,
            components=components,
        )
    
    async def list_backups(self) -> list[BackupInfo]:
        """List all available backups."""
        backups = []
        
        for f in sorted(self.backup_dir.glob("mamoun_backup_*.tar.gz"), reverse=True):
            info = self._build_backup_info(f)
            backups.append(info)
        
        for f in sorted(self.backup_dir.glob("mamoun_backup_*.tar.gz.gpg"), reverse=True):
            name = f.name.replace(".tar.gz.gpg", "")
            # Skip if already listed (unencrypted version exists)
            if any(b.name == name for b in backups):
                continue
            info = BackupInfo(
                name=name,
                timestamp=self._extract_timestamp(name),
                size_bytes=f.stat().st_size,
                size_human=self._human_size(f.stat().st_size),
                encrypted=True,
                verified=False,
                sha256="",
                components=["encrypted"],
            )
            backups.append(info)
        
        return backups
    
    async def restore_backup(self, backup_name: str, verify_first: bool = True) -> dict:
        """Restore from a specific backup."""
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        gpg_path = self.backup_dir / f"{backup_name}.tar.gz.gpg"
        
        # Decrypt if needed
        if not archive_path.exists() and gpg_path.exists():
            result = subprocess.run(
                ["gpg", "--decrypt", str(gpg_path)],
                capture_output=True, timeout=60,
            )
            if result.returncode == 0:
                archive_path.write_bytes(result.stdout)
            else:
                return {"success": False, "error": "فشل فك التشفير"}
        
        if not archive_path.exists():
            return {"success": False, "error": f"النسخة غير موجودة: {backup_name}"}
        
        # Verify first if requested
        if verify_first:
            verify = await self.verify_backup(backup_name)
            if not verify.get("valid", False):
                return {"success": False, "error": "النسخة تالفة — المجموع الاختباري غير متطابق"}
        
        # Create safety backup of current data
        safety_name = f"pre_restore_{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}"
        safety_path = self.backup_dir / f"{safety_name}.tar.gz"
        if self.data_dir.exists() and any(self.data_dir.iterdir()):
            subprocess.run(
                ["tar", "-czf", str(safety_path), "-C", str(self.data_dir), "."],
                capture_output=True, timeout=300
            )
        
        # Restore
        self.data_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["tar", "-xzf", str(archive_path), "-C", str(self.data_dir)],
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "restored_from": backup_name,
                "safety_backup": safety_name,
                "message": "تمت الاستعادة بنجاح — يرجى إعادة تشغيل النظام",
            }
        else:
            # Try to restore safety backup
            if safety_path.exists():
                subprocess.run(
                    ["tar", "-xzf", str(safety_path), "-C", str(self.data_dir)],
                    capture_output=True, timeout=300
                )
            return {"success": False, "error": f"فشل الاستعادة: {result.stderr[:200]}"}
    
    async def verify_backup(self, backup_name: str) -> dict:
        """Verify a backup's integrity."""
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        sha_path = self.backup_dir / f"{backup_name}.sha256"
        
        if not archive_path.exists():
            return {"valid": False, "error": "النسخة غير موجودة"}
        
        # Check SHA-256
        if sha_path.exists():
            actual_sha = self._calculate_sha256(archive_path)
            expected_content = sha_path.read_text(encoding="utf-8").strip()
            expected_sha = expected_content.split()[0] if expected_content else ""
            
            if actual_sha != expected_sha:
                return {"valid": False, "error": "المجموع الاختباري غير متطابق"}
        else:
            return {"valid": None, "warning": "لا يوجد ملف SHA-256 للتحقق"}
        
        # Test tar integrity
        result = subprocess.run(
            ["tar", "-tzf", str(archive_path)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            return {"valid": False, "error": "الملف المضغوط تالف"}
        
        return {"valid": True, "sha256": self._calculate_sha256(archive_path)}
    
    def _build_backup_info(self, archive_path: Path) -> BackupInfo:
        """Build BackupInfo from a backup file."""
        name = archive_path.stem.replace(".tar", "")
        sha256 = ""
        verified = False
        
        sha_path = self.backup_dir / f"{name}.sha256"
        if sha_path.exists():
            actual_sha = self._calculate_sha256(archive_path)
            expected_content = sha_path.read_text(encoding="utf-8").strip()
            expected_sha = expected_content.split()[0] if expected_content else ""
            if actual_sha == expected_sha:
                sha256 = actual_sha
                verified = True
        
        return BackupInfo(
            name=name,
            timestamp=self._extract_timestamp(name),
            size_bytes=archive_path.stat().st_size,
            size_human=self._human_size(archive_path.stat().st_size),
            encrypted=False,
            verified=verified,
            sha256=sha256[:16] + "..." if sha256 else "",
            components=[],
        )
    
    def _calculate_sha256(self, filepath: Path) -> str:
        """Calculate SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _extract_timestamp(self, name: str) -> str:
        """Extract timestamp from backup name."""
        import re
        m = re.search(r'(\d{8}_\d{6})', name)
        return m.group(1) if m else ""
    
    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def _apply_rotation(self):
        """Apply backup rotation policy: 7 daily, 4 weekly, 3 monthly."""
        backups = sorted(
            self.backup_dir.glob("mamoun_backup_*.tar.gz"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        now = time.time()
        daily_kept = 0
        weekly_kept = 0
        monthly_kept = 0
        
        for f in backups:
            age_days = (now - f.stat().st_mtime) / 86400
            
            if age_days <= 7:
                daily_kept += 1
                if daily_kept > self.KEEP_DAILY:
                    self._remove_backup(f)
            elif age_days <= 30:
                # Keep weekly backups (roughly every 7 days)
                weekly_kept += 1
                if weekly_kept > self.KEEP_WEEKLY:
                    self._remove_backup(f)
            else:
                monthly_kept += 1
                if monthly_kept > self.KEEP_MONTHLY:
                    self._remove_backup(f)
    
    def _remove_backup(self, archive_path: Path):
        """Remove a backup and its associated files."""
        archive_path.unlink(missing_ok=True)
        sha_path = self.backup_dir / f"{archive_path.stem.replace('.tar', '')}.sha256"
        sha_path.unlink(missing_ok=True)


# Singleton
backup_manager = BackupManager()
