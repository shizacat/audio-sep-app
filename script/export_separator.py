"""Export the AudioSep separator network to ONNX.

The text encoder stays in PyTorch. This script exports one fixed-length chunk
of ResUNet30: mixture waveform plus a condition vector in, waveform out.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIOSEP_ROOT = APP_ROOT.parent / "AudioSplit" / "AudioSep"
CHUNK_SAMPLES = 160_000
CONDITION_SIZE = 512


class SeparatorGraph(nn.Module):
    def __init__(self, separator: nn.Module) -> None:
        super().__init__()
        self.separator = separator

    def forward(self, mixture: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        return self.separator({"mixture": mixture, "condition": condition})["waveform"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the AudioSep separator to ONNX.")
    parser.add_argument("--audiosep-root", type=Path, default=DEFAULT_AUDIOSEP_ROOT)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "local" / "separator.onnx",
    )
    return parser.parse_args()


def load_separator(audiosep_root: Path, checkpoint: Path) -> nn.Module:
    sys.path.insert(0, str(audiosep_root))
    from models.resunet import ResUNet30
    from torchlibrosa.stft import ISTFT

    separator = ResUNet30(
        input_channels=1,
        output_channels=1,
        condition_size=CONDITION_SIZE,
    )
    loaded = torch.load(checkpoint, map_location="cpu", weights_only=False)
    state = loaded["state_dict"] if isinstance(loaded, dict) and "state_dict" in loaded else loaded
    separator_state = {
        key.removeprefix("ss_model."): value
        for key, value in state.items()
        if key.startswith("ss_model.")
    }
    separator.load_state_dict(separator_state)

    with torch.no_grad():
        real, _imag = separator.base.stft(torch.zeros(1, CHUNK_SAMPLES))
    frames = int(real.shape[2])
    separator.base.istft = ISTFT(
        n_fft=2048,
        hop_length=320,
        win_length=2048,
        window="hann",
        center=True,
        pad_mode="reflect",
        freeze_parameters=True,
        onnx=True,
        frames_num=frames,
        device="cpu",
    )
    separator.eval()
    return separator


def export(graph: SeparatorGraph, mixture: torch.Tensor, condition: torch.Tensor, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        graph,
        (mixture, condition),
        str(output),
        input_names=["mixture", "condition"],
        output_names=["waveform"],
        dynamo=False,
        opset_version=17,
    )


def check_onnx(path: Path, graph: SeparatorGraph, mixture: torch.Tensor, condition: torch.Tensor) -> float:
    import onnxruntime as ort

    with torch.no_grad():
        reference = graph(mixture, condition).numpy()
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    (exported,) = session.run(
        None,
        {"mixture": mixture.numpy(), "condition": condition.numpy()},
    )
    return float(np.max(np.abs(reference - exported)))


def main() -> None:
    args = parse_args()
    checkpoint = args.checkpoint or args.audiosep_root / "checkpoint" / "audiosep_base_4M_steps.ckpt"
    if not args.audiosep_root.is_dir():
        raise SystemExit(f"AudioSep checkout not found: {args.audiosep_root}")
    if not checkpoint.is_file():
        raise SystemExit(f"Checkpoint not found: {checkpoint}")

    separator = load_separator(args.audiosep_root, checkpoint)
    graph = SeparatorGraph(separator).eval()
    mixture = torch.randn(1, 1, CHUNK_SAMPLES)
    condition = torch.randn(1, CONDITION_SIZE)

    export(graph, mixture, condition, args.output)
    difference = check_onnx(args.output, graph, mixture, condition)
    print(f"Wrote {args.output}")
    print(f"Max absolute difference: {difference:.3e}")
    if difference > 1e-3:
        raise SystemExit("ONNX output does not match PyTorch.")


if __name__ == "__main__":
    main()
