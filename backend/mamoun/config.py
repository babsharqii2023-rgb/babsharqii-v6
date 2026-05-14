"""
BABSHARQII v40.0 — Configuration Manager
Loads and validates settings from YAML and environment variables.
7 AGI Pathways: Episodic Memory, Deep Emotion, Physical/IoT, One-Shot Learning, Constraint Planning, Original Creativity, Human Collaboration
"""

import os
import yaml
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

# v36 FIX: Load .env BEFORE any os.environ access
# Without this, API keys are unavailable outside main.py
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


# Paths
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
LAWS_PATH = BACKEND_DIR / "laws.yaml"
DATA_DIR = BACKEND_DIR / "data"
LOGS_DIR = BACKEND_DIR / "logs"
SANDBOX_DIR = BACKEND_DIR / "sandbox"
DB_PATH = DATA_DIR / "mamoun.db"
GENOME_ARCHIVE_DIR = DATA_DIR / "genome_archive"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # LLM — GLM-5.1 is the PRIMARY brain
    llm_api_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    llm_model: str = "glm-5.1"
    llm_timeout: int = 60
    llm_fallback_models: list = Field(
        default=["glm-5.1", "deepseek-chat", "glm-4-plus", "glm-4"]
    )
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # GitHub Self-Update Token
    github_token: str = ""
    github_repo: str = "babsharqii2023-rgb/babsharqii-v5"
    github_branch: str = "main"
    auto_update_interval: int = 60  # seconds between auto-update checks
    
    # Evolution
    auto_evolve: bool = True
    require_approval: bool = True
    mutation_rate: float = 0.3
    fitness_threshold: float = 0.02
    max_archive_size: int = 50
    benchmark_size: int = 150
    stagnation_threshold: int = 3
    
    # Sandbox
    sandbox_enabled: bool = True
    sandbox_docker_image: str = "mamoun-sandbox:latest"
    sandbox_timeout: int = 120
    
    # Safety
    max_patch_attempts: int = 3
    max_concurrent_mutations: int = 1
    shutdown_timeout_ms: int = 1000
    
    # PostgreSQL (Episodic Memory)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "mamoun"
    postgres_user: str = "mamoun"
    postgres_password: str = "changeme"
    
    # Neo4j (Semantic Memory)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"
    
    # ChromaDB (Procedural Memory)
    chroma_host: str = "localhost"
    chroma_port: int = 8100  # v18.1 Fix: changed from 8000 to avoid conflict with FastAPI
    
    # Monitoring
    health_check_interval: int = 15
    anomaly_check_interval: int = 10
    journal_max_entries: int = 500
    
    # v36 FIX: Replaced deprecated class Config with model_config = ConfigDict(...)
    # The old `class Config` style is deprecated in Pydantic v2+
    model_config = {
        "env_prefix": "MAMOUN_",
        "env_file": ".env",
        "extra": "ignore",
    }


def load_laws() -> dict:
    """Load and validate the immutable laws from laws.yaml."""
    if not LAWS_PATH.exists():
        raise FileNotFoundError(f"Laws file not found: {LAWS_PATH}")
    
    with open(LAWS_PATH, 'r', encoding='utf-8') as f:
        laws = yaml.safe_load(f)
    
    if not laws or 'laws' not in laws:
        raise ValueError("Invalid laws.yaml: missing 'laws' key")
    
    return laws


def ensure_directories():
    """Create required directories if they don't exist."""
    for d in [DATA_DIR, LOGS_DIR, SANDBOX_DIR, GENOME_ARCHIVE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# Singleton
settings = Settings()
laws = load_laws()
ensure_directories()
