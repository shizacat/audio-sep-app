from pathlib import Path

from PySide6.QtWidgets import QApplication

from audiosep_app.formats import result_paths
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


def test_separation_error_is_shown(qapp: QApplication, tmp_path: Path) -> None:
    source = tmp_path / "voice.mp3"
    source.write_bytes(b"")

    def fail(audio_path: Path, query: str, remove_from_original: bool) -> None:
        raise SeparationError("Разделение звука пока не подключено.")

    window = MainWindow(fail)
    window._audio_path.setText(str(source))
    window._query.setPlainText("детский голос")

    window.separate()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    assert window._message.text() == "Разделение звука пока не подключено."
    assert window._separate_button.isEnabled()


def test_success_shows_result_path(qapp: QApplication, tmp_path: Path) -> None:
    source = tmp_path / "voice.ogg"
    source.write_bytes(b"")
    separated, _residual = result_paths(source, False)

    def succeed(audio_path: Path, query: str, remove_from_original: bool) -> None:
        assert remove_from_original is False
        result_paths(audio_path, remove_from_original)[0].write_bytes(b"separated")

    window = MainWindow(succeed)
    window._audio_path.setText(str(source))
    window._query.setPlainText("речь")

    window.separate()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    assert window._result_path.toPlainText() == str(separated)
    assert window._message.text() == "Результат сохранён."
    assert separated.read_bytes() == b"separated"


def test_checkbox_saves_both_files_with_suffixes(qapp: QApplication, tmp_path: Path) -> None:
    source = tmp_path / "voice.wav"
    source.write_bytes(b"")

    def succeed(audio_path: Path, query: str, remove_from_original: bool) -> None:
        separated, residual = result_paths(audio_path, remove_from_original)
        assert residual is not None
        separated.write_bytes(b"separated")
        residual.write_bytes(b"without")

    window = MainWindow(succeed)
    window._audio_path.setText(str(source))
    window._query.setPlainText("детский голос")
    window._remove_from_original.setChecked(True)

    window.separate()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    separated, residual = result_paths(source, True)
    assert residual is not None
    assert window._result_path.toPlainText() == f"{separated}\n{residual}"
    assert separated.name == "voice_separated.wav"
    assert residual.name == "voice_without.wav"
    assert separated.read_bytes() == b"separated"
    assert residual.read_bytes() == b"without"


def _unused(audio_path: Path, query: str, remove_from_original: bool) -> None:
    raise AssertionError((audio_path, query, remove_from_original))


_task_type_check: SeparationTask = _unused
