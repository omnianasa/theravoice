"""Notification channel abstraction (console/log channel ships by default)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

notification_logger = logging.getLogger("theravoice.notifications")


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, patient_id: str, message: str) -> None: ...


class LoggingChannel(NotificationChannel):
    """Default channel: writes notifications to the application log.

    Real push/SMS/email channels can implement `NotificationChannel` and be
    swapped in without touching calling code.
    """

    def send(self, patient_id: str, message: str) -> None:
        notification_logger.info("notification", extra={"patient_id": patient_id, "message": message})
