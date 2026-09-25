"""Main window of the application."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from audiosep_app.formats import AUDIO_FILTER, AUDIO_SUFFIXES
from audiosep_app.ui.worker import SeparationTask, SeparationWorker

_REMOVE_HINT = (
    "Отделённый звук всегда сохраняется рядом с исходником, к имени добавляется _separated. "
    "Если галка включена, этот звук вычитается из исходной записи, "
    "и рядом сохраняется второй файл с суффиксом _without."
)


class MainWindow(QMainWindow):
    def __init__(self, separate_audio: SeparationTask) -> None:
        super().__init__()
        self._separate_audio = separate_audio
        self._worker: SeparationWorker | None = None

        self.setWindowTitle("AudioSep")
        self.resize(800, 480)

        hint = QLabel("Укажите запись и звук, который нужно отделить.")
        hint.setWordWrap(True)

        self._audio_path = QLineEdit()
        self._audio_path.setReadOnly(True)
        self._audio_path.setPlaceholderText("Файл не выбран")
        self._browse = QPushButton("Обзор…")
        self._browse.clicked.connect(self._browse_audio)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self._audio_path)
        audio_row.addWidget(self._browse)

        self._query = QPlainTextEdit()
        self._query.setPlaceholderText("Например, детский голос")
        self._query.setFixedHeight(96)

        self._remove_from_original = QCheckBox("Убрать отделённый звук из оригинала")
        self._remove_hint = QLabel(_REMOVE_HINT)
        self._remove_hint.setWordWrap(True)

        self._separate_button = QPushButton("Отделить")
        self._separate_button.clicked.connect(self.separate)

        self._open_folder = QPushButton("Открыть папку")
        self._open_folder.setEnabled(False)
        self._open_folder.clicked.connect(self._open_result_folder)

        result_row = QHBoxLayout()
        result_row.addWidget(QLabel("Файлы результата"))
        result_row.addStretch()
        result_row.addWidget(self._open_folder)

        self._result_path = QPlainTextEdit()
        self._result_path.setReadOnly(True)
        self._result_path.setPlaceholderText("Появится здесь после отделения")
        self._result_path.setFixedHeight(64)

        self._message = QLabel()
        self._message.setWordWrap(True)

        form = QVBoxLayout()
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.addWidget(hint)
        form.addWidget(QLabel("Аудиофайл"))
        form.addLayout(audio_row)
        form.addWidget(QLabel("Звук, который нужно отделить"))
        form.addWidget(self._query)
        form.addWidget(self._remove_from_original)
        form.addWidget(self._remove_hint)
        form.addWidget(self._separate_button)
        form.addLayout(result_row)
        form.addWidget(self._result_path)
        form.addWidget(self._message)
        form.addStretch()

        central = QWidget()
        central.setLayout(form)
        self.setCentralWidget(central)

    def separate(self) -> None:
        audio_path = Path(self._audio_path.text())
        query = self._query.toPlainText().strip()
        if not self._is_audio_file(audio_path):
            self._show_message("Укажите аудиофайл.")
            return
        if not query:
            self._show_message("Укажите звук, который нужно отделить.")
            return

        self._start(audio_path, query, self._remove_from_original.isChecked())

    def _browse_audio(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(self, "Аудиофайл", "", AUDIO_FILTER)
        if selected:
            self._audio_path.setText(selected)
            self._open_folder.setEnabled(True)
            self._show_message("")

    def _start(self, audio_path: Path, query: str, remove_from_original: bool) -> None:
        self._set_busy(True)
        self._result_path.clear()
        self._show_message("Отделение звука…")
        worker = SeparationWorker(
            self._separate_audio,
            audio_path,
            query,
            remove_from_original,
        )
        worker.finished_ok.connect(self._on_separated)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _on_separated(self, output_path: str) -> None:
        self._result_path.setPlainText(output_path)
        self._show_message("Результат сохранён.")

    def _on_failed(self, message: str) -> None:
        self._show_message(message)

    def _on_worker_finished(self) -> None:
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _set_busy(self, busy: bool) -> None:
        for widget in (
            self._browse,
            self._query,
            self._remove_from_original,
            self._separate_button,
            self._open_folder,
        ):
            widget.setEnabled(not busy)

    def _open_result_folder(self) -> None:
        folder = self._result_folder()
        if folder is None:
            self._show_message("Сначала укажите аудиофайл.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _result_folder(self) -> Path | None:
        saved = self._result_path.toPlainText().strip()
        if saved:
            return Path(saved.splitlines()[0]).parent
        audio_path = Path(self._audio_path.text())
        if self._is_audio_file(audio_path):
            return audio_path.parent
        return None

    def _show_message(self, text: str) -> None:
        self._message.setText(text)
        self.statusBar().showMessage(text)

    @staticmethod
    def _is_audio_file(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES
