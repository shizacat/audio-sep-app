from PySide6.QtWidgets import QApplication, QLabel

from audiosep_app.ui.main_window import MainWindow


def test_window_opens(qapp: QApplication) -> None:
    window = MainWindow()

    assert window.windowTitle() == "AudioSep"
    label = window.findChild(QLabel)
    assert label is not None
    assert "аудиофайл" in label.text()
    qapp.processEvents()
