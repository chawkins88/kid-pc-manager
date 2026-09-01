"""Control plane data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    ONLINE = "online"
    WARNING = "warning"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class HeartbeatPayload(BaseModel):
    kid_id: str
    hostname: str = ""
    platform: str = ""
    service_running: bool = True
    timestamp: str = ""
    minutes_until_bedtime: int = 0
    is_enforcing: bool = False
    is_past_grace: bool = False
    running_blocked: list[str] = Field(default_factory=list)
    killed_total: int = 0
    uptime_seconds: int = 0


class KidProfile(BaseModel):
    kid_id: str
    display_name: str
    device_ip: str
    agent_port: int = 8443
    api_key: str
    schedule: dict = Field(default_factory=dict)
    blocked_processes: list[str] = Field(default_factory=list)
    enforcement: dict = Field(default_factory=dict)


class KidState(BaseModel):
    profile: KidProfile
    last_heartbeat: datetime | None = None
    last_payload: HeartbeatPayload | None = None
    status: AgentStatus = AgentStatus.UNKNOWN
    missed_heartbeats: int = 0


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Alert(BaseModel):
    kid_id: str
    level: AlertLevel
    message: str
    timestamp: datetime
