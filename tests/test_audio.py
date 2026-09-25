import numpy as np
import pytest

from audiosep_app.audio import AudioFormatError, load_audio, save_audio
from audiosep_app.infer import SAMPLE_RATE


def test_wav_roundtrip_keeps_samples(tmp_path) -> None:
    waveform = _tone(SAMPLE_RATE)
    path = tmp_path / "tone.wav"
    save_audio(path, waveform)

    loaded = load_audio(path)

    assert loaded.dtype == np.float32
    assert loaded.shape == waveform.shape
    assert np.allclose(loaded, waveform, atol=1e-6)


def test_mp3_and_ogg_roundtrip(tmp_path) -> None:
    waveform = _tone(SAMPLE_RATE)
    for suffix in (".mp3", ".ogg"):
        path = tmp_path / f"tone{suffix}"
        save_audio(path, waveform)

        loaded = load_audio(path)

        assert loaded.dtype == np.float32
        assert loaded.size > waveform.size // 2
        assert np.isfinite(loaded).all()
        assert float(np.max(np.abs(loaded))) > 0.05


def test_unsupported_suffix_is_rejected(tmp_path) -> None:
    path = tmp_path / "tone.flac"

    with pytest.raises(AudioFormatError) as write_error:
        save_audio(path, _tone(100))
    assert write_error.value.action == "write"

    path.write_bytes(b"not-audio")
    with pytest.raises(AudioFormatError) as read_error:
        load_audio(path)
    assert read_error.value.action == "read"


def _tone(length: int) -> np.ndarray:
    time = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    return (0.2 * np.sin(2 * np.pi * 440 * time)).astype(np.float32)
