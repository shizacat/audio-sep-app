import pytest

np = pytest.importorskip("numpy")

from audiosep_app.infer import CHUNK_SAMPLES, separate_chunks


def test_short_waveform_is_unchanged_by_identity() -> None:
    waveform = np.linspace(-1, 1, 1000, dtype=np.float32)

    separated = separate_chunks(waveform, lambda chunk: chunk)

    assert separated.shape == waveform.shape
    assert np.allclose(separated, waveform)


def test_long_waveform_is_reconstructed_by_identity() -> None:
    for length in (CHUNK_SAMPLES, CHUNK_SAMPLES + 1, CHUNK_SAMPLES + 96_000, 400_000):
        waveform = np.random.default_rng(length).random(length, dtype=np.float32)

        separated = separate_chunks(waveform, lambda chunk: chunk)

        assert separated.shape == waveform.shape
        assert np.allclose(separated, waveform), length
