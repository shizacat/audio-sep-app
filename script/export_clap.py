"""Export the AudioSep CLAP text encoder to ONNX.

Tokenization stays outside the graph. The exported model takes RoBERTa
input ids and an attention mask and returns one L2-normalized embedding
per text. That vector is the separator condition.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIOSEP_ROOT = APP_ROOT.parent / "AudioSplit" / "AudioSep"
TEXT_LENGTH = 512
SAMPLE_TEXT = "a child speaking"


class ClapTextGraph(nn.Module):
    def __init__(self, clap: nn.Module) -> None:
        super().__init__()
        self.clap = clap

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        features = self.clap.encode_text(
            {"input_ids": input_ids, "attention_mask": attention_mask},
            device=input_ids.device,
        )
        return F.normalize(features, dim=-1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the CLAP text encoder to ONNX.")
    parser.add_argument("--audiosep-root", type=Path, default=DEFAULT_AUDIOSEP_ROOT)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=APP_ROOT / "local" / "clap_text.onnx")
    return parser.parse_args()


def allow_checkpoint_load() -> None:
    original_load = torch.load

    def load_checkpoint(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = load_checkpoint


def load_text_encoder(audiosep_root: Path, checkpoint: Path) -> nn.Module:
    sys.path.insert(0, str(audiosep_root))
    allow_checkpoint_load()
    from models.clap_encoder import CLAP_Encoder

    encoder = CLAP_Encoder(pretrained_path=str(checkpoint))
    encoder.eval()
    return encoder


def tokenize(encoder: nn.Module, text: str) -> tuple[torch.Tensor, torch.Tensor]:
    tokens = encoder.tokenize(
        text,
        padding="max_length",
        truncation=True,
        max_length=TEXT_LENGTH,
        return_tensors="pt",
    )
    return tokens["input_ids"], tokens["attention_mask"]


def export(
    graph: ClapTextGraph,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        graph,
        (input_ids, attention_mask),
        str(output),
        input_names=["input_ids", "attention_mask"],
        output_names=["embedding"],
        dynamic_axes={
            "input_ids": {0: "batch"},
            "attention_mask": {0: "batch"},
            "embedding": {0: "batch"},
        },
        dynamo=False,
        opset_version=17,
    )


def check_onnx(
    path: Path,
    graph: ClapTextGraph,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
) -> float:
    import onnxruntime as ort

    with torch.no_grad():
        reference = graph(input_ids, attention_mask).numpy()
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    (exported,) = session.run(
        None,
        {
            "input_ids": input_ids.numpy(),
            "attention_mask": attention_mask.numpy(),
        },
    )
    return float(np.max(np.abs(reference - exported)))


def main() -> None:
    args = parse_args()
    checkpoint = args.checkpoint or (
        args.audiosep_root / "checkpoint" / "music_speech_audioset_epoch_15_esc_89.98.pt"
    )
    if not args.audiosep_root.is_dir():
        raise SystemExit(f"AudioSep checkout not found: {args.audiosep_root}")
    if not checkpoint.is_file():
        raise SystemExit(f"Checkpoint not found: {checkpoint}")

    encoder = load_text_encoder(args.audiosep_root, checkpoint)
    graph = ClapTextGraph(encoder.model).eval()
    input_ids, attention_mask = tokenize(encoder, SAMPLE_TEXT)

    export(graph, input_ids, attention_mask, args.output)
    difference = check_onnx(args.output, graph, input_ids, attention_mask)
    print(f"Wrote {args.output}")
    print(f"Max absolute difference: {difference:.3e}")
    if difference > 1e-3:
        raise SystemExit("ONNX output does not match PyTorch.")


if __name__ == "__main__":
    main()
