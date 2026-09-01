"""Bedtime scheduling and warning triggers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from agent.core.config import AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class ScheduleState:
    bedtime_today: datetime
    warnings_sent: set[int] = field(default_factory=set)
    enforcement_started: bool = False
    grace_ended: bool = False


class BedtimeScheduler:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._state: ScheduleState | None = None
        self._tz = ZoneInfo(config.schedule.timezone)

    def update_config(self, config: AgentConfig) -> None:
        self._config = config
        self._tz = ZoneInfo(config.schedule.timezone)
        self._state = None  # reset daily state on config change

    def _parse_bedtime(self, now: datetime) -> datetime:
        hour, minute = map(int, self._config.schedule.bedtime.split(":"))
        bedtime = datetime.combine(now.date(), time(hour, minute), tzinfo=self._tz)
        return bedtime

    def _effective_bedtime(self, now: datetime) -> datetime:
        bedtime = self._parse_bedtime(now)
        if self._config.bonus_until:
            bonus = datetime.fromisoformat(self._config.bonus_until)
            if bonus.tzinfo is None:
                bonus = bonus.replace(tzinfo=self._tz)
            if bonus > bedtime:
                return bonus.astimezone(self._tz)
        return bedtime

    def _ensure_state(self, now: datetime) -> ScheduleState:
        bedtime = self._effective_bedtime(now)
        if self._state is None or self._state.bedtime_today.date() != now.date():
            self._state = ScheduleState(bedtime_today=bedtime)
        else:
            self._state.bedtime_today = bedtime
        return self._state

    def tick(self, now: datetime | None = None) -> dict:
        """
        Check schedule and return actions to take this tick.

        Returns dict with keys:
          - warnings: list of minutes-before-bedtime warnings to show now
          - start_enforcement: bool
          - end_grace: bool (grace period over, kill aggressively)
        """
        now = now or datetime.now(self._tz)
        state = self._ensure_state(now)
        bedtime = state.bedtime_today
        actions: dict = {"warnings": [], "start_enforcement": False, "end_grace": False}

        for minutes in sorted(self._config.schedule.warnings_minutes, reverse=True):
            warning_time = bedtime - timedelta(minutes=minutes)
            if now >= warning_time and minutes not in state.warnings_sent:
                actions["warnings"].append(minutes)
                state.warnings_sent.add(minutes)

        if now >= bedtime and not state.enforcement_started:
            actions["start_enforcement"] = True
            state.enforcement_started = True

        grace_end = bedtime + timedelta(minutes=self._config.enforcement.grace_minutes)
        if now >= grace_end and not state.grace_ended:
            actions["end_grace"] = True
            state.grace_ended = True

        return actions

    def minutes_until_bedtime(self, now: datetime | None = None) -> int:
        now = now or datetime.now(self._tz)
        bedtime = self._effective_bedtime(now)
        delta = bedtime - now
        return max(0, int(delta.total_seconds() // 60))

    def is_enforcing(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(self._tz)
        state = self._ensure_state(now)
        return state.enforcement_started

    def is_past_grace(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(self._tz)
        state = self._ensure_state(now)
        return state.grace_ended
