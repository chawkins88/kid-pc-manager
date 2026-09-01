"""Device Policy Agent — entry point."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from agent.core.api_server import AgentApiServer
from agent.core.config import AgentConfig, default_config_path, load_config, save_config
from agent.core.enforcer import ProcessEnforcer
from agent.core.heartbeat import HeartbeatClient
from agent.core.scheduler import BedtimeScheduler
from agent.ui.warnings import (
    format_bedtime_enforcement,
    format_bedtime_warning,
    format_grace_ended,
    get_platform_adapter,
)

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        self.enforcer = ProcessEnforcer(self.config)
        self.scheduler = BedtimeScheduler(self.config)
        self.platform = get_platform_adapter()
        self.started_at = datetime.now(timezone.utc)
        self._running = True

        self.api = AgentApiServer(
            self.config,
            on_config_update=self._on_config_update,
            get_status=self.get_status,
        )
        self.heartbeat = HeartbeatClient(
            self.config,
            get_status=self.get_status,
        )

    def _on_config_update(self, config: AgentConfig) -> None:
        self.config = config
        self.enforcer.update_config(config)
        self.scheduler.update_config(config)
        self.api.update_config(config)
        self.heartbeat.update_config(config)
        save_config(self.config_path, config)

    def get_status(self) -> dict:
        return {
            "platform": self.platform.platform_name(),
            "minutes_until_bedtime": self.scheduler.minutes_until_bedtime(),
            "is_enforcing": self.scheduler.is_enforcing(),
            "is_past_grace": self.scheduler.is_past_grace(),
            "running_blocked": self.enforcer.running_blocked(),
            "killed_total": self.enforcer.killed_total,
            "uptime_seconds": int((datetime.now(timezone.utc) - self.started_at).total_seconds()),
        }

    def start(self) -> None:
        self.api.start()
        self.heartbeat.start()
        logger.info(
            "Agent started for %s (%s) on %s",
            self.config.display_name,
            self.config.kid_id,
            self.platform.platform_name(),
        )

    def stop(self) -> None:
        self._running = False
        self.heartbeat.stop()
        self.api.stop()

    def run_loop(self, tick_seconds: int = 30) -> None:
        while self._running:
            self._tick()
            time.sleep(tick_seconds)

    def _tick(self) -> None:
        actions = self.scheduler.tick()
        kid = self.config.display_name

        for minutes in actions["warnings"]:
            title, message = format_bedtime_warning(minutes, kid)
            self.platform.show_warning(title, message)

        if actions["start_enforcement"]:
            msg = format_bedtime_enforcement(kid, self.config.enforcement.grace_minutes)
            self.platform.show_bedtime_notice(msg)

        if actions["end_grace"]:
            self.platform.show_bedtime_notice(format_grace_ended(kid))

        if self.scheduler.is_enforcing():
            killed = self.enforcer.enforce_once()
            if killed:
                logger.info("Enforcement tick killed: %s", killed)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Device Policy Agent")
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=default_config_path(),
        help="Path to agent config YAML",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--tick-seconds", type=int, default=30)
    args = parser.parse_args()
    setup_logging(args.verbose)

    runtime = AgentRuntime(args.config)

    def shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down (signal %s)", signum)
        runtime.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    runtime.start()
    try:
        runtime.run_loop(tick_seconds=args.tick_seconds)
    finally:
        runtime.stop()


if __name__ == "__main__":
    main()
