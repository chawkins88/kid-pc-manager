"""Push heartbeats to the control plane."""

from __future__ import annotations

import logging
import platform
import socket
import threading
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from agent.core.config import AgentConfig

logger = logging.getLogger(__name__)


class HeartbeatClient:
    def __init__(
        self,
        config: AgentConfig,
        *,
        get_status: Callable[[], dict],
        interval_seconds: int = 60,
    ) -> None:
        self._config = config
        self._get_status = get_status
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_success: datetime | None = None
        self.last_error: str | None = None

    def update_config(self, config: AgentConfig) -> None:
        self._config = config

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.send_once()
            self._stop.wait(self._interval)

    def send_once(self) -> bool:
        status = self._get_status()
        payload = {
            "kid_id": self._config.kid_id,
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "service_running": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **status,
        }
        url = f"{self._config.control_plane_url.rstrip('/')}/api/v1/heartbeat"
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._config.api_key}"},
                )
                response.raise_for_status()
            self.last_success = datetime.now(timezone.utc)
            self.last_error = None
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning("Heartbeat failed: %s", exc)
            return False
