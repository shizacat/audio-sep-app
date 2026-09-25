"""Library for the exported CLAP and separator ONNX models.

Load the models once and call ``OnnxSeparator.separate``. The module does not
read command-line arguments and does not open a window.
"""

from collections.abc import Callable
from pathlib import Path

import numpy as np

SAMPLE_RATE = 32_000
CHUNK_SAMPLES = 160_000
LEFT_SAMPLES = 32_000
HOP_SAMPLES = 96_000
RIGHT_SAMPLES = 32_000
TEXT_LENGTH = 512
TOKENIZER_PATH = Path(__file__).resolve().parent / "assets" / "tokenizer.json"
_PAD_TOKEN_ID = 1


def separate_chunks(waveform: np.ndarray, predict_window: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Split a 32 kHz waveform into 5-second windows and stitch the predictions."""
    waveform = np.asarray(waveform, dtype=np.float32).reshape(-1)
    length = waveform.shape[0]
    if length == 0:
        return waveform.copy()

    def run(start: int) -> tuple[np.ndarray, int]:
        valid = min(CHUNK_SAMPLES, length - start)
        chunk = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
        chunk[:valid] = waveform[start : start + valid]
        predicted = np.asarray(predict_window(chunk), dtype=np.float32).reshape(-1)
        if predicted.shape[0] != CHUNK_SAMPLES:
            raise ValueError(
                f"Separator returned {predicted.shape[0]} samples, expected {CHUNK_SAMPLES}."
            )
        return predicted, valid

    if length <= CHUNK_SAMPLES:
        predicted, valid = run(0)
        return predicted[:valid].copy()

    output = np.zeros(length, dtype=np.float32)
    current = 0
    while current + CHUNK_SAMPLES < length:
        predicted, _valid = run(current)
        if current == 0:
            output[: CHUNK_SAMPLES - RIGHT_SAMPLES] = predicted[: CHUNK_SAMPLES - RIGHT_SAMPLES]
        else:
            output[current + LEFT_SAMPLES : current + CHUNK_SAMPLES - RIGHT_SAMPLES] = predicted[
                LEFT_SAMPLES : CHUNK_SAMPLES - RIGHT_SAMPLES
            ]
        current += HOP_SAMPLES
        if current < length:
            predicted, valid = run(current)
            write_from = LEFT_SAMPLES if valid > LEFT_SAMPLES else 0
            output[current + write_from : current + valid] = predicted[write_from:valid]
    return output


class OnnxSeparator:
    """Text-guided separator.

    ``waveform`` is one mono channel of float samples at ``SAMPLE_RATE``.
    ``separate`` returns a waveform of the same length.
    """

    def __init__(self, separator_path: Path, clap_path: Path) -> None:
        if not separator_path.is_file():
            raise FileNotFoundError(separator_path)
        if not clap_path.is_file():
            raise FileNotFoundError(clap_path)
        if not TOKENIZER_PATH.is_file():
            raise FileNotFoundError(TOKENIZER_PATH)

        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._separator = ort.InferenceSession(
            str(separator_path),
            providers=["CPUExecutionProvider"],
        )
        self._clap = ort.InferenceSession(str(clap_path), providers=["CPUExecutionProvider"])
        tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
        tokenizer.enable_truncation(max_length=TEXT_LENGTH)
        tokenizer.enable_padding(length=TEXT_LENGTH, pad_id=_PAD_TOKEN_ID, pad_token="<pad>")
        self._tokenizer = tokenizer

    def embed_text(self, text: str) -> np.ndarray:
        encoded = self._tokenizer.encode(text)
        (embedding,) = self._clap.run(
            None,
            {
                "input_ids": np.asarray([encoded.ids], dtype=np.int64),
                "attention_mask": np.asarray([encoded.attention_mask], dtype=np.int64),
            },
        )
        embedding = np.asarray(embedding, dtype=np.float32)
        if embedding.ndim == 1:
            embedding = embedding[None, :]
        return embedding

    def separate(self, waveform: np.ndarray, text: str) -> np.ndarray:
        condition = self.embed_text(text)

        def predict_window(chunk: np.ndarray) -> np.ndarray:
            mixture = chunk.astype(np.float32)[None, None, :]
            (predicted,) = self._separator.run(
                None,
                {"mixture": mixture, "condition": condition},
            )
            return np.squeeze(predicted)

        return separate_chunks(waveform, predict_window)
