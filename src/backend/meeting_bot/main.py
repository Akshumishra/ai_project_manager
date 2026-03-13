from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path


def _configure_logging(verbose: bool) -> None:
    """Set up structured console logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meeting_bot",
        description="Google Meet recording bot.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── join ──────────────────────────────────────────────────────────────────
    join_parser = subparsers.add_parser(
        "join",
        help="Join a Google Meet and record it.",
    )
    join_parser.add_argument(
        "urls",
        nargs="+",
        help="One or more Google Meet URLs (e.g. https://meet.google.com/xxx-yyy-zzz).",
    )
    join_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where the WAV recording will be saved. "
        "Overrides the RECORDINGS_DIR env var.",
    )
    join_parser.add_argument(
        "--max-duration",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Maximum recording duration in seconds (default: 14400 = 4 hours).",
    )
    join_parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="Force headless mode (hidden browser). Default follows HEADLESS env var.",
    )

    # ── serve ───────────────────────────────────────────────────────────────
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
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0).",
    )

    # ── seed-login ────────────────────────────────────────────────────────────
    subparsers.add_parser(
        "seed-login",
        help="Open a browser for one-time interactive Google sign-in. "
        "Run this once before using 'join'.",
    )

    return parser


async def _cmd_join(args: argparse.Namespace) -> int:
    """Handle the 'join' sub-command."""
    import os
    from meeting_bot.config import BotConfig

    # Allow --output-dir to override the env var at runtime.
    if args.output_dir is not None:
        os.environ["RECORDINGS_DIR"] = str(args.output_dir)

    # Allow --headless to override env var.
    if args.headless is not None:
        os.environ["HEADLESS"] = "true" if args.headless else "false"

    config = BotConfig.from_env()

    from meeting_bot.bot.orchestrator import MultiSessionOrchestrator

    orchestrator = MultiSessionOrchestrator(config)

    print(f"\n🤖  Bot joining {len(args.urls)} meeting(s)")
    print(f"📁  Saving recordings to: {config.recordings_dir}")
    print(f"🖥️   Headless mode: {config.headless}\n")

    for url in args.urls:
        await orchestrator.start_session(
            meet_url=url,
            max_duration=args.max_duration,
        )

    await orchestrator.wait_all()
    print("\n✅  All sessions complete.\n")
    return 0


async def _cmd_seed_login() -> int:
    """Handle the 'seed-login' sub-command."""
    from meeting_bot.config import BotConfig
    from meeting_bot.bot.session_manager import SessionManager

    config = BotConfig.from_env()
    manager = SessionManager(config)

    print("\n🔑  Opening browser for one-time Google sign-in…")
    print("    Sign in, then close the browser tab to continue.\n")
    await manager.seed_login()
    print("✅  Login complete. Profile saved — you can now run 'join'.\n")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Handle the 'serve' sub-command to start the FastAPI server."""
    import uvicorn
    from meeting_bot.api import app

    print(f"\n🚀  Starting API server on {args.host}:{args.port}")
    print("    Documentation: http://localhost:8000/docs\n")

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    try:
        if args.command == "join":
            exit_code = asyncio.run(_cmd_join(args))
        elif args.command == "seed-login":
            exit_code = asyncio.run(_cmd_seed_login())
        elif args.command == "serve":
            # uvicorn.run is synchronous/blocks, so we don't need asyncio.run here
            # but _cmd_serve is not async anyway.
            exit_code = _cmd_serve(args)
        else:
            parser.print_help()
            exit_code = 1
    except ValueError as exc:
        # Config errors (missing env vars) surface here.
        print(f"\n❌  Configuration error: {exc}")
        print("    Copy .env.example to .env and fill in the required values.\n")
        exit_code = 2
    except KeyboardInterrupt:
        print("\nInterrupted — session stopped.\n")
        exit_code = 130

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
