import sys
from pathlib import Path

import numpy as np
from tokenizers import Tokenizer

from audiosep_app.infer import (
    CHUNK_SAMPLES,
    TEXT_LENGTH,
    TOKENIZER_PATH,
    separate_chunks,
    tokenizer_path,
)


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


def test_frozen_macos_tokenizer_is_read_from_resources(tmp_path: Path, monkeypatch) -> None:
    frameworks = tmp_path / "Contents" / "Frameworks"
    tokenizer = tmp_path / "Contents" / "Resources" / "audiosep_app" / "assets" / "tokenizer.json"
    tokenizer.parent.mkdir(parents=True)
    tokenizer.write_text("{}", encoding="utf-8")
    frameworks.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(frameworks), raising=False)

    found = tokenizer_path(frameworks / "audiosep_app" / "infer.py")

    assert found == tokenizer


def test_bundled_tokenizer_pads_to_the_model_length() -> None:
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    tokenizer.enable_truncation(max_length=TEXT_LENGTH)
    tokenizer.enable_padding(length=TEXT_LENGTH, pad_id=1, pad_token="<pad>")

    encoded = tokenizer.encode("a child speaking")

    assert len(encoded.ids) == TEXT_LENGTH
    assert encoded.ids[0] == 0
    assert encoded.ids[-1] == 1
    assert encoded.attention_mask[0] == 1
    assert encoded.attention_mask[-1] == 0
