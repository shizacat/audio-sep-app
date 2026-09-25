"""Standard dialog for errors that stop the application from starting."""

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from audiosep_app.paths import missing_model_paths


def startup_error_message(separator_path: Path | None, clap_path: Path | None) -> str | None:
    """Text for a startup failure, or ``None`` when the application can open."""
    missing = missing_model_paths(separator_path, clap_path)
    if not missing:
        return None
    listed = "\n".join(str(path) for path in missing)
    if len(missing) == 1:
        return f"Не найдена модель:\n{listed}"
    return f"Не найдены модели:\n{listed}"


def show_startup_error(message: str, parent: QWidget | None = None) -> None:
    """Show a modal error dialog and return after the user presses OK."""
    QMessageBox.critical(parent, "AudioSep", message)
