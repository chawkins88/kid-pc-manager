"""Local HTTPS API for receiving config from the control plane."""

from __future__ import annotations

import logging
import threading
from typing import Callable

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from agent.core.config import AgentConfig

logger = logging.getLogger(__name__)


class ConfigUpdate(BaseModel):
    schedule: dict | None = None
    blocked_processes: list[str] | None = None
    bonus_until: str | None = None
    enforcement: dict | None = None


class AgentApiServer:
    def __init__(
        self,
        config: AgentConfig,
        *,
        on_config_update: Callable[[AgentConfig], None],
        get_status: Callable[[], dict],
    ) -> None:
        self._config = config
        self._on_config_update = on_config_update
        self._get_status = get_status
        self._app = self._build_app()
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    def update_config(self, config: AgentConfig) -> None:
        self._config = config

    def _verify_api_key(self, authorization: str | None = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing API key")
        token = authorization.removeprefix("Bearer ").strip()
        if token != self._config.api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="Device Policy Agent", docs_url=None, redoc_url=None)

        @app.get("/api/v1/status")
        def status(_: None = Depends(self._verify_api_key)) -> dict:
            return {
                "kid_id": self._config.kid_id,
                "display_name": self._config.display_name,
                **self._get_status(),
            }

        @app.post("/api/v1/config")
        def update_config(
            body: ConfigUpdate,
            _: None = Depends(self._verify_api_key),
        ) -> dict:
            updated = self._config.model_copy(deep=True)
            if body.schedule is not None:
                updated.schedule = updated.schedule.model_copy(update=body.schedule)
            if body.blocked_processes is not None:
                updated.blocked_processes = body.blocked_processes
            if body.bonus_until is not None:
                updated.bonus_until = body.bonus_until or None
            if body.enforcement is not None:
                updated.enforcement = updated.enforcement.model_copy(update=body.enforcement)

            self._config = updated
            self._on_config_update(updated)
            logger.info("Config updated via API for kid %s", updated.kid_id)
            return {"status": "ok", "kid_id": updated.kid_id}

        @app.get("/health")
        def health() -> dict:
            return {"status": "ok"}

        return app

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        config = uvicorn.Config(
            self._app,
            host=self._config.api.host,
            port=self._config.api.port,
            log_level="warning",
            ssl_certfile=self._config.api.tls_cert,
            ssl_keyfile=self._config.api.tls_key,
        )
        self._server = uvicorn.Server(config)

        def run() -> None:
            self._server.run()

        self._thread = threading.Thread(target=run, name="agent-api", daemon=True)
        self._thread.start()
        logger.info("Agent API listening on %s:%s", self._config.api.host, self._config.api.port)

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)
