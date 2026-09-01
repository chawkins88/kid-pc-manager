"""Agent configuration models and loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    bedtime: str = "21:00"
    timezone: str = "America/New_York"
    warnings_minutes: list[int] = Field(default_factory=lambda: [15, 5, 1])


class EnforcementConfig(BaseModel):
    grace_minutes: int = 5
    check_interval_seconds: int = 10


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8443
    tls_cert: Optional[str] = None
    tls_key: Optional[str] = None


class AgentConfig(BaseModel):
    kid_id: str
    display_name: str
    api_key: str
    control_plane_url: str = "http://127.0.0.1:8080"
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    blocked_processes: list[str] = Field(default_factory=list)
    enforcement: EnforcementConfig = Field(default_factory=EnforcementConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    bonus_until: Optional[str] = None  # ISO datetime override from parent


def load_config(path: str | Path) -> AgentConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return AgentConfig.model_validate(data)


def save_config(path: str | Path, config: AgentConfig) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.model_dump(mode="json")
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def default_config_path() -> Path:
    env_path = os.environ.get("DEVICE_POLICY_CONFIG")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "config" / "agent.yaml"
