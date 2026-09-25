import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from bundle.build import configure_stdio, create_dmg, create_zip, macos_archive_name, place_models


def test_stdio_is_switched_to_utf8(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    class Stream:
        def reconfigure(self, **kwargs: str) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(sys, "stdout", Stream())
    monkeypatch.setattr(sys, "stderr", Stream())

    configure_stdio()

    assert calls == [
        {"encoding": "utf-8", "errors": "replace"},
        {"encoding": "utf-8", "errors": "replace"},
    ]


def test_macos_archive_name_follows_the_cpu() -> None:
    assert macos_archive_name("arm64") == "AudioSep-macos-arm64.dmg"
    assert macos_archive_name("aarch64") == "AudioSep-macos-arm64.dmg"
    assert macos_archive_name("x86_64") == "AudioSep-macos-x86_64.dmg"
    assert macos_archive_name("amd64") == "AudioSep-macos-x86_64.dmg"


def test_unknown_macos_cpu_is_refused() -> None:
    with pytest.raises(SystemExit, match="ppc"):
        macos_archive_name("ppc")


def test_models_are_copied_into_the_image_directory(tmp_path: Path) -> None:
    models = tmp_path / "models"
    local = tmp_path / "local"
    local.mkdir()
    (local / "separator.onnx").write_bytes(b"separator")
    (local / "clap_text.onnx").write_bytes(b"clap")
    (local / "other.bin").write_bytes(b"skip")

    copied = place_models(models, local)

    assert copied == ["separator.onnx", "clap_text.onnx"]
    assert (models / "separator.onnx").read_bytes() == b"separator"
    assert (models / "clap_text.onnx").read_bytes() == b"clap"
    assert not (models / "other.bin").exists()


def test_missing_models_still_create_the_directory(tmp_path: Path) -> None:
    models = tmp_path / "models"

    copied = place_models(models, tmp_path / "local")

    assert copied == []
    assert models.is_dir()


def test_dmg_without_models_is_refused(tmp_path: Path) -> None:
    app = tmp_path / "AudioSep.app"
    app.mkdir()

    with pytest.raises(SystemExit, match="separator.onnx"):
        create_dmg(app, tmp_path / "AudioSep.dmg", tmp_path / "local")


@pytest.mark.skipif(sys.platform != "darwin", reason="DMG is built on macOS")
def test_dmg_contains_the_app_and_applications_link(tmp_path: Path) -> None:
    app = tmp_path / "AudioSep.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True)
    (macos / "AudioSep").write_text("bin", encoding="utf-8")
    models = tmp_path / "local"
    models.mkdir()
    (models / "separator.onnx").write_bytes(b"separator")
    (models / "clap_text.onnx").write_bytes(b"clap")
    image = tmp_path / "AudioSep.dmg"
    mount = tmp_path / "mount"
    mount.mkdir()

    create_dmg(app, image, models)

    subprocess.run(
        [
            "hdiutil",
            "attach",
            "-nobrowse",
            "-readonly",
            "-mountpoint",
            str(mount),
            str(image),
        ],
        check=True,
    )
    try:
        bundled = mount / "AudioSep.app" / "Contents" / "MacOS" / "AudioSep"
        assert bundled.read_text(encoding="utf-8") == "bin"
        assert not (mount / "models").exists()
        macos_models = mount / "AudioSep.app" / "Contents" / "MacOS" / "models"
        assert (macos_models / "separator.onnx").read_bytes() == b"separator"
        assert (macos_models / "clap_text.onnx").read_bytes() == b"clap"
        assert (mount / "Applications").is_symlink()
        assert (mount / "Applications").readlink() == Path("/Applications")
    finally:
        subprocess.run(["hdiutil", "detach", str(mount)], check=True)


def test_zip_without_models_is_refused(tmp_path: Path) -> None:
    collect = tmp_path / "AudioSep"
    collect.mkdir()

    with pytest.raises(SystemExit, match="separator.onnx"):
        create_zip(collect, tmp_path / "AudioSep-windows.zip", tmp_path / "local")


def test_zip_contains_the_executable_and_models_beside_it(tmp_path: Path) -> None:
    collect = tmp_path / "AudioSep"
    internal = collect / "_internal"
    internal.mkdir(parents=True)
    (collect / "AudioSep.exe").write_bytes(b"exe")
    (internal / "tokenizer.json").write_text("{}", encoding="utf-8")
    models = tmp_path / "local"
    models.mkdir()
    (models / "separator.onnx").write_bytes(b"separator")
    (models / "clap_text.onnx").write_bytes(b"clap")

    archive = create_zip(collect, tmp_path / "out" / "AudioSep-windows.zip", models)

    with zipfile.ZipFile(archive) as zipped:
        names = {name.replace("\\", "/") for name in zipped.namelist()}
        assert "AudioSep/AudioSep.exe" in names
        assert zipped.read("AudioSep/models/separator.onnx") == b"separator"
        assert zipped.read("AudioSep/models/clap_text.onnx") == b"clap"
        assert "AudioSep/_internal/tokenizer.json" in names
    assert not (collect / "_internal" / "models").exists()


def test_linux_zip_keeps_the_executable_name(tmp_path: Path) -> None:
    collect = tmp_path / "AudioSep"
    collect.mkdir()
    (collect / "AudioSep").write_bytes(b"elf")
    models = tmp_path / "local"
    models.mkdir()
    (models / "separator.onnx").write_bytes(b"separator")
    (models / "clap_text.onnx").write_bytes(b"clap")

    archive = create_zip(collect, tmp_path / "AudioSep-linux.zip", models)

    with zipfile.ZipFile(archive) as zipped:
        names = {name.replace("\\", "/") for name in zipped.namelist()}
        assert "AudioSep/AudioSep" in names
        assert "AudioSep/models/separator.onnx" in names
        assert "AudioSep/models/clap_text.onnx" in names
