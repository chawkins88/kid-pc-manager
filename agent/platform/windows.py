"""Windows-specific UI and helpers."""

from __future__ import annotations

import ctypes

from agent.platform.base import PlatformAdapter


class WindowsAdapter(PlatformAdapter):
    MB_OK = 0x0
    MB_ICONWARNING = 0x30
    MB_TOPMOST = 0x40000
    MB_SETFOREGROUND = 0x10000

    def platform_name(self) -> str:
        return "Windows"

    def _message_box(self, title: str, message: str) -> None:
        flags = self.MB_OK | self.MB_ICONWARNING | self.MB_TOPMOST | self.MB_SETFOREGROUND
        ctypes.windll.user32.MessageBoxW(0, message, title, flags)

    def show_warning(self, title: str, message: str) -> None:
        self._message_box(title, message)

    def show_bedtime_notice(self, message: str) -> None:
        self._message_box("Bedtime", message)
