"""Loads the top-level `agents/manifest.yaml` -- the declarative,
enable/disable configuration for the multi-agent pipeline.

Kept separate from `src/theravoice/agents/` (the code) on purpose: the
top-level `agents/` folder is operator-facing configuration (which agents
run at all), not implementation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

# src/theravoice/agents/manifest.py -> src/theravoice -> src -> <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MANIFEST_PATH = _REPO_ROOT / "agents" / "manifest.yaml"


@lru_cache(maxsize=None)
def load_agent_manifest(path: str | Path | None = None) -> dict[str, bool]:
    """Return {agent_name: enabled} from agents/manifest.yaml.

    Missing file, missing keys, or a malformed manifest all fail open
    (every agent defaults to enabled) rather than silently disabling parts
    of the pipeline.
    """
    manifest_path = Path(path) if path is not None else _DEFAULT_MANIFEST_PATH
    if not manifest_path.is_file():
        return {}

    try:
        with manifest_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        entries = data.get("agents", [])
        return {
            entry["name"]: bool(entry.get("enabled", True))
            for entry in entries
            if isinstance(entry, dict) and "name" in entry
        }
    except (OSError, yaml.YAMLError, AttributeError, TypeError):
        return {}


def reload_agent_manifest(path: str | Path | None = None) -> dict[str, bool]:
    """Bypass the cache (used by tests that swap in a temp manifest)."""
    load_agent_manifest.cache_clear()
    return load_agent_manifest(path)
