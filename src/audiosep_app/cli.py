"""Command-line arguments for development and debugging."""

import argparse
import logging
from pathlib import Path

from audiosep_app.paths import default_clap_path, default_separator_path

LOG_LEVELS = ("debug", "info", "warning", "error", "critical")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="audiosep-app")
    parser.add_argument(
        "--log-level",
        default="info",
        choices=LOG_LEVELS,
        help="уровень логирования (по умолчанию info)",
    )
    parser.add_argument(
        "--separator",
        type=Path,
        default=None,
        help=f"файл модели разделения (по умолчанию {default_separator_path()})",
    )
    parser.add_argument(
        "--clap",
        type=Path,
        default=None,
        help=f"файл текстовой модели (по умолчанию {default_clap_path()})",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    return build_parser().parse_known_args(argv)


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper())
    logging.basicConfig(level=level)
    logging.getLogger().setLevel(level)
