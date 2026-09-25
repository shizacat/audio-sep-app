"""Default locations of the exported ONNX models."""

import sys
from pathlib import Path

SEPARATOR_FILENAME = "separator.onnx"
CLAP_FILENAME = "clap_text.onnx"
PACKAGED_MODEL_DIRNAME = "models"
DEV_MODEL_DIRNAME = "local"


def packaged_model_directory(executable: Path) -> Path:
    """Directory of ONNX files shipped next to the frozen executable.

    On macOS that is inside the ``.app``. Gatekeeper runs a downloaded app from
    a temporary copy and does not take files that sit beside the bundle.
    """
    return executable.resolve().parent / PACKAGED_MODEL_DIRNAME


def model_directory() -> Path:
    """Directory that holds the ONNX files when no path was passed in."""
    if getattr(sys, "frozen", False):
        return packaged_model_directory(Path(sys.executable))
    return Path(__file__).resolve().parents[2] / DEV_MODEL_DIRNAME


def default_separator_path() -> Path:
    return model_directory() / SEPARATOR_FILENAME


def default_clap_path() -> Path:
    return model_directory() / CLAP_FILENAME


def resolved_model_paths(
    separator_path: Path | None,
    clap_path: Path | None,
) -> tuple[Path, Path]:
    """Paths that will be opened, including defaults for arguments that were omitted."""
    return (
        separator_path or default_separator_path(),
        clap_path or default_clap_path(),
    )


def missing_model_paths(separator_path: Path | None, clap_path: Path | None) -> list[Path]:
    separator, clap = resolved_model_paths(separator_path, clap_path)
    return [path for path in (separator, clap) if not path.is_file()]
