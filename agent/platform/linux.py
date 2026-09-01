"""Linux-specific UI and helpers."""

from __future__ import annotations

import shutil
import subprocess

from agent.platform.base import PlatformAdapter


class LinuxAdapter(PlatformAdapter):
    def platform_name(self) -> str:
        return "Linux"

    def _run_dialog(self, title: str, message: str) -> None:
        if shutil.which("zenity"):
            subprocess.run(
                ["zenity", "--warning", "--title", title, "--text", message, "--no-wrap"],
                check=False,
            )
            return
        if shutil.which("notify-send"):
            subprocess.run(
                ["notify-send", "-u", "critical", title, message],
                check=False,
            )
            return
        # Fallback: terminal bell + print (better than nothing in headless dev)
        print(f"[WARNING] {title}: {message}")

    def show_warning(self, title: str, message: str) -> None:
        self._run_dialog(title, message)

    def show_bedtime_notice(self, message: str) -> None:
        self._run_dialog("Bedtime", message)
