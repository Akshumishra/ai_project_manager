from __future__ import annotations

import argparse
import logging
import sys

import uvicorn


def _configure_logging(verbose: bool) -> None:
    """Set up structured console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="meeting_bot",
        description="Google Meet backend API server.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── serve ─────────────────────────────────────────────────────────────────
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the FastAPI API server to control the bot via REST.",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000).",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1).",
    )

    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    """Handle the 'serve' sub-command to start the FastAPI server."""
    from meeting_bot.api import app

    print(f"\n🚀  Starting API server on {args.host}:{args.port}")
    print(f"    Documentation: http://{args.host}:{args.port}/docs\n")

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        if args.command == "serve":
            exit_code = _cmd_serve(args)
        else:
            parser.print_help()
            exit_code = 1
    except ValueError as exc:
        print(f"\n❌  Configuration error: {exc}")
        print("    Copy .env.example to .env and fill in the required values.\n")
        exit_code = 2
    except KeyboardInterrupt:
        print("\nInterrupted — session stopped.\n")
        exit_code = 130

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
