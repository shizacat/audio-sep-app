import threading
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from audiosep_app.formats import result_paths
from audiosep_app.separation.errors import SeparationError
from audiosep_app.ui.main_window import MainWindow, format_elapsed
from audiosep_app.ui.worker import SeparationTask


def test_remove_checkbox_has_a_visible_explanation(qapp: QApplication) -> None:
    window = MainWindow(_unused)

    window.show()
    qapp.processEvents()

    hint = window._remove_hint.text()

    assert window._remove_hint.isVisible()
    assert window._remove_hint.height() >= window._remove_hint.heightForWidth(window._remove_hint.width())
    window.resize(280, 700)
    qapp.processEvents()
    assert window._remove_hint.height() >= window._remove_hint.heightForWidth(window._remove_hint.width())
    assert "_separated" in hint
    assert "_without" in hint
    assert "вычитается" in hint


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
    assert window._message.text().startswith("Результат сохранён за ")
    assert window._message.text().endswith(".")
    assert window.statusBar().currentMessage() == window._message.text()
    assert separated.read_bytes() == b"separated"


def test_inputs_are_blocked_until_separation_finishes(qapp: QApplication, tmp_path: Path) -> None:
    source = tmp_path / "voice.wav"
    source.write_bytes(b"")
    started = threading.Event()
    release = threading.Event()

    def block(audio_path: Path, query: str, remove_from_original: bool) -> None:
        started.set()
        assert release.wait(3)

    window = MainWindow(block)
    window._audio_path.setText(str(source))
    window._query.setPlainText("речь")

    window.separate()
    assert started.wait(3)
    qapp.processEvents()

    assert not window._browse.isEnabled()
    assert not window._query.isEnabled()
    assert not window._remove_from_original.isEnabled()
    assert not window._separate_button.isEnabled()
    assert not window._open_folder.isEnabled()

    release.set()
    assert window._worker is not None
    assert window._worker.wait(3000)
    qapp.processEvents()

    assert window._browse.isEnabled()
    assert window._query.isEnabled()
    assert window._remove_from_original.isEnabled()
    assert window._separate_button.isEnabled()
    assert window._open_folder.isEnabled()


def test_open_folder_shows_the_result_directory(qapp: QApplication, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "voice.wav"
    source.write_bytes(b"")
    opened: list[str] = []

    def capture(url: QUrl) -> bool:
        opened.append(url.toLocalFile())
        return True

    monkeypatch.setattr("audiosep_app.ui.main_window.QDesktopServices.openUrl", capture)
    window = MainWindow(_unused)
    window._audio_path.setText(str(source))
    window._result_path.setPlainText(
        f"{tmp_path / 'voice_separated.wav'}\n{tmp_path / 'voice_without.wav'}"
    )
    window._open_folder.setEnabled(True)

    window._open_folder.click()
    qapp.processEvents()

    assert opened == [str(tmp_path)]


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


def test_elapsed_time_uses_a_comma_and_larger_units() -> None:
    assert format_elapsed(3.24) == "3,2 с"
    assert format_elapsed(0) == "0,0 с"
    assert format_elapsed(75) == "1 мин 15 с"
    assert format_elapsed(3661) == "1 ч 1 мин 1 с"


def _unused(audio_path: Path, query: str, remove_from_original: bool) -> None:
    raise AssertionError((audio_path, query, remove_from_original))


_task_type_check: SeparationTask = _unused
