import sys
from pathlib import Path

from audiosep_app.paths import default_clap_path, default_separator_path, model_directory


def test_development_models_live_in_local() -> None:
    root = Path(__file__).resolve().parents[1]

    assert model_directory() == root / "local"
    assert default_separator_path() == root / "local" / "separator.onnx"
    assert default_clap_path() == root / "local" / "clap_text.onnx"


def test_packaged_macos_models_live_inside_the_app(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "AudioSep.app" / "Contents" / "MacOS" / "AudioSep"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    models = executable.parent / "models"
    assert model_directory() == models
    assert default_separator_path() == models / "separator.onnx"
    assert default_clap_path() == models / "clap_text.onnx"


def test_packaged_models_live_beside_the_executable(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "AudioSep"
    executable.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert model_directory() == tmp_path / "models"
    assert default_separator_path() == tmp_path / "models" / "separator.onnx"
    assert default_clap_path() == tmp_path / "models" / "clap_text.onnx"
