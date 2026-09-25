"""Command-line arguments for development and debugging."""

import argparse
import logging

LOG_LEVELS = ("debug", "info", "warning", "error", "critical")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiosep-app")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=LOG_LEVELS,
        help="уровень логирования (по умолчанию info)",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    return build_parser().parse_known_args(argv)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper())
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)
