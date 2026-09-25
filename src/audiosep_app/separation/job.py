"""Separation entry point. The AudioSep call is not wired yet."""

import logging
from pathlib import Path

from audiosep_app.separation.errors import SeparationError

logger = logging.getLogger(__name__)


def run_separation(audio_path: Path, query: str, output_path: Path) -> None:
    logger.info("Separation requested for %s with query %r -> %s", audio_path, query, output_path)
    raise SeparationError("Разделение звука пока не подключено.")
