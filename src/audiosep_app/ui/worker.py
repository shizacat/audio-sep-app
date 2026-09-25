"""Background separation so the window stays responsive."""

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audiosep_app.formats import result_paths
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
        remove_from_original: bool,
    ) -> None:
        super().__init__()
        self._task = task
        self._audio_path = audio_path
        self._query = query
        self._remove_from_original = remove_from_original

    def run(self) -> None:
        try:
            self._task(self._audio_path, self._query, self._remove_from_original)
        except SeparationError as exc:
            logger.exception("Separation failed")
            self.failed.emit(str(exc))
        except Exception:
            logger.exception("Separation failed")
            self.failed.emit("Не удалось отделить звук.")
        else:
            separated_path, residual_path = result_paths(
                self._audio_path,
                self._remove_from_original,
            )
            saved = [separated_path] if residual_path is None else [separated_path, residual_path]
            self.finished_ok.emit("\n".join(str(path) for path in saved))
