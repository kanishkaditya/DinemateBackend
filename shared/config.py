"""
Shared Configuration

Configuration settings that are used by both API and LLM service.
"""

import os
from typing import Optional


class LLMConfig:
    """Configuration for LLM service."""
    
    # Worker settings
    WORKER_ENABLED: bool = os.getenv("LLM_WORKER_ENABLED", "true").lower() == "true"
    WORKER_INTERVAL: int = int(os.getenv("LLM_WORKER_INTERVAL", "5"))  # seconds
    WORKER_BATCH_SIZE: int = int(os.getenv("LLM_WORKER_BATCH_SIZE", "10"))
    
    # Analysis settings
    MIN_CONFIDENCE_THRESHOLD: float = float(os.getenv("LLM_MIN_CONFIDENCE", "0.3"))
    HIGH_CONFIDENCE_THRESHOLD: float = float(os.getenv("LLM_HIGH_CONFIDENCE", "0.8"))
    
    # Message processing
    MESSAGE_ANALYSIS_ENABLED: bool = os.getenv("MESSAGE_ANALYSIS_ENABLED", "true").lower() == "true"
    REAL_TIME_PROCESSING: bool = os.getenv("REAL_TIME_PROCESSING", "false").lower() == "true"
    
    # Future: External LLM API settings (OpenAI, etc.)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY","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")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")
    USE_EXTERNAL_LLM: bool = os.getenv("USE_EXTERNAL_LLM", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LLM_LOG_LEVEL", "INFO")
    LOG_ANALYSIS_RESULTS: bool = os.getenv("LOG_ANALYSIS_RESULTS", "true").lower() == "true"


class SharedConfig:
    """Configuration shared between all services."""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb+srv://kanishk:gamora12@cluster0.gmynbk3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "dinemate_db")
    
    # Redis (for future use with Celery)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# Instances
llm_config = LLMConfig()
shared_config = SharedConfig()