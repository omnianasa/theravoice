"""Response latency: time between a prompt ending and the response starting.

TheraVoice never fabricates timing. If timestamps are unavailable, this
returns None rather than inventing a value.
"""

from __future__ import annotations

from datetime import datetime


def compute_response_latency_seconds(
    response_start: datetime | None, previous_prompt_end: datetime | None
) -> float | None:
    if response_start is None or previous_prompt_end is None:
        return None
    delta = (response_start - previous_prompt_end).total_seconds()
    if delta < 0:
        return None
    return delta
