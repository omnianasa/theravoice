"""Export helpers: serialize reports to JSON-friendly dicts for API responses."""

from __future__ import annotations

from pydantic import BaseModel


def to_json_dict(model: BaseModel) -> dict:
    return model.model_dump(mode="json")
