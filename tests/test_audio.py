import numpy as np
import pytest

from audiosep_app.audio import AudioFormatError, load_audio, save_audio, subtract_extracted
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


def test_subtract_extracted_scales_only_when_the_peak_would_clip() -> None:
    mixture = np.array([0.2, -0.4, 0.4], dtype=np.float32)
    extracted = np.array([0.1, -0.2, 0.2], dtype=np.float32)

    assert np.allclose(subtract_extracted(mixture, extracted), mixture * 0.5)

    over = subtract_extracted(
        np.array([1.0, -1.0], dtype=np.float32),
        np.array([-0.5, 0.5], dtype=np.float32),
    )
    assert np.isclose(float(np.max(np.abs(over))), 0.99)


def _tone(length: int) -> np.ndarray:
    time = np.arange(length, dtype=np.float32) / SAMPLE_RATE
    return (0.2 * np.sin(2 * np.pi * 440 * time)).astype(np.float32)
