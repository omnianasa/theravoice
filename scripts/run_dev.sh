#!/usr/bin/env bash
# Run the TheraVoice API locally in development mode.
set -euo pipefail
export THERAVOICE_ENV="${THERAVOICE_ENV:-development}"
cd "$(dirname "$0")/.."
uvicorn theravoice.api.app:app --reload --host 127.0.0.1 --port 8000
