import logging
from pathlib import Path

import pytest

from audiosep_app.cli import configure_logging, parse_args


def test_log_level_defaults_to_info() -> None:
    args, qt_args = parse_args([])

    assert args.log_level == "info"
    assert qt_args == []


def test_log_level_accepts_debug_and_keeps_qt_arguments() -> None:
    args, qt_args = parse_args(["--log-level", "debug", "-platform", "offscreen"])

    assert args.log_level == "debug"
    assert qt_args == ["-platform", "offscreen"]


def test_model_paths_default_to_none() -> None:
    args, qt_args = parse_args([])

    assert args.separator is None
    assert args.clap is None
    assert qt_args == []


def test_model_paths_keep_qt_arguments() -> None:
    args, qt_args = parse_args(
        [
            "--separator",
            "models/separator.onnx",
            "--clap",
            "models/clap_text.onnx",
            "-platform",
            "offscreen",
        ]
    )

    assert args.separator == Path("models/separator.onnx")
    assert args.clap == Path("models/clap_text.onnx")
    assert qt_args == ["-platform", "offscreen"]


def test_cpu_flag_defaults_to_off() -> None:
    args, qt_args = parse_args([])

    assert args.cpu is False
    assert qt_args == []


def test_cpu_flag_keeps_qt_arguments() -> None:
    args, qt_args = parse_args(["--cpu", "-platform", "offscreen"])

    assert args.cpu is True
    assert qt_args == ["-platform", "offscreen"]


def test_unknown_log_level_exits() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--log-level", "verbose"])


def test_configure_logging_sets_root_level() -> None:
    configure_logging("warning")

    assert logging.getLogger().level == logging.WARNING
