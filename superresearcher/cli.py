"""Command-line entry point for SuperResearcher."""

from __future__ import annotations

import argparse

from . import __version__
from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="superresearcher",
        description="SuperResearcher: commission a junior research analyst, not a quick AI essay. "
        "Runs the local research UI in your browser.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", default=8765, type=int, help="Port to serve on (default: 8765)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
