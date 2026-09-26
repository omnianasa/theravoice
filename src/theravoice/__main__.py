"""Command-line entry point for TheraVoice.

Usage:
    theravoice --help
    theravoice --version
    theravoice serve [--host HOST] [--port PORT] [--reload]
    theravoice analyze --patient-id ID --text "..."
    theravoice sync-bee --patient-id ID
"""

from __future__ import annotations

import argparse
import sys

from theravoice.version import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="theravoice",
        description="TheraVoice: non-diagnostic assistive speech/communication monitoring companion.",
    )
    parser.add_argument(
        "--version", action="store_true", help="Print the installed TheraVoice version and exit."
    )

    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the TheraVoice API server (uvicorn).")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Run a one-off transcript analysis through the local pipeline."
    )
    analyze_parser.add_argument("--patient-id", required=True)
    analyze_parser.add_argument("--text", required=True)

    sync_bee_parser = subparsers.add_parser(
        "sync-bee",
        help=(
            "Pull new conversations from Bee (mock/sync/proxy per bee.mode in "
            "config -- see docs/bee_integration.md) and run them through the "
            "full analysis pipeline."
        ),
    )
    sync_bee_parser.add_argument("--patient-id", required=True)

    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "theravoice.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    import json

    from theravoice.pipeline.analysis_pipeline import AnalysisPipeline
    from theravoice.storage.database import get_session_factory, init_db

    init_db()
    session_factory = get_session_factory()
    pipeline = AnalysisPipeline(session_factory=session_factory)
    result = pipeline.run_transcript(patient_id=args.patient_id, text=args.text)
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


def _cmd_sync_bee(args: argparse.Namespace) -> int:
    from theravoice.ingestion.bee import BeeConnectionError
    from theravoice.pipeline.analysis_pipeline import PatientNotFoundError
    from theravoice.pipeline.monitoring_pipeline import build_monitoring_pipeline
    from theravoice.storage.database import get_session_factory, init_db

    init_db()
    pipeline = build_monitoring_pipeline(session_factory=get_session_factory())

    try:
        results = pipeline.poll_patient(args.patient_id)
    except PatientNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except BeeConnectionError as exc:
        print(f"Could not reach Bee: {exc}", file=sys.stderr)
        print(
            "See docs/bee_integration.md, or set bee.mode: mock in config "
            "for local testing without a Bee account.",
            file=sys.stderr,
        )
        return 1

    if not results:
        print("No new Bee conversations since the last sync.")
        return 0

    print(f"Processed {len(results)} new conversation(s) from Bee for {args.patient_id}.\n")
    for i, result in enumerate(results, start=1):
        print(f"[{i}] status={result.status}  baseline_status={result.baseline_status}")
        for event in result.events:
            print(f"    \u26a0 {event.type} ({event.severity})")
            for evidence in event.evidence:
                print(f"       - {evidence.description}")
        for action in result.actions:
            print(f"    \u2192 [{action.type}] {action.message}")
        if not result.events and not result.actions:
            print("    (no notable deviation from personal baseline)")
    print("\nThese observations are descriptive and are not a diagnosis.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"theravoice {__version__}")
        return 0

    if args.command == "serve":
        return _cmd_serve(args)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "sync-bee":
        return _cmd_sync_bee(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
