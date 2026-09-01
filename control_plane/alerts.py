"""Missed-heartbeat detection and alert management."""

from __future__ import annotations

from datetime import datetime, timezone

from control_plane.models import AgentStatus, Alert, AlertLevel, KidState


WARNING_THRESHOLD = 2   # missed heartbeats (~2 min at 60s interval)
CRITICAL_THRESHOLD = 5  # missed heartbeats (~5 min)


class AlertManager:
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def evaluate(self, kid_id: str, state: KidState, now: datetime | None = None) -> AgentStatus:
        now = now or datetime.now(timezone.utc)
        if state.last_heartbeat is None:
            state.status = AgentStatus.UNKNOWN
            return state.status

        elapsed = (now - state.last_heartbeat).total_seconds()
        # Expected interval is 60s; allow 90s grace before counting as missed
        expected_missed = max(0, int(elapsed // 60) - 1)
        state.missed_heartbeats = expected_missed

        if expected_missed >= CRITICAL_THRESHOLD:
            state.status = AgentStatus.OFFLINE
            self._add_alert(
                kid_id,
                AlertLevel.CRITICAL,
                f"Agent offline — no heartbeat for ~{int(elapsed)}s. Service may be disabled.",
            )
        elif expected_missed >= WARNING_THRESHOLD:
            state.status = AgentStatus.WARNING
            self._add_alert(
                kid_id,
                AlertLevel.WARNING,
                f"Agent heartbeat delayed (~{int(elapsed)}s since last seen).",
            )
        else:
            state.status = AgentStatus.ONLINE

        return state.status

    def on_heartbeat(self, kid_id: str, state: KidState) -> None:
        prev_missed = state.missed_heartbeats
        state.missed_heartbeats = 0
        state.status = AgentStatus.ONLINE
        if prev_missed >= WARNING_THRESHOLD:
            self._add_alert(
                kid_id,
                AlertLevel.INFO,
                "Agent is back online.",
            )

    def _add_alert(self, kid_id: str, level: AlertLevel, message: str) -> None:
        alert = Alert(
            kid_id=kid_id,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        self.alerts.insert(0, alert)
        self.alerts = self.alerts[:100]  # keep last 100

    def recent_alerts(self, limit: int = 20) -> list[Alert]:
        return self.alerts[:limit]
