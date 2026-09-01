"""Control plane — parent dashboard and agent coordinator."""

from __future__ import annotations

import argparse
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import httpx
import uvicorn
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from control_plane.alerts import AlertManager
from control_plane.models import AgentStatus, HeartbeatPayload, KidProfile, KidState

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
STATIC_DIR = Path(__file__).resolve().parent / "static"


class ControlPlaneSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    parent_pin_hash: str = ""
    heartbeat_check_interval: int = 30


class BonusTimeRequest(BaseModel):
    minutes: int
    pin: str


class ConfigPushRequest(BaseModel):
    pin: str
    schedule: dict | None = None
    blocked_processes: list[str] | None = None


def load_profiles(profiles_dir: Path) -> dict[str, KidState]:
    states: dict[str, KidState] = {}
    if not profiles_dir.exists():
        return states
    for path in profiles_dir.glob("*.yaml"):
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        profile = KidProfile.model_validate(data)
        states[profile.kid_id] = KidState(profile=profile)
    return states


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(pin: str, pin_hash: str) -> bool:
    if not pin_hash:
        # Dev mode: no PIN configured
        return True
    return bcrypt.checkpw(pin.encode(), pin_hash.encode())


def create_app(settings: ControlPlaneSettings) -> FastAPI:
    app = FastAPI(title="Device Policy Control Plane", docs_url="/docs")
    states = load_profiles(PROFILES_DIR)
    alerts = AlertManager()
    app.state.settings = settings
    app.state.states = states
    app.state.alerts = alerts

    def verify_agent_key(kid_id: str, authorization: str | None) -> KidState:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing API key")
        token = authorization.removeprefix("Bearer ").strip()
        state = states.get(kid_id)
        if not state or token != state.profile.api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")
        return state

    def verify_parent_pin(pin: str) -> None:
        if not verify_pin(pin, settings.parent_pin_hash):
            raise HTTPException(status_code=403, detail="Invalid parent PIN")

    @app.post("/api/v1/heartbeat")
    def heartbeat(
        payload: HeartbeatPayload,
        authorization: str | None = Header(default=None),
    ) -> dict:
        state = verify_agent_key(payload.kid_id, authorization)
        state.last_heartbeat = datetime.now(timezone.utc)
        state.last_payload = payload
        alerts.on_heartbeat(payload.kid_id, state)
        return {"status": "ok"}

    @app.get("/api/v1/kids")
    def list_kids() -> list[dict]:
        result = []
        for kid_id, state in states.items():
            alerts.evaluate(kid_id, state)
            result.append({
                "kid_id": kid_id,
                "display_name": state.profile.display_name,
                "device_ip": state.profile.device_ip,
                "status": state.status.value,
                "missed_heartbeats": state.missed_heartbeats,
                "last_heartbeat": state.last_heartbeat.isoformat() if state.last_heartbeat else None,
                "last_payload": state.last_payload.model_dump() if state.last_payload else None,
            })
        return result

    @app.get("/api/v1/alerts")
    def list_alerts() -> list[dict]:
        return [a.model_dump(mode="json") for a in alerts.recent_alerts()]

    @app.post("/api/v1/kids/{kid_id}/bonus")
    def grant_bonus(kid_id: str, body: BonusTimeRequest) -> dict:
        verify_parent_pin(body.pin)
        state = states.get(kid_id)
        if not state:
            raise HTTPException(status_code=404, detail="Kid not found")
        bonus_until = datetime.now(timezone.utc) + timedelta(minutes=body.minutes)
        return push_to_agent(state, {"bonus_until": bonus_until.isoformat()})

    @app.post("/api/v1/kids/{kid_id}/config")
    def push_config(kid_id: str, body: ConfigPushRequest) -> dict:
        verify_parent_pin(body.pin)
        state = states.get(kid_id)
        if not state:
            raise HTTPException(status_code=404, detail="Kid not found")
        update: dict = {}
        if body.schedule is not None:
            update["schedule"] = body.schedule
        if body.blocked_processes is not None:
            update["blocked_processes"] = body.blocked_processes
        return push_to_agent(state, update)

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


def push_to_agent(state: KidState, update: dict) -> dict:
    profile = state.profile
    url = f"http://{profile.device_ip}:{profile.agent_port}/api/v1/config"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                url,
                json=update,
                headers={"Authorization": f"Bearer {profile.api_key}"},
            )
            response.raise_for_status()
        return {"status": "ok", "kid_id": profile.kid_id}
    except Exception as exc:
        logger.error("Failed to push config to %s: %s", profile.kid_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def run_heartbeat_monitor(app: FastAPI, interval: int) -> None:
    def loop() -> None:
        while True:
            for kid_id, state in app.state.states.items():
                app.state.alerts.evaluate(kid_id, state)
            time.sleep(interval)

    thread = threading.Thread(target=loop, name="heartbeat-monitor", daemon=True)
    thread.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Device Policy Control Plane")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--set-pin",
        help="Generate a bcrypt hash for PARENT_PIN_HASH and exit",
    )
    args = parser.parse_args()

    if args.set_pin:
        print(hash_pin(args.set_pin))
        return

    pin_hash = os.environ.get("PARENT_PIN_HASH", "")
    settings = ControlPlaneSettings(host=args.host, port=args.port, parent_pin_hash=pin_hash)
    app = create_app(settings)
    run_heartbeat_monitor(app, settings.heartbeat_check_interval)

    logging.basicConfig(level=logging.INFO)
    logger.info("Control plane starting on %s:%s", settings.host, settings.port)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
