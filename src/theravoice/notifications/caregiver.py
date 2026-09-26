"""Caregiver notification helpers (opt-in, human-controlled recipient list)."""

from __future__ import annotations

from theravoice.notifications.channels import LoggingChannel, NotificationChannel


class CaregiverNotifier:
    def __init__(self, channel: NotificationChannel | None = None) -> None:
        self._channel = channel or LoggingChannel()

    def notify(self, patient_id: str, message: str) -> None:
        self._channel.send(patient_id, f"[Caregiver notice] {message}")
