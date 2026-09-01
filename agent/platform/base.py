"""Platform abstraction for notifications and system integration."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PlatformAdapter(ABC):
    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """Show a warning dialog to the user."""

    @abstractmethod
    def show_bedtime_notice(self, message: str) -> None:
        """Show the final bedtime enforcement notice."""

    def platform_name(self) -> str:
        return "unknown"
