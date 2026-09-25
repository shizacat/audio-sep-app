from pathlib import Path

from PySide6.QtWidgets import QApplication

from audiosep_app.separation.errors import SeparationError
from audiosep_app.ui.main_window import MainWindow
from audiosep_app.ui.worker import SeparationTask


def test_window_asks_for_an_audio_file(qapp: QApplication) -> None:
    window = MainWindow(_unused)

    window.separate()

    assert window.windowTitle() == "AudioSep"
    assert window._message.text() == "Укажите аудиофайл."
    qapp.processEvents()


def test_window_asks_for_a_query(qapp: QApplication, tmp_path: Path) -> None:
    source = tmp_path / "voice.wav"
    source.write_bytes(b"")
    window = MainWindow(_unused)
    window._audio_path.setText(str(source))

    window.separate()

    assert window._message.text() == "Укажите звук, который нужно отделить."
    qapp.processEvents()


def test_separation_error_is_shown(qapp: QApplication, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "voice.mp3"
    source.write_bytes(b"")
    output = tmp_path / "voice_separated.mp3"

    def fail(audio_path: Path, query: str, output_path: Path) -> None:
        raise SeparationError("Разделение звука пока не подключено.")

    window = MainWindow(fail)
    window._audio_path.setText(str(source))
    window._query.setPlainText("детский голос")
    monkeypatch.setattr(window, "_ask_output_path", lambda _audio: output)

    window.separate()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    assert window._message.text() == "Разделение звука пока не подключено."
    assert window._separate_button.isEnabled()


def test_success_shows_result_path(qapp: QApplication, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "voice.ogg"
    source.write_bytes(b"")
    output = tmp_path / "voice_separated.ogg"

    def succeed(audio_path: Path, query: str, output_path: Path) -> None:
        output_path.write_bytes(b"separated")

    window = MainWindow(succeed)
    window._audio_path.setText(str(source))
    window._query.setPlainText("речь")
    monkeypatch.setattr(window, "_ask_output_path", lambda _audio: output)

    window.separate()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    assert window._result_path.text() == str(output)
    assert window._message.text() == "Результат сохранён."
    assert output.read_bytes() == b"separated"


def _unused(audio_path: Path, query: str, output_path: Path) -> None:
    raise AssertionError((audio_path, query, output_path))


_task_type_check: SeparationTask = _unused
