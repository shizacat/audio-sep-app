"""Main window of the application."""

from pathlib import Path

from PySide6.QtWidgets import (
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

from audiosep_app.ui.worker import SeparationTask, SeparationWorker

AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg"}
AUDIO_FILTER = "Аудиофайл (*.mp3 *.wav *.ogg)"


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
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self._browse_audio)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self._audio_path)
        audio_row.addWidget(browse)

        self._query = QPlainTextEdit()
        self._query.setPlaceholderText("Например, детский голос")
        self._query.setFixedHeight(96)

        self._separate_button = QPushButton("Отделить…")
        self._separate_button.clicked.connect(self.separate)

        self._result_path = QLineEdit()
        self._result_path.setReadOnly(True)
        self._result_path.setPlaceholderText("Появится здесь после отделения")

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
        form.addWidget(self._separate_button)
        form.addWidget(QLabel("Файл результата"))
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

        output_path = self._ask_output_path(audio_path)
        if output_path is None:
            return
        self._start(audio_path, query, output_path)

    def _browse_audio(self) -> None:
        selected, _filter = QFileDialog.getOpenFileName(self, "Аудиофайл", "", AUDIO_FILTER)
        if selected:
            self._audio_path.setText(selected)
            self._show_message("")

    def _ask_output_path(self, audio_path: Path) -> Path | None:
        suggested = audio_path.with_name(f"{audio_path.stem}_separated{audio_path.suffix}")
        selected, _filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить результат",
            str(suggested),
            AUDIO_FILTER,
        )
        if not selected:
            return None
        output_path = Path(selected)
        if output_path.suffix.lower() not in AUDIO_SUFFIXES:
            output_path = output_path.with_suffix(".wav")
        return output_path

    def _start(self, audio_path: Path, query: str, output_path: Path) -> None:
        self._separate_button.setEnabled(False)
        self._result_path.clear()
        self._show_message("Отделение звука…")
        worker = SeparationWorker(self._separate_audio, audio_path, query, output_path)
        worker.finished_ok.connect(self._on_separated)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _on_separated(self, output_path: str) -> None:
        self._result_path.setText(output_path)
        self._show_message("Результат сохранён.")

    def _on_failed(self, message: str) -> None:
        self._show_message(message)

    def _on_worker_finished(self) -> None:
        self._separate_button.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _show_message(self, text: str) -> None:
        self._message.setText(text)
        self.statusBar().showMessage(text)

    @staticmethod
    def _is_audio_file(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES
