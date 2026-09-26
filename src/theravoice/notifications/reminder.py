"""Dispatches REMIND / REQUEST_CHECK_IN actions to a notification channel."""

from __future__ import annotations

from theravoice.notifications.channels import LoggingChannel, NotificationChannel
from theravoice.schemas.action import Action


class ReminderDispatcher:
    def __init__(self, channel: NotificationChannel | None = None) -> None:
        self._channel = channel or LoggingChannel()

    def dispatch(self, action: Action) -> None:
        if action.type in ("REMIND", "REQUEST_CHECK_IN", "NOTIFY"):
            self._channel.send(action.patient_id, action.message)
