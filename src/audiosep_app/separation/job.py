"""Run ONNX separation on an audio file."""

import logging
from collections.abc import Callable
from pathlib import Path

from audiosep_app.audio import AudioFormatError, load_audio, save_audio
from audiosep_app.infer import OnnxSeparator
from audiosep_app.paths import resolved_model_paths
from audiosep_app.separation.errors import SeparationError

logger = logging.getLogger(__name__)

SeparationTask = Callable[[Path, str, Path], None]

_AUDIO_MESSAGES = {
    "read": "Не удалось прочитать аудиофайл.",
    "write": "Не удалось сохранить аудиофайл.",
}


class SeparationRunner:
    """Load the models on the first call and reuse them after that."""

    def __init__(self, separator_path: Path | None, clap_path: Path | None) -> None:
        self._separator_path, self._clap_path = resolved_model_paths(separator_path, clap_path)
        self._separator: OnnxSeparator | None = None

    def __call__(self, audio_path: Path, query: str, output_path: Path) -> None:
        logger.info(
            "Separation requested for %s with query %r -> %s",
            audio_path,
            query,
            output_path,
        )
        try:
            waveform = load_audio(audio_path)
            separated = self._engine().separate(waveform, query)
            save_audio(output_path, separated)
        except FileNotFoundError as exc:
            raise SeparationError(f"Не найдена модель: {exc}") from exc
        except AudioFormatError as exc:
            logger.exception("Audio file failed")
            raise SeparationError(_AUDIO_MESSAGES[exc.action]) from exc

    def _engine(self) -> OnnxSeparator:
        if self._separator is None:
            logger.info("Loading models %s and %s", self._separator_path, self._clap_path)
            self._separator = OnnxSeparator(self._separator_path, self._clap_path)
        return self._separator


def make_separation_task(
    separator_path: Path | None = None,
    clap_path: Path | None = None,
) -> SeparationTask:
    return SeparationRunner(separator_path, clap_path)
