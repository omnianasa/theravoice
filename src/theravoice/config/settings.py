"""Central configuration loader for TheraVoice.

Configuration is primarily driven by YAML files under `config/`, selected via
the `THERAVOICE_ENV` environment variable (development | testing | production).
Sensitive values (API keys, AWS credentials) can be overridden via environment
variables so that no secrets need to live in YAML or source control.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# Repo root: src/theravoice/config/settings.py -> src/theravoice -> src -> <root>
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _PACKAGE_ROOT.parent
_CONFIG_DIR_CANDIDATES = [
    _REPO_ROOT / "config",
    Path.cwd() / "config",
]


def _find_config_dir() -> Path:
    for candidate in _CONFIG_DIR_CANDIDATES:
        if candidate.is_dir():
            return candidate
    # Fall back to repo-relative path even if it doesn't exist yet.
    return _CONFIG_DIR_CANDIDATES[0]


class DatabaseSettings(BaseModel):
    url: str = "sqlite:///./data/processed/theravoice_dev.db"
    echo: bool = False


class SecuritySettings(BaseModel):
    require_api_key: bool = False
    api_key: str = ""


class PrivacySettings(BaseModel):
    store_raw_audio: bool = False
    require_audio_consent: bool = True
    require_data_storage_consent: bool = True
    data_retention_days: int = 30
    redact_transcripts: bool = True


class BaselineSettings(BaseModel):
    minimum_observations: int = 5
    rolling_window_size: int = 20
    z_score_threshold: float = 2.0
    update_enabled: bool = True


class DetectionSettings(BaseModel):
    warning_z: float = 1.5
    significant_z: float = 2.0


class HesitationSettings(BaseModel):
    english: list[str] = Field(default_factory=lambda: ["um", "uh", "er", "hmm"])
    arabic: list[str] = Field(default_factory=lambda: ["امم", "اه", "يعني", "مم"])


class TherapySettings(BaseModel):
    require_clinician_approval: bool = True


class LLMSettings(BaseModel):
    provider: str = "none"
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = Field(default=15.0, gt=0)


class AWSSettings(BaseModel):
    enabled: bool = False
    region: str = "us-east-1"
    s3_bucket: str = ""
    dynamodb_table: str = ""


class BeeSettings(BaseModel):
    # "mock"  -> blank in-memory MockBeeAdapter (tests / no Bee account at all)
    # "sync"  -> reads a local `bee sync` markdown export from disk (real,
    #            historical data; no live connection, no token in this app)
    # "proxy" -> calls the local HTTP API started by `bee proxy` (real,
    #            near-live data; localhost only, authenticated by the
    #            user's own `bee login` session -- no token in this app)
    mode: str = "mock"
    sync_dir: str = "bee-sync"
    proxy_base_url: str = "http://127.0.0.1:8787"
    proxy_timeout_seconds: float = 10.0
    # How many recent conversations to pull per poll from either backend.
    max_conversations_per_poll: int = 50


class LoggingSettings(BaseModel):
    level: str = "INFO"


class Settings(BaseModel):
    """Fully resolved TheraVoice configuration."""

    environment: str = "development"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    baseline: BaselineSettings = Field(default_factory=BaselineSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    hesitation: HesitationSettings = Field(default_factory=HesitationSettings)
    therapy: TherapySettings = Field(default_factory=TherapySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    aws: AWSSettings = Field(default_factory=AWSSettings)
    bee: BeeSettings = Field(default_factory=BeeSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} must contain a mapping at the top level.")
    return data


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """Apply a small, explicit set of environment variable overrides.

    Only sensitive / deployment-specific values are override-able this way,
    to avoid surprising, hard-to-trace configuration drift.
    """
    raw.setdefault("database", {})
    raw.setdefault("security", {})
    raw.setdefault("llm", {})
    raw.setdefault("aws", {})

    if db_url := os.environ.get("THERAVOICE_DATABASE_URL"):
        raw["database"]["url"] = db_url

    if api_key := os.environ.get("THERAVOICE_API_KEY"):
        raw["security"]["api_key"] = api_key
        raw["security"]["require_api_key"] = True

    for env_name, setting_name in (
        ("THERAVOICE_LLM_PROVIDER", "provider"),
        ("THERAVOICE_LLM_MODEL", "model"),
        ("THERAVOICE_LLM_API_KEY", "api_key"),
        ("THERAVOICE_LLM_TIMEOUT_SECONDS", "timeout_seconds"),
    ):
        if value := os.environ.get(env_name):
            raw["llm"][setting_name] = value

    if (aws_enabled := os.environ.get("THERAVOICE_AWS_ENABLED")) is not None:
        raw["aws"]["enabled"] = aws_enabled.strip().lower() in {"1", "true", "yes", "on"}

    if aws_region := os.environ.get("AWS_REGION"):
        raw["aws"]["region"] = aws_region

    return raw


@lru_cache(maxsize=None)
def get_settings(env: str | None = None) -> Settings:
    """Load and cache Settings for the given environment.

    Args:
        env: Explicit environment name. Falls back to THERAVOICE_ENV, then
            "development".
    """
    resolved_env = env or os.environ.get("THERAVOICE_ENV", "development")
    config_dir = _find_config_dir()
    config_path = config_dir / f"{resolved_env}.yaml"

    raw = _load_yaml(config_path)
    raw.setdefault("environment", resolved_env)
    raw = _apply_env_overrides(raw)

    return Settings.model_validate(raw)


def reload_settings(env: str | None = None) -> Settings:
    """Bypass the cache and reload settings from disk (useful in tests)."""
    get_settings.cache_clear()
    return get_settings(env)
