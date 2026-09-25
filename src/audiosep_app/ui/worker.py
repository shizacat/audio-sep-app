"""Background separation so the window stays responsive."""

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audiosep_app.separation.errors import SeparationError
from audiosep_app.separation.job import SeparationTask

logger = logging.getLogger(__name__)


class SeparationWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        task: SeparationTask,
        audio_path: Path,
        query: str,
        output_path: Path,
    ) -> None:
        super().__init__()
        self._task = task
        self._audio_path = audio_path
        self._query = query
        self._output_path = output_path

    def run(self) -> None:
        try:
            self._task(self._audio_path, self._query, self._output_path)
        except SeparationError as exc:
            logger.exception("Separation failed")
            self.failed.emit(str(exc))
        except Exception:
            logger.exception("Separation failed")
            self.failed.emit("Не удалось отделить звук.")
        else:
            self.finished_ok.emit(str(self._output_path))
