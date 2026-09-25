"""Read and write an audio file as mono float32 at the model sample rate."""

from pathlib import Path

import miniaudio
import numpy as np
import soundfile as sf

from audiosep_app.formats import AUDIO_SUFFIXES
from audiosep_app.infer import SAMPLE_RATE

_MP3_BITRATE = 128


class AudioFormatError(Exception):
    """The audio file could not be read or written."""

    def __init__(self, action: str) -> None:
        super().__init__(action)
        self.action = action


def load_audio(path: Path) -> np.ndarray:
    """Return one mono channel of float32 samples at ``SAMPLE_RATE``."""
    if path.suffix.lower() not in AUDIO_SUFFIXES:
        raise AudioFormatError("read")
    try:
        decoded = miniaudio.decode_file(
            str(path),
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=SAMPLE_RATE,
        )
    except miniaudio.DecodeError as exc:
        raise AudioFormatError("read") from exc
    waveform = np.array(decoded.samples, dtype=np.float32, copy=True).reshape(-1)
    if waveform.size == 0:
        raise AudioFormatError("read")
    return waveform


def subtract_extracted(mixture: np.ndarray, extracted: np.ndarray) -> np.ndarray:
    """Return the mixture with the extracted waveform removed.

    Both arrays are mono float samples at the same rate. The residual is scaled
    only when its peak would clip.
    """
    mixture = np.asarray(mixture, dtype=np.float32).reshape(-1)
    extracted = np.asarray(extracted, dtype=np.float32).reshape(-1)
    length = min(mixture.size, extracted.size)
    residual = mixture[:length] - extracted[:length]
    if length == 0:
        return residual
    peak = float(np.max(np.abs(residual)))
    if peak > 0.99:
        residual = residual * np.float32(0.99 / peak)
    return residual


def save_audio(path: Path, waveform: np.ndarray) -> None:
    """Write ``waveform`` using the suffix of ``path``."""
    suffix = path.suffix.lower()
    if suffix not in AUDIO_SUFFIXES:
        raise AudioFormatError("write")
    samples = np.asarray(waveform, dtype=np.float32).reshape(-1)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if suffix == ".wav":
            sf.write(path, samples, SAMPLE_RATE, subtype="FLOAT")
        elif suffix == ".ogg":
            sf.write(path, samples, SAMPLE_RATE, format="OGG", subtype="VORBIS")
        else:
            _write_mp3(path, samples)
    except (OSError, ValueError, RuntimeError) as exc:
        raise AudioFormatError("write") from exc


def _write_mp3(path: Path, samples: np.ndarray) -> None:
    import lameenc

    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(_MP3_BITRATE)
    encoder.set_in_sample_rate(SAMPLE_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    path.write_bytes(encoder.encode(pcm.tobytes()) + encoder.flush())
