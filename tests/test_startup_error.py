from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from audiosep_app.main import run_application
from audiosep_app.ui.startup_error import show_startup_error, startup_error_message


def test_missing_models_are_listed(tmp_path: Path) -> None:
    separator = tmp_path / "separator.onnx"
    clap = tmp_path / "clap_text.onnx"

    message = startup_error_message(separator, clap)

    assert message is not None
    assert "Не найдены модели" in message
    assert str(separator) in message
    assert str(clap) in message


def test_one_missing_model_uses_singular_text(tmp_path: Path) -> None:
    separator = tmp_path / "separator.onnx"
    separator.write_bytes(b"model")
    clap = tmp_path / "clap_text.onnx"

    message = startup_error_message(separator, clap)

    assert message == f"Не найдена модель:\n{clap}"


def test_present_models_have_no_startup_error(tmp_path: Path) -> None:
    separator = tmp_path / "separator.onnx"
    clap = tmp_path / "clap_text.onnx"
    separator.write_bytes(b"model")
    clap.write_bytes(b"model")

    assert startup_error_message(separator, clap) is None


def test_startup_error_uses_the_standard_dialog(monkeypatch) -> None:
    shown: list[tuple[object, ...]] = []

    def critical(*args: object) -> QMessageBox.StandardButton:
        shown.append(args)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", critical)

    show_startup_error("Не найдена модель:\n/path/separator.onnx")

    assert shown == [(None, "AudioSep", "Не найдена модель:\n/path/separator.onnx")]


def test_missing_models_close_without_the_main_window(
    qapp: QApplication,
    monkeypatch,
    tmp_path: Path,
) -> None:
    shown: list[str] = []
    monkeypatch.setattr("audiosep_app.main.show_startup_error", shown.append)
    monkeypatch.setattr(
        "audiosep_app.main.MainWindow",
        lambda *_args: (_ for _ in ()).throw(AssertionError("window opened")),
    )

    code = run_application(qapp, tmp_path / "separator.onnx", tmp_path / "clap_text.onnx")

    assert code == 1
    assert shown
    assert "separator.onnx" in shown[0]


def test_present_models_open_the_main_window(
    qapp: QApplication,
    monkeypatch,
    tmp_path: Path,
) -> None:
    separator = tmp_path / "separator.onnx"
    clap = tmp_path / "clap_text.onnx"
    separator.write_bytes(b"model")
    clap.write_bytes(b"model")
    opened: list[object] = []

    class FakeWindow:
        def show(self) -> None:
            opened.append(self)

    monkeypatch.setattr("audiosep_app.main.MainWindow", lambda _task: FakeWindow())
    monkeypatch.setattr(qapp, "exec", lambda: 0)

    code = run_application(qapp, separator, clap)

    assert code == 0
    assert len(opened) == 1
