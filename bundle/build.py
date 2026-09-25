"""Build the macOS app with PyInstaller and pack it into a disk image.

The same command is used locally and in GitHub Actions.
``build/`` is PyInstaller's work directory. The file there is not the app.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

APP_NAME = "AudioSep"
MODEL_FILES = ("separator.onnx", "clap_text.onnx")


def macos_executable_dir(dist: Path) -> Path:
    """Directory that contains the frozen executable inside the .app bundle."""
    return dist / f"{APP_NAME}.app" / "Contents" / "MacOS"


def place_models(models_dir: Path, source_dir: Path) -> list[str]:
    """Copy ONNX files into ``models_dir``. Missing files are skipped."""
    models_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in MODEL_FILES:
        source = source_dir / name
        if source.is_file():
            shutil.copy2(source, models_dir / name)
            copied.append(name)
    return copied


def assert_bundle(executable_dir: Path) -> None:
    executable = executable_dir / APP_NAME
    if not executable.is_file():
        raise SystemExit(f"Исполняемый файл не найден: {executable}")
    tokenizer = list(executable_dir.parent.parent.rglob("tokenizer.json"))
    if not tokenizer:
        raise SystemExit(f"В пакете нет tokenizer.json: {executable_dir.parent.parent}")


def create_dmg(app: Path, destination: Path, models_dir: Path) -> Path:
    """Write a disk image with the app, ``models`` beside it, and a link to /Applications."""
    if not app.is_dir():
        raise SystemExit(f"Приложение не найдено: {app}")
    missing = [name for name in MODEL_FILES if not (models_dir / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"В образ нечего положить: нет {joined} в {models_dir}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="audiosep-dmg-") as raw_stage:
        stage = Path(raw_stage)
        subprocess.run(["ditto", str(app), str(stage / app.name)], check=True)
        place_models(stage / "models", models_dir)
        (stage / "Applications").symlink_to("/Applications")
        if destination.exists():
            destination.unlink()
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                APP_NAME,
                "-srcfolder",
                str(stage),
                "-ov",
                "-format",
                "UDZO",
                str(destination),
            ],
            check=True,
        )
    return destination


def build(root: Path) -> Path:
    if sys.platform != "darwin":
        raise SystemExit("Сборка пакета пока реализована только для macOS.")
    spec = root / "bundle" / "audiosep.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)],
        cwd=root,
        check=True,
    )
    executable_dir = macos_executable_dir(root / "dist")
    assert_bundle(executable_dir)
    app = executable_dir.parent.parent
    image = create_dmg(app, root / "dist" / f"{APP_NAME}.dmg", root / "local")
    print(f"Модели в образе: {', '.join(MODEL_FILES)}")
    print(image)
    return image


def main() -> None:
    build(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
