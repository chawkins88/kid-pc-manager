"""Cross-platform warning dispatch."""

from __future__ import annotations

import platform
import sys

from agent.platform.base import PlatformAdapter


def get_platform_adapter() -> PlatformAdapter:
    system = platform.system()
    if system == "Windows":
        from agent.platform.windows import WindowsAdapter

        return WindowsAdapter()
    if system == "Linux":
        from agent.platform.linux import LinuxAdapter

        return LinuxAdapter()
    print(f"Unsupported platform: {system}", file=sys.stderr)
    from agent.platform.linux import LinuxAdapter

    return LinuxAdapter()


def format_bedtime_warning(minutes: int, kid_name: str) -> tuple[str, str]:
    title = "Bedtime Reminder"
    if minutes <= 1:
        message = f"Hi {kid_name}, bedtime is in 1 minute. Please save your game and wrap up."
    else:
        message = f"Hi {kid_name}, bedtime is in {minutes} minutes. Please start wrapping up."
    return title, message


def format_bedtime_enforcement(kid_name: str, grace_minutes: int) -> str:
    return (
        f"{kid_name}, it's bedtime. You have {grace_minutes} minutes of grace "
        f"before blocked apps are closed."
    )


def format_grace_ended(kid_name: str) -> str:
    return f"{kid_name}, grace period is over. Blocked apps will now be closed."
