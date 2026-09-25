"""Audio file suffixes the window and the adapter share."""

from pathlib import Path

AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg"}
AUDIO_FILTER = "Аудиофайл (*.mp3 *.wav *.ogg)"
SEPARATED_SUFFIX = "_separated"
WITHOUT_SUFFIX = "_without"


def result_paths(audio_path: Path, remove_from_original: bool) -> tuple[Path, Path | None]:
    """Paths next to the source. The second path is set only when the residual is saved."""
    separated = audio_path.with_name(f"{audio_path.stem}{SEPARATED_SUFFIX}{audio_path.suffix}")
    if not remove_from_original:
        return separated, None
    residual = audio_path.with_name(f"{audio_path.stem}{WITHOUT_SUFFIX}{audio_path.suffix}")
    return separated, residual
