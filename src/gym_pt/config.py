from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# gym/src/gym_pt/config.py → project root is parents[2] (gym/)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = _PROJECT_ROOT
_ENV_PATH = _PROJECT_ROOT / ".env"


def setup_logging(
    name: str = "gym_pt",
    level: int | str | None = None,
) -> logging.Logger:
    """Configure a single shared logger for CLI and agents."""
    resolved = level or os.getenv("LOG_LEVEL", "INFO")
    if isinstance(resolved, str):
        resolved = getattr(logging, resolved.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(resolved)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(name)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
    return logger


class AppSettings(BaseSettings):
    """Environment-backed settings for Railengine and app-wide defaults."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    engine_pat: str | None = Field(default=None, validation_alias="ENGINE_PAT")
    engine_id: str | None = Field(default=None, validation_alias="ENGINE_ID")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )


@lru_cache
def get_settings() -> AppSettings:
    """Load `gym/.env` once (project root, not cwd) and return cached settings."""
    load_dotenv(_ENV_PATH)
    return AppSettings()
