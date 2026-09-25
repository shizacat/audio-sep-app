"""Library for the exported CLAP and separator ONNX models.

Load the models once and call ``OnnxSeparator.separate``. The module does not
read command-line arguments and does not open a window.

The separator uses a GPU provider when this build of ONNX Runtime has one.
The CLAP text encoder runs once per query and stays on CPU.
"""

import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

logger = logging.getLogger(__name__)

SAMPLE_RATE = 32_000
CHUNK_SAMPLES = 160_000
LEFT_SAMPLES = 32_000
HOP_SAMPLES = 96_000
RIGHT_SAMPLES = 32_000
TEXT_LENGTH = 512
CPU_PROVIDER = "CPUExecutionProvider"
Provider = str | tuple[str, dict[str, str]]

_COREML_GPU: Provider = (
    "CoreMLExecutionProvider",
    {"ModelFormat": "MLProgram", "MLComputeUnits": "CPUAndGPU"},
)
_CUDA: Provider = "CUDAExecutionProvider"
_DIRECTML: Provider = "DmlExecutionProvider"
_ROCM: Provider = "ROCMExecutionProvider"


def tokenizer_path(module_file: Path | None = None) -> Path:
    """Path to the bundled RoBERTa tokenizer.

    A macOS app keeps data files in Contents/Resources, while ``sys._MEIPASS``
    points at Contents/Frameworks.
    """
    beside_module = Path(module_file or __file__).resolve().parent / "assets" / "tokenizer.json"
    if beside_module.is_file():
        return beside_module
    if getattr(sys, "frozen", False):
        meipass = Path(sys._MEIPASS)
        relative = Path("audiosep_app") / "assets" / "tokenizer.json"
        for candidate in (meipass / relative, meipass.parent / "Resources" / relative):
            if candidate.is_file():
                return candidate
    return beside_module


TOKENIZER_PATH = tokenizer_path()
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


def gpu_providers(available: Sequence[str], system: str) -> tuple[Provider, ...]:
    """GPU providers for this OS, in the order they should be tried.

    macOS uses Core ML. Windows tries CUDA for NVIDIA, then DirectML, which runs
    on AMD, Intel, and NVIDIA. Linux tries CUDA for NVIDIA, then ROCm for AMD.
    A provider missing from ``available`` is skipped.
    """
    present = set(available)
    if system == "darwin":
        candidates: tuple[Provider, ...] = (_COREML_GPU,)
    elif system == "win32":
        candidates = (_CUDA, _DIRECTML)
    else:
        candidates = (_CUDA, _ROCM)
    return tuple(provider for provider in candidates if _provider_name(provider) in present)


def choose_separator_session[SessionT](
    model_path: str,
    *,
    cpu: bool,
    available: Sequence[str],
    system: str,
    open_session: Callable[[str, Sequence[Provider]], SessionT],
) -> SessionT:
    """Open the separator on the first GPU that accepts it, otherwise on CPU."""
    if not cpu:
        for provider in gpu_providers(available, system):
            name = _provider_name(provider)
            try:
                session = open_session(model_path, [provider, CPU_PROVIDER])
            except Exception as exc:  # noqa: BLE001
                # Device initialization raises different types. The next provider can still run.
                logger.warning("Separator provider %s failed: %s", name, exc)
                continue
            if name in session.get_providers():
                logger.info("Separator providers: %s", ", ".join(session.get_providers()))
                return session
            logger.warning("Separator provider %s did not join the session", name)
    session = open_session(model_path, [CPU_PROVIDER])
    logger.info("Separator providers: %s", ", ".join(session.get_providers()))
    return session


def _provider_name(provider: Provider) -> str:
    if isinstance(provider, tuple):
        return provider[0]
    return provider


def _open_separator_session(model_path: str, *, cpu: bool) -> object:
    return choose_separator_session(
        model_path,
        cpu=cpu,
        available=ort.get_available_providers(),
        system=sys.platform,
        open_session=lambda path, providers: ort.InferenceSession(path, providers=list(providers)),
    )


class OnnxSeparator:
    """Text-guided separator.

    ``waveform`` is one mono channel of float samples at ``SAMPLE_RATE``.
    ``separate`` returns a waveform of the same length.
    ``cpu`` keeps the separator on CPU. Otherwise a GPU provider is used when
    this build of ONNX Runtime has one.
    """

    def __init__(self, separator_path: Path, clap_path: Path, *, cpu: bool = False) -> None:
        if not separator_path.is_file():
            raise FileNotFoundError(separator_path)
        if not clap_path.is_file():
            raise FileNotFoundError(clap_path)
        if not TOKENIZER_PATH.is_file():
            raise FileNotFoundError(TOKENIZER_PATH)

        self._separator = _open_separator_session(str(separator_path), cpu=cpu)
        self._clap = ort.InferenceSession(str(clap_path), providers=[CPU_PROVIDER])
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
