"""Build the desktop app with PyInstaller.

macOS becomes ``dist/AudioSep.dmg``. Windows becomes ``dist/AudioSep-windows.zip``.
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


def windows_collect_dir(dist: Path) -> Path:
    """Directory that contains AudioSep.exe and the collected runtime."""
    return dist / APP_NAME


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


def assert_application(executable: Path, search_root: Path) -> None:
    if not executable.is_file():
        raise SystemExit(f"Исполняемый файл не найден: {executable}")
    if not list(search_root.rglob("tokenizer.json")):
        raise SystemExit(f"В пакете нет tokenizer.json: {search_root}")


def require_models(models_dir: Path) -> None:
    missing = [name for name in MODEL_FILES if not (models_dir / name).is_file()]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"В пакет нечего положить: нет {joined} в {models_dir}")


def create_dmg(app: Path, destination: Path, models_dir: Path) -> Path:
    """Write a disk image with the app, ``models`` beside it, and a link to /Applications."""
    if not app.is_dir():
        raise SystemExit(f"Приложение не найдено: {app}")
    require_models(models_dir)
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


def create_zip(collect_dir: Path, destination: Path, models_dir: Path) -> Path:
    """Zip the Windows folder with ``models`` next to ``AudioSep.exe``."""
    if not collect_dir.is_dir():
        raise SystemExit(f"Каталог приложения не найден: {collect_dir}")
    require_models(models_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    place_models(collect_dir / "models", models_dir)
    if destination.exists():
        destination.unlink()
    archive = shutil.make_archive(
        str(destination.with_suffix("")),
        "zip",
        root_dir=collect_dir.parent,
        base_dir=collect_dir.name,
    )
    return Path(archive)


def run_pyinstaller(root: Path) -> None:
    spec = root / "bundle" / "audiosep.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(spec)],
        cwd=root,
        check=True,
    )


def build_macos(root: Path) -> Path:
    run_pyinstaller(root)
    executable_dir = macos_executable_dir(root / "dist")
    app = executable_dir.parent.parent
    assert_application(executable_dir / APP_NAME, app)
    image = create_dmg(app, root / "dist" / f"{APP_NAME}.dmg", root / "local")
    print(f"Модели в образе: {', '.join(MODEL_FILES)}")
    print(image)
    return image


def build_windows(root: Path) -> Path:
    run_pyinstaller(root)
    collect = windows_collect_dir(root / "dist")
    assert_application(collect / f"{APP_NAME}.exe", collect)
    archive = create_zip(collect, root / "dist" / f"{APP_NAME}-windows.zip", root / "local")
    print(f"Модели в архиве: {', '.join(MODEL_FILES)}")
    print(archive)
    return archive


def build(root: Path) -> Path:
    if sys.platform == "darwin":
        return build_macos(root)
    if sys.platform == "win32":
        return build_windows(root)
    raise SystemExit("Сборка пакета пока реализована только для macOS и Windows.")


def main() -> None:
    build(Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
