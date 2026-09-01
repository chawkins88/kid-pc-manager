"""Process enforcement — terminate blocked applications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import psutil

from agent.core.config import AgentConfig

logger = logging.getLogger(__name__)


class ProcessEnforcer:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._blocked = {name.lower() for name in config.blocked_processes}
        self.last_kill_at: datetime | None = None
        self.killed_total = 0

    def update_config(self, config: AgentConfig) -> None:
        self._config = config
        self._blocked = {name.lower() for name in config.blocked_processes}

    def enforce_once(self) -> list[str]:
        """Kill all running blocked processes. Returns names of killed processes."""
        killed: list[str] = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if not name:
                    continue
                if not self._matches_blocked(name):
                    continue
                proc.kill()
                killed.append(name)
                self.killed_total += 1
                self.last_kill_at = datetime.now(timezone.utc)
                logger.info("Terminated blocked process: %s (pid %s)", name, proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return killed

    def _matches_blocked(self, process_name: str) -> bool:
        for blocked in self._blocked:
            if process_name == blocked:
                return True
            # Allow matching without .exe suffix on Windows
            if process_name.removesuffix(".exe") == blocked.removesuffix(".exe"):
                return True
        return False

    def running_blocked(self) -> list[str]:
        """Return names of blocked processes currently running."""
        found: list[str] = []
        for proc in psutil.process_iter(["name"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if name and self._matches_blocked(name):
                    found.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return found
