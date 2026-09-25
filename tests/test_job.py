from pathlib import Path

import numpy as np
import pytest

from audiosep_app.audio import load_audio, save_audio
from audiosep_app.separation.errors import SeparationError
from audiosep_app.separation.job import make_separation_task


def test_missing_model_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "voice.wav"
    save_audio(source, np.zeros(1000, dtype=np.float32))
    task = make_separation_task(tmp_path / "separator.onnx", tmp_path / "clap_text.onnx")

    with pytest.raises(SeparationError, match="Не найдена модель"):
        task(source, "a child speaking", tmp_path / "out.wav")


def test_unreadable_audio_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "voice.wav"
    source.write_bytes(b"not a wav")
    task = make_separation_task(tmp_path / "separator.onnx", tmp_path / "clap_text.onnx")

    with pytest.raises(SeparationError, match="Не удалось прочитать аудиофайл"):
        task(source, "a child speaking", tmp_path / "out.wav")


def test_runner_saves_separated_audio_and_loads_models_once(tmp_path: Path, monkeypatch) -> None:
    created: list[Path] = []

    class FakeSeparator:
        def __init__(self, separator_path: Path, clap_path: Path) -> None:
            created.append(separator_path)

        def separate(self, waveform: np.ndarray, text: str) -> np.ndarray:
            assert text == "a child speaking"
            return waveform * 0.5

    monkeypatch.setattr("audiosep_app.separation.job.OnnxSeparator", FakeSeparator)
    waveform = np.linspace(-0.4, 0.4, 3200, dtype=np.float32)
    source = tmp_path / "voice.wav"
    save_audio(source, waveform)
    output = tmp_path / "voice_separated.wav"
    task = make_separation_task(tmp_path / "separator.onnx", tmp_path / "clap_text.onnx")

    task(source, "a child speaking", output)
    task(source, "a child speaking", output)

    assert created == [tmp_path / "separator.onnx"]
    assert np.allclose(load_audio(output), waveform * 0.5, atol=1e-5)
